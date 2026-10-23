# Build-spec acceptance criteria traceability

This table maps the twelve supplied build-gate criteria to implementation and local verification. A local test run is evidence for the tested condition only; it is not a claim that a human assessor has accepted the submission.

| Criterion | Implementation | Verification |
|---|---|---|
| A1 — clean checkout | `README.md`, pinned `requirements.txt`, `.env.example`, package-local paths | Fresh-copy run of setup, test and validation commands before packaging |
| A2 — four channels | `src/ingest.py` | `test_normalizes_all_four_channels` |
| A3 — intent, urgency, confidence, alternatives | `src/classify.py`; output assembled in `src/pipeline.py` | Pipeline contract tests and validation metrics |
| A4 — ranked, identifiable retrieval | `src/retrieve.py`; stable `doc_id` and `passage_id`; passage text and score in output | `test_retrieval_returns_real_document_ids`, `test_output_sources_include_verifiable_passage_text` |
| A5 — deterministic routing threshold | `src/pipeline.py`, `.env.example`, `docs/threshold_analysis.md` | `test_pipeline_output_contract_and_deterministic_routing` and threshold sweep |
| A6 — citations | `src/generate.py`, `src/guardrails.py`; response citations use retrieved document IDs | Guardrail and output source tests; claim-level correctness still requires human review |
| A7 — guardrail can block | `src/guardrails.py`; prompt injection and outbound private-data checks | `test_prompt_injection_guardrail_blocks`, `test_generated_response_with_private_data_is_blocked` |
| A8 — persistent decision log | `src/logging_store.py`, SQLite database configured by `DATABASE_URL` | Metrics reconcile result rows with successful log writes; batch test asserts log count |
| A9 — unattended full-set run | `src/cli.py`, `evaluation/harness.py` | Validation run processes all 80 tickets without interactive prompts; hidden 120-ticket run must be done by assessor |
| A10 — automatic metrics | `src/metrics.py` | CLI creates `metrics.json`; validation artifact is included in `evaluation/results/` |
| A11 — graceful failure | per-ticket exception fallback in `src/pipeline.py`; provider fallback in `src/generate.py`; malformed-record handling in `src/cli.py` | `test_openrouter_outage_falls_back_to_evidence_template`, `test_non_object_ticket_is_retained_in_batch` |
| A12 — tests | `tests/`, pytest configuration in `pyproject.toml` | `python -m pytest tests/ -v` |

## Known gaps that must remain visible

- The validation set is not the hidden test set. The hidden 120-ticket evaluation remains unrun and unseen.
- The local run uses the offline evidence template unless `USE_LLM=true` and a valid key are configured.
- Citation integrity does not establish that each factual claim is entailed by the cited passage.
- The project is a capstone baseline, not a production-ready service. Production authentication, TLS, access control, data retention, and provider privacy review remain necessary.
