# SDK Reference

## Runtime Model

The Deepline SDK is a runtime SDK. Your TypeScript defines durable play code and typed run contracts; Deepline executes that code in the cloud runtime, records provider/tool calls, persists dataset rows, and exposes run state through SDK handles and HTTP APIs.

Use `definePlay(...)` for code that runs inside a Deepline play. Inside that function, `ctx.*` is the runtime boundary: `ctx.tools.execute` calls managed providers, `ctx.dataset` records row-level work, `ctx.step` checkpoints scalar work, `ctx.fetch` records external HTTP, and `ctx.runPlay` composes registered or prebuilt plays.

Use `Deepline.connect()` and `DeeplineClient` from regular Node/TypeScript services, scripts, schedulers, or tests. Those APIs discover tools and plays, start runs, stream/poll status, stop runs, and inspect durable output without requiring a local play file.

## Reference Map

| Area | Primary surface | Use when |
|---|---|---|
| Runtime entrypoint | `Deepline.connect()` / `DeeplineContext` | A script or service needs to call tools, run plays, or inspect runs. |
| Play authoring | `definePlay(...)` / `ctx.*` | Code should run durably inside Deepline with persisted steps, datasets, tools, and child plays. |
| Tool/provider calls | `ctx.tools.execute(...)`, `deepline.tools.execute(...)`, `client.executeTool(...)` | You need provider-backed enrichment/search with Deepline auth, billing, extraction metadata, and retries. |
| Remote plays/runs | `ctx.play(name)`, `ctx.runPlay(...)`, `PlayJob`, `client.runs` | You need to run, poll, stream, stop, export, publish, or inspect plays. |
| Raw HTTP | `references/plays-api-reference.md` | A backend, notebook, scheduler, or non-TypeScript caller invokes Deepline over REST. |

## Detail Policy

| Material | Rendered as |
|---|---|
| Tested examples | Full runnable code blocks. |
| Classes | One member table with purpose, parameters, and returns. |
| Interfaces and object types | Field tables; no duplicate declaration dump. |
| Fieldless aliases or overloads | Compact signature line plus parameter/return tables. |
| Full HTTP routes | Generated in `references/plays-api-reference.md`. |

## Tested Examples

These examples are copied from `docs-examples/sdk-v2` and validated by `bun run docs:sdk-v2:check`. Keep examples there first, then regenerate this reference.

### Run A Prebuilt From TypeScript

Source: `docs-examples/sdk-v2/run-prebuilt.ts`

```ts
import { Deepline } from 'deepline';

const ctx = await Deepline.connect();

const job = await ctx.play('prebuilt/person-linkedin-to-email').run({
  linkedin_url: 'https://www.linkedin.com/in/example-person/',
});

const result = await job.get();
console.log(JSON.stringify(result, null, 2));
```

### Define A Play With `ctx.tools.execute`

Source: `docs-examples/sdk-v2/company-lookup.play.ts`

```ts
import { definePlay } from 'deepline';

type Input = {
  domain: string;
};

type Output = {
  domain: string;
  lookupStatus: string;
};

export default definePlay(
  'docs-company-lookup',
  async (ctx, input: Input): Promise<Output> => {
    const result = await ctx.tools.execute({
      id: 'company_lookup',
      tool: 'test_rate_limit',
      input: {
        key: input.domain,
      },
      description:
        'Check that the company lookup path can run for this domain.',
    });

    return {
      domain: input.domain,
      lookupStatus: result.status,
    };
  },
);
```

### Schedule A Dataset Refresh

Source: `docs-examples/sdk-v2/nightly-account-refresh.play.ts`

```ts
import { definePlay } from 'deepline';

type Account = {
  domain: string;
  owner: string;
};

export default definePlay(
  'docs-nightly-account-refresh',
  async (ctx, input: { accounts: Account[] }) => {
    const rows = await ctx
      .dataset('account_refresh', input.accounts)
      .withColumn(
        'company_signal',
        (account, rowCtx) =>
          rowCtx.tools.execute({
            id: 'company_signal',
            tool: 'test_rate_limit',
            input: {
              key: account.domain,
            },
            description: 'Refresh one account signal for the owner.',
            staleAfterSeconds: 86_400,
          }),
      )
      .run({
        key: 'domain',
        description: 'Refresh target account signals once per day.',
      });

    return { rows };
  },
  {
    cron: {
      schedule: '0 9 * * *',
      timezone: 'America/New_York',
    },
    billing: {
      maxCreditsPerRun: 25,
    },
  },
);
```

### Verify A Webhook With HMAC

Source: `docs-examples/sdk-v2/inbound-lead-webhook.play.ts`

```ts
import { definePlay } from 'deepline';

type InboundLead = {
  email: string;
  company_domain?: string;
  source?: string;
};

export default definePlay(
  'docs-inbound-lead-webhook',
  async (ctx, input: InboundLead) => {
    const domain = input.company_domain ?? input.email.split('@')[1] ?? '';
    const company = await ctx.tools.execute({
      id: 'company_context',
      tool: 'test_rate_limit',
      input: {
        key: domain,
      },
      description: 'Add company context before routing the inbound lead.',
    });

    return {
      email: input.email,
      domain,
      source: input.source ?? 'webhook',
      company_status: company.status,
    };
  },
  {
    webhook: {
      hmac: {
        secretEnv: 'HUBSPOT_WEBHOOK_SECRET',
        header: 'x-hubspot-signature-v3',
        algorithm: 'sha256',
      },
    },
  },
);
```

Generated from source comments and type declarations by `scripts/generate-play-sdk-reference.ts`. Do not edit this file manually.

## Version And Coverage

| Field | Value |
|---|---|
| SDK version | `0.1.253` |
| API contract | `2026-07-native-monitor-launch-hard-cutover` |
| Checked-in SDK fallback | `0.1.253` |
| Minimum supported SDK | `0.1.53` |
| Deprecated below | `0.1.219` |
| Generated sources | `sdk/src/client.ts`<br />`sdk/src/play.ts`<br />`shared_libs/play-runtime/cell-staleness.ts`<br />`shared_libs/play-runtime/tool-result-types.ts`<br />`shared_libs/plays/dataset.ts` |
| Coverage | Runtime SDK surface: `Deepline.connect`, `DeeplineContext`, `DeeplineClient`, play authoring, in-play `ctx.*` primitives, provider/tool calls, named play handles, run handles, datasets, and tool result accessors. |
| Not covered | Full CLI command help, provider-specific input/output schemas, dashboard-only routes, and marketing/tutorial guides. Use `references/plays-api-reference.md` for generated HTTP route contracts. |

## Runtime Entrypoints

### `Deepline`

Static entry point for the Deepline SDK.

Signature: `class Deepline`

#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `connect` | method | Create a connected SDK context.<br /><br />Resolves configuration from options, environment variables, and CLI config<br />files. See `resolveConfig` for the resolution order. | `options?: DeeplineClientOptions` - Optional overrides for API key, base URL, etc. | `Promise<DeeplineContext>` |

### `DeeplineContext`

High-level SDK context with tool shortcuts and play handles.

Created by `Deepline.connect`. Wraps a `DeeplineClient` with
a friendlier API for common operations.

Signature: `class DeeplineContext`

#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Create a high-level SDK context.<br /><br />Most callers should use `Deepline.connect`; direct construction is<br />equivalent when you already have explicit client options. | `options?: DeeplineClientOptions` - Optional SDK client configuration. |  |
| `tools` | getter | Tool operations namespace. |  | `DeeplineToolsNamespace` |
| `plays` | getter | Play discovery and named-play handles.<br /><br />Use `plays.list()` for discovery and `plays.get(name)` when you prefer a<br />namespace spelling over `ctx.play(name)`. |  | `DeeplinePlaysNamespace` |
| `prebuilt` | getter | Convenience references for Deepline-managed prebuilt plays.<br /><br />Known prebuilts are exposed by camel-cased aliases. Any other property is<br />converted into `prebuilt/<property>` so callers can pass the reference to<br />`ctx.runPlay(...)`. |  | `Record<string, PrebuiltPlayRef>` |
| `play` | method | Get a named play handle for remote lifecycle operations. | `name: string` - Play name (as registered on the server) | `DeeplineNamedPlay<TInput, TOutput>` |
| `runPlay` | method | Run a named or prebuilt play and wait for its output.<br /><br />This is the high-level SDK equivalent of `ctx.play(name).runSync(input)`.<br />Inside a play runtime, prefer the in-play `ctx.runPlay(key, playRef, input,<br />options)` form so the child run is checkpointed under a stable key. | `playOrRef: string \| PlayReferenceLike` - Play name or prebuilt/reference object.<br />`input: TInput` - JSON input passed to the play. | `Promise<TOutput>` |

## Play Authoring And In-Play Runtime

### `definePlay`

Define a play — a composable TypeScript workflow for the Deepline platform.

The returned value is both:
1. **A callable function** — invoked by the Temporal worker with a runtime context
2. **A named play handle** — with `.run()`, `.versions()`, `.get()`, `.publish()`, etc. for remote lifecycle management

Plays are the primary abstraction for building repeatable data pipelines.
They run on Temporal for durable execution with automatic retries and timeouts.

Signature: `export function definePlay<TInput, TOutput extends PlayReturnObject>( config: DefinePlayConfig<TInput, TOutput>, ): DefinedPlay<TInput, TOutput>; export function definePlay<TInput, TOutput extends PlayReturnObject>( name: string, fn: (ctx: DeeplinePlayRuntimeContext, input: TInput) => Promise<TOutput>, bindings?: PlayBindings, ): DefinedPlay<TInput, TOutput>;`

#### Overload 1

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `config` | `DefinePlayConfig<TInput, TOutput>` | Yes | Object-form play config. |

#### Returns

`DefinedPlay<TInput, TOutput>`


#### Overload 2

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `string` | Yes | Play name. |
| `fn` | `(ctx: DeeplinePlayRuntimeContext, input: TInput) => Promise<TOutput>` | Yes | Play function. |
| `bindings` | `PlayBindings` | No | Trigger bindings. |

#### Returns

`DefinedPlay<TInput, TOutput>`


### `DefinePlayConfig`

Object-form play definition accepted by `definePlay(config)`.

Use this form when the input contract should be explicit at definition time
through `defineInput<T>(schema)`, or when configuration reads clearer as one
object. The shorthand `definePlay(name, fn, bindings?)` is equivalent for
simple file-backed plays.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Play id/name. |
| `description` | `string` | No | Human-readable one-line description of what this play does. |
| `input` | `PlayInputContract<TInput>` | Yes | Input schema. |
| `run` | `(ctx: DeeplinePlayRuntimeContext, input: TInput) => Promise<TOutput>` | Yes | Play function. |
| `bindings` | `PlayBindings` | No | Trigger bindings. |
| `billing` | `PlayBindings['billing']` | No | Billing options. |


### `PlayBindings`

Optional trigger bindings for a play.

A play can be triggered three ways, declared as the third argument to
[definePlay](/sdk-v2/sdk-reference#defineplay):
- `webhook` — an inbound HTTP call (with optional HMAC signature verification);
- `cron` — a schedule; or
- `sqlListeners` — a **monitor**: the play runs whenever a monitor writes a new
  row to its output stream. This is how you build a play "on top of" a monitor
  (e.g. run enrichment every time a watched company posts a new job). Each
  listener binds to a monitor tool id + one of its output stream keys (see
  `deepline monitors available <id>` for a tool's streams and row columns).
  The changed row is delivered to the handler as the listener event's `after`.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `description` | `string` | No | Human-readable one-line description of what this play does.<br /><br />New SDK-authored file workflows require this in `plays check`, `plays run<br />--file`, and `plays publish <file>`. The server API keeps it optional so<br />older clients can continue to register revisions during the migration. |
| `inline` | `boolean` | No | Allow compilers to bundle this named handler directly without a child run. |
| `billing` | `{ maxCreditsPerRun?: number; }` | No | Optional per-run billing controls enforced by the runtime. |
| `webhook` | `{ hmac?: { algorithm?: 'sha256'; header?: string; secretEnv: string; }; }` | No | Webhook trigger with optional HMAC signature verification. |
| `cron` | `{ schedule: string; timezone?: string; }` | No | Cron schedule trigger. |
| `sqlListeners` | `SqlListenerDeclaration[]` | No | Customer DB row-change listeners that wake this play when published. |
| `secrets` | `readonly string[]` | No | Customer-authored play secrets this play is allowed to use at runtime.<br />Values are never bundled or exposed by the SDK; access them with<br />`ctx.secrets.get("NAME")` and approved helpers such as<br />`ctx.secrets.bearer(handle)`. Secret-authenticated `ctx.fetch` calls<br />require an https:// URL so customer secrets never leave Deepline over<br />plaintext HTTP. |


### `ctx.csv(path, options)`

Load a staged CSV file as a durable dataset handle.

Use this when a play receives a CSV path from the CLI or API and row work
should continue through [DeeplinePlayRuntimeContext.dataset](/sdk-v2/sdk-reference#runtime-primitives). The path is
normally an input field such as `input.csv`, populated by
`deepline plays run my.play.ts --csv rows.csv`. Prefer `input.csv` for row
data so the CLI can run strict CSV preflight before starting a run.
Pass-through flags can also target non-reserved field names. If a play
intentionally calls `ctx.csv(input.file)`, use `--input
'{"file":"rows.csv"}'` because `--file` is reserved for the play source
path.

Each CSV row becomes an object keyed by canonical column names. Use
`options.columns` / `options.rename` to map user headers such as
`"Company Domain"` to stable code fields such as `domain`.

Signature: `csv<T = Record<string, unknown>>( path: string, options?: CsvOptions, ): Promise<PlayDataset<T>>;`

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `path` | `string` | Yes | Staged CSV path. |
| `options` | `CsvOptions` | No | CSV load options. |

#### Returns

`Promise<PlayDataset<T>>`


### `CsvOptions`

Options for loading a staged CSV with `ctx.csv(...)`.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `description` | `string` | No | Human-readable description for runtime logs and inspection. |
| `columns` | `CsvRenameMap` | No | Canonical field-to-header aliases, e.g. `{ domain: ['domain', 'Company Domain'] }`. |
| `rename` | `CsvRenameMap` | No | Header rename map; use `columns` for new code. |
| `required` | `readonly string[]` | No | Canonical fields that must be present after header normalization. |


### `ctx.dataset(key, items)`

Create a persisted row dataset/table from input rows.

`ctx.dataset` is Deepline's row-work primitive. It records row identity,
progress, retries, table output, and idempotency for a collection of rows.
Use `.withColumn(name, resolver)` on the returned builder to define output
columns, then `.run(...)` to execute the row program.

The `key` identifies the logical dataset/table. Renaming it is a persistence
migration: existing rows may no longer be reused. Row identity is derived
automatically from input row content unless `.run({ key: ... })` overrides
it with stable business fields such as `domain`, `email`, or `linkedin_url`.

By default, `ctx.dataset` is row-preserving: one input row produces one output
row, with original fields merged with the columns produced by
`.withColumn(...)`. If one input entity must become many output rows, use the
documented expand/flatten recipe instead of assuming `ctx.dataset` changes
row cardinality.

Signature: `dataset<TSource extends PlayDatasetInput<object>>( key: string, items: TSource, ): DatasetBuilder< PlayDatasetRow<TSource> & object, PlayDatasetRow<TSource> & object >;`

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `key` | `string` | Yes | Dataset/table name. |
| `items` | `TSource` | Yes | Input rows. |

#### Returns

`DatasetBuilder< PlayDatasetRow<TSource> & object, PlayDatasetRow<TSource> & object >`


### `.dataset(...).withColumn(name, resolver).run(options)`

Define one output column for every row in this dataset.

The `name` becomes a field on each output row. For example,
`.withColumn('contact', ...)` creates `row.contact` in later column resolvers; it does
not spread returned object fields such as `contact.email` into `row.email`.
Add a later column resolver when you want a top-level export field:
`.withColumn('email', row => row.contact?.email ?? null)`.

```ts
withColumn<Name extends string, Value>(
    name: Name,
    resolver: ColumnResolver<OutputRow, Value>,
  ): DatasetBuilder<InputRow, OutputRow & Record<Name, Value>>;

withColumn<Name extends string, Value>(
    name: Name,
    definition: DatasetColumnDefinition<OutputRow, Value> & {
      readonly runIf: (
        row: OutputRow,
        index: number,
      ) => boolean | Promise<boolean>;
    },
  ): DatasetBuilder<InputRow, OutputRow & Record<Name, Value | null>>;

withColumn<Name extends string, Value>(
    name: Name,
    definition: DatasetColumnDefinition<OutputRow, Value>,
  ): DatasetBuilder<InputRow, OutputRow & Record<Name, Value>>;

withColumn<Name extends string, Value>(
    name: Name,
    resolver:
      | StepResolver<OutputRow, Value>
      | StepProgramResolver<OutputRow, Value>,
    options: StepOptions<OutputRow, Value>,
  ): DatasetBuilder<InputRow, OutputRow & Record<Name, Value | null>>;

run(options?: {
    description?: string;
    mode?: 'upsert' | 'net_new';
    key?:
      | (keyof InputRow & string)
      | readonly (keyof InputRow & string)[]
      | ((
          row: InputRow,
          index: number,
        ) => string | number | readonly unknown[]);
  }): Promise<PlayDataset<OutputRow>>;
```

#### Column Overload 1 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes | Output column name. |
| `resolver` | `ColumnResolver<OutputRow, Value>` | Yes | Computes the value for one row. |

#### Column Overload 1 Returns

`DatasetBuilder<InputRow, OutputRow & Record<Name, Value>>`

#### Column Overload 2 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes | Output column name. |
| `definition` | `DatasetColumnDefinition<OutputRow, Value> & { readonly runIf: ( row: OutputRow, index: number, ) => boolean \| Promise<boolean>; }` | Yes | Object-column definition with required `runIf`. |

#### Column Overload 2 Returns

`DatasetBuilder<InputRow, OutputRow & Record<Name, Value | null>>`

#### Column Overload 3 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes | Output column name. |
| `definition` | `DatasetColumnDefinition<OutputRow, Value>` | Yes | Object-column definition. |

#### Column Overload 3 Returns

`DatasetBuilder<InputRow, OutputRow & Record<Name, Value>>`

#### Column Overload 4 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes | Output column name. |
| `resolver` | `\| StepResolver<OutputRow, Value> \| StepProgramResolver<OutputRow, Value>` | Yes | Computes the value for one row. |
| `options` | `StepOptions<OutputRow, Value>` | Yes | Row gate options. |

#### Column Overload 4 Returns

`DatasetBuilder<InputRow, OutputRow & Record<Name, Value | null>>`

#### Run Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `options` | `{ description?: string; mode?: 'upsert' \| 'net_new'; key?: \| (keyof InputRow & string) \| readonly (keyof InputRow & string)[] \| (( row: InputRow, index: number, ) => string \| number \| readonly unknown[]); }` | No | Run options. |

#### Run Returns

`Promise<PlayDataset<OutputRow>>`

Execute the row-column program and return a durable dataset handle.

The returned [PlayDataset](/sdk-v2/sdk-reference#playdataset) preserves one output row per input row,
with original fields merged with the columns produced by `.withColumn(...)`.

### `DatasetColumnRunInput`

Input object passed to an object-column `run` resolver.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `row` | `Row` | Yes | Current row, including previously computed columns. |
| `ctx` | `DeeplinePlayRuntimeContext` | Yes | Runtime context for tool/play/fetch/log calls. |
| `index` | `number` | Yes | Zero-based row index for this dataset run. |
| `previousCell` | `PreviousCell<Value>` | No | The prior stored value for this exact row+column when the runtime has<br />decided the cell is due to run again. `previousCell.value` is the same type<br />this column returns; metadata such as `completedAt` and `staleAt` lives<br />beside it and is not mixed into the value. |


### `DatasetColumnDefinition`

Object-column form for `.withColumn(...)`.

Use this when a column needs `runIf` or typed `previousCell`.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `run` | `(input: DatasetColumnRunInput<Row, Value>) => Value \| Promise<Value>` | Yes | Compute one cell value. Receives the previous stored value when rerunning. |
| `runIf` | `(row: Row, index: number) => boolean \| Promise<boolean>` | No | Optional row-level gate. Skipped rows produce `null` for this column. |


### `StepOptions`

Options for row-level `.withColumn(...)` and `steps().step(...)` entries.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `runIf` | `(row: Row, index: number) => boolean \| Promise<boolean>` | No | Optional row-level gate. Skipped rows produce `null` for this column. |
| `recompute` | `boolean` | No | Legacy dataset-column recompute flag accepted for older authored plays.<br /><br />Prefer putting freshness on the actual reusable call<br />(`ctx.tools.execute`, `ctx.step`, or `ctx.fetch`). |
| `recomputeOnError` | `boolean` | No | Legacy error-recompute flag accepted for older authored plays. |
| `staleAfterSeconds` | `number` | No | Legacy cell staleness metadata accepted for older authored plays. |


### `PreviousCell`

Previous durable cell value passed to object-column resolvers.

The runtime supplies this when a row+column is being recomputed after a
previous value existed. `value` has the same type that the column returns;
freshness metadata lives beside it.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `value` | `Value` | Yes | Previous completed value for this row+column. |
| `completedAt` | `number` | No | Millisecond timestamp when the previous value completed. |
| `staleAt` | `number \| null` | No | Millisecond timestamp when the previous value becomes stale; `null` means no expiry. |
| `staleAfterSeconds` | `number` | No | Resolved numeric TTL in seconds for the previous value, when present. |


### `ctx.step(id, fn)`

Create one scalar checkpoint for the whole play run.

Use `ctx.step` when a value is nondeterministic, expensive, external, or
useful to inspect as a named boundary. The first execution stores the
JSON-serializable output under `id`; replay and retries return the stored
value instead of running `run` again.

Plain deterministic assignment does not need `ctx.step`. Use
`ctx.dataset(...).withColumn(...)`, not `ctx.step`, when the value should become a
field on each exported row.

Signature: `step<T>( id: string, run: () => T | Promise<T>, options?: { staleAfterSeconds?: number }, ): Promise<T>;`

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Checkpoint id. |
| `run` | `() => T \| Promise<T>` | Yes | Computes the value once. |
| `options` | `{ staleAfterSeconds?: number }` | No | Checkpoint options. |

#### Returns

`Promise<T>`


### `ctx.runPlay(key, playRef, input, options)`

Invoke another registered or file-backed play as a child workflow.

Use this for real composition boundaries, especially when a fitting
scalar prebuilt play already encodes provider order, fallbacks,
normalization, and no-result behavior. Do not invoke plays through
`ctx.tools.execute`; tools and plays are separate namespaces.

`key` is the stable child-call identity for idempotency and traceability.

Signature: `runPlay<TOutput = unknown>( key: string, playRef: string | PlayReferenceLike, input: Record<string, unknown>, options?: PlayCallOptions, ): Promise<TOutput>;`

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `key` | `string` | Yes | Stable child-call key. |
| `playRef` | `string \| PlayReferenceLike` | Yes | Registered play name, play handle, or file-backed play reference. |
| `input` | `Record<string, unknown>` | Yes | Input object passed to the child play. |
| `options` | `PlayCallOptions` | No | Child play options. |

#### Returns

`Promise<TOutput>`


### `ctx.tools.execute(request)`

Execute a single tool with a keyword-style request object.

Signature: `execute<TOutput = LoosePlayObject>( request: ToolExecutionRequest, ): Promise<ToolExecuteResult<TOutput>>;`

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `request` | `ToolExecutionRequest` | Yes | Tool call request. |

#### Returns

`Promise<ToolExecuteResult<TOutput>>`


### `ToolExecutionRequest`

Keyword-style request object for `ctx.tools.execute(...)`.

The `tool` value comes from live tool discovery. The `id` is the stable
logical call name used for logs, metadata, and receipt attachment. Provider
call reuse is keyed by play, tool, semantic input, auth scope, provider action
version, and cache policy.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Stable logical id for logs, metadata, and receipt attachment. |
| `tool` | `string` | Yes | Current tool id from `deepline tools search` / `deepline tools describe`. |
| `input` | `Record<string, unknown>` | Yes | JSON-serializable provider/tool input object. |
| `description` | `string` | No | Human-readable description for logs and run inspection. |
| `force` | `boolean` | No | Recompute this tool call instead of reusing a durable receipt/checkpoint. |
| `staleAfterSeconds` | `number` | No | Numeric TTL in seconds for this tool checkpoint. |
| `timeoutMs` | `number` | No | Runtime transport timeout in milliseconds. This is not sent to the provider. |
| `receiptWaitMs` | `number` | No | Follower wait budget in milliseconds before a running receipt is reclaimable. |


### `ctx.fetch(key, url, init)`

Durable HTTP fetch.

Use this for non-provider HTTP calls that must replay safely. The response
is recorded under `key` so workflow replay sees the same value. Prefer
`ctx.tools.execute(...)` for Deepline-managed provider APIs because tools
handle auth, retries, rate limits, extraction metadata, and spend tracking.
If `init.auth` comes from `ctx.secrets`, `url` must be https://.

Signature: `fetch( key: string, url: string | URL, init?: SecretAwareRequestInit, options?: { staleAfterSeconds?: number }, ): Promise<{ ok: boolean; status: number; statusText: string; url: string; headers: Record<string, string>; bodyText: string; json: unknown | null; }>;`

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `key` | `string` | Yes | Checkpoint id. |
| `url` | `string \| URL` | Yes | URL to fetch. |
| `init` | `SecretAwareRequestInit` | No | Fetch options. |
| `options` | `{ staleAfterSeconds?: number }` | No |  |

#### Returns

`Promise<{ ok: boolean; status: number; statusText: string; url: string; headers: Record<string, string>; bodyText: string; json: unknown | null; }>`


### `ctx.runSteps(program, input, options)`

Run a reusable step program against one scalar input object.

`steps().step(...)` is a composable mini-pipeline. Use `ctx.runSteps(...)`
when that mini-pipeline should execute outside a row dataset. Inside a
`ctx.dataset` column resolver, pass the step program directly to
`.withColumn(name, program)` instead.

Signature: `runSteps<TInput extends Record<string, unknown>, TOutput>( program: RunnableStepProgram<TInput, TOutput>, input: TInput, options?: { description?: string }, ): Promise<TOutput>;`

#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `program` | `RunnableStepProgram<TInput, TOutput>` | Yes | Step program. |
| `input` | `TInput` | Yes | Program input. |
| `options` | `{ description?: string }` | No | Run options. |

#### Returns

`Promise<TOutput>`


### `PlayDataset`

Durable handle for rows produced by `ctx.csv(...)` or `ctx.dataset(...).run()`.

A `PlayDataset` is not a normal in-memory array. It points at runtime-managed
rows, usually backed by persisted sheet storage, and carries metadata such as
dataset kind, dataset id, table namespace, count, and preview rows.

Pass dataset handles directly into later `ctx.dataset(...)` stages by default so
Deepline keeps row progress, retries, memory use, and table output under
runtime control. Use `count()` and `peek()` for bounded inspection. Use
`materialize(limit)` or async iteration only when the dataset is intentionally
small and bounded. `PlayDataset` intentionally does not expose `.rows`,
`.toArray()`, or other array aliases; those hide the runtime cost of loading
persisted rows into memory.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `datasetKind` | `PlayDatasetKind` | Yes | Dataset kind. |
| `datasetId` | `string` | Yes | Dataset id. |
| `backing` | `PlayDatasetBacking` | No | Backing store info. |
| `sourceLabel` | `string \| null` | No | Display label. |
| `tableNamespace` | `string \| null` | No | Runtime table name. |


### `ToolExecuteResult`

Canonical result returned by Deepline tool execution.

The top-level object is Deepline-owned execution metadata and semantic
extraction state. Raw tool/provider data lives under `toolResponse.raw`;
response metadata lives under `toolResponse.meta`. Semantic single-value
getters live under `extractedValues.<name>.get()`, and list getters live
under `extractedLists.<name>.get()`.

Use extractors first when a tool contract exposes them. Use list getters for
row-shaped data. Drop to `toolResponse.raw` only for provider-specific scalar
fields or bounded debugging context; persisted rows may clip declared lists to
previews.

Signature: `export type ToolExecuteResult< TResult = unknown, TMeta = Record<string, unknown>, TExtracted extends Record<string, unknown> = Partial<DeeplineGetterValueMap>, TLists extends Record<string, Record<string, unknown>> = Record< string, Record<string, unknown> >, > = ToolExecuteResultBase<TResult, TMeta> & ToolExecuteResultAccessors<TExtracted, TLists>;`



## Tool And Provider Calls

### `DeeplineContext.tools`

Tool/provider operations available from a connected `DeeplineContext`.

This namespace is for regular SDK callers outside a play runtime. Inside a
`definePlay(...)` body, use `ctx.tools.execute({ id, tool, input, ... })`
so provider calls become durable runtime checkpoints.

Signature: `export type DeeplineToolsNamespace = { list(): Promise<ToolDefinition[]>; get(toolId: string): Promise<ToolMetadata>; execute( toolId: string, input: Record<string, unknown>, ): Promise<ToolExecuteResult>; };`



## Remote Plays And Runs

### `DeeplineContext.plays`

Named-play discovery and handle operations from a connected `DeeplineContext`.

Signature: `export type DeeplinePlaysNamespace = { list(): Promise<PlayListItem[]>; get<TInput = Record<string, unknown>, TOutput = unknown>( name: string, ): DeeplineNamedPlay<TInput, TOutput>; };`



### `DeeplineNamedPlay`

Handle to a named play for remote lifecycle operations.

Returned by `DeeplineContext.play` and attached to `DefinedPlay`.
Provides methods to run, inspect, list runs, and publish a play by name.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `string` | Yes | The play's name. |


### `PlayJob`

Handle to a running play execution.

Provides methods to check status, stream logs, wait for completion,
or cancel the execution.

This handle is the SDK-context equivalent of `deepline plays run --watch` and
`POST /api/v2/plays/run`: every surface returns a run id first, then exposes
the completed user output through `PlayJob.get()` or the status endpoint's
`result` field. Runtime logs are available from `status().progress.logs` and
are intentionally separate from the returned output object.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes | Temporal workflow ID for this execution. |


## Low-Level Client

### `DeeplineClient`

Low-level client for the Deepline REST API.

Provides typed methods for every API endpoint: tools, plays, auth, and health.
Handles authentication, retries, and localhost failover automatically.

Signature: `class DeeplineClient`

#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Create a low-level SDK client.<br /><br />Most callers can omit options and let the SDK resolve auth/config from<br />environment variables and CLI-managed credentials. | `options?: DeeplineClientOptions` - Optional overrides for API key, base URL, timeout, and retries. |  |
| `runs` | property | Canonical run lifecycle namespace backed by `/api/v2/runs`. |  | `RunsNamespace` |
| `db` | property | Current mutable customer database namespace backed by `/api/v2/db/query`. |  | `DbNamespace` |
| `billing` | property | Billing namespace: subscription status/cancel and invoice history. |  | `BillingNamespace` |
| `baseUrl` | getter | The resolved base URL this client is targeting (e.g. `"http://localhost:3000"`). |  | `string` |
| `listSecrets` | method | List secret metadata visible to the current workspace. |  | `Promise<PlaySecretMetadata[]>` |
| `checkSecret` | method | Check whether a named secret exists, is active, and has a stored value. | `name: string` - Secret name. It is normalized to uppercase before lookup. | `Promise<PlaySecretMetadata \| null>` |
| `listTools` | method | List all available tools.<br /><br />Returns tool definitions including ID, provider, description, input/output schemas,<br />and list extractor paths for automatic CSV conversion. | `options?: { categories?: string; tags?: string; grep?: string; grepMode?: 'all' \| 'any' \| 'phrase'; compact?: boolean; }` | `Promise<ToolDefinition[]>` |
| `searchTools` | method | Search available tools using Deepline's ranked backend search.<br /><br />This is the same discovery surface used by the CLI: it ranks across<br />tool metadata, categories, agent guidance, and input schema fields. | `options?: ToolSearchOptions` | `Promise<ToolSearchResult>` |
| `getTool` | method | Get detailed metadata for a single tool.<br /><br />Returns everything from `ToolDefinition` plus pricing info, sample<br />inputs/outputs, failure modes, and cost estimates. | `toolId: string` - Tool identifier (e.g. `"dropleads_search_people"`) | `Promise<ToolMetadata>` |
| `describeModel` | method | Describe a Deepline Agent model and its provider-specific option surface.<br /><br />Combines live AI Gateway model metadata with Deepline's generated AI SDK<br />provider option registry so agents can construct `providerOptions`<br />payloads before executing `deeplineagent`.<br /><br />The returned option schemas describe accepted provider option shapes, not<br />guaranteed support for every model. Runtime AI SDK/Gateway errors remain<br />authoritative for model-gated values. | `model: string` - Gateway model id such as `"openai/gpt-5.5"` | `Promise<DeeplineAgentModelDescription>` |
| `executeTool` | method | Execute a tool and return the standard execution envelope.<br /><br />The `toolResponse.raw` field contains the raw tool response.<br />`toolResponse.meta` contains tool/provider metadata.<br />Top-level fields such as `status`, `job_id`, and `billing` describe the<br />Deepline execution envelope. | `toolId: string`<br />`input: Record<string, unknown>`<br />`options?: ExecuteToolRawOptions` | `Promise<ToolExecution<TData, TMeta>>` |
| `executeToolRaw` | method | Back-compatible alias for `executeTool`.<br /><br />Retained for callers that still use the older raw naming while the response<br />envelope remains the same. | `toolId: string`<br />`input: Record<string, unknown>`<br />`options?: ExecuteToolRawOptions` | `Promise<ToolExecution<TData, TMeta>>` |
| `queryCustomerDb` | method | Run a bounded SQL query against the current mutable customer database.<br /><br />This query is not scoped to one play run. Use `client.runs` export actions<br />when the caller needs the rows produced by a specific run. | `input: { sql: string; maxRows?: number; }` | `Promise<CustomerDbQueryResult>` |
| `repairIngestionStorage` | method | Re-establish this workspace's tenant storage contract: role/DB connect<br />grants plus materialized table grants. Org-admin only. Use when a run fails<br />with WORKSPACE_STORAGE_NOT_READY. | `input?: { provider?: string }` | `Promise<{ connection_grants: { runtime_role: string; customer_db_role: string }; repaired: unknown[]; count: number; }>` |
| `startPlayRun` | method | Start a play run.<br /><br />Internal/advanced primitive. For normal callers, prefer the public<br />entrypoints: the CLI, `Deepline.connect`, `submitPlay`,<br />or `runPlay`.<br /><br />Supported invocation surfaces intentionally share this same run contract:<br />`deepline plays run`, repo scripts such as `bun run deepline -- plays run`,<br />SDK context calls like `Deepline.connect().play(name).run()`, and direct<br />`POST /api/v2/plays/run` calls all return a workflow/run id. The completed<br />output is always retrievable from `getPlayStatus(runId).result` (or from<br />`PlayJob.get()` for SDK context calls). Execution logs live under<br />`progress.logs`; they are not part of the user output object. | `request: StartPlayRunRequest` - Play run configuration (name, code, input, etc.) | `Promise<PlayRunStart>` |
| `startPlayRunStream` | method | Start a play run and stream live runtime events from the same request.<br /><br />Use this when a caller wants low-level event handling instead of submitting<br />first and then connecting to `streamPlayRunEvents(runId)`. | `request: StartPlayRunRequest` - Play run configuration.<br />`options?: { signal?: AbortSignal }` - Optional streaming options. | `AsyncGenerator<PlayLiveEvent>` |
| `registerPlayArtifact` | method | Register a bundled play artifact.<br /><br />Internal/advanced primitive used by packaging flows. Public callers should<br />prefer the CLI, `submitPlay`, or `runPlay`. | `input: { name: string; sourceCode: string; sourceFiles?: Record<string, string>; description?: string; artifact: Record<string, unknown>; compilerManifest?: PlayCompilerManifest; publish?: boolean; ownerType?: 'org' \| 'deepline'; scope?: 'org' \| 'system'; userId?: string; }` | `Promise<{ success?: boolean; name?: string; artifactStorageKey: string; artifactMetadata?: Record<string, unknown> \| null; staticPipeline?: unknown; definitionId?: string \| null; revisionId?: string \| null; version?: number \| null; liveVersion?: number \| null; triggerMetadata?: unknown; triggerBindings?: unknown; }>` |
| `registerPlayArtifacts` | method | Register multiple bundled play artifacts in one request.<br /><br />Used by packaging and prebuilt publication flows. Each artifact is compiled<br />first when a compiler manifest is not already supplied. | `artifacts: Array<{ name: string; sourceCode: string; sourceFiles?: Record<string, string>; description?: string; artifact: Record<string, unknown>; compilerManifest?: PlayCompilerManifest; publish?: boolean; ownerType?: 'org' \| 'deepline'; scope?: 'org' \| 'system'; userId?: string; }>` | `Promise<{ success: boolean; artifacts: Array<{ success?: boolean; name?: string; artifactStorageKey: string; artifactMetadata?: Record<string, unknown> \| null; staticPipeline?: unknown; definitionId?: string \| null; revisionId?: string \| null; version?: number \| null; liveVersion?: number \| null; triggerMetadata?: unknown; triggerBindings?: unknown; }>; }>` |
| `compilePlayManifest` | method | Compile a bundled play artifact into the server-side compiler manifest.<br /><br />The manifest records imports, trigger bindings, static pipeline shape, and<br />runtime metadata needed before a play artifact can be checked, registered,<br />or run. | `input: { name: string; sourceCode: string; sourceFiles?: Record<string, string>; artifact: Record<string, unknown>; importedPlayDependencies?: PlayCompilerManifest[]; }` | `Promise<PlayCompilerManifest>` |
| `checkPlayArtifact` | method | Check a bundled play artifact against the server's current play compiler.<br /><br />Unlike `registerPlayArtifact`, this does not store the artifact,<br />publish a revision, or start a run. It is the authoritative cloud validation<br />path used by `deepline plays check`. | `input: { name?: string; sourceCode: string; sourceFiles?: Record<string, string>; description?: string; artifact: Record<string, unknown>; integrationMode?: 'live' \| 'eval_stub' \| 'fixture'; importedPlays?: Array<{ playName?: string \| null; sourceCode: string; sourcePath?: string \| null; }>; }` | `Promise<PlayCheckResult>` |
| `startPlayRunFromBundle` | method | Register an already-bundled play artifact and start a run from it.<br /><br />This is the low-level file-backed run path used by SDK/CLI packaging<br />wrappers after local bundling has produced the runtime artifact. | `input: { name: string; sourceCode: string; sourceFiles?: Record<string, string>; description?: string; artifact: Record<string, unknown>; compilerManifest?: PlayCompilerManifest; input?: Record<string, unknown>; inputFile?: PlayStagedFileRef \| null; packagedFiles?: PlayStagedFileRef[]; force?: boolean; forceToolRefresh?: boolean; }` | `Promise<PlayRunStart>` |
| `submitPlay` | method | Register a bundled play artifact and start a run from the live revision.<br /><br />Convenience wrapper around `registerPlayArtifact` plus<br />`startPlayRun`. This is the canonical file-backed path used by wrappers.<br />The returned id can be passed to `getPlayStatus` to retrieve the same<br />durable `{ result }` object that the CLI prints after `--watch` completes. | `code: string` - Source string fallback; the bundled artifact should be passed in `options.artifact`<br />`csvPath: string \| null` - Path to input CSV file, or `null`<br />`name?: string` - Play name (extracted from source if omitted)<br />`options?: { sourceCode?: string; sourceFiles?: Record<string, string>; description?: string; artifact?: Record<string, unknown>; compilerManifest?: PlayCompilerManifest; input?: Record<string, unknown>; inputFile?: PlayStagedFileRef \| null; packagedFiles?: PlayStagedFileRef[]; force?: boolean; forceToolRefresh?: boolean; }` - Additional submission options | `Promise<PlayRunStart>` |
| `stagePlayFiles` | method | Upload files to the staging area for use in play runs.<br /><br />Internal/advanced primitive used by packaging flows. Public callers should<br />prefer the CLI, `submitPlay`, or `runPlay`.<br /><br />Staged files are referenced by their returned `PlayStagedFileRef`<br />in subsequent `startPlayRun` calls via `inputFile` or `packagedFiles`. | `files: Array<{ logicalPath: string; contentBase64: string; contentHash: string; contentType: string; bytes: number; }>` - Array of files to stage (base64-encoded content) | `Promise<PlayStagedFileRef[]>` |
| `mintStagedPlayFileUploads` | method | Mint short-lived presigned upload targets for staged play files.<br /><br />Internal primitive used by `stagePlayFiles`. The server returns an<br />already-staged ref (no upload needed) for content-addressed files it<br />already holds, or a presigned PUT URL the caller uploads the body to. | `files: Array<{ logicalPath: string; contentHash: string; contentType: string; bytes: number; }>` | `Promise<MintStagedFileUpload[]>` |
| `resolveStagedPlayFiles` | method | Resolve staged play files by content hash without uploading bytes.<br /><br />Missing files are returned so callers can upload only the files the server<br />does not already have. | `files: Array<{ logicalPath: string; contentHash: string; contentType: string; bytes: number; }>` | `Promise<{ files: PlayStagedFileRef[]; missing: Array<{ logicalPath: string; contentHash: string }>; }>` |
| `getPlayStatus` | method | Get the current status of a play execution.<br /><br />Internal/advanced primitive. Public callers should usually prefer<br />`runPlay`, `PlayJob.get`, or `deepline plays run --watch`. | `workflowId: string` - Play-run id from `startPlayRun`<br />`options?: { billing?: boolean; full?: boolean }` | `Promise<PlayStatus>` |
| `streamPlayRunEvents` | method | Stream semantic play-run events using the same SSE feed as the dashboard.<br /><br />The server emits a canonical `play.run.snapshot` event first for every<br />connection, then incremental live events until terminal state or reconnect. | `workflowId: string`<br />`options?: { signal?: AbortSignal; lastEventId?: string; mode?: 'cli' \| 'ui'; }` | `AsyncGenerator<PlayLiveEvent>` |
| `cancelPlay` | method | Cancel a running play execution.<br /><br />Sends a stop request for the run. | `workflowId: string` - Public Deepline play-run id to cancel | `Promise<void>` |
| `stopPlay` | method | Stop a running play execution, including open HITL waits. | `workflowId: string` - Public Deepline play-run id to stop<br />`options?: { reason?: string }` | `Promise<StopPlayRunResult>` |
| `listPlayRuns` | method | List recent runs for a named play.<br /><br />Returns runs sorted by start time (newest first), including workflow IDs,<br />status, timestamps, and metadata. | `playName: string` - The play name to query | `Promise<PlayRunListItem[]>` |
| `getRunStatus` | method | Get a run by id using the public runs resource model.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs get <run-id> --json<br />``` | `runId: string`<br />`options?: RunsGetOptions` | `Promise<PlayStatus>` |
| `listRuns` | method | List play runs using the public runs resource model.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs list --play <play-name> --status failed --json<br />``` | `options: RunsListOptions` | `Promise<PlayRunListItem[]>` |
| `observeRunEvents` | method | Observe one run's live events. Uses the Convex Run Snapshot subscription<br />transport first (ADR-0008), then falls back to the canonical SSE stream<br />when the subscription transport or its optional client modules are not<br />available. Pass `fallback: 'none'` to receive<br />`RunObserveTransportUnavailableError` instead. | `runId: string`<br />`options?: { signal?: AbortSignal; onNotice?: (message: string) => void; fallback?: 'sse' \| 'none'; }` | `AsyncGenerator<PlayLiveEvent>` |
| `tailRun` | method | Read the canonical run stream until a terminal run status is observed.<br /><br />Tries the Convex Run Snapshot subscription transport first (ADR-0008);<br />when the server cannot serve it (grant endpoint missing/unconfigured or<br />Convex unreachable) it falls back — with one `onNotice` message — to the<br />support-window SSE stream below.<br /><br />Server stream windows are finite: they end cleanly at the function<br />ceiling even while the run keeps executing. A window that ends (cleanly<br />or via transient network error) without a terminal event triggers one<br />durable-status re-check followed by a backed-off reconnect, so long runs<br />tail to completion. Abort via `options.signal` to stop waiting. | `runId: string`<br />`options?: RunsTailOptions` | `Promise<PlayStatus>` |
| `getRunLogs` | method | Fetch persisted logs for a run using the public runs resource model.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs logs <run-id> --limit 200 --json<br />``` | `runId: string`<br />`options?: RunsLogsOptions` | `Promise<RunsLogsResult>` |
| `getPlaySheetRows` | method | Export persisted runtime-sheet rows for a play dataset/table namespace.<br /><br />This is the SDK form of exporting `ctx.dataset(...).run()` output for a<br />specific play and optional run id. | `input: { playName: string; tableNamespace: string; runId?: string; limit?: number; offset?: number; rowMode?: 'output' \| 'all'; }` | `Promise<PlaySheetRowsResult>` |
| `stopRun` | method | Stop a run by id using the public runs resource model.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs stop <run-id> --reason "stale lock" --json<br />``` | `runId: string`<br />`options?: { reason?: string }` | `Promise<StopPlayRunResult>` |
| `stopAllRuns` | method | Stop every active run visible to the current workspace.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs stop-all --reason "stale lock" --json<br />```<br /><br />Use this when a failed parent run left child or waiting runs active and you<br />need to clear the workspace run-slot state without knowing each run id. | `options?: { reason?: string; }` | `Promise<StopAllPlayRunsResult>` |
| `listPlays` | method | List callable plays visible to the workspace.<br /><br />Pass `origin: "prebuilt"` for Deepline-managed prebuilts or<br />`origin: "owned"` for org-owned plays. | `options?: { origin?: 'prebuilt' \| 'owned'; grep?: string; grepMode?: 'all' \| 'any' \| 'phrase'; }` | `Promise<PlayListItem[]>` |
| `searchPlays` | method | Search callable plays and return compact play descriptions.<br /><br />Prebuilt plays are preferred by default because they have maintained<br />contracts and stable run behavior. | `options: { query: string; compact?: boolean; scope?: 'prebuilt' \| 'owned' \| 'all'; }` | `Promise<PlayDescription[]>` |
| `getPlay` | method | Get the full definition and state of a named play.<br /><br />Returns the play's revision state (draft, live), recent runs,<br />sheet processing summary, and database URL. | `name: string` - Play name | `Promise<PlayDetail>` |
| `describePlay` | method | Get a normalized play description suitable for agents and CLIs.<br /><br />The description includes runnable examples, input/output summaries, clone<br />guidance, revision state, and latest run metadata when available. | `name: string`<br />`options?: { compact?: boolean }` | `Promise<PlayDescription>` |
| `clearPlayHistory` | method | Clear run history and durable sheet/result data for a play without deleting<br />the play definition or revisions. | `name: string`<br />`request?: ClearPlayHistoryRequest` | `Promise<ClearPlayHistoryResult>` |
| `listPlayVersions` | method | List saved versions for a named play.<br /><br />Returns immutable revision snapshots newest-first, including the revision<br />id needed for exact-version runs and live-version switching. | `name: string` - Play name<br />`options?: { full?: boolean }` | `Promise<PlayRevisionSummary[]>` |
| `publishPlayVersion` | method | Make a play revision live.<br /><br />When `revisionId` is omitted, the current working revision becomes live.<br />The live version is what executes when the play is run by name without<br />specifying an explicit revision. | `name: string` - Play name<br />`request?: PublishPlayVersionRequest` - Optional explicit revision to make live | `Promise<PublishPlayVersionResult>` |
| `deletePlay` | method | Delete an org-owned play definition, including its revisions, trigger<br />bindings, and local run records. Deepline prebuilt plays are read-only. | `name: string` | `Promise<DeletePlayResult>` |
| `getSharePage` | method | Current share status for a play: the public page (if any), the published<br />copy, and the revision picker. Read-only. | `name: string` | `Promise<SharePageStatus>` |
| `publishSharePage` | method | Publish (or repoint) the play's public share page to a revision. Requires<br />`acknowledgedUnlisted: true` — the page is publicly viewable. Org-admin only. | `name: string`<br />`request: PublishSharePageRequest` | `Promise<SharePageStatus>` |
| `updateSharePage` | method | Update share-page settings (SEO indexing, credit-cost / latency display)<br />without moving the published pointer. Org-admin only. | `name: string`<br />`request: UpdateSharePageRequest` | `Promise<SharePageStatus>` |
| `unpublishSharePage` | method | Unshare: hard-delete the play's public page and its cards. Returns the<br />fresh status (now `share: null`). Org-admin only. Idempotent — a no-op when<br />the play was never published. | `name: string` | `Promise<SharePageStatus>` |
| `regenerateSharePage` | method | Regenerate the LLM landing-page copy for a revision (defaults to the<br />published one). Org-admin only. | `name: string`<br />`request?: { revisionId?: string }` | `Promise<SharePageStatus>` |
| `runPlay` | method | Run a play end-to-end: submit, stream until terminal, return result.<br /><br />This is the highest-level play execution method. It submits the play,<br />reads the canonical run stream for status updates, and returns a structured<br />result with logs and timing. Supports cancellation via `AbortSignal`. | `code: string` - Source string fallback; pass the bundled artifact in `options.artifact`<br />`csvPath: string \| null` - Input CSV path, or `null`<br />`name?: string` - Play name<br />`options?: { onProgress?: (status: PlayStatus) => void; signal?: AbortSignal; input?: Record<string, unknown>; sourceCode?: string; artifact?: Record<string, unknown>; compilerManifest?: PlayCompilerManifest; inputFile?: PlayStagedFileRef \| null; packagedFiles?: PlayStagedFileRef[]; force?: boolean; forceToolRefresh?: boolean; }` - Execution options | `Promise<PlayRunResult>` |
| `getBillingPlans` | method | Published plans plus the caller's active plan: prices, monthly grant<br />credits, rollover policy, and which plans are open for subscription.<br />Prefer `client.billing.plans()`. |  | `Promise<BillingPlansResult>` |
| `topUpBillingBalance` | method | Charge the saved payment method and add Deepline credits to the active<br />workspace. Prefer `client.billing.topUp(...)`. | `options: { credits: number; idempotencyKey?: string; }` | `Promise<BillingTopUpResult>` |
| `getBillingSubscriptionStatus` | method | Subscription state for the active workspace: active plan, whether a<br />Stripe subscription backs it, renewal/cancellation facts, and remaining<br />Deepline credit pools. Prefer `client.billing.subscription.status()`. |  | `Promise<BillingSubscriptionStatus>` |
| `cancelBillingSubscription` | method | Schedule subscription cancellation at period end, or reverse a pending<br />cancellation with `{ undo: true }`. The customer keeps the cycle they<br />paid for and every remaining credit — cancellation never claws back<br />credits. Prefer `client.billing.subscription.cancel(...)`. | `options?: { undo?: boolean; }` | `Promise<BillingSubscriptionCancelResult>` |
| `listBillingInvoices` | method | Customer-facing billing history: subscription invoices plus one-time<br />credit purchase receipts, newest first, with Stripe-hosted links.<br />Prefer `client.billing.invoices.list(...)`. | `options?: { limit?: number; }` | `Promise<BillingInvoicesResult>` |
| `health` | method | Check API connectivity and server health. |  | `Promise<{ status: string; version?: string }>` |

### `client.runs`

Public runs namespace exposed as `client.runs`.

This namespace mirrors the canonical `/api/v2/runs` resource family and is
the preferred low-level surface for polling, streaming, stopping, reading
logs, and exporting durable dataset rows.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `get` | `(runId: string, options?: RunsGetOptions) => Promise<PlayStatus>` | Yes | Get current run status by public run id. |
| `list` | `(options: RunsListOptions) => Promise<PlayRunListItem[]>` | Yes | List runs for one play, optionally filtered by status. |
| `tail` | `(runId: string, options?: RunsTailOptions) => Promise<PlayStatus>` | Yes | Stream run events and return the latest/terminal run status. |
| `logs` | `(runId: string, options?: RunsLogsOptions) => Promise<RunsLogsResult>` | Yes | Fetch persisted log lines for a run. |
| `exportDatasetRows` | `(input: { playName: string; tableNamespace: string; runId?: string; limit?: number; offset?: number; rowMode?: 'output' \| 'all'; }) => Promise<PlaySheetRowsResult>` | Yes | Export persisted rows for a runtime-sheet dataset/table namespace. |
| `stop` | `( runId: string, options?: { reason?: string }, ) => Promise<StopPlayRunResult>` | Yes | Stop a running/waiting run. |
| `stopAll` | `(options?: { reason?: string }) => Promise<StopAllPlayRunsResult>` | Yes | Stop active runs across the current workspace. |


### `client.billing`

Public billing namespace exposed as `client.billing`.

Carries the durable Deepline billing product model — plans, subscription
state, period-end cancellation, and invoice/receipt history — so CLI
commands and programmatic callers share the same surface.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `topUp` | `(options: { credits: number; idempotencyKey?: string; }) => Promise<BillingTopUpResult>` | Yes | Charge the saved payment method and add Deepline credits to the active workspace. |
| `plans` | `() => Promise<BillingPlansResult>` | Yes | Published plans plus the plan you are on ("what plans exist and what am I on"). |
| `subscription` | `{ status: () => Promise<BillingSubscriptionStatus>; cancel: (options?: { undo?: boolean; }) => Promise<BillingSubscriptionCancelResult>; }` | Yes |  |
| `invoices` | `{ list: (options?: { limit?: number }) => Promise<BillingInvoicesResult>; }` | Yes |  |
