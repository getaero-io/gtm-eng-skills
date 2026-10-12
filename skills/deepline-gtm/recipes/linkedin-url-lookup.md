---
name: linkedin-url-lookup
description: 'Resolve LinkedIn profile URLs from name + company with strict identity validation to avoid false positives.'
---

# LinkedIn URL Lookup

Find LinkedIn profile URLs when you have a name, with or without company context.

## When to use

- "Find LinkedIn URLs for the contacts in my CSV"
- "Resolve LinkedIn profiles from names and companies"
- "I only have names; find their LinkedIn profiles"
- "Verify these LinkedIn URLs match the right people"

## Use the prebuilt first

Deepline has a maintained play for this: it finds candidate profiles and checks the chosen one against the live profile. `deepline search "person name and company -> LinkedIn profile URL"` lists it; read its inputs before running it.

```bash
deepline plays describe prebuilt/person-to-linkedin-harvestapi
deepline plays run prebuilt/person-to-linkedin-harvestapi --input '{"first_name":"Jane","last_name":"Smith","company_name":"Acme"}'
# CSV:
deepline plays run prebuilt/person-to-linkedin-harvestapi-batch --input '{"csv":"contacts.csv"}'
deepline runs export <run-id> --out contacts_with_linkedin.csv
```

Build your own sequence only when you need a different order of sources. Start from the play's source instead of a blank file:

```bash
deepline plays get prebuilt/person-to-linkedin-harvestapi --source --out ./fork.play.ts
deepline plays check ./fork.play.ts
```

## Steps for a custom sequence

Work through these in order and stop at the first validated match. Find the tool for each step with `deepline search`, cheapest first.

1. **Structured people search.** A people database that returns LinkedIn URLs directly, searched by name plus whatever you have: company, title, seniority. Free ones first.
2. **Web search scoped to LinkedIn.** Search `"Jane Smith" "Acme Corp" site:linkedin.com/in`. Without a company, use `"Jane Smith" site:linkedin.com/in` and add a title or a city when there are too many results. Keep only `linkedin.com/in/` results.
3. **Fetch the live profile and name-validate it.** Every candidate from steps 1 and 2 goes through the validation rules below. When the first candidate fails, try the next search result.
4. **Semantic search as a fallback.** A natural-language query such as "Jane Smith VP Sales at Acme Corp LinkedIn profile". It validated far less often than scoped web search in a 253-person test (23% against 74%), but it recovered a few of the misses.
5. **Paid person enrichment last.** A lookup by name and company domain that returns the profile URL alongside other fields.

In a play, each step is one `withColumn` that runs only for rows the earlier steps left empty.

## Scenarios

| You have                         | Do                                                                                                                                                                                                                                       |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name only                        | Steps 1 and 2 with any filter you have; add geography when results are ambiguous. Still ambiguous after that: ask for more context before spending credits.                                                                              |
| Name and company                 | Steps 1 and 2 with both, then step 4, then step 5 with the company domain.                                                                                                                                                               |
| Names from an event or RSVP list | Add an OR-chain of likely titles to the web query, such as `"Jane Smith" (RevOps OR "Sales Operations" OR GTM) site:linkedin.com/in`, then score results by keyword and location before picking one. Expect about 74% validated matches. |
| Nicknames                        | Search both forms: `("Mike" OR "Michael") "Smith" "Acme" site:linkedin.com/in`. For a batch, expand common variants (Bob/Robert, Liz/Elizabeth, Alex/Alexander) before the lookup.                                                       |

## Name validation (mandatory)

After fetching a profile, compare its name to the source name and **null out any URL where first and last name do not match**. Without this gate, 26% of web-search lookups returned the wrong person in the 253-person test. Company and title are supporting signals only.

- Last name: exact or substring, which handles hyphenated names but not single-character abbreviations.
- First name: exact, a prefix of 3 or more characters, a nickname, or a quoted nickname in the profile, such as `Yerachmiel 'Rocky' Katz`.
- Normalize accents (`Rodríguez` to `Rodriguez`) and strip punctuation and emoji before comparing.

The validation script and its fixtures ship with this skill:

```bash
python3 scripts/validate-linkedin-names.py --fixtures scripts/fixtures_name_validation.json
# 52 test cases, thresholds: precision >= 0.95, recall >= 0.85
```

## Key rules

- Prefer the maintained prebuilt unless you need a custom order.
- Name-validate every looked-up URL, whichever source returned it.
- Keep the `/in/username` slug; strip query parameters and trailing slashes.
- For a large batch, run a small slice of the CSV first and read its cost before scaling.
