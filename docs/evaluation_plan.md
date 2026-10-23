# Evaluation plan

## Datasets and leakage controls

- **Development (500):** train local intent, urgency and route classifiers.
- **Validation (80):** tune confidence/retrieval thresholds, assess class-wise errors and calibration.
- **Ground truth (200):** develop response-quality rubric and map known examples to source docs.
- **Hidden set (120):** final assessment only. Do not tune prompts, rules or thresholds after inspecting hidden results.

## Automatically calculated metrics

`metrics.json` is produced next to the output on every CLI run and includes:

- volume: processed, auto-responded, escalated, guardrail-blocked;
- automation and escalation rate;
- mean, median and p95 processing latency;
- per-class intent and route precision/recall/F1 when labels are present;
- retrieval hit rate when expected document IDs are present;
- channel and region automation breakdowns;
- decision-log count and private-data detection count.

The script labels auto-response rate as an FCR proxy. It does not claim that the ticket was actually resolved. Historical FCR from source records is reported separately and must not be attributed to the pipeline.

## Metric definitions

- Precision per class = TP / (TP + FP).
- Recall per class = TP / (TP + FN).
- F1 = harmonic mean of precision and recall.
- Retrieval hit rate = fraction of labelled tickets for which at least one expected document ID appears among retrieved sources.
- Automation rate = auto-responded / processed.
- Escalation rate = escalated / processed.
- p95 latency = nearest-rank 95th percentile of per-ticket processing latency.
- Calibration error = absolute difference between average confidence and observed accuracy in each confidence band.

## Targets from supplied framework

| Metric | Target | Evidence needed |
|---|---:|---|
| First-contact resolution | ≥60% | Real outcome data; otherwise only report automation proxy |
| Mean first reply | <5 minutes | Production timestamps; offline processing latency is not customer reply time |
| CSAT proxy | ≥4.0/5 | Human review rubric and sample size |
| Escalation rate | ≤30% | Run metrics, balanced against safety |
| Classification precision | ≥85% | Per-class held-out report |
| Hallucination rate | ≤5% | Two human assessors on ≥50 responses |
| Citation accuracy | ≥95% | Claim-to-source review |
| p95 latency | <3 seconds | Report environment and provider configuration |
| Private data detections | 0 | Automated scan plus manual sample review |
| Cross-group variation | <5 percentage points | Quality outcomes by group, with sample sizes |

## Human review protocol

1. Draw a stratified sample of at least 50 auto-responses across intent and channel.
2. Two reviewers independently score factual support, citation correctness, completeness, safety/policy, and clarity using `prompts/evaluation/response_rubric_v1.txt`.
3. Mark any unsupported factual claim as a hallucination even if the rest of the response is correct.
4. Report reviewer agreement (percent agreement and Cohen's kappa where suitable), disagreement resolution and sample limitations.
5. Include escalated examples to check that safety overrides are not over- or under-triggering.

## Calibration and threshold selection

Use only the 80-ticket validation set to group predictions into confidence bands. Compare stated confidence to observed correctness, plot or tabulate the gap, and choose a threshold that balances unsafe automation against useful coverage. Keep a record of candidate thresholds and results. The default 0.80 is an initial conservative configuration, not a claim that the model is calibrated.

## Run protocol

```bash
python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results/validation_run_YYYYMMDD/
```

Record exact date, git commit, input hash, configuration, model/provider status, processed count, and whether any fallback was used. Confirm `tickets_processed == decisions_logged == number of result rows`. Test provider outage separately. Run hidden data only when authorized for the final evaluation and never use it to tune.
