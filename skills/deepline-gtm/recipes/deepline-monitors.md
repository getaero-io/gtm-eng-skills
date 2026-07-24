---
name: deepline-monitors
description: 'ACCESS-GATED beta. Deepline Monitors are provider event feeds (job posts, email replies, funding, intent) that stream into your warehouse and trigger plays. Only use if you have monitor access: run `deepline monitors status` first; if it reports no access, do NOT use this recipe — ask a Deepline admin (Admin → Rollouts) for access.'
---

# Deepline Monitors

Monitors are **access-gated Deepline-native signal feeds**. In the dashboard
they are called **Monitors**. The customer launch currently includes the
Company Radar and Contact Radar only. A monitor provisions a Deepline-managed
feed; events land in a table in your Customer DB. There is **no run to kick
off** — a monitor streams as events arrive.

## Step 0 — access gate (do this first)

Monitors are an access-gated beta. **Before any other monitor command**, confirm
access:

```bash
deepline monitors status
```

- **You have access** → proceed.
- **No access** → **STOP.** Do not run any other monitor command. Tell the user
  monitor access is granted by a Deepline admin (Admin → Rollouts) and that they
  should request it there.

Anyone with a valid Deepline login can run the check; only the answer is gated.
`--json` returns `{ "has_access": boolean, "reason": string }` — branch on
`has_access`.

## Monitors vs plays

- **Monitor** = the upstream feed. It _produces_ a stream of
  provider events into a Customer DB table. It has no schedule and no manual run;
  it fires whenever the provider sends a webhook.
- **Play** = the logic that _reacts_. A play binds to the monitor's table with a
  `sqlListeners` trigger and runs inline when matching rows are written. Plays
  own all webhook/cron/manual/SQL-listener triggering; monitors do not run plays
  themselves — they just feed the table the play watches.

Reach for a monitor when the user wants to _continuously capture_ a provider's
events (email replies, new job postings, funding rounds, intent signals) into
their warehouse. Reach for a play when the user wants to _act on_ those events,
or for any on-demand or scheduled enrichment/sourcing task.

## Find monitor types and read their filters

Monitor types live on the `tools` surface, alongside every other capability.
Browse them, then read one type's exact filters + stream columns:

```bash
# Browse the monitor types you can deploy
deepline tools list --categories monitors
deepline tools search "company radar"

# Read the full contract for ONE type
deepline tools get deepline_native.company_radar
```

(`deepline monitors available [tool-id]` is a legacy alias for the same
discovery — prefer `tools`.)

The contract for a type gives you everything you need to deploy and to filter:

- **payload_schema** — the deploy-time filters you set in the monitor `payload`
  (typed: required fields, allowed values).
- **stream columns** — the row fields a play filters on with `sqlListeners.where`
  (the post-ingestion filter surface).
- **pricing** — Deepline credits per accepted event.
- **a deploy example** — `deepline monitors deploy '<def>'`.

A monitor type is deployed, not executed: `deepline tools execute <monitor-type>`
is rejected and points you at `deepline monitors deploy`.

## Command set

All commands accept `--json` (also automatic when stdout is piped).

| Command                                    | What it does                                                                                                                                                                                                                                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `deepline monitors status`                 | Report whether you have monitor access (`has_access`). **Run first.**                                                                                                                                                                                                                |
| `deepline tools list --categories monitors` / `tools get <tool-id>` | **Preferred** discovery. Browse the monitor types you can deploy, and read one type's payload schema + stream columns + pricing. See "Find monitor types and read their filters". |
| `deepline monitors available [tool-id]`    | Legacy alias of the `tools` discovery above (still works). Read-only; `--full` or a tool id for one type's full contract.                                                                                                                                                            |
| `deepline monitors check '<definition>'`   | Validate a monitor definition without deploying. Read-only; spends nothing. Also accepts `--file <path>` or `--file -` (stdin).                                                                                                                                                      |
| `deepline monitors deploy '<definition>'`  | Deploy a monitor (positional JSON, `--file <path>`, or `--file -`). Mutates workspace state and may spend Deepline credits. `--dry-run` shows the plan (validity, deploy cost in Deepline credits, existing monitors that may already cover the scope) without deploying.            |
| `deepline monitors list`                   | List the monitors you HAVE deployed. `--status active\|disabled\|all` (default `active`), `--limit`, `--cursor`, `--compact`. Response carries `total` (true registry count, not the page size), `returned`, `is_truncated`, and `next_cursor`. When `is_truncated` is true, page with `--cursor <next_cursor>` until it is false — see "Reuse before you deploy."                                                       |
| `deepline monitors get <key>`              | Show one deployed monitor by its public key. Read-only.                                                                                                                                                                                                                              |
| `deepline monitors update <key> '<patch>'` | Update a deployed monitor (`<patch>` is a JSON object of fields; also `--file`).                                                                                                                                                                                                     |
| `deepline monitors delete <key>`           | Delete a deployed monitor. Deprovisions the upstream resource by default; `--local-only` removes just the Deepline record. Prompts y/N in a terminal; non-interactive runs must pass `--yes`. `--dry-run` previews the plan.                                                         |
| `deepline monitors reactivate <key>`       | Reactivate a previously disabled deployed monitor. May spend Deepline credits; `--dry-run` shows the cost first.                                                                                                                                                                     |


## Monitors as code (SDK)

Monitors are **fully expressible as SDK code**, not CLI-only. The CLI is a thin
terminal surface over the same product model: every `deepline monitors` verb maps
to a `client.monitors.*` method, and monitor definitions have a typed authoring
helper, `defineMonitor`, that mirrors `definePlay`. Reach for the SDK when the
monitor lifecycle is part of a script, an agent loop, or a play repo — the same
access gate, endpoints, and pricing apply.

```ts
import { DeeplineClient, defineMonitor } from 'deepline';

const client = new DeeplineClient();

// Access gate first — same contract as `deepline monitors status`.
const access = await client.monitors.status(); // { has_access, reason }
if (!access.has_access) throw new Error(access.reason ?? 'No monitor access');

// Discover deployable monitor types (compact list, or describe one by id).
const catalog = await client.monitors.available(); // list mode
const radar = await client.monitors.available('deepline_native.company_radar');

// Author a typed definition (compile-time checked key/tool/payload/controls).
const monitor = defineMonitor({
  key: 'company-job-openings',
  tool: 'deepline_native.company_radar',
  name: 'Company job openings',
  payload: { domain: 'stripe.com', radar_type: 'company_job_openings' },
});

// Validate (no spend), preview the deploy plan, then deploy for real.
const check = await client.monitors.check(monitor);
const plan = await client.monitors.deploy(monitor, { dryRun: true });
const deployed = await client.monitors.deploy(monitor);

// Lifecycle — one method per CLI verb.
const list = await client.monitors.list({ status: 'all' }); // total/is_truncated/next_cursor
const detail = await client.monitors.get('company-job-openings');
const dependents = await client.monitors.dependents('company-job-openings');
await client.monitors.update('company-job-openings', { name: 'Renamed' });
await client.monitors.reactivate('company-job-openings', { dryRun: true });
await client.monitors.delete('company-job-openings', { localOnly: true, dryRun: true });
```

Every read-only method (`status`, `available`, `check`, `list`, `get`,
`dependents`, and any `{ dryRun: true }` mutation preview) is safe to call
without approval. `deploy`, `update`, `reactivate`, and `delete` mutate workspace
or provider state and can spend credits — get explicit approval first, exactly as
with the CLI (see "Get approval before mutations"). The reuse, shared-stream, and
per-event pricing rules below apply to the SDK path unchanged.

## Recover from errors

Monitor errors return an actionable next step — follow it before retrying.

- **Transient / not ready yet**: wait briefly, then retry the same read or check
  once.
- **Unknown monitor type**: re-browse the catalog
  (`deepline tools list --categories monitors`) and pick a valid tool id. A
  missing _deployed_ monitor instead → `deepline monitors list --status all`.
- **Validation errors**: fix every reported field and rerun `monitors check`.
- **Not enough credits**: report the required credits, balance, and shortfall,
  then stop and ask the user to add Deepline credits.
- **Settlement / cleanup failure**: inspect the monitor state and report that
  repair is needed; don't blindly repeat the mutation.

A monitor suspended for insufficient credits stays disabled until you explicitly
reactivate it. Ask the user to add credits, run `monitors reactivate <key>
--dry-run`, show the approval summary, and reactivate only after approval. While
suspended, connected plays do not run.

## Workflow

1. Run `status`.
2. Run `tools list --categories monitors` and `tools get <type>` to read filters,
   stream columns, and pricing (see "Find monitor types and read their filters").
3. Run `monitors list --status all` and `monitors get <key>` to inspect reuse and
   dependents.
4. Compare the monitor with a scheduled play over provider actions; ask the user
   when the cost/scope tradeoff is material.
5. Run `check`, then the mutation's built-in dry-run when one exists.
6. Show the approval summary below and obtain explicit approval.
7. Execute the approved mutation.
8. Run `get` to verify definition, billing, streams, and dependent plays.

**Reuse before you deploy.** `deepline monitors deploy` re-provisions an upstream
provider feed and spends credits. Before deploying, run
`deepline monitors list --status all` and check whether a monitor already
**covers your need**: same `tool`, watching the same scope. If a matching monitor
exists, do NOT deploy another — a play binds to the shared per-tool **stream**,
and may react to rows from every monitor feeding it. Reuse the existing monitor
and add a `sqlListeners.where` filter when the play needs narrower behavior. Do
not deploy another monitor expecting it to create an isolated play channel. A
disabled-but-matching monitor → `deepline monitors reactivate <key>`, not a
fresh deploy.

> **The reuse check must see the WHOLE registry, or it is worthless.** The list
> response reports `total` (the true registry count for the status filter),
> `returned`, and `is_truncated`. If `is_truncated` is `true`, you are looking at
> a partial page — a "no matching monitor" conclusion off a truncated page is how
> a duplicate paid monitor gets deployed onto an already-covered stream. Either
> raise `--limit` above `total`, or page with the returned `next_cursor`
> (`deepline monitors list --status all --cursor <next_cursor> --json`) until
> `is_truncated` is `false` and `next_cursor` is `null`. Only then is "no match"
> trustworthy.

## Shared streams and downstream blast radius

A deployed monitor is not an isolated trigger channel. It writes provider events
into a shared Customer DB stream/table. Public `sqlListeners` bindings subscribe
to a `tool` and `stream`, not to one monitor key, so a play may react to rows from
every monitor feeding that stream. Deploying another monitor on the same stream
does not create an isolated channel for its events.

Before creating, updating, disabling, reactivating, or deleting a monitor:

1. Read its output streams with `deepline tools get <tool-id> --json` (type-level
   `streams[]`) or `monitors get <key> --json` (a deployed instance).
2. Run `monitors list --status all --json` and inspect other monitors using the
   same tool and stream.
3. Inspect the dependent published plays returned by `monitors get`.
4. Explain whether the mutation will add rows, stop rows, or change which rows
   enter the shared table.
5. Explain the resulting spend and downstream behavior, then obtain approval
   when the change can affect another consumer.

Use `sqlListeners.where` when a dependent play needs narrower behavior and the
stream row schema exposes a suitable field such as domain, campaign, event type,
or account id. This filter controls whether that play wakes; it does not prevent
the monitor from ingesting the row. Example:
`where: { after: { event_type: { eq: 'reply_received' } } }`.

The dependent-play list is not a complete dependency graph. It identifies
published Deepline plays, but arbitrary SQL queries, dashboards, exports, and
external warehouse jobs may also consume the table. Describe reported plays as
known dependents and state that other table consumers may exist.

## Choose scope and ingestion strategy

A monitor's provider payload filters events before Deepline receives them.
`sqlListeners.where` and enrichment inside a play filter or qualify rows only
after ingestion.

> **Per-event pricing callout:** Every event accepted by an event-priced monitor
> can consume Deepline credits. Filtering, enrichment, dedupe, or rejection
> after ingestion changes downstream behavior, not the upstream event charge.

| Strategy                             | Best fit                                                                                                                         | Price and data tradeoff                                                                                                                                                                               |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Narrow provider monitor              | One known use case, expensive events, or strict data minimization                                                                | Lower volume and higher precision, but may miss events needed by another play. The monitor may not expose every desired filter.                                                                       |
| Broad monitor + play filtering       | Several stated use cases share the feed, or events are cheap enough to retain for later use                                      | Better recall and reuse with higher event exposure; apply the per-event pricing callout above.                                                                                                        |
| Scheduled play over provider actions | The action catalog has materially better filters than the monitor, or the user wants periodic snapshots instead of an event feed | Can avoid broad continuous ingestion, but each scheduled search, page, and enrichment can cost credits and may repeat old results. Use incremental date/cursor filters when the action supports them. |

A cron is not automatically cheaper. Compare expected monitor event volume with
the scheduled action's frequency, pagination, duplicate work, and follow-up
enrichment. `net_new` output or a downstream dedupe protects the destination;
it does not prove the provider call was free.

When the request names only one monitor use case, do not invent future reuse.
If broad versus narrow scope materially changes spend, latency, recall, or data
retention, explain the options and ask which the user prefers. A useful question
is: “Should this feed be narrow for this play, or broader so other plays can
reuse it? Broader scope improves recall but can increase per-event charges.”
When the user already named multiple use cases, or an existing monitor covers
them, recommend the shared broader feed and state the price consequence.

## Get approval before mutations

Run `status`, `tools list`/`tools get` (type discovery), `monitors list`,
`monitors get`, `check`, and dependency inspection without approval because they
are read-only. Creating, updating, reactivating,
or deleting a monitor changes workspace or provider state and can spend credits.
Show the final scope and selected pricing basis. For deploy, reactivate, and
delete, also show the built-in dry-run result. Update has no dry-run, so use the
read-only planning sequence below. Then get the user's explicit approval before
the mutation. A request to design or create a monitor is not the final approval:
ask again after the concrete cost and scope are known.

Use this approval summary instead of freeform prose:

```text
Monitor mutation approval
- Scope: <provider filters and payload; say whether this is broader or narrower>
- Streams/tables: <tool.stream -> Customer DB table>
- Pricing basis: <deploy, reactivation, per accepted event, or recurring; Deepline credits only>
- Expected exposure: <known one-time cost and/or expected event volume; state unknowns>
- Reuse candidates: <matching monitor keys, or none found>
- Known dependents: <published plays and intended behavior for each>
- Unknown-consumer warning: Other SQL queries, dashboards, exports, or warehouse jobs may read these shared tables.
- Dry-run/check: <result, or "update has no dry-run; full merged definition passed check">

Approve this exact monitor and dependent-play mutation plan? (yes/no)
```

Before updating an existing monitor:

1. Run `deepline monitors get <key> --json` to read the current definition,
   selected price, billing state, outputs, and dependent published plays.
2. Merge the requested patch into that full definition locally, then run
   `deepline monitors check '<full-definition>' --json`. `check` validates the
   definition and selected pricing; it does not simulate the provider-side
   update.
3. Show the exact old/new definition diff. Explain whether the change broadens
   or narrows ingestion and how that changes charges or missing-event risk.
4. For each dependent play, say whether it should keep the old behavior, adopt
   the new scope, or needs user direction. Do not silently make one choice for
   every dependent.
5. If a play must preserve the old restriction, prepare and publish its
   equivalent `sqlListeners.where` change before broadening the monitor. This
   preserves play behavior; apply the per-event pricing callout above when
   explaining spend.
6. Ask once for approval of the combined monitor and play mutation plan. After
   approval, pass only the intended patch to `monitors update`, execute any
   approved play edits in the stated order, and verify with `monitors get` plus
   the live play bindings.

Removing a provider filter broadens the feed and expected exposure; apply the
per-event pricing callout above. Narrowing the provider filter may need no play
edit, but dependent plays can stop receiving events; that loss still needs
explicit approval.

## When to reach for a monitor

- Continuously capturing an event feed: reply-received events on a campaign, new
  job postings for a company set, funding/intent signals for target accounts.
- The value is the _ongoing stream_, not a one-time pull. For a one-time pull,
  use a normal enrichment/sourcing tool or play instead.
- You want a play to fire the moment a provider event lands (bind a play's
  `sqlListeners` trigger to the monitor's table).

## Monitor definition shape

A definition is a single JSON object:

```json
{
  "key": "company-job-openings",
  "tool": "deepline_native.company_radar",
  "name": "Company job openings",
  "payload": {
    "domain": "stripe.com",
    "radar_type": "company_job_openings"
  },
  "controls": {}
}
```

- `key` — public monitor instance id (you reference it in `get`/`update`/`delete`).
- `tool` — a live Deepline-native tool id. Get the valid ids and each
  `payload_schema` from `deepline tools list --categories monitors` /
  `deepline tools get <tool-id>`.
- `payload` — tool-specific; must match that tool's `payload_schema`.
- `name` — optional human label. `controls` — optional Deepline lifecycle metadata.

The same object is what `defineMonitor({ ... })` returns (typed) and what
`client.monitors.check`/`deploy` accept — the CLI JSON and the SDK definition are
one shape. See "Monitors as code (SDK)".

## Build a play on top of a monitor

The monitor captures a provider's events into a Customer DB table; a play reacts
to each new row. A play subscribes with a `sqlListeners` trigger:

```ts
sqlListeners: [
  {
    id: 'company-job-openings',
    tool: 'deepline_native.company_radar',
    stream: 'company_job_openings',
    operations: ['INSERT'],
    where: { after: { domain: { eq: 'stripe.com' } } },
  },
];
```

1. `deepline tools get <tool-id>` lists, per output **stream**, the `stream` key
   you bind to, the Customer DB **table**, and the typed **row columns** you
   filter on. Bind to a data stream (kind `event`/`signal`), not one marked
   `[binding metadata]`.
2. Reuse before you deploy (see above). Deploy only when nothing covers your scope.
3. Author the play with the `sqlListeners` trigger (or start from
   `deepline plays bootstrap monitor-triggered`). Validate with
   `deepline plays check <file.play.ts>`, then `deepline plays publish`. The play
   then runs inline whenever the monitor writes a matching row — no schedule, no
   polling.

If the play calls `query_customer_db`, send one SQL statement per tool call.
Multiline SQL and one trailing semicolon are valid; multiple statements in one
call are not. Prefer a single idempotent `INSERT ... ON CONFLICT` or
`INSERT ... SELECT ... WHERE NOT EXISTS` over `DELETE` followed by `INSERT`, and
include every required `NOT NULL` column. Query `information_schema.columns` in
a separate call before writing when the table contract is unknown.

## Spend

Only report **Deepline** credit spend. Read the live `tools get <type>`,
`check`, and `get` pricing fields instead of assuming every monitor bills the
same way. A
monitor can charge on deploy/reactivation, on each accepted provider event, or
on a recurring renewal. Event volume therefore matters for event-priced
monitors; apply the canonical per-event pricing callout in **Choose scope and
ingestion strategy**. Provider cost basis, balances, and exchange rates are
internal and must never be shown.
