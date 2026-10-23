from __future__ import annotations
from typing import Any

VALID_CHANNELS = {"email", "chat", "docs_comment", "forum"}


def normalize_ticket(raw: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """Normalize all channels to one schema without discarding the original text."""
    if not isinstance(raw, dict):
        raise ValueError("ticket must be a JSON object")
    ticket_id = str(raw.get("ticket_id") or f"UNKNOWN-{index + 1}").strip()
    channel = str(raw.get("channel") or "unknown").strip().lower()
    subject = str(raw.get("subject") or "").strip()
    body = raw.get("body", raw.get("message", raw.get("description", "")))
    if body is None:
        body = ""
    if not isinstance(body, str):
        body = str(body)
    body = body.strip()
    combined = "\n".join(part for part in (subject, body) if part).strip()
    return {
        "ticket_id": ticket_id,
        "channel": channel,
        "subject": subject,
        "body": body,
        "text": combined,
        "received_at": raw.get("received_at"),
        "customer_id": raw.get("customer_id"),
        "customer_tier": raw.get("customer_tier", "unknown"),
        "customer_region": raw.get("customer_region", "unknown"),
        "language_fluency": raw.get("language_fluency", "unknown"),
        "original": raw,
        "input_warning": "empty_body" if not combined else None,
    }
