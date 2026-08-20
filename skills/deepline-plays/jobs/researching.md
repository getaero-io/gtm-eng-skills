# Researching companies and markets

Use the research kernel for known entities, account briefs, current signals,
buyer language, customer examples, market maps, and claims needing evidence.
This page is complete for that job.

## 0. Compile a source plan when the ask starts as "what sources?"

When the request names source families rather than a route, compile before
binding tools. `plays/shared/source-plan.ts` turns objective, query type, source
families, and extraction keys into stages; it does not claim a source exists.
Search and describe the live catalog for every leg, then mark it native, generic
route, private connector, or gap.

```typescript
import { compileSourcePlan } from './shared/source-plan';

const plan = compileSourcePlan({
  objective: 'Build a target-account dataset from public records.',
  queryType: 'gtm_dataset',
  sourceFamilies: ['web', 'reddit', 'x', 'github'],
  extractionKeys: ['domains', 'dataset_or_api_names', 'company_names'],
});
```

A private-only plan has no public discovery stage to mint an identity, so supply
one stable input (`initialInputs: ['domain_or_account_key']`) instead of scanning
a CRM broadly.

| Compiled stage          | Author in the Play                                                             |
| ----------------------- | ------------------------------------------------------------------------------ |
| `public-fanout`         | parallel search/fetch routes with source URLs and source status                |
| `artifact-resolution`   | canonical dataset/API URL, schema, parser, stable join key                     |
| `identity-resolution`   | company/person/account identity gates before any private lookup                |
| `private-join`          | authorized CRM, warehouse, workflow, or support lookup with private provenance |
| `supplemental-gap-fill` | independent route for still-missing extraction keys only                       |
| `terminal-extraction`   | one output row preserving every requested key and its evidence                 |

Gates: a provider name never replaces a source family; no broad CRM/warehouse
query before identity resolution; a chosen route may not drop extraction keys
(preserve nulls and an explicit miss status); and an unconfirmed source is
generic, private, or gap — never "native".

Offline regression for the compiler itself:

```bash
bun .skills/deepline-plays/scripts/evaluate-source-plan-corpus.ts \
  --corpus .skills/deepline-pre-research/evals/last30days-public-private-corpus.json \
  --pre-research-planner .skills/deepline-pre-research/scripts/query_design.py
```

That checks planning only. Tool availability, adapters, coverage, and credit
economics still need a live run.

## 1. Freeze the claim matrix

Write one required-claim row for every denominator row before retrieval. Record:

- stable row key and supplied identity hints;
- claim key and evidence standard;
- recency window and fixed reference date;
- honest `insufficient_evidence` state;
- later private dataset, join key, outcome field, and decision validated.

Useful defaults for known-company work:

- canonical domain: an official-site page whose entity/product match is clear;
- product: one explicit authoritative product page, or two independent weaker
  sources that state the same thing;
- primary buyer: one official segment/customer/solution page that names the
  buyer, or two independent sources. Do not infer a buyer from product category
  alone;
- recent signal: an attributable date inside the requested window.

Treat a supplied domain as a hint. If exact-name/domain retrieval is sparse,
recover the canonical site using the name and another verified identifier.
Never silently substitute a same-named company.

For a canonical-domain claim, use the scaffold's
`evidenceHostMatchesDomain(value, evidence)` validator. The cited evidence URL
must be on the claimed domain or its subdomain. A recovered `instnt.ai` value,
for example, cannot cite a fetched `instnt.org` page.
Normalize provider-returned URLs to a bare lowercase hostname with
`normalizeDomainClaim` before creating the fact assertion. Pair the host gate
with `isLikelyOfficialDomainCandidate(item, row.company_name)` so a
self-consistent directory, social profile, or wrong-company host cannot pass.
Use `selectOfficialDomainCandidate(row.ranked_items, row.company_name)` before
the supplemental fetch. It accepts conservative name-matching official hosts
and rejects common third-party hosts such as LinkedIn and Wikipedia. For a
brand whose official domain genuinely does not match its company name, supply
an explicit `allowedDomains` exception only after separate verification.

If hints may be stale, keep the scaffold's
`requiredEvidencePhase: 'supplemental'` policy for `canonical_domain`. Broad
search discovers candidate hosts but does not certify the supplied hint. The
gap pass fetches the best name-only candidate and only that fetched page may
assert `canonical_domain`. Never make the fact conditional on
`candidateHost === domain_hint`; that guarantees stale hints survive.

## 2. Scaffold, then author only task-specific parts

Run `scripts/init-research-play.sh <target.play.ts>` as shown in `../SKILL.md`.
Edit only:

- literal broad and supplemental tool calls;
- provider response adapters;
- canonical item identity;
- required claims and evidence policies;
- final evidence-only synthesis and requested export columns.

If catalog metadata does not expose enough output shape to author the adapter,
run one denominator row through the checked broad Play first. Fix schema or
adapter errors before running the full denominator. This is a shape probe, not
a route-selection pilot.

When some results have a fact and others do not, build a typed mutable facts
record (`const facts: NonNullable<RetrievedItemInput['facts']> = {}`) and add
keys conditionally. A conditional `{fact: ...} | {}` expression often widens
the missing property to `undefined` and fails `plays check`.

Copy provider input schemas exactly from `deepline tools describe`. Do not
invent JSON Schema unions or response fields. A provider 4xx/schema error is a
failed mechanism, not an acceptable source-coverage result.

Do not rebuild fanout, fusion, ranking, coverage, or retry logic in the task
Play. Do not add pilot/selection/exploit unless the actual job is comparing
routes for a larger later run.

When it is — `scripts/init-strategy-play.sh`, backed by
`plays/shared/route-experiment.ts` — set the task controls explicitly rather than
letting them default:

```typescript
const task = {
  question: 'Return one verified answer for every input row.',
  selectionUnit: 'row' as const, // 'item' for ranked discovery
  selectionRequiresEligibility: true, // deterministic gates decide what ships
  optimizationObjective: 'coverage_then_cost' as const,
  minimumPilotRows: 3,
  minimumRelevantRows: 2,
  portfolioSize: 3,
};
```

Selection is a small set-cover problem: with 2–8 candidates, evaluate every
portfolio allowed by `portfolioSize` and the credit cap instead of trusting
vendor intuition. Decide lexicographically — verified units covered, then
estimated credits, then route count and latency, then task-fit score, then
reliability, then source diversity as the tiebreak. A route that finds nothing
new after cheaper routes are selected does not earn an exploit slot. For a ranked
list the unit is `row + canonical item`; for one-answer enrichment it is the row
regardless of candidate count; for claim research it is `row + claim`.

## 3. Broad discovery

Use 2–4 materially different mechanisms on the same rows. Good pairs include:

- search index + page fetch/extraction;
- public search + authoritative registry;
- public search + a relevant community or vertical source;
- structured lookup + public evidence.

A sourced-answer or research-aggregator route is useful for discovery, but it
cannot be the only acquisition mechanism. Two prompt variants to the same
action are one mechanism.

Useful query families:

- exact entity + task question;
- exact entity with no supplied-domain restriction, so stale hints can recover;
- official product, newsroom, careers, trust, investor, or customer pages;
- independent reporting, customer/community evidence, or registry records;
- dated signals constrained to the requested window;
- exact buyer, problem, category, or market-language queries.

Normalize each result to `RetrievedItemInput`. Use `canonicalId.url` for public
sources. Preserve title, excerpt/content, URL, author, publication date, route,
query, source family, evidence independence class, facts, and provider outcome.
Map material claim facts in the adapter so the coverage gate can measure them.
Set route `mechanismId` to the literal Deepline retrieval tool ID and
`mechanismClass` to the actual mechanism, such as `search_index`, `page_fetch`,
`research_aggregator`, or `authoritative_registry`.

A search-index or sourced-answer snippet is weak evidence even when its URL is
official. Mark a source `authoritative` only after a successful fetch of the
claimed official page or an actual authoritative registry response. For a
canonical domain, the broad pass should discover candidates and the page-fetch
route should verify the surviving host.

Do not use an entire search snippet or page excerpt as `what_they_sell` or
`primary_buyer`. After fetching the surviving pages, call the shared
`extractEvidenceClaimsWithAi` helper once on those normalized items. Pass only
the missing claim specs, with a concrete instruction and a short limit (usually
160–240 characters). The helper returns analyst-ready values with exact quotes,
clears raw values for those fact keys, and locally rejects quotes absent from
the source. This is bounded synthesis over acquired evidence, not another
retrieval mechanism.

```ts
import { extractEvidenceClaimsWithAi } from './shared/research-kernel';

const extracted = await extractEvidenceClaimsWithAi({
  rowCtx,
  entity: row.company_name,
  items: fetchedItems,
  claims: [
    {
      id: 'what_they_sell',
      fact: 'what_they_sell',
      instruction: 'State the product or service, not a heading or slogan.',
      maximumClaimCharacters: 200,
    },
    {
      id: 'primary_buyer',
      fact: 'primary_buyer',
      instruction: 'Name the customer segment or role explicitly served.',
      maximumClaimCharacters: 160,
    },
  ].filter((claim) => missing.has(claim.id)),
});

return extracted;
```

When raw engagement exists, normalize it within that route using
`normalizeEngagement`. Set source quality deliberately; do not infer truth from
provider rank. Leave missing dates missing.

## 4. Gap-only follow-up

After broad rows materialize, the kernel emits `research_coverage` with one
status per required claim: `supported`, `gap`, `no_result`, or
`provider_error`. Supplemental routes receive the missing claim IDs. They must:

- skip rows whose claims are already supported;
- use a different mechanism, recovered identity, or evidence-led query;
- preserve the broad evidence that triggered the query;
- run at most one bounded pass unless the user explicitly asks for deeper work.

Examples: resolve a discovered product on its official page, date an undated
launch, corroborate an official claim independently, recover a stale domain,
or resolve a named dataset to its exact file/API/repository.

For canonical recovery, prefer a page-fetch action already proven in the broad
pass, called with the recovered candidate URL. A recovered identity is itself
a materially different pass; do not introduce an unproven extractor only to
change provider labels. A supplemental item with evidence but no mapped claim
fact cannot close coverage.

## 5. Persist the evidence contract

Keep these visible in the task Play:

1. broad research rows with route attempts, fused/ranked items, and coverage;
2. final rows with supplemental attempts, final ranking, and final coverage;
3. `research_evidence`, one canonical source row with provenance;
4. `source_coverage`, one row per entity × phase × mechanism;
5. `supplemental_gaps`, one row per broad-pass missing claim;
6. `research_claims`, one row per denominator × required claim.

Add task-specific delivery rows after these. Synthesis receives only final
evidence. Require claim text, supporting evidence IDs, and an explicit
insufficient state. Keep exact source language unchanged and separately labeled
from rewritten copy.

The scaffold exports evidence ID lists as `|`-delimited strings. Keep claim
values short and evidence-close. Never map a whole result excerpt or fetched
page into a claim value. The default kernel limit is 320 characters; set a
smaller per-claim `maximumClaimCharacters` where appropriate. The kernel also
rejects a supported value when fewer than 45% of its substantive tokens appear
in the cited URL, title, or excerpt; verbose paraphrases re-enter the gap pass.

If the request asks for a dataset, paper, file, or repository, a landing page
is not delivery. Resolve and validate the canonical artifact URL or report the
row as partial.

## 6. Stop and report

Stop when every required claim is supported, the bounded supplemental pass
finishes, the next mechanism is not materially independent, marginal yield is
poor, or the credit cap is near.

Report denominator and per-claim coverage, mechanism outcomes, unresolved
identity conflicts, private joins not yet performed, and exact Deepline credit
usage. Never fill a gap from model memory.
