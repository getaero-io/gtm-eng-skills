# Sentrion Guidance

Use Sentrion for hiring-signal research and job market intelligence.

- Use `sentrion_company_jobs_search` when the company LinkedIn URL is known. It requires `company_linkedin_url`; with only a domain, resolve the LinkedIn company URL first.
- Use `sentrion_jobs_search` for broad market searches across companies (location, department, industry, keyword, seniority, salary, job board).
- Use the historical actions for past or closed postings back to 2020; they cost twice as much per job as current searches.
- Paginate with `search_after` when `result.data.search_after` is non-null.
- Prefer narrow filters and an explicit, small `limit` when exploring; each returned job is billed and empty searches are free.
