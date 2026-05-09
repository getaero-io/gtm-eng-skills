# Play anatomy

How to write a custom `*.play.ts` file that runs durably and survives replay. Read this when authoring or debugging custom plays. If your work is one-shot CLI invocation of a prebuilt play, this doc is not needed.

## File layout

A play is a default-exported call to `definePlay` in a TypeScript file named `*.play.ts`.

```typescript
import { definePlay } from 'deepline';

type Lead = {
  first_name: string;
  last_name: string;
  domain: string;
};

export default definePlay(
  'lead-email-lookup',
  async (ctx, input: { leads: Lead[] }) => {
    return ctx
      .map('leads', input.leads, { key: 'domain' })
      .step('email', (lead, ctx) =>
        ctx.runPlay(
          'email_waterfall',
          'prebuilt/name-and-domain-to-email-waterfall',
          {
            first_name: lead.first_name,
            last_name: lead.last_name,
            domain: lead.domain,
          },
          {
            description: 'Resolve email from name and company domain.',
          },
        ),
      )
      .run({ description: 'Resolve lead emails.' });
  },
);
```

Three parts:

1. **The play name** (`'lead-email-lookup'`) — the slug used when calling the play by name (`ctx.runPlay('lead-email-lookup', ...)`, `deepline plays run lead-email-lookup ...`). It must be unique across plays you have set live; the runtime rejects duplicates.
2. **The handler** — an `async` function that receives the runtime context (`ctx`) and the typed input. The handler's return value is the play's output.
3. **Optional input typing** — annotate the input shape inline (`input: { leads: Lead[] }`) rather than relying on `any`. The CLI uses this to validate `--input` JSON and `--csv` shape.

The exported value is also callable client-side (`Deepline.connect()` plus `ctx.play(name).run(...)`), but for most agent work the file-backed CLI flow is the right path.

## The play body re-executes — design for that

Plays run on a durable execution engine (Temporal). When a worker restarts, when a step is retried, when a workflow is replayed for any reason, **the play body runs again** from the beginning. The runtime guarantees that any step routed through `ctx.*` returns the same result on replay (it cached the first execution); anything _not_ routed through `ctx.*` will run again with fresh values, and the workflow desyncs.

This is what "replay-safety" means in practice. Concretely:

| Don't do this in a play body                       | Why it breaks                               | Use this instead                                                                                                                |
| -------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `Date.now()`, `new Date()` (for current time)      | Different value on replay                   | The runtime exposes time deterministically — record it once at handler entry if needed, or use a tool that returns a timestamp. |
| `Math.random()`, `crypto.randomUUID()`             | Non-deterministic                           | Capture once at handler entry and reuse, or use `ctx.step(id, () => crypto.randomUUID())` to memoize.                           |
| `process.env.X` (reading config that might change) | Worker restarts may load different env      | Pass environmental config in via `input`, or read it inside `ctx.step`.                                                         |
| `fs.readFile`, `fs.writeFile`                      | Not durable across replays; corrupts replay | `ctx.csv(path)` for inputs; persist outputs through tools that do the writing.                                                  |
| `fetch(url)` (raw network)                         | Fresh response on replay                    | `ctx.fetch(url, init)` — same shape as `fetch`, but the runtime caches the response.                                            |
| Calling another play with `await import(...)`      | Bypasses workflow boundaries                | `ctx.runPlay(name, input)`.                                                                                                     |
| Top-level side effects at module load              | Module re-evaluates per replay              | Move into the handler.                                                                                                          |

`ctx.step(id, fn)` is the escape hatch for arbitrary deterministic-on-replay operations — give the step a stable ID and the runtime caches `fn`'s result on first execution.

## The `ctx.*` API

This is the durable surface. Every effect a play needs goes through one of these. Always confirm the live signature with `deepline plays describe <play-name> --json` (read a prebuilt play's source) or by checking the SDK types — names below are stable but options evolve.

### `ctx.tools.execute({

id: key,
tool: toolId,
input: input,
...(options),
})` — call one provider tool

```typescript
const company = await ctx.tools.execute({
  id: 'company_search',
  tool: 'test_company_search',
  input: {
    domain: 'stripe.com',
  },
  description: 'Look up company details by domain.',
});
```

Pass a single request object. `id` is the stable idempotency key for this step, `tool` is the tool ID, `input` is the payload, and `description` is required. Returns the tool's output. The shape is provider-specific; confirm with `deepline tools describe <id> --json` before consuming fields. For tools that return wrapped results (`{ result: ..., matched_result: ... }`), drill into `result` to get the raw provider payload.

Inside plays, `ctx.tools.execute({ id, tool, input })` normalizes common execution wrappers before returning. A CLI tool call may show `{ result: { data: { status: "valid" } } }`, while the same call inside a play commonly returns `{ status: "valid" }`. When extracting provider fields in a play, prefer the normalized field first and keep wrapper fallbacks if you are unsure:

```typescript
const verification = await ctx.tools.execute({
  id: 'verify_email',
  tool: 'dropleads_email_verifier',
  input: { email },
  description: 'Validate the recovered email address.',
});
const data = verification as any;
const status =
  data?.status ?? data?.data?.status ?? data?.result?.data?.status ?? null;
```

### `ctx.runPlay(key, playRef, input, options)` — invoke another play

```typescript
const email = await ctx.runPlay(
  'email_waterfall',
  'prebuilt/name-and-domain-to-email-waterfall',
  {
    first_name: 'Ada',
    last_name: 'Lovelace',
    domain: 'example.com',
  },
  {
    description: 'Resolve email from name and company domain.',
  },
);
```

Use this to compose prebuilt plays inside a custom play. The first argument is a stable idempotency key for this child play call, and `description` is required. The play must be set live (or referenced by file path during local dev). Do not use `ctx.tools.execute({ id, tool, input })` to invoke a play — the IDs are namespaced separately and tool-shaped invocation will fail.

### `ctx.map(key, items, options).step(...).run(...)` — fan out across rows

```typescript
const enriched = await ctx
  .map('leads', input.leads, { key: 'domain' })
  .step('email', (lead, ctx) =>
    ctx.runPlay(
      'email_waterfall',
      'prebuilt/name-and-domain-to-email-waterfall',
      {
        /* ... */
      },
      {
        description: 'Resolve email from name and company domain.',
      },
    ),
  )
  .step('company', (lead, ctx) =>
    ctx.tools.execute({
      id: 'company_search',
      tool: 'test_company_search',
      input: { domain: lead.domain },
      description: 'Look up company details by domain.',
    }),
  )
  .run({ description: 'Enrich leads by domain.' });
```

Three map arguments:

1. **map key** — a string identifying the logical table/stage. Each `ctx.map` in one play needs a unique key; reuse fails registration. Conventional values: `'leads'`, `'companies'`, or a stage label when you have multiple passes.
2. **`items`** — an array, iterable, async iterable, or `PlayDataset` (e.g. from `ctx.csv`).
3. **`options.key`** — the stable per-row identity. Use a field name (`{ key: 'email' }`), a composite field list (`{ key: ['first_name', 'last_name', 'domain'] }`), or a function. This belongs on `ctx.map(...)`, not `.run(...)`.

Each `.step(name, resolver)` adds one output field to each row. Passing a nested `steps()` program creates visible child step columns such as `email.prospeo` and `email.hunter`; `.return(...)` on the nested program controls the parent field value.

Returns a `PlayDataset` of the original rows merged with the new columns. Pass it to another `ctx.map` for a second stage; do not cast it or read `.length`.

`staleAfterSeconds` also belongs on `ctx.map(...)` because it intentionally partitions the durable row identity on a relative time window. `description` belongs on `.run(...)`:

```typescript
return ctx
  .map('company_search', rows, {
    key: 'domain',
    staleAfterSeconds: 86400,
  })
  .step('contacts', (row, ctx) =>
    ctx.tools.execute({
      id: 'people_search',
      tool: 'apollo_search_people_with_match',
      input: { domain: row.domain },
      description: 'Search people at the company by domain.',
    }),
  )
  .run({ description: 'daily company contact search' });
```

Use `staleAfterSeconds` for scheduled refresh windows. Replays inside the same window still hit cache; a later window starts a fresh sheet partition for the same logical map.

A field in the same `ctx.map` cannot depend on another field produced by `ctx.runPlay` in the same stage — composition materializes between stages. Two-stage when you need to validate, classify, or otherwise condition the second column on the first.

### `ctx.waterfall(tool, input, opts?)` — try providers in order

```typescript
const email = await ctx.waterfall(
  'person_to_email',
  {
    first_name: 'Ada',
    last_name: 'Lovelace',
    domain: 'example.com',
  },
  { providers: ['hunter', 'prospeo', 'icypeas'] },
);
```

Tries each provider sequentially and returns the first hit (or `null` if all miss). Use this when you need explicit provider-order control and no prebuilt play covers the pattern. There is also an inline-spec form for arbitrary tool sequences — see the SDK source for the spec shape.

### `ctx.csv(path)` — load a staged CSV as a dataset

```typescript
const rows = await ctx.csv(input.file);
```

`path` is required — `ctx.csv()` with no argument is invalid. The argument is either a path injected by `--csv` (passed to the play as `input.file`), or a relative path to a file that lives next to the play.

Returns a `PlayDataset`, not a plain array. Pass it directly to another `ctx.map` as the second argument; do not iterate manually. The dataset supports `for await`, `peek()`, `count()`, and explicit `materialize()` for small sets, but the common path is `ctx.map("key", rows, ...)`.

### `ctx.fetch(key, url, init)` — durable HTTP

```typescript
const response = await ctx.fetch(
  'company_lookup_request',
  'https://api.example.com/lookup?q=acme',
  {
    description: 'Fetch company lookup data from the external API.',
  },
);
const data = response.json;
```

Same shape as the global `fetch`, with the response cached by the runtime so replay sees the same body. The first argument is a stable idempotency key and `description` is required in the options object. Use this when you need a one-off HTTP call inside a play that no tool covers. For provider work, prefer `ctx.tool` — tools handle auth, retries, rate limiting, and cost accounting.

The return shape is `{ ok, status, statusText, url, headers, bodyText, json }`; the runtime parses JSON when content-type indicates it, otherwise `json` is `null`.

### `ctx.step(id, fn)` — run a deterministic step

```typescript
const requestId = await ctx.step('request-id', () => crypto.randomUUID());
```

Use this to memoize the result of any non-deterministic operation that does not have a dedicated `ctx.*` method. The first execution runs `fn`; replays return the cached result. The `id` must be unique within the play body and stable across runs (do not use `Math.random()` or a timestamp as the id).

### `ctx.log(message)` — progress visible in `tail`

```typescript
ctx.log(`Looking up ${input.domain}`);
```

Visible in `deepline plays tail <play-name> --json` and in run history. Use it generously for long-running plays — it is the main agent-readable signal of progress.

### `ctx.sleep(ms)` — durable pause

```typescript
await ctx.sleep(60_000);
```

Uses a durable timer; safe across worker restarts. Use for retry backoff or scheduled coordination, not for "wait for a tool to finish" — tools handle their own waiting.

### `ctx.input` — the raw input object

Read-only access to the input passed when the play was started. Useful when the input shape is dynamic and a typed parameter is awkward.

## Bindings: cron and webhook

A third argument to `definePlay` declares optional triggers.

```typescript
export default definePlay(
  'daily-sync',
  async (ctx) => {
    const data = await ctx.tools.execute({
      id: 'crm_export',
      tool: 'crm_export',
      input: {},
      description: 'Export CRM records for the daily sync.',
    });
    return data;
  },
  {
    cron: { schedule: '0 9 * * *', timezone: 'America/New_York' },
  },
);
```

```typescript
export default definePlay('webhook-handler', handler, {
  webhook: {
    hmac: {
      algorithm: 'sha256',
      header: 'X-Hub-Signature-256',
      secretEnv: 'WEBHOOK_SECRET',
    },
  },
});
```

Bindings activate when the play is set live. `secretEnv` references an environment variable name resolved by the runtime — the secret value never enters the play body.

## Programmatic SDK (`Deepline.connect`)

When you want to call Deepline tools or plays from your own Node code (a Next.js route handler, a script, a long-running worker) without writing a `*.play.ts` and without shelling out to the CLI, use `Deepline.connect()`.

```typescript
import { Deepline } from 'deepline';

const ctx = await Deepline.connect();

// Call a tool directly
const company = await ctx.tools.execute({
  tool: 'test_company_search',
  input: { domain: 'stripe.com' },
});

// Run a registered play and wait for the output
const job = await ctx.play('prebuilt/person-linkedin-to-email-waterfall').run({
  linkedin_url: 'https://www.linkedin.com/in/example',
  first_name: 'Ada',
  last_name: 'Lovelace',
  domain: 'example.com',
});
const result = await job.get();

// Or list/inspect tools
const tools = await ctx.tools.list();
const meta = await ctx.tools.get('apollo_people_search');
```

`Deepline.connect()` resolves auth from explicit options first, then environment variables (`DEEPLINE_API_KEY`, `DEEPLINE_API_BASE_URL`), then the CLI auth file written by `deepline auth register`. For CI or container environments, prefer environment variables; for local dev, the CLI auth file is the simplest path.

```typescript
// Explicit options when env / CLI auth are not appropriate
const ctx = await Deepline.connect({
  apiKey: process.env.MY_DEEPLINE_KEY,
  baseUrl: 'https://code.deepline.com',
});
```

This client surface is **not** the same as the runtime context inside a play body. `Deepline.connect()` is for app code that calls Deepline from the outside; the `ctx` inside `definePlay(name, async (ctx, input) => { ... })` is the durable runtime that handles replay-safety, idempotency, and `ctx.map` row fan-out. Do not use `Deepline.connect()` inside a play body.

When choosing between programmatic SDK and a custom play: the programmatic SDK is right when the orchestration logic lives in your app (a request handler that needs one tool call's result before responding), and a custom play is right when the orchestration is itself the unit of work (a multi-stage row workflow you'd want to durably retry, schedule via cron, or trigger by webhook).

## Idempotency

Plays are idempotent by row + map key. A `ctx.map('domain', rows, ...)` over a row with `domain: 'acme.com'` is identified by `('lead-email-lookup', 'domain', 'acme.com')` (play name + map key + row key). If the play re-runs on the same row, the runtime returns the cached row output instead of re-executing the column callbacks.

Practical implications:

- Re-running a play over the same CSV does not double-bill providers or duplicate rows. The runtime skips already-computed rows.
- To force re-computation, change the map key string, change the play name (via `set-live`), or clear history (`deepline plays clear-history <play-name>`).
- Each `ctx.map` key must be unique within the play — see the rule in `jobs/enriching-and-researching.md`.

## Error handling

Tool calls and `ctx.runPlay` invocations throw on hard failure (bad input, provider 5xx, exhausted retries). Soft misses (provider returns no data) typically return `null` from `ctx.waterfall` and provider-specific shapes from `ctx.tool` — read the tool's described output to know which.

Inside a `ctx.map` callback, throwing fails the row but does not fail the play; the row's column value is recorded as the error and the rest of the rows continue. To make a row's failure fatal, throw outside `ctx.map`.

```typescript
return ctx
  .map('leads', rows, { key: 'domain' })
  .step('email', async (row, ctx) => {
    try {
      return await ctx.runPlay(
        'email_waterfall',
        'prebuilt/name-and-domain-to-email-waterfall',
        {
          /* ... */
        },
        {
          description: 'Resolve email from name and company domain.',
        },
      );
    } catch (err) {
      ctx.log(
        `email lookup failed for ${row.domain}: ${(err as Error).message}`,
      );
      return null;
    }
  })
  .run({ description: 'Resolve lead emails.' });
```

Use the catch-and-log pattern when you want a row-level failure to produce a null column instead of marking the row failed. Use the bare throw when you want failures to surface in run status.

## Common authoring traps

- **Reading `input.file` without calling `ctx.csv`.** When `--csv` is passed, `input.file` is a staged reference, not a file path you can `fs.readFile`. Always go through `ctx.csv(input.file)`.
- **Iterating a dataset manually.** `for (const row of dataset) { ... }` does not work — datasets are async-iterable handles, not arrays. Use `ctx.map`.
- **Reusing a map key.** Two `ctx.map` calls with the same key fail registration. Pick distinct names per stage.
- **Calling a play via `ctx.tool`.** Plays and tools live in separate ID spaces. Use `ctx.runPlay(name, input)` for plays, `ctx.tools.execute({
  tool: id,
  input: input,
})` for tools.
- **Top-level side effects** (writing files, opening connections at import time). The module re-evaluates on every replay; side effects re-run.
- **Mutating `ctx.input`.** Treat it as read-only. Mutations do not survive replay and the runtime may freeze it in future versions.
