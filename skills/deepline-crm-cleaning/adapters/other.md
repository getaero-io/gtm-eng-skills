# Qualify another CRM

Use the neutral entity, evidence, receipt, and metric contracts. Similar field names do not prove equivalent behavior.

1. Build a capability list from native documentation, live schemas, permissions, and test evidence.
2. Map the approved read export to the neutral model.
3. Record incomplete access and unsupported fields.
4. Prepare a complete repair proposal.
5. Test approved operations on disposable records.
6. Verify record state and downstream effects.

Apply the safety rule before external actions. Generic create, read, update, and delete access does not establish merge behavior. Never substitute deletion for an unavailable merge.

| Area          | Required checks                                                                                 |
| ------------- | ----------------------------------------------------------------------------------------------- |
| Reads         | Objects, fields, complete pages, associations, history, and deleted states                      |
| Identity      | Stable IDs, unique keys, external IDs, and concurrent creation                                  |
| Values        | Null, omitted, clear, scalar, multivalue, aliases, and link limits                              |
| Operations    | Merge, conversion, result IDs, preservation, and recovery limits                                |
| Writes        | Conditional updates, repeated requests, partial batches, async completion, and unknown outcomes |
| Events        | Signatures, replay, gaps, limits, and changes during pagination                                 |
| Relationships | Typed hierarchy, shared domains, protected values, and suppression                              |

**Complete when:** every required capability has evidence and a verified, unverified, or unsupported state. Preserve proposals when writes are unsupported. Do not report unexecuted behavior as verified.
