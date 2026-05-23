# ZeroBounce Workflow Guidance

- Use `zerobounce_validate` as the final email validation gate before any outbound send. Treat `invalid`, `catch-all`, `spamtrap`, `abuse`, and `do_not_mail` statuses as non-send by default.
- Always inspect `sub_status` for granular failure reasons; `status` alone is not sufficient. For example, `do_not_mail` + `role_based` may still be acceptable for account-based campaigns whereas `do_not_mail` + `disposable` never is.
- Do not use `zerobounce_batch_validate`. ZeroBounce's batch endpoint currently returns 403 Access denied from Deepline egress, so Deepline disables the batch action and `deepline enrich` runs `zerobounce_validate` as single-email calls instead.
- Use `zerobounce_email_finder` only for person-level lookups. `domain` is required, and at least one of `first_name` or `last_name` must be present.
- Use `zerobounce_domain_search` for domain-only pattern discovery. It preserves the legacy Deepline public contract while mapping to the shared v2 `guessformat` endpoint.
- Use `zerobounce_activity_data` to check recent engagement before re-engaging cold contacts. An `active_in_days` over 365 suggests the address may be abandoned.
- When the `did_you_mean` field is non-empty, consider prompting the user or auto-correcting before sending.
