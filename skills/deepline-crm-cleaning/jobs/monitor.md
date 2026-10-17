# Monitor quality

**Input:** approved record sets, metric definitions, baseline, source events, and freshness policy.

1. Compare the fixed baseline and current record set separately. Reconcile additions, deletions, late events, and changed denominators.
2. Check source coverage, page cursors, and access failures. An empty feed does not prove health.
3. Group new, recurring, and unresolved defects by writer, version, and canonical entity.
4. Investigate changes with dated evidence. A certificate renewal, missing tag, feed gap, or failed website does not prove changed ownership.
5. Prepare issues with affected records, evidence, proposed repair, and a success measure.

**Output:** trends, source status, unresolved counts and age, proposals, and `monitor` receipts.

Prepare any schedule, paid refresh, or notification under the safety rule. Use the existing control interface only after approval. Report a monitor as inactive until activation is confirmed.

**Complete when:** metrics reconcile to issues and actions. Show unobserved records. Suppress repeated unchanged alerts under the approved notification policy.
