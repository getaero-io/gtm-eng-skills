# TheirStack Agent Guidance

## Decision Framework

**Use TheirStack when:**
- Crustdata is unavailable or rate-limited
- You need tech-stack-driven company discovery (TheirStack's core strength)
- You need job posting data as a hiring intent signal
- You need to enrich a known company's tech stack

**Prefer Crustdata when:**
- You need person/contact enrichment (TheirStack has no people data)
- You need PersonDB search

## Operation Sequence

1. **Validate slug names first (free):** Use `theirstack_catalog_keywords` to look up the correct technology slug (e.g., `react`, `salesforce`, `hubspot`) before running a paid company or job search.

2. **Company discovery:** Use `theirstack_company_search` with `company_technology_slug_or` or `company_technology_slug_and`. For precision, use `_and`. For broad reach, use `_or`.

3. **Hiring signals:** Use `theirstack_job_search` to find companies actively hiring for specific roles or technologies. Always provide `posted_at_max_age_days` or a company filter — the API requires at least one.

4. **Tech stack enrichment:** Use `theirstack_technographics` for a single known company — provide `company_domain` when possible (most reliable identifier).

5. **Check credits:** Use `theirstack_credit_balance` before large batch runs.

## Key Filters

- **Technology slugs** use kebab-case (e.g., `react`, `node-js`, `salesforce`). Use `theirstack_catalog_keywords` to find the exact slug.
- **Country codes** are ISO 2-letter (e.g., `US`, `GB`, `DE`).
- **Funding stages:** `seed`, `series_a`, `series_b`, `series_c`, `growth`, `ipo`.
- **Job seniority:** `senior`, `junior`, `manager`, `director`, `vp`, `c_level`.

## Cost Awareness

- Company search: 3 credits per company returned. Use `limit: 10` for exploration.
- Job search: 1 credit per job. Safe to use with `limit: 25`.
- Technographics: 3 credits per company lookup (regardless of result count).
- Catalog keywords and credit balance: free.

## Common Mistakes

- Forgetting to provide a time filter OR company filter on job search → API returns error
- Using display names for technologies instead of slugs → no results
- Setting `limit` too high on company search → expensive
