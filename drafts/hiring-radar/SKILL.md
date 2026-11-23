---
name: hiring-radar
description: |
  Turn open job postings into a hiring signal you can rank on — pick the arm whose filters can
  express the roles you care about, count them inside a stated time window, compare against the
  company's own trailing baseline, and report the measurement alongside the number. Use whenever
  someone asks: which of my accounts are hiring, are they staffing up the team that buys from us,
  find companies hiring for X roles, is this account's hiring accelerating, or build me a hiring
  signal for scoring. Four arms return four different "job counts" for the same company on the
  same day — 384 to 8,945, measured on Clay job arms — because each silently picks its own window, so this skill fixes the
  window first and never mixes arms inside one cohort. Do NOT use it for employee-count growth
  (headcount-growth), news and funding events (monitor-buying-signals), sourcing net-new accounts
  from events (signal-sourcer), people changing jobs (track-champion-job-changes), or tech-stack
  detection (detect-tech-stack). Runs on Deepline job tools (theirstack_job_search,
  predictleads_company_job_openings, sentrion_company_jobs_search, crustdata_v3_job_search, …) and,
  for a standing watch, the deepline_native.company_job_openings monitor.
ported_from: clay-run/clay-skill-creator/skills/clay/hiring-radar
category: signals
personas: [sales-development, account-executive]
mechanism: functions
touches: read-only
keywords: []
---

# Hiring radar (declare the measurement, then count)

The insight: **there is no such thing as "the number of jobs open at a company."** Four arms,
one company, one day (2026-08-14), every one of them returning a field named some variant of
*job count*. Measured on Clay's job actions before this skill was ported; costs are Clay credits,
not Deepline prices:

| Arm (Clay action, 2026-08-14) | Field | Value | Clay cost |
|---|---|---|---|
| `theirstack-find-jobs`, no window | `totalJobsFound` | **8,945** | 0.2 |
| `cpj-find-lists-of-jobs`, no window | `jobCount` | **737** | 1 |
| `predict-leads-get-job-openings-for-company-v3`, no window | `total_job_count` | **384** | 1 |
| `theirstack-find-jobs`, 30-day window | `totalJobsFound` | **332** | 0.2 |
| `cpj-find-lists-of-jobs`, 30-day + Director | `jobCount` | **7** | 1 |

A **23× spread** between the three unwindowed totals, and none of the three declares what it
counted or over what period. They are not disagreeing — they are answering different questions.
TheirStack counts posting *events* it has ever observed across many boards. PredictLeads counts
requisitions it currently tracks. The professional-network arm counts postings of unbounded age.
The same providers sit behind Deepline's `theirstack_job_search` and
`predictleads_company_job_openings`, so the lesson carries over; the numbers have not been
re-measured on Deepline.

Three consequences follow, and each one has bitten a real build.

**The default window is unbounded on the counting arms, and the page ordering hides it.**
Every arm returns its sample newest-first, so ten postings dated today sit above a total of 8,945
and the total reads as "8,945 roles open now". The same payload disproves it for free:
TheirStack's `company_object.num_jobs_last_30_days` was **332**, shipped in the same response at no
extra cost. On Deepline, `bloomberry_search_job_postings` makes the trap explicit: `begin_date`
defaults to 2020-01-01.

**An unwindowed count is monotone in company history, so ranking on it ranks by age × size.**
Sort a book by an unwindowed total and you have rebuilt a firmographic sort and labelled it a
signal. A hiring signal has to mean "staffing up *now*", and "now" is a window.

**A waterfall across arms destroys comparability.** The usual advice is to run company job
openings as a waterfall across providers. That is right for coverage of a single-valued fact like
an email, and wrong for a metric: an account resolving on TheirStack scores 8,945 while an account
resolving on PredictLeads scores 384, and the first looks 23× hotter when the two may be hiring
identically. Waterfall the *boolean* and the *evidence* if you like. Never waterfall the count.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The accounts** | the companies to measure | no default |
| **Object** | posting events, or currently-tracked requisitions | ask — the two differed by 23× on the same company |
| **Window** | N days | **30 days is defensible** and must be stated: it matches a free corroborating field (`company_object.num_jobs_last_30_days` on `theirstack_job_search`), so the count can be cross-checked at no cost. Never leave it unset, which silently means all time |
| **Dimension** | titles, seniority, department, location, technology, or none | ask — it decides which arm is permitted, at different prices and billing units |

All four are also declarations: they travel in the output next to the number, permanently.

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the accounts you supply, and the job sources it queries for the window you set.
- **Writes** — nothing. The deliverable is handed back to you. (A standing monitor, if you ask for
  one, writes events to its own Customer DB stream — see "Standing watch".)
- **Never** — writes to a CRM, or reports a job count without naming the window it measured.

## Step 0 — Verify Deepline and pull the schemas live

Run `deepline preflight --json`. If the CLI is missing: `npm install -g deepline && deepline auth
register --wait auto`, then re-run.

Pull the contract of every arm you intend to use, free, and never from memory:

```
deepline tools search "job postings" --json
deepline tools describe <tool_id> --json      # inputSchema, outputSchema, pricing
```

Two reasons this is mandatory rather than tidy. First, **the billing unit lives in `pricing.unit`,
and it differs by arm** — per returned job, per call, per page — see step 4. Second, arm parameter
names and enums drift: a recipe written against this family three months ago named four filter
parameters of which three no longer existed, and today the TheirStack provider playbook lists
seniority values (`manager`, `director`, `vp`) that the live `job_seniority_or` enum does not
accept (`c_level, staff, senior, junior, mid_level`). The describe output wins.
`references/arm-routing.md` records what each arm accepted and costs, with dates; treat it as a
starting point to re-verify, not as a substitute for the pull.

## Step 1 — Declare the measurement before making any call

Three declarations. All three go in the output, next to the number, permanently.

| Declaration | Options | Why it cannot be defaulted |
|---|---|---|
| **Object** | posting events, or currently-tracked requisitions | differed by 23× on the same company |
| **Window** | N days, and which date it filters on | the arm default is unbounded, and "posted", "first seen", "discovered" and "indexed" are four different clocks |
| **Dimension** | titles, seniority, department, location, technology, or none | decides which arm you are allowed to use (step 2) |

Ask the user for the window if they have not stated one. A default exists — **30 days** — and it
is defensible because it matches the free corroborating field TheirStack ships
(`num_jobs_last_30_days`), which lets the count be cross-checked at no cost. State that you used
it. Never leave the window unset, which silently means "all time".

The dimension is the one the user actually cares about and the one they are most likely to state
as an adjective. "Are they hiring salespeople" is a department dimension; "are they hiring
leadership" is a seniority dimension; "are they hiring for Kubernetes" is a technology dimension.
These route to different arms at different prices.

## Step 2 — Route to the arm where your dimension is a filter

This is the step that decides whether your number is a count or a guess. An arm's total is scoped
to the filters you passed — verified on two Clay arms, in both directions: TheirStack's total went
8,945 → 3,136 when a title filter was added; the professional-network arm's went 737 → 7 when a
seniority filter and a window were added. So **when your dimension is filterable, the total is the
exact answer**, and page size does not affect it (`limit: 1` returned the same total as `limit: 10`).

Deepline arms, their window field, and their count field (contract read 2026-09-30; prices in
Deepline credits from `pricing`):

| Your dimension | Filterable on (Deepline) | Route to | Price | Count field |
|---|---|---|---|---|
| title / description keywords | `theirstack_job_search`, `sentrion_company_jobs_search`, `crustdata_v3_job_search`, `bloomberry_search_job_postings`, `forager_job_search_totals` | **`theirstack_job_search`** (`job_title_or`, `job_description_contains_or`) | 0.56 / returned job; a count with `limit: 1` bills one job, zero matches bill zero | `metadata.total_results` (needs `include_total_results: true`) |
| location | TheirStack, Sentrion, Crustdata, Bloomberry | **TheirStack** (`job_country_code_or`) | 0.56 / returned job | `metadata.total_results` |
| technology named in the posting | **TheirStack only** (`job_technology_slug_or`) | TheirStack | 0.56 / returned job | `metadata.total_results` |
| seniority | TheirStack (`job_seniority_or`, no Director tier), Sentrion (`seniority_level`: Entry / Mid / Executive), `harvestapi_search_jobs` (`experienceLevel` incl. `director`, `executive`) | **depends on the tier** — see below | | |
| department / function | `predictleads_company_job_openings` (`categories`), Sentrion (`department`), Crustdata (`job_details.category`), HarvestAPI (`functionId`) | **`predictleads_company_job_openings`** | 0.56 / call, flat — the count costs the same whatever it is | `meta.count` (only when `page` is passed) |
| department + seniority together | **Sentrion only**, and only at its three coarse seniority levels | `sentrion_company_jobs_search` | 0.42 / returned job | `total` |
| none (any role at all) | all | **TheirStack** | 0.56 / returned job | `metadata.total_results` |

Seniority routing: "Director" exists only on `harvestapi_search_jobs` (LinkedIn jobs,
`experienceLevel: director`, 0.01 / page), whose window is `postedLimit` = `24h` / `week` / `month`
only — so a 30-day count is available but a 90-day baseline is not. "Executive" or "C-level"
filters on Sentrion (`Executive Level`) and TheirStack (`c_level`). Whichever you pick, say which
tier vocabulary the number used.

Two cheaper count arms exist and have not been probed on Deepline: `forager_job_search_totals`
(free; window `date_featured_start` / `date_featured_end`; company by `organization_ids` from the
free `forager_organization_autocomplete`) and `crustdata_v3_job_search` with `limit: 0`
(0.02 / returned job, empty pages free; window on `metadata.date_added`, the date Crustdata indexed
the posting, not the posting date). Pilot them against TheirStack on a few accounts before routing
a cohort to them.

When the dimension is NOT filterable on the arm that covers the account, you have exactly two
honest options, and inventing a third is the failure this skill exists to prevent.

**Post-filtering a capped page into a count is a false-negative machine, and the rate is
computable.** Every arm returns a page you pay for — TheirStack per returned job (up to 500),
PredictLeads 100 by default per call, HarvestAPI one LinkedIn page per charge. If your dimension
has true prevalence `p` in the company's book and the page you read has `c` rows, the chance you
see none of them is about `(1 − p)^c`. Measured instance (Clay, 2026-08-14): Director-level roles
at the probed company were **7 of 332** in 30 days, so p = 2.1%; a 20-row TheirStack page without
a Director filter gives `(1 − 0.021)^20` = **65%**. Two times in three you would report "not hiring
leadership" against seven open Director requisitions. Buying a bigger page lowers the miss rate
and raises the bill linearly, and it is still a sample. So:

1. **Re-route** to the arm where the dimension filters, and pay its price.
2. Or **report it as a lower bound** — `≥ N` — and never rank, threshold or trend on it.

The estimate assumes your dimension is not correlated with posting recency, since the page is
ordered newest-first. If it is (a hiring freeze lifted last week), the page is *better* than
random for detection and still useless as a count.

## Step 3 — One arm per cohort, and misses are `unmeasured`

Pick one arm for the whole cohort based on step 2, and hold it fixed. An account the chosen arm
does not cover is **`unmeasured`** — it is not a zero, and it is not an excuse to fall back to a
second arm whose number is on a different scale. A cohort measured by two arms cannot be ranked,
and a rank is the entire deliverable of a radar.

Falling back is legitimate for two things only: the **boolean** ("any postings at all?") and the
**evidence** (a posting title and URL to quote). Both are arm-independent. The count is not.

If coverage on the chosen arm is poor enough to hollow out the cohort, say so and let the user
re-pick the arm — that is a dimension-versus-coverage trade they own, not one you resolve quietly.

For more than ~20 accounts, run the cohort as a play: one dataset over the account CSV, one
`.withColumn` per window call on the chosen arm (`deepline plays check`, pilot 3 rows with
`--debug`, then the full file, then `deepline runs export <run-id> --out <final.csv>`). Rows land in
the Customer DB, so a rerun reuses filled cells instead of re-buying them.

## Step 4 — Get a baseline, because a level is not a signal

"332 open roles" is a fact about company size, not a change. At the probed company that was ~3% of
a 10,853-person headcount in one month; whether it is a surge is unanswerable from one call. Two
ways to get the baseline:

**Two windows on the same arm — 2 × the arm's count price** (1.12 Deepline credits on TheirStack
or PredictLeads). Call your chosen arm twice, at 30 days and 90 days, and compare the recent rate
against the trailing rate: `rate_30 = c30`, `rate_prior = c90 / 3`. Measured on Clay's TheirStack
arm: 332 versus 919/3 = 306.3, so **+8.4%**. Company-wide, longitudinal, and cheap. Window fields:
TheirStack `posted_at_max_age_days` (or `posted_at_gte` / `posted_at_lte`), PredictLeads
`first_seen_at_from` / `first_seen_at_until`, Sentrion `published_after` / `published_before`,
Crustdata a `metadata.date_added` range condition.

**A trailing series in one call.** `bloomberry_search_job_postings` with `show_facets: true` returns
the number of matching jobs per month (0.09 Deepline credits per returned job, so keep `limit`
small; whether facets cover the full window when the page is small is unverified — check the first
response). Pass `begin_date` explicitly; its default is 2020-01-01.

**No Deepline tool covers the per-department change-rate arm this skill used on Clay**
(`lusha-enrich-company-jobs-growth-by-department-signal`, which shipped `newJobsPostedLast4Weeks`,
`historicalAvg` and `changeRatePercent` per department). Measured on the same company: 121 against
a historical average of 108, giving +12% for its largest department — directionally agreeing with
the two-window method while measuring a different thing. On Deepline, get a per-department
baseline by running the two-window method on PredictLeads with `categories` set, one call pair per
department.

**Read the billing unit off `pricing`, not a headline number.** `theirstack_job_search` bills per
returned job, `sentrion_company_jobs_search` and `bloomberry_search_job_postings` per returned job,
`predictleads_company_job_openings` per call, `harvestapi_search_jobs` per page, and
`crustdata_v3_job_search` per returned row (not per matched `total_count`). A count call with a
large `limit` on a per-job arm buys every row on the page. Always pass `limit` explicitly; never let
it default. (On Clay, three of four Lusha growth arms were billed per result found, stated only in a
parameter description; the catalog cost field understated them by up to 100×. The unit is the trap
on every platform.)

**Two freshness traps on a change-rate signal.** On the Clay Lusha arm, `signalDate` was 18 days
before the day it was called, so "last 4 weeks" was four weeks ending at `signalDate`, not today.
Any arm that ships its own signal or snapshot date — carry it into the output, or you will misdate
the evidence. And because such a date moves in steps, consecutive weekly runs can return an
identical signal; a radar that diffs runs must diff on the provider's date, not on the day it ran.

## Step 5 — Verdicts: measurement status first, then the read

Two verdicts at two granularities, and the second is only emitted when the first is `measured`.
Reporting "accelerating" off a lower bound is the error this split prevents.

**Part A — measurement status, in precedence order. The first that applies wins.**

1. `arm_mismatch` — the payload's own returned identity disagrees with the anchor. Compare the
   returned company domain and name (TheirStack `company_domain` / `company` on each job, Sentrion
   `company_details`, PredictLeads `included` company objects) against what you asked for, from the
   same response, before consuming any count. Free, and a domain is a join hint rather than an
   identity.
2. `unmeasured` — the chosen arm returned no coverage for this account, or the dimension is not
   filterable on it and a lower bound was declined.
3. `lower_bound_only` — the count came from post-filtering a capped page. Report `≥ N`. Excluded
   from every ranking, threshold and trend.
4. `measured` — the count came from a filter-scoped total on the routed arm, inside the declared
   window.

**Part B — the read, only when Part A is `measured`.**

1. `no_open_roles` — the windowed count is 0. A real answer, and a common one; never pad it.
2. `level_only` — count is below 10 in the current window, or no baseline was obtained. Report the
   raw counts and stop. Below 10 a percentage swing is smaller than a single posting, so a rate
   there is noise wearing a decimal point.
3. `accelerating` — the recent rate exceeds the trailing rate by more than 25%.
4. `decelerating` — the recent rate is more than 25% below the trailing rate.
5. `flat` — inside the ±25% band.

**The ±25% band is defaulted from the disagreement between two legitimate methods, not invented.**
On the probed company (Clay, 2026-08-14), two windows gave +8.4% and the dedicated arm gave +12%:
two defensible measurements of "is hiring accelerating" that differ by 3.6 points. A band tighter
than the gap between methods reports method choice as signal. The user may tighten it — say what
that costs them in false positives when they do.

## Step 6 — Emit the number with its measurement attached

Per account: the count, the object counted, the window and its date field, the dimension and its
arm (tool ID), Part A, Part B, the baseline figures behind Part B, and the evidence (one or two
posting titles with URLs and dates).

Never emit a bare count. `"47"` is unusable by the next reader; `"47 postings, last 30 days by
posting date, Executive seniority, sentrion_company_jobs_search, measured, +31% vs trailing 90d"`
survives being pasted into a spreadsheet, compared against another account, and re-run next week.

Report cohort-level spend from what was actually billed (`deepline runs get <run-id> --full --json`
for a play, or the balance delta from `deepline billing`), not from list price × calls: on
TheirStack a zero-match count bills zero, so list price × calls overstates what a book with dead
rows actually cost.

## Standing watch (optional)

When the user wants new postings pushed to them rather than a one-off rank, that is a Deepline
monitor, not a re-run: `deepline_native.company_job_openings` (deploy as tool
`deepline_native.company_radar`, `radar_type: company_job_openings`, per `domain`; optional
`departments`, `seniorities` — which include `Director` and `Vice President` — or a `job_titles`
expression, which overrides both). 1.25 Deepline credits per accepted finding at the time of
porting; read the live price from `deepline tools get deepline_native.company_job_openings --json`.
Monitors are access-gated: run `deepline monitors status --json` first and follow the
`deepline-monitors` skill for check, dry-run, approval and Slack delivery.

A monitor counts a different object — postings first discovered after deployment (or after
`updates_since`, at most 90 days back) — so its event count is not the same measurement as a
windowed count from step 2. Do not rank a cohort on a mix of the two.

## What this skill does not claim

- Five arms verified live against one company on one day, on Clay; no cohort run, and the
  Deepline arms' window and count fields are read from their declared contracts, not probed. How
  often an account turns out to be unmeasurable is unknown.
- The 65% false-negative figure is arithmetic on one measured prevalence, not an observed miss rate.
- `harvestapi_search_jobs` declares `pagination.totalElements`; whether it is an exact count or
  LinkedIn's approximate total is unverified. Check it against a second arm before ranking on it.

## What good looks like

- Every count in the output carries its window and its object; no bare "job count" anywhere.
- One arm per cohort, named by tool ID, with the accounts it did not cover listed as `unmeasured`.
- The dimension the user asked about is a filter on the arm chosen — or the number is marked
  `lower_bound_only` and excluded from the ranking.
- A baseline exists for every account reported `accelerating` or `decelerating`, with both figures.
- Arms are priced at their billing unit (per job, per call, per page) at the `limit` actually passed.
- The common failure: pulling a total with no date filter, seeing today's postings at the top of
  the page, and reporting an all-time total as current hiring. Second-worst: post-filtering a
  20-row page for a 2%-prevalence dimension and reporting the zero as "not hiring".

## Rules

- MUST declare object, window and dimension before the first call, and carry all three into the
  output; NEVER emit a count without its window.
- MUST pass an explicit date-window parameter on every counting call; NEVER rely on the arm's
  default, which is unbounded (or, on Bloomberry, 2020-01-01).
- MUST route the count to an arm where the requested dimension is a filter; NEVER post-filter a
  capped page and report the result as a count — mark it `lower_bound_only` or re-route.
- MUST use one arm for a whole cohort and mark uncovered accounts `unmeasured`; NEVER waterfall
  the count across arms, and never treat a coverage miss as a zero.
- MUST obtain a baseline before reporting acceleration, and emit both figures; NEVER report a
  level as a trend.
- MUST read the billing unit from `pricing` and pass `limit` explicitly; NEVER price an arm from a
  headline number alone.
- MUST check the payload's own returned company identity against the anchor before using any
  count from it.
- MUST carry the provider's own signal date when an arm supplies one, and diff runs on that date
  rather than on the run date.
- NEVER report a percentage change on a current-window count below 10.
- NEVER rank, threshold or trend on a `lower_bound_only` count.

## Worked example

Asked: *"which of these 200 accounts are staffing up their sales org, and who's accelerating?"*

Declared measurement: **requisitions first seen in the window, 30 days, department dimension =
sales.** The department dimension routes to `predictleads_company_job_openings`
(`categories: ["sales"]`, `first_seen_at_from`, `page: 1` so `meta.count` comes back) at 0.56
Deepline credits per call, flat. TheirStack would cost the same per count call here and would force
`lower_bound_only` on every row, since it has no department filter — so the routing is free.

Baseline by the two-window method on the same arm, so 400 calls, 224 Deepline credits at list
price. Delivered:

| Account | Count (30d, sales) | Trailing (90d/3) | Part A | Part B |
|---|---|---|---|---|
| A | 34 | 18.7 | measured | **accelerating** (+82%) |
| B | 12 | 11.3 | measured | flat (+6%) |
| C | 6 | 4.0 | measured | level_only (below 10) |
| D | 0 | 0 | measured | no_open_roles |
| E | — | — | unmeasured | — (arm returned no coverage) |
| F | ≥3 | — | lower_bound_only | — (seniority sub-filter, post-filtered) |

Row F shows the trap in miniature. The user also wanted "director+ in sales", which is a *second*
dimension. Department filters on PredictLeads, Director filters only on HarvestAPI, and the one arm
that filters both (Sentrion) stops at `Executive Level`, which is not "director+". So the honest
deliverable is two cohorts measured separately, or one cohort with the second dimension carried as
a lower bound and excluded from the ranking — not one number that quietly satisfies neither.

Stated at the top of the delivery, not buried: *counts are requisitions first seen in the 30 days
ending today, measured on one arm; the `unmeasured` accounts are not zeros; row F's figure is a
floor, not a count.*
