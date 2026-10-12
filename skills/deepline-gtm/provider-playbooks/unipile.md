# Unipile

Use these actions only with the workspace's own Unipile API key and DSN
(customer BYOK). Deepline does not bill provider spend for Unipile.

Start with `unipile_list_accounts` to find the connected `account_id` for the
channel (LinkedIn, WhatsApp, and others), then `unipile_list_chats` and
`unipile_get_chat_messages` to read history. Reads are not rate limited.

`unipile_send_message_in_chat` and `unipile_start_new_chat` send real messages
from the customer's connected account. Confirm the recipient and text before
executing them, and never retry a send to "check" it worked.

Deepline applies per-account guardrails before calling Unipile, and a blocked
call returns a validation error without an upstream request:

- LinkedIn: 100 profile retrievals, 100 messages (in-chat sends and non-InMail
  new chats), and 40 InMails per account per rolling 24 hours, with 20 seconds
  between outbound actions. Connection invites are not exposed; message
  existing connections or use InMail (`linkedin.inmail: true`, Premium only).
- WhatsApp: 20 new chats per account per rolling 24 hours, 15 seconds between
  sends, and no new chats in the first 24 hours after an account connects.

These guardrails are best-effort, not a guarantee. They are tracked in the
memory of one server process, so they reset on deploys and cold starts and
are not shared across instances. They apply only once the account's channel is
known: run `unipile_list_accounts` (or `unipile_list_chats`) first in the same
session. A send that Unipile rejects still counts toward the cap. Pace sends
yourself and stay well under the upstream limits.

LinkedIn people are addressed by provider ID (`ACoAAA…`, Sales Navigator
`ACwAAA…`) or public identifier (the last part of the profile URL). WhatsApp
recipients use the phone number with the `@s.whatsapp.net` suffix. List
endpoints paginate with `cursor`; a `null` cursor means no more results.
