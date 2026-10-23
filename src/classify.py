from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .config import DEV_PATH

try:
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - fallback is for minimal installs
    CalibratedClassifierCV = None
    SKLEARN_AVAILABLE = False

MANDATORY_ESCALATION_INTENTS = {"compliance_request", "security_incident", "feature_request", "unclear_request", "data_residency"}

class TicketClassifier:
    """Supervised baseline trained only on labelled development tickets."""
    def __init__(self, development_path: Path = DEV_PATH):
        self.intent_model = self.urgency_model = self.route_model = self.answerability_model = None
        self.intent_counts: Counter[str] = Counter()
        self._fallback_intents: list[tuple[str, set[str]]] = [
            ("security_incident", {"breach", "exposed", "compromised", "unauthorized", "stolen", "leaked", "security incident"}),
            ("compliance_request", {"compliance", "regulatory", "audit evidence", "certification", "official statement"}),
            ("billing_query", {"invoice", "billing", "charged", "payment", "refund", "subscription"}),
            ("api_key_issue", {"api key", "rotate key", "key rotation", "401", "credential"}),
            ("authentication_failure", {"login", "log in", "password", "authentication", "invalid credentials"}),
            ("deployment_failure", {"deploy", "deployment", "build failed", "rollback", "release"}),
            ("webhook_issue", {"webhook", "callback", "delivery attempt", "signature"}),
            ("rate_limit", {"rate limit", "429", "throttl", "quota"}),
            ("data_residency", {"data residency", "region", "residency", "where is data stored"}),
            ("data_export", {"export", "download my data", "data portability"}),
            ("database_issue", {"database", "query", "connection pool", "sql"}),
            ("performance_degradation", {"slow", "latency", "performance", "timeout"}),
            ("sso_configuration", {"sso", "saml", "single sign-on", "identity provider"}),
            ("onboarding", {"getting started", "onboarding", "set up account", "invite user"}),
            ("integration_help", {"integrate", "integration", "sdk", "connect"}),
            ("api_usage_question", {"api", "endpoint", "request body", "parameter"}),
            ("configuration_help", {"configure", "configuration", "setting", "environment variable"}),
            ("quota_or_overage", {"overage", "quota", "usage limit", "limit exceeded"}),
            ("rollback_request", {"rollback", "revert release", "previous version"}),
            ("account_access", {"access", "permissions", "role", "invitation"}),
            ("feature_request", {"feature request", "please add", "would like a feature"}),
        ]
        try:
            data = json.loads(Path(development_path).read_text(encoding="utf-8"))
            rows = [x for x in data if isinstance(x, dict) and isinstance(x.get("labels"), dict) and x.get("body") is not None]
            texts = [self._text(x) for x in rows]
            intents = [str(x["labels"].get("intent", "unclear_request")) for x in rows]
            urgencies = [str(x["labels"].get("urgency", "medium")) for x in rows]
            routes = [str(x["labels"].get("expected_route", "escalate")) for x in rows]
            answerability = [str(bool(x["labels"].get("answerable_from_docs", False))) for x in rows]
            self.intent_counts.update(intents)
            if SKLEARN_AVAILABLE and len(rows) >= 20:
                self.intent_model = self._fit_calibrated(texts, intents)
                self.urgency_model = self._fit_calibrated(texts, urgencies)
                self.route_model = self._fit_calibrated(texts, routes)
                if len(set(answerability)) > 1:
                    self.answerability_model = self._fit_calibrated(texts, answerability)
        except Exception:
            pass

    @staticmethod
    def _text(ticket: dict[str, Any]) -> str:
        return f"{ticket.get('subject', '')} {ticket.get('body', ticket.get('message', ''))}".strip()

    @staticmethod
    def _make_model():
        return Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True, strip_accents="unicode")),
            ("clf", LogisticRegression(max_iter=700, class_weight="balanced", random_state=17, C=2.0)),
        ])

    @classmethod
    def _fit_calibrated(cls, texts: list[str], labels: list[str]):
        """Fit probability-calibrated scores using development data only."""
        base = cls._make_model()
        if CalibratedClassifierCV is None:
            return base.fit(texts, labels)
        return CalibratedClassifierCV(estimator=base, method="sigmoid", cv=3).fit(texts, labels)

    @staticmethod
    def _predict(model, text: str, fallback: str) -> tuple[str, float, list[dict[str, Any]]]:
        if model is None:
            return fallback, 0.45, [{"label": fallback, "score": 0.45}]
        try:
            probs = model.predict_proba([text])[0]
            classes = model.classes_
            order = sorted(range(len(probs)), key=lambda i: float(probs[i]), reverse=True)
            best = order[0]
            alternatives = [{"label": str(classes[i]), "score": round(float(probs[i]), 4)} for i in order[:3]]
            return str(classes[best]), round(float(probs[best]), 4), alternatives
        except Exception:
            return fallback, 0.45, [{"label": fallback, "score": 0.45}]

    @staticmethod
    def _explicit_intent_rule(text: str) -> str | None:
        lower = text.lower()
        # Data-location wording takes precedence over a generic mention of compliance.
        if any(term in lower for term in ("data residency", "data location", "where is data stored", "data to remain within", "replicated outside our primary region", "stored within the eu")):
            return "data_residency"
        if any(term in lower for term in ("compliance certification", "official compliance statement", "regulatory statement", "audit evidence", "soc 2 report", "iso 27001", "official statement confirming")):
            return "compliance_request"
        return None

    @staticmethod
    def _class_probability(model, text: str, label: str) -> float | None:
        if model is None:
            return None
        try:
            classes = list(model.classes_)
            if label not in classes:
                return None
            probabilities = model.predict_proba([text])[0]
            return round(float(probabilities[classes.index(label)]), 4)
        except Exception:
            return None

    def _positive_probability(self, model, text: str, positive_label: str = "True") -> float:
        if model is None:
            return 0.5
        try:
            classes = list(model.classes_)
            if positive_label not in classes:
                return 0.0
            probabilities = model.predict_proba([text])[0]
            return round(float(probabilities[classes.index(positive_label)]), 4)
        except Exception:
            return 0.5

    def classify(self, ticket: dict[str, Any]) -> dict[str, Any]:
        text = self._text(ticket)
        low = text.lower()
        fallback_intent = "unclear_request"
        for intent, terms in self._fallback_intents:
            if any(term in low for term in terms):
                fallback_intent = intent
                break
        intent, intent_conf, intent_alts = self._predict(self.intent_model, text, fallback_intent)
        intent_method = "calibrated_model"
        explicit_intent = self._explicit_intent_rule(text)
        if explicit_intent:
            intent_method = "explicit_safety_rule"
            explicit_probability = self._class_probability(self.intent_model, text, explicit_intent)
            intent = explicit_intent
            if explicit_probability is not None:
                intent_conf = explicit_probability
            intent_alts = [{"label": explicit_intent, "score": intent_conf}] + [item for item in intent_alts if item["label"] != explicit_intent][:2]
            intent_alts = sorted(intent_alts, key=lambda item: float(item["score"]), reverse=True)
        urgency, urgency_conf, urgency_alts = self._predict(self.urgency_model, text, "medium")
        route, route_conf, route_alts = self._predict(self.route_model, text, "escalate")
        answerable_probability = self._positive_probability(self.answerability_model, text)
        # Deterministic hard safety overrides always supersede model predictions.
        if intent in MANDATORY_ESCALATION_INTENTS:
            route, route_conf = "escalate", max(route_conf, 0.99)
            route_alts = [{"label": "escalate", "score": route_conf}] + [x for x in route_alts if x["label"] != "escalate"][:2]
        if not text:
            intent, intent_conf, urgency, urgency_conf, route, route_conf = "unclear_request", 0.0, "medium", 0.0, "escalate", 1.0
        return {
            "intent": intent,
            "intent_method": intent_method,
            "intent_confidence": intent_conf,
            "intent_alternatives": intent_alts,
            "urgency": urgency,
            "urgency_confidence": urgency_conf,
            "urgency_alternatives": urgency_alts,
            "route_prediction": route,
            "route_confidence": route_conf,
            "route_alternatives": route_alts,
            "answerable_probability": answerable_probability,
            "answerability_prediction": answerable_probability >= 0.5,
        }

_classifier: TicketClassifier | None = None

def get_classifier() -> TicketClassifier:
    global _classifier
    if _classifier is None:
        _classifier = TicketClassifier()
    return _classifier
