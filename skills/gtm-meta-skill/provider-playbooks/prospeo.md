# Prospeo Workflow Guidance

- Use `prospeo_linkedin_email_finder` when you already have a LinkedIn profile URL -- it has the highest confidence and is the cheapest path to a verified email from LinkedIn. Prefer it over `prospeo_email_finder` when a LinkedIn URL is available.
- Use `prospeo_email_finder` when you have a name + company but no LinkedIn URL. Provide as many identifiers as possible (first_name, last_name, domain/company_website) to improve match rates.
- Use `prospeo_domain_search` to pull up to 50 email addresses from a single company domain in one 1-credit call. Best for account-based outreach where you need a full contact list.
- Use `prospeo_search_person` for prospecting -- it supports rich filters (job title with boolean operators, department, seniority, industry, headcount, technology, location). Each page of 25 results costs 1 credit.
- Use `prospeo_search_company` to build account lists by firmographic criteria before drilling into individual contacts.
- Use `prospeo_enrich_person` for full profile enrichment when you need more than just an email (title, company, location). **Mobile phone reveal (`reveal_phone_number: true`) costs 10 credits total instead of 1** -- only enable it when phone outreach is explicitly requested.
- Use `prospeo_enrich_company` for firmographic enrichment (industry, headcount, technologies, description) from a website, company name, or LinkedIn company URL.
- Use `prospeo_account` (free) to check remaining credits before running bulk operations.

Recommended workflow: `prospeo_search_person` or `prospeo_search_company` to build lists, then `prospeo_enrich_person` or `prospeo_email_finder` for individual contacts.
