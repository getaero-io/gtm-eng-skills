# Run, Export, Inspect, Repair

Use this before scale, after every meaningful run, and whenever the user asks about billing, reruns, exports, cached rows, failed rows, logs, suspicious UI/output, or partial repair.

Do not rerun to answer a billing/debug question until the existing run is inspected.

## Core Commands

```bash
deepline plays run prebuilt/<name> --input '{...}' --watch
deepline plays run workflow.play.ts --input '{...}' --watch
deepline runs get <run-id> --full --json
deepline runs logs <run-id>
deepline runs export <run-id> --dataset result.rows --out rows.csv
deepline billing usage --limit 10
```

## Pilot And Scale

Pilot before scale:

- 1-3 rows for route shape.
- 5-10 rows for hard company/contact routes.
- Confirm required export columns are present.
- Confirm representative non-null values or explicit `miss_reason`.
- Estimate paid calls: source rows * people/account * fallback legs.
- Prefer billing modes that charge on hits/results over attempts where coverage is uncertain.

Scale only when row progress, coverage, errors, and fanout are understood. If cost is unknown or beyond pilot, explain and ask before scaling.

## Inspect A Run

`runs get <run-id> --full --json` should answer:

- status, run id, play reference
- started/completed time
- billing total credits and cap when available
- result dataset handles
- output preview
- row count
- executed/reused/failed counts when available
- provider/tool failure summaries
- cache/stale summary when available
- suggested export commands

If run-level billing is missing, say it is missing and fall back to `billing usage` only as a ledger check.

## Export

Export datasets before judging output quality:

```bash
deepline runs export <run-id> --dataset result.rows --out rows.csv
```

Good export output:

- flat user-facing headers
- nested objects flattened or projected usefully
- `status`, `miss_reason`, `source`, and evidence columns
- parent ids for child tables
- no raw provider blobs unless requested

For job-change, useful export headers include:

```text
linkedin_url,current_domain,job_change.status,job_change.date,job_change.new_company,job_change.new_title,job_change.incremental_hit
```

or an approved flat equivalent.

## Billing And Cache

When explaining cost, report:

- run id
- charged credits
- billing mode and expected pricing basis from describe, if known
- row count
- executed/reused/failed counts when visible
- cached/stale reuse explanation
- whether a zero-credit run appears to be cache reuse, no billable results, or missing metadata

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

After two same-class failures, change branch or export partials with miss reasons. Do not loop the same paid failure.

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
Charged: <credits or unknown/missing reason>.
Export: <path>.
Issues: <miss/failure classes>.
Next: <scale/rerun/repair/stop>.
```

When no paid run happened, say so and list the safe commands used.
