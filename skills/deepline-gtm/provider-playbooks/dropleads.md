# Dropleads Playbook

Use Dropleads as a two-phase flow: low-cost contact discovery first, paid enrichment second. Do not use Dropleads people search as the first step for account discovery.

## 1) Start with low-cost discovery

- Use `dropleads_get_lead_count` to size the audience before any paid call.
- Use `dropleads_search_people` to inspect masked contacts and validate ICP filters (free).
- Use `dropleads_search_people` after you already have target account domains, by passing `filters.companyDomains`. It is a contact search primitive, not a dependable way to discover target accounts.
- Do not build joins or account-discovery flows that depend on every returned lead having `companyDomain`. Treat returned `companyDomain` as optional; if you need account domains as the source of truth, use a company-native search/enrichment tool first.
- Tighten filters until sample rows clearly match role, industry, and geo expectations.
- Key filter fields: `filters.jobTitles`, `filters.seniority` (C-Level/VP/Director/Manager/Senior/Entry/Intern), `filters.industries`, `filters.departments`, `filters.companyDomains`, `filters.employeeRanges`, `filters.personalCountries.include` (for geo), `pagination.page`, `pagination.limit`.

### Filter best practices

All Dropleads filters nest under the `filters` object. Pagination nests under `pagination`. The canonical payload shape:

```json
{
  "filters": {
    "companyDomains": ["microsoft.com"],
    "jobTitles": ["CTO", "VP Engineering"],
    "seniority": ["C-Level", "VP", "Director"],
    "personalCountries": { "include": ["United States"] }
  },
  "pagination": { "page": 1, "limit": 25 }
}
```

**Quick reference — correct filter keys:**

| Filter    | Correct key                         | Why                                                                                                                                                                                                                                                          |
| --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Company   | `filters.companyDomains`            | Exact domain match for known accounts. Prefer this when you already have domains; do not rely on people-search results to discover a complete account-domain list. `companyNames` does fuzzy substring matching — "Microsoft" pulls in unrelated businesses. |
| Country   | `filters.personalCountries.include` | Array inside a nested object.                                                                                                                                                                                                                                |
| Seniority | `filters.seniority`                 | Exact values only: `C-Level`, `VP`, `Director`, `Manager`, `Senior`, `Entry`, `Intern`.                                                                                                                                                                      |
| Industry  | `filters.industries`                | Exact strings from Dropleads. Pilot with a broad search first when unsure.                                                                                                                                                                                   |

### Geo filters are best-effort, not verified

Dropleads geo filters (`personalCountries` / `personalStates` / `personalCities` and the `organization*` equivalents) match against **self-reported, LinkedIn-sourced location text** — they are not verified against the contact's actual location. Treat them accordingly:

- **City-level is the loosest match and leaks.** `personalCities` can return contacts whose stated city loosely matches even when their real location differs, and non-US contacts can appear under a US-city filter (e.g. a Bulgarian contact surfacing under `personalCities: San Francisco` + `personalCountries: United States`). Country/state are more reliable.
- **Person vs. company location are different fields.** `personal*` filters the contact's own location; `organization*` filters the company HQ. Don't conflate them — filtering a remote employee by company HQ city (or vice versa) drops or leaks legitimate matches.
- **Verify geo when precision matters.** Combine `personalCountries`/`personalStates` with `personalCities`, then post-filter the returned leads on their `country`/`state`/`city` (and exclude obvious mismatches) before trusting the result or spending on enrichment. Do not assume the filter alone guarantees the geo.

## 2) Escalate paid calls only for shortlisted targets

- Run `dropleads_email_finder` for contacts that passed the discovery pass.
- Run `dropleads_mobile_finder` only when phone is required for the workflow.
- Keep pilots small first, then scale after quality checks pass.

## 3) Gate outbound with verifier status

- Treat `invalid`, `catch_all`, and `unknown` as non-send by default.
- Treat `valid` as the only status that passes automatic send gates.
- Respect `credits_charged` in responses for post-execution billing accuracy.

## 4) Practical sequencing

1. Count segment (`dropleads_get_lead_count`).
2. Sample segment (`dropleads_search_people`).
3. Pre-score titles with `run_javascript` if looking for a specific profile (e.g. founders, GTM engineers).
4. Scrape LinkedIn profiles with `apify_run_actor_sync` for work history/signals (preferred over `call_ai` — structured data, faster, cheaper).
5. Extract signals with `run_javascript` from Apify output (e.g. founder detection, hiring signals).
6. Enrich emails via waterfall (`dropleads_email_finder` first, then other providers).
7. Verify candidate emails (`dropleads_email_verifier` or `leadmagic_email_validation`).
8. Expand only after pilot quality is confirmed.

## 5) Account discovery boundary

For account-based pipelines, start with a company-native source such as `apollo_company_search` or another provider that returns account domains as first-class results. Feed those domains into Dropleads via `filters.companyDomains` to find contacts at known accounts. Dropleads may include `companyDomain` on returned people, but it is not guaranteed enough to be the join key that creates the account universe.
