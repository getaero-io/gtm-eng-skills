# Bloomberry Agent Guidance

Use Bloomberry when the user needs account-level B2B technographic signals or hiring signals.

Prefer:

- `bloomberry_get_company_tech_stack` when you already know a company domain and need the vendors it currently uses.
- `bloomberry_get_tech_stack_changes` when the user needs recent adoption, churn, or usage signals. Provide exactly one of `category` or `vendor_name`.
- `bloomberry_get_current_customers` when building a list of companies currently using a vendor or category. Provide exactly one of `category` or `vendor_name`.
- `bloomberry_list_vendors` before vendor-filtered searches when the exact vendor/category name is uncertain.
- `bloomberry_search_job_postings` for hiring intent. Provide at least one of `keyword`, `normalized_job_titles`, or `domain`.

Use `limit` conservatively on result-list endpoints because Bloomberry charges credits per returned signal, customer, or job posting.
