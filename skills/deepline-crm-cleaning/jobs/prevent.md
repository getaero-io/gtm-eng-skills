# Prevent defects

**Input:** writer inventory, event identity, canonical-key policy, and CRM constraints.

1. List forms, imports, integrations, product events, enrichment, and manual creation.
2. Mark writers that bypass checks.
3. Test incoming identities and URL roles on retained inputs. Propose create, update, or hold decisions with reasons.
4. Select a verified unique key.
5. Search-before-create can race; a delayed index can hide records. On a key conflict, read and reconcile the winning record.
6. Plan event replay and merged-ID aliases. Persist intent before effects so retries cannot recreate retired records.
7. Test repeated events, concurrent creation, missing keys, cross-object matches, and delayed indexing.
8. Measure false blocks in simulation first.
9. Prepare the exact enforcement plan for approval under the safety rule. Access to a control does not authorize enabling it.

**Output:** writer inventory, key policy, test results, bypass gaps, control proposals, and `prevent` receipts.

**Complete when:** every writer has a tested control or a stated gap. Count blocked, held, and bypassed attempts. A periodic duplicate scan does not prevent duplicates at creation.
