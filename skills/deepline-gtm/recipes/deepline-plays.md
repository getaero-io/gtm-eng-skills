---
name: deepline-plays
description: 'Create custom Deepline plays/scripts that combine multiple tools and/or other plays, with durable datasets, fallback logic, joins, projections, and custom run/export behavior.'
---

# Deepline Plays Recipe

Use this recipe when the user needs a custom Deepline play: durable TypeScript that combines multiple tools, calls other plays, maps over CSV rows, adds fallback logic, joins or projects output, persists datasets, or needs custom run/export behavior.

Read budget: normal tasks should use this recipe plus at most one plays reference. If you need more than one reference, name why before loading it.

## Negative Gates

| If the task is...                                                               | Use instead                                                                         |
| ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| A single existing prebuilt exactly solves the request                           | `deepline plays search` -> `deepline plays describe` -> direct `deepline plays run` |
| Ordinary row enrichment, waterfall columns, CSV processing, or per-row research | `enriching-and-researching.md` and `deepline enrich`                                |
| Company/contact/TAM sourcing strategy                                           | `finding-companies-and-contacts.md` and matching GTM recipe                         |
| Persisted webhook/cron-style automation, orchestration, or fanout               | Stay in this recipe and author a custom play with explicit inputs, idempotency, and run/export behavior |
| Exact SDK or HTTP syntax is the only question                                   | Load the generated reference named in Exact Syntax Escrow below                     |

## Core Loop

1. **Preflight:** check auth/health/balance when spend or cloud execution is likely.
2. **Describe before spend:** for plays, `plays search` -> `plays describe`; for tools, `tools search` -> `tools describe`.
3. **Choose direct vs compose:** direct-run only when the described contract exactly matches input, output, export, freshness, and pricing. Otherwise bootstrap, wrap, or author a custom play.
4. **Check before run:** `plays describe` gates prebuilts; `plays check <file>` is mandatory for local, bootstrapped, or forked plays.
5. **Pilot before scale:** run 1-3 rows or a small sample, then inspect/export.
6. **Report reality:** run id, export path, charged Deepline credits or why not visible, executed/reused/failed counts when available, and repair class.

Safe planning-only commands: auth/health/balance, `plays search`, `plays describe`, `tools search`, `tools describe`, `plays check`, `plays bootstrap --help`, and local scaffolding. Do not call `plays run` or provider execution in planning-only mode.

## Which Path

| Situation                                                           | First commands                                                                                      | Gate                                                        |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Existing play may fit exactly                                       | `deepline plays search "<job words>" --json`, then `deepline plays describe prebuilt/<name> --json` | Input/output/export/pricing/freshness match                 |
| CSV needs aliases, validation, projection, or joins                 | inspect headers, describe candidate play, then `plays bootstrap` or author wrapper                  | `plays check` and pilot pass                                |
| Custom multi-tool or multi-play orchestration                       | search/describe each tool/play contract, then author a `.play.ts`                                   | stable ids, durable datasets, and explicit final projection |
| Webhook/cron-style automation or cloud workflow replacement         | author a custom play with explicit inputs, idempotency, and run/export behavior                     | `plays check`, small pilot, and clear trigger handoff        |
| Company -> contacts -> email/phone fanout                           | use GTM sourcing docs first, then compose plays/tools only after the account/contact grain is clear | pilot proves account grain and contact identity             |
| Billing, rerun, export, cached rows, failed rows, suspicious output | `runs get`, `runs export`, `runs logs`                                                              | no paid rerun until run metadata is understood              |

Names in docs are hints. Live `search` and `describe` are the source of truth:

```bash
deepline plays search "<job words>" --json
deepline plays describe prebuilt/<candidate> --json
deepline tools search "<provider need>" --categories <category> --json
deepline tools describe <tool-id> --json
```

## Direct Prebuilt Run

Direct-run only when exact:

- described scalar/CSV/API input matches the user input
- no CSV mapping or semantic repair is needed
- output schema includes the requested result
- export dataset path is known
- freshness/caching behavior is acceptable
- pricing mode and likely scale are acceptable

Typical flow:

```bash
deepline plays describe prebuilt/<name> --json
deepline plays run prebuilt/<name> --input '{"field":"value"}' --watch
deepline runs get <run-id> --full --json
deepline runs export <run-id> --dataset result.rows --out rows.csv
```

For CSV prebuilts, compare required headers to actual headers. If aliases are unsupported or output projection is custom, bootstrap a wrapper instead of editing the prebuilt.

## Bootstrap, Wrap, Fork

Bootstrap is the composition tool. It is not anti-prebuilt.

Bootstrap or wrap when:

- CSV headers need mapping, validation, or projection
- a prebuilt is a useful stage but not the whole answer
- company rows need people/contact/channel fanout
- provider source rows need durable row state
- final output needs flat user-facing columns
- row gates, fallback legs, miss reasons, or stale policy matter

Fork only when internals need to change: provider/tool order, internal stale policy, getter metadata, billing stage, or native prebuilt logic. Do not fork for simple CSV aliases or final formatting.

```bash
deepline plays bootstrap <family> --from <source> --using play:prebuilt/<candidate> --limit 5 --out workflow.play.ts
deepline plays get prebuilt/<name> --source --out fork.play.ts
deepline plays check workflow.play.ts
```

Route families: `people-list`, `company-list`, `people-email`, `people-phone`, `company-people`, `company-people-email`, `company-people-phone`.

If bootstrap syntax fails, run `deepline plays bootstrap --help` or route help and retry with explicit stage flags such as `--people`, `--email`, or `--phone`.

## Authoring Basics

Use the current V2 shape from generated references when exact syntax matters:

```ts
import { definePlay } from 'deepline';

type Input = { limit?: number };

export default definePlay(
  'gtm-play',
  async (ctx, input: Input = {}) => {
    return { ok: true, limit: input.limit ?? 5 };
  },
  { billing: { maxCreditsPerRun: 50 } },
);
```

Authoring rules:

- Prefer typed inline input. Import validators only if generated refs or bootstrap output prove they exist.
- Use `ctx.csv`, `ctx.dataset`, `ctx.tools.execute`, `ctx.runPlay`, `ctx.step`, `ctx.fetch`, and `ctx.secrets`.
- Do not use local `fs`, raw `fetch`, shell commands, env reads, `Date.now`, or `Math.random` inside play bodies; replay can re-run the body and corrupt state.
- Use stable ids for paid work. Rename ids only to refresh wrong/stale provider data or changed semantics.
- Prefer one paid operation per dataset cell. Put shaping, projection, `status`, `miss_reason`, display fields, and transformations in separate pure columns after the paid column.
- Return datasets for CSV/exportable outputs.
- Use declared getters. Do not parse raw payload paths when `extractedValues.*.get()` exists.
- Project to flat user-facing columns with `status`, `miss_reason`, evidence/source, and requested output fields.

## Exact Syntax Escrow

Load these only when the task needs exact syntax or repair details:

- `references/plays-run-export-inspect-repair.md`: before scale; after every meaningful run; for billing, rerun, export, cached rows, failed rows, logs, suspicious output, partial repair, or UI/run mismatch.
- `references/plays-sdk-reference.md`: exact current SDK signatures for `.play.ts` authoring, `definePlay`, `ctx.dataset`, `ctx.runPlay`, `ctx.tools.execute`, staleness, and SDK client calls.
- `references/plays-api-reference.md`: exact API/manual invocation, polling, streaming, stop, list, inspect/export, and artifact routes.

## Finish Shape

When work ran, summarize:

- route and play reference
- run id
- rows requested and returned
- executed/reused/failed counts when visible
- charged Deepline credits or why credits are missing/zero
- export path and dataset path
- miss/failure classes
- next action: scale, rerun, repair, or stop

When no paid run happened, say so explicitly and list the safe commands used.
