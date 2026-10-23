# Architecture and pipeline design

## Context

CloudServe receives tickets through email, live chat, documentation comments, and a community forum. The pipeline creates one normalized ticket representation and returns either an autonomous answer or an auditable escalation.

## Data flow

1. **Ingest** — accept JSON records, normalize field names, preserve original ticket content and channel, tolerate missing optional fields.
2. **Classify** — train intent, urgency, route, and documentation-answerability classifiers on the supplied labelled development data. Return top alternatives and numeric model scores.
3. **Safety policy** — mandatory escalation overrides, empty-ticket handling, route and answerability thresholds, and prompt-injection detection.
4. **Retrieve** — search passage chunks derived from `documentation.json`; every passage has a stable `doc_id` and `passage_id`. The offline default is TF-IDF; optional ChromaDB uses Sentence Transformers.
5. **Route** — auto-response only when the classifier predicts auto-response, the configured confidence threshold is met, no hard escalation rule fires, and relevant documentation is retrieved.
6. **Generate** — use OpenRouter when explicitly configured; otherwise use an evidence-derived response template. Provider errors degrade to offline mode.
7. **Validate** — scan outbound text for PII-like patterns, check that citation IDs belong to retrieved sources, require evidence, and block prompt injection.
8. **Finalize** — exactly one result per input ticket; escalation includes summary, reason and available sources.
9. **Audit** — persist every decision in SQLite; produce result JSON and a metrics report automatically.

## Routing policy

A response is eligible for automatic release only if all of the following hold:

- ticket contains usable text;
- predicted intent is not in the mandatory-escalation list;
- route classifier predicts `auto_respond`;
- route confidence meets `CONFIDENCE_THRESHOLD`;
- estimated documentation answerability meets `ANSWERABILITY_THRESHOLD`;
- at least one passage exceeds the retrieval relevance threshold;
- response validation passes.

The same input and same model artifacts/configuration produce the same routing decision. The OpenRouter generation itself can vary only if provider configuration changes; temperature is set to zero. In provider failure, deterministic fallback generation is used.

## Component choices and trade-offs

- **TF-IDF first:** offline, deterministic, fast, and requires no model download. It is a baseline; semantic embeddings should be compared empirically rather than assumed better.
- **Chroma optional:** supports persistent vector search with `all-MiniLM-L6-v2`; adds download, disk, memory, and dependency complexity.
- **Local classifier:** avoids per-ticket classification API calls and free-tier throttling. Probability calibration is not guaranteed and must be measured.
- **SQLite:** appropriate for this single-process capstone. Production concurrency and retention requirements may justify PostgreSQL.
- **FastAPI:** HTTP interface shares the same pipeline as the CLI.
- **LangGraph:** if installed, models the stages as a conditional graph. A deterministic local runner keeps the required offline gate operational if optional orchestration dependencies cannot be installed.

## Reliability

- Per-ticket exceptions become escalations rather than stopping the batch.
- The output JSON is written atomically.
- Provider timeout/outage falls back to a local response template.
- Retrieval failure or no match results in escalation.
- Logging failures are surfaced in the ticket result; the pipeline does not silently pretend a decision was logged.
- Evaluation reports processed count, decision count, latency, retrieval hit rate when labels exist, classification metrics when labels exist, and fairness breakdowns where sample sizes permit.

## Security boundary

Ticket text and retrieved documents are untrusted data. The system prompt explicitly forbids following instructions embedded in ticket content. API keys are read from environment variables. The local API is for development; production needs authentication, TLS, rate limits, access controls, retention rules and secret management.
