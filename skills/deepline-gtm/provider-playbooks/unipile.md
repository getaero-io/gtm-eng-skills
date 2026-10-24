# Unipile

Use these actions only with the workspace's own Unipile API key and DSN
(customer BYOK). Deepline does not bill provider spend for Unipile.

Every Unipile v1 API route is a Deepline action, except binary file downloads
and native (password/cookie) account login. To connect or reconnect an account,
use `unipile_create_hosted_auth_link` and have the account owner open the URL.

## Find the account first

Start with `unipile_list_accounts`. Each account has an `id` (the `account_id`
other actions need) and a `type`, which decides what the account can do:

- Messaging: `LINKEDIN`, `WHATSAPP`, `INSTAGRAM`, `TELEGRAM`, `MESSENGER`,
  `TWITTER`, `SLACK`. Use the chat, message, and attendee actions.
- Email: `GOOGLE_OAUTH` (Gmail/Google Workspace), `OUTLOOK` (Microsoft 365 /
  Outlook), `MAIL` (IMAP), plus `ICLOUD` and `EXCHANGE`. Use the email, folder,
  and draft actions (`unipile_list_emails`, `unipile_send_email`, ...). Google
  and Microsoft accounts also carry calendars (`unipile_list_calendars`).
- LinkedIn also has profile, company, search, invitation, relation, post,
  comment, reaction, InMail, Sales Navigator, Recruiter, and job actions.

## Reads and writes

Reads list or fetch data. Every write action says in its description that it
sends, creates, changes, or deletes data in the customer's connected account;
delete actions start with "Destructive:". Before a write:

- confirm the exact recipient, target id, and text with the user;
- never run it again to "check" it worked; Deepline does not replay writes on
  an ambiguous upstream failure, and a repeat can send twice;
- read back with the matching list/get action instead.

`unipile_send_email` carries an Idempotency-Key, so Unipile returns the original
result for a replay of the same call. Sync actions (`unipile_resync_account`,
`unipile_sync_chat_history`, `unipile_sync_attendee_history`) start upstream
work and also report its status when called again.

## Limits

Unipile does not cap API calls itself; the limits that matter are the networks'.
Unipile's recommendations (https://developer.unipile.com/docs/provider-limits-and-restrictions):

- LinkedIn (per account): 80-100 invitations per day and about 200 per week on
  paid accounts (free accounts: far fewer, about 5 invitations with a note per
  month); about 100 profile retrievals per day; 1,000 search results per day
  (2,500 on Sales Navigator/Recruiter); 30-50 InMails per day; and by default
  at most 100 of any other action per day (messages, posts, comments,
  reactions, company profiles). Space actions at random intervals during
  working hours rather than at a fixed cadence. Poll relations and invitations
  only a few times a day.
- WhatsApp: keep new chats low, wait up to 24 hours after connecting an
  account before outreach, and leave 10-20 seconds between messages.
- Instagram: at most 100 actions per day and 10 per hour.
- Email: Gmail 50-100 sends per day (Workspace 100-150), starting at 20-50 for
  new accounts; Microsoft 365 allows 5,000 recipients and 1,000
  non-relationship recipients per day.
- Chats, messages, and attendees are synced server side by Unipile, so reading
  them does not touch the network's limits.

Deepline also applies best-effort guardrails before calling Unipile, per
connected account and rolling 24 hours. A blocked call returns a validation
error without an upstream request:

- LinkedIn: 100 profile retrievals, 100 messages (in-chat sends and non-InMail
  new chats), 40 InMails, 100 invitations, and 100 each of posts, comments,
  reactions, endorsements, and Sales Navigator/Recruiter member actions, with
  20 seconds between any two of these actions on one account. The 20 seconds
  is a Deepline guardrail, not a Unipile rule; Unipile asks for randomized
  spacing, so pace sends yourself as well.
- WhatsApp: 20 new chats, 15 seconds between sends, and no new chats in the
  first 24 hours after an account connects.

These guardrails live in one server process's memory: they reset on deploys
and cold starts, are not shared across instances, and apply only once the
account's channel is known (run `unipile_list_accounts` or `unipile_list_chats`
first in the same session). A send that Unipile rejects still counts. Stay
well under the network limits yourself.

## Identifiers

LinkedIn people are addressed by provider ID (`ACoAAA…`, Sales Navigator
`ACwAAA…`, Recruiter `AEwAAA…`) or public identifier (the last part of the
profile URL). For post comments and reactions use the post's `social_id`.
LinkedIn search takes filter ids, not text: look them up with
`unipile_linkedin_list_search_parameters`. WhatsApp recipients use the phone
number with the `@s.whatsapp.net` suffix. List endpoints paginate with
`cursor`; a `null` cursor means no more results.

File attachments, voice/video messages, and picture uploads are not supported
through Deepline (tool payloads are JSON).
