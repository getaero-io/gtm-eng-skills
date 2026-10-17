# Evaluate

**Input:** declared capability, frozen inputs, versioned policy, independent labels, and a baseline.

1. Select public licensed or synthetic data for the task.
2. Record source limits.
3. Use identity labels for matching and dated typed evidence for hierarchy.
4. Split whole people, entities, and corporate families before tuning.
5. Keep labels and answer hints outside candidate access. Previously inspected cases are regression data.
6. Run the actual candidate in a fresh process.
7. Supply only permitted tools, inputs, and the visible `input.response_contract`.
8. Produce one receipt per case. Offline actions remain proposals; historical writes remain evidence.
9. Run `evaluate-crm-cleaning.play.ts` with `mode: "evaluate"`, `inputs_file`, `labels_file`, and `predictions_file`.
10. Keep the candidate run separate from the grader. Missing, duplicate, or invalid predictions fail the test.
11. Inspect `summary`, `cases`, and `failures`.
12. Require `passed === true`.
13. Compare the same cases with a simple baseline; report errors and unresolved coverage.
14. Test native CRM effects separately in approved disposable records.
15. Follow the safety rule even for tests. State untested and unsupported capabilities.
16. Obtain independent review when required. Give the reviewer frozen inputs and outputs.
17. Retain its prompt, settings, findings, and disagreements. Agreement is not ground truth.

For artifact checks, supply `artifacts_file` rows with unique `ref` and canonical `content_base64` bytes. The grader checks their hashes. Without bytes, it reports `receipt_only`; a claimed hash is not proof.

**Output:** manifests, receipts, score datasets, coverage, baseline comparison, and `evaluate` receipts.

**Complete when:** pinned artifacts reproduce the grade. State test limits. A passing regression suite cannot guarantee future accuracy.
