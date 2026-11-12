Use HeyReach for outbound activation after qualification and verification are complete.

- Always list campaigns first and resolve the exact campaign target before inserts.
- New campaigns are created as drafts and do not start on their own; the customer starts them in HeyReach.
- To duplicate a campaign's steps, use `heyreach_clone_campaign` (copies sequence and schedule). To change steps while copying, read them with `heyreach_get_campaign_sequence` and pass the `sequence` to `heyreach_create_campaign`.
- Creating or cloning a campaign is not retried automatically. If a create fails without an answer, list campaigns by name before trying again so you do not make a duplicate draft.
- Batch writes in small chunks and validate response shape before scaling.
- Pull campaign stats after insert operations to confirm downstream effects.

```bash
deepline run heyreach_list_campaigns --input '{}'
```

```bash
# Copy campaign 12345's steps and schedule into a new draft campaign
deepline run heyreach_clone_campaign --input '{"template_campaign_id":12345,"name":"Founders Q1 copy","list_id":67890,"linkedin_account_ids":[111]}'
```

```bash
# Check the input and price; nothing is sent to HeyReach
deepline run heyreach_add_to_campaign --input '{"campaign_id":"12345","contacts":[{"linkedin_url":"https://www.linkedin.com/in/example","first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}]}' --dry-run
# Send it
deepline run heyreach_add_to_campaign --input '{"campaign_id":"12345","contacts":[{"linkedin_url":"https://www.linkedin.com/in/example","first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}]}'
```
