# Hiring arms — what each one accepts, returns, and counts

Two kinds of evidence on this page, kept apart:

- **Deepline contracts** — read from `deepline tools describe <id> --json` on **2026-09-30**.
  Inputs, output fields and prices are declared, not probed: no Deepline arm here has been run
  against a company yet.
- **Clay measurements** — five arms probed live on Clay on **2026-08-14**, one company, one day,
  before this skill was ported. The numbers are Clay facts; the lessons are provider-neutral.

**Re-pull the contracts at the start of every build** — the parameter drift documented at the
bottom of this page is the reason, and it cost a recipe three of its four filters.

## The Deepline counting arms

| Tool ID | Price (`pricing`) | Count field | Window fields (and which clock) | Company filter | Page |
|---|---|---|---|---|---|
| `theirstack_job_search` | 0.56 / returned job | `metadata.total_results` — only with `include_total_results: true` | `posted_at_max_age_days`, `posted_at_gte`, `posted_at_lte` (posting date); `discovered_at_max_age_days`, `discovered_at_min_age_days`, `discovered_at_gte`, `discovered_at_lte` (when TheirStack found it) | `company_domain_or`, `company_linkedin_url_or`, `company_name_or`, `company_name_case_insensitive_or`, `company_id_or` | `limit` up to 500; `metadata.truncated_results` |
| `predictleads_company_job_openings` | 0.56 / call | `meta.count` — **omitted unless `page` is passed** | `first_seen_at_from` / `_until` (first seen by PredictLeads), `last_seen_at_from` / `_until`; `active_only` (not closed, seen in last 5 days, found in last year), `not_closed` | `company_id_or_domain` (required) | `limit` default 100 |
| `sentrion_company_jobs_search` | 0.42 / returned job | `total` | `published_after`, `published_before` (posting date; standard plans hold 6 months) | `company_domain`, `company_linkedin_url`, `company_name` | `limit`, `search_after` |
| `sentrion_company_jobs_search_historical` | 0.42 / returned job | `total` | same, up to 6 years — **requires Sentrion historical access** | same | same |
| `crustdata_v3_job_search` | 0.02 / returned row; empty pages free | `total_count` (or an `aggregations` `count`) | a range condition on `metadata.date_added` / `metadata.date_updated` (indexing clock, not posting date) | `filters` on `company.basic_info.primary_domain` / `company_id` / `name` | `limit` (0 = aggregations only), `cursor` |
| `bloomberry_search_job_postings` | 0.09 / returned job | `pagination.total_items`; `show_facets: true` adds per-month counts | `begin_date` (**defaults to 2020-01-01**), `end_date`; `active_only` | `domain` | `limit`, `next_token` |
| `forager_job_search_totals` | Free | `total_search_results` | `date_featured_start`, `date_featured_end` | `organization_ids` (from the free `forager_organization_autocomplete`) | — (totals only) |
| `harvestapi_search_jobs` | 0.01 / page | `pagination.totalElements` (exact vs approximate unverified) | `postedLimit`: `24h` / `week` / `month` only | `companyId` (LinkedIn numeric id) | one LinkedIn page per charge |

Arms with **no date-window input**, so not usable as counting arms: `leadmagic_jobs_finder`
(0.34 / returned job, `total_count`, filters `job_title`, `job_description`, `experience_level`,
`location`, `company_website`) and `apollo_organization_job_postings` (free through Deepline with
your own Apollo key, `organization_id` only). Use them for evidence rows at most.

TheirStack count recipe (from the provider playbook): `include_total_results: true`, `limit: 1`,
omit `blur_company_data`. A matching count returns and bills one job; no matches bill zero. Totals
scan the whole matching dataset, so long windows can take up to two minutes.

## Filterability — the routing table (Deepline)

`✓` = accepted as an input filter, `out` = present in the output but **not** filterable, `—` =
absent from both.

| Dimension | TheirStack | PredictLeads | Sentrion | Crustdata | Bloomberry | Forager totals | HarvestAPI |
|---|---|---|---|---|---|---|---|
| title keywords | ✓ `job_title_or` / `_pattern_*` | — | ✓ `job_keywords` (title vs description scope not stated) | ✓ `job_details.title` | ✓ `normalized_job_titles` | ✓ `title` (boolean) | ✓ `search` |
| description keywords | ✓ `job_description_contains_or` / `_pattern_*` | — | ? `advanced_job_keywords` (scope not stated) | ✓ `content.description` | ✓ `keyword` | ✓ `description` | — |
| location | ✓ `job_country_code_or` | — | ✓ `jobs_locations` | ✓ `location.*` | ✓ `region_countries` | ✓ `locations` (ids) | ✓ `location` / `geoId` |
| date window | ✓ (posted + discovered) | ✓ (first/last seen) | ✓ (published) | ✓ (indexed) | ✓ | ✓ (featured) | coarse (`postedLimit`) |
| employment type | out | out | ✓ `job_type` | — | — | — | ✓ `employmentType` |
| **seniority** | ✓ `job_seniority_or` (no Director tier) | out | ✓ `seniority_level` (3 levels) | — | — | — | ✓ `experienceLevel` (incl. `director`) |
| **department / function** | — | **✓ `categories`** | **✓ `department`** | ✓ `job_details.category` | — | — | ✓ `functionId` (ids) |
| technology in posting | **✓ `job_technology_slug_or`** | — | — | — | via `keyword` full text | — | — |
| remote | ✓ `remote` | — | ✓ `is_remote` | ✓ `job_details.workplace_type` | ✓ `remote_only` | ✓ `is_remote` | ✓ `workplaceType` |

The cells that decide most builds: **Director-tier seniority filters only on HarvestAPI** (whose
window cannot reach 90 days), and **department filters on PredictLeads and Sentrion**. Sentrion is
the only arm that filters department and seniority together, at three coarse levels. Every other
seniority or department field you see in an output is *observable*, which is the trap — the field
is in the payload, so it looks filterable, and post-filtering it turns an exact count into a biased
one.

### The post-filter bias, measured (Clay, 2026-08-14)

Director-level roles were **7 of 332** postings in the 30-day window — a true prevalence of 2.1%.
A 20-row TheirStack page without a seniority filter misses every one of them with probability
`(1 − 0.021)^20` ≈ **65%**.

Generally: `P(false negative) ≈ (1 − p)^c` for prevalence `p` and page size `c`. For any dimension
rarer than about 10% of a company's book, a 20-row page misses it more often than it finds it. On
Deepline a bigger page is available on most arms, billed per row — it lowers the miss rate and it
is still a sample. The approximation treats the dimension as uncorrelated with recency; the page is
newest-first, so a dimension that spiked this week is easier to detect and still not countable.

## Seniority and department have many vocabularies

| Surface | Values (Deepline input enums unless noted) |
|---|---|
| TheirStack `job_seniority_or` | `c_level, staff, senior, junior, mid_level` (the TheirStack provider playbook lists `manager, director, vp` — the live enum does not accept them) |
| Sentrion `seniority_level` | `Entry Level, Mid Level, Executive Level` |
| HarvestAPI `experienceLevel` | `internship, entry, associate, mid-senior, director, executive` |
| `deepline_native.company_job_openings` monitor `seniorities` | `Owner, CXO, Vice President, Director, Manager, Senior, Entry, Training, Partner` |
| PredictLeads `categories` | `administration, consulting, data_analysis, design, directors, education, engineering, finance, healthcare_services, human_resources, information_technology, internship, legal, management, marketing, military_and_protective_services, operations, purchasing, product_management, quality_assurance, real_estate, research, sales, software_development, support, manual_work, food` |
| Sentrion `department` | Title Case, ~40 values incl. `Sales, Marketing, Engineering, Software Engineering, Customer Success, Finance, Human Resources, Information Technology` (read the full enum from describe) |
| Monitor `departments` | `Engineering, Sales, Marketing, Finance, Human Resources, Product Management, Operations, Customer Success, …` |

"Director and above but not C-level" is expressible as a filter only on HarvestAPI
(`experienceLevel: director`), and on the monitor (`seniorities: ["Director","Vice President"]`).
PredictLeads' `directors` is a category, not a seniority tier. Say which vocabulary a number used
rather than approximating it silently.

## The baseline

Two windows on the chosen counting arm, 2 × its count price:

```
rate_recent   = count(window = last 30 days)          -> 332   (Clay, TheirStack)
rate_trailing = count(window = last 90 days) / 3      -> 919 / 3 = 306.3
change        = (332 - 306.3) / 306.3                 -> +8.4%
```

On Deepline: TheirStack `posted_at_max_age_days: 30` then `90`; PredictLeads `first_seen_at_from`
= today − 30 d then today − 90 d (with `page: 1`); Sentrion `published_after` likewise.

`bloomberry_search_job_postings` with `show_facets: true` returns jobs per month in one call — a
trailing series rather than two points. Unprobed on Deepline.

**No Deepline tool covers the dedicated per-department growth arm used on Clay.** What it returned
(Clay `lusha-enrich-company-jobs-growth-by-department-signal`, `maxResultsPerSignal: 1`, 8 Clay
credits):

```
department:              "Information Technology"
signalDate:              "2026-07-27"      <- 18 days before the call
newJobsPostedLast4Weeks: 121
historicalAvg:           108
changeRatePercent:       12                <- 121/108 = +12.0%, internally consistent
```

`changeRatePercent` was derived from the two counts shipped beside it; what that arm sold was
`historicalAvg`, the company's own trailing baseline split by department. The Deepline substitute
is two windows on PredictLeads per `categories` value. Same direction as +8.4%, different
quantities — a directional cross-check, not a validation, and the two must not be quoted as one
number.

That arm also showed the billing-unit trap: three of four Lusha growth arms were billed per result
found, stated only in a parameter description, while the catalog cost field read a flat 8. On
Deepline, read `pricing.unit` (`call`, `result`, `page`, `usage`) for every arm.

## Free riders in the TheirStack payload

Each returned job embeds a `company_object` (declared fields): `num_jobs`, `num_jobs_found`,
`num_jobs_last_30_days`, `employee_count`, `employee_count_range`, `industry`, `founded_year`,
`country`, `city`, `funding_stage`, `last_funding_round_date`, `total_funding_usd`,
`annual_revenue_usd`, `publicly_traded_symbol`, `linkedin_url`, `linkedin_id`, `apollo_id`,
`num_technologies`, `technology_slugs`, `technology_names`, `company_tags`,
`is_recruiting_agency`, `yc_batch`, `num_buying_intent_topics`.

So the counting pass doubles as a firmographic read and a rough technographic one, and
`employee_count` is exactly what you need to normalise a count by company size.

Measured on Clay's TheirStack arm, 2026-08-14: the windowed 30-day `totalJobsFound` (332) equalled
`company_object.num_jobs_last_30_days` (332) — two paths to one number, agreeing, which also proved
the unwindowed 8,945 was not a current figure. Re-check the agreement on the first Deepline call.

Two cautions. **`company_object` is nested inside each job, so a query returning zero jobs returns
no `company_object`** — the free 30-day count is unavailable precisely when the filtered count is
zero, which is when you would most want a denominator. Run the unfiltered or wider-window call if
you need it. And on Clay `num_buying_intent_topics` returned **−524**, the exact negation of
`num_technologies: 524`; a negative count is not a measurement, so ignore that field.

Tech-stack detection off `technology_slugs` is `detect-tech-stack`'s job, not this skill's — the
slugs are a by-product here, unversioned and undated.

## Standing watch

`deepline_native.company_job_openings` — a monitor type, not a callable tool. Deploy with
`tool: deepline_native.company_radar`, payload `domain`, `radar_type: company_job_openings`, and
optional `departments`, `seniorities`, or `job_titles` (quoted terms joined with `AND` / `OR` /
`NOT`; overrides the other two), `updates_since` (≤ 90 days, a permanent boundary). 1.25 Deepline
credits per accepted finding. Events land in
`deepline_native.deepline_native_company_job_openings`. Access-gated; follow the
`deepline-monitors` skill.

## Parameter drift — why step 0 pulls the contract (Clay, 2026-08-14)

A widely used recipe for Clay's professional-network jobs arm named four filter parameters.
Checked against the live schema:

| Recipe parameter | Live status |
|---|---|
| `job_title_seniority_levels: ["director","vp"]` | **renamed** to `seniority`, and the closed set had no `vp` value |
| `job_functions: ["Accounting","Finance"]` | **did not exist** on that arm — function was output-only |
| `job_title_exact_keyword_match: true` | **did not exist** |
| `posted_max_days_ago: 60` | **renamed** to `max_num_days_since_posted` |

The recipe's architecture was "three filter layers, all must match: title, seniority, function".
Two of those three layers were not buildable, so the recipe silently degraded to a title-keyword
search — which returned a number, from a call that succeeded, with no error anywhere. The same
class of drift is visible on Deepline today (the TheirStack seniority enum vs its playbook). That
is the whole argument for running `deepline tools describe` at step 0 instead of trusting any
written recipe, including this page.
