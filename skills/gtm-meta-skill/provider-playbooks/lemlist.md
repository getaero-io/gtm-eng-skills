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
deepline tools execute lemlist_list_campaigns --payload '{}' 
deepline tools execute lemlist_create_campaign --payload '{"name":"My Campaign"}' 
deepline tools execute lemlist_pause_campaign --payload '{"campaign_id":"cam_abc123"}' 
deepline tools execute lemlist_update_campaign --payload '{"campaign_id":"cam_abc123","name":"New Name"}' 
deepline tools execute lemlist_get_campaign_stats --payload '{"campaign_id":"cam_abc123"}' 
```

### Sequences
```bash
deepline tools execute lemlist_get_campaign_sequences --payload '{"campaign_id":"cam_abc123"}' 
deepline tools execute lemlist_add_sequence_step --payload '{"sequence_id":"seq_abc","type":"linkedinInvite","message":"Hi!","delay":0}' 
deepline tools execute lemlist_update_sequence_step --payload '{"sequence_id":"seq_abc","step_id":"stp_xyz","type":"linkedinSend","delay":2}' 
deepline tools execute lemlist_delete_sequence_step --payload '{"sequence_id":"seq_abc","step_id":"stp_xyz"}' 
```

### Leads
```bash
deepline tools execute lemlist_add_to_campaign --payload '{"campaign_id":"cam_abc","contacts":[{"email":"ada@example.com","first_name":"Ada","last_name":"Lovelace"}]}' 
deepline tools execute lemlist_export_campaign_leads --payload '{"campaign_id":"cam_abc","state":"interested"}' 
deepline tools execute lemlist_pause_lead --payload '{"lead_id":"lea_abc"}' 
deepline tools execute lemlist_resume_lead --payload '{"lead_id":"lea_abc"}' 
deepline tools execute lemlist_mark_lead_interested --payload '{"lead_id_or_email":"ada@example.com"}' 
```

### Activities
```bash
deepline tools execute lemlist_get_activities --payload '{"campaign_id":"cam_abc","type":"emailsReplied","limit":50}' 
```

### Inbox
```bash
deepline tools execute lemlist_list_inbox --payload '{"user_id":"usr_abc"}' 
deepline tools execute lemlist_get_inbox_thread --payload '{"contact_id":"ctc_abc"}' 
deepline tools execute lemlist_send_email --payload '{"send_user_id":"usr_abc","send_user_email":"me@co.com","send_user_mailbox_id":"mbx_abc","contact_id":"ctc_abc","lead_id":"lea_abc","subject":"Follow up","message":"<p>Hi!</p>"}' 
deepline tools execute lemlist_send_linkedin_message --payload '{"send_user_id":"usr_abc","lead_id":"lea_abc","contact_id":"ctc_abc","message":"Thanks for connecting!"}' 
```

### Unsubscribes
```bash
deepline tools execute lemlist_list_unsubscribed_variables --payload '{"limit":50}' 
deepline tools execute lemlist_unsubscribe_variable --payload '{"value":"bounce@example.com"}' 
deepline tools execute lemlist_resubscribe_variable --payload '{"value":"bounce@example.com"}' 
deepline tools execute lemlist_export_unsubscribed_variables --payload '{}' 
deepline tools execute lemlist_get_unsubscribe_by_email --payload '{"email":"bounce@example.com"}' 
```

### Webhooks
```bash
deepline tools execute lemlist_add_webhook --payload '{"target_url":"https://hooks.example.com/lemlist","type":"emailsReplied"}' 
deepline tools execute lemlist_get_webhooks --payload '{}' 
deepline tools execute lemlist_delete_webhook --payload '{"hook_id":"hoo_abc123"}' 
```

## Response Shape Contract

Deepline wraps all provider payloads in a standard result envelope: `{ data, meta }`.

- `lemlist_list_campaigns` → `result.data` is an array of `{ id, name, status }`.
- `lemlist_get_campaign_stats` → `result.data` contains `{ sent, opened, clicked, replied, bounced }`.
- `lemlist_get_campaign_sequences` → `result.data` is keyed by sequence ID, each with a `steps` array.
- `lemlist_export_campaign_leads` → `result.data` is an array of lead objects with `email`, `firstName`, `lastName`, `state`.
- `lemlist_add_to_campaign` → `result.data` contains `{ pushed, failed, errors }`.
- `lemlist_create_campaign` / `lemlist_update_campaign` → `result.data` includes `web_url` for UI review.

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
- **Lead deduplication:** Validation rejects duplicate emails and duplicate `linkedin_url` values within the same batch. Across batches, Lemlist can reject duplicates (for example 409 conflicts), which surface in `result.data.errors`.
