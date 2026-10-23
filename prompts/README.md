# Prompt register

| ID | Version | Purpose | Runtime use |
|---|---|---|---|
| CS-RESP-001 | 1.0.0 | Grounded support response | OpenRouter generation when `USE_LLM=true`; offline fallback otherwise |
| CS-CLS-001 | 1.0.0 | Classification specification | Documents classifier contract; current implementation trains local TF-IDF/logistic models |
| CS-EVAL-001 | 1.0.0 | Human response review rubric | Manual evaluation protocol |

Prompt edits must increment the version and be accompanied by tests and an evaluation run.
