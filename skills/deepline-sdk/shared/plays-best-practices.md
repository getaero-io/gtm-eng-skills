# Plays best practices

Use this when authoring, copying, debugging, or customizing Deepline `*.play.ts` files. If the task is a one-shot call to a prebuilt play whose input contract already fits, use the CLI directly and do not write a play.

## Table of contents

- Start with prebuilts
- Customize by copying
- Iterate on one play file
- Idempotency and replay
- Design inputs for CLI use
- Normalize CSV columns up front
- Compose row programs
- SDK primitive reference
- Common authoring traps

## Start with prebuilts

Search before writing. Prebuilt plays encode provider order, validation rules, retry behavior, and output conventions that are easy to lose in a custom rewrite.

```bash
deepline plays search email --json
deepline plays describe <play-name-from-search> --json
deepline plays run <play-name-from-search> --input '{"csv":"leads.csv"}' --watch
```

Treat play names in this skill as starting hints. The registry changes; the CLI is the source of truth. If the prebuilt input contract fits, invoke it directly. If only CSV headers differ, pass column aliases rather than copying the play.

```bash
deepline plays run <play-name-from-search> \
  --csv leads.csv \
  --columns.first_name "First Name" \
  --columns.last_name "Last Name" \
  --columns.domain "Company Domain" \
  --watch
```

For CSV plays, pass the CSV path and any column aliases through the play's declared field names. `--csv leads.csv` means `input.csv`; `--columns.first_name "First Name"` means `input.columns.first_name`. Inspect the contract with `deepline plays describe <play> --json` before choosing `csv`, `file`, or another file input name.

## Customize by copying

Copy a prebuilt when the workflow is almost right but needs a real semantic change: provider order, validation policy, derived columns, filtering, output shape, or an added stage. Do not copy a prebuilt just to rename CSV headers; use `columns`.

Use this sequence when the user says to customize, compose, extend, tweak, add a stage, change validation, or use a prebuilt as a starting point:

```bash
deepline plays search <task> --json
deepline plays describe <play-name-from-search> --json
deepline plays get <play-name-from-search> --source --out ./my-play.play.ts
deepline plays check ./my-play.play.ts
```

`describe` tells you whether a direct run or column mapping is enough. `get --source --out` is the materialization step for real edits: it writes the current TypeScript source to a local play file so you can preserve the existing provider order, input contract, CSV handling, logs, and output shape while changing only the behavior the user asked to change.

`--source` is raw TypeScript. Do not parse `play.sourceCode` out of JSON, scrape `tool-results`, or pipe through Python just to copy a template. If a `*.play.ts` file already exists in the working directory after `plays get`, edit that file directly or copy it to the final play name.

If the exact source-export shape differs, run `deepline plays get --help`; `get` is the detailed surface for source and revisions. After copying:

- Keep the copied play running unchanged first, then make one semantic edit at a time.
- Rename the play intentionally; the play name participates in persisted identity.
- Preserve `ctx.csv`, `ctx.map`, stable map keys, required columns, and useful `ctx.log` calls.
- Keep provider evidence fields unless the user explicitly wants a display-only export.
- Run by file path while iterating; only `set-live` once stable.

```bash
deepline plays run ./my-play.play.ts --csv leads.csv --watch
deepline plays set-live ./my-play.play.ts
deepline plays run my-play --csv leads.csv --watch
```

## Iterate on one play file

Edit one local play file in place instead of creating `-v2`, `-fixed`, or `-final` variants. Deepline's durable cache makes repeated local runs cheap when names and keys stay stable; unchanged rows and steps can reuse prior results.

Run checks before spending provider credits:

```bash
deepline plays check ./my-play.play.ts
deepline plays run ./my-play.play.ts --csv pilot.csv --watch
```

Use a one-row pilot CSV first for provider waterfalls and other slow paid work:

```bash
head -2 leads.csv > pilot.csv
deepline plays run ./my-play.play.ts --csv pilot.csv --watch
```

Move to 2 rows only when the second row exercises a different branch you need to verify and there is enough time budget. Passing `--input '{"rows":"0:1"}'` does not filter a CSV unless the play code implements that option.

Use `ctx.log(...)` for long-running stages. Logs are visible through `--watch`, `runs tail`, and run history, which lets an agent tell whether the play is still searching, validating, retrying, or stuck.

## Idempotency and replay

Play authoring is not normal scripting. Plays run on a durable execution engine; the play body can re-execute from the beginning during worker restart, retry, or workflow replay. Calls routed through `ctx.*` replay from cached history. Calls outside `ctx.*` run again with fresh values and can corrupt the workflow.

Treat these names as durable identity:

- **Play name** — separates one workflow's persisted state from another's.
- **Map key** — identifies a logical table or stage inside the play.
- **Row key** — identifies a row within a map. Prefer stable business identifiers such as `domain`, `email`, or `linkedin_url` over array index when available.
- **Step name** — becomes output-column identity and part of the trace.

Stable names make reruns recoverable and avoid double-billing. Renaming play names, map keys, or step names is a migration: it can create new tables, hide old columns, or recompute work. When the semantics truly changed, that may be correct. When only the code got tidier, keep the durable names stable.

To intentionally recompute completed durable work, make the identity change explicit by changing the relevant play name, map key, row key, or step name. `deepline plays run --force` supersedes an active run for the same play; it does not clear completed row history or force already-satisfied rows to execute again. There is currently no `deepline plays clear-history` CLI command.

Every `ctx.map` key in one play must be unique. Reusing a key is ambiguous for persistence and fails registration.

## Design inputs for CLI use

Make common inputs first-class and typed. A CSV-backed play should usually expose `file` and optional `columns`:

```typescript
import { definePlay } from 'deepline';
import type { ColumnMap } from 'deepline';

type PersonRow = {
  first_name: string;
  last_name: string;
  domain: string;
  company_name?: string;
  linkedin_url?: string;
};

export default definePlay(
  'name-and-domain-email',
  async (
    ctx,
    input: { csv: string; columns?: ColumnMap<PersonRow> },
  ) => {
    const rows = await ctx.csv<PersonRow>(input.csv, {
      columns: {
        first_name: 'FIRST_NAME',
        last_name: 'LAST_NAME',
        domain: 'COMPANY_DOMAIN',
        company_name: 'COMPANY_NAME',
        linkedin_url: 'LINKEDIN_URL',
        ...input.columns,
      },
      required: ['first_name', 'last_name', 'domain'],
    });

    const enriched = await ctx
      .map('email_waterfall', rows)
      .step('email', async (row, rowCtx) => {
        return rowCtx.waterfall('person_to_email', {
          first_name: row.first_name,
          last_name: row.last_name,
          domain: row.domain,
        });
      })
      .run({ description: 'Resolve work emails from name and domain.' });

    return { rows: enriched };
  },
);
```

Dotted CLI flags map onto nested input fields:

```bash
deepline plays run ./name-and-domain-email.play.ts \
  --csv leads.csv \
  --columns.first_name "First Name" \
  --columns.last_name "Last Name" \
  --columns.domain Website \
  --watch
```

Avoid `any` and vague wrapper types when the input shape can be stated inline. Small named aliases like `PersonRow` are useful because they document the data contract and keep `ctx.csv` and `ColumnMap<PersonRow>` typed.

## Normalize CSV columns up front

CSV header differences are data-mapping problems, not reasons to rewrite a play. Use `ctx.csv(input.csv, { columns, required })` to project source headers into canonical field names once, then write the rest of the play against those canonical fields.

The projection is for code access. Persisted output should preserve the user's original CSV headers and append derived columns. That keeps lineage visible: reviewers can see the source data they uploaded next to the fields the play produced.

Fail early when required canonical fields cannot be resolved. A loud "missing `domain` column" before provider calls is cheaper than running a waterfall over undefined payloads.

## Compose row programs

When scalar and CSV/batch modes share provider logic, put that logic in a reusable row-level helper. The registered scalar play and the CSV play can both call the same row program.

Batch code should not usually call the registered scalar play once per row. That gives perfect semantic parity, but adds child-play overhead, makes traces harder to read, and can block provider-level batching or rate scheduling. Use `ctx.runPlay` for true workflow composition boundaries; use a local helper when you just want to share row logic.

Use `ctx.waterfall` when provider order is the customization point. Use direct `ctx.tools.execute` when one provider call is exactly the step you need. Use prebuilt plays when the business-level behavior already exists.

## SDK primitive reference

### `definePlay(name, handler, bindings?)`

A play is a default export from a `*.play.ts` file:

```typescript
export default definePlay(
  'lead-email-lookup',
  async (ctx, input: { file: string }) => {
    return { ok: true };
  },
);
```

The name is the slug used by `deepline plays run <name>`, `deepline plays set-live`, and `ctx.runPlay`. Bindings can add cron or webhook triggers when the play is live.

### `ctx.tools.execute(key, toolId, input, options)`

Calls one provider tool with a stable idempotency key and a required description:

```typescript
const company = await ctx.tools.execute(
  'company_search',
  '<tool-id>',
  {
    domain: row.domain,
  },
  {
    description: 'Look up company details by domain.',
  },
);

const providerPayload = company.result.data;
const upstreamStatus = company.result.meta?.status;
const normalizedDomain = company.extracted.domain?.value;
```

Find tool IDs with `deepline tools search <category> --json` and confirm payloads with `deepline tools describe <id> --json`.
The shape matches `deepline tools execute --json`: `result.data` is the provider payload, `result.meta` is provider/upstream metadata, and `extracted` contains Deepline-normalized semantic values with source paths.

### `ctx.runPlay(key, playRef, input, options)`

Invokes another registered play or file-backed play as a child workflow:

```typescript
const result = await ctx.runPlay(
  'email_waterfall',
  '<play-name>',
  {
    first_name: row.first_name,
    last_name: row.last_name,
    domain: row.domain,
  },
  {
    description: 'Resolve work email from name and domain.',
  },
);
```

The first argument is a stable child-call key. Use this for real composition boundaries, not for sharing a helper inside the same play.

### `ctx.map(key, items).step(name, resolver).run(options)`

Fans out across rows and records each step as a durable column:

```typescript
const enriched = await ctx
  .map('companies', rows)
  .step('company', (row, rowCtx) =>
    rowCtx.tools.execute(
      'company_search',
      '<tool-id>',
      { domain: row.domain },
      {
        description: 'Look up company details by domain.',
      },
    ),
  )
  .run({ description: 'Enrich companies.' });
```

`items` can be an array, async iterable, or `PlayDataset` from `ctx.csv` or another `ctx.map`. Returns a `PlayDataset` of original rows plus new columns. Pass it to another `ctx.map` for a later stage; do not treat it like an array.

### `ctx.csv(path, options?)`

Loads a staged CSV as a `PlayDataset`:

```typescript
const rows = await ctx.csv<PersonRow>(input.csv, {
  columns: input.columns,
  required: ['first_name', 'last_name', 'domain'],
});
```

`path` is required. Invoke file-backed plays with the matching input flag, for example `deepline plays run my.play.ts --csv leads.csv --watch`, and call `ctx.csv(input.csv)`. `ctx.csv()` with no argument is invalid.

### `ctx.waterfall(...)`

Runs provider attempts in order and returns the first useful hit or `null`. Prefer a prebuilt play when one covers the full business pattern; use `ctx.waterfall` when the provider order or stop condition is the reason for the custom play.

### `ctx.fetch(key, url, init)`

Durable HTTP. Same purpose as `fetch`, but cached by workflow history so replay sees the same response. Prefer provider tools for normal GTM API work because they handle auth, retries, rate limits, and cost accounting.

### `ctx.step(id, fn)`

Memoizes a one-off operation that has no dedicated `ctx.*` method:

```typescript
const requestId = await ctx.step('request-id', () => crypto.randomUUID());
```

Use stable IDs. Do not derive IDs from timestamps or random values.

### `ctx.log(message)` and `ctx.sleep(ms)`

`ctx.log` emits progress visible through `--watch`, `runs tail`, and run history. `ctx.sleep` creates a durable timer for backoff or coordination.

### `ctx.input`

Read-only access to the raw play input. Prefer a typed `input` parameter when possible.

### `Deepline.connect()`

External client for app code that calls Deepline from outside a play:

```typescript
import { Deepline } from 'deepline';

const client = await Deepline.connect();
const job = await client.play('<play-name>').run({ csv: 'leads.csv' });
const result = await job.get();
```

Do not use `Deepline.connect()` inside a play body. The runtime `ctx` is the durable surface; the external client is for scripts, route handlers, and applications.

## Common authoring traps

- **Calling live names without discovery.** Names rot. Search and describe before invoking.
- **Copying a prebuilt to rename headers.** Use `columns`; copying is for semantic changes.
- **Reading CSVs with `fs`.** Staged CSVs are runtime inputs. Use `ctx.csv(input.csv)` or the file field your play declares.
- **Mismatching CSV field names.** `--csv leads.csv` sets `input.csv`; reserved run flags such as `--file` keep their command meaning, so use `--input '{"file":"leads.csv"}'` for `input.file`. Make the invocation and `ctx.csv(input.<field>)` agree.
- **Iterating a dataset manually.** `PlayDataset` is a durable dataset handle. Use `ctx.map`.
- **Reusing a map key.** Each `ctx.map` stage needs a unique durable key.
- **Using raw `fetch` or `Date.now()` in the play body.** Route effects through `ctx.fetch`, `ctx.step`, or another `ctx.*` primitive.
- **Calling a play via `ctx.tools.execute`.** Tools and plays live in separate namespaces. Use `ctx.runPlay` for plays.
- **Using long play names.** Persisted table names include play and map names; keep them short and meaningful.
- **Hiding provider misses.** Return nulls or explicit misses. Do not pattern-complete contacts from model memory.
