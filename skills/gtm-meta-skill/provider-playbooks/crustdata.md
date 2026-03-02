Use CrustData for structured discovery and enrichment with recall-first filtering.

- Start with free autocomplete (`companydb_autocomplete`, `persondb_autocomplete`) to discover canonical values.
- Default to fuzzy contains operator `(.)`; use strict `[.]` only when explicitly requested.
- Use `crustdata_companydb_search` as the resolver step; for `crustdata_enrich_company`, prefer domain-based inputs instead of name-only payloads.
- In changed-company email recovery, use Crust as the second step after LeadMagic and before PDL.
- Keep filters composable and inspect a small sample before adding expensive enrichments.
- If Crust misses in the first 10 rows for a batch, move it later for the rest of that batch.

### Filter format

`filters` accepts an array of condition objects (AND-combined automatically). Each condition: `{"filter_type":"<field>","type":"<operator>","value":"<val>"}` or `{"filter_name":"<field>","type":"<operator>","value":"<val>"}`. `filter_name` is syntactic sugar for `filter_type`; human-friendly aliases (e.g. `company_investors` → `crunchbase_investors`, `company_funding_stage` → `last_funding_round_type`) are auto-mapped. A single condition object (not in array) also works.

**Company filter_type values:** `company_name`, `company_website_domain`, `linkedin_industries`, `hq_country`, `hq_location`, `region`, `year_founded`, `employee_metrics.latest_count`, `employee_count_range`, `employee_metrics.growth_6m_percent`, `employee_metrics.growth_12m_percent`, `employee_metrics.growth_12m`, `follower_metrics.latest_count`, `follower_metrics.growth_6m_percent`, `crunchbase_investors`, `tracxn_investors`, `crunchbase_categories`, `crunchbase_total_investment_usd`, `last_funding_date`, `last_funding_round_type`, `estimated_revenue_lower_bound_usd`, `estimated_revenue_higher_bound_usd`, `linkedin_id`, `linkedin_profile_url`, `company_type`, `acquisition_status`, `ipo_date`, `largest_headcount_country`, `markets`, `competitor_ids`, `competitor_websites`.

**Person filter_type values:** `current_employers.company_website_domain`, `current_employers.title`, `current_employers.seniority_level`, `headline`, `region`, `num_of_connections`, `years_of_experience_raw`.

**Operators:** `(.)` = fuzzy contains (default), `[.]` = substring, `=`, `!=`, `in`, `not_in`, `>`, `<`, `=>`, `=<`. Person search also supports `geo_distance` for `region`.

### Examples

```bash
deepline tools execute crustdata_companydb_autocomplete --payload '{"field":"linkedin_industries","query":"software","limit":5}' --json
```

```bash
deepline tools execute crustdata_companydb_search --payload '{"filters":[{"filter_type":"linkedin_industries","type":"(.)","value":"software"},{"filter_type":"hq_country","type":"=","value":"USA"}],"limit":5}' --json
```

```bash
deepline enrich --input accounts.csv --output accounts.csv.out.csv --with 'company_lookup=crustdata_companydb_autocomplete:{"field":"company_name","query":"{{Company}}","limit":1}' --json
```
