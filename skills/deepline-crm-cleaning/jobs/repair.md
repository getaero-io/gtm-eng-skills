# Apply approved repairs

**Input:** confirmed decisions, original records, a tested CRM operation, and approval for the exact repair plan.

This bundle has no CRM write executor. Follow the safety rule in SKILL.md. A capability grant, confidence score, or general request to clean data cannot replace approval of the concrete plan.

1. Prepare the plan: CRM tenant, action ID, targets, operation, before/after values, protected fields, versions, limits, and verification checks. Choose a survivor by identity and preservation needs, not creation order alone.
2. Record explicit approval of that plan.
3. Save original records and intent before effects.
4. Leave unapproved actions as proposals.
5. Read affected records again. A changed record or proposal requires review and new approval before execution.
6. Use the tested native operation.
7. Keep merge, Lead conversion, field edits, and link edits separate. Delete-and-create is not a merge.
8. After an uncertain response, inspect native state before retrying.
9. Read back returned IDs, fields, links, suppression, owner, attribution, and connected-system effects.
10. Preserve source-to-result ID aliases.
11. Record each action's actual status.
12. Report failed checks and recovery options. A saved snapshot is not an unmerge operation. Recovery with new external effects needs its own approved plan.

**Output:** approved plan, action results, ID mappings, preservation checks, recovery proposals, and `repair` receipts.

**Complete when:** each verified action passes its checks and repeated delivery adds no effect. Keep failed, partial, and unknown actions visible. HTTP success alone does not prove repair.
