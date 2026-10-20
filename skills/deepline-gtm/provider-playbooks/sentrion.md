# Sentrion Guidance

Use Sentrion for hiring-signal research and job market intelligence.

- Use `sentrion_company_jobs_search` when the company LinkedIn URL is known.
- Use `sentrion_jobs_search` for broad market searches across companies.
- Historical endpoints are available on every Sentrion plan. The provider's pricing page states that Standard plans include six months of history and Enterprise plans extend back to 2020.
- Paginate with `search_after` when `result.data.search_after` is non-null.
- Prefer narrow filters and an explicit `limit` of 10–100 when exploring.
