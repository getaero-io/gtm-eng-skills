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

**2b. Scrape and name-validate:**

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"harvestapi/linkedin-profile-scraper","input":{"urls":["https://linkedin.com/in/janesmith"]},"timeoutMs":90000}'
```

**Name-validate** the scraped `full_name` against source name (see Post-lookup name validation). Company/title are supporting signals only.

If validation fails, try the next Serper result. If all Serper results fail validation, move to Step 3.

For batch:

```bash
# Find candidates
deepline enrich --csv contacts.csv --rows 0:1 --in-place \
  --with '{"alias":"li_serper","tool":"serper_google_search","payload":{"query":"\"{{first_name}} {{last_name}}\" \"{{company}}\" site:linkedin.com/in","num":3}}'

# Scrape + name-validate top result
deepline enrich --csv contacts.csv --rows 0:1 --in-place \
  --with '{"alias":"li_validate","tool":"apify_run_actor_sync","payload":{"actorId":"harvestapi/linkedin-profile-scraper","input":{"urls":["{{li_serper_url}}"],},"timeoutMs":90000}}'
```

### Step 3: Exa semantic search

If Serper + validation fails, try Exa's semantic "find similar" approach.

```bash
deepline tools execute exa_search --payload '{"query":"Jane Smith VP Sales at Acme Corp LinkedIn profile","numResults":3,"type":"neural","includeDomains":["linkedin.com"]}'
```

Exa is a weak fallback for name-only lookup (23% validated vs serper's 74% in a 253-person test). Still worth trying on serper misses - it recovered 3/36 failures. Name-validate the same way.

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

### Name only (event attendees, RSVP lists)

When you have names but no company context, add event/role keywords to disambiguate:

```bash
# OR-chain of likely titles improves serper relevance
"\"Jane Smith\" (RevOps OR \"Sales Operations\" OR GTM OR Sales OR Growth) site:linkedin.com/in"
```

Use `run_javascript` to score serper results by GTM keyword density + geo before picking the best URL. Expect ~74% validated match rate on name-only with title keywords.

### Nickname handling

Common variants: Mike/Michael, Bob/Robert, Bill/William, Liz/Elizabeth, Alex/Alexander/Oleksandr, Dan/Daniel, Sara/Sarah.

- Serper handles this well: `("Mike" OR "Michael") "Smith" "Acme" site:linkedin.com/in`
- For batch, expand CSV to include common variants before lookup

## Post-lookup name validation (mandatory)

After scraping, compare profile name to source name. **Null out any URL where first+last don't match.** 26% of serper lookups returned wrong people in a 253-person test without this gate.

Rules:
- Last name: exact or substring (handles hyphenated, but not single-char abbreviations)
- First name: exact, 3+ char prefix, nickname, or quoted nickname in profile (e.g., `Yerachmiel 'Rocky' Katz`)
- Normalize accents (`Rodríguez`->`Rodriguez`) and strip punctuation/emoji before comparing

Validation script and eval fixtures:
```bash
python3 scripts/validate-linkedin-names.py --fixtures scripts/fixtures_name_validation.json
# 52 test cases, thresholds: precision >= 0.95, recall >= 0.85
```

## Tested actors

| Actor | Use | Input field | Cost |
|-------|-----|-------------|------|
| `harvestapi/linkedin-profile-scraper` | Profile scrape | `urls` (array) | $0.004/profile ($4/1k), $0.01 with email | 6.3M runs, 100% 30d, 4.8 rating. Returns `firstName`, `lastName`, `headline`, `experience`, `education`, parsed `location`. |
| `harvestapi/linkedin-profile-posts` | Posts scrape | `targetUrls` (array), `maxPosts` (int) | $0.002/post (so $0.04/profile at maxPosts=20) | 6.2M runs, 100% 30d. Rejects `profileUrls` and `postedLimit`. |

`dev_fusion/Linkedin-Profile-Scraper` has higher weighted reviews (596 vs 114) but returned empty data in testing. `data-slayer/linkedin-profile-scraper` has no reviews. Stick with `harvestapi`.

## Key rules

- Dropleads first - free, structured, returns LinkedIn URLs directly.
- Serper second - fractions of a cent, then scrape with `harvestapi/linkedin-profile-scraper`.
- Exa third - weak fallback (23% validated rate), but recovers some serper misses.
- Crustdata fourth - ~1 credit, reliable with company domain context.
- Prospeo fifth - paid, returns LinkedIn + email together.
- **Name-validate every looked-up URL.** Company/title matching alone is not enough.
- Pilot on `--rows 0:1` before full batch.
- Extract the `/in/username` slug - strip query params and trailing slashes.
- Without company context, add role keywords to serper query.
