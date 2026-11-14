# Field vocabulary — what the two axes actually accept

Read from `deepline tools describe crustdata_v3_company_search --json` and
`deepline tools describe crustdata_v3_person_search --json` on **2026-09-30**. Free metadata; no
credits and no search rows. Allowed VALUES come from the free autocomplete tools
(`crustdata_v3_company_search_autocomplete`, `crustdata_v3_person_search_autocomplete`). **Re-pull
at the start of every build** — allowed-value sets are the whole point of this skill and they are
not stable enough to recite.

## The vocabulary gap, measured (on Clay's taxonomy, 2026-08)

These numbers were measured on Clay's search taxonomy, not CrustData's. They are kept because the
shape of the gap is provider-neutral; re-measure on `basic_info.industries` with autocomplete
before quoting a number.

Clay's industry taxonomy had **457 closed values**. **6 of 25 common GTM industry terms existed as
values — a 24% hit rate:**

| Present | Absent |
|---|---|
| `Manufacturing`, `Insurance`, `Retail`, `Real Estate`, `Education`, `Hospitality` | `SaaS`, `B2B`, `B2C`, `Fintech`, `Healthcare`, `Cybersecurity`, `Software`, `MarTech`, `HR Tech`, `E-commerce`, `Logistics`, `Legal`, `Media`, `Gaming`, `Biotech`, `Telecom`, `Energy`, `Nonprofit`, `Government` |

The shape of the mismatch: only 11% of that taxonomy (52 of 457) was a single word. Industry
taxonomies are compound-phrase shaped — `Embedded Software Products`,
`Transportation, Logistics, Supply Chain and Storage` — while GTM vocabulary is single-word shaped.
Two distinct failures follow, on any taxonomy:

- **Concept absent.** `SaaS`, `B2B`, `Fintech` have no representation at all.
- **Word-form mismatch.** `Biotech` misses while `Biotechnology` is a value; `Software` misses while
  `… Software …` compounds exist. The concept is there and the user's spelling is not.

**Short terms are actively dangerous with substring matching.** On Clay's taxonomy `AI`
substring-matched 53 values including `Air, Water, and Waste Program Management` and
`Airlines and Aviation`. CrustData's `(.)` operator is fuzzy text search — the same risk. Anything
under roughly five characters must be matched exactly or not at all.

## Why a translation failure is silent — in both directions

CrustData filter semantics (from the tool schema): `filters` is a condition or an `and`/`or` group
of conditions; groups nest. `in` / `not_in` take an array and OR across its values. Operators:
`=`, `!=`, `<`, `=<`, `>`, `=>`, `in`, `not_in`, `(.)` (fuzzy), `[.]` (exact token).

So an unmatched `in` value **narrows to nothing** (reads as a tiny market — and empty result pages
are free, so not even the bill flags it) and a dropped or over-fuzzy condition **restricts
nothing** (reads as a huge one). Neither errors. This is the mechanism that turns a vocabulary
problem into a false fact about the market. A `limit: 1` search returns `total_count` for 0.02
credits — check the count after each condition is added, not only at the end.

## Account axis — `crustdata_v3_company_search` filter fields

| Dimension | Fields |
|---|---|
| Identity | `basic_info.name`, `basic_info.primary_domain`, `basic_info.website`, `basic_info.professional_network_url` |
| Industry | `basic_info.industries`, `basic_info.markets`, `taxonomy.professional_network_industry`, `taxonomy.professional_network_specialities`, `taxonomy.categories` |
| Size | `basic_info.employee_count_range` (band string), `headcount.total` (integer) |
| Growth | `headcount.growth_percent.{1m,3m,6m,12m}`, `headcount.growth_absolute.{…}`, `roles.growth_6m`, `roles.growth_yoy` |
| Function size | `roles.distribution.<function>` (engineering, sales, finance, …) — filter-only |
| Revenue | `revenue.estimated.lower_bound_usd`, `revenue.estimated.upper_bound_usd`, `revenue.acquisition_status`, `revenue.public_markets.*` |
| Funding | `funding.total_investment_usd`, `funding.last_round_amount_usd`, `funding.last_fundraise_date`, `funding.last_round_type`, `funding.investors` |
| Geography | `locations.country`, `locations.headquarters`, `headcount.largest_headcount_country` |
| Type / age | `basic_info.company_type`, `basic_info.year_founded` |
| Tech | `technographics.technologies.name`, `technographics.technologies.category`, `technographics.top_technologies` |
| Lookalike | `competitors.company_ids`, `competitors.websites` (filter-only) |

Autocomplete covers most of these, including `basic_info.industries`,
`basic_info.employee_count_range`, `funding.last_round_type`, `funding.investors`,
`locations.country`, `taxonomy.categories`. Response groups (`fields`) are a different vocabulary
from filter fields: request `basic_info`, `headcount`, `funding`, `locations`, `taxonomy`, never a
leaf like `headcount.growth_percent.6m`.

## Persona axis — `crustdata_v3_person_search` filter fields

| Dimension | Fields |
|---|---|
| Title | `experience.employment_details.current.title`, `basic_profile.normalized_title.matched_title`, `.department`, `.sub_department` |
| Seniority / function | `experience.employment_details.current.seniority_level`, `experience.employment_details.current.function_category` |
| Employer | `…current.company_name`, `…current.company_website_domain`, `…current.company_id`, `…current.company_industries`, `…current.company_type` |
| Employer size | `…current.company_headcount_range` (band string), `…current.company_headcount_latest` (integer) |
| Tenure | `…current.start_date`, `…current.years_at_company_raw` |
| Past employers | the `experience.employment_details.past.*` family |
| Geography | `basic_profile.location.country`, `.state`, `.city` |
| Contact availability | `experience.employment_details.current.business_email_verified` |
| Other | `skills.professional_network_skills`, `education.schools.*`, `professional_network.connections`, `recently_changed_jobs` |

Seniority and normalized department are the persona axis's closed vocabularies — pull the
values with `crustdata_v3_person_search_autocomplete` and translate "VP or above" to an explicit
`in` list of the values at or above VP. There is no floor operator on a string enum.

## Not filters on either axis

Fortune 500 / Global 2000 membership, unicorn status, "enterprise-ready", "well-funded" (as an
adjective), "similar to our best customers" (beyond `competitors.*`), and contact addresses
themselves. Each becomes a paid per-row verify after the population exists, or nothing. This list
differs from Clay's: on Clay, funding stage and technographics were not filters; on CrustData
both are (`funding.last_round_type`, `technographics.technologies.name`) — but sparse, see below.

## ⚠ The two axes spell the same bands differently

The account axis bands company size on `basic_info.employee_count_range`; the persona axis on
`experience.employment_details.current.company_headcount_range`. They are separate fields with
separate autocomplete vocabularies. Do not assume a string from one is in the other's set — pull
both, and translate the same stated band twice. A value carried across that does not exist on the
other axis narrows to nothing, silently.

(On Clay the split was explicit: account-axis band floors `'50'` vs persona-axis labels
`'51-200'`.)

## Band alignment

Wherever size is banded, **an arbitrary numeric threshold cannot be expressed**:

- `50–2,000 employees` → the bands that overlap it. With LinkedIn-style bands (`51-200` …
  `1001-5000`) the ceiling becomes 5,000. The stated ceiling does not exist as a boundary.
- The integer alternatives (`headcount.total`, `company_headcount_latest`) take exact bounds but
  drop every record with a null count — a recall trade, not a free fix.

The rounding is always outward on the selected bands, so a band-aligned filter is **wider** than
the stated ICP, never narrower. Say by how much; the difference changes the market size before
anyone enumerates it.

Revenue is not banded on CrustData — it is an estimate range per company. `$10M ARR floor`
becomes a condition on `lower_bound_usd` (conservative) or `upper_bound_usd` (generous); name which.

## Sparse fields — where the untranslatable terms sometimes land, and what they cost

`taxonomy.categories`, `taxonomy.professional_network_specialities`, technographics, and funding
fields are where concepts like `SaaS`, `B2B`, `Fintech`, or "uses Salesforce" can sometimes be
expressed. Two cautions before relying on them:

- **Coverage is unmeasured here.** Filtering a sparse field silently excludes every unpopulated
  record — a recall filter as well as a criteria filter. Compare `total_count` with and without
  the condition (two `limit: 1` searches, 0.04 credits) and report the drop.
- **Unknown encoded as a value.** On Clay, `total_funding_amount_range_usd` returned the string
  `"Funding unknown"` rather than null (2 of 2 observed). Check how each CrustData field encodes
  missing data in the first real response before writing a band comparison against it.
