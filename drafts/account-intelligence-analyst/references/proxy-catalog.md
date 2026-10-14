# Proxy catalog — observables, arms, and what they cost

Deepline arms and prices read with `deepline tools describe <id> --json` on **2026-09-30**. The
payload behavior in the last section was probed on **2026-08-13** through Clay's equivalent
actions; it is kept because it describes how this class of arm misbehaves, and is attributed as
such.

**Re-resolve before quoting.** Providers appear, disappear and reprice; a price recited from
this file is a price from memory, which the skill forbids. The value here is the *shape* — which
observables have arms, which have many, and how wide the spread is — not the numbers.

## ⚠ Read `pricing.unit` — many arms bill per RESULT, not per call

The single most expensive mistake available in this file. In the Deepline catalog the unit is
declared, not hidden: `describe` returns `pricing.unit` = `call`, `result`, `page` or `usage`,
plus `creditsPerUnit`. A `result`-priced arm multiplies by whatever it returns:

| Arm | Price | Unit | What one account can cost |
|---|---|---|---|
| `theirstack_job_search` | 0.56 | per result | 20 postings → **11.2 cr**; uncapped `limit` is unbounded |
| `theirstack_technographics` | 1.66 | per result | 20 technologies → **33 cr** |
| `crustdata_v3_job_search` | 0.02 | per result | 100 postings → 2 cr; empty pages free |
| `bloomberry_search_job_postings` | 0.09 | per result | 50 postings → 4.5 cr |
| `akta_*` | — | usage | priced after execution; quote as unknown until a pilot measures it |

(Measured on Clay, 2026-08: the same trap existed there with the multiplier hidden in a parameter
description — an addresses arm at "0.8 credits for each operating location" cost 8 credits at its
default and 80 at its cap.)

**Rule this yields, and it belongs in every cost estimate:** price a `result` arm at the `limit`
you intend to pass, and always pass one. Summing `creditsPerUnit` across arms is only valid for
`call`-priced arms. A per-result arm with no `limit` is an unbounded per-account cost; a
`usage` arm is unpriced until a 1–3 account pilot shows the real charge in
`deepline billing usage`.

Corollary worth its own line: **for a COUNTING question, prefer a flat or aggregate arm.**
`crustdata_v3_job_search` accepts `aggregations`, and `predictleads_company_job_openings` is 0.56
per call regardless of how many openings come back. Either beats paging a per-result listing
arm when the proxy only needs a number.

## The finding that shapes the play: the same observable costs ~10× more on one arm than another

Deepline prices, 2026-09-30, per account:

| Observable | Cheaper arm | Cost | Dearer arm | Cost | Spread |
|---|---|---|---|---|---|
| Open job postings | `crustdata_v3_job_search` | 0.02 / posting | `theirstack_job_search` | 0.56 / posting | **28×** per row |
| Employee growth | `crustdata_v3_company_enrich` (`fields: ["headcount"]`) | 0.8 | `akta_headcount_trends` | usage | pilot it |
| News / press | `contextdev_post_news_search` | free | `predictleads_company_news_events` | 0.56 / call | — |
| Tech stack | `bloomberry_get_company_tech_stack` | 0.43 / call | `theirstack_technographics` | 1.66 / result | **~4×+** |
| Web traffic | `crustdata_v3_company_enrich` (`fields: ["web_traffic"]`) | 0.8 | `akta_website_traffic` | usage | — |
| Funding | `predictleads_company_financing_events` | 0.56 / call | `crustdata_v3_company_enrich` (`fields: ["funding"]`) | 0.8 | 1.4× |
| Operating locations | `crustdata_v3_company_enrich` (`fields: ["locations"]`) | 0.8 flat | — | — | no per-location arm needed |

Note `crustdata_v3_company_enrich` is 0.8 per company **whatever field groups you request** at the
price read on 2026-09-30 — so headcount, web traffic, funding and locations in one call is one
charge. Bundle the proxies that live on it; re-check `pricing.details` in case group pricing
changes.

Two things follow, and they are the whole reason step 2 prices proxies before running them:

1. **Ordering is the cost model.** A four-proxy question costs ~1 credit per account on the
   cheap arms and 10+ on the expensive ones. At 300 accounts that is 300 versus 3,000 — the
   difference between a play someone runs weekly and one they run once.
2. **Cheap first is not just cheaper, it is better sequencing.** The cheap arms are usually the
   coarse ones (is there *any* posting) and the expensive ones the fine-grained ones (postings
   by department, by location, trended). Coarse-then-fine is the order that lets early exit
   work: the coarse arm often settles the answer, and the fine arm is only worth buying for the
   accounts still unsettled.

Note also the **free** arms, which should almost always be proxy #1: the company's own site
(`curl` locally, or `firecrawl_scrape` at 0.02/page), a DNS/status pre-gate, and
`crustdata_v3_company_identify` for the identity anchor. Free arms cannot early-exit you *out* of
a paid call if they run first, and they anchor the entity — which the skill requires before any
paid proxy.

## Question type → proxy set

Starting points, not prescriptions. The user's weights decide, and the bar comes from step 1.

### "Are they building a team / capability in X?"
| Proxy | Arm | Notes |
|---|---|---|
| Open roles naming X | job-postings arm | strongest single proxy; a posting is a committed spend |
| Growth in the relevant department | department-growth arm | expensive; buy only for unsettled accounts |
| X named in own site copy | site fetch (free) | **weak** — marketing copy, near-universal for hot categories |
| Named leader hired for X | news arm | **corroboration only** — probed: the window parameter is unreliable and results are topically adjacent, so it cannot settle a question alone |
| Internal roadmap / approval | **none** | declare unobservable |

### "Are they expanding into a geography?"
| Proxy | Arm | Notes |
|---|---|---|
| Job posts in that geography | jobs-by-location arm | direct; a role in-region is a commitment |
| Operating addresses in-region | `crustdata_v3_company_enrich` `locations` group | flat per company; locations come back as a list — count them yourself |
| Localized site / regional domain | site fetch (free) | localization is often marketing-led, not operational |
| Regional press | news arm | corroborates, rarely settles alone |

### "Do they run on / against a technology?"
| Proxy | Arm | Notes |
|---|---|---|
| Tech-stack detection | `bloomberry_get_company_tech_stack`, `builtwith_domain_lookup`, `theirstack_technographics` | providers disagree; two agreeing beats one asserting |
| Integration/partner page on own site | site fetch (free) | strong when present, silent when absent |
| Job posts naming the technology | job-postings arm | often the best signal for internal tooling |

### "Are they growing / shrinking?"
| Proxy | Arm | Notes |
|---|---|---|
| Employee-count trend | `crustdata_v3_company_enrich` `headcount` group | 0.8 cr, growth fields included |
| Web-traffic trend | traffic arm | direction only; absolute figures are estimates |
| Funding | `predictleads_company_financing_events` | 0.56 cr/call, lumpy — a raise is not growth |
| Headcount band | company enrichment | **arrives as a BAND STRING** — report the band, never a number |

## Observables with no arm on this surface

Declare these `observable: no` and keep their weight in the denominator. Each is something
users ask for:

- **Budget, approval, procurement stage** — nothing observes internal finance.
- **Contract renewal dates** — not derivable from any catalog arm.
- **Private headcount by team** — department *growth signals* exist; actual team rosters do not.
- **Intent-data / category research activity** — third-party intent comes from
  `zoominfo_search_intent` / `zoominfo_enrich_intent`, which need the user's own ZoomInfo
  connection. Without it, nothing in the catalog returns category intent per account.
- **Identified website visitors** — traffic arms (`akta_website_traffic`, crustdata
  `web_traffic`) are volume, not identity. `deepline_ip_to_company` resolves your OWN visitor
  IPs, which is first-party data the user must supply.

## Provider disagreement is evidence, not noise

Where two arms observe the same thing and disagree, that is a real finding about the account —
usually a stale record on one side. Two arms agreeing is meaningfully stronger than one
asserting, and it is the only corroboration available without human review. Where the budget
allows exactly one arm, prefer the cheap coarse one and let `insufficient evidence` do its job;
a single expensive arm's assertion is not more true for having cost 10× more.


## Probed live via Clay, 2026-08-13 — what the payloads actually do

Four Clay actions executed once each, one call per arm; credit figures are Clay credits. None of
these were run through Deepline. They are kept because the traps (null horizons, page length vs
true total, ignored date filters, topical-not-answer relevance) are properties of the upstream
data class and recur on the Deepline arms in the same role — verify each on the first response.
No payload values are reproduced here beyond field names and counts.

### Clay `cpj-find-lists-of-jobs` (1 Clay cr flat) — the best-behaved arm probed.

Deepline role-equivalent: `crustdata_v3_job_search` / `predictleads_company_job_openings`. Check
whether the response carries a true total (or use `aggregations`) before trusting page length.

Accepts a **bare domain** as `company_identifier`; `job_title_keywords` and
`max_num_days_since_posted` both worked as documented.

**It returns `jobCount` — the true total — alongside the capped result page.** Probe: 10 results
returned, `jobCount: 33`. So on this arm truncation *self-reports*, and a counting proxy is
answerable for 1 credit without paging or cap-equality guesswork. `limit` maxes at 10, but
`identifiers_only: true` lifts that to 500 (title + URL only) at the same price.

**But a job count is not a role count.** Those 10 results were **4 distinct titles** across 6
locations — the same role posted per-location, each row a genuine posting. "33 AI/ML openings"
and "4 AI/ML roles" are both true and mean different things, so a proxy must say which unit it
counted. For "are they building a team", distinct titles is the honest figure and the raw count
overstates by ~8×.

Payload note: full job descriptions ship by default — ~6–9 KB each, 72 KB for ten jobs. For an
AI-column build that is a context cost as well as a credit cost, and `identifiers_only` avoids
it.

### Clay `cpj-get-company-employee-growth` (1 Clay cr flat).

Deepline role-equivalent: `crustdata_v3_company_enrich` with `fields: ["headcount"]`.

The `website` (domain) path works, and **echoes back the resolved LinkedIn company URL** — free
corroboration that the arm resolved the same entity your anchor did. Use it as an anchor
cross-check. Its own schema warns the domain path is lower-accuracy than the LinkedIn URL path;
that trade is the price of being domain-anchored.

Returns absolute counts and percent growth at nine horizons (1/3/6/9/12/24/36/48/60 months).
**In the probe, the 1-month fields were `null` while all eight others were populated.** A null
horizon is a data gap, and reading it as zero produces "0% growth" → a `contradicts` verdict
manufactured out of missing data. The most recent horizon is the likeliest to be null, which is
exactly the one a freshness-minded author reaches for first.

Note this arm returned **integers**, while firmographic enrichment arms often return headcount
as a **band string**. Two representations of the same observable from one toolkit; never compare
across them.

### Clay `find-google-news-results` (1 Clay cr flat) — the least trustworthy arm probed.

Deepline role-equivalent: `serper_google_search` (with `tbs` for a date window),
`contextdev_post_news_search`, `predictleads_company_news_events`. Verify the date window is
honored on the first response; do not assume it.

- **`date_filter` has no declared value space** (no enum, no typeSettings, description is
  "Filters news results by date") and the value passed was **silently ignored**: a request
  filtered to the past month returned items dated five months back. It failed in the dangerous
  direction — stale results presented as fresh — with no error.
- **`date` mixes formats in one field**: relative for recent items ("1 week ago", "1 month ago"),
  absolute for older ("May 6, 2026"). Precise windowing off "1 month ago" is not possible.
- **`total_news_results` equals the returned count**, so despite the name it is *not* a
  total-available figure. Contrast `jobCount`, which is.
- **`outputParameters` is `null`** on this action: the declared output contract is not merely a
  subset of reality but entirely absent.
- **Relevance is topical, not answer-shaped.** Asked for a specific hiring event at a named
  company, the ten results included a *different* company hiring *former* employees of the
  target — evidence of the opposite — plus executive opinion pieces and unrelated product news.
  One result was an actual hire at the target, in a different function entirely.

That last point is the empirical case for this whole play. Hand those ten results to a model and
ask "is this company building an AI team?" and it will find abundant AI-adjacent text about the
right company and answer yes. The proxy fired; the question was not answered. **Treat the news
arm as corroboration only, never as a proxy that can settle a question alone**, and weight it
accordingly in step 2.

### Clay `enigma-get-operating-location-addresses` — 0.8 Clay cr **per location**, confirmed.

No Deepline per-location equivalent; `crustdata_v3_company_enrich` `locations` is flat per company.

`maxOperatingLocations: 1` → `totalCost: 0.8` exactly. Returns `operatingLocations` (array) and
`operatingLocationsFound` (the same content as a string — redundant), plus
`operatingLocationRequestedCount` echoing the request. **There is no total-available count**, so
unlike the jobs arm you cannot learn how many locations exist without paying per location — which
is precisely why a flat-priced arm is the right tool for a counting proxy.

### Process note: a timed-out call leaves the spend indeterminate

On Deepline, pass `--idempotency-key <key>` (or `--recover`) to `deepline tools execute` so a
retry after a timeout reuses the original execution instead of paying twice. The Clay probe below
had no such option.

One further probe (re-testing `date_filter` with Google's own `qdr:w` syntax) **timed out at 60
seconds**. Whether the server executed and billed it is unknowable from this side, so it was not
retried — a blind retry risks paying twice for an unknown. The `date_filter` value space
therefore remains unresolved, and the skill treats the parameter as unreliable rather than as
broken.