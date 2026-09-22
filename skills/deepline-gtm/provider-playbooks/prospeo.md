# Prospeo Workflow Guidance

- Use `prospeo_search_person` or `prospeo_search_company` to build list-level candidates, then refine with `prospeo_enrich_person` and `prospeo_enrich_company` for details.
- Use `prospeo_search_person` for prospecting -- it supports stable filters (job title with boolean operators, department, seniority, industry, headcount, technology, location). Search is billed per page of 25 results.
- Do not use Prospeo for job-change detection or job-change filtered searches. The live Prospeo job-change filter has schema drift; use FullEnrich for job-change workflows.
- Use `prospeo_search_company` to build account lists by firmographic criteria before drilling into individual contacts.
- Use `prospeo_enrich_person` for full profile enrichment when you need more than just an email (title, company, location). **Mobile phone reveal (`enrich_mobile: true` or `only_verified_mobile: true`) can cost up to 10× a standard enrichment.** The tool's payload estimate includes that 10× maximum so Play spend guards can admit or reject the request before provider execution. Only enable mobile reveal when phone outreach is explicitly requested.
- Use `prospeo_enrich_company` for firmographic enrichment (industry, headcount, technologies, description) from a website, company name, or LinkedIn company URL.

Recommended workflow: `prospeo_search_person` or `prospeo_search_company` to build lists, then `prospeo_enrich_person` for individual contacts.
