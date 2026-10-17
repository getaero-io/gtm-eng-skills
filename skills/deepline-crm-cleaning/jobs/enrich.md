# Enrich records

**Input:** canonical entities, required fields, protected values, source policy, freshness limits, and an approved lookup plan.

1. Select missing or stale fields that block the requested outcome.
2. Resolve identity first. Reuse valid evidence for each canonical entity.
3. Follow the safety rule before paid calls or private-data transfer.
4. Test a small approved sample and inspect identity, output shape, and evidence.
5. Query the approved sources within the stated budget.
6. Keep misses, access failures, conflicting values, and unresolved identities separate.
7. Retain failed rows.
8. Use another identifier only when it adds a useful lookup path. A name-only match remains a candidate until identity is supported.
9. Validate proposed values. Reject profile, map, shortener, or service URLs as company domains.
10. Preserve valid existing values and record rejected replacements.
11. Apply the field policy to proposals.
12. Keep protected human values and stronger evidence unless the approved plan permits replacement.

Separate email syntax, mail routing, and mailbox checks. Catch-all and unknown results do not prove delivery. Check dated role history; a current-looking title can refer to an advisory role.

**Output:** before/after field proposals, evidence dates, validation states, conflicts, costs, and `enrich` receipts.

**Complete when:** each requested field has a supported proposal, a retained value, or an unresolved reason. Count enrichment only when validity and freshness checks pass. Writes use the repair path.
