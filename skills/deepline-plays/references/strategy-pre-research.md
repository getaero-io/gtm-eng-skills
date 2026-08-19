# Pre-research → strategy cards

Use this before a costly GTM Play when source discovery, rather than execution,
is the uncertainty. It is an authoring step, not a runtime primitive and not a
new DSL. It never delays the first executable comparison: if a card does not
produce a literal artifact/query/path quickly, leave it dormant and run the
strongest executable cards.

The point is to turn an ambiguous request into several independently plausible ways to produce the same **required, verifiable row**. A card is a short hypothesis. A candidate Play is ordinary TypeScript that implements one card.

## The fast path

1. State the required row, its stable identity key, and the evidence needed to
   accept it.
2. Do a short public-source fanout. Search for exact registries, directories,
   APIs, communities, company sites, and private/customer datasets relevant to
   the job. Record the artifact or URL actually found, not a source family
   recalled from memory.
3. Write 2–5 executable cards first; expand to 5–10 only when a costly or
   low-coverage job needs more source geometry. Make them structurally
   different, not merely different providers with the same query.
4. Map each card to its cheapest viable executor: a direct public API/page via
   `ctx.fetch`, a prebuilt Play, a described tool, a private connector, or pure
   local parsing of a fetched artifact. Describe only the provider tools chosen
   for a tiny pilot.
5. Implement the first two cards as ordinary strategy blocks. Pilot them on the
   same small rows, rank complete evidenced outputs per Deepline credit, then
   add the strongest dormant cards only where a gap remains.

If the route is already obvious, use two cards and a one-row pilot. Do not manufacture research ceremony.

## What a card contains

Keep a card to six lines:

```md
### <short lane name>

Claim: <the same required row this lane can complete>
Corpus: <exact public/private source or source class discovered>
Join: <domain, registry id, company name + geography, LinkedIn URL, CRM id, ...>
Proof: <URL, bound excerpt, record id, or provider field that makes the result acceptable>
Executor: <public API/page, local parser, Play, provider tool, private connector>
Route: <literal call/query/path>; probe: <one query / one row>
Risk: <likely miss, ambiguity, stale data, or adapter failure>
```

Example for "mining companies above a revenue threshold and their revenue leader":

```md
### Registry-first companies, person second

Claim: company + qualifying revenue evidence + current revenue leader + profile URL
Corpus: an exact mining registry or directory found in fanout, then company site/team page
Join: legal name/domain/location
Proof: registry/company URL for company; company or profile URL naming the leader
Route: registry/web extraction, then person/title lookup; probe: two companies
Risk: revenue may be private; person lookup is a second stage, not a competing lane
```

## Heterogeneity means different failure modes

Good first-wave cards vary at least two of: corpus, join key, query shape, evidence source, or workflow stage. They can use the same tool if the underlying information path differs.

Useful lanes include:

- an authoritative public registry, directory, or open dataset;
- first-party company pages, filings, job pages, or partner/member lists;
- a broad web/discovery route followed by exact-page extraction;
- a company/person data route keyed by domain or profile URL;
- a private CRM, warehouse, product, or workflow join;
- a signal route such as hiring, funding, technology, reviews, or community activity.

The provider catalog does not constrain this list. For example, a government
registry can be queried through its documented API, a filing can be fetched and
locally parsed, and a known member directory can be traversed from its index.
Use provider tools when they reduce work or add coverage, not because the
catalog made a better source invisible.

Do not count these as separate lanes: the same corpus queried with synonymous
wording, several vendors returning the same unverified field, or a downstream
person lookup versus its upstream company discovery. Sequential stages are
complementary; candidate lanes must be alternatives for the same stage.

## Catalog and cost discipline

Public/private proof determines what should be attempted; the catalog is only
one materialization option. After the fanout:

1. Choose an executor per card: `ctx.fetch` for a documented public surface,
   local parsing for a returned artifact, a private connector for user-owned
   data, or a live catalog route when it is the best match.
2. Search the live catalog by capability, not by a favored vendor, for the
   cards that need it. Describe the few tool actions a card will pilot. Confirm required inputs,
   getters, evidence fields, and Deepline-facing billing.
3. Probe each card on identical rows. Save run receipts and record `complete`,
   `source_miss`, or `adapter_failure`.
4. Rank by accepted evidenced rows, coverage of unresolved gaps, latency, and
   Deepline credits. A no-result is information: it must be classified and
   should trigger a distinct lane, query, or join key before spending more on
   the same failed route.

Never quote or optimize around provider cost. Show only Deepline credits. Full-scope paid execution still needs its normal approval gate.

## Subagents: authoring scale, not runtime intelligence

Subagents may research and write cards in parallel, then author one normal candidate Play each. Give every subagent the same contract:

- the required row and acceptance proof;
- the source fanout findings and current tool catalog excerpt;
- an assigned lane so cards differ by corpus or join path;
- a hard instruction to return a card plus an ordinary TypeScript Play, not a new abstraction;
- a small pilot cap and the output schema needed by the parent experiment.

The parent agent deduplicates cards, rejects false diversity, picks the first
two strongest independent candidates, and wires them into the deterministic
pilot/rank/exploit helper. It does not ask a runtime agent to invent strategy
while a customer batch is running.

## Optional reusable scalar strategy Play

Keep the first experiment inline. When a strategy has earned reuse, publish it
as a scalar per-unit Play and adapt it literally in the parent. The child returns
the existing attempt shape; it does not own a CSV or dataset.

```ts
import type { SearchProgramAttempt } from './shared/search-experiment';

async run({ row, unitKey, phase, gaps, candidates }) {
  return ctx.runPlay<SearchProgramAttempt>(
    'registry_strategy',
    'mining-registry-strategy',
    { row, unitKey, phase, gaps, candidates },
    { description: 'Probe the registry strategy for this unit.' },
  );
}
```

The child returns `{ totalCalls, deeplineCredits?, results }`; each result is
the same `{ resultKey, canonicalEntityKey, claims, hardCheckFailures? }` used
by the inline template. The child must already be published, the play name must
be literal, and the parent stays responsible for the final dataset and the one
shared experiment ledger.

## Definition of done before scaling

- Every required field has an acceptance rule and bound evidence.
- At least two independent lanes were piloted when the prompt leaves the route open.
- Company discovery and contact/person enrichment are separated when they are sequential stages.
- The experiment receipt says which candidate won, what it cost in Deepline credits, and why unresolved rows were retried or left blank.
