---
name: linkedin-url-lookup
description: "Resolve LinkedIn profile URLs from name + company with strict identity validation to avoid false positives."
---

# LinkedIn URL Lookup

Find LinkedIn profile URLs from name + company, with validation to ensure you have the right person.

## When to use

- "Find LinkedIn URLs for the contacts in my CSV"
- "Resolve LinkedIn profiles from names and companies"
- "Verify these LinkedIn URLs match the right people"

## Execution

1. **Read [enriching-and-researching.md](../enriching-and-researching.md)** — the LinkedIn enrichment section covers provider selection and validation patterns.
2. **Read [finding-companies-and-contacts.md](../finding-companies-and-contacts.md)** — if you also need to find contacts first.

## Key approach

Use person enrichment providers that return LinkedIn URLs:

```bash
# From name + company
deepline enrich --csv contacts.csv --rows 0:1 --in-place \
  --with '{"alias":"linkedin","tool":"crustdata_people_search","payload":{"companyDomain":"{{domain}}","titleKeywords":["{{title}}"],"limit":1}}'
```

For nickname handling (e.g., "Mike" vs "Michael"), search with common variants or use providers that handle fuzzy matching (Crustdata, PDL).

## Key rules

- Always validate the returned profile matches the expected person — check company and title alignment.
- For ambiguous names, use Apify LinkedIn profile scraper to verify identity.
- Pilot on `--rows 0:1` before full batch.
- PDL and Crustdata are the most reliable for LinkedIn URL resolution.
