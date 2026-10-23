from __future__ import annotations
import re
from typing import Any

# PII checks are intentionally conservative and should be supplemented by review before production use.
PII_PATTERNS = {
    "email_address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone_number": re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)"),
    "api_secret_like": re.compile(r"\b(?:sk|rk|pk|api)[-_][A-Za-z0-9_-]{18,}\b", re.I),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
}
INJECTION_PATTERNS = [
    re.compile(r"ignore (?:all )?(?:previous|prior|above) instructions", re.I),
    re.compile(r"reveal (?:the )?(?:system prompt|secret|api key)", re.I),
    re.compile(r"act as (?:the )?system", re.I),
]


def scan_private_data(text: str) -> list[str]:
    return [name for name, pattern in PII_PATTERNS.items() if pattern.search(text or "")]


def detect_prompt_injection(text: str) -> bool:
    return any(p.search(text or "") for p in INJECTION_PATTERNS)


def check_must_not_claim(response: str, must_not_claim: list[str]) -> list[str]:
    """Return every phrase from must_not_claim that appears in response (case-insensitive)."""
    if not must_not_claim:
        return []
    response_lower = (response or "").lower()
    return [phrase for phrase in must_not_claim if phrase.lower() in response_lower]


def validate_response(
    response: str,
    retrieved: list[dict[str, Any]],
    ticket_text: str = "",
    must_not_claim: list[str] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    violated_phrases: list[str] = []

    private_types = scan_private_data(response)
    if private_types:
        issues.append("outbound_private_data_detected")

    if not retrieved:
        issues.append("no_retrieved_evidence")

    allowed_ids = {p.get("doc_id") for p in retrieved}
    cited_ids = set(re.findall(r"\[(DOC-[A-Z0-9-]+)\]", response or ""))
    if cited_ids and not cited_ids.issubset(allowed_ids):
        issues.append("citation_not_in_retrieved_sources")
    if retrieved and not cited_ids:
        issues.append("missing_citation")

    if detect_prompt_injection(ticket_text):
        issues.append("prompt_injection_attempt")

    # Must-not-claim check (Requirement 5): case-insensitive substring match.
    if must_not_claim:
        violated_phrases = check_must_not_claim(response, must_not_claim)
        if violated_phrases:
            issues.append("must_not_claim_violation")

    return {
        "passed": not issues,
        "issues": issues,
        "private_data_types": private_types,
        "must_not_claim_violations": violated_phrases,
        "checks": [
            "outbound_pii_scan",
            "retrieval_presence",
            "citation_integrity",
            "prompt_injection_scan",
            "must_not_claim_scan",
        ],
    }
