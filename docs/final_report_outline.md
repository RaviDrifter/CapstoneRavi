# Final capstone report — working outline

The submission guide requires a 20–30 page PDF, excluding appendices. This file is an outline, not a finished report. Fill it with your own analysis, review evidence, figures and final limitations before submission.

1. **Executive summary** — problem, system built, measured outcomes, most important caveat.
2. **Problem and context** — SLA, first-contact resolution, CSAT, volume and cost of escalation.
3. **Discovery findings** — five stakeholder transcripts, dataset profile, root-cause interpretation.
4. **Requirements and traceability** — FR/NFR priorities and the twelve acceptance criteria.
5. **Architecture and alternatives** — TF-IDF vs embeddings, local classifiers vs LLM classification, offline fallback vs provider dependence, SQLite vs larger database.
6. **Implementation** — ingestion, calibration, routing, retrieval, generation, guardrails, audit log, CLI and API.
7. **Evaluation method and results** — held-out validation metrics, threshold sweep, retrieval hit rate, confidence calibration, latency and business metrics.
8. **Human response audit** — at least 50 responses, two reviewers, unsupported-claim definition, agreement statistic, disagreements and caveats.
9. **Governance and risk** — risk register, data minimization, fairness by channel/region/tier/fluency, incident response.
10. **Requirements revision** — use `docs/prd_revision_log.md`; explain what changed and why.
11. **Conclusion and next steps** — unmet targets, uncertainty, production prerequisites.
12. **Appendices** — full metric tables, sample outputs, test results, prompt register, workbooks and effort log.

## Evidence rules

- Every performance claim must state the dataset, sample size, metric and how it was calculated.
- Do not call automation rate first-contact resolution. Do not claim a reduction in real customer response time from offline processing latency.
- Do not report a hallucination rate or citation accuracy target as achieved until the required human audit is completed.
- State whether OpenRouter was enabled and whether the run used the evidence-template fallback.
- Record the hidden-set run only when authorized by the assessor. Do not tune after viewing hidden labels.
- Include the required declaration of AI-tool use and ensure it accurately reflects how the work was produced.
