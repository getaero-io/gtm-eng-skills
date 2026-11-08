Use Lemlist for multi-channel outbound campaigns (email + LinkedIn). Full campaign lifecycle management is available.

- Keep activation behind enrichment/verification gates — only push contacts that have been validated.
- Resolve campaign IDs from `lemlist_list_campaigns` before any write operation.
- Insert contacts in batches of 10–25 and re-check campaign stats after writes.
- Always review in Lemlist UI before starting campaigns — use the `web_url` returned by create/update operations.

## Workflow

1. **Create or list campaigns** before adding contacts.
2. **Add sequence steps** (email, LinkedIn invite, LinkedIn DM) to define the outreach flow.
3. **Add contacts** in small batches (10–25), then check stats to verify.
4. **Review in Lemlist UI** before starting — use the `web_url` returned by create/update operations.
5. **Monitor** via activities and inbox threads.

## Quick Reference

### Campaigns

```bash
deepline run lemlist_list_campaigns --input '{}'
deepline run lemlist_create_campaign --input '{"name":"My Campaign"}' --dry-run
deepline run lemlist_create_campaign --input '{"name":"My Campaign"}'
deepline run lemlist_pause_campaign --input '{"campaign_id":"cam_abc123"}' --dry-run
deepline run lemlist_pause_campaign --input '{"campaign_id":"cam_abc123"}'
deepline run lemlist_update_campaign --input '{"campaign_id":"cam_abc123","name":"New Name"}' --dry-run
deepline run lemlist_update_campaign --input '{"campaign_id":"cam_abc123","name":"New Name"}'
deepline run lemlist_get_campaign_stats --input '{"campaign_id":"cam_abc123"}'
```

### Sequences

```bash
deepline run lemlist_get_campaign_sequences --input '{"campaign_id":"cam_abc123"}'
deepline run lemlist_add_sequence_step --input '{"sequence_id":"seq_abc","type":"linkedinInvite","message":"Hi!","delay":0}' --dry-run
deepline run lemlist_add_sequence_step --input '{"sequence_id":"seq_abc","type":"linkedinInvite","message":"Hi!","delay":0}'
deepline run lemlist_update_sequence_step --input '{"sequence_id":"seq_abc","step_id":"stp_xyz","type":"linkedinSend","delay":2}' --dry-run
deepline run lemlist_update_sequence_step --input '{"sequence_id":"seq_abc","step_id":"stp_xyz","type":"linkedinSend","delay":2}'
deepline run lemlist_delete_sequence_step --input '{"sequence_id":"seq_abc","step_id":"stp_xyz"}' --dry-run
deepline run lemlist_delete_sequence_step --input '{"sequence_id":"seq_abc","step_id":"stp_xyz"}'
```

### Leads

```bash
deepline run lemlist_add_to_campaign --input '{"campaign_id":"cam_abc","contacts":[{"email":"ada@example.com","first_name":"Ada","last_name":"Lovelace","timezone":"America/Chicago"}]}' --dry-run
deepline run lemlist_add_to_campaign --input '{"campaign_id":"cam_abc","contacts":[{"email":"ada@example.com","first_name":"Ada","last_name":"Lovelace","timezone":"America/Chicago"}]}'
deepline run lemlist_export_campaign_leads --input '{"campaign_id":"cam_abc","state":"interested"}'
deepline run lemlist_pause_lead --input '{"lead_id":"lea_abc"}' --dry-run
deepline run lemlist_pause_lead --input '{"lead_id":"lea_abc"}'
deepline run lemlist_resume_lead --input '{"lead_id":"lea_abc"}' --dry-run
deepline run lemlist_resume_lead --input '{"lead_id":"lea_abc"}'
deepline run lemlist_mark_lead_interested --input '{"lead_id_or_email":"ada@example.com"}' --dry-run
deepline run lemlist_mark_lead_interested --input '{"lead_id_or_email":"ada@example.com"}'
```

### Activities

```bash
deepline run lemlist_get_activities --input '{"campaign_id":"cam_abc","type":"emailsReplied","limit":50}'
```

### Inbox

```bash
deepline run lemlist_list_inbox --input '{"user_id":"usr_abc"}'
deepline run lemlist_get_inbox_thread --input '{"contact_id":"ctc_abc"}'
deepline run lemlist_send_email --input '{"send_user_id":"usr_abc","send_user_email":"me@co.com","send_user_mailbox_id":"mbx_abc","contact_id":"ctc_abc","lead_id":"lea_abc","subject":"Follow up","message":"<p>Hi!</p>"}' --dry-run
deepline run lemlist_send_email --input '{"send_user_id":"usr_abc","send_user_email":"me@co.com","send_user_mailbox_id":"mbx_abc","contact_id":"ctc_abc","lead_id":"lea_abc","subject":"Follow up","message":"<p>Hi!</p>"}'
deepline run lemlist_send_linkedin_message --input '{"send_user_id":"usr_abc","lead_id":"lea_abc","contact_id":"ctc_abc","message":"Thanks for connecting!"}' --dry-run
deepline run lemlist_send_linkedin_message --input '{"send_user_id":"usr_abc","lead_id":"lea_abc","contact_id":"ctc_abc","message":"Thanks for connecting!"}'
```

### Unsubscribes

```bash
deepline run lemlist_list_unsubscribed_variables --input '{"limit":50}'
deepline run lemlist_unsubscribe_variable --input '{"value":"bounce@example.com"}' --dry-run
deepline run lemlist_unsubscribe_variable --input '{"value":"bounce@example.com"}'
deepline run lemlist_resubscribe_variable --input '{"value":"bounce@example.com"}' --dry-run
deepline run lemlist_resubscribe_variable --input '{"value":"bounce@example.com"}'
deepline run lemlist_export_unsubscribed_variables --input '{}'
deepline run lemlist_get_unsubscribe_by_email --input '{"email":"bounce@example.com"}'
```

## Response Shape Contract

`deepline run` saves the tool response as the data file its receipt names (`--json-out <path>` chooses the file). Its contents by tool:

- `lemlist_list_campaigns` → an array of `{ id, name, status }`.
- `lemlist_get_campaign_stats` → contains `{ sent, opened, clicked, replied, bounced }`.
- `lemlist_get_campaign_sequences` → keyed by sequence ID, each with a `steps` array.
- `lemlist_export_campaign_leads` → an array of lead objects with `email`, `firstName`, `lastName`, `state`.
- `lemlist_add_to_campaign` → contains `{ pushed, failed, errors }`.
- `lemlist_create_campaign` / `lemlist_update_campaign` → includes `web_url` for UI review.

## Key Notes

- **Step types:** `email`, `linkedinInvite`, `linkedinSend`, `linkedinVisit`, `manual`, `phone`, `api`, `whatsappMessage`, `conditional`, `sendToAnotherCampaign`
- **Delays are in days** for both `add_sequence_step` and `update_sequence_step` (0 = immediate, 2 = 2 days). Do not pass seconds or hours.
- **Deep links:** Campaign mutations return `web_url` — always review in Lemlist UI before starting campaigns.
- **Lead states for export:** `all`, `contacted`, `interested`, `notInterested`, `emailsBounced`, `paused`, `emailsSent`, `emailsOpened`, `emailsReplied`
- **Activity types:** `emailsSent`, `emailsOpened`, `emailsClicked`, `emailsReplied`, `emailsBounced`, `emailsUnsubscribed`

## Gotchas

- **Delay unit:** Always days. Passing `172800` thinking "seconds" will result in a `> 1500 days` API error.
- **Inbox operations require user/mailbox IDs:** `send_email` needs `send_user_id`, `send_user_email`, and `send_user_mailbox_id`. List inbox first to discover these values.
- **Sequence writes:** Prefer adding/updating sequence steps while campaigns are still draft/paused to avoid campaign-state edge cases.
- **Lead deduplication:** Validation rejects duplicate emails and duplicate `linkedin_url` values within the same batch. Across batches, Lemlist can reject duplicates (for example 409 conflicts), which surface in `errors`.
- **Lead timezone:** Set the native field with `contacts[].timezone` using an IANA name. `custom_fields.timezone` is a separate custom variable; if both use that key, the dedicated timezone takes precedence. Local-time sending also requires timezone-based scheduling on the campaign.
- **Exact custom-field readback:** Lemlist HTML-escapes a bare `&` as `&amp;` in custom field values containing an HTML tag; plain-text values are stored exactly.
- **Lead removal:** `lemlist_delete_lead` without `action: "remove"` unsubscribes the lead. Pass the action explicitly to remove it from the campaign.
