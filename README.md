# CloudServe Solutions — AI Support System

A reproducible support-ticket pipeline for classification, evidence retrieval, safe response drafting, escalation, audit logging, and evaluation. It is designed around the capstone's twelve acceptance criteria and the unattended hidden-set gate.

> **Safety and evaluation note:** An auto-response is not proof that a ticket was actually resolved. The pipeline reports an automation/FCR proxy separately from labelled historical outcomes. Do not describe simulated outcomes as measured customer impact.

## What is included

- Normalisation for `email`, `chat`, `docs_comment`, and `forum` tickets.
- Supervised TF-IDF/logistic-regression classifiers with sigmoid probability calibration, trained only from the supplied 500 development tickets. They return intent, urgency, route and documentation-answerability estimates plus alternatives.
- Mandatory escalation overrides for compliance requests, security incidents, feature requests, unclear requests, data-residency requests, billing disputes, active customer-impact incidents, prompt-injection patterns, low confidence, and insufficient evidence.
- Retrieval over the supplied 29-article corpus with stable document and passage IDs. TF-IDF is the deterministic offline default; ChromaDB + `all-MiniLM-L6-v2` is an optional backend.
- Evidence-based response templates that work without an API key. Optional OpenRouter generation is enabled with `USE_LLM=true` and an API key.
- Response guardrails for outbound PII-like strings, citation integrity, missing evidence, and prompt-injection attempts.
- SQLite decision logging, a FastAPI endpoint, Prometheus metrics, tests, CI, and an unattended evaluation harness.

## Requirements

- Python 3.11 recommended (3.10–3.12 supported).
- Git.
- The ZIP includes the source datasets and the original capstone reference pack.
- The offline evaluation path does not require a model API key or a model download.

## Setup from a clean checkout

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest tests/ -v
```

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python -m pytest tests/ -v
```

No key is required for the offline fallback. Never commit `.env` or a real API key.

### Optional integrations

To enable the LangGraph orchestration and ChromaDB + Sentence Transformers backend, install:

```bash
python -m pip install -r requirements-ai.txt
```

Then set `RETRIEVAL_BACKEND=chroma` in `.env`. On first use, `sentence-transformers` may need to download `all-MiniLM-L6-v2`; run ingestion/test queries while internet is available. If the optional stack fails to initialize, retrieval safely falls back to TF-IDF. LangGraph is used automatically when installed; otherwise the same pipeline nodes run through a local deterministic runner.

To enable OpenRouter generation, set `USE_LLM=true`, add a valid `OPENROUTER_API_KEY`, and confirm that `MODEL_NAME` is currently available on your OpenRouter account. Free-tier availability and rate limits can change. Provider errors fall back to a documentation-based response template rather than terminating the batch.

## Run the pipeline

The required CLI takes input and output paths and never prompts for interactive input:

```bash
python -m src.cli --input_path data/validation_tickets.json --output_path evaluation/results/validation_results.json
```

Equivalent shorter flags are supported:

```bash
python -m src.cli --input data/validation_tickets.json --output evaluation/results/validation_results.json
```

The output file contains one result per input ticket, including passage text and IDs so citations can be checked. A `metrics.json` report is automatically written beside it. It includes classification, routing, answerability, calibration, retrieval, latency, historical baseline, logging and group-breakdown metrics when the relevant labels are present. Every ticket decision is written to `storage/decisions.db` by default. Paths can be changed through environment variables.

The grading-style harness also accepts an output directory:

```bash
python -m evaluation.harness --input data/validation_tickets.json --output evaluation/results/
```

It writes `evaluation/results/results.json` and `evaluation/results/metrics.json`. For the hidden test set, pass the evaluator's path as the input; do not hardcode or copy a hidden filename into the repository.

### Output schema (summary)

Each result includes `ticket_id`, `channel`, `decision` (`auto_respond` or `escalate`), `intent`, `intent_confidence`, `urgency`, `confidence`, alternative predictions, a readable decision reason, response or escalation summary, retrieved source IDs/passages, guardrail findings, generation mode, and latency.

An escalated ticket has `response: null` and a human-readable `escalation_summary`. Its retrieved sources are retained when available.

## Run the API

```bash
python -m src.api
```

- `GET /health`
- `GET /metrics`
- `POST /tickets/process` with a ticket JSON object

By default, the API listens on `http://127.0.0.1:8000`. Do not expose it publicly without authentication, TLS, request limits, and production security review.

## Tests

```bash
python -m pytest tests/ -v
```

The tests cover channel normalisation, retrieval source integrity, prompt-injection blocking, PII scanning, deterministic routing, output files, provider/retrieval failure fallbacks, policy overrides, and metrics generation. CI runs the same suite on Python 3.11.

## Monitoring

The API exposes Prometheus metrics at `/metrics`. `monitoring/prometheus.yml` and `monitoring/docker-compose.yml` provide a local Prometheus/Grafana starting point. For local Docker monitoring, verify the target address for your OS; `host.docker.internal` may require adjustment on Linux. A dashboard should include ticket volume by channel/outcome, automation vs escalation, latency percentiles, guardrail activations, and confidence distribution.

## Architecture

See [`docs/architecture.md`](docs/architecture.md), [`docs/requirements_traceability.md`](docs/requirements_traceability.md), [`docs/acceptance_criteria.md`](docs/acceptance_criteria.md), [`docs/threshold_analysis.md`](docs/threshold_analysis.md), and [`docs/governance.md`](docs/governance.md). The original supplied instructions and workbooks are retained under `reference_pack/`.

## Threshold analysis

Reproduce the validation-only threshold sweep with:

```bash
python -m scripts.analyze_thresholds --input data/validation_tickets.json --output evaluation/results/threshold_sweep.json
```

The script uses development-trained models and validation labels only. See `docs/threshold_analysis.md` for the selected trade-off and caveats. Never tune on the hidden evaluation set.

## Evaluation discipline

- `development_tickets.json` is used to fit local classifiers.
- `validation_tickets.json` is used for threshold and error analysis.
- `ground_truth_responses.json` is for response rubric development and human review; it is not blindly copied into responses.
- Do not tune against the hidden evaluation set. Record run date, system version, exact command, input size, and any provider outage.
- The metrics report explicitly distinguishes label-based metrics from proxies. Automated checks cannot establish a human-judged hallucination rate; review a sample independently and record reviewer agreement.

## Known limitations / before production

1. The default TF-IDF retriever is a deterministic lexical baseline, not semantic retrieval. ChromaDB with `all-MiniLM-L6-v2` is an optional backend; compare it on a labelled retrieval set before claiming a semantic improvement.
2. Logistic-regression probabilities are estimates rather than guarantees. The routing and answerability thresholds are configurable and were selected using a validation-set trade-off; see `docs/threshold_analysis.md`. Recalibrate on larger, representative production data before launch.
3. PII patterns are not a complete privacy detector. They can miss variants and flag legitimate strings. Add structured redaction and human review before production.
4. Citation integrity confirms that citations refer to retrieved documents; it does not prove that each claim is entailed by that passage. Human audit is required for the capstone's hallucination and citation-accuracy measures.
5. The local response template is a safe fallback, not equivalent to an expert-authored response. Review outputs for completeness and tone.
6. A production deployment requires authentication, access controls, retention policies, secrets management, backups, rate limits, and incident response.

## Project artefacts

- `docs/discovery_findings.md` — observed dataset evidence and open discovery questions.
- `docs/product_requirements.md` — initial PRD.
- `docs/prd_revision_log.md` — implementation-driven requirements revision with measured validation evidence.
- `docs/sprint_plan.md` — backlog and definitions of done.
- `docs/evaluation_plan.md` — metric definitions and human review protocol.
- `docs/threshold_analysis.md` — measured threshold trade-offs and limitations.
- `docs/demo_script.md` — live demonstration rehearsal outline.
- `docs/clean_checkout_checklist.md` — reproducibility checklist.
- `docs/workbooks/` — completed draft workbooks for discovery, PRD, prompt library, sprint plan and PRD revision. Review and personalize them before submission.
- `docs/final_report_outline.md` and `docs/ai_tool_use_declaration.md` — report outline and AI-use declaration draft; student must finalize these.
- `docs/governance.md` — risks, controls, fairness and incident response.
- `docs/effort_log_template.csv` — record actual effort throughout the project; do not fabricate hours.

This ZIP is a working baseline, not a claim that the 85% precision, ≤5% hallucination, ≥95% citation accuracy, <3-second p95, or fairness targets have already been achieved. Run the evaluation and report measured results honestly.
