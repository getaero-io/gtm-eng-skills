---
name: clay-to-deepline
description: 'Move Clay tables, workflows and functions to Deepline Plays, and compare what the same run costs in Clay and in Deepline. Use for any Clay migration, Clay export or bookmarklet JSON, Clay CLI workspace, "convert this Clay table", Clay credit cost, or "is Deepline cheaper than Clay". Reads a Clay CLI export or a bookmarklet / clay-extract.py JSON file. Makes the Plays, proves formula parity on real rows, and prices both sides.'
---

# Clay to Deepline

Convert Clay tables to Deepline Plays. Make one `withColumn` for each Clay column.
Prove that the formulas give the same values as Clay. Then compare the cost of
the Clay run with the cost of the Deepline run.

For run authority, pilots, and result retrieval, use [build, run and retrieve](../SKILL.md).

## 1. Choose the input

Two inputs give the same result. Each makes one export folder (`<dir>`). Every later command reads that folder.

| You have                                            | Command                         | Notes                                                                                           |
| --------------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------- |
| The Clay CLI (`clay`), logged in                    | `export <dir>`                  | Best input. Reads the whole workspace. Does not need a browser cookie. Read-only.               |
| A bookmarklet or `clay-extract.py` JSON (one table) | `import <dir> <file-or-folder>` | Use when the user has no Clay CLI. Read [clay-extraction.md](../references/clay-extraction.md). |
| A HAR file, or only a description of the table      | none                            | No command reads these. Use section 9, and mark every claim `config-inferred, unvalidated`.     |

The bookmarklet keeps display values. It does not keep structured `fields` for most actions.
Parity is weaker for formulas that read those actions. `import` prints a warning when this applies.

## 2. Commands

Set `S` to the script in this skill folder. Node 18 or later. No npm packages.

```bash
S=<this skill>/scripts/clay-to-deepline.mjs
node $S export  <dir> --rows 25                  # Clay CLI: tables, columns, functions, 25 full rows per table
node $S import  <dir> extract.json [more.json]   # bookmarklet / clay-extract.py JSON, or a folder of them
node $S compile <dir>                            # plays/*.play.ts, *.clay.js, seeds/*.csv, migration-report.json, keys.json
node $S parity  <dir>                            # each formula and lookup cell against Clay's stored value; exit 1 on a mismatch
node $S check   <dir>                            # deepline plays check on every play (free, no run)
node $S cost    <dir> [--plan launch|growth|legacy] [--pricing file.json]   # Clay cost and Deepline cost, per column
node $S workflow-cost <dir> wf_xxx [--limit 50] # Clay-metered credits for each completed workflow run
node $S sample  <dir> --table t_x --column "Work Email" --row-ids r_a,r_b   # one column and its inputs as a pilot play
node $S selftest                                 # Clay-semantics assertions, no network
```

- Add `--tables t_a,t_b` to `export` for a subset of tables.
- Run `compile` and `check` from a folder pinned to the target Deepline workspace.
  `compile` reads tool schemas with `deepline describe`. `check` validates credentials there.
- `import` and `export` can write to the same `<dir>`. The tables add up.
- No command in this list runs a paid Deepline call. `sample` only writes a play.

## 3. Output files

| File                                             | Use                                                                                                                                                                                                                                                                  |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plays/<table>.play.ts`                          | One play for each Clay table. Formula columns are local `withColumn`s. Actions are tool calls. Run conditions are `runIf`. Columns are in dependency order.                                                                                                          |
| `plays/<table>.clay.js`, `plays/clay-runtime.js` | Clay formulas and Clay semantics as plain JS. The play and `parity` import the same files. The parity result is about the code that the play runs.                                                                                                                   |
| `seeds/<table>.csv`                              | The input columns of the exported rows. Use it as a pilot CSV.                                                                                                                                                                                                       |
| `migration-report.json`                          | Each column with `kind` (seed, formula, local, lookup, waterfall, action) and `status` (compiled, mapped, needs_review, unmapped). Also the mapped tool and provider, `substitute`, `sameCapability`, `resolveTool`, `reuses`, and the reason a column needs review. |
| `keys.json`                                      | One row for each Deepline provider: `required`, `optional` or `managed`. Also whether Clay used the user's own key, and the `deepline tools connect` command.                                                                                                        |
| `parity-cells.csv`, `parity-columns.json`        | The parity verdict for each cell and each column. Show these to the user.                                                                                                                                                                                            |
| `billing.json`                                   | Written by `export`. Records whether the workspace is on an action-execution plan. `cost` reads it to choose the plan.                                                                                                                                               |
| `workflow-cost-<id>.json`                        | Written by `workflow-cost`. Clay-metered credits for each run.                                                                                                                                                                                                       |
| `cost-report.json`, `cost-columns.csv`           | Cost for each action column: Clay, Deepline, and the source of each number. See section 5.                                                                                                                                                                           |

## 4. Keys

`export` records the connection that each Clay action used: the workspace's own key, or the Clay shared key.
`compile` writes `keys.json`. Before any run, show this table to the user and ask the user to connect:

- Each `deeplineKey: required` provider (CRMs, sequencers: HubSpot, Salesforce, HeyReach). Deepline has no managed access for them. Their plays fail until connected.
- Each `optional` provider where `clayKeys` includes `own`. The user paid that vendor directly in Clay. The user keeps that contract and rate in Deepline.
- An `optional` provider that ran on a Clay-managed key runs on Deepline credits. A key is optional.

The user connects each provider with `deepline tools connect <provider>` (owner or admin; OAuth opens a browser),
or at the `setupUrl` in `keys.json`. Suggest `! deepline tools connect <provider>` so that it runs in the user's session.
Never ask for a key in chat. Never connect a key yourself. Run `check` again after the user connects.

## 5. Compare cost: Clay and Deepline

Run `cost <dir>` after `compile`. Without `compile`, the Deepline side is empty.
The command reads the completed Clay rows in `<dir>`. It does not start any Clay or Deepline run.

**How each number is found**

| Number                      | Source                                                                                                                                                                                               |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clay credits, from metadata | A credit key inside a cell `metadata` object. This is Clay's own record. When it exists, the command uses it (`claySource: metadata`).                                                               |
| Clay credits, from catalog  | If no metadata credit exists, the command uses the public Clay price catalog (`claySource: catalog`): data credits plus action credits, and the USD for each run on the chosen plan.                 |
| Vendor-reported credits     | A credit key inside `fields` (`credits_consumed`, `creditBurn`). The vendor wrote it. Clay did not bill this number. The command reports it as `vendorReportedAvg` and does not use it for Clay USD. |
| Deepline cost               | The mapped tool in `migration-report.json`, priced by `deepline describe` ("credits / $ per result").                                                                                                |

**Choose the plan**

The Clay CLI does not return the plan name or tier. Use this order:

1. The `--plan` flag, when the user states the plan.
2. `billing.json`. If `actionExecutionBalance` was absent, the workspace is on the legacy plan, and `cost` uses `legacy`.
   If it was present, the workspace is on an action-execution plan. The tier is unknown, so `cost` uses `growth`.
3. With no `billing.json` (for example after `import`), `cost` uses `growth`.

`cost-report.json` shows `planSource`. When the tier is unknown, ask the user for the tier. Do not guess it.

**Workflows have measured credits**

A table cell has no Clay billing field. A workflow run does.
`clay workflows runs get <runId>` returns `dataCreditsUsed` and `actionCreditsUsed`.
Run `workflow-cost <dir> wf_xxx` to total them over the completed runs.
These numbers are Clay's own metering (`source: metadata`). The totals are final only when a run is complete.
To see spend over a period for the whole workspace, run
`clay workflows analysis aggregate --input '{"groupBy":["workflow","day"]}'`.
This needs run analysis to be enabled for the workspace.

**Rules**

1. Say which source gave each Clay number. A catalog price is a plan estimate. A metadata number is a measured charge.
2. Do not call a vendor credit a Clay charge. The exported CLI cell has only `status`, `value` and `fields`. It has no Clay billing field. A bookmarklet cell can have `metadata`. Check one cell before you promise measured Clay cost. For a workflow, use `workflow-cost`.
3. Report `pricedBothSides` and `unpricedColumns`. AI columns, CRM writes, and unmapped actions have no fixed Deepline price. Do not add them to a total as zero.
4. The result is for the exported sample, scaled to the source row count of each table. State the sample size.
5. A tool priced "per result" bills a hit only. Clay can bill a miss. Treat the Deepline number as an upper bound for those columns.
6. Clay USD comes from a point-in-time catalog (`catalogUpdatedAt`). It is a plan estimate. It excludes plan fees and seats. Say this.
7. For a measured check, use `clay credits balance` before and after one pilot run. Other runs in the workspace change the balance. Use this only on a quiet workspace.

The public catalog is `https://code.deepline.com/api/public/gtm-data-pricing/clay-actions/export`.
Pass `--pricing <file>` to use a saved copy when the network is closed.

**Answer format.** Give a short table for the user: the five columns with the largest Clay cost, then the totals.

| Column | Clay action | Clay USD (source) | Deepline tool | Deepline USD | Note |
| ------ | ----------- | ----------------- | ------------- | ------------ | ---- |

After the table, give the total for the columns priced on both sides, the number of unpriced columns, and the sample size.

## 6. Clay semantics that the compiler reproduces

Each rule below was a parity failure on a real workspace. `parity` now covers each one.

- A Clay formula is a JavaScript expression. It is not a template. A raw newline inside a string literal is legal in Clay. The compiler escapes it.
- `{{column}}` on an action or source column reads its structured `fields`. Its `value` is only a display string, for example "No Record Found". A column with no `fields` reads as empty.
- `{{column}}?.a?.["b"]` resolves as one path lookup. A missing column or path is `''`. It is never `"undefined"`.
- Clay stores output as trimmed text, then types it with the column data type. A `url` or `email` that fails validation becomes empty. A `date` becomes ISO UTC. Text over about 8 KB becomes empty.
- `Clay.formatForJSON(x)` escapes text for use inside a JSON string that already has quotes.
- `moment` and lodash calls run on a small UTC subset: `format`, `isSame`, `isSameOrAfter`, `diff`, `toISOString`, `_.uniq`, `_.keys`. If the report shows another helper, add it to `clay-runtime.js`.
- `lookup-row-in-other-table` returns the first match in creation order as `{ record }`. `lookup-multiple-rows` returns `{ records, numberOfResults }`. The play takes the target table as a CSV input, `lookup_<tableId>`, with Clay column names as headers. Clay's own CSV export has this shape.

## 7. Waterfalls

A Clay waterfall is a merge column (`formulaType: waterfall`) over N provider columns.
Each provider column has a run condition. The condition skips the column when an earlier step found a validated value.
The compiler keeps this. The merge becomes `__clay.waterfall(step1, step2, ...)`. Each provider column keeps its own `runIf`.

How the compiler maps a vendor:

- **Same vendor, if Deepline has it.** Findymail stays Findymail. `find-email-v2` is Hunter. `validate-email` is ZeroBounce. `enrich-person` is PDL. The vendor comes from the connection type, not from the action key.
- **Same capability.** Clay's `google-company-to-domain` is the same Google search on Serper (`serper_google_search`). The report marks it `sameCapability`.
- **Two-step id lookup.** Dealroom and Crunchbase take their own entity ids. The column first searches by company domain, then calls the funding tool on the id. A call is skipped when its input is empty. Both vendors need the user's own key.
- **Vendor that Deepline does not have.** The compiler picks a substitute from an ordered pool. The pool skips providers that the table already uses. An identical call reuses the result of the earlier column. A waterfall `note` says when Deepline has fewer distinct providers than Clay.
- **Clay field names.** Clay formulas read Clay field names (`{{finder}}?.email`). A provider column is read through `__clay.view`. It finds the first non-null field with that name in the Deepline response. Without it, every gate reads empty and every step runs.
- **Empty input.** A tool call with an empty required input is skipped, as in Clay.

Pilot one waterfall with `sample`. Run it with `--max-credits`. Compare each row's step trace with the step that Clay hit.
Clay's stored hits can be months old. A same-vendor miss today is a data difference, not a mapping error.
Check that no later step ran after a validated hit.

## 8. Read `parity`

`parity` rebuilds each row from Clay's input cells. It compares each formula cell with the value that Clay stored.
A clean run shows `mismatch: 0`. Report the other verdicts as counts. Never report them as matches.

| Verdict                           | Meaning                                                                                                                      |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `match`                           | Same value. For a formula that reads the current time, "same" means both are empty or both are not empty. Count these apart. |
| `clay_not_evaluated`              | Clay never computed the cell (status `empty`). The play computes it.                                                         |
| `clay_stale_input` / `clay_stale` | An input is empty or stale. Clay's value is older than its inputs.                                                           |
| `dangling_ref`                    | The formula reads a deleted Clay column. Fix the formula in Clay or in the play.                                             |
| `clay_error`                      | Clay gave an error. The play made no value.                                                                                  |
| `not_in_sample`                   | Lookup only. Clay's matched row is not in the exported sample. Raise `--rows`.                                               |
| `target_changed_later`            | Lookup only. The target row or column is newer than this row. Clay does not re-run a lookup when its target changes.         |

`parity` covers formula, local, lookup and waterfall-merge columns. These are deterministic. They must match 100%.
Provider columns and AI columns return live data. Validate them on a paid pilot (`sample`, then section 11).
A formula that reads a provider output path is `config-inferred` until a pilot shows that the path resolves on a Deepline response.
A substitute vendor can change the response shape more than a same vendor does.

## 9. Work the compiler does not do

**Manual columns.** The compiler writes a column that throws, with the reason. A run fails loudly. It does not skip.
These actions are manual: `route-row`, `write-to-other-table-v2`, `trigger-find-people-source`, `lookup-company-in-other-table`, Google Docs writes, and Google Sheet upserts.
For `route-row`, write one filtered output CSV for each destination.

**Clay Functions.** A function table has a "Function inputs" source field (`f_subroutine_source`) and a `write-to-cell` action.
The compiler lists each function with its inputs and actions. It does not compile it. `clay functions get` returns an XML schema with action display names. It does not return action keys.
Port each function as one reusable play:

1. Make the play input from `SUBROUTINE_INPUTS`. If `tableSettings` is missing, use the distinct `{{f_subroutine_source}}?.["..."]` keys.
2. Add one `withColumn` for each field that is not a source and not `write-to-cell`. Keep dependency order.
3. Make the output from the `write-to-cell` `data` `formulaMap`. Do not build a `write-to-cell` column.

See the Functions section of [clay-extraction.md](../references/clay-extraction.md).

**Triggers and routing.** A table with a webhook trigger, a CRM write, or a campaign push needs a play with triggers.
Run `deepline plays --help`. Use the extracted config as the source.

**Unknown action.** Do not guess from the action name. Use this order:

1. The job-based table in [clay-api-surface.md](../references/clay-api-surface.md#map-by-job-not-by-provider-name). It covers about 85% of real usage.
2. The payload reference [clay-action-mappings.md](../references/clay-action-mappings.md). It has no phone or CRM rows. Verify each tool id.
3. The Clay action catalog in `clay-api-surface.md`, for the real input schema.
4. `deepline search "<input you have -> result you need>" --type tools`, then `deepline describe <tool>`.
5. If no tool fits, use `deeplineagent` with a `jsonSchema`.

Common mappings: email waterfall with `validate-email` is `name-and-domain-to-email-waterfall`. A phone column is `prebuilt/person-to-phone`; it needs a name and a domain, but many Clay finders need only a LinkedIn URL.
`use-ai` without web is `deeplineagent`. `chat-gpt-schema-mapper` is `deeplineagent` with `jsonSchema`.
A campaign push is `instantly_add_to_campaign` or `smartlead_push_to_campaign`.
A column with `enrich-person` as the key is often wired as a phone or email finder. Read `inputsBinding` first.

**Web research columns (`use-ai` with claygent).** Use two columns: `exa_search` for retrieval and `deeplineagent` for synthesis.
Add `research_confidence` and `research_passes` columns. Add the domain to every query. Quote the company name.
Judge the result by content, not by the confidence label. Count markers such as `UNCHANGED`, `UNRESOLVED` and `Unable to determine` as failed research.

**Prompts.** Use Clay's exact prompt text. A small change causes drift. Recover it in this order, and mark the source in the play:

1. HAR: `bulk-fetch-records` cell values have the rendered prompt.
2. Extract: `fields[].typeSettings.inputsBinding[name=prompt].formulaText` (`RECOVERED FROM EXTRACT`).
3. ClayMate `portableSchema` (`RECOVERED FROM PORTABLE SCHEMA`).
4. Approximation from outputs (`APPROXIMATED`).

In a recovered prompt, change `{{@Name}}` to `{{name}}`. Remove the `Clay.formatForAIPrompt(...)` wrapper. A single-brace `{name}` is not filled in by Deepline.

**No cell data.** Some extracts have config only. You cannot check the cell values of three or more records.
Infer the pipeline from `actionKey`, `conditionalRunFormulaText` and `formulaWaterfall`.
Mark every architecture and parity claim `config-inferred, unvalidated`. Do not decide anything that needs real cell values.

## 10. Rules

- Declaration order is execution order. Put local transforms before the paid columns that read them.
- Gate each expensive column with `runIf`. Do not pay for a row that a cheaper column already answered.
- A column reference is `row.alias`. A Clay path `{{a.items[0].b}}` becomes a typed read with explicit missing-value handling. TypeScript does not fill in braces.
- Use one `deeplineagent` call for each AI column. Put all fields in one `jsonSchema`.
- Accept `valid`, `valid_catch_all` and `catch_all` from email validation. Do not accept `unknown`.
- Never put a Clay cookie in a play or in a payload.
- A rerun is not free. A tool receipt is reused only when the tool and the input are the same. Do not promise a free rerun.

## 11. Validate and run

Thresholds:

| Column type                                 | Threshold                                                 |
| ------------------------------------------- | --------------------------------------------------------- |
| Formula, local, lookup, waterfall merge     | 100% match (`parity`, `mismatch: 0`)                      |
| LLM classification                          | 90% or more exact match on clear cases                    |
| LLM generation                              | Tone and intent match (manual review)                     |
| Structured (`deeplineagent` + `jsonSchema`) | All schema fields filled in 100% of rows                  |
| Email (`work_email`)                        | Deepline found rate is 95% or more of the Clay found rate |
| Web research                                | Failed research on 15% of rows or fewer                   |

For provider and AI columns, run a pilot. Then export it and compare each column with the same Clay rows:

```bash
node $S check  <dir>                                                               # step 1: compile only, no spend
deepline plays run <dir>/plays/<table>.play.ts --input '{"csv":"<dir>/seeds/<table>.csv"}' --max-credits <cap>   # step 2: pilot rows
deepline runs export <run-id> --out pilot.csv
deepline csv show pilot.csv --summary                                               # fill rate for each column
```

Join the pilot to Clay's cells (`rows/<tableId>/<rowId>.json`, `value` and `fields`) on the seed columns.
Report found rate and agreement for each column.

If a mismatch appears, check these in order: prompt parity, model parity, true ambiguity (run it three times). Then write it down. Do not tune the play to one row.

Authority and spend:

- Planning, `compile`, `parity`, `check` and `cost` permit no paid run.
- Start a paid pilot only with the user's approval of the scope and the cap. State the row count and the credit estimate.
- After a good pilot, run the rest of the approved scope. Ask again only if scope, cost or risk changes.
- `deepline plays check` calls the Deepline compile API. It needs auth and network.

## 12. Checklist

1. Choose the input (section 1). Run `export` or `import`.
2. Run `compile`, `parity` and `check`. Show the user the parity counts, `keys.json`, and the columns that need review.
3. Get the user's approval for the scope and the cap.
4. Run one pilot. Compare the provider and AI columns with Clay.
5. Run `cost`. Show the comparison table from section 5, with the source of each number.
6. Run the approved scope. Report coverage, spend, and the columns that stayed manual.
