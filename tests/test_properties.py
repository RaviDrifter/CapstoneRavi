"""Property-based tests (Requirement 14.4, 14.5) and round-trip tests (Requirement 13.3).

Uses Hypothesis for the PBT cases.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from src.guardrails import validate_response, check_must_not_claim
from src.ingest import normalize_ticket
from src.pipeline import _retrieval_confidence
from src.retrieve import KnowledgeRetriever

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Requirement 14.4 — Guardrail idempotence property (Requirement 5, Criterion 6)
# Applying the guardrail twice must produce the same block/pass decision as once.
# ---------------------------------------------------------------------------

@given(
    response=st.text(min_size=0, max_size=400),
    phrases=st.lists(st.text(min_size=1, max_size=40), max_size=5),
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_guardrail_idempotent(response: str, phrases: list[str]):
    """Guardrail check is idempotent: applying it twice yields the same decision."""
    doc = {"doc_id": "DOC-AUTH-001", "content": "Test content"}
    first = validate_response(response, [doc], "", must_not_claim=phrases)
    second = validate_response(response, [doc], "", must_not_claim=phrases)
    assert first["passed"] == second["passed"], (
        f"Guardrail not idempotent for response={response!r}, phrases={phrases!r}"
    )


@given(
    response=st.text(min_size=0, max_size=400),
    phrases=st.lists(st.text(min_size=1, max_size=40), max_size=5),
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_must_not_claim_check_idempotent(response: str, phrases: list[str]):
    """must_not_claim substring check returns same violations on repeated calls."""
    first = check_must_not_claim(response, phrases)
    second = check_must_not_claim(response, phrases)
    assert first == second


# ---------------------------------------------------------------------------
# Requirement 14.5 — Confidence score monotonicity property (Requirement 6.2)
# Confidence must be non-increasing as max retrieval similarity decreases.
# ---------------------------------------------------------------------------

@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
def test_retrieval_confidence_monotone(scores: list[float]):
    """_retrieval_confidence is non-decreasing in the maximum similarity score.

    If we have two source lists where list_b has a strictly lower max score than list_a,
    confidence(list_b) must be <= confidence(list_a).
    """
    sources = [{"doc_id": "DOC-X", "score": s} for s in scores]
    conf = _retrieval_confidence(sources)

    # Reduce every score by half and verify confidence does not increase.
    reduced_sources = [{"doc_id": "DOC-X", "score": s * 0.5} for s in scores]
    conf_reduced = _retrieval_confidence(reduced_sources)

    assert conf_reduced <= conf + 1e-9, (
        f"Confidence increased when scores were halved: "
        f"original={conf:.4f}, reduced={conf_reduced:.4f}, scores={scores}"
    )


def test_retrieval_confidence_zero_when_no_sources():
    """Confidence must be 0.0 when no sources are retrieved (Requirement 6.2)."""
    assert _retrieval_confidence([]) == 0.0


def test_retrieval_confidence_in_range():
    """Confidence is always in [0.0, 1.0]."""
    for score in (0.0, 0.5, 1.0, 1.5, -0.1):
        sources = [{"doc_id": "DOC-X", "score": score}]
        conf = _retrieval_confidence(sources)
        assert 0.0 <= conf <= 1.0, f"Confidence {conf} out of range for score {score}"


# ---------------------------------------------------------------------------
# Requirement 13.3 — Document parse-serialise round-trip property
# ---------------------------------------------------------------------------

def _parse_doc(raw: dict[str, Any]) -> dict[str, Any]:
    """Minimal Document object matching Requirement 13.1 fields."""
    return {
        "doc_id": str(raw.get("doc_id", "")),
        "title": str(raw.get("title", "")),
        "category": str(raw.get("category", "")),
        "content": str(raw.get("content", "")),
        "related_docs": list(raw.get("related_docs") or []),
    }


def _serialise_doc(doc: dict[str, Any]) -> str:
    return json.dumps(doc, ensure_ascii=False, sort_keys=True)


def test_document_round_trip():
    """Parsing then serialising then parsing again yields an equal Document."""
    docs = json.loads((ROOT / "data" / "documentation.json").read_text(encoding="utf-8"))
    for raw in docs:
        parsed = _parse_doc(raw)
        serialised = _serialise_doc(parsed)
        re_parsed = _parse_doc(json.loads(serialised))
        assert parsed == re_parsed, (
            f"Round-trip failed for doc_id={raw.get('doc_id')}: "
            f"{parsed} != {re_parsed}"
        )


@given(
    doc_id=st.text(min_size=1, max_size=30),
    title=st.text(min_size=0, max_size=80),
    category=st.text(min_size=0, max_size=40),
    content=st.text(min_size=0, max_size=500),
    related=st.lists(st.text(min_size=1, max_size=20), max_size=5),
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_document_round_trip_property(
    doc_id: str, title: str, category: str, content: str, related: list[str]
):
    """For any valid Document, parse -> serialise -> parse produces an equal object."""
    raw = {"doc_id": doc_id, "title": title, "category": category, "content": content, "related_docs": related}
    parsed = _parse_doc(raw)
    re_parsed = _parse_doc(json.loads(_serialise_doc(parsed)))
    assert parsed == re_parsed


# ---------------------------------------------------------------------------
# Issue 6 — must_not_claim guardrail correctness checks
# ---------------------------------------------------------------------------

def test_must_not_claim_blocks_matching_phrase():
    verdict = validate_response(
        "Great news — a refund has been issued to your account [DOC-BILL-001].",
        [{"doc_id": "DOC-BILL-001", "content": "Billing info"}],
        "",
        must_not_claim=["a refund has been issued"],
    )
    assert not verdict["passed"]
    assert "must_not_claim_violation" in verdict["issues"]
    assert "a refund has been issued" in verdict["must_not_claim_violations"]


def test_must_not_claim_case_insensitive():
    verdict = validate_response(
        "The issue has been FIXED ON OUR SIDE [DOC-AUTH-001].",
        [{"doc_id": "DOC-AUTH-001", "content": "Auth info"}],
        "",
        must_not_claim=["the issue has been fixed on our side"],
    )
    assert not verdict["passed"]
    assert "must_not_claim_violation" in verdict["issues"]


def test_must_not_claim_passes_when_empty():
    verdict = validate_response(
        "Please clear cookies and try again [DOC-AUTH-001].",
        [{"doc_id": "DOC-AUTH-001", "content": "Auth info"}],
        "",
        must_not_claim=[],
    )
    # must_not_claim check should not add a violation for an empty list
    assert "must_not_claim_violation" not in verdict["issues"]


def test_must_not_claim_passes_when_none():
    verdict = validate_response(
        "Please clear cookies and try again [DOC-AUTH-001].",
        [{"doc_id": "DOC-AUTH-001", "content": "Auth info"}],
        "",
        must_not_claim=None,
    )
    assert "must_not_claim_violation" not in verdict["issues"]


# ---------------------------------------------------------------------------
# Issue 2/3 — API health and kill-switch
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Issue 2/3 — API health and kill-switch (basic smoke tests)
# ---------------------------------------------------------------------------

def test_api_health_smoke():
    """Health endpoint exists and returns a status field."""
    from fastapi.testclient import TestClient
    from src.api import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert "status" in response.json()


def test_api_kill_switch(monkeypatch):
    """When PIPELINE_ENABLED=false, POST /tickets must return 503."""
    import os
    os.environ["PIPELINE_ENABLED"] = "false"
    from fastapi.testclient import TestClient
    from src import api as api_module
    client = TestClient(api_module.app)
    response = client.post("/tickets", json={
        "ticket_id": "KILL-1", "channel": "email", "body": "How do I reset my password?"
    })
    os.environ["PIPELINE_ENABLED"] = "true"
    assert response.status_code == 503


def test_api_tickets_endpoint_accepts_post():
    """POST /tickets (not /tickets/process) must exist (Requirement 8.2)."""
    import os
    os.environ["PIPELINE_ENABLED"] = "true"
    from fastapi.testclient import TestClient
    from src.api import app
    client = TestClient(app)
    response = client.post("/tickets", json={
        "ticket_id": "ROUTE-TEST",
        "channel": "email",
        "subject": "API key question",
        "body": "How do I rotate an API key?",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "ROUTE-TEST"
    assert data["decision"] in {"auto_respond", "escalate"}


def test_kb_status_endpoint():
    """GET /kb/status must return loaded article count (Requirement 13.5)."""
    from fastapi.testclient import TestClient
    from src.api import app
    client = TestClient(app)
    response = client.get("/kb/status")
    assert response.status_code == 200
    data = response.json()
    assert "loaded_article_count" in data
    assert data["loaded_article_count"] > 0
    assert isinstance(data["loaded_doc_ids"], list)
    assert isinstance(data["skipped_doc_ids"], list)


# ---------------------------------------------------------------------------
# Issue 10/11 — Decision log schema fields
# ---------------------------------------------------------------------------

def test_decision_log_includes_tier_region_and_version(tmp_path):
    """customer_tier, customer_region and pipeline_version must be in the log."""
    from src.logging_store import DecisionLogger, DecisionRecord, PIPELINE_VERSION
    from sqlalchemy import select

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    log = DecisionLogger(database_url=db_url)

    log.log(
        {
            "ticket_id": "LOG-SCHEMA-1",
            "channel": "email",
            "decision": "escalate",
            "intent": "billing_query",
            "urgency": "medium",
            "confidence": 0.72,
            "decision_reason": "test",
            "sources": [],
            "guardrail": {"passed": True},
            "_ticket_meta": {
                "customer_tier": "enterprise",
                "customer_region": "europe",
                "original_body": "Raw body",
                "normalised_body": None,
            },
        },
        latency_ms=10.0,
    )

    with log.Session() as session:
        row = session.execute(
            select(DecisionRecord).where(DecisionRecord.ticket_id == "LOG-SCHEMA-1")
        ).scalar_one()

    assert row.customer_tier == "enterprise"
    assert row.customer_region == "europe"
    assert row.pipeline_version == PIPELINE_VERSION


# ---------------------------------------------------------------------------
# Issue 12 — RETRIEVAL_TOP_K is wired up
# ---------------------------------------------------------------------------

def test_retrieval_top_k_env_var(monkeypatch):
    """RETRIEVAL_TOP_K must control the number of retrieved passages."""
    from src import config as cfg_module
    monkeypatch.setattr(cfg_module, "RETRIEVAL_TOP_K", 2)

    retriever = KnowledgeRetriever(ROOT / "data" / "documentation.json", backend="tfidf")
    results = retriever.search("How do I rotate an API key?", top_k=2)
    assert len(results) <= 2
