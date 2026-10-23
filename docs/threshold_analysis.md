# Validation-set threshold analysis

**Status:** Initial measured analysis; rerun after material model, prompt, corpus, or routing changes.

## Method

The classifier is fitted only on `data/development_tickets.json` (500 labelled tickets). Threshold candidates are evaluated against the separate `data/validation_tickets.json` (80 tickets). The analysis script never reads hidden evaluation data:

```bash
python -m scripts.analyze_thresholds \
  --input data/validation_tickets.json \
  --output evaluation/results/threshold_sweep.json
```

For each candidate, the simulation applies the same mandatory escalation rules, routing-class confidence threshold, answerability threshold, and retrieval-presence check as the runtime pipeline. Precision is measured for the `auto_respond` decision against the validation labels. These labels are useful for selecting an operating point, but are not proof of production safety or human-reviewed factual correctness.

## Selected operating point

The checked-in `.env.example` uses:

- `CONFIDENCE_THRESHOLD=0.60`
- `ANSWERABILITY_THRESHOLD=0.60`

The classifiers now use sigmoid calibration fitted with cross-validation on development data only. On the 80-ticket validation set, this setting produced the following measured result:

| Measure | Result |
|---|---:|
| Tickets processed | 80 |
| Automated responses | 32 (40.0%) |
| Escalations | 48 (60.0%) |
| Automated-route precision | 84.38% |
| Automated-route recall | 56.25% |
| Overall final-decision accuracy | 67.50% |
| Route-classifier accuracy before final routing/answerability gates | 78.75% |
| Answerability model accuracy | 76.25% |
| Retrieval hit rate among 53 tickets with expected document IDs | 94.34% |

A stricter candidate (`route=0.70`, `answerability=0.60`) reached 84.62% automated-route precision, but only automated 26/80 tickets (32.5%) and recalled 45.83% of expected auto-response cases. The selected operating point trades a small amount of precision for more coverage. The selected setting still misses the aspirational escalation-rate target; safety and unsupported-answer avoidance take priority over forcing the automation rate upward.

## Other observed validation figures

The current local/offline run recorded a mean processing latency of 11.19 ms, median 10.72 ms and p95 13.25 ms. This is local pipeline execution time without a live hosted-model call, **not** customer first-reply time and not a prediction of hosted-model latency.

The supplied historical fields on these validation records report 46.25% first-contact resolution, 441.48 minutes mean resolution time, 218 minutes median resolution time, and 2.60/5 average CSAT. Those are historical dataset values, not outcomes caused by this system.

The intent classifier scored 100% accuracy on this validation sample. That unusually high score may reflect strong template or lexical similarity between the supplied synthetic splits. It must not be presented as evidence of equivalent real-world performance without a fresh, independently sampled dataset.

## Limitations and next actions

1. The answerability model remains imperfect (76.25% accuracy on this validation set); false positives can route an unanswerable ticket toward automation, and false negatives cause avoidable escalation.
2. TF-IDF similarity is lexical, not semantic entailment. A retrieved passage may be top-ranked without answering every question in the ticket.
3. Citation-ID validation confirms source identity, not claim-level entailment. A human review of at least 50 responses by two reviewers remains required by the evaluation framework.
4. The current confidence calibration report gives an expected calibration error for intent of 0.1541, route of 0.0560, and answerability of 0.0551 on this sample. Calibration estimates from 80 synthetic tickets are noisy; before production, evaluate calibration by class and confidence band on a larger, representative sample.
5. Re-run this analysis when the corpus, model, routing policy, or prompt changes. Do not tune on the hidden 120-ticket set.
