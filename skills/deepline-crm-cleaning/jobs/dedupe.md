# Find duplicates

**Input:** normalized records, account unit, source namespaces, identity evidence, and matching policy.

1. Find candidate pairs from supported identifiers, names with address context, aliases, and domains. Empty keys provide no evidence.
2. Compare identity evidence.
3. Keep people separate from their employment. Shared inboxes, phones, and employer domains do not prove identity.
4. Preserve email local-part meaning unless a verified domain rule permits normalization.
5. Decide: same entity, distinct entities, related entities, or unresolved.
6. Record supporting evidence and conflicts.
7. Check the whole proposed group. Hold groups with distinct identities, parent-child relationships, or incompatible account units. A chain of similar pairs does not remove a conflict.
8. Propose a canonical record and source-ID mapping.
9. Leave unsupported decisions in review.

**Output:** candidate pairs, decisions, groups, conflicts, mappings, and `dedupe` receipts. Apply the safety rule before any merge.

## Company candidates

Use `score-crm-company-candidates.play.ts` with canonical company records. It compares every pair in at most 1000 records. It returns Jaro-Winkler name scores and shared eligible domain keys. It preserves hosted-site boundaries; it does not remove legal suffixes or infer aliases.

The default threshold, 0.88, controls retrieval. It is not a match probability or merge threshold. All returned pairs remain unresolved; omitted pairs remain unassessed.

Export `inventory`, `pair_groups`, and `metadata`. Join pair indices to the inventory and decode flags with `metadata.pair_group_schema`. Check legal identifiers, addresses, and dated relationships before deciding identity.

Report candidate recall and review volume on separate labeled data. For more than 1000 records, test a method that selects likely pairs before scoring. Arbitrary batches miss duplicates across batches.

## Contact proposals

Use `resolve-crm-contact-duplicates.play.ts`. Map `last_name` to `surname`; supply only supported fields and omit unavailable values. Keep labels out of the input. Export `record_inventory`, `pairs`, `clusters`, and `metadata`.

Inspect the default policy in `plays/shared/duplicates.ts`. Set tested overrides through the `policy_json` object string. Retain the effective policy and hash. Default thresholds are provisional; they are not proven for the deployment population.

Contact decision features use the lower of the two directional sequence-matcher scores. Record IDs and input order do not affect the decision. This conservative rule can leave more pairs unresolved.

Without birth dates and cities, matching needs email agreement and supporting names. A changed work email can remain unresolved. Review English shared-inbox terms for the locale. Exact short names can match; unequal names below three characters get no fuzzy score. Birth-date conflicts hold the pair and connected group for review.

The Play compares pairs quadratically and accepts at most 5000 contacts. Pairs outside candidate generation remain unassessed. Deprecated policy controls have no decision effect. It does not establish employment, company identity, or safe native merge behavior.

**Complete when:** report candidate recall, decision precision and recall, group errors, and unresolved pair and record coverage separately. Accuracy claims need independent labels.
