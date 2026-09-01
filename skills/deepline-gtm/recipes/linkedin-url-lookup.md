---
name: linkedin-url-lookup
description: 'Resolve LinkedIn profile URLs from name + company with strict identity validation to avoid false positives.'
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

## Prebuilt first

`prebuilt/person-to-linkedin-harvestapi` runs the maintained Serper candidate
route with native HarvestAPI profile validation. Inspect the live contract
before running it:

```bash
deepline plays describe prebuilt/person-to-linkedin-harvestapi
deepline plays run prebuilt/person-to-linkedin-harvestapi --input '{"first_name":"Jane","last_name":"Smith","company_name":"Acme"}'
# CSV:
deepline plays run prebuilt/person-to-linkedin-harvestapi-batch --input '{"csv":"contacts.csv"}'
deepline runs export <run-id> --out contacts_with_linkedin.csv
```

The HarvestAPI play tries company-anchored Serper, name-only Serper, and
Crustdata when an email is available. It validates the chosen candidate with
`harvestapi_get_profile`, then scans later Serper results only when the first
candidate fails validation. The older `prebuilt/person-to-linkedin` and
`prebuilt/person-to-linkedin-batch` IDs keep their original Serper-validation
behavior for existing workflows.

Use the expanded manual sequence below only when you need a custom provider
order. Pull the maintained play as a starting point, then inspect and check the
fork before running it:

```bash
deepline plays get prebuilt/person-to-linkedin-harvestapi --source --out ./fork.play.ts
deepline plays check ./fork.play.ts
```

## Expanded provider sequence for a custom fork

Follow this order. Stop when you get a validated match.

### Step 1: Dropleads (free)

Start with Dropleads — free people search that returns LinkedIn URLs directly.

```bash
deepline tools execute dropleads_search_people --payload '{"filters":{"keywords":["Jane","Smith"],"jobTitles":["Sales"],"seniority":["VP","Director"]},"pagination":{"page":1,"limit":5}}'
```

For batch:

_In a fork/custom play, this step is one `withColumn` calling the same tool per row._

### Step 2: Serper Google search + HarvestAPI validation

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

**2b. Retrieve and name-validate:**

```bash
deepline tools describe harvestapi_get_profile --schema-only
deepline tools execute harvestapi_get_profile --payload '{"url":"https://linkedin.com/in/janesmith"}' --json
```

**Name-validate** the returned `element.firstName` and `element.lastName` against the source name (see Post-lookup name validation). Company/title are supporting signals only.

If validation fails, try the next Serper result. If all Serper results fail validation, move to Step 3.

For batch:

```bash
deepline tools execute serper_google_search --input '{"query":"\"Jane Smith\" \"Acme\" site:linkedin.com/in","num":3}'
deepline tools execute harvestapi_get_profile --input '{"url":"<top-hit-url>"}' --json
```

_In a fork/custom play these are two `withColumn` steps: search, then scrape + name-validate the top hit._

### Step 3: Exa semantic search

If Serper + validation fails, try Exa's semantic "find similar" approach.

```bash
deepline tools execute exa_search --payload '{"query":"Jane Smith VP Sales at Acme Corp LinkedIn profile","numResults":3,"type":"neural","includeDomains":["linkedin.com"]}'
```

Exa is a weak fallback for name-only lookup (23% validated vs serper's 74% in a 253-person test). Still worth trying on serper misses - it recovered 3/36 failures. Name-validate the same way.

### Step 4: Crustdata (paid, ~1 credit)

Structured people search with company domain context.

_In a fork/custom play, this step is one `withColumn` calling the same tool per row._

### Step 5: Prospeo (paid)

Email + LinkedIn finder from name and company.

```bash
deepline tools execute prospeo_enrich_person --payload '{"first_name":"Jane","last_name":"Smith","company_name":"Acme Corp"}'
```

Prospeo returns LinkedIn URLs alongside email when available.

## Scenarios

### Name only

1. Dropleads with whatever filters you have
2. Serper: `"Jane Smith" site:linkedin.com/in` → validate with HarvestAPI
3. Too many results? Add geography: `"Jane Smith" "New York" site:linkedin.com/in`
4. Exa neural search for the person
5. Still ambiguous? Ask the user for more info before spending credits

### Name + company

1. Dropleads with name + company
2. If miss, Serper: `"Jane Smith" "Acme Corp" site:linkedin.com/in` → validate with HarvestAPI
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

## Native HarvestAPI operations

| Operation                      | Use                          | Starting input                                       |
| ------------------------------ | ---------------------------- | ---------------------------------------------------- |
| `harvestapi_get_profile`       | Profile lookup/validation    | `url`, `publicIdentifier`, or `profileId`            |
| `harvestapi_get_profile_posts` | Posts published by a profile | `profile`, `profileId`, or `profilePublicIdentifier` |

Confirm the live input and Deepline pricing with `deepline tools describe <operation>` before building a batch. Use Apify only when the native HarvestAPI provider does not expose the required result shape.

## Key rules

- Prefer the maintained prebuilt unless you need a custom provider order.
- In an expanded fork, Dropleads is free and structured; validate every URL it returns.
- Serper candidates must be validated with `harvestapi_get_profile`.
- Exa is a weak fallback (23% validated rate), but recovers some Serper misses.
- Crustdata and Prospeo are paid fallbacks for a custom route.
- **Name-validate every looked-up URL.** Company/title matching alone is not enough.
- Pilot on `--rows 0` before the full batch. Row ranges are inclusive.
- Extract the `/in/username` slug - strip query params and trailing slashes.
- Without company context, add role keywords to serper query.
