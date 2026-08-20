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

The job defines truth. The catalog supplies executable moves. The Play records what worked.

```text
contract → compare → exploit → recover → export
```

This is ordinary TypeScript. Do not invent a DSL, an agent runtime, or a provider wrapper. A `SearchProgram` is one small function that calls a tool, fetch, child Play, private connector, or local artifact and returns a typed attempt. `runSearchExperiment` owns the fair pilot, ranked waterfall, holdout, gap-only retries, and cost/coverage report.

## Map the source terrain before code

For an open-world, thin-data, or costly job, read
`references/strategy-pre-research.md` **before** opening the scaffold. Start
with where the fact could live, not with which provider to call. This is the
execution-sized pre-research pass: catalog actions, public sources, private
data, and existing Plays are all candidate ways to materialize the same claim.

Write a one-screen source map for each stage. It is complete when the stage's
acceptance fact has three plausible, differently-shaped places to look and a
first small probe for each:

| Claim shape               | Places the fact may live                                                    | Different route geometries                                           |
| ------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Company and qualification | entity index, registry/filing, first-party page, internal account data      | filter query, registry page, direct source traversal                 |
| Current person and role   | people index, leadership directory, professional profile, CRM               | company/domain join, title/function query, profile/roster extraction |
| Revenue, event, or signal | structured data, dated public record, company document, internal event data | entity lookup, filing/document retrieval, event/date query           |

Use `tools list` and `tools describe` to map current catalog capabilities. Use
search to find the public source or dataset itself; once a source is known, map,
fetch, or parse that source directly. The map becomes 6–12 route cards across
the relevant stages. It is not a provider shopping list: each card says which
corpus, join, or failure mode makes it valuable when another route misses.

Treat the first catalog request as a preflight decision. If it fails and the
job needs a Deepline tool or durable runtime, record the exact error in the
source map and stop with the scaffold still unbound. Do not expand it into
throwing placeholder routes: they look like an experiment to a structural check
but cannot compare, exploit, or recover anything. A route based solely on an
already-confirmed local artifact or direct source may continue; otherwise report
`needs catalog/schema` rather than producing a pretend Play or CSV.

For supplied, trusted rows, skip company discovery but still map two independent
ways to complete each missing fact. For an actual source map, scout assignment,
and card format, read `references/strategy-pre-research.md`.

## The only live-information rule

Do not present a live result as complete until its durable Play has:

1. Compared two materially different routes on the same unit.
2. Used an observed valid route on a later unit.
3. Tried an eligible dormant route only for real unresolved gaps, or recorded why none remained within the credit cap.
4. Exported accepted and unresolved rows from the completed run.

When the user has not supplied company rows, the company-stage rows are source
partitions such as query shards, registry pages, or geography × category. The
company experiment produces the cohort. A literal array is appropriate only for
user-supplied known rows, because otherwise it hides the discovery decision the
Play is meant to test.

## Score a run; evaluate a concept

A **score** chooses a route inside one live Play. `runSearchExperiment` already
scores only accepted evidence: complete rows, verified required claims,
supported evidence, source misses, adapter failures, observed calls, and
observed Deepline credits. It exposes a cost/coverage frontier rather than
letting a model trade unsupported answers for a better-looking number.

An **eval** asks whether an approach generalizes beyond that one run. A concept
is an information geometry such as “registry page → operator evidence,” not a
provider name or a prompt variant. Run an eval when a workflow will recur, a
source map/scaffold/skill changed, or an economic claim needs evidence. A
single pilot plus untouched holdout is the smallest useful eval. A repeated
task needs a frozen case set that includes normal, sparse, and likely-miss
units.

Freeze these before comparing concepts:

1. The contract and denominator. Do not lower a required claim to make a
   candidate look better.
2. Cases, source/date snapshot where relevant, credit ceiling, and acceptance
   verifier. Each concept sees the same cases and its own receipts.
3. The decision order: hard truth and cohort gates first, then verified
   coverage, then marginal Deepline credits/calls and latency. Record unknown
   cost as unknown, never zero.

Export the run's result dataset **and** route scorecard. Across repeated evals,
compare the same scorecard columns by concept and failure slice. A route that
wins one easy pilot but loses sparse rows or produces adapter failures is a
local winner, not a reusable default. Read `references/evaluating.md` when
designing a repeated evaluation or changing this skill.

## Establish the execution boundary

Create the durable Play before sourcing final rows. It is the only artifact
allowed to produce the user-facing list: it keeps the pilot comparable, records
which route supplied each fact, and makes a later gap actionable. Direct calls
are valuable only as sentinel probes for an input or response seam; their rows
do not enter the final cohort.

The output receipt is concrete: before writing final rows, run
`run-and-export-search-experiment.py` and obtain its `{ ok: true, runId,
output }` response. Until that receipt exists, work is a source map or a probe,
not a deliverable. Writing a CSV from remembered values or direct-call results
hides which route won and erases the unresolved frontier, so it cannot close the
job.

The completed live artifact has four receipts:

1. Two materially different routes compared on the same unit.
2. An observed valid route used on a later untouched unit.
3. A dormant route challenged only for an unresolved gap, or an explicit reason
   no eligible route remains within the frozen Deepline-credit ceiling.
4. An export of accepted and unresolved rows from that completed Play run.

Use `tools list` and `tools describe` to seed cards without spending a row
budget. If a sentinel probe exposes a bad payload or adapter, repair or replace
that route in the Play before calling it again. Start the scaffold before a
third live route probe. This keeps discovery from becoming an unscored terminal
waterfall whose results cannot be exploited or recovered.

## Run the frontier loop

A single direct tool call is allowed only as a sentinel probe for an input or getter. If it errors, repair or replace that route in the Play. Do not issue more row-by-row terminal calls. A broken adapter is not a source miss.

## Decide the topology first

Write one sentence before touching tools:

```text
unit + decision + required facts + scale
```

| JTBD   | Unit                  | Required completion facts               |
| ------ | --------------------- | --------------------------------------- |
| Search | market partition      | identity + qualifying evidence          |
| Enrich | frozen supplied row   | requested claim for that exact identity |
| Signal | subject × time window | subject, change, dated source           |
| Score  | accepted row          | bound facts + reproducible verdict      |

Keep requested fields required. Do not make contacts, titles, LinkedIn, dates, or evidence optional merely to promote a run. A null requires an absence receipt: materially different routes tried, typed outcomes retained.

Choose one shape:

- **Known rows:** one experiment enriches the supplied rows.
- **Open-world discovery:** rows are query/page/geography/registry partitions, never remembered companies. The experiment emits accepted companies.
- **Company → person:** two stages. Company programs compete first; only `companyExperiment.finalResults` become contact rows. Company and people tools are sequential stages, not consensus.
- **End-to-end:** compare only when every program can produce the same complete final row from the same starting seam.

## Browse just enough catalog

Start with information roles, not a remembered vendor. Search, inspect the returned categories, then describe the two active and two possible dormant routes. Do not dump the full catalog or browse for minutes before coding.

```bash
deepline tools search "<information role and controls>" --json
deepline tools list <returned-category> --json
deepline tools describe <tool-id> --json \
  | python3 <skill-root>/scripts/show-declared-getters.py
```

The getter view can also read a saved contract without re-querying:
Also look for public primary sources, user-owned data, local artifacts, and
prebuilt Plays. The source terrain step above is required for open-world work;
assign 3–6 short-lived scouts by information geometry when the map needs more
than one perspective.

```bash
python3 <skill-root>/scripts/show-declared-getters.py "$WORKDIR/<tool-id>.json"
```

`tools describe` is the authoring contract. For every `ctx.tools.execute`, bind a named declared `playExpression` from the response that made that call:

```ts
const response = await ctx.tools.execute({
  id: 'route_a',
  tool: '...',
  input,
  description: '...',
});
const value = response.extractedValues.described_value?.get() ?? null;
```

For lists, map provider-shaped rows through the durable handle's `keys`, not a guessed raw preview path:

```ts
const list = response.extractedLists.companies;
if (!list) throw new Error('GETTER_REQUIRED: companies');
const rows = await list.get().peek(10);
const domainKey = list.keys.company_domain;
const domain = domainKey ? rows[0]?.[domainKey] : null;
```

Use `toolResponse.raw` only to bind a value back to an exact source excerpt, to debug, or for an explicitly undeclared field after one sentinel probe. Never cast it into an invented `Company[]` or `Person[]`. If a declared list lacks a needed field, that is an adapter seam: add an evidence route or bind the observed path after the probe.

## Write the first real Play now

Scaffold once, edit the first two routes, then run it. Do not read the whole reference library first.

```bash
python3 <skill-root>/scripts/scaffold-search-experiment.py \
  ./deepline/data/<task-slug> --name <task-slug>
```

For an open-world company → person job, use the stage-aware scaffold instead.
It is deliberately one Play, not a company collector plus a separate
`contact-lookup.play.ts`: that separate shape is how a direct loop bypasses the
pilot, winner selection, recovery, and accepted-company handoff.

```bash
python3 <skill-root>/scripts/scaffold-search-experiment.py \
  ./deepline/data/<task-slug> --name <task-slug> \
  --topology company-to-person
```

Change only these seams on the first pass:

1. `rows` and the required claim contract.
2. The incumbent's literal mechanism, declared getter, evidence binding, and canonical entity key.
3. One heterogeneous challenger that can satisfy the same stage contract.
4. The final row mapping.

The final mapping is the CSV contract. Use the field names the user asked for
exactly: an internal `company_domain` claim can export as `domain`,
`contact_title` as `title`, and `contact_linkedin` as `linkedin_url`. A useful
row with renamed headers still breaks downstream imports and hides coverage
checks.

Give each retained program an honest information shape and terminal lineage. Two vendors that return the same page may compete on coverage/cost, but cannot form independent evidence consensus. Several query variants of one provider can be a coverage fallback only when their observed miss behavior differs.

When five or more routes are viable, bind at least four before the first batch: two active, two dormant. This does **not** call them all per row. The helper fans the active pair out in parallel, exploits the winner, then spends dormant routes only on gaps. A catalog of twenty tools followed by two handwritten calls is not broad exploration.

One program must not put competing routes in `Promise.all` or a dataset column. The helper already parallelizes programs and needs separate outcomes to rank. If one mechanism truly has dependent calls, assign each result a named response and consume its own getter sequentially.

Use `boundClaim`, `found`, and `attempt` from the copied helpers. `boundClaim`
uses `bindResearchEvidenceToSource`: the literal returned value must occur in
the source receipt. Candidates are not final claims. A finder plus verifier is
a candidate seam plus an acceptance seam; a validator rejection reopens only
that row/claim.

For company → person, call `runSearchExperiment` twice. Derive the second stage from accepted company results, not a raw/handpicked side array:

```ts
const contactRows = companyExperiment.finalResults
  .filter((result) => result.complete)
  .map((result) => ({
    domain: verifiedSearchClaimValue<string>(result, 'company_domain'),
    company_name: verifiedSearchClaimValue<string>(result, 'company_name'),
  }));
```

If stage one yields zero accepted rows, stop before stage two. Inspect that run, repair one mapping/claim seam or replace one route, then rerun stage one. Do not substitute direct web research or a manual cohort.

## Run, inspect, recover

Use this one command for the first output. It runs the structural check, Play check, completed Play, and run-bound export; it refuses to overwrite a CSV.

```bash
python3 <skill-root>/scripts/run-and-export-search-experiment.py \
  ./deepline/data/<task-slug>/<task-slug>.play.ts \
  --input '{}' --out ./results.csv
```

For the stage-aware company → person scaffold, its printed command already has
`--company-to-person`. That enforces two experiments, live company discovery,
and the accepted-company handoff before a run can export.

Then inspect the run. If target coverage is unmet, repair a malformed getter, then test an unused heterogeneous route only for unresolved units. Do not declare `programs_exhausted` because two easy routes were tried while catalog options remain unbound. Stop when the contract is met, the frozen credit cap is met, or distinct eligible routes yield a real absence receipt.
The generated `run-and-export-search-experiment.py` command is the output gate.
Use it for the first result instead of calling `deepline plays run` directly: it
checks the experiment shape, runs the completed Play, and exports that run's
dataset. This is what prevents a syntactically valid ordinary Play from quietly
becoming an unscored batch or a hand-authored CSV.

Bind each retained route as one named `SearchProgram` with an honest hypothesis,
lineage, maximum calls, cost ceiling when paid, and expected miss. Add every
bound route to `boundProgramIds`. `explorationProgramCount` is the parallel
first wave, not the pool size. The runtime supplies parallelism across programs;
putting competing routes in one `Promise.all` hides their receipts and prevents
ranking.

Quality gates precede economics. Among valid results prefer fewer observed Deepline credits, then fewer calls. Use run receipts when present; otherwise use a catalog ceiling and label it unknown. Never expose provider spend.

Report: output path, run ID, initial/final waterfall, pilot and holdout result, recovery attempts, unresolved/absence receipts, and whole-run Deepline cost.

## Subagents and references

Use one or two short-lived subagents only when there are several genuinely different source geometries. Give each the same contract and one source lane. They return one strategy card and ordinary TypeScript block; the parent binds, runs, and judges routes. They do not execute providers or decide truth.

Read only the matching detail when needed:

| Need                                         | Read                                  |
| -------------------------------------------- | ------------------------------------- |
| Repeated strategy evaluation or skill change | `references/evaluating.md`            |
| Open-world company or people discovery       | `jobs/finding.md`                     |
| Known-row enrichment or scoring              | `jobs/enriching.md`                   |
| Automation or activation                     | `jobs/automating.md`                  |
| Tool choice and source geometry              | `references/provider-navigation.md`   |
| Source-first ideation or subagent lanes      | `references/strategy-pre-research.md` |
| Failed/empty/misshapen run                   | `references/debugging.md`             |
| General Play syntax                          | `shared/authoring.md`                 |
