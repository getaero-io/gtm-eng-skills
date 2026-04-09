Use Instantly for campaign activation and lightweight outbound reporting.

- Resolve campaign IDs from `list_campaigns` before any add operation.
- For `instantly_create_campaign`, do **not** brute-force timezone guesses. Reuse a known-good timezone from an existing campaign via `instantly_get_campaign` when possible.
- If the requested timezone is not directly accepted, map it to the closest supported Instantly value before sending. Example: use `America/Detroit` when the user asks for `America/New_York`.
- Treat `UTC` as unsupported by Instantly create-campaign; use a supported UTC-equivalent enum value from existing campaigns instead of sending literal `UTC`.
- For `campaign_schedule.schedules[].days`, use numeric day keys (`"0"`..`"6"`). Named weekdays are normalized by Deepline, but values outside sunday..saturday are rejected.
- Insert in controlled batches and re-check campaign stats after writes.
- Keep activation behind enrichment/verification gates to reduce low-quality sends.

```bash
deepline tools execute instantly_list_campaigns --payload '{}'
```

```bash
deepline tools execute instantly_add_to_campaign --payload '{"campaign_id":"abc-123","contacts":[{"email":"ada@example.com","first_name":"Ada","last_name":"Lovelace"}]}'
```
