# Icypeas Workflow Guidance

- **Always start with counts.** Run `icypeas_count_people` or `icypeas_count_companies` before paid find operations. These are free and let you estimate result volume, refine filters, and avoid wasting credits on overly broad queries.
- **Email search is async.** `icypeas_email_search` returns a `SCHEDULED` status immediately. Poll `icypeas_read_results` with the returned `_id` to get the final email. Plan for this delay in workflows.
- **Use bulk search for volume.** When processing more than a handful of records, prefer `icypeas_bulk_search` over individual `icypeas_email_search` calls. Bulk supports up to 5,000 rows per batch. Monitor progress via `icypeas_read_bulk_files`.
- **Verify before sending.** Always run `icypeas_email_verification` on discovered emails before outbound. It costs only 0.1 credits. Treat `NOT_FOUND` and `DEBITED_NOT_FOUND` as non-deliverable.
- **LinkedIn scraping is powerful but costs more.** `icypeas_scrape_profile` (1.5 credits) returns rich contact data including phone numbers and verified emails. `icypeas_scrape_company` (0.5 credits) is cheaper for company-level data.
- **Find-people supports 16 filters.** Use include/exclude arrays for precise targeting: job title, company, location, skills, languages, school, keywords, and more. Start broad with count, then narrow.
- **Pagination uses token-based cursors.** For `icypeas_find_people` and `icypeas_find_companies`, pass the `token` from the previous response into the next request's `pagination.token`. Page size max is 200.
- **Free operations for planning:** `icypeas_count_people`, `icypeas_count_companies`, `icypeas_read_results`, `icypeas_read_bulk_files`, and `icypeas_subscription` cost zero credits. Use them liberally.
- **Check account status.** Run `icypeas_subscription` to verify credit balance before large operations.
