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

Use `crustdata_v3_company_identify` before company enrich when the inbound identifier is fuzzy. It is free.

Do not use old PersonDB field paths with V3 unless a reviewed compatibility mapper converts them to the documented `2025-11-01` field vocabulary.
