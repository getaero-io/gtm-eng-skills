# TheirStack Agent Guidance

## Decision Framework

**Use TheirStack when:**

- You need tech-stack-driven company discovery (TheirStack's core strength)
- You need job posting data as a hiring intent signal
- You need to enrich a known company's tech stack

**Do not use TheirStack when:**

- You need to filter by MX/email provider such as Microsoft 365, Office 365, Google Workspace, or Gmail. `theirstack_company_search` has no `company_email_provider` filter. Discover an action whose current schema explicitly supports the required email-provider filter.

TheirStack has no people/contact enrichment or person database search.

## Operation Sequence

1. **Validate keyword slugs first (free):** Use `theirstack_catalog_keywords` to look up the correct keyword slug (e.g., `react`, `salesforce`, `hubspot`) before running a paid company or job search.

2. **Company discovery:** Use `theirstack_company_search` with `company_keyword_slug_or` or `company_keyword_slug_and`. For precision, use `_and`. For broad reach, use `_or`.

3. **Hiring signals:** Use `theirstack_job_search` to find companies actively hiring for specific roles or technologies. Always provide `posted_at_max_age_days` or a company filter — the API requires at least one.

4. **Count before a large search:** Use `theirstack_job_search` with `include_total_results: true` and `limit: 1`; omit `blur_company_data`. A matching count returns and bills one job at the published Deepline per-result price; no matches return and bill zero jobs. Totals require TheirStack to scan the full matching dataset, so broad filters or long date windows can take up to two minutes.

5. **Tech stack enrichment:** Use `theirstack_technographics` for a single known company — provide `company_domain` when possible (most reliable identifier).

6. **Check credits:** Use `deepline billing balance` before large batch runs.

## Key Filters

- **Keyword slugs** use kebab-case (e.g., `react`, `node-js`, `salesforce`). Use `theirstack_catalog_keywords` to find the exact slug first.
- **Field names differ by endpoint:** `theirstack_company_search` and company-level filters on `theirstack_job_search` use `company_keyword_slug_*`; job text filters on `theirstack_job_search` use `job_keyword_slug_*`; `theirstack_technographics` uses `keyword_slug_or`.
- **No email-provider filter:** do not invent `company_email_provider`, `email_provider`, `mx_provider`, or similar fields for TheirStack company search.
- **Country codes** are ISO 2-letter (e.g., `US`, `GB`, `DE`).
- **Funding stages:** `seed`, `series_a`, `series_b`, `series_c`, `growth`, `ipo`.
- **Job seniority:** `senior`, `junior`, `manager`, `director`, `vp`, `c_level`.

## Cost Awareness

- Company search is billed per company returned and is the most expensive of these
  operations. Use `limit: 10` for exploration.
- Job search is billed per job returned and is cheaper per row. Safe to use with `limit: 25`.
- Technographics is billed per company lookup, regardless of result count.
- Catalog keyword lookup is free.
- `deepline tools describe <tool> --pricing-only` shows the Deepline credits per
  returned company or job. Estimate a search as `limit` times that price; TheirStack
  returns up to 25 rows when `limit` is omitted.

## Common Mistakes

- Forgetting to provide a time filter OR company filter on job search → API returns error
- Using display names for keywords instead of slugs → no results
- Reusing `keyword_slug_or` from technographics in `theirstack_company_search` → use `company_keyword_slug_or` instead
- Using Prospeo-style MX filters such as `company_email_provider` in `theirstack_company_search` → TheirStack does not support email-provider filtering
- Setting `limit` too high on company search → expensive
- Fetching years of job results in one request → use non-overlapping windows of 180 days or less; keep `include_total_results: false` when totals are not needed

`blur_company_data: true` alone does not guarantee a free request. A count
request (`include_total_results: true`, `limit: 1`) is billable. Any company
identifier filter (`company_name_or`, `company_name_case_insensitive_or`,
`company_domain_or`, `company_linkedin_url_or`, `company_id_or`, or
`company_name_partial_match_or`) also makes the request billable. The ordinary
blurred preview without those filters is free only where the legacy preview
mode is eligible. Inspect the quote for the complete payload before execution.
