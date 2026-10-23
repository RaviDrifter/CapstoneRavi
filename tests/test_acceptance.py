import json
from pathlib import Path

import pytest

from src.cli import run
from src.generate import ResponseGenerator
from src.guardrails import validate_response
from src.pipeline import SupportPipeline
from src.routing import human_review_override

ROOT = Path(__file__).resolve().parents[1]


def test_non_object_ticket_is_retained_in_batch(tmp_path):
    input_path = tmp_path / "mixed.json"
    output_path = tmp_path / "results.json"
    input_path.write_text(json.dumps([
        {"ticket_id": "GOOD", "channel": "email", "subject": "How do I rotate an API key?", "body": "Please help."},
        None,
        "not a ticket object",
    ]), encoding="utf-8")

    metrics = run(input_path, output_path)
    results = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(results) == 3
    assert [row["ticket_id"] for row in results] == ["GOOD", "INVALID-2", "INVALID-3"]
    assert all(row["decision"] in {"auto_respond", "escalate"} for row in results)
    assert metrics["tickets_processed"] == 3
    assert metrics["decisions_logged"] == 3


def test_output_sources_include_verifiable_passage_text():
    pipeline = SupportPipeline(enable_langgraph=False)
    result = pipeline.process({
        "ticket_id": "DOC-CITE-1",
        "channel": "chat",
        "subject": "API rate limits",
        "body": "How do API rate limits and quotas work?",
    })
    for source in result["sources"]:
        assert source["doc_id"].startswith("DOC-")
        assert "::chunk-" in source["passage_id"]
        assert source["passage_text"].strip()
        assert isinstance(source["score"], float)


def test_generated_response_with_private_data_is_blocked():
    verdict = validate_response(
        "Please contact another customer at other.person@example.com [DOC-AUTH-001]",
        [{"doc_id": "DOC-AUTH-001", "content": "Public troubleshooting text"}],
        "How can I log in?",
    )
    assert not verdict["passed"]
    assert "outbound_private_data_detected" in verdict["issues"]


def test_openrouter_outage_falls_back_to_evidence_template(monkeypatch):
    import src.generate as generation

    monkeypatch.setattr(generation, "USE_LLM", True)
    monkeypatch.setattr(generation, "OPENROUTER_API_KEY", "test-placeholder")
    monkeypatch.setattr(ResponseGenerator, "_langchain_available", staticmethod(lambda: False))

    def raise_timeout(*args, **kwargs):
        raise TimeoutError("simulated provider outage")

    monkeypatch.setattr(generation.requests, "post", raise_timeout)
    generator = ResponseGenerator()
    response, mode = generator.generate(
        {"text": "How do I rotate an API key?"},
        {"intent": "api_key_issue"},
        [{
            "doc_id": "DOC-AUTH-004",
            "passage_id": "DOC-AUTH-004::chunk-000",
            "title": "API key rotation",
            "content": "Rotate an API key from the security settings and revoke the exposed key.",
            "score": 0.4,
        }],
    )
    assert mode == "evidence_template"
    assert "DOC-AUTH-004" in response
    assert "Rotate an API key" in response


def test_metrics_distinguish_historical_resolution_from_pipeline_latency(tmp_path):
    input_path = tmp_path / "history.json"
    output_path = tmp_path / "results.json"
    input_path.write_text(json.dumps([{
        "ticket_id": "HISTORY-1",
        "channel": "email",
        "body": "Please explain your compliance certification.",
        "labels": {"intent": "compliance_request", "expected_route": "escalate", "answerable_from_docs": False},
        "history": {"first_contact_resolution": False, "resolution_time_minutes": 120, "csat_rating": 3},
    }]), encoding="utf-8")
    metrics = run(input_path, output_path)
    assert metrics["historical_resolution_time_minutes"]["mean"] == 120
    assert metrics["historical_csat_average"] == 3
    assert metrics["final_decision_classification"]["accuracy"] is not None
    assert metrics["response_latency_ms"]["mean"] < 120 * 60 * 1000


def test_policy_overrides_escalate_data_residency_and_billing_disputes():
    assert human_review_override("We need our data to remain within the EU for a contract.", "data_residency")
    assert human_review_override("There are charges for a service I do not believe we use.", "billing_query")


def test_policy_override_escalates_active_customer_impact():
    reason = human_review_override(
        "A release has broken checkout for a portion of our customers.",
        "rollback_request",
    )
    assert reason is not None
    assert "customer impact" in reason.lower()


def test_retrieval_failure_becomes_escalation(monkeypatch):
    pipeline = SupportPipeline(enable_langgraph=False)

    def fail_retrieval(*args, **kwargs):
        raise TimeoutError("simulated retrieval failure")

    monkeypatch.setattr(pipeline.retriever, "search", fail_retrieval)
    result = pipeline.process({
        "ticket_id": "RETRIEVAL-FAIL",
        "channel": "email",
        "subject": "API question",
        "body": "How do I configure this API endpoint?",
    })
    assert result["decision"] == "escalate"
    assert result["response"] is None
    assert result["error_type"] == "TimeoutError"


def test_explicit_compliance_request_is_classified_and_escalated():
    pipeline = SupportPipeline(enable_langgraph=False)
    result = pipeline.process({
        "ticket_id": "COMPLIANCE-1",
        "channel": "email",
        "subject": "Compliance statement",
        "body": "Please provide an official compliance certification statement.",
    })
    assert result["intent"] == "compliance_request"
    assert result["decision"] == "escalate"
    assert result["response"] is None
