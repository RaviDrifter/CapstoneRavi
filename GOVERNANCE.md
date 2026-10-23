# Governance, Risk, Fairness and Incident Response

> Full detail is in [`docs/governance.md`](docs/governance.md). This root-level file satisfies the project submission requirement (Requirement 12.4) that `GOVERNANCE.md` be present at the repository root.

## Principles

1. Safety overrides automation rate. Uncertain or policy-sensitive cases go to a human.
2. Decisions must be explainable to support staff in plain language and reproducible from logged fields.
3. Customer text and retrieved documents are untrusted input, not system instructions.
4. Hosted-model use is opt-in; customer data sent to a provider must be reviewed against contractual and privacy requirements.
5. The team must distinguish automated proxies from observed business outcomes.

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Residual Owner |
|---|------|------------|--------|------------|----------------|
| 1 | Hallucinated product/policy claim | Medium | High | Retrieval gate, source IDs, grounded prompt, fallback, `must_not_claim` guardrail, manual sample review | Engineer + support reviewer |
| 2 | Unsafe autonomous response to compliance/security request | Medium | Critical | Mandatory escalation list, explicit override tests, compliance intent rule | Classifier may misclassify; add rules + red-team cases; support lead |
| 3 | Prompt injection inside ticket | Medium | High | Treat ticket as JSON data, injection pattern detector, hard escalation block | Pattern checks cannot catch every phrasing; security reviewer |
| 4 | Private data in generated output | Medium | High | Outbound PII scan, no cross-customer lookup, minimal logs | Regex is incomplete; privacy reviewer |
| 5 | Provider outage or rate limit | High on free tier | Medium | Timeouts, no unbounded retry, offline evidence-template fallback, escalation | Fallback less helpful than expert response; engineer |
| 6 | Retrieval returns irrelevant passage | Medium | High | Relevance threshold gate, no-hit escalation, expected-doc recall evaluation | Lexical matching may miss paraphrases; retrieval owner |
| 7 | Confidence miscalibration | Medium | High | Retrieval-score–derived confidence, validation-set threshold analysis | Small dataset, class imbalance; evaluation owner |
| 8 | Unequal performance by channel/region/fluency | Medium | High | Group breakdowns in metrics report, sample review, no demographic routing shortcuts | Small subgroup counts make estimates noisy; fairness reviewer |
| 9 | Incomplete decision log | Low/Medium | High | One row per ticket, SQLAlchemy commit, count reconciliation in metrics | Disk/permission failures surfaced in output; operations owner |
| 10 | Secret accidentally committed | Low | Critical | `.env` in `.gitignore`, placeholder-only template, CI credential scan | CI regex is not a full secret scanner; repository owner |

---

## Kill-Switch

Set `PIPELINE_ENABLED=false` in the environment to disable all autonomous responses immediately.
The `POST /tickets` endpoint will return HTTP 503 and log every rejected request at WARNING level.
Escalation intake (human review queue) is not affected.

To re-enable: set `PIPELINE_ENABLED=true` (or remove the variable) and restart the service.

---

## Fairness Audit Protocol

1. Run the fixed validation set and save a dated results artifact.
2. Report auto-response and routing accuracy by channel, customer region, tier and language-fluency field.
3. Include sample sizes; avoid interpreting small groups as stable estimates.
4. Compare quality outcomes, not just automation rates. Manually review a sample from each group.
5. Investigate variation ≥ 5 percentage points.
6. Do not infer protected attributes not present in data or use region/fluency as a shortcut for lower-quality service.
7. Record mitigations, residual risk and the next review date.

---

## Incident Response Procedure

**Trigger examples:** confirmed unsupported claim, private data leak, unsafe auto-answer, widespread retrieval error, model-provider failure, or loss of audit logs.

1. **Contain** — set `PIPELINE_ENABLED=false` immediately; preserve escalation intake.
2. **Record** — log incident time, affected ticket IDs, output and decision-log records, model/prompt version and corpus version. Do not copy secrets into incident notes.
3. **Triage** — notify project owner/support lead; involve security/privacy owner for data exposure.
4. **Scope** — query `storage/decisions.db` and output artifacts by `ticket_id`.
5. **Remediate** — correct the rule, corpus, prompt or dependency; add a regression test that reproduces the incident.
6. **Verify** — re-run the full validation suite and manually review impacted cases before re-enabling automation.
7. **Document** — record root cause, customer impact, remediation, residual risk and follow-up owner in `docs/prd_revision_log.md`.

---

## Governance Gates Before Production

- Human review of ≥ 50 generated responses by two assessors with agreement reported.
- Evidence-based citation accuracy review and unsupported-claim rate estimate.
- Confidence calibration and threshold decision documented.
- Privacy/legal approval for provider use and log retention.
- Authentication, TLS, rate limits, role-based access, backups and alerting implemented.
- Security red-team test for prompt injection, secrets and cross-customer data disclosure.
