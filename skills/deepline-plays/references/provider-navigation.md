# Provider navigation: seed, pattern, scale

Use this reference while turning a GTM job into distinct, testable retrieval
strategies. Providers are components in a source program, not the strategy.

## Table of contents

1. Start from the job
2. Discover the live catalog
3. Route by retrieval role
4. Navigate search and third-party data
5. Probe, learn the pattern, then scale
6. Provider-specific guidance
7. Preserve independence and source lineage
8. Evaluate a strategy pool
9. Compile the selected route

## Start from the job

Write the outcome before searching the catalog:

- **Unit:** company, person, location, job, event, or another entity.
- **Required claims:** the facts each delivered row must establish.
- **Terminal evidence:** the URL, excerpt, record, and freshness needed to
  accept each claim.
- **Cohort rule:** requested complete rows and any cross-row constraints, such
  as a minimum LinkedIn coverage rate.
- **Economics:** pilot size, maximum Deepline credits, latency target, and what
  may remain unresolved.

This contract separates a useful lead from a completed row. A search result can nominate a company or page; it cannot prove a final claim unless its evidence satisfies the claim policy.

## Discover the live catalog

Provider names and action IDs below are starting hints. The installed Deepline catalog is the source of truth for availability, inputs, outputs, limits, and Deepline credit bounds.

Search by the role you need, not by a remembered action name:

```bash
deepline tools search "concept web search source discovery" --json
deepline tools search "structured company people search filters" --json
deepline tools search "known URL scrape map crawl extract" --json
deepline tools search "current role company identity verification" --json
```

Then inspect only the strongest candidates:

```bash
deepline tools describe <tool-id> --json
```

Use the description to bind the literal action ID, current schema, output
shape, async behavior, and maximum Deepline credits. Do not infer fields,
enums, or price from this skill. Record catalog gaps instead of inventing calls.

## Route by retrieval role

| Role                            | Question                                       | Prefer                                                                            |
| ------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------- |
| Seed discovery                  | Where might the answer live?                   | Claude Code or another authoring agent, broad web/SERP search, Exa concept search |
| Structured candidate generation | Which entities match crisp filters?            | Company, people, jobs, maps, registry, or vertical database tools                 |
| Known-URL retrieval             | What does this page actually say?              | `ctx.fetch`, single-page scrape, or content retrieval                             |
| Site planning                   | Which pages on this domain are relevant?       | Sitemap/site map before content retrieval                                         |
| Repeated retrieval              | How do we fetch an already-known URL set?      | Batch scrape or bounded parallel `ctx.fetch`                                      |
| Extraction                      | How do we turn retrieved text into fields?     | Deterministic parser first; schema-guided extraction when layout varies           |
| Terminal verification           | Does this exact source prove this exact claim? | Claim-specific binder and acceptance check over raw source text                   |

The authoring agent may use browser, terminal, or its own web tools to discover promising sites and query shapes quickly. That work seeds the Play. Final facts must still be fetched and bound inside the completed Play so each row has a receipt and replay path.

## Navigate search and third-party data

Choose by the shape of uncertainty:

- Use **structured providers** when filters are crisp and match the provider's
  ontology: headcount, funding, geography, seniority, technologies, or current
  employer. They give normalized candidates efficiently, but coverage and
  freshness vary by segment.
- Use **web or SERP search** when the source is unknown, the concept is
  semantic, the fact changes quickly, or niche entities are missing from
  databases. Search has wider source reach but noisier ranking and weaker
  completeness guarantees.
- Use **maps search** for local businesses, storefronts, service areas,
  addresses, phones, and websites. Ordinary web search often under-ranks these
  entities.
- Use **known-source retrieval** when the authoritative directory, registry,
  portfolio, staff page, ATS, or filing is already known. Repeated search is a
  costly and less complete substitute for traversing the source itself.
- Use **private data** when the claim belongs to CRM, warehouse, or product
  state. Public corroboration does not replace a stable private join.

A provider database can supply a lead and an official page can supply proof. That is one end-to-end strategy, not two competing final answers.

## Probe, learn the pattern, then scale

Use a three-stage transformation:

1. **Probe:** run a few focused searches or inspect a few representative sites.
   Preserve result URLs, misses, query text, and the source types returned.
2. **Pattern:** identify the durable access path: a directory pagination rule,
   sitemap section, URL prefix, page template, registry endpoint, or stable
   entity key. Write a deterministic adapter and excerpt binder for it.
3. **Scale:** replace repeated open-ended discovery with the cheapest bounded
   mechanism that follows the pattern: `ctx.fetch`, a map plus selected batch,
   a capped crawl, or a structured provider query.

Do not scale the seed tool by habit. Claude Code or Serper may reveal a directory that a direct fetch loop should traverse. Exa may reveal a staff-page pattern that Firecrawl map plus batch scrape should execute once domains are known.

Re-probe when a source template, query policy, or acceptance rule changes.
Version the adapter and checkpoint IDs so stale cells are recomputed instead of
silently reused.

## Provider-specific guidance

### Exa: semantic source discovery

Use Exa for concept-driven company, people, page, and signal discovery. Use
search or entity search to collect candidate URLs, then contents retrieval to
inspect the selected pages. Treat answer/synthesis actions as a presentation
layer when precision matters, not as the evidence-gathering first step.

Exa ranking is strong for semantic relevance, but one broad query is not a census. Partition along axes that change the result population: geography, vertical, entity type, company-size band, time window, role family, or a known source domain. Keep pilots small. Dedupe by canonical entity and URL before widening.

Granular queries beat one giant prompt only when the partitions are meaningful.
Cosmetic paraphrases return correlated rankings and create false coverage.
Keep entity-category search separate from source/domain-scoped page search;
mixing those intents can suppress useful results. Confirm the current controls
with `tools describe` rather than copying old payloads.

### Serper: fast live breadth

Use Serper for fast Google recall, changing facts, source discovery, and URL
recovery. Use its maps family for local-business discovery. Validate important
results by retrieving the returned URL; a snippet is a lead, not durable proof.

When many rows need the same search shape, use the catalog's batch route or let
row-wise calls coalesce when the current compiler supports it. Batch capacity
and shared option constraints can change. Inspect the live description before
compiling the Play, and keep positional alignment between query and result.

Batching reduces transport overhead; it does not make searches independent. Queries that differ only by wording still share Google's index and belong to one source-lineage group.

### Firecrawl: turn known web scope into content

Choose the smallest surface that matches the known scope:

- One known page: scrape it.
- Known URL list: batch scrape it rather than issuing independent jobs.
- Known domain, unknown page paths: map first, select relevant URLs, then batch.
- A bounded site section that requires link following: preview crawl parameters,
  then crawl with explicit path and page limits.
- Variable page layouts that resist deterministic parsing: use structured
  extraction over the smallest known URL set.

Map discovers URLs but does not retrieve their content. Its current catalog
contract has a large default and a higher hard ceiling, so always pass a small,
intentional limit. Batch scrape scales with the number of input URLs; dedupe and
select before submission. Crawl currently defaults to a very large page budget
and preflights against the requested limit; always preview and set an explicit
lower limit unless a broad crawl is genuinely intended.

Map, batch, crawl, and extraction constraints can change. Read their live
descriptions before execution. Treat blocked pages and processed 4xx responses
as evidence about the route, not invitations to retry blindly.

## Preserve independence and source lineage

Consensus means independent evidence mechanisms agree, not that several tools
repeat one underlying source.

- Record the final URL, publisher/owner, raw excerpt or record, retrieval time,
  and provider action for every accepted claim.
- Assign a lineage group such as `official_site`, `google_index`,
  `professional_profile_index`, `public_registry`, `private_crm`, or
  `warehouse`.
- Collapse duplicate URLs, syndicated copies, and providers backed by the same
  corpus before counting corroboration.
- Keep discovery provenance separate from terminal evidence provenance.
- Let an LLM reject a bound excerpt that fails the claim policy. Do not let it
  add a fact absent from the excerpt.

Two search vendors agreeing on the same LinkedIn page is one source. An official staff page and a state license record are usually independent sources.

## Evaluate a strategy pool

Each candidate strategy should state:

- hypothesis and source lineage;
- literal retrieval stages and the handoff between them;
- query partitions or traversal pattern;
- expected calls per row and catalog-bound credit ceiling;
- terminal evidence and binder;
- likely coverage segment and failure mode;
- why it is materially different from the other candidates.

Pilot distinct strategies on the same small, representative rows. Promote by:

1. hard claim and cohort constraints;
2. verified complete-row yield;
3. marginal coverage over the routes already selected;
4. adapter stability and source bindability;
5. Deepline credits and latency.

Copy a current described/quoted ceiling into the program's
`maximumDeeplineCreditsPerAttempt` only when attempt-level billing attribution
is unavailable. The experiment labels that value `catalog_upper_bound`; it is
never presented as observed spend. Whole-run opening-minus-closing billing is
still authoritative.

Do not average away a hard failure. An adapter break is not a source miss. A
zero-result source is not proof that the entity lacks the fact. Freeze the
checks before the holdout; strategies may improve their queries and adapters,
but they may not weaken acceptance to look better.

## Compile the selected route

After the pilot, turn the winning stages and useful independent fallbacks into
one deterministic Play. Keep literal provider branches visible. Preserve the
seed queries, selected URLs, excluded candidates, raw evidence, and stop reason.

At runtime, use search only where uncertainty remains. Exploit learned site or
query patterns everywhere else. The result should feel adaptive during
authoring and be inspectable, replay-safe, and bounded in production.
