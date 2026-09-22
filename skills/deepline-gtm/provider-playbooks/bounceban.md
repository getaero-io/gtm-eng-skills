# BounceBan Guidance

Use BounceBan to verify email deliverability, particularly when an address may be accept-all or protected by a secure email gateway.

- Use `bounceban_verify_single` for a single email. It may return `status: verifying`; poll `bounceban_get_single_status` with the returned id instead of submitting it again.
- Use `bounceban_verify_bulk` to create a batch from known email addresses. A Play waits for the terminal result while it is running; its run log prints the BounceBan task ID and a ready-to-copy status command as soon as the task starts. Status checks back off to 30 seconds to reduce repeated polls; if the provider returns 429, Deepline waits for `Retry-After` before the next check.
- If a run is canceled or times out, the remote BounceBan task may still be active. Use `deepline tools execute bounceban_get_bulk_status --input '{"id":"<task-id>"}' --json` to check it, then `bounceban_get_bulk_emails` after it finishes. Status and result reads are free; the accepted verification task may still incur Deepline credits under its normal pricing.
- The account, status, and result retrieval actions are free. Do not submit an address again while its verification is still running.
- Completed raw responses may wrap the verdict at `toolResponse.raw.data.data.result` and its score at `toolResponse.raw.data.data.score`. Use `email_status` for the normalized Deepline verdict; do not treat a response envelope's outer `result` key as the email verdict.
- The waterfall endpoint is not available yet: its documented HTTP 408 can retain a billable task, which needs a non-2xx async settlement path in the shared V2 runtime.
