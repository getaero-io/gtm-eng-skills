Use HeyReach for outbound activation after qualification and verification are complete.

- Always list campaigns first and resolve the exact campaign target before inserts.
- Batch writes in small chunks and validate response shape before scaling.
- Pull campaign stats after insert operations to confirm downstream effects.

```bash
deepline tools execute heyreach_list_campaigns --payload '{}' --json
```

```bash
deepline tools execute heyreach_add_to_campaign --payload '{"campaign_id":"{{campaign_id}}","contacts":[{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}]}' --json
```
