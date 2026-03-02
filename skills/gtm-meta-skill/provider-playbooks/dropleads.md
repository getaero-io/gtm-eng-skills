# Dropleads Playbook

Use Dropleads as a two-phase flow: low-cost segment discovery first, paid enrichment second.

## 1) Start with low-cost discovery

- Use `dropleads_get_lead_count` to size the audience before any paid call.
- Use `dropleads_search_people` to inspect masked contacts and validate ICP filters (free).
- Tighten filters until sample rows clearly match role, industry, and geo expectations.
- Key filter fields: `filters.jobTitles`, `filters.seniority` (C-Level/VP/Director/Manager/Senior/Entry/Intern), `filters.industries`, `filters.departments`, `filters.companyDomains`, `filters.employeeRanges`, `filters.personalCountries.include` (for geo), `pagination.page`, `pagination.limit`.

### Common filter mistakes

- **Country filter**: Use `filters.personalCountries.include` (array), NOT `filters.countries`. Example: `"personalCountries": {"include": ["United States"]}`.
- **Seniority values**: Must be exact: `C-Level`, `VP`, `Director`, `Manager`, `Senior`, `Entry`, `Intern`. Not lowercase, not abbreviated.
- **Industry values**: Use exact strings from Dropleads. When unsure, pilot with a broad search first.

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
