# Detector mechanics — the net-new arm, noise profiles, harvest rules, surfaces

Tool IDs confirmed with `deepline tools describe <id> --json` on 2026-09-30; re-verify
per org — catalogs, prices, and payload shapes drift, and `describe` does not publish
these tools' output fields, so read the first response before writing the harvester.
Noise profiles and harvest rules below were live-observed on Clay's Google News action
(2026-08, isolated eval workspace); they describe the search-index channel, not that
vendor, and apply to the Deepline search arms the same way.

## What this surface has (and doesn't)

| Arm | Verdict |
|---|---|
| `serper_google_search` (0.02 credits per result, 2026-09-30) | **The net-new detector.** Free-text `query` (required), `tbs` recency bucket (`qdr:h/d/w/m/y`), `num` (honoured exactly), `gl`, `hl`. Event-anchored queries (no company in the query) return articles about companies you don't know yet. |
| `dataforseo_serp_google_news_live_advanced` (usage-priced) | News-tab SERP by `keyword` + location/language; second detector for news-heavy vocabularies. |
| `exa_search`, `parallel_search` | Semantic web search; useful as a variant arm, same gates apply. Describe before use. |
| `prebuilt/funding-updates` (play) | **Structured net-new funding feed** from the Deepline funding-rounds radar: up to 100 rounds per page discovered since `since`, with `next_cursor`. Funding only. Still gated on entity, ICP and book. |
| Company search (`crustdata_v3_company_search`, `free_simple_company_search`) | **No event or date filters** beyond static firmographics and funding fields — search cannot source by signal; it is the ICP-first arm (build-prospect-list's turf) and the free entity-resolution arm here. |
| Structured event lookups (`predictleads_company_financing_events`, `predictleads_company_news_events`, `predictleads_company_job_openings`; 0.56 credits per call) | All take a **domain as input** — corroboration arms for candidates you already resolved, never sourcing arms. |
| Deepline industry radar monitors (`deepline_native.industry_mentions`, `deepline_native.industry_job_openings`) | Standing, event-billed feeds keyed on `industry` + `countries`. Access-gated; graduation path, not built by this play. |

## The query contract

- Compose queries as **event vocabulary × ICP qualifier** (round/incident/expansion
  vocabulary × vertical/industry term). Two to three variants per signal type beats
  one broad query — vocabulary drives the noise profile (below).
- Quoted phrases are RECALL, not precision (observed: a quoted round name returned
  adjacent-round raises and a preferred-stock conversion notice). Never treat the
  query as the qualifier; the gates qualify.
- Windowing is relative buckets only (`qdr:*`) — precise windows need bucket +
  post-filter on derived dates.
- **Quiet shape**: on the search arms a quiet query can omit the results field
  entirely (not an empty list). Gate on absence-of-events; `serper_google_search` bills
  per result returned.
- **The date stamps are crawl dates.** Observed: a years-old roundup surfaced
  inside a one-week bucket stamped "3 days ago" — the bucket bounds when the index
  saw the page, not when the event happened. Also, dates arrive as relative strings
  ("6 days ago"); parse to absolute at sweep time, then treat as a claim.

## Noise profiles by vocabulary (live-observed; expect both mixes)

| Vocabulary family | Dominant noise | Countermeasure |
|---|---|---|
| Funding/round terms | Roundup + listicle pages; false vocabulary matches (finance-instrument notices, adjacent rounds); social posts with garbled figures; stale archives with fresh crawl stamps | Harvest roundups per below; per-candidate event verification; drop social; derive dates from content |
| Incident/breach terms | High article precision but heavy CROSS-OUTLET DUPLICATION (one event in 3–4 outlets per sweep); law-firm "investigation" PRs derivative of the true event; tracker/listicle pages | Dedupe on (entity, event); demote law-firm PRs to entity-only leads; corroborate to the primary notice |

## Harvest rules (article → candidate)

The unit of work is a CANDIDATE = (company, claimed event), never an article.
**Order matters**: classify the source (rules 1–4) → dedupe into event clusters
(rule 6) → derive the merged candidate's event date from its best-basis source
(rule 5) → window-check the merged candidate. Dating before dedupe kills cluster
members one by one on their weakest source; the EVENT is the unit that lives or
dies.

1. **Direct event article** → one candidate: name, event type, claimed date
   (from text/URL), amount/scale if stated, source URL.
2. **Event roundup/digest page** (weekly deals roundup, breach tracker — pages
   aggregating DATED events) → harvest every named company as a candidate marked
   `corroboration-required`. Sourcing posture inverts the monitoring rule: when
   WATCHING a named account, aggregator pages are dropped (a page about history
   is not an event); when SOURCING, an event roundup is a candidate-rich feed —
   but the roundup is a pointer, not evidence. Each harvested candidate must be
   corroborated per-company (primary article or structured lookup) before
   delivery. Harvest ONLY entries matching the sweep's signal menu (a deals
   roundup mentions acquisitions, milestones, hires — take what was asked for),
   and only entries whose own claimed timing can sit inside the window; a
   roundup aggregating a longer period than the sweep ("this summer", "this
   year") contributes only its in-window entries. **Profile listicles are not
   event pages** ("top X to watch", "best Y of 2026" — companies aggregated by
   PROFILE, not by something that happened): drop them; harvesting them
   manufactures undated candidates that waste corroboration spend.
3. **Social posts / forums** → drop the article (garbled figures observed live);
   an entity may be re-harvested if another source carries it.
4. **Law-firm / class-action PRs and other derivative coverage** → the
   underlying event is usually real but the page is derivative; keep the entity,
   mark `corroboration-required`, cite the primary notice in delivery. A
   derivative source's dates never DATE the event and never KILL the candidate —
   they simply don't count; the date comes from corroboration or a primary
   cluster-mate.
5. **Date derivation** — the date of the UNDERLYING EVENT, not the article:
   in-text event date > URL-path date > publication dateline (weakest — derivative
   coverage is fresh about old events: a new lawsuit story dates the lawsuit, not
   the breach it's about). For incident/disclosure signals the actionable event
   date is the DISCLOSURE/notification date, not the incident's start (breaches
   are often months old when disclosed — a prior-report or filing date in the
   text dates the disclosure and counts). Applied to the merged candidate using
   its best-basis source: outside the window kills it (recorded); no derivable
   date → `undated`, deliverable only if corroboration supplies the date.
6. **Dedupe into event clusters** across the whole sweep — key on (entity,
   event-type, approximate date), and merge on EVENT FINGERPRINT (matching scale
   figure, geography, timing) even when names differ or are missing: one outlet
   names the parent, another the subsidiary, a third no company at all — one
   incident, one candidate, all names carried forward for Step 5 to resolve to
   the entity the user would actually sell to. Lead-source primacy: the
   disclosing party's own notice > regulator/registry filing > trade press
   (peers — pick any, say so). An unnamed-entity article matching no cluster is
   an `unresolved-entity` candidate. Same entity with two DIFFERENT events = two
   candidates.
7. **Name-boundary discipline** (monitoring kin, applies here too): a candidate
   name must not be a prefix of a longer org name (suffix tokens:
   Partners/Group/Capital/Holdings) or a vessel/product designation. Resolution
   (SKILL.md Step 5) is where near-name traps are finally settled.

## Running the sweep

A handful of queries runs fine as ad-hoc calls:

```bash
deepline tools execute serper_google_search \
  --input '{"query":"\"data breach\" hospital notification","tbs":"qdr:w","num":10}'
```

Past ~10 queries, put them in a CSV (`query,signal_type`) and run a play with one
`.withColumn('results', 'serper_google_search', {...})` step — the play persists every
response in the Customer DB, so a rerun reuses filled cells instead of re-buying them,
and `deepline runs get <run-id> --full --json` reports the measured cost. Harvesting
(rules above) can be a `run_javascript` column or done by the agent on the exported
rows; `deeplineagent` with a `jsonSchema` is the LLM pass for ambiguous articles only.
See the deepline-gtm skill (`recipes/deepline-plays.md`) for play authoring.

## Degraded-mode corroboration (primary source unreachable)

The primary article may not scrape (`contextdev_get_web_scrape_markdown` fails on
paywalls, bot walls, removed pages), and incident-type signals have NO structured
corroboration tool (structured lookups are funding/news/jobs only) — so "fetch the
primary source" can be unexecutable. The substitute ladder: (1) cross-outlet agreement —
≥2 independent outlets carrying the same event fingerprint corroborates the event;
(2) the enrichment/search echo corroborates the ENTITY (never the event); (3) a
candidate left with one derivative source drops as `uncorroborated — source
unreachable`. State which mode the sweep ran in; never claim primary-source
verification that didn't happen.

## Cost model (state before the sweep)

- Query: `serper_google_search` bills per result returned (0.02 credits per result,
  2026-09-30) — fan-out = signal types × variants × `num`.
- Resolution: `crustdata_v3_company_identify` and `free_simple_company_search` are free.
- Qualification: `crustdata_v3_company_enrich` per surviving candidate (0.8 credits per
  result, 2026-09-30; band-string outputs — compare as bands, never parse to ints).
- Premium corroboration: structured funding/news/jobs lookups (0.56 credits per call)
  per company — shortlist only, named and approved.
- Read measured cost from `deepline runs get <run-id> --full --json`; ad-hoc calls get
  "declared estimate" wording from `describe`'s `pricing`.

## Graduation (standing watches)

A repeated ask ("every week, same definition") should not become a re-scraping
loop. Hand off to Deepline monitors (access-gated: `deepline monitors status --json`):
an industry radar (`deepline_native.industry_radar` with `radar_type:
industry_mentions` or `industry_job_openings`, payload `industry` + `countries`) bills
per accepted event and lands rows in a Customer DB table; a play bound with a
`sqlListeners` trigger (`deepline plays bootstrap monitor-triggered`) runs this
skill's harvest → resolve → qualify gates per new row. Funding sourcing runs
`prebuilt/funding-updates` on the cadence with `since` = last run. Validate with
`deepline monitors check` and `deploy --dry-run`, and deploy only after the user
approves the per-event price. Offer the arithmetic (cadence × fan-out vs per-event
cost); the sweep remains right for one-shot and exploratory definitions.
