---
name: deepline-plays
description: 'Use for Deepline GTM work that searches, enriches, scores, collects signals, or automates a workflow: find companies or people, enrich a CSV, find emails or LinkedIn, compare providers, build a waterfall, create a webhook or cron, or write a Play. For live information work, run a small heterogeneous experiment, exploit the observed winner, and reopen misses. Skip pure copywriting and non-GTM research.'
---

# Deepline Plays

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

## Build, run and inspect

- **Discover/build:** search and describe relevant Plays/tools; reuse a suitable
  prebuilt. Use Plays for workflows and batches, direct tools for spot checks.
  See [authoring](shared/authoring.md) and the [SDK reference](references/sdk-reference.md).
- **Check/pilot:** inspect input mappings and run `deepline plays check <file>`
  before local-source execution. Pilot costly or unproven work within the agreed
  budget. Run small supplied Plays once, without a duplicate pilot or redesign.
- **Run:** `plays run` waits by default; `--no-wait` returns its ID immediately.
  Use `runs tail <run-id>` to follow an existing run and `runs get <run-id>`
  for status/results. After a disconnect, reconnect—don't relaunch.
- **Inspect/transform:** overview first, then follow the suggested commands.
  Play datasets persist in database tables. Prefer read-only SQL for filtering,
  joining, flattening and aggregating stored data before downloading. Inspect
  actual column types and sample values first; don't assume a JSON structure.
  After a type error, inspect the data rather than guessing another query.
  Adapt the suggested SQL, preserving its table and run filter.

  Get the run ID, physical tables and suggested SQL in one call:

  ```bash
  deepline runs get <run-id> --json run.id,datasets.storage,actions
  ```

  Use the returned schema/table for `<returned-table>` (for example,
  `"storage"."contact_email_waterfall_email_rows"`). Copy the run-membership
  predicate from the suggested SQL into `<returned-run-filter>` (for example,
  `_run_id = '<run-id>'`); storage alone doesn't supply it. Check additional
  status filters and sample limits before computing whole-run totals.
  Use the dataset's actual columns and JSON structure:

  ```sql
  -- Aggregate before downloading.
  SELECT domain, COUNT(*) AS contacts, COUNT(email) AS emails_found
  FROM <returned-table>
  WHERE <returned-run-filter>
  GROUP BY domain;
  ```

  These are read-only projections, not changes to stored rows.

- **Export:** use the suggested export command for complete rows, CSV for delivery
  or `--format json` for nested evidence. The response is a file receipt—read
  the file. Use `csv show <file> --summary` for local CSV summaries.
- **CLI hygiene:** use `-h`; run `deepline preflight --json` as a standalone command
  and wait before parallel Deepline work. No `head`/`tail` truncation of CLI responses;
  use field selection or summaries. Preserve complete responses, separate
  stderr from JSON, and check exit status (`pipefail` for pipelines).
- **Evidence:** previews aren't complete results; completed runs can contain
  failures; nulls don't explain misses. Inspect affected rows, then use
  `runs logs <run-id> --kind receipt.completed --payloads --json` for saved
  tool results. Select an exact result by its returned `eventId` with `--where`.
  Logs reads don't execute tools. Investigate unresolved requested conditions
  and stop once supported. See [debugging](references/debugging.md).
- **Save/scope:** keep deliverables in a durable project directory, preserve
  source files and every supplied identity, including misses and failed rows.
  Planning/inspection authorizes no paid execution; returned actions don't
  authorize retries, provider changes, publishing or external writes. Monitor
  access/consent remains separate. A credit shortage doesn't block otherwise
  accessible retained results.

**Read logs and events:** use `deepline runs logs --help` for all known kinds
and filter examples. A run ID alone reads text logs; omit it or add a search
flag to search events. Use `--kind` for run/step outcomes and `--payloads` for
available details or saved results. Follow `next.logs` to page with the same
UTC window. These reads execute no providers. Read
[Run logs and events](references/run-events.md) for more recipes and SDK fields.

**Write searchable customer logs:** use `ctx.log('Lookup finished', { context:
{ companyId: 'acme_123', rows: 12 } })`, then filter with
`--where '$.context.companyId == "acme_123"'`. The runtime attaches the
authenticated org, Run, Play and known attempt; do not copy those into context.
Customer KV cannot override that identity. Context allows eight flat scalar
fields and 2 KiB per line, with a 128 KiB context budget per run. Sampling and
run text limits also apply. Fetch large outputs through receipt events and
`--payloads`, rather than logging their bodies.

Typed provider activity events also expose safe `provider` and `operation` keys
for equality filters. They identify the provider and tool operation recorded by
the runtime; they do not index raw request/response bodies or promise one search
event per provider call.

```bash
deepline runs logs --kind run.failed --json
deepline runs logs --kind step.failed --payloads --json
deepline runs logs --kind receipt.failed --payloads --json
```

Before the first Deepline fanout in a task, run `deepline preflight --json` as
one standalone command and wait for it to finish. Never submit preflight beside
another Deepline command. After it succeeds, prefix every Deepline command that
may run concurrently with `DEEPLINE_SKIP_SELF_UPDATE=1`; serial commands may
stay bare.

The experiment methodology below applies when designing or comparing new work,
not to execution-only or existing-run inspection requests.

```text
contract → compare → exploit → recover → export → price
```

Ordinary TypeScript, no DSL. A `SearchProgram` is one function that calls a tool,
a fetch, a child Play, a connector, or a local artifact and returns a typed
attempt. `runSearchExperiment` owns the pilot, ranked waterfall, holdout,
gap-only retries, and cost/coverage report.

## Deliverable

| Part                | Contents                                                                |
| ------------------- | ----------------------------------------------------------------------- |
| **Result line**     | rows in / accepted / marginal credits per accepted row / run id         |
| **CSV**             | the user's exact headers, per-claim source, `miss_reason` on every null |
| **Unresolved rows** | in the same file; a null carries an absence receipt                     |
| **Route table**     | initial and final waterfall, cost and completions per route             |
| **COST RECEIPT**    | the block `run-and-export-search-experiment.py` prints, verbatim        |
| **Next actions**    | dormant routes and what each would buy, at measured cost deltas         |

- Marginal, never amortized. Total ÷ successes reported 1.51 credits/email for a
  route whose real marginal cost was 0.21.
- Pass the printed block through. Do not recompute credits in prose.
- A catalog ceiling stops the run; it is not spend. Label it. A 120-credit
  ceiling truncated recovery at ~12 credits actual, and two apparent logic
  regressions were budget artifacts.

## Read one job page

Read the row that matches this job, and only that row. Each page is complete for
its job: source geometry, route ladder, pilot sizing, stop conditions.

| The job                                         | Page                  |
| ----------------------------------------------- | --------------------- |
| Companies or people that are not rows yet       | `jobs/finding.md`     |
| Columns to fill on rows you already have        | `jobs/enriching.md`   |
| Claims that need attributable evidence          | `jobs/researching.md` |
| A trigger, review gate, or external side effect | `jobs/automating.md`  |

Two lookups, consulted on a trigger rather than read up front:
`shared/authoring.md` for Play syntax outside the scaffold, and
`references/debugging.md` for a failed, empty, or misshapen run.

For every public `definePlay`/`ctx.*` type, binding, durable-cache rule, and
runtime error, read `references/sdk-reference.md`. It is generated from the
authoring contract and SDK source; do not duplicate that surface in this skill.

**If your configuration forbids subagents, say so before starting serial work.**
Resolving that conflict silently cost one run ~30 minutes.

## Topology

Write `unit + decision + required facts + scale` before touching tools.
Requested fields stay required; demoting one to promote a run is not a pass. A
null needs an absence receipt: materially different routes tried, typed outcomes
retained.

One shape. **Known rows:** one experiment over the supplied rows. **Open-world
discovery:** rows are query/page/geography/registry partitions, never remembered
companies. **Company → person:** two sequential stages, not consensus; only
`companyExperiment.finalResults` become contact rows. **End-to-end:** compare
only when every program produces the same complete final row from the same seam.

## Catalog

```bash
deepline search --type tools "<information role and controls>"
deepline tools grep "<substring>" --json   # ranked search has returned the same
                                           # irrelevant hits for three different queries
deepline tools list <returned-category> --json
deepline tools describe <tool-id> --json | python3 <skill-root>/scripts/show-declared-getters.py
python3 <skill-root>/scripts/show-declared-getters.py "$WORKDIR/<tool-id>.json"   # saved contract
```

`tools describe` is the authoring contract and can disagree with runtime: a
declared getter has been absent, and a tool documenting one scalar has returned a
full list. Bind a named declared `playExpression` and sentinel-probe one row
before scaling. `toolResponse.rawV2` is for an exact source excerpt, debugging, or
an undeclared field after that probe — never a cast into an invented `Company[]`.

Cover source classes before provider names — index, SERP, primary document,
registry, event feed, first-party data, aggregator, validator. Two vendors
reaching the same terminal corpus are one evidence lineage.

Record each route's pricing basis: per call, per returned result, or unknown. A
confirmed-uncharged miss justifies a broader challenge wave, not a narrower one.

## Build and run

```bash
python3 <skill-root>/scripts/scaffold-search-experiment.py \
  ./deepline/data/<task-slug> --name <task-slug> --input-csv <rows.csv>
```

Read its printed `next` list: it carries the four seams, `tools: [...]`,
`coherenceChecks`, and the company→person handoff at the point you edit them.
`--input-csv` also writes a stratified `fixture.csv`. Iterate route code against
that; use the full cohort only for a scored run.

Keep the top-level `definePlay` description short and concrete. The UI shows it
below the Play identifier. Catalog categories are derived from the registered
tools used by the Play; do not author category metadata on the Play itself.

```bash
deepline billing balance --json
python3 <skill-root>/scripts/run-and-export-search-experiment.py \
  ./deepline/data/<task-slug>/<task-slug>.play.ts --input '{}' --out ./results.csv
python3 <skill-root>/scripts/cost-receipt.py <run-id> --scorecard <scorecard>.csv  # already-run
```

`run-and-export` does the structural check, Play check, completed Play, run-bound
export of both the results dataset and the route scorecard, then the COST
RECEIPT. Its `{ok: true, runId, output}` is the completion receipt: before it the
work is a probe, and a CSV written from remembered values hides which route won.

Receipt labels:

- **CUT CANDIDATE** — spent credits, completed nothing. Cut it. One route at 3.95
  credits/call, 200× a search, ran ten rounds for zero results because the
  scorecard reported no cost at all.
- **NEVER REACHED** — never invoked, so its zero results are not a ceiling and not
  a source miss. `maxFallbacks` bounds the dependency-closed waterfall and
  defaults to 2; raise it (up to 4, scaled to pool size) or drop the route.
- **cached calls** — reruns of the same inputs reuse tool receipts. Quote the
  marginal rate, not this run's total.

Quality gates precede economics; among valid results prefer fewer observed
credits, then fewer calls. Never expose provider spend.

Reusing a route across jobs is an eval, not a score: freeze the contract,
verifier, cases and ceiling, and stratify the case set (normal, sparse,
likely-miss, collision-prone) rather than picking easy rows after seeing results.
A concept is an information geometry, never a vendor.

## Product friction feedback

Unless the user restricts external reporting, send one proactive
`deepline feedback send` report per issue cluster when a Play
is disproportionately slow, appears stuck through repeated status checks, or an
ordinary result requires avoidable product steps. Continue the user's task after
reporting; feedback is not the deliverable and does not authorize paid
reproduction or session sharing.

Use judgment rather than a fixed threshold. Do not report normal provider work
just because it is not instant. Report when the duration is surprising for the
input size or prior comparable runs, progress stays uninformative, or the path
needs avoidable discovery, conversion, ID extraction, retry, export, or manual
workaround steps.

Include the goal and Play/run ID. For latency, include input size, observed
duration, status transitions or polling count, and expected progress. For excess
steps, include the actual path, avoidable detours, and expected direct path. Do
not pass `--requested` for a proactive report. Omit `--error-outcome` when no
error occurred; if an error did occur, use `terminal` only when it stopped the
task and `continued` when work continued.

```bash
deepline feedback send "Goal: <goal>. Play/run: <play and run id>. Friction: <what was slow or indirect>. Observed: <duration, polling, or actual steps>. Expected: <reasonable duration, progress, or direct path>."
```

## Subagents

One or two, only when several source geometries are plausible: same contract, one
source lane each, returning a strategy card and ordinary TypeScript. The parent
binds, runs, and judges. Verification fans out the same way — four defects found
in four sequential rounds of eyeballing output fit in one pass over row batches.
