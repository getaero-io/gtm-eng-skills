# Authoring plays

Use this when writing, copying, debugging, or customizing Deepline `*.play.ts` files. Deepline work runs through plays: a fitting prebuilt for canonical one-shots, or a local scratchpad play for anything that discovers, enriches, filters, scores, validates, or exports rows. Direct `tools execute` calls are probes, not the script that produces the final artifact.

Exact SDK signatures (`definePlay`, `ctx.*`, `PlayDataset`, tool-result shapes, `Deepline.connect`) live in the hosted reference — https://deepline.com/docs/sdk-v2/sdk-reference. HTTP invocation contracts — https://deepline.com/docs/sdk-v2/api-reference. This doc is the how-to; those are the exact contracts.

## Table of contents

- Start with prebuilts
- Customize by copying
- Iterate on one play file
- Idempotency and replay
- Design inputs for CLI use
- Compose row programs
- Parallelism
- Common authoring traps

## Start with prebuilts

Search before writing. Prebuilts encode provider order, validation rules, retry behavior, and output conventions that are easy to lose in a rewrite. Use `plays search` first for workflow/outcome tasks (contact discovery, email waterfalls, phone enrichment, LinkedIn resolution, job-change detection, engagers, CSV enrichment); use `tools search` only after no play fits or when a custom play needs one atomic provider operation.

```bash
deepline plays search email --json
deepline plays describe <play-name-from-search> --json
deepline plays run <play-name-from-search> --input '{"csv":"leads.csv"}' --watch
```

If the input contract fits, invoke directly. If only CSV headers differ, pass column aliases rather than copying — `--csv leads.csv` means `input.csv`, `--columns.first_name "First Name"` means `input.columns.first_name`. Inspect the contract with `deepline plays describe <play> --json` before choosing `csv`, `file`, or another file input name.

## Customize by copying

Copy a prebuilt only for a real semantic change: provider order, validation policy, derived columns, filtering, output shape, or an added stage. Do not copy to rename headers — use `columns`.

```bash
deepline plays search <task> --json
deepline plays describe <play-name-from-search> --json
deepline plays get <play-name-from-search> --source --out ./my-play.play.ts
deepline plays check ./my-play.play.ts
```

`get --source --out` writes the current TypeScript source to a local file so you preserve the existing provider order, input contract, CSV handling, logs, and output shape while changing only what the user asked for. `--source` is raw TypeScript — do not parse `play.sourceCode` out of JSON, scrape `tool-results`, or pipe through Python to copy a template. If the exact export shape differs, run `deepline plays get --help`. After copying:

- Keep the copied play running unchanged first, then make one semantic edit at a time.
- Rename the play intentionally; the play name participates in persisted identity.
- Preserve `ctx.csv`, `ctx.dataset`, stable dataset keys, required columns, useful `ctx.log` calls, and provider evidence fields.
- Run by file path while iterating; only `set-live` once stable.

```bash
deepline plays run ./my-play.play.ts --csv leads.csv --watch
deepline plays set-live ./my-play.play.ts
deepline plays run my-play --csv leads.csv --watch
```

## Iterate on one play file

Start the play early, while still discovering the workflow. A small scratchpad play with one provider call beats ten terminal probes plus a late rewrite: it gives each known-good step a durable identity, makes watch output inspectable, and lets the next run resume from completed work. Edit one file in place — no `-v2`, `-fixed`, `-final` variants. Deepline's durable cache makes repeated local runs cheap when names and keys stay stable; unchanged rows and steps reuse prior results.

```bash
deepline plays check ./my-play.play.ts
head -2 leads.csv > pilot.csv
deepline plays run ./my-play.play.ts --csv pilot.csv --watch
```

Move to 2 rows only when the second exercises a different branch you need to verify. Passing `--input '{"rows":"0:1"}'` does not filter a CSV unless the play code implements that option. Use `ctx.log(...)` for long stages — logs are visible through `--watch`, `runs tail`, and run history, so an agent can tell whether a play is searching, validating, retrying, or stuck.

When a run exposes an empty derived column or a wrong getter path, debug from persisted run tables, not direct tool previews. `tools describe` gives the declared contract and `tools execute` probes an isolated call; neither proves what a prior step serialized into that play's table. The first fix comes from a `deepline db query` row for the failed run:

```bash
deepline plays run ./my-play.play.ts --input '{...}' --watch
deepline runs get <run-id> --json
deepline db query --sql 'select * from "storage"."<run_table>" where _run_id = ... limit 20' --json
```

Use `top-level outputs` for scalar `ctx.step` / top-level `ctx.tools.execute` results; use `inspect rows` for `ctx.dataset` stages. Then edit the getter from the stored JSON row you actually queried.

## Idempotency and replay

Play authoring is not normal scripting. Plays run on a durable engine; the play body can re-execute from the beginning during worker restart, retry, or replay. Calls routed through `ctx.*` replay from cached history. Calls outside `ctx.*` run again with fresh values and corrupt the workflow.

Treat these as durable identity:

- **Play name** — separates one workflow's persisted state from another's.
- **Dataset key** — identifies a logical table/stage inside the play.
- **Row key** — identifies a row within a dataset. Prefer stable business identifiers (`domain`, `email`, `linkedin_url`) over array index.
- **Dataset column name** — becomes output-column identity and part of the trace.

Stable names make reruns recoverable and avoid double-billing. Renaming any of them is a migration: it can create new tables, hide old columns, or recompute work. When semantics truly changed, that may be correct; when only the code got tidier, keep the names stable. To intentionally recompute completed durable work, make the identity change explicit by changing the relevant name. `deepline plays run --force` supersedes an active run for the same play; it does not clear completed row history or force already-satisfied rows to execute again. There is no `deepline plays clear-history` command. Every `ctx.dataset` key in one play must be unique — reusing a key fails registration.

## Design inputs for CLI use

Make common inputs first-class and typed. A CSV-backed play exposes a file field and optional `columns`. Use `ctx.csv(input.csv, { columns, required })` to project source headers into canonical fields once, then write the play against canonical fields. The projection is for code access — persisted output preserves the user's original headers and appends derived columns, so lineage stays visible. Fail early when a required canonical field cannot be resolved: a loud "missing `domain` column" before provider calls is cheaper than a waterfall over undefined payloads.

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
  async (ctx, input: { csv: string; columns?: ColumnMap<PersonRow> }) => {
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
      .dataset('email_waterfall', rows)
      .withColumn('email', async (row, rowCtx) => {
        const result = await rowCtx.tools.execute({
          id: 'person_to_email',
          tool: '<provider-id>',
          input: { first_name: row.first_name, last_name: row.last_name, domain: row.domain },
          description: 'Resolve work email.',
        });
        return result.extractedValues.email?.get() ?? null;
      })
      .run({ description: 'Resolve work emails from name and domain.' });

    return { rows: enriched };
  },
  { description: 'Resolve work emails for a CSV of names and domains.' },
);
```

Dotted CLI flags map onto nested input fields: `--columns.first_name "First Name"` sets `input.columns.first_name`. Avoid `any` and vague wrapper types; small named aliases like `PersonRow` document the data contract and keep `ctx.csv` and `ColumnMap<PersonRow>` typed. Do not widen a tool input to `Record<string, string>` — the play checker cannot prove required schema keys are present after that widening.

## Compose row programs

When scalar and CSV/batch modes share provider logic, prefer the highest-level prebuilt that fits. If a batch prebuilt matches the input/output contract, run or copy it. If the business behavior exists only as a scalar prebuilt, call that scalar prebuilt inside `ctx.dataset` with `ctx.runPlay(...)` — better than reconstructing a provider waterfall from low-level tools, because the prebuilt already encodes provider order, fallbacks, normalization, and no-result semantics.

Use a stable step key inside the dataset; row identity comes from `ctx.dataset`, so the step key names the logical operation, not row data. The child play returns an object — extract the scalar so the column exports cleanly:

```typescript
const enriched = await ctx
  .dataset('email_waterfall', rows)
  .withColumn('email', async (row, rowCtx) => {
    const result = await rowCtx.runPlay<{ email: string | null }>(
      'name_domain_email',
      'prebuilt/name-and-domain-to-email-waterfall',
      { first_name: row.first_name, last_name: row.last_name, domain: row.domain },
      { description: 'Resolve a verified work email.' },
    );
    return result.email ?? null;
  })
  .run({ key: 'domain', description: 'Find work emails per row.' });
```

When follow-up fields depend on a `ctx.runPlay(...)` result, put them in a second `ctx.dataset` stage with a distinct key — do not read a just-produced `fields.email` value in the same stage. Use `ctx.tools.execute` when one provider call is exactly the step you need; for ordered provider fallback, write explicit `steps(...).step(...).return(...)` so each attempt is visible and cached. Do not call a prebuilt play through `ctx.tools.execute` — plays and tools are separate namespaces; use `ctx.runPlay`.

## Parallelism: ordinary promises, inside the play

There is no `ctx.parallel` primitive — use normal `Promise.all` over independent `ctx.tools.execute` / `ctx.runPlay` calls. Each durable operation still needs a stable, distinct key, and the runtime still owns provider rate limits, retries, receipts, and billing — submitting promises concurrently does not bypass any of those controls, it just stops you paying wall-clock for work that never depended on each other.

```typescript
const [company, contact] = await Promise.all([
  ctx.tools.execute({ id: 'company', tool: 'company_lookup', input: { domain: input.domain }, description: 'Look up company details.' }),
  ctx.tools.execute({ id: 'contact', tool: 'contact_lookup', input: { email: input.email }, description: 'Look up contact details.' }),
]);
```

Choose the shape by intent:

- **Parallel** when the calls are independent and you want ALL results: multi-provider corroboration, route comparison on a golden set, multi-channel fanout (email + phone + LinkedIn at once), gathering signals for one row from several sources.
- **Sequential** when order IS the economics: a waterfall stops on first hit precisely so later legs only spend on earlier misses — parallelizing it pays every leg on every row.
- For large collections, bound in-flight promises; use `ctx.dataset(...).withColumn(...).run()` when the output should materialize as a Runtime Sheet.

This is also why multi-provider trials belong **inside the play**, not in a shell loop of `deepline tools execute` probes: only play code gets durability, receipts, governed concurrency, and a sheet. A one-off `tools execute` is for sniffing a contract; the moment you are trying several providers, that is a play.

## Common authoring traps

- **Calling live names without discovery.** Names rot. Search and describe before invoking.
- **Copying a prebuilt to rename headers.** Use `columns`; copying is for semantic changes.
- **Reading CSVs with `fs`.** Staged CSVs are runtime inputs. Use `ctx.csv(input.csv)` or the file field your play declares.
- **Mismatching CSV field names.** Make the invocation and `ctx.csv(input.<field>)` agree (`--csv leads.csv` sets `input.csv`); `ctx.csv()` with no argument is invalid. Reserved-flag collisions: see "input shape rejected" in `../references/debugging.md`.
- **Treating a dataset as a normal array.** `PlayDataset` is a durable handle. Pass it to `ctx.dataset` by default; use `count()`, `peek()`, or bounded `materialize(limit)` only when you intentionally need a small in-memory slice.
- **Reusing a dataset key.** Each `ctx.dataset` stage needs a unique durable key.
- **Using raw `fetch` or `Date.now()` in the play body.** Route effects through `ctx.fetch`, `ctx.step`, or another `ctx.*` primitive. Read play input from the handler's second argument, not `ctx.input`/`ctx.args`/`ctx.params`.
- **Calling a play via `ctx.tools.execute`.** Use `ctx.runPlay` for plays.
- **Using long play names.** Persisted table names include play and map names; keep them short and meaningful.
- **Hiding provider misses.** Return nulls or explicit misses. Do not pattern-complete contacts from model memory.

## Exit

- A run failed, stalled, or a column came back empty or misshapen → `../references/debugging.md`.
