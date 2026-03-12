# ZeroBounce Workflow Guidance

- Use `zerobounce_validate` as the final email validation gate before any outbound send. Treat `invalid`, `catch-all`, `spamtrap`, `abuse`, and `do_not_mail` statuses as non-send by default.
- Always inspect `sub_status` for granular failure reasons; `status` alone is not sufficient. For example, `do_not_mail` + `role_based` may still be acceptable for account-based campaigns whereas `do_not_mail` + `disposable` never is.
- Use `zerobounce_batch_validate` when validating 5+ emails at once (up to 100 per call). Same cost per email but fewer round-trips.
- Use `zerobounce_email_finder` (guessformat) to discover the most likely email pattern for a domain. Provide `first_name` and `last_name` for a personalized guess; omit them to get only the domain format pattern.
- Use `zerobounce_domain_search` to enumerate known email formats for a domain before constructing candidate addresses.
- Use `zerobounce_activity_data` to check recent engagement before re-engaging cold contacts. An `active_in_days` over 365 suggests the address may be abandoned.
- Use `zerobounce_credits` before large batch runs to verify sufficient balance. The 2,000 free monthly validations reset on your billing cycle.
- When the `did_you_mean` field is non-empty, consider prompting the user or auto-correcting before sending.
