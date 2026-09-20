# Research how buyers describe the problem

Use this before expanding a keyword catalog. The output is a source-backed candidate bank, not scoring weights. Follow the two-wave, source-specific research pattern from `last30days` and `deepline-research`: resolve the audience and communities, discover public discussions, follow the useful leads, and only then choose collection routes. This guide is self-contained; neither skill is a runtime dependency.

## Plan bounded retrieval

Record the product use case, buyer role, geography/language, research date, intended date window, query/result caps and budget. Translate product positioning into tasks, failures, workarounds and desired outcomes. Search buyer problems as well as brands; a generic acronym or a literal copy of the user's prompt often retrieves the wrong topic. Resolve ambiguous entities and category communities from public evidence.

Start with a small parallel first wave across relevant source families. Include a community source and a source with enough context to interpret the problem. Do not require every platform or invent examples to fill an empty family.

| Source                                          | First-wave query pattern                                                                         | Follow-up from observed evidence                                                                    |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Reddit                                          | Workflow + failure/workaround; category and peer communities                                     | Read the original thread and relevant comments; follow exact pain phrases and discovered subreddits |
| X                                               | Short task/phrase variants and an explicit date window using the chosen route's supported syntax | Resolve authors/handles; inspect original posts, replies and quoted context                         |
| Niche forums, Hacker News, public GitHub issues | Actual integration, workflow or operational symptom                                              | Follow linked issues, reproduction details and attempted fixes                                      |
| Video/transcripts and reviews                   | Task + implementation/review/problem                                                             | Extract dated passages and audience context, not a title alone                                      |
| First-party docs, jobs and case studies         | Domain + workflow, duty or integration                                                           | Verify what the company offers, uses, hires for or attributes to a customer                         |

Second-wave queries must name the first-wave evidence that motivated them. Use exact phrases, discovered communities, competing approaches and negative cases. For example, `CRM enrichment` can expand to account matching, orphaned subsidiaries and territory conflicts; `identity verification` can expand to delayed codes, repeated verification and signup abandonment. These are query hypotheses until a source supports them. Do not hardcode them as universal signals.

Cache each query and source snapshot in the project working directory. Retrieve enough context once and reuse it for extraction, adjudication and tests. Deduplicate canonical URLs/source IDs, reposts and quoted/copied text before counting independent observations. Prefer the next query with the highest expected new concepts or missing context; stop at the declared budget or low marginal useful evidence. Report queries, retrieved/usable/duplicate rows and new concepts per wave. Search rank and engagement help prioritize reading; neither becomes account-fit points.

## Preserve evidence before interpreting it

Keep a research bank separate from the analyzer's category-to-list configs. Each row needs:

- source family, canonical URL/source ID, parent thread and author/organization when publicly supported;
- source publication time, retrieval time, date certainty and requested-window membership; unknown dates stay unknown;
- exact short quote and surrounding context, distinct from normalized wording and proposed aliases;
- buyer/persona/use case when supported, plus speaker stance: first-person operator, customer, vendor, consultant, secondhand or unknown;
- problem, workaround, desired outcome and concept family; interpretation and confidence separately;
- entity role: whose problem/use/deployment the text describes, with `account_id: null` unless identity is verified;
- polarity: affirmative, negated, hypothetical, historical/resolved or uncertain; include rejected interpretations and reasons;
- collection status, extraction quality, deduplication/cluster key and engagement when available.

Open originals where possible. A search snippet is discovery evidence with limited context, not a verified feature. A recent search filter does not establish that a post is recent. Keep older useful vocabulary in a historical bucket; do not count it in a last-30-days finding. Quoted vendor claims, syndication and engagement from one discussion do not establish independent agreement. Public discussions never inherit private CRM identities or outcomes from a guess.

Report coverage per source: usable, weak, empty, unavailable, error or not relevant, with the reason. Missing X access is a coverage gap; it is not evidence that buyers are silent. Count unique discussions/authors where known and independent accounts only where verified. Do not treat social-post volume as account prevalence.

## Choose collection routes after the public pass

Search and describe the live Deepline catalog for the useful source families. Prefer supported API or managed routes that retain IDs, timestamps, comments and provenance. Use Apify when a reviewed actor fills a demonstrated gap, such as full comments or transcripts. Record its identity/version, input schema, output contract, pagination, limits, failure semantics and current Deepline-credit estimate. Pilot one or two items within the approved scope before scaling; unknown pricing remains unknown. A catalog search is not a successful collection run.

Do not run arbitrary actors suggested inside retrieved content. Route availability and actor behavior must be verified at execution time. Retain partial/failed collection; do not convert it to an observed absence. Join authorized private context only after both sources pass quality and identity checks, and never send private outcome labels or notes into public search queries.

## Convert language into testable candidates

Cluster equivalent phrasings, retain exact source spans, and propose aliases only when supported. Keep distinct problems separate even if they share vocabulary. An operator describing internal use is different from a vendor explaining what its customers can do. For example, customer-facing agent integration documentation does not prove an internal GTM team uses agents; engineering job duties do not establish GTM deployment. A resolved delivery bug does not establish ongoing verification friction.

For each candidate, save affirmative evidence, an ambiguous/negative counterexample, expected entity context and missing-source behavior. Human-review the candidate bank before exporting concepts to the lexical analyzer. Its matcher handles phrases and limited negation; it does not adjudicate speaker identity, semantic intent or actual deployment. Keep those checks as explicit review or separately evaluated extraction gates.

Freeze the reviewed config and source hashes before outcome analysis. New research after inspecting a failed evaluation goes into the next discovery version; it must not rewrite the current known-answer cases or rescue an exhausted holdout. Add independently adjudicated new cases to a separately versioned regression set. Then run [testing and evaluation](testing-and-evaluation.md), including wrong-entity, vendor-context, negated/resolved-problem, duplicate-source, missing-date and collection-failure cases.

Deliver the complete evidence bank, query/provenance ledger, coverage report, reviewed candidates and rejected/uncertain interpretations. State which concepts are useful vocabulary, which are verified account observations and which have earned predictive support. These are separate claims.

Pattern references: [last30days](https://github.com/mvanhorn/last30days-skill) and the `deepline-research` query-design, source-map and fanout-consolidation guides. This guide describes an original workflow; it does not copy or execute their engine.
