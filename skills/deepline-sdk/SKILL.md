---
name: deepline-sdk
description: "Use this skill for Deepline SDK and CLI work: writing or running plays, enriching CSVs, prospecting, list-building, account research, contact enrichment, email/phone/LinkedIn lookup, ICP qualification, lead scoring, outreach copy, and provider-driven GTM workflows. Triggers on phrases like 'write a play', 'build a Deepline workflow', 'enrich this CSV', 'find contacts', 'build a TAM list', 'waterfall emails', 'detect job changes', 'score these leads', and on any request mentioning Deepline, plays, or GTM providers such as Apollo, Crustdata, Hunter, Dropleads, Clay-style enrichment, or LinkedIn scraping. Skip only when the request is a Clay table extraction (use clay-to-deepline), a cron/webhook setup with no enrichment work (use workflow-hello-world), or has no Deepline/outbound/data-enrichment dimension."
---

# Deepline SDK

Plays are the durable source of truth for GTM workflows. Build plays incrementally: capture the search itself, then enrichment, validation, scoring, and export as named checkpoints agents can inspect, rerun, and extend.

Why: GTM work is expensive to repeat and easy to fake. A good play shows what signals were searched, what evidence was found, what was reused, and what new enrichment ran.

## Core Workflow

1. Discover the live contract with the CLI.
2. Put the first useful search, lookup, or list pull inside a play.
3. Run a 1-2 example pilot and inspect the run.
4. Add the next enrichment, validation, score, or copy stage.
5. Rerun the same play. Stable ids reuse completed work; new ids compute only the new boundary.
6. Keep outputs and evidence in sandbox/workspace files the user can inspect.

This is the default: use the play as a durable scratchpad, not a one-shot script. The play should show the GTM work, not just consume a CSV that hides the hard part.

Direct CLI tool calls are probes only. Use count endpoints or `limit: 1`/`page_size: 1`; bigger pulls belong in the play. Treat probe output as disposable until the same provider call exists behind a stable id in a play. If a provider result feeds the deliverable, the search/enrichment must run through `ctx.tools.execute`, `ctx.map`, `ctx.runPlay`, or `deepline plays run`. If a prebuilt play has the wrong shape or fails, write or copy a local `.play.ts` and fix the play; do not finish with a shell, Node, or Python loop over `deepline tools execute`. If `plays check/run`, `runs get/list/export`, auth, sheet, or database infrastructure fails, stop with that blocker. Do not create the requested CSV from probe output or direct provider calls. A CSV produced outside the play hides the durable boundaries the user needs to rerun, audit, and extend.

## Route

1. Write `my-play.play.ts` with the SDK's `definePlay`.
2. Run it locally via the CLI: `deepline plays run my-play.play.ts --input '{...}' --watch`.
3. Promote it: `deepline plays set-live my-play.play.ts`. Now it's a registered play named `my-play`.
4. Invoke by name from anywhere: `deepline plays run my-play ...` from the CLI, or `ctx.runPlay('my-play', input)` from another play.

Same backend, three invocation paths.

## Mental model

Deepline has two kinds of building blocks. CLI probes answer questions; durable play steps accumulate progress.

Think of a play as a checkpointed data pipeline, not a final wrapper around manual CLI work. For multi-step work, use the CLI to probe the smallest unknowns cheaply, then move each confirmed provider call, row shape, filter, and output column into a local `*.play.ts` file with stable keys. Rerun the play after each step so Deepline can reuse durable checkpoints instead of repeating known-good work.

The loop:

1. Probe one provider/tool/play call with `describe` and a tiny sample run.
2. Add that step to the play with a stable `ctx.tools.execute`, `ctx.runPlay`, or `ctx.map(...).step(...)` key.
3. Run `deepline plays check <file.play.ts>`.
4. Run the play on a tiny input or one row.
5. Inspect the result, then add the next step.

When the user gives you an existing or starter `*.play.ts`, run it before
editing output getter paths. `tools describe` shows declared contracts and
semantic getters; it does not prove what that play serialized at runtime. If
the run output is empty, null, or shaped wrong, use the `top-level outputs:` or
`inspect rows:` `deepline db query` command printed by the run, then edit from
that stored row. Top-level `ctx.tools.execute` / `ctx.step` results are in
`top-level outputs`; `ctx.map` stage results are in `inspect rows`.

Use direct CLI calls for probes, schema inspection, and known prebuilt one-offs. Use a play as soon as the work has multiple provider calls, row fanout, a waterfall, intermediate filtering, or a final output schema the user may want to rerun.

A play should accumulate known-good steps. It should not be a last-minute escape hatch after broad CLI probing, JSON parsing failures, or output truncation. If a `plays check` failure takes more than two edits to resolve, stop and re-anchor on current play-authoring patterns in `shared/plays-best-practices.md`.

| Building block | What it is                                                                                                                                                                                                                                      | How to find one                           | How to invoke                                                                                                                   |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Tool**       | A single provider call. One tool ID per integration capability (e.g. an email-finder, a company-search, a job-search).                                                                                                                          | `deepline tools search <category>` | `deepline tools execute <id> --payload '{...}' --json` from the CLI, or `ctx.tools.execute({ id, tool, input, description })` from a play |
| **Play**       | A typed workflow that composes tools and other plays. Some plays are shipped by Deepline ("prebuilt") for canonical patterns like email waterfalls; others are written by you in a `*.play.ts` file ("custom"). Both kinds invoke the same way. | `deepline plays search <category>` | `deepline plays run <name-or-file> --input '{...}' --watch` from the CLI, or `ctx.runPlay(name, input)` from another play |


**Probe** vs **pipeline** is a judgment call:

- **Direct CLI probes** are the right answer for: a single provider lookup, a quick search to inspect what is available, an interactive exploration of a CSV, or kicking off a known prebuilt play once.
- **Custom `*.play.ts` pipelines** are the right answer when: the workflow has multiple row-aware stages (enrich, then validate; lookup, then qualify), the workflow needs to be durable across long runs, the workflow will be re-run on different inputs, or the typed composition makes the logic clearer than a chain of CLI commands.

If a prebuilt play already covers the goal, use it directly — do not wrap it in a custom play just to invoke it.

## Choose your job

Start by reading the matching job doc, then use the CLI loop below to discover live tool and play names. The rules and mental model above apply to every Deepline task, but the provider-specific path, the filters that silently fail, and the order to validate things in are in the job docs — they encode what previous runs learned the expensive way (broad people searches before company qualification, guessed payloads, missing evidence columns, runs that collected data but never wrote the CSV).

For multi-phase tasks (e.g. "find 5 VP Marketing contacts at US fintech companies and get work emails"), discovery and row-level enrichment are different phases — read both docs in order before executing. The first picks the source; the second handles the waterfall.

| If the user wants to… | Start in | Then read |
| --- | --- | --- |
| Find companies, build TAM, source accounts, find contacts | `jobs/finding-companies-and-contacts.md` | `shared/plays-best-practices.md` |
| Add contact data, account signals, research, validation, or scoring | `jobs/enriching-and-researching.md` | `shared/plays-best-practices.md` |
| Write outreach or qualification copy | `jobs/writing-outreach.md` | `jobs/enriching-and-researching.md` if evidence is thin |
| Build an incremental play | `shared/plays-best-practices.md` | `deepline plays search <task>` then `deepline plays get <play-name> --source` |
| Customize provider order | `jobs/enriching-and-researching.md` | `deepline plays search <task>` then `deepline plays get <play-name> --source` |
| Debug a stale, locked, failed, or surprising run | `references/debugging.md` | `shared/plays-best-practices.md` |

## CLI First

Names rot. Use the CLI to prove the live contract, then make the play perform that search or lookup as its first durable boundary.

Use plain search output for discovery. Do not add `--json` to `tools search` or `plays search` unless you have a specific machine-readable consumer and have inspected the returned shape first. Do not pipe search output through Python, `jq`, or brittle `grep` to infer IDs; read the visible results, choose the best candidate, then confirm it with `describe`. Use `--json` for `describe`, `execute`, and run inspection commands where structured contracts or debug data matter.

```bash
deepline tools search "company search"
deepline tools describe <tool-id> --json
deepline plays search "email"
deepline plays describe <play-name> --json
```

Tools go through `ctx.tools.execute`; plays go through `deepline plays run` or `ctx.runPlay`.

Useful play commands:

```bash
deepline plays check ./workflow.play.ts
deepline plays run ./workflow.play.ts --input '{"keyword":"fraud fintech"}' --watch
deepline runs get <run-id> --json
deepline runs export <run-id> --out results.csv
deepline plays search "email waterfall"
deepline plays get <play-name> --source --out ./waterfall.play.ts
```

When authoring a custom `*.play.ts`, keep the play file in the current working directory when `node_modules/deepline` is available there; otherwise use a project directory with the Deepline SDK dependencies installed. Eval and scratch workspaces may provide those dependencies locally, and in that case the play source should stay inside the current workspace. Do not search parent repos or unrelated worktrees for old `*.play.ts` scratch files. After a run completes, export the final CSV to the user-requested output path with `deepline runs export <run-id> --out <path>`.

## Scripts

Use these checked `.play.ts` files as copyable starting points. They are validated by `tests/scripts/deepline-sdk-skill-play-examples.test.ts` through the real SDK bundler and play preflight.

- `scripts/market-research-scratchpad.play.ts`: search first, then research on top.
- `scripts/lead-email-scratchpad.play.ts`: CSV input, durable row stages.
- `scripts/work-email-helper-waterfall.play.ts`: provider order with `steps()`, `when()`, and semantic `extractedValues.email?.get()` access.

When a play processes a CSV, the play owns the input field name. If the play declares `input: { csv: string }`, run it with `deepline plays run enrich.play.ts --csv leads.csv --watch` and call `ctx.csv(input.csv, { columns, required })`. A play can instead declare `leads_csv` or another unreserved name; the matching CLI flag is just the field name. If the play declares a field that collides with a reserved run flag, such as `file`, pass it through JSON input: `--input '{"file":"leads.csv"}'`. `ctx.csv()` with no argument is invalid. The return value is a `PlayDataset` — pass it directly to `ctx.map`, do not cast it, do not read `.length`, do not iterate it manually. Row progress, retries, idempotency, and table output all depend on the runtime owning the iteration; manual `for...of` loops break those guarantees. See `jobs/enriching-and-researching.md` for the row-work patterns built on this contract.

## SDK Shape

- `ctx.map('stage', rows).step(...).run({ key: ... })` is the current API. Do not pass `{ key }` as the third argument to `ctx.map`.
- `ctx.map(...).step('leader', ...)` writes the step result to `row.leader` in later map stages. It does not spread returned object fields onto the row. If the step returns `{ email }`, read `row.leader?.email`, not `row.email`. To create top-level fields, add a later `step('email', row => row.leader?.email ?? null)`.
- `ctx.tools.execute({ id, tool, input, description })` is the durable provider-call API inside plays.
- Tool results keep raw provider output at `result.toolResponse.raw`; semantic extractors live at `result.extractedValues.<target>?.get()`.
- For list-shaped tools, prefer `Object.values(result.extractedLists)[0]?.get() ?? []` over hand-parsing nested provider JSON.
- Keep all replay-sensitive work behind `ctx.*`. Play bodies can re-execute during retry or replay; bare `fetch`, `fs`, `Date.now()`, `Math.random()`, top-level side effects, and runtime env reads can produce different values on replay.

## Defaults

Pilot 1-2 examples, preserve evidence, return null on misses, write transforms as TypeScript in the play, keep replay-sensitive work behind `ctx.*`, and prefer prebuilts when they fit.
