"""Deterministic policy overrides for high-risk or evidence-insufficient ticket patterns."""
from __future__ import annotations
import re


_REVIEW_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "billing_dispute_requires_authorized_review",
        re.compile(
            r"\b(disput(e|ing)|unauthori[sz]ed charge|incorrect charge|charged twice|"
            r"do not recognize (the )?charge|don't recognize (the )?charge|"
            r"charges? (that )?i (do not|don't) believe we use|"
            r"(do not|don't) believe we use)\b",
            re.I,
        ),
    ),
    (
        "active_customer_impact_requires_incident_review",
        re.compile(
            r"\b(production outage|production incident|service is down|broke(n)? checkout|"
            r"took down part of|cannot ship|can't ship|customers? (are|cannot|can't) (blocked|unable|affected))\b",
            re.I,
        ),
    ),
    (
        "unresolved_after_documented_steps",
        re.compile(r"\b(exactly as (the )?(documentation|docs|guide)|followed the (documentation|docs|guide))\b", re.I),
    ),
    (
        "data_integrity_issue_requires_engineer_review",
        re.compile(r"\b(pagination|paginated)\b.*\b(duplicate|duplicated|missing|skip|inconsistent)\b|\b(duplicate|duplicated|missing)\b.*\b(records?|results?)\b", re.I),
    ),
    (
        "complex_sso_failure_requires_review",
        re.compile(r"\b(sso|single sign-on|saml)\b.*\b(group|department|team)\b.*\b(error|fail|denied|does not work|doesn't work)\b", re.I),
    ),
]


def human_review_override(text: str, intent: str) -> str | None:
    """Return a human-readable reason when a deterministic policy requires review."""
    if intent == "data_residency":
        return "Data-location and residency statements require authorized human review."
    content = text or ""
    for reason, pattern in _REVIEW_PATTERNS:
        if pattern.search(content):
            return reason.replace("_", " ").capitalize() + "."
    # A documented troubleshooting step that has already been tried and still fails is not
    # automatically answered by repeating the same step.
    lower = content.lower()
    if any(term in lower for term in ("already tried", "still fails", "still failing", "still doesn't work", "still does not work")) and any(term in lower for term in ("docs", "documentation", "guide", "steps")):
        return "The customer reports that documented troubleshooting has not resolved the issue."
    return None
