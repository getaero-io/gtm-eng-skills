---
name: linkedin-url-lookup
description: "Resolve LinkedIn profile URLs from name + company with strict identity validation to avoid false positives."
---

# LinkedIn URL Lookup

Find LinkedIn profile URLs when you have a name, with or without company context.

## When to use

- "Find LinkedIn URLs for the contacts in my CSV"
- "Resolve LinkedIn profiles from names and companies"
- "I only have names — find their LinkedIn profiles"
- "Verify these LinkedIn URLs match the right people"

## Execution

1. **Read [enriching-and-researching.md](../enriching-and-researching.md)** — the LinkedIn enrichment section covers provider selection and validation patterns.
2. **Read [finding-companies-and-contacts.md](../finding-companies-and-contacts.md)** — if you also need to find contacts first.

## Provider sequence

Follow this order. Stop when you get a validated match.

### Step 1: Dropleads (free)

Start with Dropleads — free people search that returns LinkedIn URLs directly.

```bash
deepline tools execute dropleads_search_people --payload '{"filters":{"keywords":["Jane","Smith"],"jobTitles":["Sales"],"seniority":["VP","Director"]},"pagination":{"page":1,"limit":5}}'
```

For batch:

```bash
deepline enrich --csv contacts.csv --rows 0:1 --in-place \
  --with '{"alias":"li_url","tool":"dropleads_search_people","payload":{"filters":{"keywords":["{{first_name}}","{{last_name}}"],"jobTitles":["{{title}}"]},"pagination":{"page":1,"limit":1}}}'
```

### Step 2: Serper Google search + Apify validation

If Dropleads misses, search Google scoped to LinkedIn then validate the profile.

**2a. Find candidate URLs with Serper:**

```bash
# Name + company (highest confidence)
deepline tools execute serper_google_search --payload '{"query":"\"Jane Smith\" \"Acme Corp\" site:linkedin.com/in","num":5}'

# Name only
deepline tools execute serper_google_search --payload '{"query":"\"Jane Smith\" site:linkedin.com/in","num":5}'

# Name + title
deepline tools execute serper_google_search --payload '{"query":"\"Jane Smith\" \"VP Sales\" site:linkedin.com/in","num":5}'
```

Parse the LinkedIn URL from `organic[0].link`. Skip results that aren't `linkedin.com/in/` URLs.

**2b. Validate with Apify LinkedIn profile scraper:**

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"2SyF0bVxmgGr8IVCZ","input":{"urls":["https://linkedin.com/in/janesmith"]},"timeoutMs":60000}'
```

Compare the scraped profile against your data:
- Company name match (fuzzy — "Acme" matches "Acme Corp" or "Acme, Inc.")
- Title/seniority consistent
- Location plausible

If validation fails, try the next Serper result. If all Serper results fail validation, move to Step 3.

For batch:

```bash
# Find candidates
deepline enrich --csv contacts.csv --rows 0:1 --in-place \
  --with '{"alias":"li_serper","tool":"serper_google_search","payload":{"query":"\"{{first_name}} {{last_name}}\" \"{{company}}\" site:linkedin.com/in","num":3}}'

# Validate top result
deepline enrich --csv contacts.csv --rows 0:1 --in-place \
  --with '{"alias":"li_validate","tool":"apify_run_actor_sync","payload":{"actorId":"2SyF0bVxmgGr8IVCZ","input":{"urls":["{{li_serper_url}}"]},"timeoutMs":60000}}'
```

### Step 3: Exa semantic search

If Serper + validation fails, try Exa's semantic "find similar" approach.

```bash
deepline tools execute exa_search --payload '{"query":"Jane Smith VP Sales at Acme Corp LinkedIn profile","numResults":3,"type":"neural","includeDomains":["linkedin.com"]}'
```

Exa's neural search handles fuzzy name matching and context better than keyword search. Validate results with the same Apify step.

### Step 4: Crustdata (paid, ~1 credit)

Structured people search with company domain context.

```bash
deepline enrich --csv contacts.csv --rows 0:1 --in-place \
  --with '{"alias":"linkedin","tool":"crustdata_people_search","payload":{"companyDomain":"{{domain}}","titleKeywords":["{{title}}"],"limit":1}}'
```

### Step 5: Prospeo (paid)

Email + LinkedIn finder from name and company.

```bash
deepline tools execute prospeo_enrich_person --payload '{"first_name":"Jane","last_name":"Smith","company_name":"Acme Corp"}'
```

Prospeo returns LinkedIn URLs alongside email when available.

## Scenarios

### Name only

1. Dropleads with whatever filters you have
2. Serper: `"Jane Smith" site:linkedin.com/in` → validate with Apify
3. Too many results? Add geography: `"Jane Smith" "New York" site:linkedin.com/in`
4. Exa neural search for the person
5. Still ambiguous? Ask the user for more info before spending credits

### Name + company

1. Dropleads with name + company
2. If miss, Serper: `"Jane Smith" "Acme Corp" site:linkedin.com/in` → validate with Apify
3. Exa: `"Jane Smith VP Sales Acme Corp LinkedIn"`
4. Crustdata people search with company domain

### Nickname handling

Common variants: Mike/Michael, Bob/Robert, Bill/William, Liz/Elizabeth.

- Serper handles this well: `("Mike" OR "Michael") "Smith" "Acme" site:linkedin.com/in`
- For batch, expand CSV to include common variants before lookup

## Key rules

- Dropleads first — free, structured, returns LinkedIn URLs directly.
- Serper second — fractions of a cent, then always validate with Apify profile scraper.
- Exa third — neural search handles fuzzy/ambiguous cases better than keyword search.
- Crustdata fourth — ~1 credit, reliable with company domain context.
- Prospeo fifth — paid, returns LinkedIn + email together.
- Always validate Serper/Exa results — a wrong LinkedIn profile is worse than none.
- Pilot on `--rows 0:1` before full batch.
- Extract the `/in/username` slug — strip query params and trailing slashes.
