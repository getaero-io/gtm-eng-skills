# Openmart Guidance

Use Openmart for local-business and SMB workflows where store-level location data, brand records, shared company emails, known-person enrichment, employee discovery, or technology detection matter.

- Prefer `openmart_search_brands` when the workflow needs one row per company/brand.
- Prefer `openmart_search_businesses` when the workflow needs physical store records, ratings, categories, addresses, or location filters.
- `openmart_search_businesses` and `openmart_search_brands` return contacts locked: every row has `contacts_locked: true` (under `content` for business search, top level for brand search) and empty phone and email arrays. Each row is still billed, at a lower rate than a row with contacts unlocked. `has_contact_info`, `has_business_phone`, and `has_business_email` describe Openmart inventory, not values in the response. If the goal is contacts, search with a small `limit`, then use `openmart_lookup_business_email` for company emails (billed per email found) or `openmart_find_people` for named decision makers with emails or phones. Openmart's company or store phone lookup is not exposed as a Deepline tool yet. Do not page through a full search expecting contacts.
- Use `openmart_enrich_company` when the input is a website or social profile and the goal is to resolve matching Openmart records.
- Async launchers default to synchronous execution: they submit the batch, wait for completion, and return completed task results. Set `wait_for_completion: false` when the workflow only needs a `batch_id`.
- For manually managed async jobs, poll `openmart_get_batch_status`, list completed IDs with `openmart_get_batch_task_ids`, then fetch each result with `openmart_get_task_result`.
- Treat `null` arrays in brand responses as empty arrays.
- Openmart docs require `country` on each `/api/v2/brands/search` location entry.
- The configured provider token should be rotated if it has been pasted into chat, logs, or other plaintext surfaces.

Pricing note: search, enrichment, and technographics are billed per returned record, and phone lookups are the most expensive result type — bound `limit` when exploring. Openmart bills successful results only; failed calls and no-result calls are not billed. Deepline credit pricing for these actions is generated from the provider pricing metadata and rendered on the public provider pages.
