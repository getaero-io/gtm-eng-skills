Use Lemlist for multi-channel outbound campaigns (email + LinkedIn). Full campaign lifecycle management is available.

- Keep activation behind enrichment/verification gates — only push contacts that have been validated.
- Resolve campaign IDs from `lemlist_list_campaigns` before any write operation.
- Insert contacts in batches of 10–25 and re-check campaign stats after writes.
- Always review in Lemlist UI before starting campaigns — use the `web_url` returned by create/update operations.

## Sequence Design

### The conditional gate after linkedinInvite

LinkedIn DMs only deliver to accepted connections. If you place a `linkedinSend` directly after a `linkedinInvite`, messages to non-accepted contacts silently fail or mis-route — the contact gets stuck and neither channel works. The fix is a `conditional` step that waits for acceptance and branches accordingly.

Use `delay: 7` with `delayType: "waitUntil"` at the gate — this gives the contact up to 7 days to accept before falling to the email branch. Using `delay: 1` routes most people to email within 24 hours, which defeats the purpose of LinkedIn-first sequencing.

Standard conditional shape to use after every `linkedinInvite`:

```json
{
  "type": "conditional",
  "conditions": [
    {
      "sequenceId": "<accepted-branch-seq-id>",
      "label": "Accepted invite",
      "key": "linkedinInviteAccepted",
      "delay": 7,
      "delayType": "waitUntil"
    },
    {
      "sequenceId": "<fallback-branch-seq-id>",
      "fallback": true
    }
  ]
}
```

Always wire a fallback branch with at least one email step. An empty fallback means contacts who never accept just stop — no second chance.

### Canonical sequence structure (default for all new campaigns)

Based on the Casebeer / Deal Lab message-market fit framework. The arc is: **connect → observation → dilemma → offer**. Product name appears only in the offer step — introducing it earlier collapses the conversation into a pitch before trust is established.

```
Level 0 — main sequence:
  Step 1: linkedinInvite  (delay 0, blank note)
  Step 2: conditional
           ├─ [linkedinInviteAccepted, waitUntil 7d] → Level 1A
           └─ [fallback]                             → Level 1B

Level 1A — LinkedIn accepted branch:
  Step 3: linkedinSend  (delay 1 from previous step)
           OBSERVATION — segment-level tension, one question, no product name.
           Wait 1 day before sending: a DM sent the instant someone accepts
           reads as automated. The gap makes it feel human.
           Keep it text-message length. End on a question that's true for
           the whole segment, not an assumption about this specific person.

  Step 4: linkedinSend  (delay 3 from previous step)
           DILEMMA — name the acute problem the segment faces, then give
           something valuable with no strings attached: a free resource,
           a repo, a skill, a sharp insight, sample output. No demo ask.
           No product name yet. This step exists to prove you're useful
           before you're selling.

  Step 5: linkedinSend  (delay 7 from previous step)
           OFFER — first time the product appears by name. Soft CTA only
           (demo if timing works, pressure-release closer). This is what
           they discover after the conversation is already going.

Level 1B — email fallback (invite not accepted within 7 days):
  Step 3: email  (delay 0) — same angle as Level 1A observation, email format
  Step 4: email  (delay 3) — bump, different angle, soft close
```

Note: `delay` in all steps means days from the *previous step in that branch*, not days from campaign start or from acceptance.

### Message-market fit principles (Casebeer / Deal Lab)

These govern copy written for any campaign sequence:

- **Segment before you write.** The segment changes what you *say*, not just who you target. "SaaS companies" is a market. "Series A fintech that hired a VP of Sales last month" is a segment you can write a message for.
- **Test offers before scaling copy.** The offer (free audit, sample output, competitive teardown) matters more than phrasing. Run 50–100 contacts per segment, 3-touch sequences. Don't scale until 10%+ reply rate on a segment.
- **Angles, not pain points.** Pain points are what the market experiences — you don't control them. Angles are your argument for why this persona should care right now — you choose them. Write angles.
- **The offer in the DM is the free thing.** The product is what they discover after the reply. A demo ask as a cold CTA signals "I need something from you" — use it only in the offer step, never earlier.
- **Text-message length per DM.** One message doing the job of a whole sequence is too long. Each step earns the next one.

### Known preferences (don't change without explicit instruction)

- **Blank invite note** is intentional. Don't add a note unless the user asks.
- **Email sent before invite acceptance** is intentional in some campaigns (e.g., recruiting). Don't flag it as a bug if the user confirms it.
- **`delayType: "waitUntil"`** is correct for the top-level invite acceptance gate. Use `"within"` only for checking subsequent conditions deeper in the tree.

## Workflow

1. **Create or list campaigns** before adding contacts.
2. **Design the sequence** — decide the branch structure before writing any steps. Conditional branches are separate sequence objects linked by ID; the Lemlist API cannot create branches inline with `add_sequence_step`. For complex branching, build in the Lemlist UI first, then use the API for contacts.
3. **Add steps** to each sequence in order. Keep campaigns in draft/paused state while writing sequence steps.
4. **Add contacts** in batches of 10–25, check stats after each batch.
5. **Review in the Lemlist UI** before activating — use the `web_url` returned by campaign create/update.
6. **Monitor** via activities and inbox threads.

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
deepline tools execute lemlist_add_sequence_step --payload '{"sequence_id":"seq_abc","type":"linkedinInvite","message":"","delay":0}'
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
- **Delays are in days** — both `add_sequence_step` and `update_sequence_step` use days. Passing seconds causes multi-year delay errors.
- **Deep links:** Campaign mutations return `web_url` — use it to review in Lemlist UI before activating.
- **Lead states for export:** `all`, `contacted`, `interested`, `notInterested`, `emailsBounced`, `paused`, `emailsSent`, `emailsOpened`, `emailsReplied`
- **Activity types:** `emailsSent`, `emailsOpened`, `emailsClicked`, `emailsReplied`, `emailsBounced`, `emailsUnsubscribed`

## Gotchas

- **No conditional after linkedinInvite:** Messages to non-accepted contacts silently fail. Every invite step needs a conditional gate — see Sequence Design above.
- **Acceptance gate delay too short:** `delay: 1` on the conditional routes most contacts to email within 24 hours. Use `delay: 7`.
- **First DM at delay 0 after acceptance:** Sending the moment someone accepts reads as automated. `delay: 1` on the first `linkedinSend` in Level 1A preserves the human feel.
- **Product name in observation or dilemma steps:** Introducing the product before the offer step collapses the sequence into a pitch. Steps 3 and 4 build trust; step 5 converts it.
- **Empty fallback branch:** Contacts who never accept just stop. Wire at least one email step into the fallback.
- **Stale copy when cloning:** Fallback email branches often retain old sender names, old product descriptions, or old Calendly links from the source campaign. Check every branch when cloning.
- **Branching via API:** The `add_sequence_step` tool adds steps to a single sequence — it can't create conditional branches inline. Branches are separate sequence objects referenced by ID in the conditional. Build branching structure in the Lemlist UI, then use the API for contacts and monitoring.
- **Delay unit is days:** `172800` reads as over 1500 days, not 2 days. Always pass integers representing days.
- **Inbox operations need user/mailbox IDs:** `send_email` requires `send_user_id`, `send_user_email`, and `send_user_mailbox_id`. Call `lemlist_list_inbox` first to discover them.
- **Lead deduplication:** Duplicate emails or `linkedin_url` values within a batch are rejected. Across batches, Lemlist may return 409 conflicts surfaced in `result.data.errors`.
