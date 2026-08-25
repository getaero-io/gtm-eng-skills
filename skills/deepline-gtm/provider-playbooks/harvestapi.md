# HarvestAPI

Choose the action for the LinkedIn resource you need. Use `harvestapi_get_*` for a known profile, company, job, post, group, ad, or engagement target. Use `harvestapi_search_*` for discovery. HarvestAPI interaction actions that send messages or manage connections are intentionally unavailable.

For company employee searches, use `harvestapi_search_leads` and pass one or more LinkedIn company URLs or identifiers in `currentCompanies`. HarvestAPI matches this filter by company name even when an ID or URL is provided, so discard results whose `currentPositions.companyId` does not match the intended company ID. Generate a random `sessionId` and reuse it on later pages. For other paginated actions, preserve the returned `paginationToken` when the input supports it. For profile posts, comments, and reactions, `pagination.totalPages: 0` means the total page count is unknown; totals may be inaccurate even when results are present. A returned `paginationToken` guarantees another page exists, so use it rather than totals to decide whether to continue.

For profile posts, `postedLimit` may return posts outside the requested duration. Prefer `scrapePostedLimit` when a date cutoff is required, but its enforcement has not been live-verified. HarvestAPI documents no numeric result-limit parameter for this endpoint; request page 1 and truncate `elements` client-side when a fixed count is needed.

Use `harvestapi_get_profile` with `main: "true"` when the smaller main-profile response is sufficient. Set `findEmail: "true"` only when email discovery is needed because it costs more. Set `skipSmtp: "true"` only when a non-SMTP email lookup is acceptable.

HarvestAPI plan limits are concurrent-request limits, not per-minute quotas. Deepline uses its Business subscription's 40-request concurrency limit and applies shared retry/backoff handling for transient failures.
