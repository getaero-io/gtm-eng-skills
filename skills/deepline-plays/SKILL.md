---
name: deepline-plays
description: 'Use for Deepline GTM work that searches, enriches, scores, collects signals, or automates a workflow: find companies or people, enrich a CSV, find emails or LinkedIn, compare providers, build a waterfall, create a webhook or cron, or write a Play. For live information work, run a small heterogeneous experiment, exploit the observed winner, and reopen misses. Skip pure copywriting and non-GTM research.'
---

# Deepline Plays

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

## CLI resolution

Run `deepline` when it is available. If the shell reports that command is missing, use `<workspace-root>/.deepline/runtime/bin/deepline` (or the npm-created `.cmd` shim on Windows). If neither exists, follow `https://code.deepline.com/INSTALL.md` to set up Deepline.

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
deepline tools search "<information role and controls>" --json
deepline tools grep "<substring>" --json   # ranked search has returned the same
                                           # irrelevant hits for three different queries
deepline tools list <returned-category> --json
deepline tools describe <tool-id> --json | python3 <skill-root>/scripts/show-declared-getters.py
python3 <skill-root>/scripts/show-declared-getters.py "$WORKDIR/<tool-id>.json"   # saved contract
```

`tools describe` is the authoring contract and can disagree with runtime: a
declared getter has been absent, and a tool documenting one scalar has returned a
full list. Bind a named declared `playExpression` and sentinel-probe one row
before scaling. `toolResponse.raw` is for an exact source excerpt, debugging, or
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

## Subagents

One or two, only when several source geometries are plausible: same contract, one
source lane each, returning a strategy card and ordinary TypeScript. The parent
binds, runs, and judges. Verification fans out the same way — four defects found
in four sequential rounds of eyeballing output fit in one pass over row batches.
