# Product requirements document — v1.0

**Product:** CloudServe AI Support Pipeline  
**Status:** Initial implementation baseline; revise after validation.  
**Owner:** Individual capstone engineer  
**Traceability:** See `requirements_traceability.md`.

## Problem statement

CloudServe's support function receives more than 500 tickets per week, takes 8–12 hours to reply against a 2-hour SLA, resolves fewer than half without handoff, and has a CSAT score of 3.2/5. A chatbot alone does not address the root causes. The system must route eligible documented questions to safe, grounded answers and escalate cases where policy, evidence, or uncertainty requires a human.

## Users

- Customers seeking troubleshooting and product guidance.
- Support agents receiving escalations with summaries and evidence.
- Support managers reviewing routing quality, workload, latency and guardrail activity.
- Governance reviewers auditing decisions and data handling.

## Functional requirements

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---|---|
| FR-01 | Normalize tickets from email, chat, docs comments and forum into one schema while preserving original text/channel. | Must | A2 and unit tests |
| FR-02 | Assign intent, urgency, numeric confidence and alternatives for every ticket. | Must | A3 and metrics report |
| FR-03 | Retrieve ranked, relevant passages from the supplied 29-article corpus with resolvable IDs. | Must | A4 and retrieval tests |
| FR-04 | Apply deterministic routing rules and a validation-derived confidence threshold. | Must | A5 and threshold evaluation |
| FR-05 | Generate concise answers grounded in retrieved evidence and cite actual source IDs. | Must | A6 and manual citation review |
| FR-06 | Block unsafe responses when guardrails detect a violation. | Must | A7 and guardrail tests |
| FR-07 | Escalate with reason, summary and available sources. | Must | Output inspection and routing tests |
| FR-08 | Persist every decision with route, confidence, reason, source IDs, guardrails, prompt version and latency. | Must | A8 reconciliation |
| FR-09 | Process arbitrary input paths in one unattended CLI run and write one result per ticket. | Must | A1/A9 clean-checkout test |
| FR-10 | Produce metrics automatically after a run. | Must | A10 and metrics file |
| FR-11 | Degrade gracefully on malformed input, no retrieval hit, provider timeout, rate limiting or outage. | Must | A11 fault-injection tests |
| FR-12 | Provide a test suite and automated CI. | Must | A12 and GitHub Actions |
| FR-13 | Expose a FastAPI service and Prometheus metrics. | Should | API smoke test and `/metrics` |
| FR-14 | Support persistent ChromaDB + sentence-transformer retrieval as an optional backend. | Should | Optional integration test |

## Non-functional requirements

- **Reliability:** no ticket silently dropped; per-ticket failure becomes an escalation result.
- **Auditability:** every decision logged and count reconciles with output ticket count.
- **Safety:** no outbound private-data detections; unsupported evidence must not be represented as fact.
- **Latency:** report mean, median and p95; target p95 <3 seconds is a goal to measure, not yet a proven result.
- **Portability:** Python 3.11, pinned dependencies, clean-checkout instructions.
- **Cost:** free-tier or offline-first execution; no paid provider required for the gate.
- **Privacy:** do not commit API keys; minimize customer data in operational logs.

## Out of scope

- Sending real emails or changing customer accounts.
- Performing refunds, deleting data, rotating production keys or making compliance commitments.
- Claiming a ticket is resolved without outcome evidence.
- A production multi-tenant deployment without authentication and security hardening.

## Initial success measures

Use the supplied Evaluation Framework targets as goals: first-contact resolution ≥60%, reply time under five minutes, CSAT review proxy ≥4/5, escalation ≤30%, classification precision ≥85%, hallucination ≤5%, citation accuracy ≥95%, p95 latency <3 seconds, zero outbound private-data detections, and <5 percentage-point variation across groups. These are targets, not claims of achievement. Use the supplied 80-ticket validation set for tuning and preserve the hidden set for final assessment.

## Assumptions and risks

- Development labels are usable training targets; inspect label quality and leakage risk.
- The local documentation is authoritative and current enough for the capstone; document stale articles as a risk.
- The hidden evaluator may have no network access; offline fallback is therefore required.
- Confidence estimates need calibration; threshold choice must be based on held-out validation results.
