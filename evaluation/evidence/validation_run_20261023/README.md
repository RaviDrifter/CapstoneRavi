# Validation run evidence — 2026-10-23

This evidence folder contains the output of an offline run against the supplied 80-ticket validation dataset. It is not the hidden 120-ticket evaluation and must not be presented as that result.

Command used:

```bash
python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results/validation_results.json
python -m scripts.analyze_thresholds --input data/validation_tickets.json --output evaluation/results/threshold_sweep.json
```

Summary from `metrics.json`:

- Processed: 80; output rows: 80; decisions logged: 80; log failures: 0.
- Automated responses: 32 (40.0%); escalations: 48 (60.0%).
- Final-decision auto precision: 84.38%; recall: 56.25%; accuracy: 67.50%.
- Route-classifier accuracy before final policy gates: 78.75%.
- Answerability classification accuracy: 76.25%.
- Retrieval hit rate: 94.34% over 53 tickets with expected document IDs.
- Local/offline processing latency: mean 11.19 ms, median 10.72 ms, p95 13.25 ms for this run.
- Historical labels in the supplied validation records: FCR 46.25%; mean resolution time 441.48 minutes; median 218 minutes; average CSAT 2.60/5. These are not outcomes caused by the pipeline.

Limitations: no live OpenRouter call was made in this run; offline response templates were used. Guardrail tests demonstrate blocking behavior separately; the validation set itself had zero blocked responses. Claim-level hallucination and citation accuracy have not been established because the required two-reviewer human audit is outstanding. Results may vary slightly in latency and should be regenerated after code/config changes.
