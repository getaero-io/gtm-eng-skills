# Radar arms — sweep mechanics, costs, and traps per surface

The traps below marked "observed" were pinned on Clay's equivalent actions in an isolated
eval workspace (2026-08-12, sibling-skill research); the Deepline tool IDs are mapped by
contract and must be re-verified on the first sweep. Prices are Deepline list prices from
`deepline tools describe <id> --json` at the time of writing — re-read them before quoting;
catalogs, costs, and payload shapes drift.

## The news arm (backbone)

| Tool | Input | Window control | Price |
|---|---|---|---|
| `serper_google_search` | `query` | `tbs` relative bucket (`qdr:h/d/w/m/y`) | 0.02 credits/result (`num` sets result count) |
| `contextdev_post_news_search` | `searchBy` (+ `filterBy.articleType` e.g. `press_release`) | `filterBy.date.from` / `.to` — a published-at window in epoch ms | free |
| `dataforseo_serp_google_news_live_advanced` | `keyword` | `search_param` | calculated from usage |
| `predictleads_company_news_events` | `company_id_or_domain` | `found_at_from` / `found_at_until` | 0.56 credits/call |
| `deepline_native.company_mentions` (monitor) | `domain` | forward from deploy, or `updates_since` | 1.5 credits per accepted finding |

Run the query arms as one play over the competitor set (`.withColumn` per angle query) so
sweeps are reproducible and the run records spend. `contextdev_post_news_search` filters on
a published-at window, which is a better first date than a crawl stamp — still confirm the
event date from content before it enters the digest. `predictleads_company_news_events` is
domain-keyed and returns categorized, dated events — good for launches and hires, weaker
for pricing. The monitor is the standing alternative to a cron sweep; follow the
`deepline-monitors` skill for approval and read-back.

Query construction — ENTITY-anchored: `"<competitor name>" <angle vocabulary>`
(pricing terms, launch terms, leadership terms). Two to three angle variants per
competitor beat one broad query. Traps (observed):

- **Quiet shape**: the results field can be ABSENT entirely, not an empty list. Gate on
  absence-of-events; the call bills either way.
- **Crawl-date illusion**: Google's returned dates are relative strings measuring when
  the index SAW the page, not when the event happened — a years-old roundup
  surfaces inside a one-week bucket stamped "3 days ago." Derive every event date
  from content (in-text date > URL-path date > dateline), and remember derivative
  coverage (a lawsuit story about last year's incident) dates the coverage, not
  the event.
- **Name-boundary**: the competitor name followed by org-suffix tokens
  (Partners/Group/Capital/Holdings) or embedded in a product/vessel designation is
  a DIFFERENT entity. Drop before classification.
- **Cross-outlet duplication**: one real event arrives in 3–5 outlets per sweep.
  Dedupe into event clusters — key (entity, event-class, approximate date), merge
  on event fingerprint (same figures, same timing) even when headlines differ.
  Lead source primacy: the competitor's own announcement > regulator/registry
  filing > trade press.
- **Roundups and listicles**: an event roundup naming your competitor contributes
  its in-window entry (corroborate to the primary link); a profile listicle
  ("top X vendors") is not an event — drop it.

## The hiring-pattern arm (optional)

Two tells: leadership arrivals in a function (a VP-of-X hire is a roadmap tell 2–3
quarters out) and posting/headcount concentration by function.

- `company_titles` (free, `domain`) — the current title roster; count senior titles per
  function.
- `predictleads_company_job_openings` (0.56 credits/call, `company_id_or_domain`,
  `first_seen_at_from`, `categories`) — dated openings by category for concentration.
- `deepline_native.company_new_hires` / `company_job_openings` monitors (1.75 / 1.25
  credits per finding) — the standing version; filter with `departments` / `seniorities`
  or a `job_titles` expression.

Traps (observed on people-search reads): title keyword filters are substring recall —
post-validate role identity from the returned title; a record's company field can echo
the search anchor rather than verified current employment — treat individual rows as
signals in aggregate, never name individuals in the digest (the digest reports "senior
security leadership arrivals: 2," not people).

## The product/pricing-page arm (optional escalation; scheduled diff)

A scrape of the competitor's pricing/product pages only ever sees CURRENT state —
to make it an event source you must re-run on the sweep cadence and diff against
the stored prior copy (keep last sweep's extraction in the digest record or the play's
Customer DB table; the diff IS the event). Use `contextdev_get_web_scrape_markdown`
(free, `url`, `useMainContentOnly: true`). Scrape traps (observed): success means
"a vendor served bytes," never "the page exists" — a 404 page can scrape as success
content, so corroborate existence-critical reads with a status-honest HTTP probe
(`generic_http` tools, with a User-Agent header); read the output field names from the
first response rather than assuming them.

## The structured corroboration arms (optional; per-company)

`predictleads_company_financing_events` (0.56 credits/call, `company_id_or_domain`) and
`aviato_get_company_funding_rounds` (0.14 credits/call, `website` or `linkedinURL`) for a
claimed raise; `predictleads_company_job_openings` for a claimed hiring surge. They take a
DOMAIN as input — they corroborate a specific claimed event for one competitor, never
discover events. Use for the rare act-on-now item worth a paid confirmation. Read each
tool's price from `describe` before running; where pricing is "calculated after
execution", report the pilot's measured charge as the estimate.

## Degraded-mode rule (no general web egress)

Sandboxed sessions may be unable to fetch arbitrary article URLs. Then: corroborate via
cross-outlet agreement (≥2 independent outlets carrying the same event fingerprint), date
from the strongest in-snippet basis, and mark items `single-source — unverified` when
neither is available. Say which mode the sweep ran in; never silently claim
primary-source verification that didn't happen.

## Cost ladder (state before each sweep)

| Arm | Cost (Deepline list price, re-read before quoting) | Default? |
|---|---|---|
| News queries | `serper_google_search` 0.02/result × results × competitors × variants; `contextdev_post_news_search` free | yes |
| Hiring-pattern reads | `company_titles` free; `predictleads_company_job_openings` 0.56/call | on request |
| Page diffs | `contextdev_get_web_scrape_markdown` free per page | on request |
| Structured corroboration | 0.14–0.56 per confirmed item | act-on-now only |
| Standing monitors | `company_mentions` 1.5 / finding; `company_new_hires` 1.75 / finding | on request |
