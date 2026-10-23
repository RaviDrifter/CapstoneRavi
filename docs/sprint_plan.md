# Sprint plan — three-week capstone

## Backlog

| ID | Work item | Estimate | Dependency | Definition of done |
|---|---|---:|---|---|
| S1 | Inspect requirements, datasets and acceptance criteria | 4h | None | Schema notes and discovery findings committed |
| S2 | Normalize four ticket channels | 2h | S1 | Unit tests pass for all channels and empty fields |
| S3 | Fit local classifiers and alternatives | 4h | S2, development data | Intent/urgency/route predictions include numeric scores |
| S4 | Build documentation chunking and TF-IDF retrieval | 4h | Dataset schema | Real source IDs returned and no-hit path tested |
| S5 | Add optional Chroma + sentence-transformers | 4h | S4 | Backend can ingest corpus and return resolvable passages |
| S6 | Add route policy and mandatory escalation | 3h | S3/S4 | Same input yields same route; rules tested |
| S7 | Response generation and source citations | 4h | S4/S6 | Offline fallback works; optional provider errors degrade safely |
| S8 | Guardrails and escalation summary | 4h | S7 | Prompt injection and outbound PII checks can block |
| S9 | CLI/harness and metrics report | 4h | S2–S8 | Full validation set runs unattended and writes output/metrics |
| S10 | SQLite audit logging | 2h | S9 | Decision count reconciles with output count |
| S11 | Evaluation and threshold tuning | 5h | S9 | Per-class, retrieval, calibration and fairness report generated |
| S12 | FastAPI + Prometheus | 3h | Pipeline | Health, process, and metrics endpoints work |
| S13 | Tests, CI, clean checkout rehearsal | 4h | S1–S12 | CI passes and README reproduced in fresh directory |
| S14 | Governance and final reporting | 5h | Evaluation | Risk register, human review and honest report completed |

Estimates are planning placeholders, not claimed actual effort. Record actual time in `docs/effort_log_template.csv` throughout the project.

## Day-by-day checkpoints

- **Week 1:** discovery, schema review, first PRD, baseline CLI, initial retrieval.
- **Week 2, day 1:** all four channels normalize; day 2 retrieval IDs resolve; day 3 classify/route/log; day 4 guardrail blocks; day 5 full validation run; remaining week: error analysis and PRD revision.
- **Week 3:** governance, fairness audit, monitoring, CI, clean checkout, human review, report/video/submission packaging.

## Scope cut order if behind

1. Keep the unattended CLI, output contract, safe escalation, logging and metrics.
2. Keep the retrieval baseline and test coverage.
3. Defer optional Chroma integration before cutting the full batch run.
4. Defer Grafana dashboard polish before removing Prometheus metrics.
5. Never disable guardrails to improve automation rate.

## Definition of done for the sprint

- One documented command processes all supplied validation tickets unattended.
- No ticket is silently dropped; output count equals input count.
- Decisions logged equal decisions returned.
- Every automatic response has retrieved source IDs and passes guardrails.
- Provider outage and malformed records do not crash the run.
- Tests pass from a clean checkout.
