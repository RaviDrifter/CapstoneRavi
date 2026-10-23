# Requirements traceability matrix

| Requirement / criterion | Implementation | Verification |
|---|---|---|
| FR-01 / A2 | `src/ingest.py` | `test_normalizes_all_four_channels` |
| FR-02 / A3 | `src/classify.py`, result schema in `src/pipeline.py` | validation metrics: per-class precision/recall; output confidence range |
| FR-03 / A4 | `src/retrieve.py` | `test_retrieval_returns_real_document_ids` |
| FR-04 / A5 | `src/pipeline.py`, `CONFIDENCE_THRESHOLD`, `ANSWERABILITY_THRESHOLD` | `test_pipeline_output_contract_and_deterministic_routing` |
| FR-05 / A6 | `src/generate.py`, `src/guardrails.py` | inspect source IDs and manually audit claim-to-passage support |
| FR-06 / A7 | `src/guardrails.py`, pre-route block in `src/pipeline.py` | `test_prompt_injection_guardrail_blocks`, `test_pipeline_escalates_prompt_injection_and_logs` |
| FR-07 | `src/pipeline.py` escalation summary and sources | inspect escalated output results |
| FR-08 / A8 | `src/logging_store.py` | compare `metrics.json` decisions logged to output count; inspect SQLite table |
| FR-09 / A1/A9 | `src/cli.py`, `evaluation/harness.py` | run complete validation and hidden input path unattended |
| FR-10 / A10 | `src/metrics.py`, `src/cli.py` | assert `metrics.json` created automatically |
| FR-11 / A11 | per-ticket exception fallback in `src/pipeline.py`; provider fallback in `src/generate.py` | provider timeout and malformed-record fault-injection tests |
| FR-12 / A12 | `tests/`, `.github/workflows/ci.yml` | `python -m pytest tests/ -v` |
| FR-13 | `src/api.py`, `monitoring/` | `GET /health`, `GET /metrics`, POST smoke test |
| FR-14 | `src/retrieve.py` Chroma integration | install `requirements-ai.txt`, set `RETRIEVAL_BACKEND=chroma`, verify retrieved IDs |

## Evidence still required before final submission

- Clean checkout rehearsal on a separate directory or machine.
- Full unattended 80-ticket validation run with a dated metrics artifact.
- Fault injection for provider timeout/outage, malformed JSON, and retrieval failure.
- Manual review of at least 50 responses by two assessors, with agreement rate.
- Calibration table and confidence-threshold rationale.
- Fairness review with sample sizes and uncertainty reported.
