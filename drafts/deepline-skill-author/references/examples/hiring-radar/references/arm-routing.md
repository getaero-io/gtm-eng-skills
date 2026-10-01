# Hiring arms — what each one accepts, returns, and counts

> Measured on Clay's action catalogue, 2026-08. Arm keys, field paths and credit figures below are
> Clay facts, kept as evidence for the example's reasoning; resolve Deepline equivalents with
> `deepline tools search` / `describe` before reusing any of them.

Probed live **2026-08-14**, one company, one day.
Costs are each call's own `metadata.upfrontCreditUsage.totalCost`. **Re-pull the input schemas at
the start of every build** — the parameter drift documented at the bottom of this page is the
reason, and it cost a recipe three of its four filters.

Identify every arm by `(packageId, actionKey)`. Keys collide across packages.

## The counting arms

| Arm | packageId | Cost | Count field | Page cap | Truncation signal |
|---|---|---|---|---|---|
| `theirstack-find-jobs` | `d2b33e01-…` | **0.2** | `totalJobsFound` | 20 (default 10) | `totalJobsReturned` beside it |
| `cpj-find-lists-of-jobs` | `e251a70e-…` | 1 | `jobCount` | 10, or **500** with `identifiers_only` | compute from `limit` |
| `predict-leads-get-job-openings-for-company-v3` | `aa68bb13-…` | 1 | `total_job_count` | unstated, no `limit` param | `more_matches_than_we_can_display` boolean |
| `leadmagic-find-jobs` | `edb58209-…` | 2 | `total_count` | unstated, no `limit` param | **none** |

`leadmagic-find-jobs` is the one arm with no way to tell whether its array is complete: no `limit`
to reason from and no truncation flag. It is also the dearest of the four. Not probed.

## One company, one day, five numbers

| Call | Result |
|---|---|
| TheirStack, no filters | `totalJobsFound` **8,945** |
| TheirStack, `job_titles: "Engineer"` | `totalJobsFound` **3,136** |
| TheirStack, `days_since_posted: 30` | `totalJobsFound` **332** |
| TheirStack, `days_since_posted: 90` | `totalJobsFound` **919** |
| CPJ, no filters | `jobCount` **737** |
| CPJ, `seniority: ["Director"]` + 30 days | `jobCount` **7** |
| PredictLeads, no filters | `total_job_count` **384**, `more_matches_than_we_can_display: true` |
| TheirStack `company_object.num_jobs` (free rider) | **8,580** |
| TheirStack `company_object.num_jobs_last_30_days` (free rider) | **332** |

Three findings are load-bearing.

**Totals are filter-scoped, in both directions and on both arms tested.** 8,945 → 3,136 on a title
filter; 737 → 7 on a seniority filter plus a window. So a filterable dimension gives an exact
count, not a sample.

**Page size does not move the total.** `limit: 1` and `limit: 10` returned identical
`totalJobsFound` for the same query. The count is population-scoped within the filter; only the
array shrinks.

**The 30-day total is independently corroborated inside the same payload.** TheirStack's windowed
`totalJobsFound` (332) equals its own `company_object.num_jobs_last_30_days` (332), which arrives
free and unasked. Two paths to one number, agreeing — which also proves the unwindowed 8,945 is
not a current figure.

## Window defaults are unbounded, and dates are not comparable across arms

No counting arm applies a default date window. The unwindowed and 30-day totals differ by **27×**
on the same arm and company (8,945 vs 332), and every arm returns its page newest-first, so the
sample looks current regardless.

Date fields differ in kind, which matters when you try to window client-side:

| Arm | Posting date | Notes |
|---|---|---|
| TheirStack | `date_posted`, plus `discovered_at`, `date_reposted`, `closed_at` | fully dated; `reposted` flag present |
| CPJ | `posted_at`, plus `closed_at` | probed row was posted 9 months earlier with a future `closed_at` — long-open reqs are counted |
| PredictLeads | **`posted_at` was null on all 10 rows** — only `first_seen_at` / `last_seen_at` | first-seen is when the provider saw it, not when it was posted |

So on PredictLeads you cannot compute a posting age from the payload. Its `days_since_posted`
filter must be trusted on the provider's own terms, and a client-side window is not available as a
cross-check.

## Filterability — the routing table

A dimension is only countable on an arm that filters it. `✓` = accepted as an input filter,
`out` = present in the output but **not** filterable, `—` = absent.

| Dimension | TheirStack | CPJ | PredictLeads | LeadMagic |
|---|---|---|---|---|
| title keywords | ✓ | ✓ | ✓ | ✓ |
| description keywords | ✓ | ✓ | ✓ | ✓ |
| location | ✓ | ✓ | partial (`with_location_only`) | ✓ |
| date window | ✓ (3 params) | ✓ (2 params) | ✓ | ✓ |
| employment type | ✓ | ✓ | out | ✓ |
| **seniority** | **out** | **✓** | **out** | `experience_level` |
| **department / function** | **—** | **out** (`functions`) | **✓** (`categories`) | — |
| technology in posting | **✓** (`technologies_used`) | — | — | — |
| recruiter listed | ✓ | ✓ | — | — |
| company size | — | — | — | ✓ (`min/max_employees`) |

The two cells that decide most builds: **seniority filters only on CPJ**, and **department filters
only on PredictLeads**. Both are *observable* on other arms, which is the trap — the field is in
the payload, so it looks filterable, and post-filtering it turns an exact count into a biased one.

### The post-filter bias, measured

Director-level roles were **7 of 332** postings in the 30-day window — a true prevalence of 2.1%.
TheirStack has no seniority filter and caps its page at 20 rows, so a seniority read taken off that
page misses every one of them with probability `(1 − 0.021)^20` ≈ **65%**.

Generally: `P(false negative) ≈ (1 − p)^c` for prevalence `p` and page cap `c`. For any dimension
rarer than about 10% of a company's book, a 20-row page misses it more often than it finds it. The
approximation treats the dimension as uncorrelated with recency; the page is newest-first, so a
dimension that spiked this week is easier to detect and still not countable.

## Seniority and department have five vocabularies

| Surface | Values observed |
|---|---|
| CPJ `seniority` **input** (closed, 7) | `Internship, Entry level, Associate, Mid-Senior level, Director, Executive, Not Applicable` |
| TheirStack `seniority` output | `senior, staff, mid_level` (snake_case) |
| PredictLeads `seniority` output | `mid_senior, manager` (snake_case) |
| PredictLeads `categories` in/out | `human_resources, sales, information_technology, product_management, data_analysis, management, support, marketing, operations` (snake_case) |
| CPJ `functions` output | `Engineering, Information Technology` (Title Case) |
| Lusha `department` output | `Information Technology` (Title Case) |

**There is no `VP` tier anywhere in CPJ's closed input set.** "Director and above" is expressible
only as `["Director", "Executive"]`, and `Executive` also carries the C-suite — so the common GTM
ask "director+ but not C-level" cannot be filtered, only post-filtered. Say so rather than
approximating it silently.

## The baseline arms

`lusha-enrich-company-jobs-growth-by-department-signal` (`f8a143aa-…`), probed with
`maxResultsPerSignal: 1`, cost **8**:

```
department:              "Information Technology"
signalDate:              "2026-07-27"      <- 18 days before the call
newJobsPostedLast4Weeks: 121
historicalAvg:           108
changeRatePercent:       12                <- 121/108 = +12.0%, internally consistent
```

`changeRatePercent` is derived from the two counts shipped beside it, so it corroborates nothing —
what the credits buy is **`historicalAvg`**, the company's own trailing baseline, split by
department. That is the only thing here you cannot compute from a 0.2-credit call.

**`signalDate` trailed the call date by 18 days.** "Last 4 weeks" ends at `signalDate`, not today.
Carry it into the output, and diff scheduled runs on `signalDate` rather than on the run date —
otherwise a stepwise-updating signal reads as "no change" for weeks and then jumps.

### Per-unit pricing is stated only in a parameter description

All four Lusha growth arms report `creditCost: 8` in the catalog. Three are charged per result:

| Arm | Billing basis (from the arm's own description) |
|---|---|
| `…-jobs-growth-by-department-signal` | "8 credits **per department found**" — default 3, max 100 |
| `…-jobs-growth-by-location-signal` | "8 credits **per location found**" |
| `…-headcount-growth-signal` | "8 credits **per headcount growth signal found**" |
| `…-jobs-growth-signal` | **silent** — no basis stated either way |

Default `maxResultsPerSignal: 3` means the by-department arm bills **24 credits**, and its maximum
of 100 means **800 credits for one company**. The catalog's cost field cannot distinguish these
from a flat 8. Pull the input schema and pass the unit-count parameter explicitly.

The fourth arm stating no basis is not evidence that it is flat. Treat an unstated basis as
unknown, bound it with an explicit unit parameter if it has one, and probe before committing a book.

### The cheap substitute

Two windows on the chosen counting arm, **0.4 credits total**:

```
rate_recent   = count(days_since_posted = 30)          -> 332
rate_trailing = count(days_since_posted = 90) / 3      -> 919 / 3 = 306.3
change        = (332 - 306.3) / 306.3                  -> +8.4%
```

Against the dedicated arm's +12% for its largest department, over a window ending 18 days earlier.
Same direction, different quantities — this is a directional cross-check, not a validation, and the
two must not be quoted as one number. What you give up is the per-department split.

## Free riders in the TheirStack payload

One 0.2-credit call embeds a `company_object` on every returned job:

`num_jobs`, `num_jobs_last_30_days`, `employee_count`, `employee_count_range`, `industry`,
`founded_year`, `country`, `city`, `funding_stage`, `last_funding_round_date`,
`annual_revenue_usd`, `publicly_traded_symbol`, `linkedin_url`, `linkedin_id`, `apollo_id`,
`num_technologies`, `technology_slugs` (**524 entries** on the probed company), `company_tags`,
`is_recruiting_agency`, `yc_batch`.

So the counting pass doubles as a firmographic read and a rough technographic one, and
`employee_count` is exactly what you need to normalise a count by company size.

Two cautions. **`company_object` is nested inside each job, so a query returning zero jobs returns
no `company_object`** — the free 30-day count is unavailable precisely when the filtered count is
zero, which is when you would most want a denominator. Run the unfiltered or wider-window call if
you need it. And `num_buying_intent_topics` returned **−524**, the exact negation of
`num_technologies: 524`; a negative count is not a measurement, so ignore that field.

Tech-stack detection off `technology_slugs` is `detect-tech-stack`'s job, not this skill's — the
slugs are a by-product here, unversioned and undated.

## Not probed

| Arm | Cost | Why it is listed anyway |
|---|---|---|
| `pubrio-find-open-jobs-at-company` (`fd621cb7-…`) | 6 | **Declared output is `peoples[]`** — name, first/last name, title, employment history, LinkedIn URL — while the action is named "find open jobs at company", its description says "a maximum of 25 jobs will be returned", and its inputs are job-shaped (`job_title`, `posted_after`). Name, description, inputs and declared output do not agree about the entity returned. It sits in the tail of the waterfall this pattern is usually built with, so a builder following that advice will reach it. **Unverified** — the probe was blocked by the daily test-run cap. Treat the contradiction as a reason to probe before use, not as a measurement. |
| `pdl-enrich-company-job-post-insights` (`78593846-…`) | 10 | Declares only `active_job_postings` and `deactivated_job_postings` — no postings array, so no evidence line and no dimension filtering. 50× TheirStack's price for a narrower answer. |
| `leadmagic-find-jobs` | 2 | No `limit`, no truncation flag; its `country_id` / `region_id` / `job_type_id` / `company_industry_id` filters are opaque numeric ids with no vocabulary in the schema. |
| `enrich-job` (`e251a70e-…`) | undeclared | Takes a job id and enriches one posting. Useful for deepening evidence on a specific req after a counting pass; irrelevant to counting. `creditCost` absent from the catalog. |

## Parameter drift — why step 0 pulls the schema

A widely used recipe for the CPJ arm names four filter parameters. Checked against the live
schema on 2026-08-14:

| Recipe parameter | Live status |
|---|---|
| `job_title_seniority_levels: ["director","vp"]` | **renamed** to `seniority`, and the closed set has no `vp` value |
| `job_functions: ["Accounting","Finance"]` | **does not exist** on this arm — function is output-only |
| `job_title_exact_keyword_match: true` | **does not exist** |
| `posted_max_days_ago: 60` | **renamed** to `max_num_days_since_posted` |

The recipe's architecture is "three filter layers, all must match: title, seniority, function".
Two of those three layers are not buildable on this arm today, so the recipe silently degrades to
a title-keyword search — which returns a number, from a call that succeeds, with no error anywhere.
That is the whole argument for pulling the schema at step 0 instead of trusting any written recipe,
including this page.
