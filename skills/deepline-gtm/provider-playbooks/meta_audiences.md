# Meta Audiences

Use these tools for Meta customer-list custom audiences.

- Create one custom audience per segment and then keep syncing member files into the same audience ID.
- Use `mode: "replace"` for full snapshots and `mode: "append"` for incremental adds.
- Deepline hashes supported identifiers locally before upload.
- Watch `operation_status`, `delivery_status`, the `approximate_count_*_bound` pair, and invalid-entry counts when evaluating match health.
- Meta reports audience size as a range. Read `approximate_count_lower_bound` and `approximate_count_upper_bound`; `approximate_count` is a midpoint Deepline derives for backward compatibility, not a figure Meta returns.
- Sizes stay null until Meta finishes processing an upload, and Meta withholds them entirely for audiences below its minimum size threshold. A null count shortly after a sync is normal, not a failed upload.
- `delivery_status` code 411 means a low rate of matched people, which is the signal that a list matched poorly.
