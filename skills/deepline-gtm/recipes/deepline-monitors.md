---
name: deepline-monitors
description: 'ACCESS-GATED beta. Deepline Monitors are provider event feeds (job posts, email replies, funding, intent) that stream into your warehouse and trigger plays. Only use if you have monitor access: run `deepline monitors status` first; if it reports no access, do NOT use this recipe — every command returns monitor_access_required. Ask a Deepline admin (Admin → Rollouts) for access.'
---

# Deepline Monitors

Monitors are **access-gated Deepline-native signal feeds**. In the dashboard
they are called **Monitors**. The customer launch currently includes the
Company Radar and Contact Radar only. A monitor provisions a Deepline-managed
feed; events land in a table in your Customer DB. There is **no run to kick
off** — a monitor streams as events arrive.

## Step 0 — access gate (do this first)

Monitors are a production rollout-gated beta. Local and preview runtimes admit
every authenticated actor; production admits Deepline/GetAero email domains and
the admin-managed email rollout. **Before any other monitor command**, run:

```bash
deepline monitors status
```

- Exit code `0` and `✓ You have access to Deepline Monitors` → proceed.
- Exit code `1` / `✗ No access` → **STOP.** Do NOT run `available`, `check`,
  `deploy`, `list`, or any other monitor command — each returns a
  `monitor_access_required` error. In production, tell the user access is
  granted by a Deepline admin via **Admin → Rollouts** and that they should
  request it there. Other non-zero exits are auth, configuration, or server
  failures and must be diagnosed by their actual code.

`deepline monitors status --json` emits `{ "has_access": boolean, "reason": string }`
for programmatic branching. The status check itself works for anyone with a valid
Deepline login/API key — only the _answer_ is gated. Do not proceed past this
step on a failed check.

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

## Command set

All commands accept `--json` (also automatic when stdout is piped).

| Command                                    | What it does                                                                                                                                                                                                                                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `deepline monitors status`                 | Report whether you have monitor access. Exit 0 + `has_access: true` = access; exit 1 + `has_access: false` = rollout denial. Other exits are errors, not access decisions. **Run first.**                                                                                            |
| `deepline monitors available [tool-id]`    | The catalog of monitor types you CAN deploy. Read-only. **Compact by default** (id + name + `deployed: N`); pass `--full` for the complete catalog (payload schemas + output streams). Pass a tool id positionally to describe one. Filter with `--provider`, `--search`, `--limit`. |
| `deepline monitors check '<definition>'`   | Validate a monitor definition without deploying. Read-only; spends nothing. Also accepts `--file <path>` or `--file -` (stdin).                                                                                                                                                      |
| `deepline monitors deploy '<definition>'`  | Deploy a monitor (positional JSON, `--file <path>`, or `--file -`). Mutates workspace state and may spend Deepline credits. `--dry-run` shows the plan (validity, deploy cost in Deepline credits, existing monitors that may already cover the scope) without deploying.            |
| `deepline monitors list`                   | List the monitors you HAVE deployed. `--status active\|disabled\|all` (default `active`), `--limit`, `--compact`.                                                                                                                                                                    |
| `deepline monitors get <key>`              | Show one deployed monitor by its public key. Read-only.                                                                                                                                                                                                                              |
| `deepline monitors update <key> '<patch>'` | Update a deployed monitor (`<patch>` is a JSON object of fields; also `--file`).                                                                                                                                                                                                     |
| `deepline monitors delete <key>`           | Delete a deployed monitor. Deprovisions the upstream resource by default; `--local-only` removes just the Deepline record. Prompts y/N in a terminal; non-interactive runs must pass `--yes`. `--dry-run` previews the plan.                                                         |
| `deepline monitors reactivate <key>`       | Reactivate a previously disabled deployed monitor. May spend Deepline credits; `--dry-run` shows the cost first.                                                                                                                                                                     |

Typed exit codes: 0 success, 2 usage, 3 auth/permission, 4 not found, 5 server
failure, 7 validation failed (`monitors status` keeps its exit-1-on-no-access
contract).

## Recover from errors by code

Monitor API errors include a server-owned `next_action`. Follow it before
improvising or retrying. The two common recovery paths are:

- `ingestion_plane_not_ready`: wait for the returned `retry_after_ms`, then
  retry the same read or check once.
- `monitor_tool_not_found`: run `deepline monitors available --json` and choose
  a catalog tool id. A missing deployed monitor instead routes to
  `deepline monitors list --status all --json`.

For validation errors, fix every returned issue path and rerun `monitors check`.
For billing denial, report the required credits, balance, and shortfall, then
stop. For settlement or cleanup failure, inspect the monitor state and report
that repair is required; do not repeat the mutation blindly. When the server
cannot identify a safe fix, `next_action` points back to this section: diagnose
the exact auth, permission, configuration, connection, or server failure rather
than guessing or calling it missing rollout access.

A monitor suspended for insufficient credits stays disabled until explicit
reactivation. Ask the user to add credits, run `monitors reactivate <key>
--dry-run`, show the approval summary, and reactivate only after approval. While
suspended, callbacks may remain captured for audit, but typed Customer DB rows
and connected plays do not run.

## Workflow

1. Run `status`.
2. Run `available` and read filters, streams, and pricing.
3. Run `list --status all` and `get` to inspect reuse and dependents.
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

## Shared streams and downstream blast radius

A deployed monitor is not an isolated trigger channel. It writes provider events
into a shared Customer DB stream/table. Public `sqlListeners` bindings subscribe
to a `tool` and `stream`, not to one monitor key, so a play may react to rows from
every monitor feeding that stream. Deploying another monitor on the same stream
does not create an isolated channel for its events.

Before creating, updating, disabling, reactivating, or deleting a monitor:

1. Read its output streams with `monitors available <tool-id> --json` or
   `monitors get <key> --json`.
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

Run `status`, `available`, `list`, `get`, `check`, and dependency inspection
without approval because they are read-only. Creating, updating, reactivating,
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
  `payload_schema` from `deepline monitors available`.
- `payload` — tool-specific; must match that tool's `payload_schema`.
- `name` — optional human label. `controls` — optional Deepline lifecycle metadata.

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

1. `deepline monitors available <id>` lists, per output **stream**, the `stream`
   key you bind to, the Customer DB **table**, and the **row columns** on
   `event.after`. Bind to a data stream (kind `event`/`signal`), not one marked
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

Only report **Deepline** credit spend. Read the live `available`, `check`, and
`get` pricing fields instead of assuming every monitor bills the same way. A
monitor can charge on deploy/reactivation, on each accepted provider event, or
on a recurring renewal. Event volume therefore matters for event-priced
monitors; apply the canonical per-event pricing callout in **Choose scope and
ingestion strategy**. Provider cost basis, balances, and exchange rates are
internal and must never be shown.
