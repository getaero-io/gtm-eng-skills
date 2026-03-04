---
name: investor-company-prospecting
disable-model-invocation: true
description: |
  Find YC (or other accelerator/investor-backed) companies hiring for a specific
  role and build personalized outbound to contacts at those companies.

  Read gtm-meta-skill to guide how to use this skill.
---

> Start here first: read `gtm-meta-skill` before running this skill.

# YC / Investor-Portfolio Prospecting

Find companies backed by a specific investor or accelerator (YC, a16z, Sequoia, etc.) that are hiring for a target role, then find contacts and build personalized outbound.

## Core insight: VC portfolio data is public

Every major VC and accelerator publishes their portfolio online. **Do NOT waste turns trying to discover portfolio companies through Deepline search tools.** Instead, fetch the public portfolio page directly and extract company names from it.

This is faster, cheaper, and more complete than any provider-based approach.

---

## What NOT to do (and why)

These approaches were tested in eval runs and all failed or were extremely wasteful:

### Do NOT use Apollo to filter by investor

Apollo's `q_organization_keyword_tags` and `q_keywords` fields do not reliably filter by investor/accelerator. Searching `q_keywords: "Y Combinator"` returns mostly irrelevant results. Apollo is great for people search AFTER you have a company list, but cannot produce the company list.

### Do NOT search Apollo for people first and then verify investor status

Searching for "GTM Engineer" across all companies returns ~7-9% YC hit rate. You end up pulling 300+ contacts and running `call_ai` on each one to check if their company is YC-backed. Burns 60-80% of your turn budget on filtering alone.

### Crustdata `crunchbase_investors` filter is inconsistent

Crustdata has a `crunchbase_investors` filter that SHOULD work but returns results inconsistently. Do not rely on it as your primary source.

### Do NOT use `call_ai` to verify investor status at scale

Using `call_ai` + WebSearch to check "Is {{company_name}} a YC company?" per row is ~5-10s per row. Unacceptable for 100+ rows.

---

## The proven approach: Fetch the public portfolio page

### Step 1: Get the company list from the VC's public portfolio

Every major investor publishes their portfolio. Fetch it directly:

**For YC specifically** — use the YC company directory:

```bash
# Fetch YC companies page and extract company data
curl -sS "https://www.ycombinator.com/companies" \
  -H "Accept: text/html" \
  -o /tmp/yc_page.html

# Or use the YC API/directory to get structured data
# YC's company directory is at ycombinator.com/companies
# You can filter by batch, industry, etc.
```

Parse the HTML to extract company names and domains. Use `run_javascript` or python to extract structured data from the page.

```python
# Example: parse company names from the fetched page
# Adjust selectors based on the actual page structure
from html.parser import HTMLParser
import csv, json

# Write extracted companies to CSV
with open('yc_companies.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['company_name', 'domain', 'batch', 'description'])
    writer.writeheader()
    for company in extracted_companies:
        writer.writerow(company)
```

**For other VCs** — find their portfolio page and fetch it:

| Investor | Portfolio URL pattern | Notes |
|----------|----------------------|-------|
| YC | `ycombinator.com/companies` | Filterable directory with batch, industry |
| a16z | `a16z.com/portfolio` | Lists all portfolio companies |
| Sequoia | `sequoiacap.com/our-companies` | Categorized by stage |
| Greylock | `greylock.com/portfolio` | Simple list |
| Benchmark | `benchmark.com/portfolio` | Simple list |

```bash
# Generic approach for any VC:
curl -sS "https://[vc-website]/portfolio" -o /tmp/portfolio.html
# Parse the HTML to extract company names and domains
```

If the portfolio page uses JavaScript rendering and curl returns an empty shell, use `call_ai` with WebSearch to get the list:

```bash
deepline tools execute call_ai --payload '{
  "prompt": "List all portfolio companies from [VC Name]. Return company name and website domain for each. Focus on companies founded in the last 3 years.",
  "json_mode": {"type":"object","properties":{"companies":{"type":"array","items":{"type":"object","properties":{"name":{"type":"string"},"domain":{"type":"string"}},"required":["name"]}}},"required":["companies"]},
  "tools": ["WebSearch"],
  "max_tokens": 4000
}'
```

### Step 1b: Filter to companies hiring your target role (optional)

If you need companies hiring a specific role (e.g., "GTM Engineer"), use Exa to cross-reference against the YC job board. **Exa works well for small datasets (≤50 results) but degrades on larger ones.**

```bash
deepline tools execute exa_search --payload '{
  "query": "GTM Engineer",
  "numResults": 50,
  "includeDomains": ["ycombinator.com"],
  "type": "auto"
}'
```

Cross-reference the Exa results against your portfolio company list to identify which companies are actively hiring for the role.

For larger datasets or when Exa returns too few results, use `call_ai` with WebSearch to check job boards:

```bash
deepline enrich --input yc_companies.csv --in-place --rows 0:2 \
  --with 'has_role=call_ai:{"prompt":"Is {{company_name}} ({{domain}}) currently hiring a GTM Engineer or similar GTM role? Check their careers page and job boards. Return true or false with the job title if found.","json_mode":{"type":"object","properties":{"hiring":{"type":"boolean"},"job_title":{"type":"string"}},"required":["hiring"]},"tools":["WebSearch"]}'
```

### Step 2: Build a clean company seed CSV

From Step 1, you should have a CSV with at minimum: `company_name`, `domain`.

For companies missing domains, resolve them in a single enrichment pass:

```bash
deepline enrich --input yc_companies.csv --in-place \
  --with 'resolved_domain=call_ai:{"prompt":"What is the primary website domain for {{company_name}}? Return ONLY the domain, nothing else (e.g. pump.co, langfuse.com).","max_tokens":20}'
```

This is fast because `call_ai` without WebSearch uses model knowledge and these are well-known VC-backed companies.

### Step 3: Find contacts at each company

**Important: these are small startups (5-50 people).** Exact-job-title searches are often sparse in smaller teams, so broaden your search:

```bash
deepline enrich --input yc_companies.csv --output yc_with_contacts.csv \
  --rows 0:2 \
  --with 'contact=dropleads_search_people:{
    "filters": {
      "companyDomains": ["{{domain}}"],
      "keywords": ["sales", "growth", "marketing", "revenue", "operations"],
      "seniority": ["C-Level", "VP", "Director", "Manager"]
    },
    "pagination": {"page": 1, "limit": 5}
  }'
```

Note: no `person_titles` filter — for tiny startups, just get whoever is there and pick the best GTM-adjacent contact. Founders, growth leads, founding AEs, and heads of sales are all valid targets when the company has 10 people.

If Dropleads returns 0 for a company, fall back to `call_ai` with WebSearch:

```bash
deepline enrich --input yc_missing.csv --in-place \
  --with 'contact_lookup=call_ai:{"prompt":"Find the founder, CEO, or GTM/growth lead at {{company_name}} ({{domain}}). Return their full name, title, and LinkedIn URL.","json_mode":{"type":"object","properties":{"name":{"type":"string"},"title":{"type":"string"},"linkedin_url":{"type":"string"}},"required":["name","title"]},"tools":["WebSearch"]}'
```

### Step 4: Find emails via waterfall

**For small startups, use LeadMagic as your primary email finder, not Hunter.** Hunter has poor coverage for companies under 50 people. LeadMagic's `email_finder` has significantly better fill rates for small startups.

```bash
deepline enrich --input yc_with_contacts.csv --in-place --rows 0:2 \
  --with-waterfall "email" \
  --type email \
  --result-getters '["data.email","email"]' \
  --with 'leadmagic=leadmagic_email_finder:{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}' \
  --with 'dropleads=dropleads_email_finder:{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_domain":"{{domain}}"}' \
  --with 'hunter=hunter_email_finder:{"domain":"{{domain}}","first_name":"{{first_name}}","last_name":"{{last_name}}"}' \
  --end-waterfall
```

Expected fill rate: ~60-70% with the 3-provider waterfall. Lower than typical because these are tiny, recently-founded companies.

### Step 5: Generate personalized email copy

```bash
deepline enrich --input yc_with_contacts.csv --in-place --rows 0:2 \
  --with 'outbound=call_ai:{"prompt":"Write a short (≤80 word) cold email to {{first_name}} at {{company_name}}. They are a {{title}}. Mention Deepline helps GTM teams enrich data across 20+ providers in a single CLI. Be specific to their company — no generic templates. Return subject and body.","json_mode":{"type":"object","properties":{"subject":{"type":"string"},"body":{"type":"string"}},"required":["subject","body"]}}'
```

After pilot, run the full batch:

```bash
deepline enrich --input yc_with_contacts.csv --in-place --rows 2: \
  # ... same flags
```

---

## Common pitfalls

| Pitfall | What happens | Fix |
|---------|-------------|-----|
| Trying to discover portfolio companies via Deepline tools | Wastes 60-80% of turn budget on company discovery | Fetch the public portfolio page directly |
| `json_mode: true` in call_ai | `RuntimeError: json_mode expected object\|string, got boolean` | Pass a JSON schema object: `{"type":"object","properties":{...},"required":[...]}` |
| Searching with strict titles at small startups | 0 results — person hasn't been hired yet | Remove title filter, get broader roles, pick best match |
| Using Hunter as primary email finder for <50 person companies | 0/25 fill rate | Use LeadMagic first — better small-company coverage |
| Asking for user approval in headless/eval mode | Run stops dead | The prompt says "You have approval to spend up to N credits" — treat that as blanket approval |
| Storing raw JSON from LeadMagic in email column | Email column contains `{"data":{"email":"x@y.com",...}}` instead of `x@y.com` | Use waterfall syntax with `--result-getters` to auto-extract, or add a `run_javascript` step |
| Using Exa for large datasets (100+ companies) | Degraded results, missed companies | Exa is fine for ≤50 results; for larger lists, fetch the portfolio page directly |

## Cost estimation

| Step | Credits | Notes |
|------|---------|-------|
| Portfolio page fetch (curl) | 0 | Free — public web page |
| Exa search (optional, role filtering) | ~5 | Only if filtering by active job postings |
| call_ai domain resolution | ~0 | Free (model knowledge, no tools) |
| Dropleads contact search (per company) | ~0.1 | Contact lookup |
| LeadMagic email finder (per contact) | ~0.3 | Primary email source |
| Dropleads email finder (per contact) | ~0.3 | Waterfall fallback |
| call_ai outbound copy (per contact) | ~0 | Free |
| **Total for 25 companies** | **~15-20** | Well within 150 credit budget |

## Related skills

- **Need emails after finding contacts?** → Use `contact-to-email` skill
- **Building a broader account list?** → Use `build-tam` skill
- **Want to score accounts first?** → Use `niche-signal-discovery` skill

## Get started

Sign up and get your API key at [code.deepline.com](https://code.deepline.com).

```bash
curl -s "https://code.deepline.com/api/v2/cli/install" | bash
deepline auth register
```
