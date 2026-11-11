# Resend

Connect your own Resend API key. Sending-only keys cannot manage contacts,
templates, domains or webhooks; use an appropriately scoped account key for those actions.
Deepline does not charge provider usage for this connector. Resend's own quotas and billing apply.

Use contacts and topics to inspect subscription eligibility before sending marketing.
Set `topic_id` on individual sends to request Resend's topic enforcement. A topic's
default subscription can permit unknown contacts, so choose the default deliberately.
Contact/topic opt-outs and bounce/complaint suppressions are different controls.
Marketing mail still needs a visible unsubscribe link and RFC 8058 headers in the
email body's `headers` object. This connector does not create an unsubscribe handler.

`resend_emails_send` submits an email; it does not prove inbox placement or delivery.
Use its ID with `resend_emails_get`, or configure delivery webhooks and inspect their
events. Pagination uses the provider's `after`/`before` cursors; do not pass both.
Keep the same `idempotency_key` for retries of the same email. In a Play, an omitted
key is derived from the runtime step identity. Resend retains keys for 24 hours,
so persist send history and reconcile unknown outcomes before retrying later.
Never automatically resend through another provider after an ambiguous timeout.

Create and publish a new template version before using its ID in a send. Broadcast
creation can send immediately when `send` is true; use an unsent draft for review.
Broadcast sending and webhook event replay are writes, not read-only test actions.
Webhook configuration does not deploy a receiver: the receiving application must
verify signatures, deduplicate events and persist delivery/subscription state.

All 143 reviewed account actions are exposed, including inboxes, imports,
automations/events, API keys, OAuth grants, legacy audiences and suppressions.
OAuth application registration and the interactive token flow are not implemented.
Some endpoints require account enrollment; an access error is not an empty list.

Use `body` for the batch email array. Import `file` is literal CSV text, not a path
or URL; it uploads as multipart data. Prefer `on_conflict: skip` for migrations
unless reviewed reconciliation requires updates. Imports do not establish consent.
Resend's 50 MB upload ceiling is not a Deepline request-size guarantee: the CSV
travels in JSON and deployment limits may be lower. Use small imports or the
provider's native upload surface for large files. Events and broadcast sends do
not support the connector's retry key; reconcile uncertain outcomes before replay.

Native automation stop is campaign-wide, not a per-person pause. Keep onboarding
reply/booking pauses and manual resume in Deepline's enrollment state. Finish the
series after product activation. Check state immediately before each send.
Preserve equivalent-lesson history across campaign versions and email providers.

Suppression removal does not restore consent. Contact deletion is not unsubscribe.
API key creation and webhook secret rotation return credentials: store securely,
never print in logs or reports.
Documented API-key tokens and webhook creation/rotation signing secrets are
returned to the authenticated caller; diagnostic and metadata projections remain
redacted. Do not treat an unfiltered tool response as a safe diagnostic artifact.
Inbox reply/forward/send-draft sends real email; creating a draft is not
authorization to send it. Domain/key/contact/automation
deletion, suppression removal, broadcast sending and secret rotation need deliberate
operator intent. Do not use them as connection tests.
