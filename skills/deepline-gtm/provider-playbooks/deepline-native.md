# Deepline Native — Agent Guidance

## Operation Selection

| Goal                                          | Operation                    |
| --------------------------------------------- | ---------------------------- |
| Find contacts at a company                    | `prospector`                 |
| Enrich a single contact                       | `enrich_contact`             |
| Look up phone numbers                         | `enrich_phone`               |
| Enrich a company record                       | `enrich_company`             |
| Detect job changes (preferred)                | `job_change`                 |
| People and LinkedIn profile search            | `search_contact`             |
| Get a company's available job titles for free | `company_titles`             |
| Search companies for free with SQL            | `free_simple_company_search` |

## Provider Positioning

- **`job_change`**: preferred job-change provider — charges only on confirmed moves.
- **`search_contact`**: secondary people search. **Standard managed pricing** — `0.56` Deepline credits per contact returned on successful calls. Zero returned contacts are free. Deepline `422` schema validation errors are rejected before provider execution and should not bill. Use it for company-specific or company-set LinkedIn candidate discovery; check current catalog options and pricing before selecting a provider.
- **`prospector` / `enrich_contact`**: use for company-scoped prospecting and contact enrichment.
- **`enrich_company`**: `0.98` Deepline credits per call. Use when firmographic data is required and other sources have been exhausted.

## Key Behaviors

- Rate budget split: `search_contact` uses the dedicated shared search-account budget (`300 RPM`); per-workspace limits come from `deepline billing entitlements`.
- Rate budget split: `prospector`, `enrich_contact`, `enrich_phone`, `enrich_company`, `job_change`, and related finder calls use the enrichment key/budget (`200 RPM`).
- When planning provider waterfalls inside a Play, do not treat `search_contact` and the enrichment-style Waterfall actions as one shared bucket.

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

- Preferred job-change provider. Only charges `1.96` Deepline credits when status is `moved`.
- Field names match the API exactly: `company_domain`, `professional_email`, `contact_linkedin`, etc.
  Do NOT use `email`, `linkedin`, `domain` — those are wrong field names for this operation.
- Best coverage combo: `company_domain` + `contact_linkedin`.
- Minimum viable: `professional_email` alone.
- When status is `left`, `no_change`, or `unknown` — no charge, person object may be empty.
- Check `output.job_change_status` for the result.

### search_contact

- Workspace-specific included usage, remaining quota, reset time, rate limits, and overage price come from `deepline billing entitlements`; those terms take precedence over the standard prices below.

- Search a known LinkedIn profile, people at one company, or people across companies by HQ country, industry, or headcount. Company-set mode requires `experience_start_date` or `experience_start_date_new_hire` (`YYYY-MM-DD`) and nonempty `title_filters` or `title_lists`. No company domain is required in this mode.
- Example: `{"company_location_countries":["United States"],"title_filters":[{"name":"gtm","filter":"GTM Engineer"}],"experience_start_date":"2020-01-01","page_size":10}`. This finds profiles within that date range; it does not establish the total number of GTM engineers worldwide.
- Uses the dedicated shared search-account budget (`300 RPM`), separate from enrichment. Per-workspace entitlement limits apply in addition to that shared budget.
- **Standard pricing: `0.56` Deepline credits per contact returned (post-deduct, billed on success). Zero returned contacts are free. Deepline `422` schema validation errors, such as `title_lists[0].titles` not being an array, happen before provider execution and should not bill.** A `page_size: 10` call that returns 10 contacts costs `5.6` credits — keep `page_size` small (`1-3`) for targeted lookups.
- Synchronous. Returns LinkedIn URLs and profile/title data only. There is no request option to reveal contact data: `professional_email`, `personal_email`, `mobile_phone`, `phone_numbers`, and `email_verified` are present in each person but always empty, and every returned profile still bills. Use `enrich_contact` / `enrich_phone` on the rows you keep.
- Treat returned profiles as candidates to verify. It is good at surfacing plausible current people at a company, but broad title queries can still return adjacent or support roles.
- To enrich selected results through Waterfall, pass the returned `linkedin_url` as `linkedin` to `enrich_contact`. Email enrichment costs `0.98` Deepline credits when a usable email is returned. Set `include_phones: true` for an additional `3.5` Deepline credits when phone data is returned: up to `4.48` Deepline credits for email plus phone. For phone-only enrichment, use `enrich_phone`, billed `3.5` Deepline credits per distinct returned number. These charges are additional to search. Redacted fields do not guarantee an available channel; this is a separate enrichment lookup, with no reveal-by-person-ID endpoint or search unlock flag in the documented API.
- Request subsequent pages by incrementing `page_number`.
- For a company-specific search, prefer `domain` as the company anchor. Omit it when searching a company set.
- `company_titles` returns the available current title roster at a known company for free. Select relevant titles and pass them in `title_lists`. Verify returned titles and current employment; matching can be loose.
- `free_simple_company_search` offers free SQL company search by industry, location, headcount, founding year, name, or domain. Use its returned domains as company anchors for people search. To discover values in that company corpus, use bounded aggregates such as `SELECT industry, COUNT(*) AS n FROM companies GROUP BY industry ORDER BY n DESC LIMIT 100`. Its industry taxonomy is separate from Waterfall people-search filters.
- For other people-search filter values, inspect the `company_employee_ranges` enum in `deepline describe search_contact` and the [Waterfall filter reference](https://docs.waterfall.io/v1/search-contact-filters) for department values. This integration normalizes seniorities to `Director`, `Manager`, `Entry`, `Senior`, or `Partner`; broader upstream-documented values may be dropped. Choose `company_industries` from Waterfall's [supported industry list](https://waterfall-io-public.s3.us-east-1.amazonaws.com/industries.txt), such as `Software Development`. Countries use full names such as `United States` or `France`. The integration exposes no country autocomplete/facet endpoint. Free-company-search industry values are not automatically interchangeable with Waterfall's list.
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

- Pre-reserves `0.98` Deepline credits per launch.
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

1. Use `search_contact` with domain + title_filters for company-scoped candidates.
2. Inspect the returned profiles and keep matches for the requested company and role.
3. Follow up with `enrich_contact` on the returned `linkedin_url` to get email.

### CLI quick checks

```bash
deepline describe deepline_native_job_change
deepline tools execute deepline_native_job_change --payload '{"company_domain":"stripe.com","professional_email":"jane@stripe.com"}'
deepline tools execute deepline_native_search_contact --payload '{"domain":"stripe.com","title_filters":[{"name":"eng","filter":"VP Engineering OR Head of Engineering"}],"page_size":5}'
deepline tools execute deepline_native_search_contact --payload '{"domain":"hubspot.com","title_filters":[{"name":"sales-leadership","filter":"VP Sales OR Head of Sales OR Director of Sales"}],"page_size":3}'
deepline tools execute deepline_native_search_contact --payload '{"domain":"openai.com","title_filters":[{"name":"eng-leadership","filter":"VP Engineering OR Head of Engineering OR Director of Engineering"}],"page_size":3}'
deepline tools execute deepline_native_enrich_company --payload '{"domain":"stripe.com"}'
```

### CSV job-change Play

Use a supplied Play when it already fits the task. When selecting or authoring one,
discover with `deepline plays search "job change"` and confirm the selected
contract with `deepline describe <play-ref>`. Tool IDs below are
starting hints: confirm them with `deepline describe <tool-id>`;
do not infer renamed IDs from provider names.

For a custom CSV workflow, save this as `job-change.play.ts`. It keeps the original
`domain` and `email` columns and adds the provider result without renaming the
operation's required payload fields.

```ts
import deepline from 'deepline';

export default async function (input: { csv: string }) {
  const contacts = await deepline.csv(input.csv, {
    required: ['domain', 'email'],
  });
  const rows = await deepline
    .dataset('contacts', contacts)
    .withColumn('job_change', (row) =>
      deepline.tools.execute({
        id: 'job_change',
        tool: 'deepline_native_job_change',
        input: { company_domain: row.domain, professional_email: row.email },
        description: 'Check whether this contact changed employers.',
      }),
    )
    .run({});
  return { rows };
}
```

```bash
deepline plays check job-change.play.ts
deepline plays run --file job-change.play.ts --csv contacts.csv --watch
```

Run only within the requested scope. For larger or uncertain authorized batches,
use a small representative input before scaling; a small supplied Play does not
need an extra pilot or repeated approval. Inspect the existing run with
`deepline runs get <run-id>` and follow its full-result/export commands to
save the rows (for example, to `contacts.csv.out.csv`). Inspection is read-only:
do not rerun, add paid enrichment, or repair the workflow just to retrieve results.

## Anti-Patterns to Avoid

- Do not assume `search_contact` is included: check `deepline billing entitlements` for any workspace-specific allowance and overage rate before estimating cost.
- Do not assume portable play-style seniorities like `C-Level` are valid on the raw `search_contact` tool.
- Do not use broad founder/CEO filters when you really want a functional leader at a company; they can produce noisy candidate sets.
- Do not use `email`/`linkedin`/`domain` field names for `job_change` — use the correct API names (`professional_email`, `contact_linkedin`, `company_domain`).
- Do not use `search_contact` expecting email or phone — those are always redacted.
- Do not loop finder endpoints more than 20 times — jobs that don't complete in ~5 minutes have failed.
- Do not run `prospector` without a title filter — results will be unbounded.
- Do not read `enrich_company` result at top level — data is nested under `output.company.*`.
