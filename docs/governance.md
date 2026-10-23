# Governance, risk, fairness and incident response

## Principles

1. Safety overrides automation rate. Uncertain or policy-sensitive cases go to a human.
2. Decisions must be explainable to support staff in plain language and reproducible from logged fields.
3. Customer text and retrieved documents are untrusted input, not system instructions.
4. Hosted-model use is opt-in; customer data sent to a provider must be reviewed against contractual and privacy requirements.
5. The team must distinguish automated proxies from observed business outcomes.

## Initial risk register

| Risk | Likelihood | Impact | Controls | Residual risk / owner |
|---|---|---|---|---|
| Hallucinated product/policy claim | Medium | High | Retrieval gate, source IDs, grounded prompt, fallback, manual sample review | Semantic entailment is not fully automated; engineer + support reviewer |
| Unsafe autonomous response to compliance/security/privacy request | Medium | Critical | Mandatory escalation list and explicit override tests | Classifier may misclassify; add rules and red-team cases; support lead |
| Prompt injection inside ticket | Medium | High | Treat ticket as JSON data, injection pattern detector, escalation block | Pattern checks cannot catch every phrasing; security reviewer |
| Private data in generated output | Medium | High | Outbound PII scan, no customer-to-customer lookup, minimal logs | Regex is incomplete; privacy reviewer |
| Provider outage/rate limit | High on free tier | Medium | Timeouts, no repeated unbounded retry, offline response fallback, escalation | Fallback less helpful than expert response; engineer |
| Retrieval returns irrelevant passage | Medium | High | Relevance threshold, no-hit escalation, expected-doc evaluation | Lexical matching may miss paraphrases; retrieval owner |
| Confidence miscalibration | Medium | High | Validation-set calibration table and threshold selection | Small dataset, class imbalance; evaluation owner |
| Unequal performance by channel/region/fluency | Medium | High | Report group breakdowns, review samples, avoid using demographic-like attributes for routing | Small subgroup counts make estimates noisy; fairness reviewer |
| Incomplete decision log | Low/Medium | High | One result per input, SQLAlchemy logging, count reconciliation | Disk/permission failures surfaced in output; operations owner |
| Secret accidentally committed | Low | Critical | `.env` ignored, placeholder-only template, CI credential scan | CI regex is not a full secret scanner; repository owner |
| Stale knowledge-base content | Medium | High | Preserve source metadata and review age; route unsupported questions | Corpus owners must maintain content; documentation owner |

## Data minimization and retention

- The local SQLite decision log stores ticket ID, channel, predicted category/urgency, confidence, decision reason, source IDs, guardrail results, prompt version and latency. It does not intentionally store the full customer message or response body.
- Response JSON contains the customer-facing answer or escalation summary and source excerpts because that is needed for the capstone output and review. Treat it as sensitive and do not commit generated runs containing real data.
- Keep `.env`, API keys and secrets out of version control.
- Before using OpenRouter with real tickets, confirm company policy permits the transfer and review provider data handling, retention, region and contractual terms.
- Set a retention period and deletion procedure before production deployment; this capstone leaves storage local for assessment.

## Fairness audit protocol

1. Run the same fixed validation set and save a dated results artifact.
2. Report auto-response and routing accuracy by channel, customer region, tier and language-fluency field where present.
3. Include sample sizes and avoid interpreting tiny groups as stable estimates.
4. Compare quality outcomes, not just automation rates. Manually review a sample of escalations and answers from each sufficiently sized group.
5. Investigate variation ≥5 percentage points; do not force equal automation rates if risk and answerability differ.
6. Do not infer protected attributes that are not present or use region/language fluency as a shortcut for lower-quality service.
7. Record mitigations, residual risk and the next review date.

The current metrics report provides region and channel automation breakdowns as a screening measure. A complete fairness audit needs manually reviewed answer quality and confidence intervals; the current data alone cannot establish equal customer outcomes.

## Incident response

**Trigger examples:** confirmed unsupported claim, private data leak, unsafe auto-answer, widespread retrieval error, model-provider failure causing bad outputs, or loss of audit logs.

1. Disable autonomous response by setting the routing threshold high or disabling the service; preserve escalation intake.
2. Record incident time, affected ticket IDs, output and decision-log records, model/prompt version and corpus version. Do not copy secrets into incident notes.
3. Triage severity and notify the project owner/support lead; involve security/privacy owner for data exposure.
4. Identify scope by querying the SQLite decision log and output artifacts.
5. Correct the rule, corpus, prompt or dependency; add a regression test that reproduces the incident.
6. Re-run the full validation suite and manually review impacted cases before re-enabling automation.
7. Document root cause, customer impact, remediation, residual risk and follow-up owner.

## Governance gates before production

- Human review of at least 50 generated responses by two assessors, with agreement reported.
- Evidence-based citation accuracy review and unsupported-claim rate estimate.
- Confidence calibration and threshold decision documented.
- Privacy/legal approval for provider use and log retention.
- Authentication, TLS, rate limits, role-based access, backups and alerting implemented.
- Security red-team test for prompt injection, secrets and cross-customer data disclosure.
