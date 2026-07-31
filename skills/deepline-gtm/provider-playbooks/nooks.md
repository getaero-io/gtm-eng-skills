# Nooks

Use Nooks to inspect a connected customer's sales-engagement workspace.

- The internal test endpoint uses hidden `nooks_get_me` to verify the
  credential and identify the connected workspace.
- Use list actions to find IDs, then fetch a specific sequence, prospect,
  account, task, call, mailbox, user, sequence state, step, disposition, or
  email template.
- Keep pagination bounded. Nooks supports cursor pagination with `page[size]`
  up to 100 and `page[after]` or `page[before]`.
- Use at most three comma-separated top-level `include` values. Nested includes
  are not supported.
- All mutations are unavailable until Deepline can validate them in an internal
  test workspace. `nooks_create_sequence_state` has the additional risk that it
  can trigger immediate enrichment and consume workspace entitlements.
  Email reads remain unavailable until complete provider-owned response
  evidence is available.
- Do not use the deferred `call.logged` webhook as a polling or monitor
  substitute.
