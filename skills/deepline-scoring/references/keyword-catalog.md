# Broad phrase and concept discovery

Do not reuse one customer's vocabulary or score weights as universal truth.

Before generating aliases, read [buyer-language research](buyer-language-research.md). Use bounded, source-specific public searches and a second wave driven by observed phrases, communities and handles. Preserve exact buyer wording, source context, dates, rejected interpretations and missing coverage in a separate research bank. Social language proposes concepts; account identity and predictive value require separate evidence.

## Coverage matrix

For each target, explore these families independently:

1. Jobs to be done and workflow steps.
2. Failure modes, rework, delays, queues, handoffs.
3. User roles, manager roles, implementation and economic buyers.
4. Duties and systems mentioned in job descriptions (separate from job titles).
5. Quantities: team size, calls/day, processing time, locations, transaction volume.
6. Existing providers, integrations, internal tools, substitutes.
7. Buying/change events: expansion, migration, hiring, consolidation.
8. Capacity and deployment constraints, compliance, safety, language.
9. Buyer wording, abbreviations, regional synonyms.
10. Negative statements, counterexamples, resolved problems, vendor self-descriptions.

Use careers/ATS, workflow/help pages, case studies, customer interviews, integrations, reviews, news and structured fields. Record source availability; never force every family to produce a signal.

## Generate many candidates without fishing for wins

Mine the discovery corpus before viewing outcome labels. Default 500 candidates; use a second min-one-account pass for rare phrases. Count distinct accounts, not repeated mentions or syndicated pages. The local miner reports total inventory and truncation, with source/length diversity. It is an English-oriented lexical proposal generator, not a semantic classifier. Long documents still yield more proposals; audit candidates by source and company size. Expand multilingual retrieval separately when required.

For a substantial corpus, aim to EXPLORE roughly 10–20 concepts per relevant family and 3–8 source-backed phrasings per concept. These are planning ranges, not quotas or promises of predictive results. Do not invent aliases to hit a count. Export the complete candidate bank, including rejected/uncertain candidates and rejection reasons.

Schema: category -> strings or concepts:

```json
{
  "workload": [
    {
      "name": "inbound booking workload",
      "aliases": ["inbound calls", "appointment requests", "booking enquiries"]
    },
    {
      "name": "integration duties",
      "aliases": ["integration", "integrations", "integrat*"]
    }
  ]
}
```

Bare strings match whole terms/phrases. Only an explicit trailing \* broadens a final token. Short/ambiguous words need explicit aliases and context review. Short tokens do not match arbitrary substrings inside longer words. Casing is ignored. Whitespace/hyphen variants match; periods do not join phrases across sentences.

For tool names, add official alternate names and actual deployment evidence; mentions remain mentions. For roles, add equivalent titles (not every word in a title). Roles match advertised titles only. CSR open requisitions, observed profiles and verified employees are three different measures.

## Adversarial expansion prompt

"Using only the discovery source documents, propose candidate phrases for each relevant family. Do not inspect won/lost labels. For every alias, return an exact source span, URL, account, source type and date; identify positive, negative, hypothetical and vendor contexts. Include phrases a seed list would miss. Keep minority and zero-prevalence-in-one-source terms. Return candidates, rejected interpretations, and unfilled source families. Do not produce scores or predictive claims."

Human-review the expansion and freeze the exact config plus hashes. Aliases form an OR within a concept and count each account once. Keep concept families distinct; do not sum correlated aliases as independent points. Outcome-driven refinement is allowed only within discovery and must be recorded as exploration, never reused to claim untouched validation.

## Queries

Run separate bounded query families rather than one giant query:

- site:{domain} + a workflow phrase;
- site:{domain} + duties/roles;
- exact company name + careers/ATS;
- exact company name + operating quantities;
- exact company name + change events;
- known location/place identity + specific review failures.

Describe the selected provider's query syntax and limits. Query/result caps are retrieval limits, not absence evidence. Record pagination and marginal new accounts/phrases; stop when budget or reviewed marginal value is exhausted, not when ten examples have been found.
