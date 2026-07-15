# Sentrion Guidance

Use Sentrion for hiring-signal research and job market intelligence.

- Use `sentrion_company_jobs_search` when the company LinkedIn URL is known.
- Use `sentrion_jobs_search` for broad market searches across companies.
- Use historical actions only when the user or workspace has Sentrion historical access.
- Paginate with `search_after` when `result.data.search_after` is non-null.
- Prefer narrow filters and an explicit `limit` when exploring.
