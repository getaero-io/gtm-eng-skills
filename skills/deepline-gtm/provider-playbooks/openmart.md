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

Pricing note: local-business search, business-ID search, and brand search cost 0.3 Openmart credits per returned company record; enrich company costs 0.3 credits per returned store record; find people and known-person lookup cost 8 credits per phone found and 3 credits per email found; technographics costs 2 credits when technologies are found. Openmart bills successful results only; failed calls and no-result calls should not consume provider credits.
