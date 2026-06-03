# Meta Audiences

Use these tools for Meta customer-list custom audiences.

- Create one custom audience per segment and then keep syncing member files into the same audience ID.
- Use `mode: "replace"` for full snapshots and `mode: "append"` for incremental adds.
- Deepline hashes supported identifiers locally before upload.
- Watch `operation_status`, `approximate_count`, and invalid-entry counts when evaluating match health.
