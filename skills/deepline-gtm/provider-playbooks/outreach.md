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

For collection reads, `page_size` returns one page but Deepline does not currently surface the next cursor, so `page_after` cannot continue the walk. To read beyond one page, use `page_limit` with an increasing `page_offset`. Set `count: true` when you need the filtered total without fetching every row. Use `fields` to reduce large records and `include` only when the related records are needed.

Date filters accept either `filters: { createdAt: "2026-07-18..2026-08-01" }` or, with `newFilterSyntax: true`, `filters: { createdAt: { gte, lte } }`. Do not combine `newFilterSyntax: true` with a `..` string range; that pairing fails with `filterParameter.invalidDatetimeFormat`.

To add a prospect to a sequence, first resolve the prospect, sequence, and mailbox IDs. Then call `outreach_create_sequence_state`. Use the dedicated finish, pause, and resume actions for state transitions.

Outreach write and action calls change the connected workspace. Confirm the target IDs and intended mutation before execution.

For reporting, read `outreach_list_mailings` for send and engagement activity, `outreach_list_sequences` plus `outreach_list_sequence_steps` for campaign structure, `outreach_list_opportunities` for pipeline, and `outreach_list_tasks` or `outreach_list_calls` for rep activity. Records reference lookup tables by ID, so resolve names through `outreach_list_opportunity_stages`, `outreach_list_stages`, `outreach_list_personas`, and `outreach_list_teams` rather than guessing what an ID means.

Webhooks are available through `outreach_list_webhooks`, `outreach_get_webhook`, `outreach_create_webhook`, and `outreach_update_webhook`. A webhook delivers Outreach events to a URL you control, so confirm the target URL, resource, and action before creating one, and prefer updating an existing subscription over adding a duplicate.

Bulk and batch operations, imports, and record deletion for accounts, prospects, sequence states, and webhooks are not exposed, and there is no generic passthrough action for them.

Deepline maps 58 of the 253 documented Outreach operations. If no typed action covers what you need, say so rather than improvising: `generic_http_request` cannot read the connected OAuth credential, so it is not a substitute.
