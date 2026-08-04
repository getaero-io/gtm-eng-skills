---
name: deepline-plays
description: 'Run Deepline GTM workflows: find companies or people, enrich CSV rows, compare providers, build waterfalls, verify data, and write outreach from verified research. Trigger for provider-backed discovery, enrichment, research, scoring, outreach copy or sequences, or any request involving Deepline Plays. Skip Clay table conversion and work with no Deepline, outbound, or data-provider step.'
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

Turn a GTM request into an exportable row dataset and a reusable Play. For an
uncertain retrieval task, use one fast loop:

**PLAN → EXPLORE → RERANK → COMPOSE → EXPLOIT → VERIFY**

Do not scale the first plausible provider. Its private misses are not market
truth.

## Contract

- Answer-producing provider calls run inside a Play. Row work returns datasets.
- The task-authored Play contains literal tool calls and response adapters.
- `plays/shared/route-experiment.ts` owns generic fanout, failure isolation,
  canonical fusion, RRF, the bounded `ai_inference` judge, route scoring,
  portfolio selection, datasets, and atomic exploit.
- A provider error is excluded. A successful empty response is a measured miss.
- “Done” means inspectable rows were exported. Otherwise report `partial`.

## PLAN — generate retrieval hypotheses

Freeze the row grain, stable key, desired output, task-fit rubric, deterministic
delivery gates, credit limit, and stopping condition. Decide whether delivery
needs exactly one answer per input or a ranked set. A retrieved item can be a
person, company, source, signal, event, product, recommendation, or any other
task-defined result with a stable ID. Use `selected_item` only for exactly-one
jobs. Export `selected_items`, or expand one row per item, for ranked-set jobs.

Search the live Play and tool catalogs. Describe plausible actions and run only
the smallest probes needed to learn real input/output shapes. Put proposed
routes into the same one-row Play probe so independent calls run concurrently;
only successful schema-compatible routes proceed to the pilot. Generate
materially different routes by varying:

- source or provider;
- stable identifier;
- narrow versus broad query formulation;
- structured lookup versus public evidence;
- one action versus a small task-local composition.

Use 2–4 routes for a quick pass. Expand only when the first pass leaves useful
uncertainty and the budget supports it. Include at least one recall-oriented
route when exact filters could hide valid results.

## Author one code-native experiment Play

Copy `plays/shared/route-experiment.ts` and `plays/shared/rerank.ts` unchanged
into `./shared/` beside the task Play. Import `createRouteExperiment` and
`createAiInferenceJudge`. Only the routes, provider adapters, task rubric,
optional judge model override, and survivor enrichment are task-authored.
Declare each route as ordinary TypeScript with literal `ctx.tools.execute`
calls and a typed adapter that returns `RetrievedItemInput[]`.

Keep the top-level `definePlay` description to a 2–6 word outcome phrase, at
most 48 characters, with no trailing period. The UI uses it as the Play title.

```text
const routes = [
  {
    id, sourceFamilies, queryFamily, estimatedCreditsPerRow, maxItems,
    retrieve: async ({ row, rowCtx, limit }) => {
      const raw = await rowCtx.tools.execute({
        id: "route_specific_stable_call_id",
        tool: "literal_live_tool_id",
        input: { literal_schema_fields: row.value },
        description: "one sentence"
      })
      return adaptProvider(raw).slice(0, limit)
    }
  }
]

const experiment = createRouteExperiment({
  task,
  routes,
  judge: createAiInferenceJudge(),
  enrichSurvivors,
  maximumCreditsPerRow
})

const pilot = await ctx.dataset("route_experiment_pilot", pilotRows)
  .withColumn("route_results", experiment.routeResults)
  .withColumn("fused_items", experiment.fusedItems)
  .withColumn("judge_result", experiment.judgeResult)
  .withColumn("ranked_items", experiment.rankedItems)
  .run({ key: experiment.rowKey })

const selection = selectRoutes({
  rows: await pilot.materialize(1000),
  routes, task, maximumCreditsPerRow
})

// Persist scorecard + selection datasets visibly, bind selected route ids,
// then createRouteExperiment({...config, phase: "exploit", routes: selected})
// and declare the exploit dataset with the same columns. Add
// enriched_items plus selected_item and/or selected_items.
```

This snippet is conceptual. The task Play must use the live tool schema.
Every concurrent tool call needs a stable, distinct literal `id`; do not reuse
one placeholder across routes.

The normal validation path is enough:

```bash
deepline plays check ./task-route-experiment.play.ts
deepline plays run ./task-route-experiment.play.ts \
  --input '{"pilotCsv":"pilot.csv","exploitCsv":"full.csv"}' --watch
```

There is no strategy manifest, generated preflight Play, receipt, or custom
fingerprint. Play revision is code identity. A selection artifact contains
measured route IDs and evidence, not serialized executable code.

Keep each `ctx.dataset(...)` and its `.withColumn(...)` chain visible in the
task Play. Deepline's static sheet-contract checker cannot see dataset graphs
hidden inside imported helpers. The shared helper supplies resolvers and pure
kernels; the authored Play declares durable storage. See the complete,
zero-provider fixture in `plays/route-experiment.example.play.ts`.

## EXPLORE — parallel streams on the same rows

Start with one representative row to remove schema errors and unavailable
routes. Then run surviving routes on 3–5 stratified rows. Put each independent
provider/query in its own `routes[]` entry. Never invoke route callbacks in a
task-authored loop: `experiment.routeResults` fans them out concurrently.
Inside one route, use `mapBounded` for item fanout.

Each route returns a ranked item stream. Normalize retrieved items onto stable
keys:

| Item    | Preferred key                                 |
| ------- | --------------------------------------------- |
| Source  | canonical URL                                 |
| Person  | normalized LinkedIn URL or provider person ID |
| Company | normalized domain or provider company ID      |
| Product | canonical product/site URL                    |
| Other   | stable source ID or declared composite key    |

Never fuse on display name alone when collisions are plausible. Preserve facts,
source URLs, native ranks, evidence classes, route IDs, and errors.

Discovery routes emit observations and available evidence. Delay expensive
item enrichment. Fuse and rerank first. Run `enrichSurvivors` once per
canonical survivor after promotion, not once inside every discovery route.
Apply delivery gates to those enriched facts.

## RERANK — Last30Days-style fusion

The helper accumulates raw weighted reciprocal rank across every route stream:

```text
rawRrf(item) += routeWeight / (60 + nativeRank)
```

It never normalizes a weak route winner to equal a strong multi-route item.
Normalized RRF is only a blend/display signal.

The global pool is bounded before the judge. Make one batched judge call per
nonempty row with `createAiInferenceJudge()`. Its default is
`openai/gpt-5.6-luna` at low reasoning effort; override it only when measured
quality or cost warrants a different live Gateway model. The judge scores task
fit only. It does not prove identity, current employment, title, or any other
fact. Missing or partial judge output falls back to query-centric relevance,
RRF, freshness, and provenance signals.

Provider content is fenced as untrusted data. Do not make one model call per
item.

## COMPOSE — promote a route portfolio

Score routes on:

- relevant items contributed;
- items no other route found;
- source/query novelty;
- evaluable execution reliability;
- marginal Deepline credits.

Select a small complementary portfolio under the credit cap. The artifact is a
`deepline.route_selection` record with selected route IDs, scorecard, and
promotion evidence. The authored Play remains the executable strategy.

Do not require every discovery route to verify the final answer. A route can be
valuable because it finds an item or identifier that enables later work.

## EXPLOIT — run the selected code

Pass `exploitCsv` in the same run. The helper binds selected IDs back to the
in-memory route callbacks and starts the full dataset only after positive
promotion. Selected independent routes remain parallel.

Partition delivered and unresolved rows. Re-enter EXPLORE only for unresolved
rows and only with a materially independent source, identifier, query, or
composition. Stop at target, marginal-yield limit, depth limit, or budget.

## VERIFY — delivery facts, not retrieval relevance

Apply deterministic gates only when the task has a binary fact to check.
Examples include same person, current company, accepted title, canonical
company, recency, email validity, phone activity, and line type.

One authoritative source may verify a declared fact. Otherwise use the
task-declared number of independent weak source families. Agreement raises
confidence; it is not a universal discovery gate. Conflicts remain unresolved.
A high judge score cannot clear a failed fact gate.

Read the full run and use its dataset-specific export action. Inspect the CSV
header and sample rows. Preserve denominator rows, provenance, honest nulls,
and miss reasons. Report coverage as `N/M`.

## Route the job

| Work                             | Read                      |
| -------------------------------- | ------------------------- |
| Find companies or people         | `jobs/finding.md`         |
| Fill columns on existing rows    | `jobs/enriching.md`       |
| Write copy from verified rows    | `jobs/writing.md`         |
| Author or repair a Play          | `shared/authoring.md`     |
| Score routes and verify output   | `shared/correctness.md`   |
| Understand fusion and reranking  | `shared/reranking.md`     |
| Diagnose a failed or waiting run | `references/debugging.md` |

Provider effects use `ctx.*`. Customer-facing costs are Deepline credits only.
Paid tests use an explicit internal/test workspace.
