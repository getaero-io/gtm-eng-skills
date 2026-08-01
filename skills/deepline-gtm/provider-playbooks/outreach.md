# Outreach agent guidance

Connect Outreach with OAuth before executing a tool. Do not ask for or accept a static Outreach API token.

Use `outreach_list_accounts` and `outreach_list_prospects` before creating records. This prevents duplicates and gives you the numeric relationship IDs required by JSON:API writes.

Preserve JSON:API request bodies:

```json
{
  "data": {
    "type": "prospect",
    "attributes": {},
    "relationships": {}
  }
}
```

For collection reads, prefer cursor pagination with `page_size` and the returned next cursor. Set `count: false` unless the total is required. Use `fields` to reduce large records and `include` only when the related records are needed.

To add a prospect to a sequence, first resolve the prospect, sequence, and mailbox IDs. Then call `outreach_create_sequence_state`. Use the dedicated finish, pause, and resume actions for state transitions.

Outreach write and action calls change the connected workspace. Confirm the target IDs and intended mutation before execution.

This provider does not expose webhooks, bulk operations, deletes, sequence creation, or mailing creation in the initial pilot surface.
