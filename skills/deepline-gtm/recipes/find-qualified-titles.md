---
name: find-qualified-titles
description: "Use when finding real role-holders at known company domains from an ICP, especially prompts like 'find all job titles at these companies', 'find qualified titles', 'find RevOps or marketing-ops buyers', or when exact title discovery should precede paid people search."
---

# Find Qualified Titles (company_titles -> ICP filter -> contacts)

Given a list of companies and an ICP described in plain English, find the people who
hold the matching roles - starting from each company's **real title roster**, not
keyword guesses. The title roster is free, the ICP match is one small LLM call per
company, and you only spend on contacts at the very end.

**Why exact-match (`title_lists`) is correct here - not a tradeoff.** Normally exact
title matching is brittle (it misses "Sr Director Marketing Operations" if you typed
"Senior Director..."). That problem does not exist in this pipeline, because the titles
come from `company_titles` - they are the company's *own verbatim roster strings*. The
LLM picks from that list, so every matched title is guaranteed to resolve. `title_lists`
then returns **all exact matches for every title you selected** (it's an OR across the
list, exact per entry): pick 5 titles -> get every person holding any of those 5. This is
the whole payoff of qualifying against the real roster first.

## When to use

- "Find all job titles at these companies" / "what roles exist at X".
- "Find the marketing ops / RevOps / Salesforce buyers at these accounts."
- "Find qualified titles" - user has accounts + an ICP and wants the real owners of a function.
- Any time you would otherwise guess `title_filters` keyword patterns and miss real titles
  (e.g. "Revenue Architect" instead of "VP Sales", "GTM Systems" instead of "Sales Ops").

Do **not** reach for paid people-search (`peopledatalabs_person_search`,
`crustdata_persondb_search`) for this. `company_titles` answers "what titles exist here"
for free; people-search is for when you already know the persona and need volume.

## Inputs

- A CSV (or just a list) of company domains. `domain` column required;
  `company_name` / `company_linkedin` optional.
- An ICP in plain English (the qualification criteria).

## Quick reference

| Step | What | Tool | Cost |
|------|------|------|------|
| 1 | Full title roster per company | `company_titles` | FREE |
| 1b | Flatten nested titles -> scalar column | `run_javascript` | 0 |
| 2 | LLM filters roster to ICP-matching titles | `deeplineagent` | cheap (1 small call/co) |
| 2b | Flatten `matched_titles` -> scalar column | `run_javascript` | 0 |
| 3 | Find all holders of the matched titles (exact) | `deepline_native_search_contact` (`title_lists`) | LinkedIn-only tier |
| 4 | (optional) reveal email / phone | `enrich_contact` / `enrich_phone` | only on kept rows |

## Why this shape (non-obvious rules, all verified live)

- **`title_lists`, not `title_filters`.** Matched titles are exact strings from the
  company's own roster - `title_lists` does exact, full-string matching and returns every
  holder of each title you pass. `title_filters` is boolean keyword/substring matching
  (e.g. `"operations"` also catches "People Operations Intern") - use that only when you
  did NOT qualify against the real roster first and want a broad keyword sweep.
- **`title_lists` works on `search_contact`, NOT `prospector`.** Verified live:
  `prospector` returns `422 unexpected key 'title_lists'` - its Deepline schema only
  accepts `title_filter`/`title_filters` + `limit`. (Upstream Waterfall once announced
  `title_lists` on Prospector, but Deepline's prospector parser does not wire it through;
  `search_contact` is the path that works today.)
- **`page_size` caps results per call - raise it for big lists.** `search_contact`
  defaults to a small page. If you select many titles or expect many holders, set
  `page_size` high enough (or paginate with `page_number`) so matches aren't silently
  truncated. Don't assume 10 is enough when you passed 30 titles.
- **Materialize nested output into flat columns before referencing it.** `company_titles`
  output sits at `result.data.output.titles`; `deeplineagent` JSON at `result.object.<field>`.
  A bare placeholder like `{{titles.output.titles}}` does NOT resolve, and a raw array
  placeholder breaks the JSON `--with` spec. Extract with `run_javascript` first.
  - Inside `run_javascript`, the alias is already unwrapped:
    `row.titles.result.data.output.titles` and `row.icp_match.object.matched_titles`.
  - When injecting the flattened array into a later payload, **quote the placeholder**:
    `"titles": "{{matched_titles}}"` (the interpolator substitutes the real array).

## Pipeline

```bash
# 1 - full title roster per company (FREE)
deepline enrich --input companies.csv --output titles.csv \
  --with '{"alias":"titles","tool":"company_titles","payload":{"domain":"{{domain}}"}}'

# 1b - flatten titles into a scalar column
deepline enrich --input titles.csv --output titles_flat.csv \
  --with '{"alias":"titles_flat","tool":"run_javascript","payload":{"code":"const t = row.titles?.result?.data?.output?.titles || []; return JSON.stringify(t);"}}'

# 2 - LLM filters the roster to the ICP (cheap)
deepline enrich --input titles_flat.csv --output matched.csv \
  --with '{
    "alias":"icp_match","tool":"deeplineagent",
    "payload":{
      "model":"openai/gpt-5.4-mini",
      "prompt":"ICP: <describe the buying-power roles, e.g. Marketing Ops, Sales Ops, RevOps, Salesforce admin/architect; senior IC and above; exclude recruiters/finance/support/plain reps>. From this exact title list return ONLY matching titles as exact strings: {{titles_flat}}. Return JSON.",
      "jsonSchema":{"type":"object","properties":{"matched_titles":{"type":"array","items":{"type":"string"}},"reasoning":{"type":"string"}},"required":["matched_titles","reasoning"],"additionalProperties":false}
    }
  }'

# 2b - flatten matched_titles (note JS-runtime path: object.matched_titles)
deepline enrich --input matched.csv --output matched_flat.csv \
  --with '{"alias":"matched_titles","tool":"run_javascript","payload":{"code":"const t = (row.icp_match && row.icp_match.object && row.icp_match.object.matched_titles) || []; return JSON.stringify(t.slice(0,100));"}}'

# 3 - find the people. search_contact returns all exact matches for every matched title
#   (LinkedIn only - email/phone redacted). Quote the array placeholder. Raise page_size
#   if you selected many titles so matches aren't truncated.
deepline enrich --input matched_flat.csv --output contacts.csv \
  --with '{
    "alias":"contacts","tool":"deepline_native_search_contact",
    "payload":{"domain":"{{domain}}","title_lists":[{"name":"icp","titles":"{{matched_titles}}"}],"page_size":50}
  }'
```

Contacts land at `contacts.result.data.output.persons[]` (name, title, `linkedin_url`,
seniority, department). Flatten to one row per contact before any email or phone reveal:

```bash
python3 .skills/deepline-gtm/scripts/flatten-search-contact-persons.py contacts.csv \
  --contacts-col contacts > contact_rows.csv
```

If the skill is installed outside the repo, use the same script from the installed
`deepline-gtm/scripts/` directory. This expansion is a file-level step, not another
`run_javascript` column, because one company can produce many people.

## Tiered contact reveal - buy only what the user needs

Step 3 (`search_contact`) returns LinkedIn only - the lowest upfront cost. **Ask the user
which channels they actually need before spending**, then add only the steps they pick:

| Tier | Tool | Returns |
|------|------|---------|
| LinkedIn only | `search_contact` (above) | name, title, LinkedIn (email/phone redacted) |
| + work email | `enrich_contact` on the kept `linkedin_url` (or `first_name`+`last_name`+`domain`) | + verified email |
| + phone | `enrich_phone` on priority contacts only | + phone (top picks only) |

Run email/phone only on the rows the user keeps; never blanket-enrich the full set.

Cost note: if the user wants emails on *most* contacts up front, `prospector` (boolean
`title_filters`, returns contact+verified email in one call) can be cheaper net than
`search_contact` + a separate `enrich_contact` per row - but `prospector` does **not**
support exact `title_lists`, so you lose the roster-exact precision. Use `search_contact`
when you want exact-title precision and LinkedIn-first; consider `prospector` only when
broad boolean matching is acceptable and you want emails in one shot.

## Notes

- Don't pre-trim the roster before the LLM filter - let the LLM pick from the full list,
  then raise `page_size` on step 3 so all holders of the matched titles come back.
- The LLM filter is only as good as the ICP prompt - be specific about include/exclude,
  and tell it to return **exact strings from the list** so titles map back to `title_lists`.
- v2 SDK equivalent: `docs-examples/sdk-v2/companies-to-contacts-icp-titles.play.ts`.
