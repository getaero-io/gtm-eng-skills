# Meta Audiences

Use these tools for Meta customer-list custom audiences.

- Create one custom audience per segment and then keep syncing member files into the same audience ID.
- Use `mode: "replace"` for full snapshots and `mode: "append"` for incremental adds.
- Deepline hashes supported identifiers locally before upload.
- Watch `operation_status`, `delivery_status`, the `approximate_count_*_bound` pair, and invalid-entry counts when evaluating match health.
- Meta reports audience size as a range. Read `approximate_count_lower_bound` and `approximate_count_upper_bound`; `approximate_count` is a midpoint Deepline derives for backward compatibility, not a figure Meta returns.
- Sizes stay null until Meta finishes processing an upload, and Meta withholds them entirely for audiences below its minimum size threshold. A null count shortly after a sync is normal, not a failed upload.
- `delivery_status` code 411 means a low rate of matched people, which is the signal that a list matched poorly.
- Meta locks an audience while a users upload ingests: `operation_status` code 414 means a replace is still processing, and further writes fail with `META_AUDIENCE_UPDATE_IN_PROGRESS` until it settles. Poll `meta_audiences_get_audience_status` until `operation_status` code returns 200, then retry the full sync in one call. Do not resume a partial upload with `mode: "append"`; re-send the complete list.
- Send the whole member list in one `sync_audience_members` call. Chunking into separate calls collides with the ingest lock and strands a partial audience.
- `audience_id` must be the numeric id Meta returns. Read it from `meta_audiences_create_audience` at `data.audience.id`; a literal "undefined" id means the caller read the wrong response field, and the tool now rejects it before compiling the payload.
