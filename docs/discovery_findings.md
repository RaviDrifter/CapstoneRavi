# Discovery findings — CloudServe Solutions

**Evidence sources:** supplied transcripts of five discovery conversations, the 500 labelled development tickets, 80 labelled validation tickets, 200 senior-agent reference responses, and the 29-article support knowledge base. CloudServe is fictional; the supplied interview transcripts are the project's primary discovery evidence.

## 1. Problem framing

CloudServe asked for a chatbot, but the evidence points to a support-throughput and knowledge-findability problem with a safety boundary. The system should answer repeatable, documented questions quickly and consistently, while giving humans better context on cases that remain uncertain or sensitive. Automation that increases wrong answers or creates unhelpful escalations would fail the actual business need.

## 2. Stakeholder evidence

| Stakeholder | Evidence from supplied transcript | Design implication |
|---|---|---|
| Marcus Adeyemi, Head of Support | More than 500 tickets/week, six agents, 8–12 hour first reply against a two-hour SLA, 42% FCR; wrong answers and loss of explainability are unacceptable | Measure automation and safety together; log every route and its rationale; do not claim auto-response equals resolution |
| Sofia Restrepo, Tier One Agent | Estimates around 70% of tickets are familiar repeat questions; searching and rewriting answers consume time; security tickets must be escalated; non-fluent English tickets can be misunderstood | Retrieve from approved documentation; preserve channel and original text; add uncertainty handling and human review |
| Daniel Okonkwo, Tier Two Engineer | About half of escalations may have been answerable by Tier One if the right page had been found; escalations lack summaries and prior context; warns against stale personal snippets | Include a concise escalation summary, relevant source passages and a plain-language reason; use the approved corpus rather than private snippets |
| Ines Varga, Technical Writer | 29 reviewed support articles exist; internal search uses exact terms and misses paraphrases; private agent snippets are not governed; feature/roadmap/novel incidents are not covered | Make article IDs and text traceable; evaluate retrieval separately; escalate unsupported requests; retain corpus review metadata |
| Ravi Menon, Customer | Waiting is most costly when a deployment is blocked; he accepts automated help if transparent and sourced; customers on different plans may expect different service | Prioritize safe answers to urgent documented blockers; disclose automation; audit outcomes by customer tier and avoid widening service gaps |

These interviews disagree in useful ways: the support lead sees aggregate SLA pressure, while the Tier Two engineer sees avoidable escalation content. Both are compatible with the data-backed hypothesis that finding and confidently applying known answers is a bottleneck.

## 3. Dataset inventory and observed labels

| Asset | Size | Use |
|---|---:|---|
| Development tickets | 500 | Fit intent, urgency, route and documentation-answerability classifiers |
| Validation tickets | 80 | Tune operating thresholds and measure held-out behavior |
| Senior-agent reference responses | 200 | Build the response rubric and support claim-level human review |
| Knowledge-base articles | 29 | Authoritative retrieval corpus for this capstone |

The supplied development labels contain 311 expected auto-responses (62.2%), 189 expected escalations (37.8%), and 87 tickets marked `must_not_auto_respond` (17.4%). The validation labels contain 48 expected auto-responses and 32 expected escalations. These are supplied labels, not independently verified production outcomes.

## 4. Findings that changed the design

1. **Search/findability is a first-class requirement.** Two support stakeholders and the technical writer describe a gap between customer phrasing and article wording. The system therefore returns ranked passages with stable IDs and keeps the passage text available for review.
2. **Safety overrides automation.** The support lead explicitly prefers silence to a confident wrong answer; the Tier Two engineer identifies security/account compromise, billing disputes and data location as high-risk. The pipeline has mandatory escalation categories, a documentation-answerability gate, a response validator and safe fallbacks.
3. **Escalations need context.** The Tier Two engineer reports that escalations often arrive without a summary or prior reasoning. The output includes a human-readable reason, summary and any retrieved sources.
4. **Novel or policy-sensitive questions must not be improvised.** Feature requests, roadmap/timing questions, compliance and novel incidents are escalated when policy or evidence does not support a safe answer.
5. **Automation must be transparent and measurable.** The customer wants to know when an answer is machine-drafted. Output metadata records generation mode, citations and decision reason; a production user interface should disclose the automated origin to customers.
6. **Historical outcomes must not be confused with system outcomes.** The supplied ticket history includes FCR, resolution time and CSAT. The pipeline reports these as historical baselines and reports its own automation rate separately.
7. **Fairness needs monitoring.** The agent reports worse satisfaction for tickets from customers who are less fluent in English; customer tier and region may also influence expectations. Metrics break down automation by region and channel, but quality fairness requires a human-reviewed sample and uncertainty reporting.

## 5. First validation findings

The first full offline validation run processed all 80 tickets and logged all 80 decisions. With routing confidence and answerability thresholds at 0.60, 32 tickets were answered automatically (40.0%) and 48 were escalated (60.0%). Automated-route precision was 84.38%, recall 56.25%, and final-decision accuracy 67.5%. The route classifier accuracy before final policy gates was 78.75%, and the answerability classifier accuracy was 76.25%. Retrieval hit rate was 94.34% across 53 tickets with expected document IDs.

The intent classifier's measured accuracy was 100% on this small supplied validation sample. Because the data appears strongly template/lexical structured, this score should be treated cautiously and not generalized to real-world support traffic. The answerability model scored 76.25%, exposing a remaining source of avoidable escalation and false automation. See `threshold_analysis.md` for the operating-point trade-off.

## 6. Open questions and assumptions

- Are customer-facing responses allowed to be sent automatically, or must an agent approve drafts during the pilot?
- Which exact categories are contractual mandatory-escalation categories, especially billing disputes and data residency?
- Does SLA measure first response, meaningful response, or resolution, and how are reopened tickets counted?
- What response-retention and ticket-log retention period is required?
- Is OpenRouter approved for customer data, and what redaction is required before transmission?
- How should enterprise-plan SLA differences be represented without unfairly deprioritizing other customers?
- The 29 supplied articles are treated as authoritative for this capstone, but article age and gaps need a knowledge-owner review before production.

## 7. Discovery conclusion

The system should be a safety-first support pipeline rather than an unrestricted chatbot: classify intent and urgency, estimate whether the corpus can answer, retrieve traceable passages, route deterministically, generate only from evidence, validate every draft, and provide human escalations with context. The first validation run demonstrates the end-to-end mechanics, but the current automation rate and answerability accuracy show that further evaluation and knowledge-base coverage work are needed before production.
