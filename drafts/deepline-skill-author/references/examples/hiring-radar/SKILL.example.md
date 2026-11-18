---
name: hiring-radar
description: |
  Turn open job postings into a hiring signal you can rank on — pick the arm whose filters can
  express the roles you care about, count them inside a stated time window, compare against the
  company's own trailing baseline, and report the measurement alongside the number. Use whenever
  someone asks: which of my accounts are hiring, are they staffing up the team that buys from us,
  find companies hiring for X roles, is this account's hiring accelerating, or build me a hiring
  signal for scoring. Four arms return four different "job counts" for the same company on the
  same day — 384 to 8,945 — because each silently picks its own window, so this skill fixes the
  window first and never mixes arms inside one cohort. Do NOT use it for employee-count growth
  (headcount-growth), news and funding events (monitor-buying-signals), sourcing net-new accounts
  from events (signal-sourcer), people changing jobs (track-champion-job-changes), or tech-stack
  detection (detect-tech-stack).
category: signals
personas: [sales-development, account-executive]
mechanism: functions
touches: read-only
keywords: []
---

# Hiring radar (declare the measurement, then count)

> **Example kept for its reasoning.** It was written against Clay's action catalogue: arm names,
> `(packageId, actionKey)` pairs and credit figures in its body were measured on Clay in 2026-08 and
> are not Deepline tool IDs or prices. Step 0 shows the Deepline form; resolve each arm with
> `deepline tools search` / `describe` before reusing any number.

The insight: **there is no such thing as "the number of jobs open at a company."** Four arms,
one company, one day (2026-08-14), every one of them returning a field named some variant of
*job count*:

| Arm | Field | Value | Cost |
|---|---|---|---|
| `theirstack-find-jobs`, no window | `totalJobsFound` | **8,945** | 0.2 |
| `cpj-find-lists-of-jobs`, no window | `jobCount` | **737** | 1 |
| `predict-leads-get-job-openings-for-company-v3`, no window | `total_job_count` | **384** | 1 |
| `theirstack-find-jobs`, 30-day window | `totalJobsFound` | **332** | 0.2 |
| `cpj-find-lists-of-jobs`, 30-day + Director | `jobCount` | **7** | 1 |

A **23× spread** between the three unwindowed totals, and none of the three declares what it
counted or over what period. They are not disagreeing — they are answering different questions.
TheirStack counts posting *events* it has ever observed across many boards. PredictLeads counts
requisitions it currently tracks. CPJ counts professional-network postings of unbounded age.

Three consequences follow, and each one has bitten a real build.

**The default window is unbounded on all three counting arms, and the page ordering hides it.**
Every arm returns its sample newest-first, so ten postings dated today sit above a total of 8,945
and the total reads as "8,945 roles open now". The same payload disproves it for free:
`company_object.num_jobs_last_30_days` is **332**, shipped in the same response at no extra cost.

**An unwindowed count is monotone in company history, so ranking on it ranks by age × size.**
Sort a book by `totalJobsFound` with no date filter and you have rebuilt a firmographic sort and
labelled it a signal. A hiring signal has to mean "staffing up *now*", and "now" is a window.

**A waterfall across arms destroys comparability.** The usual advice is to run company job
openings as a native waterfall (Mixrank → PredictLeads → TheirStack → Pubrio). That is right for
coverage of a single-valued fact like an email, and wrong for a metric: an account resolving on
TheirStack scores 8,945 while an account resolving on PredictLeads scores 384, and the first looks
23× hotter when the two may be hiring identically. Waterfall the *boolean* and the *evidence* if
you like. Never waterfall the count.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The accounts** | the companies to measure | no default |
| **Object** | posting events, or currently-tracked requisitions | ask — the two differ by 23× on the same company |
| **Window** | N days | **30 days is defensible** and must be stated: it matches a free corroborating field, so the count can be cross-checked at no cost. Never leave it unset, which silently means all time |
| **Dimension** | titles, seniority, department, location, technology, or none | ask — it decides which arm is permitted, at three different prices |

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
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or reports a job count without naming the window it measured.

## Step 0 — Verify Deepline and pull the schemas live

Run `deepline preflight --json`. If it fails, name the one command that fixes it (setup at
https://code.deepline.com) and stop.

Pull the input schema of every arm you intend to use, free, and never from memory:

```
deepline tools search "job postings" --json
deepline tools describe <tool_id> --json
```

Two reasons this is mandatory rather than tidy. First, **the cost multiplier lives in the input
schema, not in the cost field** — see step 4. Second, arm parameter names drift: a recipe written
against this family three months ago named four filter parameters of which three no longer exist.
`references/arm-routing.md` records what each arm accepted and returned when probed, with the
dates; treat it as a starting point to re-verify, not as a substitute for the pull.

Identify every arm by its exact **tool ID**. On Clay, action keys collided across packages, so the
same key could resolve to a different vendor at a different price.

## Step 1 — Declare the measurement before making any call

Three declarations. All three go in the output, next to the number, permanently.

| Declaration | Options | Why it cannot be defaulted |
|---|---|---|
| **Object** | posting events, or currently-tracked requisitions | differ by 23× on the same company |
| **Window** | N days | the arm default is unbounded, which is never what anyone means |
| **Dimension** | titles, seniority, department, location, technology, or none | decides which arm you are allowed to use (step 2) |

Ask the user for the window if they have not stated one. A default exists — **30 days** — and it
is defensible because it matches the free corroborating field TheirStack ships
(`num_jobs_last_30_days`), which lets the count be cross-checked at no cost. State that you used
it. Never leave the window unset, which silently means "all time".

The dimension is the one the user actually cares about and the one they are most likely to state
as an adjective. "Are they hiring salespeople" is a department dimension; "are they hiring
leadership" is a seniority dimension; "are they hiring for Kubernetes" is a technology dimension.
These route to three different arms at three different prices.

## Step 2 — Route to the arm where your dimension is a filter

This is the step that decides whether your number is a count or a guess. An arm's total is scoped
to the filters you passed — verified on two arms, in both directions: TheirStack's total went
8,945 → 3,136 when a title filter was added; CPJ's went 737 → 7 when a seniority filter and a
window were added. So **when your dimension is filterable, the total is the exact answer**, and
page size does not affect it (`limit: 1` returned the same total as `limit: 10`).

| Your dimension | Filterable on | Route to | Cost | Count field |
|---|---|---|---|---|
| title / description keywords | TheirStack, CPJ, PredictLeads, LeadMagic | **TheirStack** | 0.2 | `totalJobsFound` |
| location | TheirStack, CPJ, LeadMagic | **TheirStack** | 0.2 | `totalJobsFound` |
| technology named in the posting | **TheirStack only** | TheirStack | 0.2 | `totalJobsFound` |
| seniority | **CPJ only** | CPJ | 1 | `jobCount` |
| department / function | **PredictLeads only** (`categories`) | PredictLeads | 1 | `total_job_count` |
| employment type | TheirStack, CPJ | TheirStack | 0.2 | `totalJobsFound` |
| none (any role at all) | all | **TheirStack** | 0.2 | `totalJobsFound` |

When the dimension is NOT filterable on the arm that covers the account, you have exactly two
honest options, and inventing a third is the failure this skill exists to prevent.

**Post-filtering a capped page into a count is a false-negative machine, and the rate is
computable.** Every arm caps its returned page — TheirStack at 20, CPJ at 10 (or 500 with
`identifiers_only: true`, which returns title and URL only), PredictLeads unstated with a
`more_matches_than_we_can_display` boolean instead. If your dimension has true prevalence `p` in
the company's book and the page cap is `c`, the chance you see none of them is about `(1 − p)^c`.
Measured instance: Director-level roles at the probed company were **7 of 332** in 30 days, so
p = 2.1%; TheirStack has no seniority filter and caps at 20, giving `(1 − 0.021)^20` = **65%**.
Two times in three you would report "not hiring leadership" against seven open Director
requisitions. So:

1. **Re-route** to the arm where the dimension filters, and pay the difference (0.2 → 1 credit).
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

## Step 4 — Get a baseline, because a level is not a signal

"332 open roles" is a fact about company size, not a change. At the probed company that is ~3% of
a 10,853-person headcount in one month; whether it is a surge is unanswerable from one call. Two
ways to get the baseline, and they cost 60× different amounts:

**Two windows on the same arm — 0.4 credits.** Call your chosen arm twice, at 30 days and 90 days,
and compare the recent rate against the trailing rate: `rate_30 = c30`, `rate_prior = c90 / 3`.
Measured: 332 versus 919/3 = 306.3, so **+8.4%**. Company-wide, longitudinal, and cheap.

**The dedicated change-rate arm — 8 credits per unit.** `lusha-enrich-company-jobs-growth-by-
department-signal` ships `newJobsPostedLast4Weeks`, `historicalAvg` and `changeRatePercent`
per department. Measured on the same company: 121 against a historical average of 108, giving
+12% for its largest department — arithmetically consistent, and directionally agreeing with the
0.4-credit method while measuring a different thing (one department, and a window ending earlier).

What the 8 credits actually buys is **`historicalAvg`** — the company's own trailing baseline, per
department. The rate itself is arithmetic on two numbers in the same payload. So pay for it when
you need the baseline *split by department*, and use two windows when company-wide will do.

**Read the per-unit rate off the input schema, not the cost field.** The catalog reports
`creditCost: 8` for all four Lusha growth arms. Three of them are charged **per result found**,
and the only place that is stated is a parameter description on `maxResultsPerSignal`: *"You will
be charged 8 credits per department found."* Its default is 3 (**24 credits**) and its maximum is
100 (**800 credits for one company**). A build priced off the catalog field understates by up to
100×. Always pass this parameter explicitly; never let it default.

**Two freshness traps on the change-rate arm.** Its `signalDate` was 18 days before the day it was
called, so "last 4 weeks" is four weeks ending at `signalDate`, not ending today — carry
`signalDate` into the output or you will misdate the evidence. And because that date moves in
steps, consecutive weekly runs can return an identical signal; a radar that diffs runs must diff
on `signalDate`, not on the day it ran.

## Step 5 — Verdicts: measurement status first, then the read

Two verdicts at two granularities, and the second is only emitted when the first is `measured`.
Reporting "accelerating" off a lower bound is the error this split prevents.

**Part A — measurement status, in precedence order. The first that applies wins.**

1. `arm_mismatch` — the payload's own returned identity disagrees with the anchor. Compare the
   returned `company_domain` and company name against what you asked for, from the same response,
   before consuming any count. Free, and a domain is a join hint rather than an identity.
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
On the probed company, two windows gave +8.4% and the dedicated arm gave +12%: two defensible
measurements of "is hiring accelerating" that differ by 3.6 points. A band tighter than the gap
between methods reports method choice as signal. The user may tighten it — say what that costs
them in false positives when they do.

## Step 6 — Emit the number with its measurement attached

Per account: the count, the object counted, the window, the dimension and its arm, Part A, Part B,
the baseline figures behind Part B, and the evidence (one or two posting titles with URLs and dates).

Never emit a bare count. `"47"` is unusable by the next reader; `"47 postings, last 30 days,
Director+ seniority, CPJ, measured, +31% vs trailing 90d"` survives being pasted into a
spreadsheet, compared against another account, and re-run next week.

Report cohort-level spend, and subtract refunded misses: an arm that finds nothing returns
`status: SUCCESS_NO_DATA` with `isRefunded: true` and is free, so summing the upfront cost
overstates what a book with dead rows actually cost.

## What this skill does not claim

- Five arms verified live against one company on one day; no cohort run, so how often an account turns out to be unmeasurable is unknown.
- The 65% false-negative figure is arithmetic on one measured prevalence, not an observed miss rate.
- One arm's jobs-versus-people output contradiction is unresolved — its probe was blocked by a daily cap.

## What good looks like

- Every count in the output carries its window and its object; no bare "job count" anywhere.
- One arm per cohort, named, with the accounts it did not cover listed as `unmeasured`.
- The dimension the user asked about is a filter on the arm chosen — or the number is marked
  `lower_bound_only` and excluded from the ranking.
- A baseline exists for every account reported `accelerating` or `decelerating`, with both figures.
- Per-unit arms are priced at the unit count actually passed, not at the catalog's cost field.
- The common failure: pulling `totalJobsFound` with no date filter, seeing today's postings at the
  top of the page, and reporting an all-time total as current hiring. Second-worst: post-filtering
  a 20-row page for a 2%-prevalence dimension and reporting the zero as "not hiring".

## Rules

- MUST declare object, window and dimension before the first call, and carry all three into the
  output; NEVER emit a count without its window.
- MUST pass an explicit date-window parameter on every counting call; NEVER rely on the arm's
  default, which is unbounded on every counting arm probed.
- MUST route the count to an arm where the requested dimension is a filter; NEVER post-filter a
  capped page and report the result as a count — mark it `lower_bound_only` or re-route.
- MUST use one arm for a whole cohort and mark uncovered accounts `unmeasured`; NEVER waterfall
  the count across arms, and never treat a coverage miss as a zero.
- MUST obtain a baseline before reporting acceleration, and emit both figures; NEVER report a
  level as a trend.
- MUST read per-unit credit rates from the input parameter descriptions and pass unit-count
  parameters explicitly; NEVER price an arm from the catalog's cost field alone.
- MUST check the payload's own returned company identity against the anchor before using any
  count from it.
- MUST carry the provider's own signal date when an arm supplies one, and diff runs on that date
  rather than on the run date.
- NEVER report a percentage change on a current-window count below 10.
- NEVER rank, threshold or trend on a `lower_bound_only` count.

## Worked example

Asked: *"which of these 200 accounts are staffing up their sales org, and who's accelerating?"*

Declared measurement: **posting events, 30-day window, department dimension = sales.** The
department dimension routes to PredictLeads (`categories`) at 1 credit — the only probed arm on
which department is a filter. TheirStack would be five times cheaper and would force
`lower_bound_only` on every row, so the routing is worth the 0.8 credit difference: 200 rows at
1 credit is 200 credits, against 40 credits for numbers that cannot be ranked.

Baseline by the two-window method on the same arm, so 400 calls, 400 credits total. Delivered:

| Account | Count (30d, sales) | Trailing (90d/3) | Part A | Part B |
|---|---|---|---|---|
| A | 34 | 18.7 | measured | **accelerating** (+82%) |
| B | 12 | 11.3 | measured | flat (+6%) |
| C | 6 | 4.0 | measured | level_only (below 10) |
| D | 0 | 0 | measured | no_open_roles |
| E | — | — | unmeasured | — (arm returned no coverage) |
| F | ≥3 | — | lower_bound_only | — (seniority sub-filter, post-filtered) |

Row F shows the trap in miniature. The user also wanted "director+ in sales", which is a *second*
dimension: seniority filters only on CPJ, department only on PredictLeads, and no probed arm
filters both. So the honest deliverable is two cohorts measured separately, or one cohort with the
second dimension carried as a lower bound and excluded from the ranking — not one number that
quietly satisfies neither.

Stated at the top of the delivery, not buried: *counts are posting events over the 30 days ending
today, measured on one arm; the four `unmeasured` accounts are not zeros; row F's figure is a
floor, not a count.*
