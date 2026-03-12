# Dropleads Playbook

Use Dropleads as a two-phase flow: low-cost segment discovery first, paid enrichment second.

## 1) Start with low-cost discovery

- Use `dropleads_get_lead_count` to size the audience before any paid call.
- Use `dropleads_search_people` to inspect masked contacts and validate ICP filters (free).
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
    "personalCountries": {"include": ["United States"]}
  },
  "pagination": {"page": 1, "limit": 25}
}
```

**Quick reference — correct filter keys:**

| Filter | Correct key | Why |
|--------|------------|-----|
| Company | `filters.companyDomains` | Exact domain match. `companyNames` does fuzzy substring matching — "Microsoft" pulls in unrelated businesses. 53K+ results at microsoft.com confirmed. |
| Country | `filters.personalCountries.include` | Array inside a nested object. |
| Seniority | `filters.seniority` | Exact values only: `C-Level`, `VP`, `Director`, `Manager`, `Senior`, `Entry`, `Intern`. |
| Industry | `filters.industries` | Exact strings from Dropleads. Pilot with a broad search first when unsure. |

## 2) Escalate paid calls only for shortlisted targets

- Run `dropleads_email_finder` for contacts that passed the discovery pass.
- Run `dropleads_mobile_finder` only when phone is required for the workflow.
- Keep pilots small first, then scale after quality checks pass.

## 3) Gate outbound with verifier status

LeadMagic returns five distinct statuses — use this table as the send gate:

| Status | Send? | Notes |
|---|---|---|
| `valid` | ✅ Yes | SMTP-verified, <1% bounce |
| `valid_catch_all` | ✅ Yes | Engagement-confirmed on catch-all domain, <5% bounce — treat same as `valid` |
| `catch_all` | ✅ Yes | Domain-level only, unverified, but sendable (same risk as Clay's default) |
| `unknown` | ❌ No | Server no response; don't send |
| `invalid` | ❌ No | Will bounce; discard |

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
