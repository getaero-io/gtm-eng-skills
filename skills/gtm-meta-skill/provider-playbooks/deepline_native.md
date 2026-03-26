# Deepline Native — Agent Guidance

## Operation Selection

| Goal | Operation |
| ------ | ----------- |
| Find contacts at a company | `prospector` |
| Enrich a single contact | `enrich_contact` |
| Look up phone numbers | `enrich_phone` |
| Enrich a company record | `enrich_company` |
| Detect job changes (preferred) | `job_change` |
| LinkedIn lookup — dropleads fallback only | `search_contact` |

## Provider Positioning

- **`job_change`**: preferred job-change provider — charges only on confirmed moves.
- **`search_contact`**: secondary people search. **Dropleads is the default people search.** Use `search_contact` only when dropleads fails or is unavailable. Not yet tested enough to be the primary path.
- **`prospector` / `enrich_contact`**: use when dropleads + Apollo coverage is insufficient for the target segment.
- **`enrich_company`**: use sparingly — $1.00 per call. Only when firmographic data is required and other sources have been exhausted.

## Key Behaviors

### Launcher operations (prospector, enrich_contact, enrich_phone, enrich_company)

- These are async but the executor waits for completion and returns the final payload.
- The result includes `job_id` if you need to re-fetch later via finder operations.
- Finder endpoints (`*_finder`) are available for explicit polling by `job_id`.

### Synchronous operations (job_change, search_contact)

- Return results immediately. No job_id, no polling needed.

## Operation-Specific Notes

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

- Preferred job-change provider. Only charges $0.14 when status is `moved`.
- Field names match the API exactly: `company_domain`, `professional_email`, `contact_linkedin`, etc.
  Do NOT use `email`, `linkedin`, `domain` — those are wrong field names for this operation.
- Best coverage combo: `company_domain` + `contact_linkedin`.
- Minimum viable: `professional_email` alone.
- When status is `left`, `no_change`, or `unknown` — no charge, person object may be empty.
- Check `output.job_change_status` for the result.

### search_contact

- **Not the default people search — dropleads is.** Use as a fallback when dropleads fails or returns no results.
- Free and synchronous. Returns LinkedIn URLs only — email and phone are always redacted.
- Treat it as a company-scoped LinkedIn candidate finder, not a clean org-chart API. It is good at surfacing plausible current people at a company, but broad title queries can still return adjacent or support roles.
- Follow up with `enrich_contact` to get email/phone for returned LinkedIn URLs.
- Supports pagination: `page_number` and `page_size` (default 10, max 250 per page).
- Always include `domain` when you can. That is the strongest company anchor and produced the best live results.
- Prefer `title_filters` as `{name, filter}` objects. Use `title_lists` for exact title matching. Legacy string arrays are normalized into a single `title_lists` entry, but raw object form is clearer and more reliable.
- Best live pattern: function-specific leadership queries such as `VP Sales OR Head of Sales OR Director of Sales` or `VP Engineering OR Head of Engineering OR Director of Engineering`.
- Risky pattern: broad executive/founder searches such as `CEO OR Founder OR Co-Founder`, which can return noisy founder-adjacent or regional-entity matches.
- Live API `seniorities` support is narrower than our higher-level plays. Confirmed safe values: `Director`, `Manager`, `Entry`, `Senior`, `Partner`.
- Legacy `seniority`/portable values are normalized on the raw tool path where possible. Unsupported values such as `C-Level` are dropped rather than forwarded upstream.
- Keep `page_size` small for targeted lookups, usually `1-3`.
- Results are at `output.persons` — an array of person objects with `linkedin_url`.
- Inspect the returned `title` and current experience before trusting rank 1. Good queries return strong candidates; weak queries often return either `0 results` or obvious near-misses.

### enrich_company

- Pre-reserves $1.00 per launch. Use sparingly and only when firmographic data is needed.
- Input: domain is most reliable; linkedin also works.
- Result is nested under `output.company.*` — not top-level.

## Common Patterns

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
