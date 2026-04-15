Use Smartlead for outbound email campaign management. Full lifecycle from campaign creation through lead push, scheduling, sequencing, and monitoring.

- Keep activation behind enrichment/verification gates -- only push contacts that have been validated.
- Resolve campaign IDs from `smartlead_list_campaigns` before any write operation.
- Push leads in batches of up to 100 (the hard limit) and re-check campaign stats after writes.
- Always configure sequences and schedule before starting a campaign.
- Include `SMARTLEAD_API_KEY` as fallback env credential when not using org-linked auth.
- Keep payloads provider-native. There is no shared outbound standard contract for Smartlead.

## Workflow

1. **Create or list campaigns** to get a stable campaign ID.
2. **Add email accounts** to the campaign using `smartlead_add_campaign_email_account`.
3. **Configure sequences** with `smartlead_save_campaign_sequences` (email steps, delays, variants).
4. **Set the schedule** with `smartlead_update_campaign_schedule` (timezone, days, hours, send rate).
5. **Configure settings** with `smartlead_update_campaign_settings` (tracking, stop conditions).
6. **Push leads** in batches (max 100) using `smartlead_push_to_campaign`.
7. **Start the campaign** with `smartlead_update_campaign_status` (status: `START`).
8. **Monitor** via `smartlead_get_campaign_stats` and `smartlead_get_campaign_analytics`.

## Quick Reference

### Campaigns
```bash
deepline tools execute smartlead_list_campaigns --payload '{}'
deepline tools execute smartlead_create_campaign --payload '{"name":"Insurance Brokerage - Book Assessment"}'
deepline tools execute smartlead_get_campaign --payload '{"campaign_id":12345678}'
deepline tools execute smartlead_clone_campaign --payload '{"campaign_id":12345678,"name":"Cloned Campaign"}'
deepline tools execute smartlead_update_campaign_status --payload '{"campaign_id":12345678,"status":"START"}'
deepline tools execute smartlead_delete_campaign --payload '{"campaign_id":12345678}'
```

### Leads
```bash
deepline tools execute smartlead_push_to_campaign --payload '{"campaign_id":"12345678","leads":[{"email":"jane@example.com","first_name":"Jane","last_name":"Lovelace","company_name":"Acme Corp","custom_fields":{"tag":"demo"}}]}'
deepline tools execute smartlead_list_campaign_leads --payload '{"campaign_id":12345678,"offset":0,"limit":100}'
deepline tools execute smartlead_fetch_lead_by_email --payload '{"email":"jane@example.com"}'
deepline tools execute smartlead_update_lead_by_campaign --payload '{"campaign_id":12345678,"lead_id":1,"lead":{"first_name":"Updated"}}'
deepline tools execute smartlead_pause_lead_by_campaign --payload '{"campaign_id":12345678,"lead_id":1}'
deepline tools execute smartlead_resume_lead_by_campaign --payload '{"campaign_id":12345678,"lead_id":1}'
deepline tools execute smartlead_unsubscribe_lead --payload '{"lead_id":1}'
deepline tools execute smartlead_export_campaign_leads --payload '{"campaign_id":12345678}'
```

### Sequences
```bash
deepline tools execute smartlead_fetch_campaign_sequences --payload '{"campaign_id":12345678}'
deepline tools execute smartlead_save_campaign_sequences --payload '{"campaign_id":12345678,"sequences":[{"seq_number":1,"seq_delay_details":{"delay_in_days":0},"seq_variants":[{"email_body":"<p>Hello Ada</p>","variant_label":"A","subject":"Quick question"}]},{"seq_number":2,"seq_delay_details":{"delay_in_days":3},"seq_variants":[{"email_body":"<p>Following up</p>","variant_label":"A","subject":"Re: Quick question"}]}]}'
```

### Schedule and Settings
```bash
deepline tools execute smartlead_update_campaign_schedule --payload '{"campaign_id":12345678,"timezone":"America/New_York","days_of_the_week":[1,2,3,4,5],"start_hour":"09:00","end_hour":"17:00","min_time_btw_emails":5,"max_new_leads_per_day":20}'
deepline tools execute smartlead_update_campaign_settings --payload '{"campaign_id":12345678,"track_settings":["DONT_TRACK_EMAIL_OPEN"],"stop_lead_settings":"REPLY_TO_AN_EMAIL"}'
```

### Analytics
```bash
deepline tools execute smartlead_get_campaign_stats --payload '{"campaign_id":12345678}'
deepline tools execute smartlead_get_campaign_analytics --payload '{"campaign_id":12345678}'
deepline tools execute smartlead_get_campaign_analytics_by_date --payload '{"campaign_id":12345678,"start_date":"2026-01-01","end_date":"2026-01-30"}'
deepline tools execute smartlead_get_lead_statistics --payload '{"campaign_id":12345678}'
```

### Email Accounts
```bash
deepline tools execute smartlead_list_email_accounts --payload '{}'
deepline tools execute smartlead_add_campaign_email_account --payload '{"campaign_id":12345678,"email_account_ids":[1,2,3]}'
deepline tools execute smartlead_remove_campaign_email_account --payload '{"campaign_id":12345678,"email_account_ids":[3]}'
deepline tools execute smartlead_update_email_account_warmup --payload '{"email_account_id":1,"warmup_enabled":true,"total_warmup_per_day":20,"daily_rampup":2,"reply_rate_percentage":30}'
```

### Webhooks
```bash
deepline tools execute smartlead_upsert_campaign_webhook --payload '{"campaign_id":12345678,"webhook":{"name":"Reply Tracker","webhook_url":"https://hooks.example.com/sl","event_types":["EMAIL_REPLY","LEAD_UNSUBSCRIBED"]}}'
deepline tools execute smartlead_fetch_campaign_webhooks --payload '{"campaign_id":12345678}'
deepline tools execute smartlead_delete_campaign_webhook --payload '{"campaign_id":12345678,"id":42}'
```

### Block List
```bash
deepline tools execute smartlead_add_domain_block_list --payload '{"domain_block_list":["competitor.com","spam@bad.org"]}'
deepline tools execute smartlead_get_block_list --payload '{}'
```

### Smart Delivery
```bash
deepline tools execute smartlead_create_delivery_test --payload '{"name":"Q2 Deliverability","email_accounts":[1,2]}'
deepline tools execute smartlead_get_delivery_test --payload '{"test_id":1}'
deepline tools execute smartlead_get_delivery_score --payload '{"test_id":1}'
```

### Smart Senders (Domains)
```bash
deepline tools execute smartlead_search_domain --payload '{"domain":"example.com"}'
deepline tools execute smartlead_add_domain --payload '{"domain":"outbound.example.com"}'
deepline tools execute smartlead_verify_domain --payload '{"domain_id":1}'
deepline tools execute smartlead_auto_generate_mailboxes --payload '{"domain_id":1,"count":5}'
```

### Generic API Request
```bash
deepline tools execute smartlead_api_request --payload '{"method":"GET","endpoint":"/api/v1/campaigns"}'
```

## Response Shape Contract

Deepline wraps all provider payloads in a standard result envelope: `{ data, meta }`.

- `smartlead_list_campaigns` -> `result.data` is an array of `{ id, name, status }`.
- `smartlead_get_campaign_stats` -> `result.data` contains `{ sent, opened, clicked, replied, bounced }`.
- `smartlead_push_to_campaign` -> `result.data` contains `{ pushed, failed, results }`.
- `smartlead_create_campaign` -> `result.data` includes `{ ok, id, name, created_at }`.
- `smartlead_export_campaign_leads` -> `result.data` is a raw lead export array.
- `smartlead_list_campaign_leads` -> `result.data` is a paginated list of lead objects.
- `smartlead_get_campaign_analytics_by_date` -> `result.data` contains daily stats breakdown.

## Gotchas

- **`min_time_btw_emails` vs `min_time_btwn_emails`:** The schedule endpoint accepts both field names. `min_time_btw_emails` is canonical; `min_time_btwn_emails` is the legacy alias. At least one must be provided. The validator normalizes the legacy alias to the canonical field.
- **Campaign status values:** Only `PAUSED`, `STOPPED`, and `START` are valid. Note it is `START`, not `STARTED` or `RUNNING`.
- **Timezone handling:** `update_campaign_schedule` requires an IANA timezone string (e.g. `America/New_York`). The schedule uses 24-hour `HH:MM` format for `start_hour` and `end_hour`, and `start_hour` must be strictly before `end_hour`.
- **Days of the week:** 0 = Sunday through 6 = Saturday. At least one day is required.
- **Sequence ordering:** `seq_number` values must be contiguous starting at 1 (no gaps). The first sequence step (seq_number 1) must have a subject line (either at step level or on every variant).
- **Delay units:** `delay_in_days` is in days (0 = immediate). Do not pass hours or minutes.
- **Lead batch limits:** Maximum 100 leads per `push_to_campaign` call. Duplicate emails within a batch are rejected. Emails are automatically lowercased for deduplication.
- **Analytics date range:** `get_campaign_analytics_by_date` enforces a maximum 30-day window between `start_date` and `end_date`. Dates must be in `YYYY-MM-DD` format.
- **Track settings normalization:** `update_campaign_settings` accepts either a single string or an array for `track_settings`. Valid values: `DONT_TRACK_EMAIL_OPEN`, `DONT_TRACK_LINK_CLICK`, `DONT_TRACK_REPLY_TO_AN_EMAIL`.
- **Stop lead settings:** Valid values: `REPLY_TO_AN_EMAIL`, `CLICK_ON_A_LINK`, `OPEN_AN_EMAIL`.
- **Block list entries:** Each entry must be a valid domain (`example.com`) or email address (`user@example.com`). URLs with protocol prefixes or paths are rejected.
- **Webhook event types:** `EMAIL_SENT`, `EMAIL_OPEN`, `EMAIL_LINK_CLICK`, `EMAIL_REPLY`, `LEAD_UNSUBSCRIBED`, `LEAD_CATEGORY_UPDATED`.
- **Campaign IDs:** Accepted as integer or numeric string. Non-numeric strings are rejected.
- **Reply thread:** `reply_email_time` must be a full ISO datetime (e.g. `2026-01-15T09:30:00.000Z`). Date-only strings are rejected.
- **Client permissions:** Only `reply_master_inbox` and `full_access` are valid. Client passwords must be at least 8 characters.
- **API key auth:** Pass `SMARTLEAD_API_KEY` environment variable. The API key is appended as a query parameter by the integration layer.
