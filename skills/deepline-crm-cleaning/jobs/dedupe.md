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

Use `score-crm-company-candidates.play.ts` with canonical company records. It compares every pair in at most 1000 records. Exact normalized names and eligible shared domains retrieve review candidates directly. For other names, lexical similarity, shared tokens and generated acronyms retrieve candidates before Jev (`ai_evaluate`, model `typesafe-ai/jev`) judges name variants using supplied country, address and account grain. Unrelated pairs make no model call. No maintained alias or legal-suffix dictionary is required.

The default `name_similarity_threshold`, 0.88, applies to Jev's name-variant probability for retrieval. It does not establish entity identity or authorize merging. Jaro-Winkler scores remain diagnostic observations in the existing pair tuples. All candidates remain unresolved; omitted pairs remain unassessed.

Export `inventory`, `pair_groups`, `identity_judgments`, and `metadata`. Join pair indices to the inventory and decode flags with `metadata.pair_group_schema`. Each identity-judgment group contains `[right_record_index, name_variant_probability, basis]` tuples. Check legal identifiers, addresses, and dated relationships before deciding identity.

## Contact proposals

Use `resolve-crm-contact-duplicates.play.ts`. Map `last_name` to `surname`; supply only supported fields and omit unavailable values. Keep labels out of input. Export `record_inventory`, `pairs`, `clusters`, and `metadata`.

Exact identifiers and compatible names with independent birth-date, email or city corroboration retain deterministic fast paths. Cheap name, email and date checks retrieve the remaining candidate pairs. Jev judges ambiguous name compatibility and whether an email identifies an individual; these judgments support the evidence rules rather than replacing them. Recognize nicknames, reordered names, initials and transliterations without maintaining name or mailbox vocabularies. Names alone cannot establish CRM identity.

Compatibility and individual-mailbox probabilities use a provisional 0.5 decision boundary. Validate the complete policy on independent deployment data; this is not a claimed 95% identity probability. Missing evidence remains unknown. Conflicting birth dates, explicit distinct decisions and rejected conflicting full names hold the proposed group. An unknown edge does not veto an otherwise supported group. Keep probabilities, effective policy and hash. `policy_json` remains accepted: lexical and date controls apply, and an explicitly supplied `shared_email_locals` exclusion remains binding. The live resolver does not use the legacy offline resolver's built-in mailbox list.

Contact resolution accepts at most 5000 records and compares pairs quadratically. Both matching Plays make metered model calls and transfer supplied identity fields to the evaluation provider. Agree on cohort size, data transfer and cost limits before execution, then pilot at most two records. Repeated identical field pairs reuse one evaluation per run. `max_evaluations` defaults to 1000 unique ambiguous field pairs after fast paths and candidate filtering. Both Plays count unique candidate states incrementally before any model call and fail the whole cohort when it is exceeded; increase it only within the approved run budget. For large cohorts, design and evaluate candidate selection explicitly; arbitrary batches miss cross-batch duplicates. Neither Play performs CRM merges or establishes safe native merge behavior.

**Complete when:** report candidate recall, decision precision and recall, group errors, and unresolved pair and record coverage separately. Accuracy claims need independent labels.
