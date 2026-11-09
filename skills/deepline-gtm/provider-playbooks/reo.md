# Reo.dev

Connect your own Reo.dev **Read** API key before calling these tools (Reo:
Settings → Configurations → API Keys → Product Export & Zapier Integration).
The Product Usage (Write) key does not work. Deepline charges 0 credits for
Reo.dev calls. Every tool reads data from the connected Reo workspace only.
To create lists or send product usage, use the `reo_write_*` tools, which
need the Write key on their own Reo.dev Write API connection.

## Find the ID first

Segment, list, audience, account and developer IDs are Reo UUIDs. Never guess
one.

- Segments: `reo_list_segments` returns each segment's `id` and `type`. Use an
  ACCOUNT segment with `reo_get_segment_accounts`, DEVELOPER with
  `reo_get_segment_developers`, BUYER with `reo_get_segment_buyers`. A segment
  of the wrong type fails as `UPSTREAM_BAD_INPUT`, not as a key problem.
- Lists: `reo_list_lists`, then `reo_get_list_accounts` or
  `reo_get_list_developers` by list type.
- Audiences: `reo_list_audiences`, then `reo_get_audience_members`.
- Accounts: `reo_get_account_details` takes a company `domain` (or `org_id`)
  and returns the account `id`. An account with no match in the workspace is
  `no_result`.
- Developers: the `id` on any developer row.

## Developer signals

- Who at an account is active: `reo_get_account_developers` with the account
  ID.
- What they did: `reo_get_account_activities` or
  `reo_get_developer_activities`. Filter with `activity_source` (GITHUB,
  DOCUMENT, WEBSITE, PRODUCT_JS, CODE_INTERACTIONS, SLACK, LINKEDIN,
  PRODUCT_API) and optionally `activity_type`, which needs a source.
  `reo_get_activity_types` lists the valid pairs.

## Paging

Member tools take `page` (starts at 1) and return `page_no`, `page_size` and
`total_pages`. Activity tools return `has_more`. The list-of-segments, lists
and audiences tools return everything at once.

Timestamps named `first_activity`, `latest_activity` and
`latest_activity_time` are epoch milliseconds. `tags` and `agent_tags` are
comma-separated strings.
