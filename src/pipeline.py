from __future__ import annotations
import logging
import time
from datetime import datetime, timezone
from typing import Any

from .classify import get_classifier, MANDATORY_ESCALATION_INTENTS
from .config import CONFIDENCE_THRESHOLD, ANSWERABILITY_THRESHOLD, RETRIEVAL_TOP_K, USE_LLM
from .generate import get_generator
from .guardrails import validate_response, detect_prompt_injection
from .ingest import normalize_ticket
from .logging_store import DecisionLogger
from .retrieve import get_retriever
from .routing import human_review_override

logger = logging.getLogger(__name__)


def _retrieval_confidence(sources: list[dict[str, Any]]) -> float:
    """Derive a confidence score from retrieval similarity scores (Requirement 6.2).

    The score equals the maximum cosine/TF-IDF similarity across retrieved passages,
    clamped to [0.0, 1.0].  When there are no sources the score is 0.0.
    """
    if not sources:
        return 0.0
    return float(min(1.0, max(0.0, max(s.get("score", 0.0) for s in sources))))


def _normalise_body_with_llm(text: str) -> str | None:
    """Use the LLM to paraphrase a non-fluent ticket body into standard English.

    Returns the normalised paraphrase or None if normalisation fails / LLM is disabled.
    """
    if not USE_LLM:
        return None
    try:
        from .generate import ResponseGenerator, OPENROUTER_API_KEY
        if not OPENROUTER_API_KEY:
            return None
        # Minimal prompt: restate the message in clear standard English, nothing else.
        user_content = (
            f"Restate the following customer message in clear, standard English without "
            f"adding any new information or claims. Output only the restatement.\n\n"
            f"Message: {text}"
        )
        normalised = ResponseGenerator._invoke_model(user_content)
        return normalised.strip() if normalised else None
    except Exception as exc:
        logger.warning("Non-fluent normalisation failed: %s", exc)
        return None


class SupportPipeline:
    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        answerability_threshold: float = ANSWERABILITY_THRESHOLD,
        enable_langgraph: bool = True,
    ):
        self.confidence_threshold = confidence_threshold
        self.answerability_threshold = answerability_threshold
        self.classifier = get_classifier()
        self.retriever = get_retriever()
        self.generator = get_generator()
        self.logger_store = DecisionLogger()
        self.graph = self._build_graph() if enable_langgraph else None

    # ------------------------------------------------------------------ nodes

    def _classify_node(self, state: dict[str, Any]) -> dict[str, Any]:
        state["classification"] = self.classifier.classify(state["ticket"])
        return state

    def _retrieve_node(self, state: dict[str, Any]) -> dict[str, Any]:
        ticket = state["ticket"]
        query_text = ticket.get("normalised_text") or ticket.get("text", "")
        state["sources"] = self.retriever.search(query_text, top_k=RETRIEVAL_TOP_K)
        # Confidence is derived from retrieval similarity scores (Requirement 6.2).
        state["retrieval_confidence"] = _retrieval_confidence(state["sources"])
        return state

    def _route_node(self, state: dict[str, Any]) -> dict[str, Any]:
        c = state["classification"]
        ticket_text = state["ticket"].get("text", "")
        override_reason = human_review_override(ticket_text, c.get("intent", "unclear_request"))

        if detect_prompt_injection(ticket_text):
            state["decision"] = "escalate"
            state["decision_reason"] = (
                "Prompt-injection pattern detected in customer-provided text; "
                "automated response blocked."
            )
            state["guardrail"] = {
                "passed": False,
                "blocked": True,
                "issues": ["prompt_injection_attempt"],
                "private_data_types": [],
                "must_not_claim_violations": [],
                "checks": ["prompt_injection_scan"],
            }
        elif not ticket_text.strip():
            state["decision"] = "escalate"
            state["decision_reason"] = "The ticket has no usable message text."
        elif override_reason:
            state["decision"] = "escalate"
            state["decision_reason"] = override_reason
        elif c["intent"] in MANDATORY_ESCALATION_INTENTS:
            state["decision"] = "escalate"
            state["decision_reason"] = (
                f"The {c['intent'].replace('_', ' ')} category requires human review."
            )
        elif c["route_prediction"] != "auto_respond":
            state["decision"] = "escalate"
            state["decision_reason"] = (
                "The routing classifier predicts human review is appropriate."
            )
        elif c["route_confidence"] < self.confidence_threshold:
            state["decision"] = "escalate"
            state["decision_reason"] = (
                f"Routing confidence ({c['route_confidence']:.2f}) is below the configured "
                f"threshold ({self.confidence_threshold:.2f})."
            )
        elif c.get("answerable_probability", 0.0) < self.answerability_threshold:
            state["decision"] = "escalate"
            state["decision_reason"] = (
                f"Estimated documentation answerability "
                f"({c.get('answerable_probability', 0.0):.2f}) is below the configured "
                f"threshold ({self.answerability_threshold:.2f})."
            )
        elif not state.get("sources"):
            state["decision"] = "escalate"
            state["decision_reason"] = (
                "No documentation passage met the retrieval relevance threshold."
            )
        elif state["retrieval_confidence"] < self.confidence_threshold:
            state["decision"] = "escalate"
            state["decision_reason"] = (
                f"Retrieval confidence ({state['retrieval_confidence']:.2f}) is below the "
                f"configured threshold ({self.confidence_threshold:.2f})."
            )
        else:
            state["decision"] = "auto_respond"
            state["decision_reason"] = (
                "Intent is eligible, routing and answerability thresholds are met, "
                "and relevant documentation was retrieved."
            )
        return state

    def _generate_node(self, state: dict[str, Any]) -> dict[str, Any]:
        answer, mode = self.generator.generate(
            state["ticket"], state["classification"], state.get("sources", [])
        )
        state["draft_response"] = answer
        state["generation_mode"] = mode
        return state

    def _validate_node(self, state: dict[str, Any]) -> dict[str, Any]:
        ticket = state["ticket"]
        must_not_claim: list[str] = ticket.get("original", {}).get("must_not_claim", []) or []
        verdict = validate_response(
            state.get("draft_response", ""),
            state.get("sources", []),
            ticket.get("text", ""),
            must_not_claim=must_not_claim,
        )
        state["guardrail"] = verdict
        if not verdict["passed"]:
            state["decision"] = "escalate"
            state["decision_reason"] = (
                "Response blocked by guardrails: " + ", ".join(verdict["issues"])
            )
            state["draft_response"] = None
            verdict["blocked"] = True
        else:
            verdict["blocked"] = False
        return state

    def _finalize_node(self, state: dict[str, Any]) -> dict[str, Any]:
        c = state.get("classification", {})
        is_auto = state.get("decision") == "auto_respond"
        ticket = state["ticket"]
        sources = [
            {
                "doc_id": s["doc_id"],
                "passage_id": s["passage_id"],
                "title": s["title"],
                "score": s["score"],
                "passage_text": s["content"],
            }
            for s in state.get("sources", [])
        ]
        return {
            "ticket_id": ticket["ticket_id"],
            "channel": ticket["channel"],
            "decision": "auto_respond" if is_auto else "escalate",
            "intent": c.get("intent", "unclear_request"),
            "intent_method": c.get("intent_method", "fallback"),
            "intent_confidence": c.get("intent_confidence", 0.0),
            "urgency": c.get("urgency", "medium"),
            "urgency_confidence": c.get("urgency_confidence", 0.0),
            # confidence is now retrieval-derived (Requirement 6.2)
            "confidence": state.get("retrieval_confidence", 0.0),
            "answerable_probability": c.get("answerable_probability", 0.5),
            "answerability_prediction": c.get("answerability_prediction", False),
            "alternatives": {
                "intent": c.get("intent_alternatives", []),
                "urgency": c.get("urgency_alternatives", []),
                "route": c.get("route_alternatives", []),
            },
            "decision_reason": state.get("decision_reason", "No decision reason supplied."),
            "response": state.get("draft_response") if is_auto else None,
            "escalation_summary": (
                None
                if is_auto
                else self._escalation_summary(
                    ticket, c, state.get("decision_reason", "Human review required.")
                )
            ),
            "sources": sources,
            "guardrail": state.get(
                "guardrail", {"passed": True, "issues": [], "checks": ["routing_safety"]}
            ),
            "generation_mode": state.get("generation_mode"),
            "error_type": state.get("error_type"),
            # Carry ticket metadata for the decision logger.
            "_ticket_meta": {
                "customer_tier": ticket.get("customer_tier", "unknown"),
                "customer_region": ticket.get("customer_region", "unknown"),
                "original_body": ticket.get("body"),
                "normalised_body": ticket.get("normalised_body"),
            },
        }

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _escalation_summary(
        ticket: dict[str, Any], classification: dict[str, Any], reason: str
    ) -> str:
        body = (ticket.get("text") or "No message content supplied.").strip().replace("\n", " ")
        if len(body) > 450:
            body = body[:447] + "..."
        return (
            f"Human review requested. Intent: {classification.get('intent', 'unclear_request')}; "
            f"urgency: {classification.get('urgency', 'medium')}. Reason: {reason} "
            f"Ticket summary: {body}"
        )

    def _build_graph(self):
        try:
            from langgraph.graph import StateGraph, START, END

            graph = StateGraph(dict)
            graph.add_node("classify", self._classify_node)
            graph.add_node("retrieve", self._retrieve_node)
            graph.add_node("route", self._route_node)
            graph.add_node("generate", self._generate_node)
            graph.add_node("validate", self._validate_node)
            graph.add_node("finalize", self._finalize_node)
            graph.add_edge(START, "classify")
            graph.add_edge("classify", "retrieve")
            graph.add_edge("retrieve", "route")
            graph.add_conditional_edges(
                "route",
                lambda s: "generate" if s.get("decision") == "auto_respond" else "finalize",
                {"generate": "generate", "finalize": "finalize"},
            )
            graph.add_edge("generate", "validate")
            graph.add_conditional_edges(
                "validate", lambda s: "finalize", {"finalize": "finalize"}
            )
            graph.add_edge("finalize", END)
            return graph.compile()
        except Exception as exc:
            logger.info(
                "LangGraph unavailable; using equivalent deterministic node runner: %s", exc
            )
            return None

    # ------------------------------------------------------------------ public

    def process(self, raw_ticket: dict[str, Any], index: int = 0) -> dict[str, Any]:
        started = time.perf_counter()
        ticket_id = (
            str(raw_ticket.get("ticket_id", f"UNKNOWN-{index + 1}"))
            if isinstance(raw_ticket, dict)
            else f"UNKNOWN-{index + 1}"
        )
        channel = (
            str(raw_ticket.get("channel", "unknown"))
            if isinstance(raw_ticket, dict)
            else "unknown"
        )
        try:
            ticket = normalize_ticket(raw_ticket, index)

            # Non-fluent language handling (Requirement 11): normalise before classify/retrieve.
            if ticket.get("language_fluency") == "non_fluent" and ticket.get("text"):
                try:
                    normalised = _normalise_body_with_llm(ticket["text"])
                    if normalised:
                        ticket["normalised_body"] = normalised
                        ticket["normalised_text"] = normalised
                except Exception as exc:
                    logger.warning(
                        "Non-fluent normalisation failed for %s, using raw body: %s",
                        ticket_id,
                        exc,
                    )

            state: dict[str, Any] = {
                "ticket": ticket,
                "decision": "escalate",
                "decision_reason": "Processing started.",
                "retrieval_confidence": 0.0,
            }
            if self.graph is not None:
                result = self.graph.invoke(state)
            else:
                for node in (
                    self._classify_node,
                    self._retrieve_node,
                    self._route_node,
                ):
                    state = node(state)
                if state.get("decision") == "auto_respond":
                    state = self._generate_node(state)
                    state = self._validate_node(state)
                result = self._finalize_node(state)
        except Exception as exc:
            logger.exception("Ticket processing failed for %s", ticket_id)
            result = {
                "ticket_id": ticket_id,
                "channel": channel,
                "decision": "escalate",
                "intent": "unclear_request",
                "intent_confidence": 0.0,
                "urgency": "medium",
                "urgency_confidence": 0.0,
                "confidence": 0.0,
                "answerable_probability": 0.0,
                "answerability_prediction": False,
                "alternatives": {"intent": [], "urgency": [], "route": []},
                "decision_reason": "A processing error occurred; ticket retained for human review.",
                "intent_method": "fallback",
                "response": None,
                "escalation_summary": (
                    f"Human review required because processing failed safely. "
                    f"Ticket ID: {ticket_id}."
                ),
                "sources": [],
                "guardrail": {
                    "passed": False,
                    "blocked": True,
                    "issues": ["processing_error"],
                    "checks": ["exception_fallback"],
                },
                "generation_mode": None,
                "error_type": type(exc).__name__,
                "_ticket_meta": {"customer_tier": "unknown", "customer_region": "unknown"},
            }

        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        result["latency_ms"] = latency_ms
        try:
            self.logger_store.log(result, latency_ms)
        except Exception as exc:
            result["logging_error"] = type(exc).__name__
            logger.exception("Decision log write failed for %s", ticket_id)

        # Strip internal metadata from the public result after logging.
        result.pop("_ticket_meta", None)
        return result
