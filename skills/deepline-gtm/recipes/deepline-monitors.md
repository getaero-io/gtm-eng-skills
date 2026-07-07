---
name: deepline-monitors
description: 'ACCESS-GATED beta. Deepline Monitors (dashboard name: Signal Radars) — provider event feeds (job posts, email replies, funding, intent) that stream into your warehouse and trigger plays. Only use if you have monitor access: run `deepline monitors status` first; if it reports no access, do NOT use this recipe — every command returns monitor_access_required. Ask a Deepline admin (Admin → Rollouts) for access.'
---

# Deepline Monitors (Signal Radars)

Monitors are **access-gated provider event feeds**. In the dashboard they are
called **Signal Radars**; the CLI and API call them **monitors**. A monitor
provisions an upstream provider resource (a TamRadar radar, an Instantly webhook
subscription, a TheirStack saved search, …); the provider posts webhooks to a
Deepline callback, and matching rows land in a table in your Customer DB. There
is **no run to kick off** — a monitor streams as events arrive.

## Step 0 — access gate (do this first)

Monitors are a rollout-gated beta. **Before any other monitor command**, run:

```bash
deepline monitors status
```

- Exit code `0` and `✓ You have access to Deepline Monitors` → proceed.
- Non-zero exit / `✗ No access` → **STOP.** Do NOT run `available`, `check`,
  `deploy`, `list`, or any other monitor command — each returns a
  `monitor_access_required` error. Tell the user monitor access is granted by a
  Deepline admin via **Admin → Rollouts** and that they should request it there.

`deepline monitors status --json` emits `{ "has_access": boolean, "reason": string }`
for programmatic branching. The status check itself works for anyone with a valid
Deepline login/API key — only the _answer_ is gated. Do not proceed past this
step on a failed check.

## Monitors vs plays

- **Monitor (Signal Radar)** = the upstream feed. It _produces_ a stream of
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

| Command                                    | What it does                                                                                                                                                                                                                                                        |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `deepline monitors status`                 | Report whether you have monitor access. Exit 0 = access, non-zero = none. **Run first.**                                                                                                                                                                             |
| `deepline monitors available [tool-id]`    | The catalog of monitor types you CAN deploy. Read-only. **Compact by default** (id + name + `deployed: N`); pass `--full` for the complete catalog (payload schemas + output streams). Pass a tool id positionally to describe one. Filter with `--provider`, `--search`, `--limit`. |
| `deepline monitors check '<definition>'`   | Validate a monitor definition without deploying. Read-only; spends nothing. Also accepts `--file <path>` or `--file -` (stdin).                                                                                                                                      |
| `deepline monitors deploy '<definition>'`  | Deploy a monitor (positional JSON, `--file <path>`, or `--file -`). Mutates workspace state and may spend Deepline credits. `--dry-run` shows the plan (validity, deploy cost in Deepline credits, existing monitors that may already cover the scope) without deploying. |
| `deepline monitors list`                   | List the monitors you HAVE deployed. `--status active\|disabled\|all` (default `active`), `--limit`, `--compact`.                                                                                                                                                    |
| `deepline monitors get <key>`              | Show one deployed monitor by its public key. Read-only.                                                                                                                                                                                                              |
| `deepline monitors update <key> '<patch>'` | Update a deployed monitor (`<patch>` is a JSON object of fields; also `--file`). E.g. `'{"controls":{"enabled":false}}'` to disable.                                                                                                                                  |
| `deepline monitors delete <key>`           | Delete a deployed monitor. Deprovisions the upstream resource by default; `--local-only` removes just the Deepline record. Prompts y/N in a terminal; non-interactive runs must pass `--yes`. `--dry-run` previews the plan.                                          |
| `deepline monitors reactivate <key>`       | Reactivate a previously disabled deployed monitor. May spend Deepline credits; `--dry-run` shows the cost first.                                                                                                                                                     |

Typed exit codes: 0 success, 2 usage, 3 auth/permission, 4 not found, 5 server
failure, 7 validation failed (`monitors status` keeps its exit-1-on-no-access
contract).

Workflow: `status` → `available` (find a tool + read its `payload_schema`) →
`list --status all` (see what already exists) → `check` (validate your
definition) → `deploy --dry-run` (see cost + reuse candidates) → `deploy` (only
if nothing covers it) → `list` (confirm it is live).

**Reuse before you deploy.** `deepline monitors deploy` re-provisions an upstream
provider feed and spends credits. Before deploying, run
`deepline monitors list --status all` and check whether a monitor already
**covers your need**: same `tool`, watching the same scope. If a matching monitor
exists, do NOT deploy another — a play binds to the shared per-tool **stream**,
so it already reacts to that monitor's rows; just author the play against the
existing stream. A disabled-but-matching monitor →
`deepline monitors reactivate <key>`, not a fresh deploy.

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
  "key": "campaign-events",
  "tool": "instantly.campaign_events",
  "name": "Reply capture",
  "payload": { "campaign_id": "camp_123" },
  "controls": {}
}
```

- `key` — public monitor instance id (you reference it in `get`/`update`/`delete`).
- `tool` — `<provider>.<capability>` (e.g. `lemlist.campaign_events`,
  `theirstack.saved_search_webhook`). Get valid ids and the `payload_schema`
  from `deepline monitors available`.
- `payload` — tool-specific; must match that tool's `payload_schema`.
- `name` — optional human label. `controls` — optional Deepline lifecycle metadata.

## Build a play on top of a monitor

The monitor captures a provider's events into a Customer DB table; a play reacts
to each new row. A play subscribes with a `sqlListeners` trigger:

```ts
sqlListeners: [
  {
    id: 'replies',
    tool: 'instantly.campaign_events',
    stream: 'webhook_events',
    operations: ['INSERT'],
    where: { after: { event_type: { eq: 'reply_received' } } },
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

## Spend

Only ever report **Deepline** credit spend. Deploy, reactivate, and per-event
monitor activity are billed in Deepline credits; provider cost basis, balances,
and exchange rates are internal and must never be shown to the customer.
