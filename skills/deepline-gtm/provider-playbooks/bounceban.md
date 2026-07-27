# BounceBan Guidance

Use BounceBan to verify email deliverability, particularly when an address may be accept-all or protected by a secure email gateway.

- Use `bounceban_verify_single` for a single email. It may return `status: verifying`; poll `bounceban_get_single_status` with the returned id instead of submitting it again.
- Use `bounceban_verify_bulk` to create a batch from known email addresses. Poll its status and then retrieve results with the bulk result actions.
- `bounceban_check` is a quick syntax/domain classification. It does not perform SMTP verification and does not consume verification credits.
- The account and result retrieval actions are free. Do not submit an address again while its verification is still running.
- The waterfall endpoint is not available yet: its documented HTTP 408 can retain a billable task, which needs a non-2xx async settlement path in the shared V2 runtime.
