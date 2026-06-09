# CrustData V2 Guidance

Use autocomplete before structured CompanyDB or PersonDB searches when a field expects canonical values. Prefer in-DB search for broad list building and reserve realtime search/enrichment for freshness-sensitive cases.

For job data, use `crustdata_v2_job_search` for indexed job-listing discovery and `crustdata_v2_live_job_search` when the user explicitly needs current professional-network jobs for one known CrustData company id. Legacy dataset-table compatibility actions are hidden from discovery and should not be selected for new workflows.

Do not expose provider credit ladders to customers; Deepline tool pricing should remain Deepline-facing.
