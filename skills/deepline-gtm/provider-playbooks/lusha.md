# Lusha — Agent Guidance

## When to use

Lusha for B2B email + direct dial enrichment. Strong North American and European coverage with intent signal data. Good for sales prospecting workflows where direct dials matter. Cost-competitive at $0.05/credit.

**Key strength**: Direct dials (not just HQ numbers). Lusha often surfaces mobile and desk direct numbers that other providers miss.

## Provider characteristics

- **Input required**: LinkedIn URL (best), email, or first_name+last_name+(company_name or company_domain)
- **Geographic coverage**: Global, strongest in North America + Europe
- **Credit cost**: ~$0.05 per credit (person enrich, company enrich, or contact from search)
- **LinkedIn URL requirement**: Must contain "linkedin.com/in/". Sales Navigator URLs not supported.

## Key operations

### lusha_enrich_person

Enriches a person by LinkedIn URL (preferred), email, or name+company. Returns emails at `emails[].email` and phones at `phones[].number`.

```json
{
  "linkedin_url": "https://www.linkedin.com/in/johndoe"
}
```

```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "company_domain": "acme.com"
}
```

Optional flags:
- `reveal_emails: true` — include email addresses in response (default: true)
- `reveal_phones: true` — include phone numbers (default: true)
- `signals: true` — include intent signal data

### lusha_enrich_company

Enriches a company from domain, name, or Lusha company ID. Returns size, revenue, industry, technologies.

```json
{
  "domain": "salesforce.com"
}
```

### lusha_search_contacts

Prospecting search with rich filters: department, seniority, company size, industry, job title, location, and tech stack.

```json
{
  "filters": {
    "seniority": ["director", "vp", "c_suite"],
    "companySize": ["201-500", "501-1000"],
    "department": ["sales"]
  },
  "pageSize": 25
}
```

## Output shape

`lusha_enrich_person` returns a flat profile. Email at `emails[0].email` or `email`. Phone at `phones[0].number` or `phone`.

`lusha_enrich_company` returns a flat company object with `name`, `domain`, `size`, `industry`, `technologies[]`.

`lusha_search_contacts` returns `{ contacts: [...], pagination: { page, pageSize, total, totalPages } }`.

## Anti-patterns

- Don't use Sales Navigator or Recruiter LinkedIn URLs — they'll fail
- Don't include "http://" or "www." in domain values for company enrichment
- Don't pass `company_name` alone without `first_name` + `last_name` for person lookup — name+company is the minimum combo
- Don't assume `phone` (top-level) is always populated — check `phones[]` array first for the most complete list
