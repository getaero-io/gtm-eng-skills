# CrustData V3 guidance

Use autocomplete before search when filter values are uncertain. Autocomplete is free and reduces expensive zero-result searches.

Use indexed search for discovery:

- `crustdata_v3_person_search`
- `crustdata_v3_company_search`
- `crustdata_v3_job_search`

Keep `limit` strict. Search is billed per returned result, not by matched `total_count`.

Use enrich after narrowing candidates:

- `crustdata_v3_person_enrich` for full cached person profiles.
- `crustdata_v3_person_contact_enrich` for contact-only lookups.
- `crustdata_v3_company_enrich` for full company records.

Use `crustdata_v3_company_identify` before company enrich when the inbound identifier is fuzzy. It is free. Prefer a domain or LinkedIn company URL. Name-only matching can return unrelated companies even at `confidence_score: 1.0`; treat those results as candidates and verify an independent identifier before changing stored names or domains.

Some `crustdata_v3_person_enrich` field groups (for example `certifications`, per CrustData's own docs) may 403 with a permission error depending on the account's CrustData entitlement — this is not restricted in the schema because a different account may have different access. If a caller hits `PROVIDER_AUTHORIZATION_FAILED` requesting a specific field group, drop it and retry without that group rather than assuming every documented group is universally available to every account.

Do not use old PersonDB field paths with V3 unless a reviewed compatibility mapper converts them to the documented `2025-11-01` field vocabulary.
