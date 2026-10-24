# PRD revision log — implementation-driven update

**Revision:** v1.0 → v1.1  
**Evidence date:** 2026-10-23  
**Status:** Implemented in the current project baseline; human response review remains outstanding.

| Requirement / assumption | Initial version | Evidence from implementation or validation | Revision | Status |
|---|---|---|---|---|
| FR-03 retrieval | Use the RAG corpus and return source IDs | TF-IDF retrieval hit 50/53 labelled answerable validation tickets (94.34%), but a top-ranked passage is not proof the ticket is answerable | Keep a deterministic offline retriever and expose actual passage text/IDs; add a separate answerability classifier and keep Chroma embeddings optional | Implemented; semantic comparison remains future work |
| FR-04 routing | Use a fixed 0.80 route-confidence threshold | Initial 0.80 setting using classifier probabilities produced only 7/80 auto-responses; revised to retrieval-derived confidence with 0.10 threshold and 0.40 answerability gate | Confidence is now derived from max retrieval similarity score (Requirement 6.2); thresholds are 0.10/0.40, configurable via env vars; validation run produced 35/80 auto-responses (43.75%) with 80% precision | Implemented; final-decision precision is 80.00% on the supplied validation set |
| FR-05 response | A cited document may be sufficient to release a draft | Source-ID integrity cannot prove claim-level entailment; templates can also be incomplete or too verbose | Preserve passage text in output for review, block invalid citations/PII, and require a two-reviewer claim-level audit before making hallucination claims | Partly implemented; human audit pending |
| FR-07 escalation | Escalate uncertain tickets | Tier Two interview says escalations commonly lack summary/context | Include summary, reason and retrieved source references in escalation output | Implemented |
| FR-09 reliability | External model provider expected to be available | Free-tier throttling and outages are explicit risks; the acceptance gate may run offline | Keep provider optional, apply timeouts and fall back to evidence-only templates; test provider timeout and malformed records | Implemented and covered by fault-injection tests |
| Outcome reporting | Auto-response rate approximates FCR | Auto-response does not prove a ticket was resolved; supplied historical FCR/CSAT are not pipeline outcomes | Report automation proxy separately from historical FCR, resolution-time and CSAT values | Implemented in metrics |

## What was learned

The most important change was to separate route confidence from documentation answerability and to derive confidence from retrieval similarity rather than classifier probabilities. A ticket can look like a known intent while still asking a question the 29-article corpus does not answer. The confidence score now reflects how well the retrieved documentation matches the ticket (max TF-IDF cosine similarity), which is a more direct signal of answerability. The extra answerability gate reduces unsafe automation, although its validation accuracy (76.25%) shows it needs more representative labels and better semantic evidence.

The selected thresholds are not claimed to meet every business target. The chosen 0.10/0.40 setting automates 43.75% of validation tickets with 80% precision for the auto-response decision. This is an explicit safety/coverage trade-off, not a hidden success claim.

## Outstanding work

- Complete a human review of at least 50 generated responses with two independent reviewers and report agreement.
- Validate calibration on a larger representative dataset.
- Review category-level escalation policies with a support/compliance owner.
- Run the assessor's hidden 120-ticket evaluation once, without tuning on its contents.
- Complete actual effort logs and personal submission materials; no hours or reviewer outcomes are fabricated in this repository.
