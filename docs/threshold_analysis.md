# Validation-set threshold analysis

**Status:** Updated 2026-10-24 to reflect revised confidence thresholds (0.10/0.40). Rerun after material model, prompt, corpus, or routing changes.

## Method

The classifier is fitted only on `data/development_tickets.json` (500 labelled tickets). Threshold candidates are evaluated against the separate `data/validation_tickets.json` (80 tickets). The analysis script never reads hidden evaluation data:

```bash
python -m scripts.analyze_thresholds \
  --input data/validation_tickets.json \
  --output evaluation/results/threshold_sweep.json
```

For each candidate, the simulation applies the same mandatory escalation rules, routing-class confidence threshold, answerability threshold, and retrieval-presence check as the runtime pipeline. Precision is measured for the `auto_respond` decision against the validation labels. These labels are useful for selecting an operating point, but are not proof of production safety or human-reviewed factual correctness.

## Confidence score derivation

The pipeline derives its confidence score from the **maximum retrieval similarity score** across retrieved passages (TF-IDF cosine similarity in the offline default). This is distinct from the classifier's `route_confidence` (logistic regression probability) and the `answerable_probability` (answerability model output). All three gates must pass for a ticket to be auto-responded:

1. Route classifier predicts `auto_respond` with confidence ≥ `CONFIDENCE_THRESHOLD`
2. Answerability model estimates documentation coverage ≥ `ANSWERABILITY_THRESHOLD`
3. At least one retrieved passage has similarity ≥ `CONFIDENCE_THRESHOLD`
4. No mandatory escalation override applies

## Selected operating point

The checked-in `.env.example` uses:

- `CONFIDENCE_THRESHOLD=0.10`
- `ANSWERABILITY_THRESHOLD=0.40`

These values were selected because TF-IDF cosine similarity scores for well-matched tickets typically peak at 0.20–0.25, while poorly matched tickets score below 0.05. A threshold of 0.10 separates relevant from irrelevant retrievals without being so strict that nothing passes. The answerability threshold of 0.40 admits tickets where the model is at least moderately confident the documentation covers the question.

On the 80-ticket validation set, this setting produced the following measured result:

| Measure | Result |
|---|---:|
| Tickets processed | 80 |
| Automated responses | 35 (43.75%) |
| Escalations | 45 (56.25%) |
| Automated-route precision | 80.00% |
| Automated-route recall | 58.33% |
| Overall final-decision accuracy | 66.25% |
| Route-classifier accuracy before final routing/answerability gates | 78.75% |
| Answerability model accuracy | 76.25% |
| Retrieval hit rate among 53 tickets with expected document IDs | 94.34% |
| Guardrail blocks | 0 |
| Private data detections | 0 |
| Decision log failures | 0 |

The previous operating point (0.60/0.60) used classifier probabilities rather than retrieval-derived confidence. It produced 32 auto-responses (40%) with 84.38% precision. The revised operating point trades a small amount of precision for broader coverage while maintaining the same safety gates.

## Other observed validation figures

The current local/offline run recorded a mean processing latency of 15.91 ms, median 15.38 ms and p95 20.51 ms. This is local pipeline execution time without a live hosted-model call, **not** customer first-reply time and not a prediction of hosted-model latency.

The supplied historical fields on these validation records report 46.25% first-contact resolution, 441.48 minutes mean resolution time, 218 minutes median resolution time, and 2.60/5 average CSAT. Those are historical dataset values, not outcomes caused by this system.

The intent classifier scored 100% accuracy on this validation sample. That unusually high score may reflect strong template or lexical similarity between the supplied synthetic splits. It must not be presented as evidence of equivalent real-world performance without a fresh, independently sampled dataset.

### Regional automation breakdown

| Region | Total | Auto-responded | Automation rate |
|---|---:|---:|---:|
| Asia Pacific | 21 | 12 | 57.14% |
| North America | 27 | 13 | 48.15% |
| Europe | 25 | 8 | 32.00% |
| Latin America | 7 | 2 | 28.57% |

The 28.57 percentage-point spread between the highest and lowest regions warrants investigation. However, sample sizes per group are small (7–27), so these figures should be treated as screening indicators rather than stable estimates.

## Limitations and next actions

1. The answerability model remains imperfect (76.25% accuracy on this validation set); false positives can route an unanswerable ticket toward automation, and false negatives cause avoidable escalation.
2. TF-IDF similarity is lexical, not semantic entailment. A retrieved passage may be top-ranked without answering every question in the ticket.
3. Citation-ID validation confirms source identity, not claim-level entailment. A human review of at least 50 responses by two reviewers remains required by the evaluation framework.
4. The confidence calibration report gives an expected calibration error for intent of 0.1541, route of 0.5976, and answerability of 0.0551 on this sample. The route calibration error is high because the retrieval-derived confidence operates on a different scale than the classifier probabilities. Calibration estimates from 80 synthetic tickets are noisy; before production, evaluate calibration by class and confidence band on a larger, representative sample.
5. The regional automation variation (28.57% spread) needs investigation with quality outcomes, not just automation rates.
6. Re-run this analysis when the corpus, model, routing policy, or prompt changes. Do not tune on the hidden 120-ticket set.
