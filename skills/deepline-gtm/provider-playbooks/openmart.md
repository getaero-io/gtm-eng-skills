# Openmart Guidance

Use Openmart for local-business and SMB workflows where store-level location data, brand records, shared company emails, known-person enrichment, employee discovery, or technology detection matter.

- Prefer `openmart_search_brands` when the workflow needs one row per company/brand.
- Prefer `openmart_search_businesses` when the workflow needs physical store records, ratings, categories, addresses, or location filters.
- Use `openmart_enrich_company` when the input is a website or social profile and the goal is to resolve matching Openmart records.
- Async launchers default to synchronous execution: they submit the batch, wait for completion, and return completed task results. Set `wait_for_completion: false` when the workflow only needs a `batch_id`.
- For manually managed async jobs, poll `openmart_get_batch_status`, list completed IDs with `openmart_get_batch_task_ids`, then fetch each result with `openmart_get_task_result`.
- Treat `null` arrays in brand responses as empty arrays.
- Openmart docs require `country` on each `/api/v2/brands/search` location entry.
- The configured provider token should be rotated if it has been pasted into chat, logs, or other plaintext surfaces.

Pricing note: Openmart provider spend is modeled at $0.0298 per Openmart credit. Search and brand search cost 0.3 credits per company record; enrich company costs 0.3 credits per store record; find people and known-person lookup cost 14 credits per phone found, 1 per email found, and 1 per name found; technographics costs 2 credits per company record.
