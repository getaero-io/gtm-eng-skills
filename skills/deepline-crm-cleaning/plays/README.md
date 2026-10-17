# CRM cleaning Plays

These nine TypeScript Plays read records, prepare proposals, or grade evidence. They do not write to the CRM.

## Prepare an approved run

Follow the safety rule in SKILL.md. Local file input is uploaded for cloud execution. Obtain approval for that transfer, execution scope, and any charges first.

1. Select the approved Deepline workspace.
2. Run `bun install --frozen-lockfile` in this folder.
3. Check the selected source with the command below.
4. Inspect the returned artifact hash and validation result.

```sh
deepline plays check ./audit-crm-snapshot.play.ts --json
```

Keep this folder intact. The bundle needs its helpers, schemas, and frozen data. It needs no Python process or local credential file at execution time.

For either HubSpot Play, configure `HUBSPOT_API_KEY` through the supported secrets interface. Use `deepline secrets --help` for its current contract. The provider key needs account, property, record, and association read permissions. Supply `expected_portal_id`; mismatches stop collection before property or record reads. Never put the key in source or input.

## Input and output

Use CSV files with one complete JSON object in each `record_json` cell. Standard CSV quoting preserves nested data. Omit unavailable properties; use null for observed blanks. An optional `row_id` preserves export order. Inline Play input has a 1 MiB limit.

Each `*_file` below uses this CSV format. A document file contains exactly one row. Policy JSON strings contain objects, not paths.

| Entrypoint                               | Control input                                                                                                                                 | Row contract                                                                                                                                  | Result dataset handles                                                                                                |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `audit-crm-snapshot.play.ts`             | `records_file`, `as_of`; optional `company_population_complete`, `stale_days` (365), `source_lag_hours` (24), `required_fields_json`          | `id`, `object_type`, `source:{system,scope_id}`, `properties`; optional complete `company_ids`, `retrieved_at`, `source_snapshot_at`          | `summary`, `normalized`, `issues`, `candidates`                                                                       |
| `collect-hubspot-companies.play.ts`      | `expected_portal_id`; optional property-name array `properties`                                                                               | No file. Reads all company pages and compares before/after totals.                                                                            | `companies`, `manifest`                                                                                               |
| `sample-hubspot-crm.play.ts`             | `expected_portal_id`, `inventory_file`, `manifest_file`, `seed`; optional `company_limit`, `contact_limit` (1–1000 each, default 1000)        | Exact inventory and one-row manifest from the collector                                                                                       | `companies`, `contacts`, `company_contacts`, `contact_companies`, `company_hierarchy`, `hierarchy_labels`, `manifest` |
| `classify-company-domains.play.ts`       | `records_file`                                                                                                                                | `url`; optional `context` with documented platform-owner evidence                                                                             | `classifications`                                                                                                     |
| `collect-domain-evidence.play.ts`        | `domains_file`; optional `max_domains` (1000), `timeout` (8 seconds), `max_bytes` (262144), `max_legal_pages` (2), `max_redirects` (5)        | `domain` string, including a blank string when the input is missing                                                                           | `evidence`                                                                                                            |
| `plan-crm-domain-repairs.play.ts`        | `records_file`, `candidates_file`; optional `contexts_file`                                                                                   | Company records, scoped evidence-backed candidates, optional `{id,source,context}` rows. See [domain evidence](../shared/domain-evidence.md). | `before_after`, `proposed_records`, `metrics`                                                                         |
| `score-crm-company-candidates.play.ts`   | `records_file`; optional `name_similarity_threshold` (0.88)                                                                                   | `id`, `object_type:"company"`, `source:{system,scope_id}`, `fields:{name,domain?,country?,address?,account_grain?}`                           | `inventory`, `pair_groups`, `metadata`                                                                                |
| `resolve-crm-contact-duplicates.play.ts` | `records_file`; optional `policy_json`                                                                                                        | `id`, `object_type:"contact"`, `source:{system,scope_id}`, `fields:{first_name,surname,email,dob,city}`; omit unavailable fields              | `record_inventory`, `pairs`, `clusters`, `metadata`                                                                   |
| `evaluate-crm-cleaning.play.ts`          | `mode` (`evaluate` or `validate_receipts`), `predictions_file`; evaluation also needs `inputs_file`, `labels_file`; optional `artifacts_file` | Frozen cases and receipts in separate files. Artifact rows contain unique `ref` and canonical `content_base64` bytes.                         | `summary`, `cases`, `failures`                                                                                        |

Use timezone-qualified `as_of` values. Keep labels outside candidate input. The sampler's manifest and inventory must come from the same collector run.

For audit input, map native HubSpot or Salesforce fields. For another source, set `source.adapter` to `canonical.v1` after explicit mapping. Supported canonical fields are `name`, `first_name`, `last_name`, `domain`, `website`, `email`, `job_title`, `company_id`, `parent_id`, and `modified_at`. Use strings or null; reference IDs also accept safe integers. Leads and Person Account-specific behavior are unsupported.

Audit and HubSpot helpers trim IDs and convert safe integer IDs to strings. Normalization collisions fail validation. Do not use this adapter when surrounding whitespace distinguishes identities.

The sampler includes source, object type, and retrieval time. Verify these fields and supply snapshot time before audit. Supply complete association lists separately from primary-company pointers. Map `last_name` to `surname` before contact resolution.

Domain-repair records need `id`, `source:{system,scope_id}`, and company `properties`. Candidates use the same scoped identity with `candidate_domain`, `discovery_refs`, `domain_evidence`, and `identity_assessment`. Use `plays/shared/domain-repairs.ts` for the exact contract. Context rows contain `{id,source,context}`. The collector's raw output needs explicit mapping and identity review before planning.

## Execute and inspect

Create `audit-input.json` with the approved `records_file`, `as_of`, and policy options. After approval, start the checked source:

```sh
deepline plays run --file ./audit-crm-snapshot.play.ts --input @audit-input.json --json
```

Export output datasets with the returned export commands. Inspect failed rows and coverage before claiming completion. Keep inventory order unchanged when verifying its hash.

Dataset rows contain `record_json` and run-specific `row_id` values. Repeated execution of one run reuses its keys. Separate runs retain separate evidence. Run output contains dataset references and fixed counts; detailed records remain in datasets.

For approved publication, first inspect `deepline plays publish <file> --dry-run --json`. Publish the checked file with its returned `--expected-artifact` hash. For an approved directory deploy, run `deepline plays deploy . --json`. The manifest selects all nine entrypoints. Both HubSpot entrypoints require the configured key. Publish only needed entrypoints when that prerequisite is absent.

Publishing and deployment do not read CRM records. Running a collector does. A valid bundle does not prove live access.

## Matching limits

Company scoring accepts at most 1000 records and compares every pair. Supply `name` explicitly; null preserves a missing name. Names have a 256-code-point limit before and after normalization. Optional country codes use uppercase two-letter values. `account_grain` accepts `legal_entity`, `brand`, `business_unit`, `location`, or `unknown`.

Each `pair_groups` row contains a left inventory index and tuples: `[right_record_index, name_jaro_winkler, retrieval_mask, review_mask]`. Join indices to `inventory`. Decode masks with `metadata.pair_group_schema`; `(mask & flag_value) !== 0` indicates a flag. Null scores mean missing names or no normalized letters, marks, or numbers.

Use `generated_pair_count` for pair totals; storage-group count is different. Every candidate remains unresolved. The 0.88 threshold controls retrieval, not identity confidence. Retain policy, case-fold, and runtime Unicode versions.

Contact resolution accepts at most 5000 records. This input limit does not establish safe runtime capacity. Completion for a dense 1000-contact cohort was not established within the bounded test. Output size depends on candidate count and evidence size. The dataset writer can reject materialization with `RUNTIME_MAP_MEMORY_LIMIT_EXCEEDED`; it does not truncate pairs. This guard does not bound memory during matching. The default policy is provisional. Validate it on separate target-population records before using proposals for merge review.

Both matchers compare pairs quadratically. Arbitrary batches can miss cross-batch duplicates. Omitted pairs remain unassessed. Input limits do not promise constant latency.

## Collection and evidence limits

The full HubSpot inventory can be held in memory by the runtime. It does not guarantee constant memory for large portals. The sampler retains unique IDs and a bounded company sample.

Complete pages and matching before/after totals detect some drift; they do not make scans atomic. The contact sample depends on the company sample. It cannot measure unlinked contacts. The sampler reads a fixed field set; use an approved export for narrower field selection.

Association continuations keep each source ID and cursor on the [same batch-read endpoint](https://developers.hubspot.com/changelog/bug-fix-batch-read-limit-for-hubspot-associations-api). Missing pages or repeated edges fail collection.

Domain collection uses guarded HTTP requests and DNS-over-HTTPS. Set `max_domains` to the approved row limit; the default is 1000. The cap limits collection, not CSV-read memory. Connected IP and TLS-session fields remain unknown. `max_bytes` limits text extraction after response receipt, not network download. Legal text and domain observations do not verify identity. Collector output removes URL credentials, query strings, fragments, and private response headers. Other analysis outputs retain source values for review; keep them private.

## Fingerprints and grades

Normalized fingerprints use versioned `crm-json-js-v1` JSON. Keys use Unicode code-point order; numbers use finite JavaScript values. Signal and duplicate-policy hashes use escaped ASCII strings. Inventory and evaluator hashes use Unicode strings. Scope identifies the variant.

Unsafe integer-valued numbers, duplicate JSON keys, and nonfinite values fail validation. Represent exact large IDs and decimals as strings. Number normalization can erase signed zero or underflow small values. Preserve original byte hashes; normalized hashes do not prove identical source bytes.

The frozen suffix list and case-fold table are versioned inputs. Changes require a new artifact and matching/domain evaluation.

The evaluator can complete with `passed:false`. Require `passed === true` for release. `receipt_only` checks supplied receipts; `retained_bytes` requires hashes that match supplied artifact bytes. Neither independently proves a live write. Invalid datasets and unsupported schema constraints fail execution.

The bundle has no live merge, paid-enrichment, enforcement, schedule, or parent-discovery implementation. Use the selected recipe and verified capability for approved operations.
