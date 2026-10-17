# Outcome receipts

Use [`plays/schemas/receipt.schema.json`](../plays/schemas/receipt.schema.json). Receipts record evidence and outcomes; they are not approval credentials.

Validate receipts with `evaluate-crm-cleaning.play.ts`, `mode: "validate_receipts"`, and `predictions_file`. Inspect every failed case. Standalone validation checks schema and semantics, not external execution proof. Play-specific datasets do not replace this receipt.

## Required fields

Use `crm-cleaning.receipt.v1` and all required fields. Record run, case, job, CRM, status, decision, reasons, evidence, scope, outcome, actions, metrics, and artifacts. Identify the CRM tenant, snapshot, and policy in `scope`.

Use empty arrays for inapplicable collections. Use null for unknown nullable values. Account for every evaluated case.

| Status            | Meaning                                                    |
| ----------------- | ---------------------------------------------------------- |
| `completed`       | Analysis or approved action finished at the declared scope |
| `partial`         | Work remains unresolved or unattempted                     |
| `no_change`       | Assessment finished; no repair is needed                   |
| `review_required` | A consequential choice is unresolved                       |
| `blocked`         | A prerequisite prevents work                               |

Completed analysis does not imply a CRM change. Do not shrink scope to claim completion.

For `partial`, include coverage `unit`, `planned`, `attempted`, `resolved`, and `unresolved`. Require `resolved <= attempted <= planned` and `resolved + unresolved = planned`. At least one unit must remain unresolved. Validate coverage whenever present. `completed` and `no_change` require every planned unit attempted.

Follow a supplied `response_contract`. If it cannot express `partial`, use its incomplete status and preserve coverage in an artifact. Never claim completion to fit a restricted contract.

## Actions and relationships

Record every proposed or attempted action, known targets, actual status, and provider receipt reference. Keep `proposed`, `executed`, `verified`, `blocked`, `failed`, and `unknown` distinct. Historical operations remain evidence, not new actions.

For a relationship, record source, target, type, direction, `valid_from`, `valid_to`, `observed_at`, and verification state. Action targets must equal its two endpoints. Keep one-endpoint observations in evidence.

Keep unknown dates null. Use `observed_at` for the latest supporting evidence, including evidence that a relationship ended. An observation date does not establish an effective date.

`end_relationship` requires the typed relationship and endpoint targets. Set a supported closing time in `valid_to`. If it is unknown, use `proposed` or `blocked` and explain the reason in both action and receipt reason codes.

Every executed or verified action requires matching provider proof. A reference alone is insufficient. An included relationship must match that proof. Keep optional unsupported detail in evidence artifacts.

Include only the requested relationship types and node kinds in the outcome. Allowed vocabulary does not require assertions. Unknown facts remain unknown. An unverified capability does not prove the platform lacks it.

## Metrics

For new metrics, include state, source reference, required values, window start/end, and reporting cutoff `as_of`. Cite an input evidence ID or source reference. Source observation time cannot exceed the cutoff.

| State              | Values                                      |
| ------------------ | ------------------------------------------- |
| `measured`         | Supported numerator, denominator, and value |
| `not_measured`     | Null numerator, denominator, and value      |
| `zero_denominator` | Zero numerator and denominator; null value  |

Keep eligibility windows, effective dates, and observation times separate. A later snapshot can measure an earlier period if its coverage supports it. Preserve unavailable measurements' applicable windows and coverage evidence.

Store ratios without display rounding. For counts, seconds, and credits, use null denominator and `value = numerator`. The grader checks provenance separately. Equivalent time zones identify the same instant. Legacy metrics can have inferred states.

Emit only fields and metrics permitted by the response contract. Schema-defined provenance and permitted coverage do not authorize extra facts. Preserve exact enums. Treat `x-ordering: set` arrays as duplicate-free sets; retain other declared order.

## Verify and retain

Retain observations, decision policy, approved plan, execution attempts, returned IDs, and read-back checks separately. Follow the safety rule before effects. After an uncertain response, reconcile native state before retrying. Count retries under the same logical action.

Verify suppression, owners, attribution, activities, deals, history, and source-to-result ID aliases. Equal counts and successful responses do not prove preservation. State actual recovery limits.

For artifact checks, supply one `{ref, content_base64}` object per `artifacts_file` row. Use unique relative logical names and exact bytes. Artifact verification requires a matching SHA-256 hash. The grader rejects missing bytes, unbound hashes, absolute paths, URIs, and parent traversal. It does not read local files.

Without artifact bytes, validation is `receipt_only`. An empty artifact list is valid when none are required. Keep original byte hashes separate from normalized JSON fingerprints.

Keep raw responses, normalized observations, and reviewed facts separate. Record connection and mapping versions. Several tools observing one source do not provide independent evidence.

Remove private session and cookie values before retention. Hash the redacted artifact and record the removed category. For analysis, record zero CRM changes. Report missing pages, access failures, stale evidence, and unsupported operations with their coverage effect.
