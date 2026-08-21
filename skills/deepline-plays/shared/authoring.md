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
- Handle provider failures
- Parallelism
- Author the run diagram
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
- Keep the top-level `description` concise because it becomes the primary title shown in the UI. Use a 2–6 word outcome phrase, at most 48 characters, with no trailing period (for example, `Refresh provider status`). Do not recap the request or implementation. Tool, step, and dataset descriptions can remain explanatory.
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
          input: {
            first_name: row.first_name,
            last_name: row.last_name,
            domain: row.domain,
          },
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
      {
        first_name: row.first_name,
        last_name: row.last_name,
        domain: row.domain,
      },
      { description: 'Resolve a verified work email.' },
    );
    return result.email ?? null;
  })
  .run({ key: 'domain', description: 'Find work emails per row.' });
```

When follow-up fields depend on a `ctx.runPlay(...)` result, put them in a second `ctx.dataset` stage with a distinct key — do not read a just-produced `fields.email` value in the same stage. Use `ctx.tools.execute` when one provider call is exactly the step you need; for ordered provider fallback, write explicit `steps(...).step(...).return(...)` so each attempt is visible and cached. Do not call a prebuilt play through `ctx.tools.execute` — plays and tools are separate namespaces; use `ctx.runPlay`.

## Handle provider failures

New Plays receive typed tool failures. A read waterfall needs one catch:

```
import { ProviderTransientError } from 'deepline';

try {
  return await primaryProvider();
} catch (error) {
  if (!(error instanceof ProviderTransientError)) throw error;
}
return fallbackProvider();
```

`ProviderTransientError` means a provider-owned rate limit, network failure, or
upstream failure. It does not include bad input, missing credentials, billing,
Deepline infrastructure, or unknown failures. Keep the final provider outside
the catch so an exhausted waterfall fails loudly.

Do not match `error.message`, catch every `ToolExecutionError`, or use
`retryable` as a fallthrough flag. `retryable` only says the same semantic call
is safe to repeat. See the [SDK reference](https://deepline.com/docs/sdk-v2/sdk-reference#errors-and-provider-fallthrough)
for the full field contract and the explicit legacy-contract option.

## Parallelism: ordinary promises, inside the play

There is no `ctx.parallel` primitive — use normal `Promise.all` over independent `ctx.tools.execute` / `ctx.runPlay` calls. Each durable operation still needs a stable, distinct key, and the runtime still owns provider rate limits, retries, receipts, and billing — submitting promises concurrently does not bypass any of those controls, it just stops you paying wall-clock for work that never depended on each other.

```typescript
const [company, contact] = await Promise.all([
  ctx.tools.execute({
    id: 'company',
    tool: 'company_lookup',
    input: { domain: input.domain },
    description: 'Look up company details.',
  }),
  ctx.tools.execute({
    id: 'contact',
    tool: 'contact_lookup',
    input: { email: input.email },
    description: 'Look up contact details.',
  }),
]);
```

Choose the shape by intent:

- **Parallel** when the calls are independent and you want ALL results: multi-provider corroboration, route comparison on a golden set, multi-channel fanout (email + phone + LinkedIn at once), gathering signals for one row from several sources.
- **Sequential** when order IS the economics: a waterfall stops on first hit precisely so later legs only spend on earlier misses — parallelizing it pays every leg on every row.
- For large collections, bound in-flight promises; use `ctx.dataset(...).withColumn(...).run()` when the output should materialize as a Runtime Sheet.

This is also why multi-provider trials belong **inside the play**, not in a shell loop of `deepline tools execute` probes: only play code gets durability, receipts, governed concurrency, and a sheet. A one-off `tools execute` is for sniffing a contract; the moment you are trying several providers, that is a play.

## Author the run diagram

**Access-gated beta.** Authored diagrams and the cell trace they power are on by account, not by play. Outside the beta a `@mermaid` block is an inert comment: nothing parses it, no diagram attaches, the canvas stays the inferred graph, `plays check` reports none of the `docflow_*` rules below, and a malformed diagram costs nothing because it is never read. So the whole section is optional. Write the play first; add the diagram only when you know the account has access.

To find out: run `plays check` on a play that has a block. Access shows up as `docflow_*` issues and the per-export diagram echo. Silence means no access — do not read that as a clean diagram. If you need it, ask the Deepline team.

A play's dashboard canvas can be authored, not just inferred. Add a `/** @mermaid */` flowchart block above the imports and the compiler renders it as the run canvas instead of the auto-generated graph; a `// @mermaid-node <id> ...` comment binds a diagram node to real code so it shows live status and run values.

Diagrams are opt-in. Comments stay ordinary TypeScript prose unless they use the
explicit Mermaid forms above, so write human-facing strings normally:

```ts
const readyMessage = `Put ${input.title} through to send-ready.`;
// Put ${input.title} through to send-ready.
```

Neither ordinary prose nor a comment beginning with `put` is Docflow syntax.

For a new or materially reworked Play in a beta account, start with a small authored diagram. Draw the business story, not every statement: input rows, the decisions or provider cascade that matter, durable datasets, child Plays, and the result. Omit the block when the inferred graph is already clearer. `.skills/deepline-plays/plays/research-kernel.example.play.ts` is the current worked example.

Start from this shape and replace the nouns before adding detail:

```ts
/** @mermaid
 * flowchart TD
 * input[("Input rows")] --> work["Enrich each row"]
 * work --> output["Return enriched rows"]
 */
```

**One block per exported play.** A block names the play in the header — `/** @mermaid contact-to-phone-waterfall` — the same place `// @mermaid-node <id>` puts its target. An export name (`scalar`, `batch`) works too, but the play's own name is the one a reader recognises. An unnamed block means the default export, so a one-play file needs no name. A file exporting a scalar and a batch play carries two blocks, one each, both above the imports; `plays check` checks every exported play and reports per export. Naming an export the file does not define fails the check with the names it does define, and two blocks claiming one export fails too. Node ids must be unique inside one block. Separate named exports may reuse natural ids such as `input` and `output`; bindings resolve against the enclosing `definePlay` handler.

**A binding resolves by its `out:` name, not by the line it sits on.** Put each `// @mermaid-node` comment directly above the statement it names — inside the handler, above the whole `const rows = await ctx` statement for a chained `.dataset(...)`, or above the `.withColumn(...)` line for a column — and `out:` must name what that statement produces. When the name and the position disagree, `plays check` errors `docflow_binding_drift` and tells you both, rather than silently binding the wrong statement.

Every node declares a `type:` (default `"action"` when omitted). The shape in the diagram must match the `type:`:

| Mermaid         | `type:`      | Use for                                  |
| --------------- | ------------ | ---------------------------------------- |
| `id["Label"]`   | `action`     | a step, column, or tool call (default)   |
| `id{"Label?"}`  | `decision`   | a branch with `yes` and `no` edge labels |
| `id[("Label")]` | `dataset`    | a `ctx.dataset` or `ctx.csv` row source  |
| `id[["Label"]]` | `play`       | a `ctx.runPlay` child Play               |
| `id(["Label"])` | `conceptual` | presentation-only; never binds to code   |

Any other `type:` fails `plays check`, and the error lists the valid set — lean on it.

A `play` node's `out:` names the value the child call produces, same as an action. The card shows the child play's real id under your label — resolved from the `ctx.runPlay` call, not from what you typed — and carries live status like every other bound node. Draw one whenever a step is another play: a reader who cannot see the second run cannot tell which run failed. `plays check` errors if a `play` node names work no `ctx.runPlay` produces, and warns (`docflow_child_play_undrawn`) if the code runs a child play the diagram never shows.

The binding rules the checker enforces (four traps):

- **`out:` names the value the statement produces, not the node id.** For a `ctx.dataset`/`ctx.csv` statement, `out:"<the const you assigned>"`; for a column, `out:"<the withColumn name>"`; for a `ctx.runPlay`, the value the call produces.
- **`$output` marks the terminal only.** Exactly one node uses `out:"$output"`, on the final returned value. Every other node names a real variable/column.
- **Draw every runtime dataset, and account for every column it computes.** A missing `ctx.dataset`/`ctx.csv` errors `docflow_dataset_unrepresented`. A `subgraph` wired to a dataset is that dataset's per-row loop, and a diagrammed play must account for every column that dataset computes. A column is accounted for two ways, and only two: a member of the region names it (`out:"<column>"`, and one member may name several, comma-separated), or the run call declares it out of the picture.

```ts
.run({
  description: 'Resolve a personal email for each contact row.',
  // Flat projections of the result the "waterfall" node already draws.
  undrawnColumns: ['personal_email', 'email_source', 'miss_reason'],
})
```

Anything else errors `docflow_dataset_column_undrawn`, naming the column, the construct that produces it, and both remedies. A column drawn by a node that sits outside every region is reported too: per-row work belongs in the loop. Declaring a column the dataset does not compute, or one a node already draws, errors `docflow_undrawn_declaration_invalid`. `plays check` echoes the declared list under the dataset every run, so an opt-out is never invisible. Draw the work; declare the projections. A real waterfall computes 10–23 columns and most of them unpack one result object — draw the cascade, declare the unpacking. A member outside the row work errors `docflow_loop_foreign_step`; a loop touching two datasets errors `docflow_loop_ambiguous`.

- **A decision binds to the value that computes the branch** (`// @mermaid-node id type:"decision" out:"<the branch value>"`); its `yes`/`no` edges point at the follow-on nodes.

- **Say which arm the condition leads to** with `arm:"run"` on the node that arm points at (`// @mermaid-node tierOne out:"priority_tier" arm:"run"`). Your edge labels are prose — `"fit 65 or better"`, `"nicht gefunden"` — so without this the run trace reads the arms by draw order and marks the guess with a `*`. Annotate one arm only: a conditional is boolean, so the sibling resolves to `else` on its own. Optional, and a play without it is unaffected.

**Every box binds a statement, or says no statement runs it.** A diagram is a claim about the code: click a box and it answers with the tool it called, the columns it wrote, what this run did there. A box bound to nothing cannot answer, and the canvas cannot tell the two apart — so it renders a box plainly labelled `Hunter` as "this node has nothing configured".

When the work genuinely has no statement to point at — the legs live in another module, the providers are a list a loop walks, the box is the outcome of a branch rather than a step — declare it:

```
 * cascade --> answer(["Return the email and how it was found"])
 * class hunter,prospeo,answer sketch
```

`class <ids> sketch` is mermaid's own class statement, so the block stays a diagram any renderer can draw. A sketched box keeps its `type:` — a sketched decision is still a diamond — and loses only the promise that there is something to click into: it draws dashed and its panel says no statement in this play runs it. `plays check` fails on a box that is neither bound nor declared, and names both exits.

**The canvas draws your diagram and nothing else.** Every node, edge, region and label on it comes from your `@mermaid` block, in your words. Nothing reads your compiled code and adds boxes you did not write. So if a node says too little, the fix is a better diagram — not a hope that the UI will fill it in.

**A provider waterfall: one node, or a region of attempts.** Both are authored; pick by whether the attempts are worth reading one at a time.

A single `action` node over the `steps(...)` cascade — `out:"<the const you assigned>"` for `ctx.runSteps`, `out:"<the withColumn name>"` when the cascade fills a column — says "a cascade happens here" and carries how deep it is:

```
cascade["Find a mobile number"]   # node: 11 tries · 2 off
```

Those two numbers are the only thing the canvas adds, and they are facts about the node you drew — read from the compiled cascade, so they never go stale. The names of the attempts are not among them: your step ids are internal, and printing them would be the canvas inventing a list you never authored.

To show the attempts, draw them. A `subgraph` whose members are legs is a **waterfall region**; bind each member with `out:"<the step name>"` and label it for a reader:

```
subgraph cascade["Try each source until one returns a mobile"]
  dropleads["Dropleads · from LinkedIn"] --> forager["Forager · from email"]
  forager --> leadmagic["LeadMagic · from LinkedIn"]
end
```

The frame carries the same `11 tries · 2 off`, so drawing a subset stays honest — members may be a subset and there is no coverage warning, because a waterfall's later legs mostly never run. Good for a handful of attempts read in order; a sixteen-member region is taller than the rest of the diagram put together, so use the single node there.

A waterfall region shows **no live state**, and the trade is deliberate: a leg's statement is the shared `steps(...)` builder, so observing it would time the builder rather than the attempt. Leg cards carry position, provider, `off`, and a check on the leg this run's result named — never a status pill, and the frame never lights up the way a dataset loop's does. Want the run to move, use the single cascade node, which marks the answering leg by matching your result against the cascade's own step names: a play returning `source: 'hunter_email'` gets the mark, one that names nothing gets none. `plays check` errors `docflow_waterfall_region_invalid` when members span two cascades, or when a member's `out:` names no leg of this one (the error lists the valid step names).

**Malformed mermaid fails the check.** The block has to parse cleanly or the play does not compile — a diagram the parser has to guess at is a diagram that renders wrong, silently. `plays check` errors on a shape it does not know (your label would arrive with its own brackets attached), a shape that never closes, a `subgraph` without its `end`, an `end` without its `subgraph`, a line that is neither an edge nor a declaration, and an edge naming a node nothing ever declares. Each error names the node and quotes the line. Supported shapes: `[…]`, `[[…]]`, `[(…)]`, `([…])`, `{…}`, `{{…}}`, `((…))`, `[/…/]`, `[\…\]`, `[/…\]`, `[\…/]`, `>…]`.

Mermaid styling directives such as `style`, `classDef`, and `linkStyle` are accepted for source compatibility but are not rendered by the run canvas. `plays check` warns `docflow_directive_ignored`; express meaning through node labels, shapes, regions, and labeled edges instead.

**A node label names the thing; it never counts it.** Counts are live — the canvas prints the run's real row count on the node as a status pill, and the run storyline prints it again beside the output. A number typed into the label is a fourth copy that nothing updates, so it goes stale the first time someone passes a different input, and the node then argues with the pill directly above it:

```
seed[("8k seed rows")]     # the label says 8k, the pill says 10,000 rows,
                           # and the run was started with rows: 10000
seed[("Seed rows")]        # the label names the thing; the pill carries the count
```

That is a real case: a play defaulting to 8,000 rows, run at 10,000, showing "8k seed rows" under a "10,000 rows" pill. Name what the node IS — `"Seed rows"`, `"Probed rows"`, `"Qualified accounts"` — and let the runtime say how many. `plays check` warns `docflow_label_counts_rows` when a label carries a magnitude (`8k`, `10,000 rows`, `500 leads`); a digit that is part of a name (`"SOC 2 signals"`, `"Series B companies"`) is fine and is not flagged. The same rule applies to the play's `description`: describe what it does, not the size of one run's input.

Use human labels (`"Score fit"`, `"Probe attempt B"`), not `step2`. Reading dataset rows back into JS — to chain a second dataset, filter, or tally — is `await ds.materialize()` (or `.peek(n)` for a bounded preview); the `PlayDataset` handle is lazy, so `.rows`/`.toArray()`/array methods on it fail `plays check`.

## Common authoring traps

- **Calling live names without discovery.** Names rot. Search and describe before invoking.
- **Copying a prebuilt to rename headers.** Use `columns`; copying is for semantic changes.
- **Reading CSVs with `fs`.** Staged CSVs are runtime inputs. Use `ctx.csv(input.csv)` or the file field your play declares.
- **Mismatching CSV field names.** Make the invocation and `ctx.csv(input.<field>)` agree (`--csv leads.csv` sets `input.csv`); `ctx.csv()` with no argument is invalid. Reserved-flag collisions: see "input shape rejected" in `../references/debugging.md`.
- **Treating a dataset as a normal array.** `PlayDataset` is a durable handle. Pass it to `ctx.dataset` by default; use `count()`, `peek()`, or bounded `materialize(limit)` only when you intentionally need a small in-memory slice.
- **Reusing a dataset key.** Each `ctx.dataset` stage needs a unique durable key.
- **Using raw `fetch` or `Date.now()` in the play body.** Route effects through `ctx.fetch`, `ctx.step`, or another `ctx.*` primitive. Read play input from the handler's second argument, not `ctx.input`/`ctx.args`/`ctx.params`.
- **Calling a play via `ctx.tools.execute`.** Use `ctx.runPlay` for plays.
- **Using a long top-level play description.** The play `description` is the primary UI title. Keep it to a 2–6 word outcome phrase no longer than 48 characters; put implementation detail in the play body and step descriptions.
- **Using long play names.** Persisted table names include play and map names; keep them short and meaningful.
- **Hiding provider misses.** Return nulls or explicit misses. Do not pattern-complete contacts from model memory.

## Exit

- A run failed, stalled, or a column came back empty or misshapen → `../references/debugging.md`.
