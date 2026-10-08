# Run, Export, Inspect, Repair

Canonical execution mechanics for GTM work: execute authorized work once, read
its overview, retrieve the selected complete output, then investigate specific
unanswered questions. Inspection does not authorize repair or another paid run.

## Contents

- [Choose the task](#choose-the-task)
- [Core commands](#core-commands)
- [Pilot and scale](#pilot-and-scale)
- [Inspect a run](#inspect-a-run)
- [Export](#export)
- [Inspect exported data](#inspect-exported-data)
- [Retrieve retained tool responses](#retrieve-retained-tool-responses)
- [Billing and cache](#billing-and-cache)
- [Repair classes](#repair-classes)
- [Partial failures](#partial-failures)
- [Suspicious UI or output](#suspicious-ui-or-output)
- [Final response shape](#final-response-shape)

## Choose The Task

| Request                                       | Execution boundary                                                                                                                                             |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inspect an existing run                       | Read that run and its retained outputs; do not start another run.                                                                                              |
| Run a supplied Play on a small, bounded input | Validate the input contract, execute once within the requested scope, and deliver all supplied rows including misses. No duplicate pilot or provider redesign. |
| Design new work or scale an unproven route    | Describe contracts and use an authorized bounded pilot where it resolves a concrete risk.                                                                      |
| Diagnose a failure                            | Gather retained evidence and explain the cause or evidence gap. Repair, refresh, fallback, and rerun require execution authority.                              |

Use the available CLI; install only if unavailable and authenticate only when
needed. Before concurrent Deepline commands, finish one standalone
`deepline preflight --json`. This does not authorize paid work.

Planning and inspection authorize no paid pilot. A bounded execution request
already authorizes its stated work; do not ask again after a successful pilot
unless scope, spend, risk, destination, or side effects materially change.
Monitor access checks and explicit paid-mutation consent still apply; follow
[the monitor recipe](../recipes/deepline-monitors.md). Execution authority does
not grant permission to send outreach, publish automation, or share sessions.

## Core Commands

```bash
deepline plays run prebuilt/<name> --input @input.json
deepline plays run workflow.play.ts --csv contacts.csv
deepline runs get <run-id> --json
deepline runs export <run-id> --dataset <returned-selector> --out rows.csv --json
```

These are alternatives for starting work, not instructions to run both forms.
Match inputs to the Play contract: the CSV example supplies `input.csv`;
`--input` accepts an inline JSON object or `@input.json`. Reserved `--file`
selects Play source, not data. Run waits and shows progress by default. Use `--no-wait`
only to start and return immediately. `runs tail <run-id>` follows an existing
run without starting work. See `deepline plays -h` and `deepline runs -h`,
then the relevant subcommand's `-h`, for more commands and options.
Use `plays describe` for a named Play and `plays check` for local source before
execution. `plays check` spends no provider credits but uses the compile API;
it is not offline. A supplied Play need not be rediscovered or replaced.

For a focused view of a named Play's inputs and invocation examples:

```bash
deepline plays describe <play> --json inputSchema,runCommand,examples
```

`--input` supplies inputs; `--json` controls output. Check each command's help
for supported selectors.

If waiting times out or the CLI disconnects, retrieve the existing run with
`runs get` or resume observation with `runs tail <run-id>`. A wait timeout does
not cancel execution. Do not resubmit just to get its results.

Do not pipe live CLI output through `head` or `tail`: the discarded section
may contain validity, warnings or failures. Use supported field selection, or
save complete stdout and stderr separately, check the CLI's exit status, then
analyze the saved response. Do not use `2>&1` to mix diagnostics into JSON.
Other pipes and deterministic JSON/CSV processing are fine when the original
response/export is preserved. Use `set -o pipefail` in Bash pipelines and label
filtered or sampled views. Use a CSV parser for slices: quoted fields can
contain newlines, so `head` is not a general CSV-row selector. Keep paid outputs
in a durable project-local working directory, not a temporary directory.

## Pilot And Scale

For new or larger unproven work, a pilot can test the following within the
approved population and budget. A small authorized supplied Play is already
the bounded run; do not execute a second sample first.

- 1-3 rows for route shape.
- 5-10 rows for hard company/contact routes.
- Confirm required export columns are present.
- Confirm representative non-null values or explicit `miss_reason`.
- Estimate paid calls: `source rows * people/account * fallback legs`.
- Prefer billing modes that charge on hits/results over attempts where coverage is uncertain.

Read the Play contract and `deepline plays list --show-cost` for available
static or observed per-row/per-run estimates. Inspect actual Deepline charges
only when needed and label extrapolations. On `plays share publish` and
`plays share update`, `--show-cost` instead opts into average cost metrics on
the public page when safe comparable run samples exist; it is not a spending
control. Sharing requires its own authority. `plays run` has no spending-cap
flag; neither a monthly cap nor an estimate is a runtime-enforced per-run cap.

Scale when row progress, coverage, errors, and fanout support the approved plan.
Ask when cost cannot be bounded within that authority or the plan must change,
not merely because a pilot ended. Do not widen a fixed input cohort or replace
its misses with newly sourced successes. Oversourcing belongs only to authorized
discovery where the target records are interchangeable.

## Inspect A Run

`runs get <run-id>` returns the structured JSON overview by default; explicit
`--json` is also accepted. Read the recorded:

- status, run id, play reference
- started/completed time
- retained result and available retrieval commands
- summaries and explicitly labeled output previews
- row count
- executed/reused/failed counts when available
- provider/tool failure summaries
- coverage, scope, and consistency warnings
- available SQL inspection and export commands

`result` preserves the retained return structure; dataset references point to
`datasets[]` by `datasetId`. Each dataset's `name` is its registered logical
name; `storage.schema` and `storage.table` are exact physical identifiers,
not alternative export selectors. Commands are flat under `actions`, including
`exportDatasetCmds` and run-filtered `queryTableSqlCmds`. An explicit
`exportUnavailable` explains a restriction. A preview may be
empty or partial while rows exist; neither that preview nor its summary is the
complete dataset.

Choose `queryTableSqlCmds` for read-only filtering, counts, grouping, and
inspection in place, or `exportDatasetCmds` for complete downloads and local
analysis. Neither path requires trying the other first. Start with the returned
SQL command; adapt its projection, filters, or aggregation while preserving the
exact schema/table and run predicate. A returned physical table is a valid SQL
target, not a guessed name. Export instead uses the returned dataset selector.
Both can expose the same stored rows, so agreement is not independent
corroboration. Label query limits and filters when reporting coverage.

`runs get <run-id> --full --json` resolves a result marked
`resultState: available_in_full` and adds diagnostics to the same overview.
It is not a complete row export: handles remain references. Historical runtime
root normalization is retained rather than guessed away. There is no
`runs get --compact` workflow. `--input` retrieves retained input separately.
This CLI presentation does not change the raw SDK/API contract: do not move
SDK `package.datasets` or raw billing fields under `diagnostics`.

`completed` describes execution, not successful enrichment of every row or
acceptance by an external destination. Step progress, dataset row counts,
summary populations, and preview counts can describe different populations.
Do not sum attempts as unique rows or infer zero failures from unfetched logs.
Report disagreements rather than silently substituting one count for another.

Use overview actions for the unanswered question. Actions are
commands to retrieve evidence, not evidence already fetched:

```bash
# Only when failure evidence or an external-delivery question requires it:
deepline runs logs <run-id> --failed --json
deepline runs logs <run-id> --log-level debug
# Save the complete retained stream when a bounded log view is insufficient:
deepline runs logs <run-id> --out run.log --json
# Only when the overview/logs do not expose the needed diagnostic or cost:
deepline runs get <run-id> --full --json
```

For typed history or cross-run failures, use `deepline runs logs --help`.
It lists every known searchable kind, payload fields and recorded filter
availability. `--kind step.failed --payloads` retrieves step failure details;
`--kind receipt.failed --payloads` retrieves durable work outcomes. A lifecycle
kind does not imply a `status` field. Continue with returned `next.logs`,
preserving the UTC window. See [Run logs and events](run-events.md) for the
shared catalog and text/search mode rules.

`--failed` is a terminal-failed-run window; it is not a universal row-miss
query. Logs can be sampled or truncated and do not replace durable output.
Debugging is conditional, not required on every run.

## Export

Choose the logical output from the overview's dataset selectors and export
actions; do not guess a backing table or assume every Play returns `result.rows`.
Multiple outputs need an explicit selector, such as `result.results` for a Play
that actually returns that path:

```bash
deepline runs export <run-id> --dataset <returned-selector> --out rows.csv --json
```

`--out` is required. Export retrieves the complete selected persisted dataset,
including failed rows and all dataset columns: authored, nested and generated
intermediates. `--dataset` selects an output, not a column subset. Export has
no column-filter flags and does not silently hide intermediate evidence.

CSV is the default, useful for spreadsheet delivery. Objects and arrays are
JSON-encoded text inside CSV cells. For programmatic investigation, preserve
native objects, arrays, booleans and nulls in a JSON array of rows:

```bash
deepline runs export <run-id> --dataset <returned-selector> --format json --out rows.json
```

`--json` controls the **stdout receipt**, not the file format. The receipt
includes `csv_path` or `json_path`, row count, columns and source. Optionally
save that metadata with `--metadata-out rows.meta.json`. Read the file and
receipt to verify delivery. A preview or summary is never a complete export.
JSON export preserves dataset values, not provider evidence the Play never
persisted; a null alone does not explain a miss or prove a provider failure.
Neither format automatically adds runtime status/error metadata to authored
rows. When that metadata is needed, consult the unchanged SDK
`client.runs.exportDatasetRows` contract in [the SDK reference](plays-sdk-reference.md),
including `rowMode: 'all'` and all pages.

Ordinary dataset export selects rows for the requested run, but underlying
Runtime Sheets are mutable: overwritten rows can disappear from an older run's
view. Explicitly shared handles can export the current table instead; if the
receipt has `CURRENT_SHARED_DATASET`, report that it may include other runs'
writes. Current-table exports and queries are not historical snapshots. Label
scope and any completeness gap; keep the original export before transforming
or joining it. Derived tables should identify their source and transformations.

Run-owned export checks run scope and completeness before writing the row file. Treat
a scope mismatch or incomplete result as a failed retrieval, not a delivered
partial artifact. If export is not ready, retry only retrieval when the error says it is
retryable. Scope mismatch, ambiguous selection, or unavailable output needs
resolution, not a Play rerun. Report missing rows and partial output honestly.

For a focused display or separately labeled derived deliverable, useful columns
include the following. Preserve the complete original export; these are not
instructions to remove columns during export:

- flat user-facing headers
- nested objects flattened or projected usefully
- `status`, `miss_reason`, `source`, and evidence columns
- parent ids for child tables
- no raw provider blobs unless requested

For a fixed supplied cohort, retain every input identity, including missing
emails, failed rows, and unresolved records. If the selected output omits a row,
reconcile against the input in a labeled derived view; absence is not proof of
why it failed. Do not drop invalid contacts from the execution report merely
because they must be excluded from an outreach list.

For job-change, useful export headers include:

```text
linkedin_url,current_domain,job_change.status,job_change.date,job_change.new_company,job_change.new_title,job_change.incremental_hit
```

or an approved flat equivalent.

## Inspect Exported Data

`csv show` reads a local file without modifying it or executing a Play. Start
with coverage across the file, then inspect the fields that answer the question:

```bash
deepline csv show rows.csv --summary
deepline csv show rows.csv --columns first_name,last_name,email --format table
# Use actual column names from the export for either inclusion or exclusion.
deepline csv show rows.csv --exclude-columns email_attempts --rows 20:39
```

- Normal display defaults to rows `0:19` (the first 20); it is a view, not proof
  of the whole population. Explicit `--rows start:end` is inclusive and also
  limits summary mode.
- `--summary` analyzes all file rows by default. JSON output has `rows` with
  one object per selected column, `total_rows` analyzed and `source_total_rows`
  in the file. Column fields are `column`, `present`, `missing`,
  `present_percent`, `unique`, `top_values` and `other_count`. Blank/whitespace
  cells count as missing; presence is not validation or a causal miss reason.
  Top values summarize frequencies when values repeat; all-unique columns have
  an empty top list. Nested CSV cells are counted as text, not semantic objects.
- `--columns a,b` includes named columns; `--exclude-columns c` omits them.
  Exclusions win; unknown names or selecting no columns fail explicitly.
  Neither changes the complete export on disk.
- Both modes accept `--format json|csv|table` (JSON by default). Table display
  can shorten long cells; `--verbose` shows full values, not extra columns.
  For native nested row evidence use JSON export, not CSV display's JSON format,
  which still represents CSV cells as strings.

See `deepline csv show -h` and `deepline runs export -h` for current options.
For joins or transformations, retain the original and label derived data.
Investigate misses from persisted row evidence first; use full diagnostics or
logs only for what it does not establish. Missing email, rejected candidate,
provider failure and absent evidence are different outcomes.

## Retrieve Retained Tool Responses

Read saved results when an exported row's mapped result or inline evidence
leaves a question unanswered. Use the original run's workspace and UTC window:

```bash
deepline runs logs <run-id> --kind receipt.completed --payloads --json
```

Select one returned `eventId` with `--where` for its exact saved details;
read `payload.output`. New failed-call details also use `receipt.completed`;
filter `$.context.callStatus == "failed"` to find them. Use `step.failed` for
causal step failures and follow `next.logs` to page. Check `runs logs --help` for filters. These reads
never execute tools. Missing evidence is a limitation to report, not permission
to rerun the Play or replace a deliberately pinned CLI.

Retained tool responses preserve existing redactions and list previews; they
are not guaranteed full HTTP wire captures. Stored and inline evidence can
have different wrappers. Inspect `rawV2` and the recorded view before
comparing; do not rewrite originals or infer provider variation from wrapper
differences. A skipped alternative has no provider result, a rejected candidate
is not necessarily an execution failure, and missing evidence stays unknown.
For authored resolution schemas, flat convenience fields copy the final answer;
`_dl_meta` explains intermediate work. Validate claims against the recorded
validator/source rather than treating a nonempty value as verified.

## Billing And Cache

When explaining cost, report:

- run id
- charged credits
- billing mode and expected pricing basis from describe, if known
- row count
- executed/reused/failed counts when visible
- cached/stale reuse explanation
- whether a zero-credit run appears to be cache reuse, no billable results, or missing metadata

Follow the overview's billing action. In CLI full JSON the billing payload is
`.diagnostics.billing`, not `.billing`; raw SDK/API reads are unchanged. Missing
billing is unknown, not zero. Recent `billing usage` can corroborate a ledger
question but is not proof of this run's cost; account balance deltas can include
concurrent work. Distinguish parent charges and available child rollups. Expose
Deepline charges only, never provider spend.

For result-priced job change:

```text
This appears to charge only on confirmed moved results. A 0-credit run can be normal if all rows reused cached work or no successful job-change event occurred.
```

Do not return credits as row output. Billing belongs in run metadata.

## Repair Classes

Classify before changing route:

- route mismatch
- described contract mismatch
- getter/output projection issue
- CSV/header/row validation issue
- provider/tool input issue
- credentials/permission issue
- infra/callback/scheduler/persistence issue
- runtime/code error
- UI/static-analysis/preview issue
- namespace/navigation issue

Preserve the evidence and propose the smallest repair. Do not automatically
change provider, refresh cached data, edit the Play, stop a run, or rerun it.
With repair authority, identify the cause and bound the affected rows and cost
before executing. Repeated same-class failures are a reason to stop and report,
not permission to cycle through paid alternatives. Completed receipts may be
reused; incomplete or ambiguous external work can execute again. Do not promise
a free or exactly-once rerun.

## Partial Failures

Runtime failures are acceptable when legible:

- One invalid row should mark one row/cell failed when possible.
- Batch-level infra failures can mark affected rows failed but must say why.
- Provider 422 row validation should become row failure when possible.
- Code/runtime errors can still fail the play if not row-scoped.

Export partials when useful. Preserve row failure metadata: tool id, provider, failure origin, and error class.

## Suspicious UI Or Output

Inspect/export before rerunning when:

- grid shows `true` for a nested object
- pricing disappeared from run rows
- namespace navigation opens "no plays found"
- static analysis shows extra/weird stages
- expected nested fields are null/missing
- output changed from object to boolean/string

Likely fixes:

- output schema or rowOutputSchema needs nested field paths
- final projection is returning truthiness instead of object fields
- run detail is hiding billingTotalCredits
- play reference namespace is wrong (`prebuilt/<name>` vs user/org/local)
- stale/cache metadata reused an old cell

## Final Response Shape

When a run happened:

```text
Ran <play-ref> on <N> rows.
Run id: <run-id>.
Result rows: <N>.
Executed/reused/failed: <x>/<y>/<z> when available.
Charged: <only if requested/decision-relevant; credits or unknown>.
Export: <path>.
Issues: <miss/failure classes>.
Next: <only if useful; distinguish a proposal from an authorized action>.
```

Show useful records and summarize found, missing, failed, and unknown outcomes
separately. Give the selected output, requested delivery path, completeness and
scope caveats. Billing investigation is optional unless requested or needed for
a spending decision. When only inspecting, say that no new run was started.
