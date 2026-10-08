# Debugging

A run failed, stalled, or produced unexpected output. Start with the overview
of the existing run, not a new execution:

```bash
deepline runs get <id> --json
```

Read lifecycle, progress, output selectors, summaries, errors and actions. A
completed run can contain row failures or ordinary data misses. Preview rows
are samples, not complete output. Follow the selected output's export action
before drawing population-wide conclusions. `result` preserves the return
structure; dataset references link to `datasets[]` by `datasetId`. Dataset names
are logical names, `storage` holds physical identifiers, and flat `actions`
hold retrieval commands. Use the returned commands rather than guessing paths
from a physical table name. `exportUnavailable` explains export restrictions.

Export keeps all columns, including intermediate evidence. Inspect a CSV with
`deepline csv show rows.csv --summary` for whole-file coverage, or
`--columns` / `--exclude-columns` for a focused display without changing the
file. For nested attempts or other structured evidence, use
`deepline runs export <id> --dataset <returned-selector> --format json --out rows.json`.
This preserves native nested values; CSV display's JSON format does not decode
JSON text inside cells. Inspect recorded attempts before attributing a null to
a provider failure. Missing evidence remains unknown, not permission to rerun.

For referenced tool evidence, use [retained tool responses](#retained-tool-responses)
before a new probe. For runtime questions, use only the next read that answers
the question: `runs watch <id>` to resume
observation, `runs logs <id> --failed --json` for a terminal failure window,
`runs logs <id> --log-level debug` for retained delivery/runtime detail, or
`runs get <id> --full --json` for the **same overview plus diagnostics** and a
retained result marked `available_in_full`. Dataset handles still need export.
There is no mandatory debug/full/log sequence on every run. Logs can be sampled
or truncated; missing evidence is not proof that nothing failed.

For typed history, start with `deepline runs logs --help` or the generated
[Run logs and events](run-events.md) catalog. Use `--kind run.failed`,
`step.failed` or `receipt.failed` to distinguish lifecycle failures from durable
work outcomes. `--where` matches only recorded indexed fields: a missing
`status` does not match even if the event kind ends in `.failed`.
`--payloads` returns canonical event details or retained receipt outcomes in
the same page; it does not export dataset rows. Continue with returned
`next.logs`; keep one explicit UTC window for reproducible comparisons.

Diagnosis alone does not authorize editing, stopping, rerunning, refreshing,
or changing providers.
The remedies below describe options when repairs are authorized; do not start
a new pilot to explain already-paid output.

## Retained tool responses

Read the exported row's authored final fields and stage evidence first. In a
resolution-based schema, ordinary fields are convenience copies; `_dl_meta`
holds intermediate evidence. A nonempty value is not validation, a skipped
alternative is not a miss, and a rejected candidate need not be a failed call.

Use `deepline runs logs <run-id> --kind receipt.completed --payloads --json`
for saved tool results, or `--kind receipt.failed` for recorded failures. Keep
the original run's workspace and UTC window. Select one returned `eventId`
with `--where` to retrieve its exact details; follow `next.logs` for more.
Read the returned `payload.output`. Missing details stay unknown and do not
justify a new provider call. Check `runs logs --help` for current filters.

Current `rawV2` receipts retain complete parsed and scrubbed provider data.
Inline list previews are separate and do not establish completeness; these
responses are not original HTTP bytes or headers. Compare the recorded `rawV2`
view and field values,
not wrapper equality alone. Keep originals unchanged. Missing evidence or an
unavailable command is a limitation to report, not authority to rerun or
replace a deliberately pinned CLI.

## Triage

One row per failure class. The row is usually the whole fix; the three deep-dives below are the exceptions.

| Symptom                                                                                                                      | Likely cause                                                                                                                                                                                                        | Fix                                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Column empty / getter path wrong                                                                                             | Play guessed a provider path or copied a `tools execute` probe shape; runtime wrapper differs                                                                                                                       | Inspect the persisted row, don't cast — see **Empty column** below                                                                                                                                                                                                                                                                                                                |
| Fails at registration or mid-run with replay / determinism / non-deterministic error                                         | An effect bypasses `ctx.*` in the play body                                                                                                                                                                         | Route it through `ctx.*` — see **Replay-safety** below                                                                                                                                                                                                                                                                                                                            |
| `plays run <name>` output doesn't match local file; or `set-live` rejects "local differs from stored source"                 | Live registered version is older than the local file; runtime ran the registered one                                                                                                                                | See **Set-live vs file** below                                                                                                                                                                                                                                                                                                                                                    |
| Confusing rerun output, or an old run keeps spending                                                                         | Concurrent runs may still be active                                                                                                                                                                                 | Inspect `deepline runs list --play <name> --status running --json` and identify the exact runs. Stop only with cancellation authority. Do not launch another run to inspect the current one.                                                                                                                                                                                      |
| **Input shape rejected** — schema/validation error, or empty set for a payload that worked before                            | Tool/play input contract changed; a field was renamed or an enum value moved (e.g. `c_level` → `C-Level`)                                                                                                           | `deepline plays describe <name> --json` / `deepline tools describe <id> --json` (authoritative), diff against your payload                                                                                                                                                                                                                                                        |
| **Provider returns nothing** — every row's column is `null`, run succeeded                                                   | Possible filter mismatch (`"United States"` vs `"USA"`), provider-class mismatch (work vs personal email), unsupported `/sales/lead/` URL, legitimate miss, or missing evidence                                     | Inspect retained inputs, row/cell outcomes and declared contracts. A null alone does not prove a bad filter. Use [finding](../jobs/finding.md) for enum/ISO rules and [enriching](../jobs/enriching.md) for provider classes. Propose a bounded probe only if evidence is insufficient and new execution is authorized.                                                           |
| `ctx.csv` / `ctx.dataset` error                                                                                              | `csv input not staged`: invocation and `ctx.csv(input.<field>)` disagree. `duplicate dataset key`: two `ctx.dataset` calls share a key. `cannot read .length of dataset`: code treats the `PlayDataset` as an array | staged: if `ctx.csv(input.csv)` invoke `--csv leads.csv`; if `ctx.csv(input.file)` invoke `--input '{"file":"leads.csv"}'` because **`--file` is reserved for the play file target**. dup key: distinct name per stage. length: pass the dataset to `ctx.dataset`; use `count()`/`peek()`, or `materialize(limit)` only for small bounded data. Contract in `shared/authoring.md` |
| Stuck — `tail` stops emitting, `runs get` still active                                                                       | Slow provider call (Apify, large searches), intentional sleep, backoff, or an execution fault                                                                                                                       | Inspect current-step source, timing, activity and retained logs. Resume observing the same run. Report unexplained lack of progress; elapsed time alone is not permission to stop and rerun.                                                                                                                                                                                      |
| Looks right, still fails (same payload worked yesterday)                                                                     | Environment drift                                                                                                                                                                                                   | `deepline auth status --json` (expired / wrong host), `deepline health` (runtime reachable), then re-check `tools describe` and the play's set-live version — a teammate may have shipped a breaking change                                                                                                                                                                       |
| **Declared getter is undefined at runtime**, or a tool documenting one scalar returns a full list                            | Declared and observed contracts can disagree: e.g. absent SERP `extractedLists` getter or maps `places[]` beyond the declared `phone`                                                                               | Inspect persisted evidence first (**Empty column** below); report the contract mismatch, not a source miss. If repair is authorized, bind only an evidenced path and validate before scaling.                                                                                                                                                                                     |
| **Export fails after a successful run** — "the backing dataset was not ready to export yet", possibly with a wrong row count | Materialization delay has been observed (~75s); other errors may be selector/scope failures                                                                                                                         | Retry the same retrieval only when its error is retryable; the experiment helper handles this materialization case. A current `db query` is not a run snapshot. Report unresolved completeness instead of rerunning the Play.                                                                                                                                                     |
| **Export demands `--dataset`** or exports the wrong table                                                                    | Multiple returned datasets make selection ambiguous                                                                                                                                                                 | Use the selector returned by the overview/export error. `result.results` is the experiment scaffold's result path, not a universal default. Its helper also exports the route scorecard.                                                                                                                                                                                          |
| Route scorecard shows `deepline_credits` empty, `cost_basis=catalog_upper_bound`                                             | No attempt carried a cost receipt, so the column can only hold a catalog bound                                                                                                                                      | Declare `tools: [...]` on each program and read the COST RECEIPT from `scripts/cost-receipt.py`, which joins the run's billing breakdown onto those ids                                                                                                                                                                                                                           |
| A registered route reports zero results but you never saw it run                                                             | It was never reached: `maxFallbacks` bounds the dependency-closed waterfall                                                                                                                                         | Check `reachability` in the scorecard. `never_reached` is not a source miss and not a coverage ceiling                                                                                                                                                                                                                                                                            |

## What a run cost

Investigate cost when asked or needed for a spending decision. Follow the
overview's billing action: CLI `runs get <id> --full --json` exposes billing at
`.diagnostics.billing`. Raw SDK/API billing fields are unchanged. Reuse and
execution counters are not charge receipts; they have historically disagreed.
An empty provider-event list does not by itself prove zero total charges.

Report available parent charges and child rollups separately. Inline
`ctx.runPlay` work belongs to the parent; independently launched child runs can
have their own charges. The experiment cost-receipt helper joins billing to
the route scorecard. Missing billing is unknown, not zero; account balance
deltas may include other work. Expose Deepline charges, never provider spend.

Use the installed CLI for clean JSON. Do not pipe live CLI output through
`head` or `tail`: this can hide validity, warnings and failures. Use supported
field selection, or save complete stdout and stderr separately, check the CLI's
exit status, then analyze the saved response. Do not merge diagnostics into
JSON with `2>&1`. Preserve failures through other pipelines with `pipefail`.
Do not silently discard arbitrary prefixes until malformed output happens to
parse.

## Empty column / getter path

Compare the run's persisted provider value with its derived column. Follow the
overview's selector/export actions before resorting to storage diagnostics.
Use a returned current-table query only with its mutable scope labeled; it is
not a historical snapshot. Tool execution returns an envelope: declared
semantic getters live under `extractedValues` / `extractedLists`, while raw
provider responses live under `toolResponse.rawV2`. Inspect the retained
response envelope; a direct probe can have a different wrapper. Upgrade and
rebundle an older artifact if it does not expose `rawV2`.
Use declared getters such as `result.extractedValues.email.get()` or
`result.extractedLists.people.get()` when supported. Do not cast an invented
shape or launch a new probe instead of inspecting existing evidence. With
repair authority, change extraction only from an evidenced contract; otherwise
report the discrepancy and proposed fix.

## Replay-safety

The play body re-executes during replay, so effects must be deterministic. Hunt
for `Date.now()`, `new Date()`, `Math.random()`, or `crypto.randomUUID()` outside
a `ctx.step`; filesystem reads/writes; bare `fetch`; `process.env`; and module
side effects. With repair authority, route external I/O through `ctx.*`, use
`ctx.secrets` for credentials, and reserve `ctx.step` for local nondeterminism,
not arbitrary filesystem/network work. See [authoring](../shared/authoring.md).

## Set-live vs file

`plays run <file.play.ts>` submits the local source; `plays run <name>` and
`ctx.runPlay` resolve the registered version. Compare the launched revision
and retained source before concluding that local edits were executed. Publish
with `deepline plays set-live <file.play.ts> --json` only when changing what
other callers run is authorized, not merely to investigate the mismatch.

## One-liners

```bash
# Latest failed run for a play
deepline runs list --play <name> --status failed --json | jq -r '.runs[0].runId'

# Watch the most recent run live (--jsonl prints events; swap for --json to wait for the terminal package)
deepline runs list --play <name> --json | jq -r '.runs[0].runId' | xargs -I {} deepline runs watch {} --jsonl

# Active runs older than a day (likely stuck)
deepline runs list --play <name> --status running --json | jq '.runs[] | select((.createdAt // 0) < ((now - 86400) * 1000))'
```
