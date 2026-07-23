# Debugging

A run failed, stalled, or produced wrong output. Run these three first, in order — they answer most "why did this stop working" questions before you read any play code:

```bash
deepline runs get <id> --full --json   # terminal state, progress, outputs, execution statistics, last event
deepline runs tail <id> --json         # waits and prints the terminal package (--jsonl streams live events instead)
deepline runs logs <id>                # ctx.log(...) output up to the failure (--failed for error lines, --json to parse)
```

`runs get` shows a failed run as `failed` with a final-event message; for a run that never completes it tells you whether it's mid-tool-call, retrying, or waiting. `tail --jsonl` reveals which.

## Triage

One row per failure class. The row is usually the whole fix; the three deep-dives below are the exceptions.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Column empty / getter path wrong | Play guessed a provider path or copied a `tools execute` probe shape; runtime wrapper differs | Inspect the persisted row, don't cast — see **Empty column** below |
| Fails at registration or mid-run with replay / determinism / non-deterministic error | An effect bypasses `ctx.*` in the play body | Route it through `ctx.*` — see **Replay-safety** below |
| `plays run <name>` output doesn't match local file; or `set-live` rejects "local differs from stored source" | Live registered version is older than the local file; runtime ran the registered one | See **Set-live vs file** below |
| Confusing rerun output, or an old run keeps spending | V2 allows concurrent runs; a stale run keeps its own sheets and keeps billing | `deepline runs list --play <name> --status running --json`, then `deepline runs stop <id> --reason "superseded" --json`. Row-level leases fence writes, so stale runs don't corrupt newer ones — they just waste spend. |
| **Input shape rejected** — schema/validation error, or empty set for a payload that worked before | Tool/play input contract changed; a field was renamed or an enum value moved (e.g. `c_level` → `C-Level`) | `deepline plays describe <name> --json` / `deepline tools describe <id> --json` (authoritative), diff against your payload |
| **Provider returns nothing** — every row's column is `null`, run succeeded | (1) wrong filter shape (`"United States"` vs `"USA"`); (2) wrong provider for the data class (work-email tool for a personal-email ask); (3) Sales Navigator `/sales/lead/` URL fed to an email waterfall — every provider rejects those | Pilot one row (`head -2 rows.csv > pilot.csv`; rerun `--csv pilot.csv`). Nothing back for row 1 → filter wrong. Data back but column null → extraction wrong. See `jobs/finding.md` enum/ISO rules, `jobs/enriching.md` provider-class rules |
| `ctx.csv` / `ctx.dataset` error | `csv input not staged`: invocation and `ctx.csv(input.<field>)` disagree. `duplicate dataset key`: two `ctx.dataset` calls share a key. `cannot read .length of dataset`: code treats the `PlayDataset` as an array | staged: if `ctx.csv(input.csv)` invoke `--csv leads.csv`; if `ctx.csv(input.file)` invoke `--input '{"file":"leads.csv"}'` because **`--file` is reserved for the play file target**. dup key: distinct name per stage. length: pass the dataset to `ctx.dataset`; use `count()`/`peek()`, or `materialize(limit)` only for small bounded data. Contract in `shared/authoring.md` |
| Stuck — `tail` stops emitting, `runs get` still active | Waiting: slow provider call (Apify actors, big company searches), an intentional `ctx.sleep`, or a quiet rate-limit backoff | Read the play source for the current step. Intentional waits and long provider calls: wait — the runtime handles retries/timeouts. Genuinely stuck (no progress 10+ min on a fast synchronous tool): `deepline runs stop <id> --reason "stuck on provider call" --json`, rerun |
| Looks right, still fails (same payload worked yesterday) | Environment drift | `deepline auth status --json` (expired / wrong host), `deepline health` (runtime reachable), then re-check `tools describe` and the play's set-live version — a teammate may have shipped a breaking change |

## Empty column / getter path

The authoritative output shape for a play is the object persisted by the run, not `tools execute` probe output and not `tools describe` (that's the input contract). `runs get --full --json` lists the persisted tables under `execution statistics` and prints ready `deepline db query` commands: `top-level outputs:` hits the run-receipt table for top-level `ctx.step` / `ctx.tools.execute` outputs; `inspect rows:` hits the map/runtime-sheet table for row-backed stages. Tool-result cells are JSON: raw provider data under `toolResponse.raw`, semantic getters under `extractedValues` / `extractedLists`. Query the row holding both the raw column and the derived column, then fix the play from what you see — use declared getters like `result.extractedValues.email.get()` / `result.extractedLists.people.get()` when the tool exposes them. Never add casts before inspecting the stage-table row or an explicit `ctx.log(...)` shape.

## Replay-safety

The play body re-executes during replay, so effects must be deterministic. Hunt the body for: `Date.now()`, `new Date()`, `Math.random()`, `crypto.randomUUID()` outside a `ctx.step`; `fs.readFile`/`fs.writeFile`; bare `fetch(url)` instead of `ctx.fetch('stable-key', url)` (first arg is the durable checkpoint key); `process.env.X` reads; any top-level side effect at module load. Route each through its `ctx.*` method, or wrap arbitrary work in `ctx.step('stable-id', () => op())`. Full safe-surface list in `shared/authoring.md`.

## Set-live vs file

`plays run <file.play.ts>` runs the local file directly — use it while iterating. `plays run <name>` and `ctx.runPlay` calls run the registered version, so publish with `deepline plays set-live <file.play.ts> --json` when the file is stable and you want callers to pick up the change.

## One-liners

```bash
# Latest failed run for a play
deepline runs list --play <name> --status failed --json | jq -r '.runs[0].runId'

# Tail the most recent run live (--jsonl streams; swap for --json to wait for the terminal package)
deepline runs list --play <name> --json | jq -r '.runs[0].runId' | xargs -I {} deepline runs tail {} --jsonl

# Active runs older than a day (likely stuck)
deepline runs list --play <name> --status running --json | jq '.runs[] | select((.createdAt // 0) < ((now - 86400) * 1000))'
```
