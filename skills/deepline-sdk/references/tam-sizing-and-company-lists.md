# TAM Sizing and Company Lists

Use this when the user asks to size a market, build an account list, find companies by ICP, qualify hiring/growth, or produce a company-only CSV. The expensive failure is enriching contacts at the wrong accounts.

## Count-First TAM

Use when the user asks "how many", "pull N", "size TAM", or gives a large target. Prefer a count endpoint. Otherwise run the likely retrieval with `limit:1`, `per_page:1`, or `size:1` and read totals/shape before pulling pages.

Economic routing matters before scale. Prefer count/free/preview probes first, then result-priced providers when coverage is uncertain. If a 1-3 row/list pilot shows zero usable companies, wrong taxonomy, missing domains, or high cost per usable row, change source strategy before buying the same miss at full size.

TAM route by deliverable:

- TAM sizing only: count/limit-1 first, then return estimate, assumptions, filter definitions, confidence, and provider caveats. Do not build/export rows unless asked.
- TAM list build: structured company discovery prebuilt first; bootstrap `company-list` when filters/evidence/export columns need edits.
- TAM plus contacts: confirm company source first, then use the contacts/personas doc; cap people/account.
- TAM plus automation: prove the batch route first, then add cron/webhook/API wrapper.

Counts are gates for source choice, page count, and fanout, not deliverables.

## Source Choice

| Source shape | Route | Why |
| --- | --- | --- |
| Official portfolio, accelerator, conference, partner directory, registry, filing | Extract source URL directly, then enrich | Official source beats provider reconstruction |
| Crisp ICP: funding, headcount, HQ, exact category, stage | Structured company discovery | Stable filters and useful firmographics |
| Fuzzy niche category, pain language, market concept | Semantic/web account seed, then evidence scoring | Taxonomies may be empty or broad |
| Known company/domain list | Company-to-contact route | Avoid broad people search drift |
| Known people/contact rows | People email/phone/LinkedIn route | This is enrichment, not discovery |
| Hiring-qualified accounts | Company seed first, then hiring evidence | Hiring is a qualification layer |
| Local SMB / maps-style ask | Maps/local source route, then website/domain validation | Generic B2B providers under-cover local businesses |

Known-source rule: if you have the URL, fetch/extract it. Search only to find the URL. For JS-rendered pages, directories, LinkedIn/Reddit/X/platform pages, use source-specific extractors/actors and keep `source_url`.

## Scout Before Scale

For hard account-list asks, do not build a large custom play around the first source that returns 100 rows.

1. Probe 2-3 plausible company sources with 3-10 row limits.
2. Normalize source rows to `company_name`, `domain`, category, `company_fit_evidence`, `source`, and `miss_reason`.
3. Compare company quality, domain quality, category evidence, geographic fit, duplicate rate, cost, and billing shape.
4. Reject broad taxonomy noise before contact fanout.
5. Bootstrap/scale the winning route.

If source A gives 100 companies but the rows are org units, directories, missing root domains, sentinel headcount values, or weak evidence, source A is not validated.

## Structured Company Search

Default fields to preserve: `company_name`, `domain`, `headcount`, `funding_round`, `hq_country`, `category`/`<vertical>_category`, `company_fit_evidence`, `source`, `status`, `miss_reason`.

CrustData/company-search scar tissue:

- `hq_country` uses ISO-3 codes such as `USA`, `GBR`, `DEU`, `FRA`, `NLD`; full names can silently return zero.
- Autocomplete canonical filter values before scale, especially `crunchbase_categories`, `linkedin_industries`, and `last_funding_round_type`.
- For niche verticals, prefer specific categories such as Fraud Detection or Identity Management over broad LinkedIn industries.
- `employee_count_range` is the filter; `employee_metrics.latest_count` is useful for sorting/output.
- Search responses already include headcount, funding, HQ, categories, and growth. Extract them; do not re-enrich facts already returned.
- Positive `employee_metrics.growth_6m_percent` is a free hiring proxy before paid job listings.

Provider taxonomy is not enough. A healthcare list needs `healthcare_category`; fintech needs `fintech_category`; otherwise use `category`. Include evidence text or URL so the user can audit why it belongs.

## Healthcare Company Lists

Healthcare company asks are source-quality traps. Do not source by broad `hospital & health care` and sort by employee count. That yields giant systems, org units, weak domains, and poor contact coverage.

Good seed strategy:

- Prefer credible healthcare providers, care delivery, digital health, healthtech, clinical operations/informatics companies, provider groups, and health systems with root company domains.
- Exclude universities, foundations, government agencies, departments/divisions, directories, URL shorteners, and non-company domains unless fit evidence is explicit.
- Avoid seed lists dominated by `employee_count=10001`; mix company sizes and categories.
- Export `healthcare_category` such as `health_system`, `provider_group`, `digital_health`, `healthtech`, `medical_device`, `clinical_informatics`, `care_delivery`, or `payer`.

## Hiring-Qualified Companies

Use hiring when the user asks for companies hiring a role or with demand for a function.

1. Source companies from a known list or structured/semantic search.
2. Qualify with hiring evidence: job listings, careers pages, Exa/Serper scoped search, or growth proxy.
3. Filter/score hiring evidence before people lookup.
4. Preserve `hiring_evidence`, `hiring_source_url`, and `hiring_status`.

CrustData job listings can batch known domains but may be spotty for smaller companies and often lacks server-side title filtering; filter client-side. Public web search with scoped domains is better for role-specific evidence when provider coverage is thin.

## Geography

Geography fields vary by provider. Company HQ filters may require ISO-3 while people geography in the same workflow may use full country names.

- Validate enum-like geography with autocomplete or a `limit:1` pilot before scale.
- Serper defaults skew US/English; make Europe/non-US intent explicit in query and locale fields when available.
- Prefer domain/apex matching over fuzzy company names.
- Handle multi-label suffixes: `co.uk`, `org.uk`, `ac.uk`, `co.it`, `co.es`, `com.es`, plus APAC/LATAM local suffixes.
