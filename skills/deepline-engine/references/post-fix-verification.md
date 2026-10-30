# Post-fix verification

This reference distinguishes engine authoring from verification of a Deepline
product fix. It does not authorize an engine-authoring pilot in a personal or
third-party customer workspace.

When a product fix depends on a real paid-provider response or Production usage
admission or settlement, its acceptance check is one synthetic case through the
deployed public SDK, CLI, API, or Play entrypoint. Run only after the fix reaches
Production; provider-free fixtures remain the pre-release check.

Use either a designated Deepline-owned internal Production workspace or the
operator's personal workspace. Personal ownership requires the operator's
explicit identification and the authenticated `owner` role. Access, membership,
or a workspace name alone does not establish ownership. Never use third-party
customer credentials, credits, or data.

Before dispatch, verify the Production host and selected workspace using the
CLI's authentication and workspace commands. Read the funded balance, billing
status, and automatic-recharge status. Require automatic recharge to be off and
idle; do not change billing settings to satisfy this gate. Inspect current
pricing and bound the entire case to at most **5 Deepline credits**, honoring any
lower user cap. A Deepline operator must also establish the separate internal
provider-cost limit before dispatch. If ownership, existing funding, recharge
state, pricing, or an enforceable limit cannot be verified, report the check as
blocked. Do not buy, grant, transfer, or top up credits.

Prefer a read-only provider action. A provider write requires a disposable
resource in an approved internal provider account, an exact effect and cleanup
path, and cleanup included in the bound. Sending or publishing requires a
specifically authorized operator-controlled test destination. Do not modify
pre-existing third-party resources.

Keep one stable idempotency key or retained run identity. If the response is
lost, inspect the retained execution before submitting again. Do not retry an
ambiguous paid operation with a new identity or advance to another case after a
failure.

Verify the deployed revision, a usable real provider result, durable terminal
outcome, settled Deepline usage within the quote, and unchanged recharge and
unrelated billing state. A fixture, cache-only hit, provider-access failure, or
pre-provider admission denial does not prove the paid path.

Keep the normal settled charge and usage record. Restore only separately
allocated fixture funding through its existing accounting path, after retaining
settlement evidence; do not refund or grant credits to erase the test. Report
the sanitized input, revision, outcome, and settled Deepline usage. Keep
credentials, stable workspace identifiers, and internal provider costs out of
customer reports.

This one-case acceptance does not replace the new-engine author's multi-record
pilot and replay check. It does not authorize purchases, payment or plan changes,
a larger batch, trigger installation, or unrelated external work.
