# Deepline Native — Agent Guidance

## Operation Selection

| Goal                                      | Operation        |
| ----------------------------------------- | ---------------- |
| Get all current job titles at a company   | `company_titles` |
| Find contacts at a company                | `prospector`     |
| Enrich a single contact                   | `enrich_contact` |
| Look up phone numbers                     | `enrich_phone`   |
| Enrich a company record                   | `enrich_company` |
| Detect job changes (preferred)            | `job_change`     |
| LinkedIn lookup — dropleads fallback only | `search_contact` |

## Provider Positioning

- **`company_titles`**: free. Returns every current job title Waterfall has for a domain. Use before contact discovery when you want LLM-assisted ICP matching against the real title list rather than guessing keyword filters - then feed matched titles to `search_contact` via `title_lists`. See the ICP title-match pipeline pattern below.
- **`job_change`**: preferred job-change provider — charges only on confirmed moves.
- **`search_contact`**: secondary people search. **Not free** — `0.56` Deepline credits per contact returned on successful calls. Zero returned contacts are free. Deepline `422` schema validation errors are rejected before provider execution and should not bill. **Dropleads is the default people search and is free per call.** Use `search_contact` only when dropleads fails or is unavailable. Not yet tested enough to be the primary path.
- **`prospector` / `enrich_contact`**: use when Dropleads coverage is insufficient for the target segment.
- **`enrich_company`**: use sparingly — `0.98` Deepline credits per call. Only when firmographic data is required and other sources have been exhausted.

## Key Behaviors

- Rate budget split: `search_contact` uses the dedicated search key/budget (`60 RPM`).
- Rate budget split: `prospector`, `enrich_contact`, `enrich_phone`, `enrich_company`, `job_change`, and related finder calls use the enrichment key/budget (`200 RPM`).
- When planning `deepline enrich` waterfalls, do not treat `search_contact` and the enrichment-style Waterfall actions as one shared bucket.

### Launcher operations (prospector, enrich_contact, enrich_phone, enrich_company)

- These are async but the executor waits for completion and returns the final payload.
- The result includes `job_id` if you need to re-fetch later via finder operations.
- Finder endpoints (`*_finder`) are available for explicit polling by `job_id`.

### Synchronous operations (job_change, search_contact, company_titles)

- Return results immediately. No job_id, no polling needed.

## Operation-Specific Notes

### company_titles

- Free. No per-call charge - counts only against the rate limit (same bucket as `search_contact`, 60 RPM).
- Input: `domain` (recommended) and/or `company_linkedin` handle. At least one is required.
- Output: `output.titles` - a flat string array of current job titles at the company (e.g. `["Head of Sales", "VP Engineering", "Software Engineer"]`).
- Returns 404-category error when the company is not in Waterfall's database - handle gracefully.
- **Primary use case:** feed `output.titles` to an LLM step with your ICP criteria. The LLM returns the subset of titles that match. Then pass those exact titles as `title_lists` to `search_contact` (the title_lists-capable contact tool), giving you real titles rather than guessed keyword patterns. See the ICP title-match pipeline below.
- Do not use `title_filters` (boolean expressions) on the contact follow-up - use `title_lists` (verbatim roster strings) so the match is tighter. It is still not exact: re-check returned titles.

```bash
deepline tools execute company_titles --payload '{"domain":"stripe.com"}'
# output.titles: ["Head of Revenue Operations", "VP Sales", "Account Executive", ...]
```

### prospector

- Requires one company identifier (domain, company_name, or linkedin) AND one title filter.
- Keep title filters specific — e.g. `vp sales OR director of sales` not just `sales`.
- Use `title_filters` (ordered array) to cascade: fill C-suite first, then VP, then Director.
- Use `location_countries` not `location_name` when filtering by country — exact names required.
- `verified_only: false` returns catch-all emails in addition to safe-to-send.
- `include_phones: true` runs phone enrichment on all returned contacts (adds cost).

### enrich_contact

- Best input: `linkedin` URL + `domain`.
- Raw tool accepts exactly one identity strategy: `email`, `linkedin`, `full_name + domain`, or `first_name + last_name + domain`.
- Name-only input is not valid. If you know the account domain, prefer `first_name + last_name + domain` over LinkedIn because it anchors the result to that company.
- Do not use for bulk enrichment — run one identity at a time.

### job_change

- Preferred job-change provider. Only charges `1.96` Deepline credits when status is `moved`.
- Field names match the API exactly: `company_domain`, `professional_email`, `contact_linkedin`, etc.
  Do NOT use `email`, `linkedin`, `domain` — those are wrong field names for this operation.
- Best coverage combo: `company_domain` + `contact_linkedin`.
- Minimum viable: `professional_email` alone.
- When status is `left`, `no_change`, or `unknown` — no charge, person object may be empty.
- Check `output.job_change_status` for the result.

### search_contact

- **Not the default people search — dropleads is.** Use as a fallback when dropleads fails or returns no results.
- Uses the dedicated Waterfall search key/budget (`60 RPM`), separate from the higher-throughput enrichment key.
- **Pricing: `0.56` Deepline credits per contact returned (post-deduct, billed on success). Zero returned contacts are free. Deepline `422` schema validation errors, such as `title_lists[0].titles` not being an array, happen before provider execution and should not bill.** A `page_size: 10` call that returns 10 contacts costs `5.6` credits — keep `page_size` small (`1-3`) for targeted lookups.
- Synchronous. Returns LinkedIn URLs and profile/title data only. There is no request option to reveal contact data: `professional_email`, `personal_email`, `mobile_phone`, `phone_numbers`, and `email_verified` are present in each person but always empty, and every returned profile still bills. Use `enrich_contact` / `enrich_phone` on the rows you keep.
- Treat it as a company-scoped LinkedIn candidate finder, not a clean org-chart API. It is good at surfacing plausible current people at a company, but broad title queries can still return adjacent or support roles.
- Follow up with `enrich_contact` to get email/phone for returned LinkedIn URLs.
- Supports pagination: `page_number` and `page_size` (default 10, max 250 per page).
- Always include `domain` when you can. That is the strongest company anchor and produced the best live results.
- The upstream applies an email-domain blocklist to `domain` and can reject real companies (e.g. `asics.com`, `business.cableone.net` as "disposable email provider"). That returns `DEEPLINE_NATIVE_SEARCH_CONTACT_DOMAIN_REJECTED` (422, no charge); retry the company with `company_name` or `company_linkedin` instead of `domain`.
- `company_name` must be at least 3 characters (upstream limit). For names like "2U", use `domain` or `company_linkedin`.
- Prefer `title_filters` as `{name, filter}` objects. Use `title_lists` for a named list of roster titles, but it is NOT exact matching: live results include titles that merely contain a listed title (e.g. "Staff Engineer Heat Transfer Group" for "Staff Engineer"; 128 of 380 results in one run). Re-check `title` on returned rows if you need exact matches. Legacy string arrays are normalized into a single `title_lists` entry, but raw object form is clearer and more reliable.
- Best live pattern: function-specific leadership queries such as `VP Sales OR Head of Sales OR Director of Sales` or `VP Engineering OR Head of Engineering OR Director of Engineering`.
- Risky pattern: broad executive/founder searches such as `CEO OR Founder OR Co-Founder`, which can return noisy founder-adjacent or regional-entity matches.
- Live API `seniorities` support is narrower than our higher-level plays. Confirmed safe values: `Director`, `Manager`, `Entry`, `Senior`, `Partner`.
- Legacy `seniority`/portable values are normalized on the raw tool path where possible. Unsupported values such as `C-Level` are dropped rather than forwarded upstream.
- Keep `page_size` small for targeted lookups, usually `1-3`.
- Results are at `output.persons` — an array of person objects with `linkedin_url`.
- Inspect the returned `title` and current experience before trusting rank 1. Good queries return strong candidates; weak queries often return either `0 results` or obvious near-misses.

### enrich_company

- Pre-reserves `0.98` Deepline credits per launch. Use sparingly and only when firmographic data is needed.
- Input: domain is most reliable; linkedin also works.
- Result is nested under `output.company.*` — not top-level.

## Common Patterns

### ICP title-match pipeline (company_titles -> LLM filter -> find qualified titles)

This is the **"find qualified titles"** campaign: the user has a list of companies and an
ICP described in plain English ("marketing ops / RevOps people who buy Salesforce",
"VP/Head of Sales at B2B SaaS"), and wants the real people who hold those roles -
without guessing keyword filters. It is the cheapest correct path because step 1 is
free and step 2 is a single small LLM call per company; you only spend on contacts at
the very end, and only for the tier the user actually needs.

1. `company_titles` - get every current title at the company (free, synchronous)
2. `deeplineagent` - given the title list + ICP criteria, return the matching titles as exact strings
3. `search_contact` with `title_lists` set to those matched titles - find the people

Rules, all verified live:

- **Use `title_lists`, not `title_filters`.** `title_lists` returns holders of each title
  you pass (OR across the list). The matched titles come straight from `company_titles`,
  so they are the company's own verbatim strings and resolve well. It is **not** exact
  full-string matching, though: live runs return titles that only contain a listed title
  (e.g. "Staff Engineer Heat Transfer Group" for "Staff Engineer"; 128 of 380 rows in one
  run). If you need exact holders, drop returned rows whose `title` is not in your list.
  `title_filters` is boolean keyword/substring matching - only reach for it when you did
  NOT qualify against the real roster and want a broad keyword sweep.
- **`title_lists` is supported by `search_contact`, NOT by `prospector`.** Verified live:
  `prospector` returns `422 unexpected key 'title_lists'` - its schema only accepts
  `title_filter`/`title_filters` and `limit`. (Upstream Waterfall announced `title_lists`
  on Prospector, but Deepline's prospector parser doesn't wire it through.) Use
  `search_contact` for the matched-title step.
- **Raise `page_size` for big title lists.** `search_contact` paginates; the default page
  is small. If you pass many titles, set `page_size` high enough (or page with
  `page_number`) so holders aren't silently truncated.
- **Placeholders can't reach nested tool output directly, and a bare array placeholder
  breaks the JSON `--with` spec.** `company_titles` output lands at
  `result.data.output.titles` and `deeplineagent` JSON lands at `result.object.<field>` in
  persisted cells - but inside `run_javascript` the alias is already unwrapped
  (`row.titles.result.data.output.titles`, `row.icp_match.object.matched_titles`).
  Materialize both into flat scalar columns with `run_javascript` first, then reference
  the flat column. A raw array placeholder (`"titles": {{matched}}`) fails to compile;
  wrap it in quotes (`"titles": "{{matched}}"`) so the interpolator substitutes the array.

**V1 CLI (deepline enrich) - copy/paste, validated end to end:**

```bash
# Step 1 - get the full title roster per company (FREE)
deepline enrich --input companies.csv --output titles.csv \
  --with '{"alias":"titles","tool":"company_titles","payload":{"domain":"{{domain}}"}}'

# Step 1b - flatten the nested titles array into a scalar column
deepline enrich --input titles.csv --output titles_flat.csv \
  --with '{"alias":"titles_flat","tool":"run_javascript","payload":{"code":"const t = row.titles?.result?.data?.output?.titles || []; return JSON.stringify(t);"}}'

# Step 2 - LLM filters the roster against the ICP, returns matched_titles[] (cheap)
deepline enrich --input titles_flat.csv --output matched.csv \
  --with '{
    "alias":"icp_match",
    "tool":"deeplineagent",
    "payload":{
      "model":"openai/gpt-5.4-mini",
      "prompt":"ICP: roles with budget authority over Salesforce / GTM-systems purchasing - Marketing Ops, Sales Ops, RevOps, GTM/Business Ops, Salesforce admin/architect. Senior IC and above; exclude recruiters, finance, support, and plain AE/SDR reps. From this exact title list return ONLY matching titles as exact strings: {{titles_flat}}. Return JSON.",
      "jsonSchema":{"type":"object","properties":{"matched_titles":{"type":"array","items":{"type":"string"}},"reasoning":{"type":"string"}},"required":["matched_titles","reasoning"],"additionalProperties":false}
    }
  }'

# Step 2b - flatten matched_titles into a scalar column (note the JS-runtime path: object.matched_titles)
deepline enrich --input matched.csv --output matched_flat.csv \
  --with '{"alias":"matched_titles","tool":"run_javascript","payload":{"code":"const t = (row.icp_match && row.icp_match.object && row.icp_match.object.matched_titles) || []; return JSON.stringify(t.slice(0,100));"}}'

# Step 3 - search_contact returns all holders of every matched title (LinkedIn only).
#   NOTE: title_lists is quoted ("{{matched_titles}}") so the array interpolates into JSON.
#   Raise page_size when you matched many titles so holders aren't truncated.
deepline enrich --input matched_flat.csv --output contacts.csv \
  --with '{
    "alias":"contacts",
    "tool":"deepline_native_search_contact",
    "payload":{
      "domain":"{{domain}}",
      "title_lists":[{"name":"icp","titles":"{{matched_titles}}"}],
      "page_size":50
    }
  }'

# Step 4 - flatten one company row into one row per returned contact.
# Use the same script from the installed deepline-gtm skill when outside the repo.
python3 .skills/deepline-gtm/scripts/flatten-search-contact-persons.py contacts.csv \
  --contacts-col contacts > contact_rows.csv
```

**Tiered contact reveal - only buy what the user needs.** Step 3 above is the cheapest
tier. Confirm with the user which contact channels they want before spending, then add
only the steps they need:

| Tier          | Tool                                        | Cost / result  | Returns                                          |
| ------------- | ------------------------------------------- | -------------- | ------------------------------------------------ |
| LinkedIn only | `search_contact`                            | cheapest       | name, title, LinkedIn URL (email/phone redacted) |
| + work email  | `enrich_contact` on the kept `linkedin_url` | + email cost   | adds verified email                              |
| + phone       | `enrich_phone` on priority contacts only    | most expensive | adds phone                                       |

Run the email/phone steps only on the rows the user keeps - never blanket-enrich the
full set. (Do not quote raw provider per-credit prices to customers; surface only
Deepline-facing cost tiers.)

**Single-company quick check:**

```bash
# Step 1 - get titles
deepline tools execute company_titles --payload '{"domain":"acme.com"}'

# Step 2 - LLM picks ICP-matching titles from the list (deeplineagent in enrich)

# Step 3 - search_contact with exact matched titles
deepline tools execute deepline_native_search_contact --payload '{
  "domain": "acme.com",
  "title_lists": [{"name":"icp","titles":["Head of Revenue Operations","VP Sales"]}],
  "page_size": 10
}'
```

### Prospect + Enrich flow

1. `prospector` — find contacts at target companies with title filters
2. `enrich_contact` — get verified email for specific LinkedIn URLs found
3. (Optional) `enrich_phone` — get phone for priority contacts

### Job change signal flow (on CRM contacts)

1. `job_change` with `company_domain` + `professional_email`
2. If `job_change_status === "moved"`: use `person.company_domain` and `person.linkedin_url` to target at new company
3. If `job_change_status === "left"` or `"no_change"`: no action needed, no charge

### LinkedIn lookup fallback flow

1. Try dropleads first (`dropleads_search_people`) — it is the default.
2. If dropleads fails or returns no results, fall back to `search_contact` with domain + title_filters.
3. Follow up with `enrich_contact` on the returned `linkedin_url` to get email.

### CLI quick checks

```bash
deepline tools get deepline_native_job_change
deepline tools execute deepline_native_job_change --payload '{"company_domain":"stripe.com","professional_email":"jane@stripe.com"}'
deepline tools execute deepline_native_search_contact --payload '{"domain":"stripe.com","title_filters":[{"name":"eng","filter":"VP Engineering OR Head of Engineering"}],"page_size":5}'
deepline tools execute deepline_native_search_contact --payload '{"domain":"hubspot.com","title_filters":[{"name":"sales-leadership","filter":"VP Sales OR Head of Sales OR Director of Sales"}],"page_size":3}'
deepline tools execute deepline_native_search_contact --payload '{"domain":"openai.com","title_filters":[{"name":"eng-leadership","filter":"VP Engineering OR Head of Engineering OR Director of Engineering"}],"page_size":3}'
deepline tools execute deepline_native_enrich_company --payload '{"domain":"stripe.com"}'
```

### `deepline enrich` usage

```bash
deepline enrich --input contacts.csv --output contacts.csv.out.csv \
  --with '{"alias":"job_change","tool":"deepline_native_job_change","payload":{"company_domain":"{{domain}}","professional_email":"{{email}}"}}'
```

## Anti-Patterns to Avoid

- Do not default to `search_contact` for people search — use dropleads first.
- Do not assume portable play-style seniorities like `C-Level` are valid on the raw `search_contact` tool.
- Do not use broad founder/CEO filters when you really want a functional leader at a company; they can produce noisy candidate sets.
- Do not use `email`/`linkedin`/`domain` field names for `job_change` — use the correct API names (`professional_email`, `contact_linkedin`, `company_domain`).
- Do not use `search_contact` expecting email or phone — those are always redacted.
- Do not loop finder endpoints more than 20 times — jobs that don't complete in ~5 minutes have failed.
- Do not run `prospector` without a title filter — results will be unbounded.
- Do not read `enrich_company` result at top level — data is nested under `output.company.*`.
- Do not pass `company_titles` output into `title_filters` (boolean keyword expressions) - use `title_lists` (exact string arrays) on `search_contact` so the match uses the actual titles returned, not keywords derived from them (still re-check returned titles; matching is not exact). Note `prospector` does not accept `title_lists`; use `search_contact` for the matched-title step.
