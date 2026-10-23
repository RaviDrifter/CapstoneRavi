from __future__ import annotations
import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .pipeline import SupportPipeline
from .retrieve import get_retriever

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CloudServe AI Support",
    version="1.0.0",
    description="Evidence-grounded customer support triage and response API",
)

PIPELINE = SupportPipeline()
TICKETS = Counter(
    "cloudserve_tickets_processed_total",
    "Tickets processed",
    ["channel", "outcome"],
)
GUARDRAILS = Counter(
    "cloudserve_guardrail_activations_total",
    "Guardrail activations",
    ["guardrail"],
)
LATENCY = Histogram(
    "cloudserve_ticket_processing_seconds",
    "End-to-end ticket processing latency",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 20),
)


def _pipeline_enabled() -> bool:
    """Kill-switch: return False when PIPELINE_ENABLED env var is set to 'false'."""
    return os.getenv("PIPELINE_ENABLED", "true").strip().lower() not in {"false", "0", "no"}


@app.get("/health")
def health():
    """Return 200 ok when operational; 503 degraded when dependencies are unavailable."""
    issues: dict[str, str] = {}

    # Check retrieval (ChromaDB or TF-IDF corpus)
    try:
        retriever = get_retriever()
        if not retriever.passages:
            issues["retrieval"] = "retrieval_unavailable"
    except Exception:
        issues["retrieval"] = "retrieval_unavailable"

    # Check LLM reachability only when LLM mode is enabled.
    from .config import USE_LLM, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
    if USE_LLM and OPENROUTER_API_KEY:
        import requests as _requests
        try:
            # Lightweight HEAD/GET to the base URL — not a full inference call.
            resp = _requests.get(
                OPENROUTER_BASE_URL.rsplit("/chat/completions", 1)[0],
                timeout=3,
            )
            if resp.status_code >= 500:
                issues["llm"] = "llm_unavailable"
        except Exception:
            issues["llm"] = "llm_unavailable"

    if issues:
        from fastapi.responses import JSONResponse
        reasons = list(issues.values())
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "reason": reasons[0], "details": issues},
        )
    return {"status": "ok", "service": "cloudserve-ai-support", "version": "1.0.0"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/kb/status")
def kb_status():
    """Return count of loaded KB articles and any skipped article IDs (Requirement 13.5)."""
    retriever = get_retriever()
    loaded_doc_ids = list({p["doc_id"] for p in retriever.passages})
    all_doc_ids = [d.get("doc_id") for d in retriever.documents]
    skipped = [doc_id for doc_id in all_doc_ids if doc_id not in loaded_doc_ids]
    return {
        "loaded_article_count": len(loaded_doc_ids),
        "loaded_doc_ids": sorted(loaded_doc_ids),
        "skipped_doc_ids": skipped,
    }


@app.post("/tickets")
def process_ticket(ticket: dict, request: Request):
    """Process a single ticket (Requirement 8.2). Respects PIPELINE_ENABLED kill-switch."""
    # Kill-switch check (Requirement 12.5)
    if not _pipeline_enabled():
        logger.warning(
            "POST /tickets rejected: PIPELINE_ENABLED=false. Remote: %s",
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=503,
            detail="Pipeline is currently disabled. Please contact support.",
        )

    if not isinstance(ticket, dict):
        raise HTTPException(status_code=422, detail="Request body must be a JSON object")

    with LATENCY.time():
        result = PIPELINE.process(ticket)

    TICKETS.labels(
        channel=result.get("channel", "unknown"),
        outcome=result.get("decision", "escalate"),
    ).inc()
    for guardrail in result.get("guardrail", {}).get("issues", []):
        GUARDRAILS.labels(guardrail=guardrail).inc()
    return result


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.api:app", host="127.0.0.1", port=port, reload=False)
