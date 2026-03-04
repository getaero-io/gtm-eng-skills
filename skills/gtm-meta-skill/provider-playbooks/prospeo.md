# Prospeo Workflow Guidance

- Use `prospeo_search_person` or `prospeo_search_company` to build list-level candidates, then refine with `prospeo_enrich_person` and `prospeo_enrich_company` for details.
- Use `prospeo_search_person` for prospecting -- it supports rich filters (job title with boolean operators, department, seniority, industry, headcount, technology, location). Each page of 25 results costs 1 credit.
- Use `prospeo_search_company` to build account lists by firmographic criteria before drilling into individual contacts.
- Use `prospeo_enrich_person` for full profile enrichment when you need more than just an email (title, company, location). **Mobile phone reveal (`enrich_mobile: true`) costs 10 credits total instead of 1** -- only enable it when phone outreach is explicitly requested.
- Use `prospeo_enrich_company` for firmographic enrichment (industry, headcount, technologies, description) from a website, company name, or LinkedIn company URL.

Recommended workflow: `prospeo_search_person` or `prospeo_search_company` to build lists, then `prospeo_enrich_person` for individual contacts.
