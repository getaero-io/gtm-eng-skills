# Evaluation

Test decision quality, procedure correctness, and live CRM behavior separately. Finite tests cannot guarantee every future outcome.

## Freeze the test

1. Define the decision, account unit, output contract, and effective date.
2. Freeze public licensed or synthetic inputs with source, rights, dates, limits, and hashes.
3. Obtain independent labels with evidence, reviewer state, unknowns, and valid alternatives.
4. Split whole people, aliases, legal entities, and corporate families before tuning.
5. Keep labels, answer hints, earlier outputs, and research notes outside candidate access.
6. Pin the skill, code, model settings, dependencies, policy, and source versions.
7. Run the actual candidate in a fresh process with permitted tools and inputs only.
8. Retain prompts, file access, tool trace, outputs, failures, duration, and Deepline charges.

Keep representative samples separate from selected challenge cases. Historical merges prove recorded operations, not correct identity. Provider scores and candidate predictions are not independent labels.

Test skill invocation separately from task success. Supplying expected answers to the grader tests only the grader.

## Grade

Use `evaluate-crm-cleaning.play.ts` with the separate input, label, and prediction files. Keep scoring controls outside the candidate run. Validate IDs, versions, types, evidence, and vocabulary before scoring.

Read `summary`, `cases`, and `failures`. Require `passed === true`; completed execution can still contain a failed grade. Missing or invalid predictions remain failures.

With `artifacts_file`, the grader hashes retained bytes. Without it, validation is `receipt_only`. Neither mode independently proves a live CRM change. Keep original byte hashes separate from recalculated `crm-json-js-v1` fingerprints.

| Task                | Required checks                                                                                    |
| ------------------- | -------------------------------------------------------------------------------------------------- |
| Candidate retrieval | Reviewed-candidate precision; recall over all known positives, including omitted pairs             |
| Duplicate decisions | Pair precision and recall; implied group pairs; group contamination; unresolved pairs and records  |
| Hierarchy           | Directed typed-edge precision and recall; effective dates; complete paths; unresolved parent slots |
| Enrichment          | Correct current fields; conflicts; unresolved fields; useful results per charge                    |
| Repair              | Protected values; exact targets and links; required postconditions; retry and uncertain outcomes   |
| Prevention          | Writer coverage; false accepts and blocks; holds; bypasses; concurrent and repeated events         |

Keep abstained positives in recall. Absent evidence is not a negative label. State whether unresolved coverage uses candidates, all pairs, or records.

Report counts with rates. Use null for zero denominators. Related pairs are not independent trials. Separate missing-field groups from richer benchmark records. Keep explicit no-parent states separate from unknown parent slots.

## Test transfer

Vary IDs, names, domains, regions, account units, source systems, field availability, and record order. Check unchanged outcomes under opaque-ID changes and irrelevant records.

Test shared services, shared contact details, conflicting IDs, stale evidence, incomplete graphs, repeated events, and late events. Include completed and failed deals, asset sales, minority interests, franchises, rebrands, and concurrent jobs.

Use counterfactual cases where a changed legal ID or effective date changes the answer. Synthetic cases test rules; they do not estimate real defect rates.

Retain the first failed result. After inspecting held-out results, treat those cases as regression data. Use new independent families for the next held-out claim.

## Test external effects

Apply the safety rule before tests that change records or incur charges. Use approved disposable records for merges, conversions, unique-key races, restrictions, and event replay.

Retain before/after state, provider receipts, result IDs, and exact preservation checks. Offline simulation does not certify live writes.

Set separate release gates for false merges, unsupported ownership, useful recall, and unresolved coverage. Universal abstention must not pass. Report passed, failed, not run, unsupported, and insufficient evidence separately.
