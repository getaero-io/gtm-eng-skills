---
name: deepline-plays
description: 'Create, audit, and modernize Deepline Plays that combine tools or other Plays, with durable datasets, fallback logic, joins, projections, and custom run/export behavior.'
---

# Deepline Plays Recipe

Use this recipe when the user needs a custom Deepline Play or asks to audit an existing local or saved Play for deprecated APIs, tool IDs, Play references, or command patterns.

Read budget: normal tasks should use this recipe plus at most one plays reference. If you need more than one reference, name why before loading it.

## Negative Gates

| If the task is...                                                               | Use instead                                                                                             |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| A single existing prebuilt exactly solves the request                           | `deepline plays search` -> `deepline plays describe` -> direct `deepline plays run`                     |
| Ordinary row enrichment, waterfall columns, CSV processing, or per-row research | `enriching-and-researching.md` (prebuilt plays and their batch forms)                                   |
| Company/contact/TAM sourcing strategy                                           | `finding-companies-and-contacts.md` and matching GTM recipe                                             |
| Persisted webhook/cron-style automation, orchestration, or fanout               | Stay in this recipe and author a custom play with explicit inputs, idempotency, and run/export behavior |
| Exact SDK or HTTP syntax is the only question                                   | Load the generated reference named in Exact Syntax Escrow below                                         |

## Core Loop

1. **Preflight:** when spend or cloud execution is likely, run `deepline preflight --json` as one standalone command and wait for it before launching any parallel Deepline commands.
2. **Describe before spend:** for plays, `plays search` -> `plays describe`; for tools, `tools search` -> `tools describe`.
3. **Choose direct vs compose:** direct-run only when the described contract exactly matches input, output, export, freshness, and pricing. Otherwise bootstrap, wrap, or author a custom play.
4. **Check before run:** `plays describe` gates prebuilts; `plays check <file>` is mandatory for local, bootstrapped, or forked plays.
5. **Pilot before scale:** run 1-3 rows or a small sample, then inspect/export.
6. **Report reality:** run id, export path, charged Deepline credits or why not visible, executed/reused/failed counts when available, and repair class.

Safe planning-only commands: auth/health/balance, `plays search`, `plays describe`, `tools search`, `tools describe`, `plays check`, `plays bootstrap --help`, and local scaffolding. Do not call `plays run` or provider execution in planning-only mode.

## Audit Existing Plays

Treat “audit my Plays,” “check whether these Plays are outdated,” and “find deprecated Deepline usage” as a read-only check unless the user also asks for repairs. `deepline plays check` owns the authoring and deprecation policy; do not recreate a second checklist from memory.

1. Establish whether the scope is local `*.play.ts` files, saved non-archived workspace Plays, or both. Inventory local Plays with hidden and gitignored files included while excluding dependency/build directories. Inventory saved Plays with `deepline plays list --json`; do not claim completeness if the owned result page is capped or the user requested archived Plays that the CLI cannot enumerate.
2. For saved Plays, check every applicable live and dirty working revision. Fetch each revision's complete source bundle into a unique temporary directory outside the repository, preserve its entry file, and remove the exact temporary directory after the audit.
3. Run `deepline plays check <entry-file> --json` for every in-scope local or materialized saved revision. Checking is read-only and spends no provider credits. A named check is not a substitute for checking the revision's source bundle.
4. Read `issues` as the remediation queue. Fix every `error` first because it is Blocking; then fix every `warning` because it is non-blocking migration debt. Use each issue's `path`, `hint`, `validOptions`, and `docsHint`; do not guess replacements. Rerun `plays check` after each Play until both arrays are empty.
5. If a warning says validation is partial—for example, a dynamic tool id could not be resolved—make the identity static or report that the Play could not be certified clean. A successful check with unresolved warning issues is not a clean deprecation audit.

Report one row per emitted issue with the Play/revision, severity, path, message, and prescribed fix. Finish with error and warning counts and name every checked Play/revision. Do not edit during an audit-only request, and do not publish or run repaired Plays without separate authorization.

`plays check` audits Play source, not neighboring shell scripts or runbooks. If the user explicitly includes companion automation in scope, audit those separately for retired CLI commands and label that result separately from the Play linter.

### Trigger notification handoff

After publishing a cron- or webhook-triggered play, verify the product notification path. Do not assume the trigger can report its own failure.

```bash
deepline notifications list
deepline notifications events
deepline notifications slack channels --search pipeline
deepline notifications add pipeline-watchdog --to slack:#pipeline-alerts --for play.cron.failed
deepline notifications test pipeline-watchdog
```

Slack OAuth belongs in Dashboard → Integrations. This CLI only configures named notifications: each one selects a connected provider target and the Play events it receives. Use `deepline notifications list` before editing a rule; do not guess event IDs. Delivery retries and dead-letter handling are bounded internal reliability behavior, not a customer configuration surface.

## Which Path

| Situation                                                           | First commands                                                                                      | Gate                                                        |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Existing play may fit exactly                                       | `deepline plays search "<job words>" --json`, then `deepline plays describe prebuilt/<name> --json` | Input/output/export/pricing/freshness match                 |
| CSV needs aliases, validation, projection, or joins                 | inspect headers, describe candidate play, then `plays bootstrap` or author wrapper                  | `plays check` and pilot pass                                |
| Custom multi-tool or multi-play orchestration                       | search/describe each tool/play contract, then author a `.play.ts`                                   | stable ids, durable datasets, and explicit final projection |
| Webhook/cron-style automation or cloud workflow replacement         | author a custom play with explicit inputs, idempotency, and run/export behavior                     | `plays check`, small pilot, and clear trigger handoff       |
| Company -> contacts -> email/phone fanout                           | use GTM sourcing docs first, then compose plays/tools only after the account/contact grain is clear | pilot proves account grain and contact identity             |
| Billing, rerun, export, cached rows, failed rows, suspicious output | `runs get`, `runs export`, `runs logs`                                                              | no paid rerun until run metadata is understood              |
| Existing Play may use deprecated APIs, tool IDs, or aliases         | inventory, `plays check`, then describe every referenced tool/Play                                  | report line-level findings before any edit, publish, or run |

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
- Do not use local `fs`, raw `fetch`, or shell commands anywhere in a Play, including inside `ctx.step`; route external I/O through the matching `ctx.*` API so retries remain safe. Put local nondeterministic computation such as `Date.now` or `Math.random` in a durable `ctx.step` callback. Always use `ctx.secrets` for credentials, never `process.env`, including inside a step — see External HTTP And Secrets below.
- Use stable ids for paid work. Rename ids only to refresh wrong/stale provider data or changed semantics.
- The default Play runtime is 30 minutes. For a bounded long batch, set the
  Play-level option `runtime: { timeout: '90m', size: 'standard' }`; static
  whole-minute/hour durations are supported up to `4h`. This is not the CLI
  wait timeout or `ctx.tools.execute({ timeoutMs })`, which applies to one
  provider-call transport. Preserve row-level state and split work when a
  batch is unbounded.
- Prefer one paid operation per dataset cell. Put shaping, projection, `status`, `miss_reason`, display fields, and transformations in separate pure columns after the paid column.
- For recurring sourcing, use `.run({ key: 'domain', mode: 'net_new' })` on the candidate table. It atomically returns only previously unseen domains; ordinary `upsert` reruns return known rows too. This cannot suppress rows at a provider before that provider returns them.
- Return datasets for CSV/exportable outputs.
- Use declared getters. Do not parse raw payload paths when `extractedValues.*.get()` or `extractedLists.*.get()` exists.
- For query tools such as `query_customer_db` and `snowflake_run_query`, use `result.extractedLists.rows.get()` and return that Dataset Handle for full-row export. Do not build exports from a raw response preview in newly authored Plays.
- Dataset Handles are async-only, regardless of whether rows are already in memory. Use `await rows.count()`, `await rows.first()`, `await rows.at(index)`, `await rows.peek(limit)`, `await rows.materialize(limit)`, or `for await...of`. Do not use `.length`, numeric indexing, spread, or synchronous `for...of`.
- Project to flat user-facing columns with `status`, `miss_reason`, evidence/source, and requested output fields.

### Cron input is explicit and revision-pinned

A cron trigger receives `{}` unless its binding declares `input`. Put every
scheduled argument in the static JSON object below; do not rely on a handler
default for a side effect such as `apply`. The object is pinned with the
published revision, so retries retain the event revision's arguments after a
later republish.

```json
{
  "cron": {
    "schedule": "0 8 * * 1-5",
    "timezone": "America/New_York",
    "input": { "apply": true, "batchSize": 100 }
  }
}
```

`input` must be an inline JSON object—no variables, spreads, or functions.

The most common cell: a tool call. Column resolvers are positional
`(row, rowCtx)`; call `rowCtx.tools.execute({ id, tool, input, description })`
(all four required; `id` is the durable receipt key) and read the envelope —
`result.status` or declared getters. For a newly admitted raw-v2 Play, read
`result.toolResponse.rawV2` only when the full scrubbed provider response is
genuinely required and no declared getter represents the needed field. A stored
legacy artifact can expose only `toolResponse.raw`; keep that access until its
response contract is deliberately migrated:

```ts
/** @mermaid probe-accounts
 * flowchart TD
 * accounts[("Account rows")] --> loop
 * subgraph loop["For each account"]
 *   probe["Probe the domain"] --> flag["Flag success"]
 * end
 * loop --> out["Return the probed accounts"]
 */
import { definePlay } from 'deepline';

export default definePlay(
  'probe-accounts',
  async (ctx, input: { rows: Array<{ domain: string }> }) => {
    // @mermaid-node accounts type:"dataset" out:"accounts"
    const accounts = await ctx
      .dataset('accounts', input.rows)
      // @mermaid-node probe out:"probe_status"
      .withColumn('probe_status', async (row, rowCtx) => {
        const result = await rowCtx.tools.execute({
          id: 'probe',
          tool: 'test_rate_limit',
          input: { key: row.domain },
          description: 'Probe the account domain.',
        });
        return result.status;
      })
      // @mermaid-node flag out:"probed"
      .withColumn('probed', (row) => row.probe_status === 'completed')
      .run({ key: 'domain' });

    // @mermaid-node out out:"$output"
    return { accounts };
  },
  { description: 'Probe each account domain and flag success.' },
);
```

### External HTTP And Secrets

A play reaches a non-Deepline API with `ctx.fetch`, and authenticates it with
`ctx.secrets`. `await ctx.secrets.get("NAME")` resolves an allowed secret only
inside the executing Play. Treat it like a Vercel environment variable: do not
log or return it. Pass credentials through `ctx.secrets.bearer(...)` or
`ctx.secrets.header(...)` so the request requires HTTPS and its credential is
redacted from Deepline fetch receipts.

```ts
import { definePlay } from 'deepline';

export default definePlay(
  'campaign-name-sync',
  async (ctx) => {
    const apiKey = await ctx.secrets.get('INSTANTLY_API_KEY');
    const res = await ctx.fetch(
      'list-campaigns',
      'https://api.instantly.ai/api/v2/campaigns',
      { auth: ctx.secrets.bearer(apiKey) },
    );
    if (!res.ok) {
      throw new Error(`Instantly returned ${res.status}: ${res.bodyText}`);
    }
    const body = res.json as { items?: Array<{ name: string }> } | null;
    return { names: (body?.items ?? []).map((item) => item.name) };
  },
  {
    description: 'Read campaign names from Instantly with a workspace secret.',
  },
);
```

**Durable call-site keys must be static string literals.** The `ctx.fetch` key,
the `ctx.dataset` key, and the `ctx.step` id name durable call sites, so check,
publish, and replay have to agree on them before the body runs. A computed key
fails check with `ctx.fetch key must be a non-empty static string. The value
could not be resolved statically.` When a top-level `ctx.step` result depends on
input or query values, retain a static step id and pass the stable semantic
identity separately, for example
`ctx.step('generated-at', async () => Date.now(), { semanticKey: input.id })`.
The callback must remain an inline arrow or function expression. Row-scoped
steps already include dataset row identity; add a semantic key only when it
further identifies the work.

Plan around it before you write the play, because it decides the shape:

- A play **cannot page a large table**. `for (const p of pages) ctx.fetch(key(p), ...)`
  does not compile, and unrolling 149 literal keys is not a design.
- Instead **push the aggregation server-side and call it once** — a SQL
  function, a view, or a provider endpoint that returns the whole result. This
  is usually the better architecture anyway: one durable call, one receipt.
- To fan out over rows, use `ctx.dataset` with a static key. Per-row receipt
  identity comes from the row, not from the key — that is the supported way to
  do N-of-something.

Three more things that cost people iterations:

- `res.json` is a **property**, not a method. The body is read once at request
  time so the call can be checkpointed and replayed, so `await res.json()` is a
  type error. It is `null` both when the body is empty and when it is not valid
  JSON, so check `res.ok` and fall back to `res.bodyText`.
- `init.auth` accepts one credentialed header or an array of headers. Each array
  entry must target a distinct header.
- Manage stored values with `deepline secrets set` / `deepline secrets list`.
  Names are uppercased. Declare them in the Play's top-level `secrets` option when the play needs
  them present at publish time.

### The `@mermaid` block is the play's UI

The block is what the dashboard draws for this play. "Change how the play
looks" = edit the block, `deepline plays check`, republish.

Rules, using the example above:

1. **One block per export.** Forked prebuilts carry two: `/** @mermaid scalar
*/` and `/** @mermaid batch */`. Every line is a node, edge, `subgraph`, or
   `class` — prose lines are errors. A `subgraph` wired to its dataset renders
   as the loop. ~12 boxes max, labels under 48 chars, no counts in labels.
2. **Shapes are cosmetic except two.** `{…}` = decision; `[[…]]` claims a
   `ctx.runPlay` (error otherwise). Datasets come from `type:"dataset"` on
   the annotation — required for every dataset you `.run()`.
3. **Bind with `// @mermaid-node <id> out:"<identifier>"`** above the
   statement. `out:` is code: the assigned const (`out:"result"`), the column
   name inside a loop, `out:"$output"` on returns. Words go in the box label,
   never in `out:` (`out:"raw companies"` is rejected). Also available:
   `in:"row.domain"`, `label:"…"`.
4. **A box no statement runs**: `class a,b sketch` (or `type:"conceptual"`).
   Never sketch a subgraph id. Undrawn computed columns go in
   `.run({ undrawnColumns: [...] })`.
5. **Decisions**: unique label on every branch edge (`ok -->|found| next` —
   unlabeled is an error), max 3 branches, `arm:"run"` on the `runIf` run
   side.
6. **`plays check` reviews all this — for docflow-gated accounts.** Ungated,
   the block isn't validated yet: author it to these rules anyway; they're
   exactly what check enforces.

### Provider fallthrough

New Plays receive typed tool failures. Catch only `ProviderTransientError` when
another read provider can answer the same question. Let validation,
authentication, billing, Deepline, and unknown failures stop the Play. Keep the
last provider call outside the catch so an exhausted waterfall fails loudly.

```
try {
  return await primary();
} catch (error) {
  if (!(error instanceof ProviderTransientError)) throw error;
}
return fallback();
```

Do not branch on error messages or catch `ToolExecutionError` as a generic
fallthrough signal. The generated SDK reference documents every stable field,
the `retryable` distinction, and the explicit legacy-contract option.

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
