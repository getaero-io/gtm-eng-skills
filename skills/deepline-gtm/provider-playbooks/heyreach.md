Use HeyReach for outbound activation after qualification and verification are complete.

- Always list campaigns first and resolve the exact campaign target before inserts.
- HeyReach public API does not expose campaign creation. Do not attempt to create campaigns via API tools; create campaigns in HeyReach UI first, then reference the resulting `campaign_id`.
- Batch writes in small chunks and validate response shape before scaling.
- Pull campaign stats after insert operations to confirm downstream effects.

```bash
deepline tools execute heyreach_list_campaigns --payload '{}'
```

```bash
deepline tools execute heyreach_add_to_campaign --payload '{"campaign_id":"12345","contacts":[{"linkedin_url":"https://www.linkedin.com/in/example","first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}]}'
```
