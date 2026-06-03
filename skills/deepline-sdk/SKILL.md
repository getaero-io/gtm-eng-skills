---
name: deepline-sdk
description: 'Use for Deepline SDK/CLI GTM work: build/run/debug plays, find companies or contacts, enrich emails/phones/LinkedIn, control spend, and export CSVs.'
---

# Deepline SDK GTM Loop

Deepline work is paid uncertainty reduction. The job is to turn live provider contracts into a small replayable play, prove the shape on a few rows, then scale only when the rows match the user's requested output.

The play is the notebook. Stable step ids are the cache. Getter contracts are the interface. The CSV is the final surface.

## First Moves

Start with one compact preflight:

```bash
deepline preflight
```

Then find the closest existing route before touching individual providers:

```bash
deepline plays search "<capability>" --prebuilt
deepline plays describe prebuilt/<play-name> --json
deepline plays check prebuilt/<play-name>
deepline plays run prebuilt/<play-name> --input '{"limit":2}' --watch
```

Use `plays bootstrap` for route templates such as `people-email` or `company-people-email`, not for `prebuilt/<play-name>` references. To edit an existing prebuilt, clone it with `deepline plays get prebuilt/<play-name> --source --out scratchpad.play.ts`.
Bootstrap routes need a concrete source via `--from`. Never run bootstrap without `--from`; pick a CSV, provider, or earlier exported file first.

Use provider tools only after naming why a prebuilt play does not fit: missing input, missing output, wrong scale, direct-run-only, or a custom gate the user needs.

For company-list sourcing, try a structured company discovery prebuilt before raw company-search tools. For company rows to role-matched people with email, try a company-row-to-contact/email prebuilt before custom code.

Describe the chosen prebuilt before the first full run. The description is the contract; search results are only candidates.
Prebuilt search results are plays. Inspect them with `deepline plays describe ...`, not `deepline tools describe ...`.

For a new task, ignore workspace-owned plays unless the user names one explicitly. Owned plays may be old scratchpads with stale contracts, old runs, or unfinished output shapes.

For account-to-contact or account-to-contact-to-channel tasks, prefer a bootstrap route such as `company-people`, `company-people-email`, or `company-people-phone` over hand-composing source code from multiple plays. Hand-compose only after the route template cannot represent the chain, and write down that mismatch.

## Command Rules

- Run Deepline commands directly. Do not pipe Deepline output through `jq`, Python, `head`, `grep`, or shell parsing.
- Do not background Deepline commands. Wait for the command you started, read its result, then decide. `plays run --no-wait` is allowed for long Deepline runs when you immediately inspect the returned run id.
- Do not redirect Deepline stdout or stderr. If you start typing `|`, `2>&1`, `2>/dev/null`, `python3 -c`, `head`, or `grep` around a Deepline command, stop and use a narrower Deepline command instead.
- If a command used shell slicing or parsing, treat that as a failed command and rerun it directly with a narrower Deepline option before continuing.
- Use `--json` only when exact ids, schemas, getters, prices, or status fields are needed. For search, watched runs, and exports, prefer normal output.
- Never pass `--no-open`.
- Use `deepline tools search "<capability>"` for provider discovery. Do not invent `tools list` capability filters.
- Do not use `deepline db query` unless the user explicitly asks for SQL or storage debugging. Inspect runs with `deepline runs get <run-id> --full --json` and export with `deepline runs export <run-id> --out <path>`.
- If output is large, narrow the Deepline command. Do not solve large output by shell slicing.

## Build The Play

Bootstrap is a scaffold, not truth. Read it, delete examples that do not match the discovered contract, and keep only the route you are about to run.

Use these rules while editing:

- Put every provider call that can contribute final rows inside the play before continuing exploration.
- Use stable ids for slow or paid work.
- Call declared getters from `tools describe`; avoid payload archaeology.
- Add cheap scalar filtering, scoring, dedupe, and column shaping before `ctx.map`.
- Cap source rows and people per account before paid fanout.
- If a map-backed or direct-run-only prebuilt play fits, run it directly and export its table. Do not call it with `ctx.runPlay(...)` from another play.
- If you need validation or reshaping after a direct-run-only play, export first, then run a second play over the exported CSV.
- A map table exists only after its `ctx.map(...).run(...)` executed for that run. If the run has not reached that map, do not chase the table.

Dataset handles are bounded surfaces:

```text
const rows = await dataset.peek(5);
const materialized = await dataset.materialize(100);
```

Do not invent `.rows`, `.toArray()`, or unbounded materialization.

Use `staleAfterSeconds` when a column's value should refresh on its own schedule, like email verification, enrichment freshness, or profile data that changes over time. Put it on the column that creates the value:

```text
.withColumn('verified_email', verifyEmail, { staleAfterSeconds: 86400 })
```

Deepline will reuse fresh cells, recompute expired ones, and leave other columns alone.

For exportable row work, return the dataset handle produced by `.run()`:

```ts
import { definePlay } from 'deepline';

export default definePlay('skill-example-projection', async (ctx) => {
  const leads = [
    { company: 'Acme', domain: 'acme.example', priority: 'high' },
    { company: 'Beacon', domain: 'beacon.example', priority: 'medium' },
  ];

  const rows = await ctx
    .dataset('qualified_leads', leads)
    .withColumn('export_status', (row) =>
      row.priority === 'high' ? 'ready' : 'needs_review',
    )
    .run({ description: 'Shape leads into export-ready rows.' });

  return { rows };
});
```

## Pilot Before Scale

Run a few before running many. A normal ladder is `1 -> 5 -> 25 -> requested count`.

A pilot passes only when:

- requested columns are present under user-facing names;
- row shape is flat enough to export;
- category, account, persona, or channel fit is visible in evidence columns;
- nulls and misses have explicit reasons;
- downstream enrichment inputs are valid enough to use;
- price is known or bounded from Deepline-facing contract fields.

For list-building tasks with optional enrichment, make the deliverable projection early. Once the primary entity source works, shape rows with every requested column plus miss reasons, even if contact, email, phone, or profile fields are still blank. Enrichment should fill those columns; it should not be the first moment an exportable CSV exists.

If a direct-run play returns the requested export columns with miss reasons, keep that route and scale or export it. Do not hand-write provider code solely to improve sparse optional fields unless the user required those fields to be complete.
After a described prebuilt appears to fit, run a 1-2 row pilot before cloning or rewriting it. Clone only after that pilot proves a contract mismatch that input, export, or a small projection play cannot solve. Do not clone just to add scoring or reshaping that can be done after export.

For a full run that may take more than a couple minutes, start it with `--no-wait`, inspect it with `deepline runs get <run-id> --full --json`, and export with `deepline runs export <run-id> --out <path>`. If time is running out, export the best completed pilot or partial with miss reasons.

Optional enrichment can miss. A pilot with the primary entity rows, requested columns, provenance, and miss reasons can pass even when optional contact, phone, profile, or email fields are sparse. Scale that route, export the honest result, and report the miss rate instead of cloning/editing a working prebuilt.

A cheap failed pilot is still failed. Change route, add a gate, try a meaningfully different source branch, or export a small honest partial with miss reasons. Do not scale because the balance can afford it.

After a failed pilot, do not spend the remaining window running one-off direct probes for individual rows. One direct probe can validate whether the route is alive; after that, either change the play once, export a bounded partial with miss reasons, or stop with the blocker.

Clone a prebuilt only for a contract gap you cannot solve with run input, export, or a tiny follow-up projection play. Do not clone to tune source quality after an exportable direct run already exists.

## Price And Spend

Always show customer-visible Deepline price in status and final notes. Never expose provider spend, wholesale rates, or margin.

Before paid scale, report:

```text
Plan before paid scale:
- Goal: <target rows and required fields>
- Pilot: <rows attempted, useful rows, misses, run id>
- Route: <prebuilt play or custom provider chain, plus why>
- Limits: <source rows, people/account, fallback legs, stop conditions>
- Price: <observed pilot Deepline credits/USD> and <estimated full-run Deepline credits/USD>
- Inspect: deepline runs get <run-id> --full --json
```

Ask before scaling unless the user already gave a budget or the next step is a tiny pilot.

Prefer Deepline-managed billing routes. If a provider reports missing credentials, do not retry that same provider; switch to an available route or report the credential blocker.

## Repair Rules

Treat errors by class:

- Syntax or type error: fix the exact line, run `plays check`, then pilot again.
- Wrong column casing or row shape: add a normalizer/projection step; keep final columns in the user's requested names.
- Missing credentials: switch provider/play route or stop with the blocker.
- Callback, worker, or unreachable server error: run `deepline preflight` once, inspect the run if one exists, then report the infrastructure failure. Do not edit the play, clone a new play, inspect local tunnel files, kill processes, or switch to one-off paid tool calls for this error class.
- Timeout: export the best completed run or partial rows to the requested path, then report what remains.

After two failed repairs of the same class, stop looping on that branch. Switch route, reduce scope to a smaller pilot, or return the best available partial with miss reasons.

## Final Output

If the user asked for a file, writing that exact path is part of the task. Preserve requested columns, include provenance and miss reasons when useful, and mention run id plus Deepline price in the final note.
