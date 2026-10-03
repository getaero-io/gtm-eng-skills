Use CrustData for structured discovery and enrichment with recall-first filtering.

- Start with free autocomplete (`crustdata_v3_company_search_autocomplete`, `crustdata_v3_person_search_autocomplete`) to discover canonical values. Confirm these hints with `deepline tools describe <tool-id> --json`.
- Preserve recall-first matching: in historical CompanyDB filters, fuzzy `(.)` was the default and strict `[.]` was only for an explicit substring request. V3 uses `contains`; confirm its semantics and current field vocabulary rather than forwarding old operators.
- Use `crustdata_v3_company_search` as the resolver step; for `crustdata_v3_company_enrich`, prefer domain-based inputs instead of name-only payloads. Check each input schema before converting older company filters.
- For job data, use `crustdata_v3_job_search` for indexed listings or `crustdata_v2_live_job_search` when freshness is required for a known CrustData company id. Legacy job-listing compatibility actions are hidden from discovery and should not be selected for new workflows.
- In changed-company email recovery, use Crust as the second step after LeadMagic and before PDL.
- Keep filters composable and inspect a small sample before adding expensive enrichments.
- If Crust misses in the first 10 rows for a batch, move it later for the rest of that batch.

### Historical CompanyDB / PersonDB filter knowledge

Keep this vocabulary when interpreting existing payloads and results; it is not a
V3 input template. New V3 searches take a `filters` group with `op` and
`conditions`, whose leaves use `field`, `type`, and `value`. Discover the current
field paths and operators with `deepline tools describe <tool-id> --json` before
translating. Do not blindly rename tools while keeping these older filters.

`filters` accepts an array of condition objects (AND-combined automatically). Each condition: `{"filter_type":"<field>","type":"<operator>","value":"<val>"}` or `{"filter_name":"<field>","type":"<operator>","value":"<val>"}`. `filter_name` is syntactic sugar for `filter_type`; human-friendly aliases (e.g. `company_investors` → `crunchbase_investors`, `company_funding_stage` → `last_funding_round_type`) are auto-mapped. A single condition object (not in array) also works.

**Company filter_type values:** `company_name`, `company_website_domain`, `linkedin_industries`, `hq_country`, `hq_location`, `region`, `year_founded`, `employee_metrics.latest_count`, `employee_count_range`, `employee_metrics.growth_6m_percent`, `employee_metrics.growth_12m_percent`, `employee_metrics.growth_12m`, `follower_metrics.latest_count`, `follower_metrics.growth_6m_percent`, `crunchbase_investors`, `tracxn_investors`, `crunchbase_categories`, `crunchbase_total_investment_usd`, `last_funding_date`, `last_funding_round_type`, `estimated_revenue_lower_bound_usd`, `estimated_revenue_higher_bound_usd`, `linkedin_id`, `linkedin_profile_url`, `company_type`, `acquisition_status`, `ipo_date`, `largest_headcount_country`, `markets`, `competitor_ids`, `competitor_websites`.

**Person filter_type values:** `current_employers.company_website_domain`, `current_employers.title`, `current_employers.seniority_level`, `headline`, `region`, `num_of_connections`, `years_of_experience_raw`.

**Operators:** `(.)` = fuzzy contains (default), `[.]` = substring, `=`, `!=`, `in`, `not_in`, `>`, `<`, `=>`, `=<`. Person search also supports `geo_distance` for `region`.

**Range filtering:** There is NO range operator like `[100..500]` or `between`. To filter a numeric range, use TWO separate filter conditions with `>` and `<` (or `=>` and `=<`):

```json
[
  {
    "filter_type": "employee_metrics.latest_count",
    "type": ">",
    "value": "100"
  },
  {
    "filter_type": "employee_metrics.latest_count",
    "type": "<",
    "value": "500"
  }
]
```

**Headcount filtering:** For headcount, prefer `employee_count_range` (string enum like `"51-200"`, `"201-500"`) with the `in` operator when exact buckets work. Use `employee_metrics.latest_count` with `>` / `<` only when you need precise numeric boundaries. Note: `employee_metrics.latest_count` is valid for `sorts` and `filters`, but `employee_count_range` uses string enum values.

### Examples

```bash
deepline tools execute crustdata_v3_company_search_autocomplete --input '{"field":"taxonomy.professional_network_industry","query":"software","limit":5}'
```

Historical search payload for interpreting existing CompanyDB work (not a V3
execution example). It combines recall-first software-industry matching with an
exact US HQ filter. Resolve current V3 field/value equivalents through discovery:

```json
{"filters":[{"filter_type":"linkedin_industries","type":"(.)","value":"software"},{"filter_type":"hq_country","type":"=","value":"USA"}],"limit":5}
```

For CSV company-name lookup, use a supplied Play if it fits. Otherwise discover
with `deepline plays search company --json` and inspect the selected contract with
`deepline plays describe <play-ref> --json`. Confirm the tool hint below with
`deepline tools describe crustdata_v3_company_search_autocomplete --json`; autocomplete
does not replace the company-search resolver or the domain-first enrichment policy.

Save this custom workflow as `company-lookup.play.ts`:

```ts
import { definePlay } from 'deepline';

export default definePlay(
  'company-lookup',
  async (ctx, input: { csv: string }) => {
    const accounts = await ctx.csv(input.csv, { required: ['Company'] });
    const rows = await ctx.dataset('accounts', accounts)
      .withColumn('company_lookup', (row, rowCtx) => rowCtx.tools.execute({
        id: 'company_lookup',
        tool: 'crustdata_v3_company_search_autocomplete',
        input: { field: 'basic_info.name', query: row.Company, limit: 1 },
        description: 'Look up the canonical company-name candidate.',
      }))
      .run({});
    return { rows };
  },
  { description: 'Look up company names from the supplied accounts CSV.' },
);
```

```bash
deepline plays check company-lookup.play.ts --json
deepline plays run --file company-lookup.play.ts --csv accounts.csv --watch
```

V3's `basic_info.name` replaces the historical autocomplete field `company_name`;
the query still comes from `Company` and `limit` remains 1. Autocomplete declares
no semantic getters, so retain its full tool response as evidence instead of
inventing an `extractedValues` accessor.

Keep the input columns and lookup evidence. For larger or uncertain authorized
work, inspect a small representative input before scaling; do not add pilot runs
or repeat approval for a small supplied Play. Use
`deepline runs get <run-id> --json` and its full-result/export commands to retrieve
existing rows into `accounts.csv.out.csv`. A request to inspect results does not
authorize another run, paid fallback, or repair.
