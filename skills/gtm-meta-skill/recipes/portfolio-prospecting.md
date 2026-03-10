# Portfolio/VC Prospecting

Find companies backed by a specific investor or accelerator (YC, a16z, Sequoia, etc.), then find contacts and build personalized outbound.

## Core insight: VC portfolio data is public

Every major VC and accelerator publishes their portfolio online. **Do NOT waste turns trying to discover portfolio companies through Deepline search tools.** Instead, fetch the public portfolio page directly and extract company names from it. This is faster, cheaper, and more complete than any provider-based approach.

## What NOT to do

Tested and failed: Apollo investor filtering (irrelevant results), people-first then verify investor (~7-9% hit rate, wastes 60-80% of turns), Crustdata `crunchbase_investors` (inconsistent), `call_ai` per-row investor verification (~5-10s/row, unacceptable at scale).

## Proven approach

**Step 1: Get the company list from the VC's public portfolio.** Common URLs: YC (`ycombinator.com/companies`), a16z (`a16z.com/portfolio`), Sequoia (`sequoiacap.com/our-companies`), Greylock/Benchmark (`/portfolio`).

```bash
# Fetch YC companies page (or use parallel_extract if JS-rendered)
curl -sS "https://www.ycombinator.com/companies" -H "Accept: text/html" -o /tmp/yc_page.html

deepline tools execute parallel_extract --payload '{"urls":["https://www.ycombinator.com/companies?batch=W26"],"objective":"Extract all company names, website domains, and one-line descriptions from this YC batch directory page","full_content":true}'
```

**Step 2: Filter to companies hiring your target role (optional).**

```bash
deepline enrich --input yc_companies.csv --in-place --rows 0:2 \
  --with '{"alias":"exa_jobs","tool":"exa_search","payload":{"query":"GTM Engineer site:ycombinator.com","numResults":50,"type":"auto"}}'
```

**Step 3: Find contacts at each company.**

For small startups (5-50 people), dropleads has near-zero coverage. Use `exa_people_search` — it returns structured person entities (name, title, LinkedIn, work history) and works well for startups:

```bash
deepline enrich --input yc_companies.csv --output yc_with_contacts.csv \
  --rows 0:2 \
  --with '{"alias":"contact","tool":"exa_people_search","payload":{"query":"GTM Engineer at {{company_name}}","numResults":3}}'
```

Write a `run_javascript` step to extract the best contact from exa entities (walk `results[].entities[].properties.workHistory[]` for title keywords). If exa returns 0 for a company, fall back to `call_ai` with WebSearch:

```bash
deepline enrich --input yc_missing.csv --in-place \
  --with '{"alias":"contact_lookup","tool":"call_ai","payload":{"prompt":"Find the founder, CEO, or GTM/growth lead at {{company_name}} ({{domain}}). Return their full name, title, and LinkedIn URL.","json_mode":{"type":"object","properties":{"name":{"type":"string"},"title":{"type":"string"},"linkedin_url":{"type":"string"}},"required":["name","title"]},"tools":["WebSearch"]}}'
```

**Step 4: Find emails via waterfall.**

For small startups, use LeadMagic as primary (not Hunter -- Hunter has poor coverage for <50 person companies):

```bash
deepline enrich --input yc_with_contacts.csv --in-place --rows 0:2 \
  --with-waterfall "email" \
  --with '{"alias":"leadmagic","tool":"leadmagic_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"dropleads","tool":"dropleads_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_domain":"{{domain}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"hunter","tool":"hunter_email_finder","payload":{"domain":"{{domain}}","first_name":"{{first_name}}","last_name":"{{last_name}}"},"extract_js":"extract(\"email\")"}' \
  --end-waterfall
```

**Step 5: Generate personalized email copy** using `call_ai` with `json_mode` for subject/body. Pilot on rows 0:2, then run full batch.

## Common pitfalls

| Pitfall | What happens | Fix |
|---------|-------------|-----|
| Trying to discover portfolio companies via Deepline tools | Wastes 60-80% of turn budget on company discovery | Fetch the public portfolio page directly |
| `json_mode: true` in call_ai | `RuntimeError: json_mode expected object\|string, got boolean` | Pass a JSON schema object: `{"type":"object","properties":{...},"required":[...]}` |
| Searching with strict titles at small startups | 0 results — person hasn't been hired yet | Remove title filter, get broader roles, pick best match |
| Using Hunter as primary email finder for <50 person companies | 0/25 fill rate | Use LeadMagic first — better small-company coverage |

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
