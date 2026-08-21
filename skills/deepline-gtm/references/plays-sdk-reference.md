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

### Fall Through A Transient Provider Failure

Catch only `ProviderTransientError` when another read provider can answer the same question. Validation, authentication, billing, Deepline, unknown, and final-provider failures stay loud.

Source: `docs-examples/sdk-v2/provider-fallback.play.ts`

```ts
import { definePlay, ProviderTransientError } from 'deepline';

type Input = {
  firstName: string;
  lastName: string;
  domain: string;
};

export default definePlay(
  'docs-provider-fallback',
  async (ctx, input: Input) => {
    try {
      const primary = await ctx.tools.execute({
        id: 'primary_email',
        tool: 'hunter_email_finder',
        input: {
          first_name: input.firstName,
          last_name: input.lastName,
          domain: input.domain,
        },
        description: 'Try the primary email provider.',
      });
      return { email: primary.extractedValues.email?.get() ?? null };
    } catch (error) {
      if (!(error instanceof ProviderTransientError)) throw error;
    }

    const fallback = await ctx.tools.execute({
      id: 'fallback_email',
      tool: 'leadmagic_email_finder',
      input: {
        first_name: input.firstName,
        last_name: input.lastName,
        domain: input.domain,
        company_domain: input.domain,
      },
      description: 'Try the fallback email provider.',
    });
    return { email: fallback.extractedValues.email?.get() ?? null };
  },
  {
    description:
      'Find an email with one safe provider-failure fallback and loud terminal errors.',
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
      auth: {
        type: 'standard-webhooks',
        headerFamily: 'standard',
        signingSecrets: ['INBOUND_RELAY_WEBHOOK_SECRET'],
        toleranceSeconds: 300,
      },
    },
  },
);
```

## Play Authoring Contract

New artifacts pin authoring contract edition 3. Check, publish, and run use the same admitted snapshot.

| Field | Type | Required | Contract |
|---|---|---:|---|
| `description` | `string` | No | Optional non-empty human-readable summary of the Play. |
| `compatibility.toolErrorSchemaVersion` | `0 \| 1` | No | Artifact-pinned tool error behavior, either 0 or 1. |
| `inline` | `boolean` | No | Compiler hint for an inline named Play handler. |
| `billing.maxCreditsPerRun` | `number` | No | Maximum Deepline credits permitted for one Play Run. |
| `bindings.webhook.hmac.secretEnv` | `string` | Yes | Environment variable containing the webhook HMAC secret. |
| `bindings.webhook.hmac.algorithm` | `'sha256'` | No | Webhook signature hash algorithm. Only sha256 is supported. |
| `bindings.webhook.hmac.header` | `string` | No | HTTP header containing the webhook signature. |
| `bindings.webhook.auth.type` | `'standard-webhooks'` | No | Uses the Standard Webhooks v1 symmetric signing scheme. |
| `bindings.webhook.auth.headerFamily` | `'standard' \| 'svix'` | No | Header namespace expected from the webhook provider. |
| `bindings.webhook.auth.signingSecrets[]` | `string` | No | Deepline Secret name used to verify Standard Webhooks. |
| `bindings.webhook.auth.toleranceSeconds` | `number` | No | Accepted delivery timestamp skew in seconds, from 1 through 3600. |
| `bindings.cron.schedule` | `string` | Yes | Five-field cron expression. |
| `bindings.cron.timezone` | `string` | No | IANA timezone. Omitted means UTC. |
| `bindings.sqlListeners` | `SqlListener[]` | No | Static provider-monitor listener declarations. |
| `bindings.sqlListeners[].id` | `string` | Yes | Unique static listener identifier within one Play. |
| `bindings.sqlListeners[].tool` | `string` | Yes | Modeled provider monitor tool id in provider.tool form. |
| `bindings.sqlListeners[].stream` | `string` | Yes | Static output stream key exposed by the monitor tool. |
| `bindings.sqlListeners[].operations[]` | `'INSERT' \| 'UPDATE' \| 'DELETE'` | No | Database operation that wakes the listener. |
| `bindings.sqlListeners[].where.before` | `Record<string, SqlListenerFilterOperator>` | No | Column filters evaluated against the row before mutation. |
| `bindings.sqlListeners[].where.after` | `Record<string, SqlListenerFilterOperator>` | No | Column filters evaluated against the row after mutation. |
| `bindings.sqlListeners[].where.*.*.eq` | `SqlListenerFilterScalar` | No | Scalar equality condition. |
| `bindings.sqlListeners[].where.*.*.neq` | `SqlListenerFilterScalar` | No | Scalar inequality condition. |
| `bindings.sqlListeners[].where.*.*.in` | `readonly SqlListenerFilterScalar[]` | No | Non-empty scalar membership condition. |
| `bindings.sqlListeners[].where.*.*.notIn` | `readonly SqlListenerFilterScalar[]` | No | Non-empty scalar exclusion condition. |
| `bindings.sqlListeners[].where.*.*.isNull` | `true` | No | Matches null values when set to true. |
| `bindings.sqlListeners[].where.*.*.isNotNull` | `true` | No | Matches non-null values when set to true. |
| `bindings.sqlListeners[].where.*.*.ilike` | `string` | No | Case-insensitive SQL pattern condition. |
| `bindings.secrets[]` | `string` | No | Environment variable made available to the Play. |
| `staleAfterSeconds` | `number \| null` | No | `0` always executes; `null`/omitted never expires; a positive integer is a TTL in seconds. |
| `ctx.tools.execute.id` | `string` | Yes | Stable durable receipt identity within one execution scope. |
| `ctx.tools.execute.tool` | `K` | Yes | Integration tool id resolved against the generated ToolMap. |
| `ctx.tools.execute.input` | `K extends keyof ToolMap ? ToolMap[K]['input'] : Record<string, unknown>` | Yes | Tool-specific input object. |
| `ctx.tools.execute.description` | `string` | No | Human-readable purpose of the durable tool call. |
| `ctx.tools.execute.force` | `boolean` | No | Explicitly bypasses a completed durable tool receipt. |
| `ctx.tools.execute.timeoutMs` | `number` | No | Positive whole-number runtime transport timeout in milliseconds. |
| `ctx.tools.execute.receiptWaitMs` | `number` | No | Positive whole-number durable receipt wait budget in milliseconds. |
| `ctx.csv.options.description` | `string` | No | Non-empty description for a staged CSV load. |
| `ctx.csv.options.columns` | `CsvRenameMap` | No | Canonical field-to-header aliases for a staged CSV. |
| `ctx.csv.options.rename` | `CsvRenameMap` | No | Legacy header rename aliases for a staged CSV. |
| `ctx.csv.options.required` | `readonly string[]` | No | Canonical columns required after CSV normalization. |
| `ctx.dataset.key` | `string` | Yes | Stable durable identity for one dataset. |
| `ctx.dataset.run.description` | `string` | No | Non-empty description for one dataset execution. |
| `ctx.dataset.run.key` | `DatasetRowKey<InputRow>` | No | Stable field or fields used for durable row identity. |
| `ctx.dataset.run.onRowError` | `'isolate' \| 'fail'` | No | Whether row failures isolate or fail the whole dataset. |
| `ctx.dataset.run.mode` | `'upsert' \| 'net_new'` | No | Whether the dataset returns all rows or only newly admitted rows. |
| `ctx.dataset.run.undrawnColumns` | `readonly string[]` | No | Computed columns deliberately left out of the authored @mermaid diagram. |
| `ctx.step.id` | `string` | Yes | Stable durable identity for one scalar checkpoint. |
| `ctx.step.semanticKey` | `string` | No | Optional semantic receipt identity for a scalar checkpoint. |
| `ctx.step.staleAfterSeconds` | `number \| null` | No | Checkpoint freshness: null/omitted never expires, 0 always executes. |
| `ctx.fetch.key` | `string` | Yes | Stable durable identity for one external HTTP request. |
| `ctx.fetch.staleAfterSeconds` | `number \| null` | No | Fetch freshness: null/omitted never expires, 0 always executes. |
| `ctx.runPlay.key` | `string` | Yes | Stable identity for one inline child Play call. |
| `ctx.runPlay.playRef` | `string \| PlayReferenceLike` | Yes | Child Play name or typed Play definition handle. |
| `ctx.runPlay.input` | `Record<string, unknown>` | Yes | Scalar input object submitted to the child Play. |
| `ctx.runPlay.options.description` | `string` | Yes | Non-empty purpose for one inline child Play call. |
| `ctx.runPlay.options.execution` | `'inline'` | No | Child composition strategy. Only inline is supported. |
| `ctx.runPlay.options.timeoutMs` | `never` | No | Unsupported legacy child-workflow timeout. |
| `runtime.timeout` | `string` | No | Sandbox deadline such as 90m or 2h. |
| `runtime.size` | `'standard'` | No | Deepline-managed sandbox size. Only standard is supported. |
| `ctx.customerDb.query.statement` | `SqlQuery` | Yes | One non-empty Customer DB SQL string; the deprecated SqlQuery object is accepted only without parameter values. |
| `ctx.customerDb.query.options.maxRows` | `number` | No | Positive whole-number Customer DB response row limit. |
| `ctx.customerDb.query.options.timeoutMs` | `number` | No | Positive whole-number Customer DB timeout in milliseconds. |
| `ctx.tool.key` | `string` | Yes | Stable receipt identity for the tool shorthand. |
| `ctx.tool.tool` | `string` | Yes | Integration tool id for the tool shorthand. |
| `ctx.tool.input` | `Record<string, unknown>` | Yes | Tool-specific input object for the shorthand. |
| `ctx.tool.options.description` | `string` | No | Non-empty purpose for the tool shorthand. |
| `ctx.runSteps.options.description` | `string` | No | Non-empty purpose for a reusable step program. |
| `ctx.sleep.ms` | `number` | Yes | Non-negative whole-number sleep duration in milliseconds. |
| `ctx.fetch.url` | `string` | Yes | HTTP request URL. Secret authentication requires HTTPS. |
| `ctx.fetch.init.method` | `string` | No | HTTP method. Mutating methods require an Idempotency-Key. |
| `ctx.fetch.init.headers.Idempotency-Key` | `string` | No | Required for mutating HTTP methods to make replay safe. |

### Durable call keys are static

Durable call keys — the ctx.fetch key, the ctx.dataset key, the ctx.step id — must be static string literals. The key names a durable receipt, so check, publish, and replay have to agree on it before the body runs. A key computed at runtime cannot be resolved at check time and is rejected.

This is an architectural constraint, not a style rule. A play cannot loop over a computed key, so it cannot page a large table with a helper like page(pageNumber). Unrolling one literal key per page is not a design at any real page count.

Push the aggregation server-side and call it once: a SQL function, a view, or a provider endpoint that returns the whole result. Keep unrolled literal keys only for a handful of genuinely distinct calls. To fan out over rows, use ctx.dataset with a static key — the per-row receipt identity comes from the row, not from the key.

### Durable HTTP batches

A static ctx.fetch key inside a loop is a warning because every iteration must still have distinct method, URL, body, or safe headers. One durable receipt must never stand in for every request.

Keep the static fetch label. For a mutating batch, make the body distinct and use a replay-stable external Idempotency-Key such as `${ctx.run.id}:signals:${batchIndex}`.

### `ctx.run.id`

ctx.run.id is stable while Deepline retries or resumes one durable run. A separately submitted run receives a new id.

Use it when deriving an external idempotency key for a sequence of batches.

Generated from source comments and type declarations by `scripts/generate-play-sdk-reference.ts`. Do not edit this file manually.

## Version And Coverage

| Field | Value |
|---|---|
| SDK version | `0.2.0` |
| SDK HTTP API | `v2` |
| Checked-in SDK fallback | `0.2.0` |
| Minimum supported SDK | `0.1.53` |
| Deprecated below | `0.1.219` |
| Generated sources | `sdk/src/client.ts`<br />`sdk/src/errors.ts`<br />`sdk/src/play.ts`<br />`shared_libs/play-runtime/cell-staleness.ts`<br />`shared_libs/play-runtime/tool-result-types.ts`<br />`shared_libs/plays/authoring-contract.ts`<br />`shared_libs/plays/dataset.ts`<br />`shared_libs/tool-execution-error.ts` |
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
| `bindings` | [`PlayBindings`](#playbindings) | No | Trigger bindings. |

#### Returns

`DefinedPlay<TInput, TOutput>`


### `DefinePlayConfig`

Object-form play definition accepted by `definePlay(config)`.

Use this form when the input contract should be explicit at definition time
through `defineInput<T>(schema)`, or when configuration reads clearer as one
object. The shorthand `definePlay(name, fn, bindings?)` is equivalent for
simple file-backed plays.

Signature: `export type DefinePlayConfig< TInput, TOutput extends PlayReturnObject, > = PlayAuthoringDefineConfig<TInput, TOutput, DeeplinePlayRuntimeContext>;`


### `PlayBindings`

Optional trigger bindings for a play.

A play can be triggered three ways, declared as the third argument to
[definePlay](/sdk-v2/sdk-reference#defineplay):
- `webhook` — an inbound HTTP call (with optional legacy HMAC or Standard
  Webhooks signature verification);
- `cron` — a schedule; or
- `sqlListeners` — a **monitor**: the play runs whenever a monitor writes a new
  row to its output stream. This is how you build a play "on top of" a monitor
  (e.g. run enrichment every time a watched company posts a new job). Each
  listener binds to a monitor tool id + one of its output stream keys (see
  `deepline monitors available <id>` for a tool's streams and row columns).
  The changed row is delivered to the handler as the listener event's `after`.

Signature: `export type PlayBindings = PlayAuthoringBindings;`


### `ctx.csv(path, options)`

Load a staged CSV file as a durable dataset handle.

Signature: `csv<T = Record<string, unknown>>( path: string | CsvInput<T & object>, options?: CsvOptions, ): Promise<PlayDataset<T>>;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `path` | `string \| CsvInput<T & object>` | Yes |  |
| `options` | [`CsvOptions`](#csvoptions) | No |  |

#### Returns

`Promise<PlayDataset<T>>` — see [`PlayDataset`](#playdataset)


### `CsvOptions`

Options for loading a staged CSV with `ctx.csv(...)`.

Signature: `export type CsvOptions = CsvOptions;`


### `ctx.dataset(key, items)`

Create a persisted row dataset and define durable output columns.

Signature: `dataset<TSource extends PlayDatasetInput<object>>( key: string, items: TSource, ): DatasetBuilder< PlayDatasetRow<TSource> & object, PlayDatasetRow<TSource> & object, PlayAuthoringRuntimeContext >;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `key` | `string` | Yes |  |
| `items` | `TSource` | Yes |  |

#### Returns

`DatasetBuilder< PlayDatasetRow<TSource> & object, PlayDatasetRow<TSource> & object, PlayAuthoringRuntimeContext >`


### `.dataset(...).withColumn(name, resolver).run(options)`

Define one output column for every row in this dataset.

```ts
withColumn<Name extends string, Value>( name: Name, resolver: ColumnResolver<OutputRow, Value>, ): DatasetBuilder< InputRow, OutputRow & Record<Name, Value> >;

withColumn<Name extends string, Value>( name: Name, definition: DatasetColumnDefinition< OutputRow, Value > & { readonly runIf: ( row: OutputRow, index: number, ) => boolean | Promise<boolean>; }, ): DatasetBuilder< InputRow, OutputRow & Record<Name, Value | null> >;

withColumn<Name extends string, Value>( name: Name, definition: DatasetColumnDefinition< OutputRow, Value >, ): DatasetBuilder< InputRow, OutputRow & Record<Name, Value> >;

withColumn<Name extends string, Value>( name: Name, resolver: | StepResolver<OutputRow, Value> | RunnableStepProgram<unknown, Value>, options: StepOptions<OutputRow, Value>, ): DatasetBuilder< InputRow, OutputRow & Record<Name, Value | null> >;

run( options?: DatasetRunOptions<InputRow>, ): Promise<PlayDataset<OutputRow>>;
```

#### Column Overload 1 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes |  |
| `resolver` | `ColumnResolver<OutputRow, Value>` | Yes |  |

#### Column Overload 1 Returns

`DatasetBuilder< InputRow, OutputRow & Record<Name, Value> >`

#### Column Overload 2 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes |  |
| `definition` | `DatasetColumnDefinition< OutputRow, Value > & { readonly runIf: ( row: OutputRow, index: number, ) => boolean \| Promise<boolean>; }` | Yes |  |

#### Column Overload 2 Returns

`DatasetBuilder< InputRow, OutputRow & Record<Name, Value | null> >`

#### Column Overload 3 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes |  |
| `definition` | `DatasetColumnDefinition< OutputRow, Value >` | Yes |  |

#### Column Overload 3 Returns

`DatasetBuilder< InputRow, OutputRow & Record<Name, Value> >`

#### Column Overload 4 Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `Name` | Yes |  |
| `resolver` | `\| StepResolver<OutputRow, Value> \| RunnableStepProgram<unknown, Value>` | Yes |  |
| `options` | `StepOptions<OutputRow, Value>` | Yes |  |

#### Column Overload 4 Returns

`DatasetBuilder< InputRow, OutputRow & Record<Name, Value | null> >`

#### Run Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `options` | `DatasetRunOptions<InputRow>` | No |  |

#### Run Returns

`Promise<PlayDataset<OutputRow>>` — see [`PlayDataset`](#playdataset)

Execute the row-column program and return a durable dataset handle.
`upsert` preserves row-by-row enrichment. `net_new` admits and returns only
unseen stable keys. `isolate` records failed rows while siblings continue;
`fail` opts into fail-fast behavior.

### `DatasetColumnRunInput`

Input object passed to an object-column `run` resolver.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `row` | `Row` | Yes | Current row, including previously computed columns. |
| `ctx` | `DeeplinePlayRuntimeContext` | Yes | Runtime context for tool, Play, fetch, and log calls. |
| `index` | `number` | Yes | Zero-based row index for this dataset run. |
| `previousCell` | `PreviousCell<Value>` | No | Prior stored cell value and freshness metadata when this cell reruns. |


### `DatasetColumnDefinition`

Object-column form for `.withColumn(...)`.

Use this when a column needs `runIf` or typed `previousCell`.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `run` | `( input: DatasetColumnRunInput<Row, Value>, ) => Value \| Promise<Value>` | Yes | Compute one cell value. Receives the previous stored value when rerunning. |
| `runIf` | `(row: Row, index: number) => boolean \| Promise<boolean>` | No | Optional row-level gate. Skipped rows produce `null` for this column. |


### `StepOptions`

Options for row-level `.withColumn(...)` and `steps().step(...)` entries.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `runIf` | `(row: Row, index: number) => boolean \| Promise<boolean>` | No | Optional row-level gate. Skipped rows produce `null` for this column. |
| `recompute` | `boolean` | No | Legacy dataset-column flag. Prefer freshness on the reusable call. |
| `recomputeOnError` | `boolean` | No | Legacy error-recompute flag accepted for older authored Plays. |
| `staleAfterSeconds` | `number` | No | Legacy cell staleness metadata accepted for older authored Plays. |


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

Create one scalar durable checkpoint.

Signature: `step<T>( id: string, run: () => T | Promise<T>, options?: RuntimeStepOptions, ): Promise<T>;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `id` | `string` | Yes |  |
| `run` | `() => T \| Promise<T>` | Yes |  |
| `options` | `RuntimeStepOptions` | No |  |

#### Returns

`Promise<T>`


### `ctx.runPlay(key, playRef, input, options)`

Compose another Play inline under a stable call key.

Signature: `runPlay<TOutput = unknown>( key: string, playRef: string | PlayReferenceLike, input: Record<string, unknown>, options: PlayCallOptions, ): Promise<TOutput>;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `key` | `string` | Yes |  |
| `playRef` | `string \| PlayReferenceLike` | Yes |  |
| `input` | `Record<string, unknown>` | Yes |  |
| `options` | `PlayCallOptions` | Yes |  |

#### Returns

`Promise<TOutput>`


### `ctx.tools.execute(request)`

Execute a provider tool through the durable receipt contract.

Signature: `execute<TOutput = PlayLooseObject>( request: PlayToolExecutionRequest, ): Promise<ToolExecuteResult<TOutput>>;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `request` | `PlayToolExecutionRequest` | Yes |  |

#### Returns

`Promise<ToolExecuteResult<TOutput>>` — see [`ToolExecuteResult`](#toolexecuteresult)


### `ToolExecutionRequest`

Keyword-style request object for `ctx.tools.execute(...)`.

The `tool` value comes from live tool discovery. The `id` is the stable
logical call name used for logs, metadata, and receipt attachment. Provider
call reuse is keyed by play, tool, semantic input, auth scope, provider action
version, and cache policy.

Signature: `export type ToolExecutionRequest = PlayToolExecutionRequest;`


### `ctx.fetch(key, url, init)`

Execute a durable, replay-safe HTTP request.

Signature: `fetch( key: string, url: string | URL, init?: SecretAwareRequestInit, options?: FetchOptions, ): Promise<PlayFetchResponse>;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `key` | `string` | Yes |  |
| `url` | `string \| URL` | Yes |  |
| `init` | [`SecretAwareRequestInit`](#secretawarerequestinit) | No |  |
| `options` | `FetchOptions` | No |  |

#### Returns

`Promise<PlayFetchResponse>` — see [`PlayFetchResponse`](#playfetchresponse)


### `ctx.secrets.get(name)`

Reference a workspace secret by name without reading its value. This is the only supported way to authenticate an outbound request from a Play: `process.env.X` is rejected at check time because an env read puts the raw value in a play variable, where it can reach a log line or a replay artifact. A handle cannot — pass it to `bearer` or `header` and the runtime resolves it only while attaching the header. Names are uppercased; manage stored values with `deepline secrets set` / `deepline secrets list`.

Signature: `get(name: string): SecretHandle;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `string` | Yes |  |

#### Returns

`SecretHandle` — see [`SecretHandle`](#secrethandle)


### `ctx.secrets.bearer(secret)`

Send the secret as `Authorization: Bearer <value>`.

Signature: `bearer(secret: SecretHandle): SecretAuth;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `secret` | [`SecretHandle`](#secrethandle) | Yes |  |

#### Returns

`SecretAuth` — see [`SecretAuth`](#secretauth)


### `ctx.secrets.header(header, secret)`

Send the secret as a named header, for APIs that do not use bearer tokens — `x-api-key`, `apikey`, `private-token`, and similar.

Signature: `header(header: string, secret: SecretHandle): SecretAuth;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `header` | `string` | Yes |  |
| `secret` | [`SecretHandle`](#secrethandle) | Yes |  |

#### Returns

`SecretAuth` — see [`SecretAuth`](#secretauth)


### `SecretAwareRequestInit`

The `init` accepted by `ctx.fetch`. Same shape as `RequestInit` plus `auth`.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `headers` | `HeadersInit` | No | Ordinary request headers, recorded in the durable receipt. Never interpolate a secret value here — use `auth`. |
| `auth` | `SecretAuthInput` | No | One or more secret-backed authentication headers for this request. Pass a single `ctx.secrets` auth for the common case, or an array when an API requires multiple credentialed headers — for example, Supabase with both `apikey` and `Authorization`. Every secret is resolved only while the request is attached, never stored in the durable receipt. Each auth entry must target a distinct header. |


### `PlayFetchResponse`

The value `ctx.fetch(...)` resolves to: a plain durable record, not a WHATWG `Response`. The body is read once at request time so the call can be checkpointed and replayed, so `bodyText` and `json` are already-materialized properties. There is no `.json()`, `.text()`, or `.body` to await — `await res.json()` is a type error, not a typing problem.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `ok` | `boolean` | Yes | True when the response status is in the 2xx range. |
| `status` | `number` | Yes | HTTP status code as returned by the upstream server. |
| `statusText` | `string` | Yes | HTTP status text as returned by the upstream server. |
| `url` | `string` | Yes | Final response URL after any redirects. |
| `headers` | `Record<string, string>` | Yes | Response headers, lowercased, with any known secret values redacted. |
| `bodyText` | `string` | Yes | Full response body as text, with any known secret values redacted. |
| `json` | `unknown \| null` | Yes | The parsed body, eagerly decoded at request time. Read it as a property — `const body = res.json`, never `await res.json()`. Null when the body is empty AND when it is not valid JSON: a malformed payload is reported as null rather than thrown, so check `res.ok` and fall back to `res.bodyText` before treating null as an empty result. |


### `SecretHandle`

An opaque reference to a workspace secret, returned by `ctx.secrets.get`. The handle never carries the value into play code: it stringifies to `[secret:NAME]` and throws on `JSON.stringify`, so a secret cannot reach a play variable, a log line, a dataset cell, or a replay artifact even by accident. Only the runtime resolves it, at the moment it attaches the request header.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `name` | `string` | Yes | Name of the workspace secret, uppercased. Never its value. |


### `SecretAuth`

One resolved authentication scheme, built by `ctx.secrets.bearer` or `ctx.secrets.header` and attached to a request through `init.auth`.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `kind` | `'bearer' \| 'header'` | Yes | `bearer` sends `Authorization: Bearer <value>`; `header` sends a named header. |
| `secret` | `SecretHandle` | Yes | The handle whose value the runtime attaches. |
| `header` | `string` | No | Header name, set only when `kind` is `header`. |


### `ctx.runSteps(program, input, options)`

Execute one reusable step program against a scalar input.

Signature: `runSteps<TInput extends Record<string, unknown>, TOutput>( program: PlayAuthoringRunnableStepProgram< TOutput, PlayAuthoringRuntimeContext > & { readonly __inputType?: (input: TInput) => void }, input: TInput, options?: PlayAuthoringRunStepsOptions, ): Promise<TOutput>;`
#### Parameters

| Name | Type | Required | Description |
|---|---|---:|---|
| `program` | `PlayAuthoringRunnableStepProgram< TOutput, PlayAuthoringRuntimeContext > & { readonly __inputType?: (input: TInput) => void }` | Yes |  |
| `input` | `TInput` | Yes |  |
| `options` | `PlayAuthoringRunStepsOptions` | No |  |

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
`.toArray()`, `.length`, numeric indexing, spread, or synchronous iteration;
those hide the runtime cost of loading persisted rows into memory or make
behavior depend on whether rows happen to be resident.

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


## Errors And Provider Fallthrough

New Plays receive typed tool errors. Existing published artifacts keep the error contract stored with their revision.

For a read waterfall, catch only `ProviderTransientError` and keep the final provider call loud. For structured diagnostics, narrow to `ToolExecutionError` and branch on its stable fields. Never branch on `error.message`.

A newly authored Play can explicitly retain legacy errors with `compatibility: { toolErrorSchemaVersion: 0 }` in its `definePlay` options. Use that only while migrating old message-based handling.

### `DeeplineError`

Base error class shared by the SDK and play runtime.

The global brand preserves `instanceof DeeplineError` when a bundled play
and the runtime load separate physical copies of this module.

Signature: `class DeeplineError extends Error`
#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Construct a Deepline error.<br /><br />SDK and runtime code construct these errors. Application and Play code<br />normally catches the public subclasses instead. | `message: string` - Human-readable failure summary.<br />`statusCode?: number` - HTTP status when one exists.<br />`code?: string` - Stable machine-readable code when one exists.<br />`details?: Record<string, unknown>` - Local diagnostic context; never a portable error contract. |  |
| `statusCode` | property | HTTP status when the failure crossed an HTTP boundary. |  | `number` |
| `code` | property | Stable machine-readable error code when one exists. |  | `string` |
| `details` | property | Local diagnostic context; not a portable error contract. |  | `Record<string, unknown>` |

### `ToolExecutionErrorOrigin`

The boundary responsible for a failed tool call.

Use `provider` to distinguish a provider answer from caller input and
Deepline infrastructure. `unknown` fails closed and must not trigger a
waterfall fallback.

Signature: `export type ToolExecutionErrorOrigin = | 'caller' | 'provider' | 'deepline' | 'unknown';`


### `ToolExecutionErrorCategory`

The stable reason family for a failed tool call.

Branch on this field only after narrowing to `ToolExecutionError`. Catch
`ProviderTransientError` when the policy is simply “try the next read
provider”; it is the safer and shorter waterfall contract.

Signature: `export type ToolExecutionErrorCategory = | 'validation' | 'authentication' | 'authorization' | 'rate_limit' | 'network' | 'upstream' | 'billing' | 'conflict' | 'internal' | 'unknown';`


### `ToolExecutionNetworkKind`

The transport failure observed when `category` is `network`.

This is `null` for failures that are not network failures.

Signature: `export type ToolExecutionNetworkKind = | 'timeout' | 'dns' | 'connect' | 'reset' | 'unavailable' | 'unknown';`


### `ToolExecutionNetworkScope`

The request boundary on which a network failure occurred.

`deepline_to_provider` is provider-side. Client and runtime scopes are
Deepline transport failures and never qualify as provider fallthrough.

Signature: `export type ToolExecutionNetworkScope = | 'client_to_deepline' | 'runtime_to_deepline' | 'deepline_to_provider';`


### `ProviderTransientErrorCategory`

Provider-owned failure categories that may fall through to another read
provider.

Signature: `export type ProviderTransientErrorCategory = | 'rate_limit' | 'network' | 'upstream';`


### `ToolExecutionFailureV1`

Portable version-1 `tool_error` payload.

This allowlisted shape crosses the API, runtime, and SDK boundaries.
`message` remains on the Error object and is deliberately not a policy
field.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `schemaVersion` | `typeof TOOL_EXECUTION_ERROR_SCHEMA_VERSION` | Yes | Payload version. |
| `toolId` | `string` | Yes | Public tool id passed to `tools.execute`. |
| `provider` | `string \| null` | Yes | Provider responsible for the operation, or `null`. |
| `operation` | `string \| null` | Yes | Provider operation name, or `null`. |
| `code` | `string \| null` | Yes | Stable machine-readable failure code, or `null`. |
| `origin` | `ToolExecutionErrorOrigin` | Yes | Boundary responsible for the failure. |
| `category` | `ToolExecutionErrorCategory` | Yes | Stable reason family. |
| `retryable` | `boolean` | Yes | Whether repeating the same semantic call is delivery-safe. |
| `statusCode` | `number \| null` | Yes | HTTP status when one exists, or `null`. |
| `requestId` | `string \| null` | Yes | Provider or Deepline request id, or `null`. |
| `retryAfterMs` | `number \| null` | Yes | Suggested same-call retry delay in milliseconds, or `null`. |
| `networkKind` | `ToolExecutionNetworkKind \| null` | Yes | Network failure kind, or `null`. |
| `networkScope` | `ToolExecutionNetworkScope \| null` | Yes | Network boundary that failed, or `null`. |


### `ToolExecutionErrorOptions`

Constructor input for a structured tool failure.

Deepline creates these values while decoding the versioned wire payload.
Customer code normally reads `ToolExecutionError` fields instead of
constructing an error.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `details` | `Record<string, unknown>` | No | Local diagnostic context inherited from DeeplineError. This is not part of<br />the portable failure payload and is intentionally omitted by serialization. |


### `ToolExecutionError`

A failed `tools.execute` call with stable, allowlisted provenance.

`retryable` means Deepline's delivery/idempotency contract says it is safe
to repeat the same semantic call. It does not describe durable receipt
repairability and does not make arbitrary side-effecting fallbacks safe.

In a Play, catch `ProviderTransientError` to continue a read waterfall and
let every other `ToolExecutionError` remain loud. In an SDK client, catch
this base class when you need structured diagnostics for every tool failure.

Signature: `class ToolExecutionError extends DeeplineError`
#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Construct a structured tool error.<br /><br />Deepline constructs this from the versioned `tool_error` payload.<br />Application and Play code should catch it rather than create it. | `message: string`<br />`options: ToolExecutionErrorOptions` |  |
| `toolId` | property | Public tool id passed to `tools.execute`. |  | `string` |
| `provider` | property | Provider responsible for the operation, or `null` when unattributed. |  | `string \| null` |
| `operation` | property | Provider operation name, or `null` when unavailable. |  | `string \| null` |
| `origin` | property | Boundary responsible for the failure. |  | `ToolExecutionErrorOrigin` |
| `category` | property | Stable reason family for policy and diagnostics. |  | `ToolExecutionErrorCategory` |
| `retryable` | property | Whether repeating the same semantic call is delivery-safe.<br /><br />This does not mean the error may be ignored. Waterfall fallthrough is<br />represented by `ProviderTransientError`. |  | `boolean` |
| `requestId` | property | Provider or Deepline request id, or `null` when unavailable. |  | `string \| null` |
| `retryAfterMs` | property | Suggested same-call retry delay in milliseconds, or `null`. |  | `number \| null` |
| `networkKind` | property | Network failure kind, or `null` for non-network failures. |  | `ToolExecutionNetworkKind \| null` |
| `networkScope` | property | Network boundary that failed, or `null` for non-network failures. |  | `ToolExecutionNetworkScope \| null` |

### `ProviderTransientError`

A provider-owned transient failure that is safe to handle as an empty
waterfall leg. Validation, auth, billing, Deepline, and unknown failures
never satisfy this type.

`retryable` remains independent: it says whether the same semantic call may
be repeated safely. Falling through to a different read provider depends on
this class, not on `retryable`.

Signature: `class ProviderTransientError extends ToolExecutionError`
#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Constructed by Deepline when a provider-owned transient failure arrives. | `message: string`<br />`options: Omit<ToolExecutionErrorOptions, 'origin' \| 'category'> & { category: ProviderTransientErrorCategory; }` |  |
| `origin` | property | Provider attribution is guaranteed for this subtype. |  | `"provider"` |
| `category` | property | Provider failure category that made this error eligible for fallthrough. |  | `ProviderTransientErrorCategory` |

### `AuthError`

Thrown when the API rejects the request due to an invalid or missing API key.

This maps to HTTP 401 responses. HTTP 403 means the caller was authenticated
but lacks permission, so the SDK preserves the server's API error instead.
The SDK never retries auth errors —
they fail immediately.

Fix: run `deepline auth register` to obtain a valid key, or pass one via
the `apiKey` option or `DEEPLINE_API_KEY` environment variable.

Signature: `class AuthError extends DeeplineError`
#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Constructed by the SDK when Deepline rejects the caller's credentials. | `message?: string` |  |

### `RateLimitError`

Thrown when the API returns HTTP 429 (Too Many Requests).

The SDK retries rate-limited requests automatically up to `maxRetries` times
with exponential backoff. This error is only thrown when all retries are exhausted.

Use `RateLimitError.retryAfterMs` to implement your own backoff if needed.

Signature: `class RateLimitError extends DeeplineError`
#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Constructed by the SDK after exhausting HTTP-level rate-limit retries. | `retryAfterMs?: number`<br />`message?: string` |  |
| `retryAfterMs` | property | Milliseconds to wait before retrying, from the `Retry-After` response header. Defaults to 5000. |  | `number` |

### `ToolRateLimitError`

Tool-specific 429 preserving both historical RateLimitError catches and the
structured ToolExecutionError ontology. JavaScript has one prototype chain,
so this class extends RateLimitError and carries ToolExecutionError's stable
cross-bundle brand.

This class appears in external SDK calls after HTTP 429 retries are
exhausted. It also satisfies `instanceof ToolExecutionError` and, for a
provider-owned rate limit, `instanceof ProviderTransientError`. Authored
Plays should use `ProviderTransientError`; they do not need this
compatibility class.

Signature: `class ToolRateLimitError extends RateLimitError`
#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Constructed by the SDK after a structured tool HTTP 429. | `message: string`<br />`options: ToolExecutionErrorOptions` |  |
| `toolId` | property | Public tool id passed to `tools.execute`. |  | `string` |
| `provider` | property | Provider responsible for the operation, or `null`. |  | `string \| null` |
| `operation` | property | Provider operation name, or `null`. |  | `string \| null` |
| `code` | property | Stable machine-readable failure code when one exists. |  | `string \| undefined` |
| `origin` | property | Boundary responsible for the failure. |  | `ToolExecutionError['origin']` |
| `category` | property | Stable reason family for policy and diagnostics. |  | `ToolExecutionError['category']` |
| `retryable` | property | Whether repeating the same semantic call is delivery-safe. |  | `boolean` |
| `requestId` | property | Provider or Deepline request id, or `null`. |  | `string \| null` |
| `networkKind` | property | Network failure kind, or `null` for non-network failures. |  | `ToolExecutionError['networkKind']` |
| `networkScope` | property | Network boundary that failed, or `null` for non-network failures. |  | `ToolExecutionError['networkScope']` |

### `ConfigError`

Thrown when the SDK cannot resolve a valid configuration.

Most commonly: no API key found in any of the resolution sources
(explicit option, environment variable, CLI env files).

Signature: `class ConfigError extends DeeplineError`
#### Members

| Member | Kind | Purpose | Parameters | Returns / type |
|---|---|---|---|---|
| `constructor` | constructor | Construct a local SDK configuration failure. | `message: string` |  |

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
| `listProviders` | method | List discoverable providers without requiring a local plugin catalog. | `options?: { changed?: boolean; }` | `Promise<ProviderDefinition[]>` |
| `searchTools` | method | Search available tools using Deepline's ranked backend search.<br /><br />This is the same discovery surface used by the CLI: it ranks across<br />tool metadata, categories, agent guidance, and input schema fields. | `options?: ToolSearchOptions` | `Promise<ToolSearchResult>` |
| `getTool` | method | Get detailed metadata for a single tool.<br /><br />Returns everything from `ToolDefinition` plus pricing info, sample<br />inputs/outputs, failure modes, and cost estimates. | `toolId: string` - Tool identifier (e.g. `"dropleads_search_people"`) | `Promise<ToolMetadata>` |
| `describeModel` | method | Describe a Deepline Agent model and its provider-specific option surface.<br /><br />Combines live AI Gateway model metadata with Deepline's generated AI SDK<br />provider option registry so agents can construct `providerOptions`<br />payloads before executing `deeplineagent`.<br /><br />The returned option schemas describe accepted provider option shapes, not<br />guaranteed support for every model. Runtime AI SDK/Gateway errors remain<br />authoritative for model-gated values. | `model: string` - Gateway model id such as `"openai/gpt-5.5"` | `Promise<DeeplineAgentModelDescription>` |
| `quoteInferenceTool` | method | Quote dynamic AI inference pricing for a concrete payload.<br /><br />The result separates a planning estimate from a proven authorization<br />maximum and contains Deepline credits only. | `toolId: 'ai_inference' \| 'deeplineagent'`<br />`payload: Record<string, unknown>` | `Promise<InferenceQuote>` |
| `executeTool` | method | Execute a tool and return the standard execution envelope.<br /><br />The `toolResponse.raw` field contains the raw tool response.<br />`toolResponse.meta` contains tool/provider metadata.<br />Top-level fields such as `status`, `job_id`, and `billing` describe the<br />Deepline execution envelope. | `toolId: string`<br />`input: Record<string, unknown>`<br />`options?: ExecuteToolRawOptions` | `Promise<ToolExecution<TData, TMeta>>` |
| `executeToolRaw` | method | Back-compatible alias for `executeTool`.<br /><br />Retained for callers that still use the older raw naming while the response<br />envelope remains the same. | `toolId: string`<br />`input: Record<string, unknown>`<br />`options?: ExecuteToolRawOptions` | `Promise<ToolExecution<TData, TMeta>>` |
| `queryCustomerDb` | method | Run a bounded SQL query against the current mutable customer database.<br /><br />This query is not scoped to one play run. Use `client.runs` export actions<br />when the caller needs the rows produced by a specific run. | `input: { sql: string; maxRows?: number; }` | `Promise<CustomerDbQueryResult>` |
| `repairIngestionStorage` | method | Re-establish this workspace's tenant storage contract: role/DB connect<br />grants plus materialized table grants. Org-admin only. Use when a run fails<br />with WORKSPACE_STORAGE_NOT_READY. | `input?: { provider?: string; }` | `Promise<IngestionStorageRepairResult>` |
| `startPlayRun` | method | Start a play run.<br /><br />Internal/advanced primitive. For normal callers, prefer the public<br />entrypoints: the CLI, `Deepline.connect`, `submitPlay`,<br />or `runPlay`.<br /><br />Supported invocation surfaces intentionally share this same run contract:<br />`deepline plays run`, repo scripts such as `bun run deepline -- plays run`,<br />SDK context calls like `Deepline.connect().play(name).run()`, and direct<br />`POST /api/v2/plays/run` calls all return a workflow/run id. The completed<br />output is always retrievable from `getPlayStatus(runId).result` (or from<br />`PlayJob.get()` for SDK context calls). Execution logs live under<br />`progress.logs`; they are not part of the user output object. | `request: StartPlayRunRequest` - Play run configuration (name, code, input, etc.) | `Promise<PlayRunStart>` |
| `startPlayRunStream` | method | Start a play run and stream live runtime events from the same request.<br /><br />Use this when a caller wants low-level event handling instead of submitting<br />first and then connecting to `streamPlayRunEvents(runId)`. | `request: StartPlayRunRequest` - Play run configuration.<br />`options?: { signal?: AbortSignal }` - Optional streaming options. | `AsyncGenerator<PlayLiveEvent>` |
| `registerPlayArtifact` | method | Register a bundled play artifact.<br /><br />Internal/advanced primitive used by packaging flows. Public callers should<br />prefer the CLI, `submitPlay`, or `runPlay`. | `input: { name: string; sourceCode: string; sourceFiles?: Record<string, string>; description?: string; artifact: Record<string, unknown>; compilerManifest?: PlayCompilerManifest; publish?: boolean; ownerType?: 'org' \| 'deepline'; scope?: 'org' \| 'system'; userId?: string; }` | `Promise<{ success?: boolean; name?: string; artifactStorageKey: string; artifactMetadata?: Record<string, unknown> \| null; staticPipeline?: unknown; definitionId?: string \| null; revisionId?: string \| null; version?: number \| null; liveVersion?: number \| null; triggerMetadata?: unknown; triggerBindings?: unknown; }>` |
| `registerPlayArtifacts` | method | Register multiple bundled play artifacts in one request.<br /><br />Used by packaging and prebuilt publication flows. Each artifact is compiled<br />first when a compiler manifest is not already supplied. | `artifacts: Array<{ name: string; sourceCode: string; sourceFiles?: Record<string, string>; description?: string; artifact: Record<string, unknown>; compilerManifest?: PlayCompilerManifest; publish?: boolean; ownerType?: 'org' \| 'deepline'; scope?: 'org' \| 'system'; userId?: string; }>` | `Promise<{ success: boolean; artifacts: Array<{ success?: boolean; name?: string; artifactStorageKey: string; artifactMetadata?: Record<string, unknown> \| null; staticPipeline?: unknown; definitionId?: string \| null; revisionId?: string \| null; version?: number \| null; liveVersion?: number \| null; triggerMetadata?: unknown; triggerBindings?: unknown; }>; }>` |
| `compilePlayManifest` | method | Compile a bundled play artifact into the server-side compiler manifest.<br /><br />The manifest records imports, trigger bindings, static pipeline shape, and<br />runtime metadata needed before a play artifact can be checked, registered,<br />or run. | `input: { name: string; sourceCode: string; sourceFiles?: Record<string, string>; artifact: Record<string, unknown>; importedPlayDependencies?: PlayCompilerManifest[]; }` | `Promise<PlayCompilerManifest>` |
| `checkPlayArtifact` | method | Check a bundled play artifact against the server's current play compiler.<br /><br />Unlike `registerPlayArtifact`, this does not store the artifact,<br />publish a revision, or start a run. It is the authoritative cloud validation<br />path used by `deepline plays check`. | `input: { name?: string; sourceCode: string; sourceFiles?: Record<string, string>; description?: string; artifact: Record<string, unknown>; exportName?: string \| null; integrationMode?: 'live' \| 'eval_stub' \| 'fixture'; importedPlays?: Array<{ playName?: string \| null; sourceCode: string; sourcePath?: string \| null; }>; }` | `Promise<PlayCheckResult>` |
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
| `getRunInput` | method | Get the exact original input retained for a run. This is intentionally separate from status. | `runId: string` | `Promise<{ runId: string; input: Record<string, unknown> \| unknown[]; bytes: number; sha256: string \| null; replayedFromRunId: string \| null; }>` |
| `rerun` | method | Start a fresh run from a prior run's retained input and pinned revision. | `runId: string` | `Promise<{ runId: string; replayedFromRunId: string; revisionId: string \| null; status: string; next: { inspect: string; input: string }; }>` |
| `getRunLogs` | method | Fetch persisted logs for a run using the public runs resource model.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs logs <run-id> --limit 200 --json<br />``` | `runId: string`<br />`options?: RunsLogsOptions` | `Promise<RunsLogsResult>` |
| `getPlaySheetRows` | method | Export persisted runtime-sheet rows for a play dataset/table namespace.<br /><br />This is the SDK form of exporting `ctx.dataset(...).run()` output for a<br />specific play and optional run id. | `input: { playName: string; tableNamespace: string; runId?: string; limit?: number; offset?: number; rowMode?: 'output' \| 'all'; }` | `Promise<PlaySheetRowsResult>` |
| `stopRun` | method | Stop a run by id using the public runs resource model.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs stop <run-id> --reason "stale lock" --json<br />``` | `runId: string`<br />`options?: { reason?: string }` | `Promise<StopPlayRunResult>` |
| `stopAllRuns` | method | Stop every active run visible to the current workspace.<br /><br />This is the SDK equivalent of:<br /><br />```bash<br />deepline runs stop-all --reason "stale lock" --json<br />```<br /><br />Use this when a failed parent run left child or waiting runs active and you<br />need to clear the workspace run-slot state without knowing each run id. | `options?: { reason?: string; }` | `Promise<StopAllPlayRunsResult>` |
| `listPlays` | method | List callable plays visible to the workspace.<br /><br />Pass `origin: "prebuilt"` for Deepline-managed prebuilts or<br />`origin: "owned"` for org-owned plays. | `options?: { origin?: 'prebuilt' \| 'owned'; grep?: string; grepMode?: 'all' \| 'any' \| 'phrase'; categories?: string \| string[]; includeToolCategories?: boolean; includeArchived?: boolean; }` | `Promise<PlayListItem[]>` |
| `setPlayPinned` | method | Set whether an org-owned Play sorts before unpinned Plays. | `playName: string`<br />`pinned: boolean` | `Promise<{ name: string; pinned: boolean }>` |
| `getNotificationSettings` | method | Read product-notification destinations, subscriptions, event catalog, and DLQ health. |  | `Promise<ProductNotificationSettings>` |
| `connectNotificationSlack` | method | Start the Slack OAuth flow required by product notifications. | `options?: { successUrl?: string; failureUrl?: string; }` | `Promise<{ ok: boolean; redirect_url: string }>` |
| `listNotificationSlackChannels` | method | List Slack channels visible to the connected Deepline Slack app. | `query?: string` | `Promise<{ identity: { teamId: string; teamName?: string }; channels: Array<{ id: string; name: string; isPrivate: boolean }>; }>` |
| `setNotificationSlack` | method | Select the Slack channel used for product notifications. | `channel: string` | `Promise<unknown>` |
| `testNotificationSlack` | method | Send one synchronous test ping and return Slack's delivery result. |  | `Promise<{ ok: boolean; deliveryId: string; state: string; message: string; }>` |
| `disableNotificationSlack` | method | Disable Slack product notifications without deleting the OAuth connection. |  | `Promise<unknown>` |
| `setNotificationSubscriptions` | method | Enable or disable event IDs from the server-provided notification catalog. | `eventTypes: string[]`<br />`enabled: boolean` | `Promise<unknown>` |
| `listNotificationDlq` | method | List exhausted deliveries. Dead-lettered messages never replay automatically. | `limit?: number` | `Promise<unknown>` |
| `getNotificationDlqDelivery` | method | Inspect one exhausted notification delivery. | `deliveryId: string` | `Promise<unknown>` |
| `updateNotificationDlqDelivery` | method | Explicitly retry or archive one dead-lettered notification delivery. | `deliveryId: string`<br />`action: 'retry' \| 'archive'` | `Promise<unknown>` |
| `getNotifications` | method | List the workspace's named notification rules. |  | `Promise<ProductNotificationSettings>` |
| `listNotificationChannels` | method | List Slack channels available to an already-connected Slack integration. | `query?: string` | `Promise<{ identity: { teamId: string; teamName?: string }; channels: Array<{ id: string; name: string; isPrivate: boolean }>; }>` |
| `createNotification` | method | Create a named notification routed through an existing provider integration. | `input: { name: string; provider: 'slack'; channel: string; eventTypes: string[]; }` | `Promise<unknown>` |
| `updateNotification` | method | Update a notification's target, event selection, or enabled state. | `notificationId: string`<br />`input: \| { enabled: boolean } \| { name: string; channel: string; eventTypes: string[] }` | `Promise<unknown>` |
| `testNotification` | method | Send a validation ping to one notification. | `notificationId: string` | `Promise<{ ok: boolean; deliveryId: string; state: string; message: string; }>` |
| `deleteNotification` | method | Archive one notification without touching its provider integration. | `notificationId: string` | `Promise<{ deleted: boolean; id: string }>` |
| `searchPlays` | method | Search callable plays and return compact play descriptions.<br /><br />Prebuilt plays are preferred by default because they have maintained<br />contracts and stable run behavior. | `options: { query: string; compact?: boolean; scope?: 'prebuilt' \| 'owned' \| 'all'; }` | `Promise<PlayDescription[]>` |
| `getPlay` | method | Get the full definition and state of a named play.<br /><br />Returns the play's revision state (draft, live), recent runs,<br />sheet processing summary, and database URL. | `name: string` - Play name<br />`options?: { source?: 'working' \| 'live' \| `version:${number}` }` | `Promise<PlayDetail>` |
| `describePlay` | method | Get a normalized play description suitable for agents and CLIs.<br /><br />The description includes runnable examples, input/output summaries, clone<br />guidance, revision state, and latest run metadata when available. | `name: string`<br />`options?: { compact?: boolean }` | `Promise<PlayDescription>` |
| `clearPlayHistory` | method | Clear run history and durable sheet/result data for a play without deleting<br />the play definition or revisions. | `name: string`<br />`request?: ClearPlayHistoryRequest` | `Promise<ClearPlayHistoryResult>` |
| `listPlayVersions` | method | List saved versions for a named play.<br /><br />Returns immutable revision snapshots newest-first, including the revision<br />id needed for exact-version runs and live-version switching. | `name: string` - Play name<br />`options?: { full?: boolean }` | `Promise<PlayRevisionSummary[]>` |
| `publishPlayVersion` | method | Make a play revision live.<br /><br />When `revisionId` is omitted, the current working revision becomes live.<br />The live version is what executes when the play is run by name without<br />specifying an explicit revision. | `name: string` - Play name<br />`request?: PublishPlayVersionRequest` - Optional explicit revision to make live | `Promise<PublishPlayVersionResult>` |
| `deletePlay` | method | Move an org-owned play to Trash. This disables its active triggers while<br />retaining its revisions and run history so it can be restored. Deepline<br />prebuilt plays are read-only. | `name: string` | `Promise<DeletePlayResult>` |
| `restorePlay` | method | Restore an org-owned play that was previously moved to Trash. | `name: string` | `Promise<RestorePlayResult>` |
| `getSharePage` | method | Current share status for a play: the public page (if any), the published<br />copy, and the revision picker. Read-only. | `name: string`<br />`options?: { revisionId?: string }` | `Promise<SharePageStatus>` |
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
| `getTargetBillingPlans` | method | List the reviewed target plans and whether new acquisition is enabled. |  | `Promise<TargetBillingPlansResult>` |
| `getTargetBillingStatus` | method | Read the workspace's normalized target plan, payment, and balance state. |  | `Promise<TargetBillingStatusResult>` |
| `purchaseTargetBillingCredits` | method | Purchase target-billing credits through the durable commercial operation<br />flow. The caller supplies an idempotency key for safe retries. | `options: { credits: number; idempotencyKey: string; }` | `Promise<TargetBillingMutationResult>` |
| `transitionTargetBillingPlan` | method | Start, change, cancel, or restore a target plan through one idempotent<br />commercial operation. | `options: TargetBillingPlanTransitionOptions` | `Promise<TargetBillingMutationResult>` |
| `createTargetBillingPortalSession` | method | Create a Stripe-hosted portal session for payment recovery and invoices. |  | `Promise<{ url: string }>` |
| `health` | method | Check API connectivity and server health. |  | `Promise<{ status: string; version?: string; status_banner?: { message: string; updatedAt: number; }; }>` |

### `client.runs`

Public runs namespace exposed as `client.runs`.

This namespace mirrors the canonical `/api/v2/runs` resource family and is
the preferred low-level surface for polling, streaming, stopping, reading
logs, and exporting durable dataset rows.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `get` | `(runId: string, options?: RunsGetOptions) => Promise<PlayStatus>` | Yes | Get current run status by public run id. |
| `input` | `(runId: string) => Promise<{ runId: string; input: Record<string, unknown> \| unknown[]; bytes: number; sha256: string \| null; replayedFromRunId: string \| null; }>` | Yes | Explicitly read the retained original input (may include customer data). |
| `rerun` | `(runId: string) => Promise<{ runId: string; replayedFromRunId: string; revisionId: string \| null; status: string; next: { inspect: string; input: string }; }>` | Yes | Start a fresh run from a prior run's retained input and pinned revision. |
| `list` | `(options: RunsListOptions) => Promise<PlayRunListItem[]>` | Yes | List runs for one play, optionally filtered by status. |
| `tail` | `(runId: string, options?: RunsTailOptions) => Promise<PlayStatus>` | Yes | Stream run events and return the latest/terminal run status. |
| `logs` | `(runId: string, options?: RunsLogsOptions) => Promise<RunsLogsResult>` | Yes | Fetch persisted log lines for a run. |
| `exportDatasetRows` | `(input: { playName: string; tableNamespace: string; runId?: string; limit?: number; offset?: number; rowMode?: 'output' \| 'all'; }) => Promise<PlaySheetRowsResult>` | Yes | Export persisted rows for a runtime-sheet dataset/table namespace. |
| `stop` | `( runId: string, options?: { reason?: string }, ) => Promise<StopPlayRunResult>` | Yes | Stop a running/waiting run. |
| `stopAll` | `(options?: { reason?: string }) => Promise<StopAllPlayRunsResult>` | Yes | Stop active runs across the current workspace. |


### `client.billing`

Public billing namespace exposed as `client.billing`.

Carries plans, subscription state, cancellation, and invoice/receipt history
so CLI commands and programmatic callers share one surface.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `topUp` | `(options: { credits: number; idempotencyKey?: string; }) => Promise<BillingTopUpResult>` | Yes | Charge the saved payment method and add Deepline credits to the active workspace. |
| `plans` | `() => Promise<BillingPlansResult>` | Yes | Published plans plus the plan you are on ("what plans exist and what am I on"). |
| `subscription` | `{ status: () => Promise<BillingSubscriptionStatus>; cancel: (options?: { undo?: boolean; }) => Promise<BillingSubscriptionCancelResult>; }` | Yes |  |
| `invoices` | `{ list: (options?: { limit?: number }) => Promise<BillingInvoicesResult>; }` | Yes |  |
| `targetPlans` | `() => Promise<TargetBillingPlansResult>` | Yes | Metronome-authored target catalog and current Contract projection. |
| `targetStatus` | `() => Promise<TargetBillingStatusResult>` | Yes | Normalized target billing state. |
| `purchaseCredits` | `(options: { credits: number; idempotencyKey: string; }) => Promise<TargetBillingMutationResult>` | Yes | Buy Deepline credits through a payment-gated Metronome commit. |
| `transitionPlan` | `( options: TargetBillingPlanTransitionOptions, ) => Promise<TargetBillingMutationResult>` | Yes | Start, change, cancel, or undo a target plan transition. |
| `portalSession` | `() => Promise<{ url: string }>` | Yes | Create a Stripe-hosted billing Portal session. |


### `client.monitors`

Public monitors namespace exposed as `client.monitors`.

Mirrors the /api/v2/monitors resource family so the monitors CLI and
programmatic callers share one product surface — every `deepline monitors`
verb maps to a method here. Monitors are fully expressible as SDK code: author
a definition with `defineMonitor`, then check/deploy/list/get/update/
delete/reactivate through this namespace.

#### Fields

| Name | Type | Required | Description |
|---|---|---:|---|
| `status` | `() => Promise<MonitorsAccessStatus>` | Yes | Whether the current workspace can use monitors (`{ has_access, reason }`). |
| `available` | `( toolIdOrOptions?: string \| (MonitorsAvailableOptions & { tool?: string }), options?: MonitorsAvailableOptions, ) => Promise<MonitorsAvailableResult>` | Yes | The deployable monitor tools catalog. Call with no tool id for the list, or<br />with a tool id (positional or `{ tool }`) to describe one tool's full<br />payload/stream contract. |
| `check` | `(definition: MonitorDefinition) => Promise<MonitorCheckResult>` | Yes | Validate a monitor definition without deploying it (no spend). |
| `deploy` | `( definition: MonitorDefinition, options?: { dryRun?: boolean }, ) => Promise<MonitorDeployResult>` | Yes | Deploy a monitor from a definition. May spend Deepline credits. |
| `list` | `(options?: MonitorsListOptions) => Promise<MonitorsListResult>` | Yes | List deployed monitors (active by default). `includeConsumers` requires a limit of 20 or fewer. |
| `get` | `(key: string) => Promise<MonitorDetail>` | Yes | Fetch one deployed monitor by public key with bounded current listener health. |
| `test` | `( key: string, payload: Record<string, unknown>, options?: { validationOnly?: boolean; dispatch?: boolean }, ) => Promise<MonitorTestResult>` | Yes | Test a deployed monitor. `validationOnly` safely verifies the callback<br />envelope; omitted options preserve the historic full-ingestion behavior. |
| `validate` | `(key: string) => Promise<MonitorValidateResult>` | Yes |  |
| `dependents` | `(key: string) => Promise<MonitorDependents>` | Yes | List the published plays depending on one monitor's output streams. |
| `update` | `( key: string, patch: Record<string, unknown>, ) => Promise<MonitorUpdateResult>` | Yes | Update a deployed monitor by public key. |
| `delete` | `( key: string, options?: { localOnly?: boolean; dryRun?: boolean }, ) => Promise<MonitorDeleteResult>` | Yes | Delete a deployed monitor by public key. Deprovisions the upstream provider<br />resource unless `localOnly` is set. `dryRun` returns the delete plan. |
| `reactivate` | `( key: string, options?: { dryRun?: boolean }, ) => Promise<MonitorReactivateResult>` | Yes | Reactivate a disabled monitor. `dryRun` returns the reactivation cost. |
