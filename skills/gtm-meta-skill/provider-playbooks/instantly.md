Use Instantly for campaign activation and lightweight outbound reporting.

- Resolve campaign IDs from `list_campaigns` before any add operation.
- Insert in controlled batches and re-check campaign stats after writes.
- Keep activation behind enrichment/verification gates to reduce low-quality sends.

```bash
deepline tools execute instantly_list_campaigns --payload '{}' --json
```

```bash
deepline tools execute instantly_add_to_campaign --payload '{"campaign_id":"{{campaign_id}}","contacts":[{"email":"ada@example.com","first_name":"Ada","last_name":"Lovelace"}]}' --json
```
