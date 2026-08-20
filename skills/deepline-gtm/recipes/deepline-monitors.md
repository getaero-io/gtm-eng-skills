---
name: deepline-monitors
description: 'ACCESS-GATED beta. Deepline Monitors are provider event feeds (job posts, email replies, funding, intent) that stream into Customer DB and can trigger Plays. Run `deepline monitors status` first; if it reports no access, stop and tell the user to contact Deepline.'
---

# Deepline Monitors

Monitors turn a future company or person change into an action. A monitor watches
for the signal, writes a row to Customer DB, and a Play can send the useful hits
to Slack, update a CRM, or create a task. Change the filters or destination as
the team learns what a useful hit looks like.

## Access

Before any monitor command:

```bash
deepline monitors status --json
```

Proceed only when `has_access` is true. `has_access: false` is a rollout denial;
other failures need diagnosis.

## Core workflow

1. Discover the live monitor type and its filters, output stream, and pricing.
2. List all deployed monitors and reuse one that already covers the request.
3. Run `check` and `deploy --dry-run`; show scope, stream impact, and live
   Deepline pricing before a paid mutation.
4. Deploy or update only the requested definition, then run `get` to verify the
   stored filters and active state.
5. If a Play consumes the stream, inspect its filter and state whether its
   behavior changes.

```bash
deepline tools list --categories monitors --json
deepline tools get deepline_native.company_job_openings --json
deepline monitors list --status all --json
deepline monitors check '<definition>' --json
deepline monitors deploy --dry-run '<definition>' --json
deepline monitors deploy '<definition>' --json
deepline monitors get <key> --json
```

`check` validates a definition and selected pricing. It does not prove provider
coverage or wait for an event. The final `get`, not the deploy response, proves
what was stored. If the stored payload differs from the requested scope, report
a failed write.

If a live preflight helps, use a one-result or one-event read from the same
signal type after the user approves its cost. A current-data lookup is not proof
that a future monitor will fire. Do not use a people search as proof of job-post
or job-change delivery.

## Choose the right starting point

- **Companies:** use the company domain and a company radar. This is for job
  posts, new hires, promotions, mentions, reviews, and other supported company
  signals.
- **People:** use a LinkedIn profile URL and a contact radar. This watches a
  specific person directly, such as a job change or social activity.

Do not present a company monitor as person monitoring, or a people lookup as
proof that a company signal will arrive.

### Define a high-signal hit

A hit is useful only when it is in the approved company or person scope, recent,
matches the chosen provider filter, and gives the team a specific next action.
The result table must make those facts visible.

Use only filters in the live `payload_schema`. Its output columns are what a
Play can test. Do not infer a title, seniority, or role filter from another
radar.

## Historical scouting and batch rollout

There is no separate search product or `tail` command. Read the existing monitor
and its declared output table while waiting. Do not attribute a shared-stream
row to one monitor without a documented monitor-to-row binding.

### The customer story

Start with a small, bounded paid calibration. The job is to prove that the right
signals reach the right Slack channel or workflow before the team commits to a
larger account or contact list. Get the live Deepline quote from `check` and
`deploy --dry-run`; do not promise a fixed setup cost.

Explain the flow in the customer's terms:

```text
We will watch <companies or people> for <signal>. When a useful match arrives,
we will send it to <Slack channel or other destination>. We will first test a
small set, tune the filters until the results look useful, then show the cost and
ask before expanding to the rest of the list.
```

To start in Slack, publish a Play that sends matching monitor rows to the chosen
channel. The monitor gathers the signal; the Play handles delivery. The team can
change filters, recipients, or destination later without replacing the monitor.

State the calibration contract before deploying: approved pilot companies or
people, historical boundary or forward-only start, success criteria, and the
live Deepline pricing basis. Existing Plays are known consumers; other table
consumers may exist.

### `updates_since`: history, not a temporary switch

`updates_since` tells the source how far back to look when a radar is created.
Omit it for forward-only monitoring. It does not turn itself off after a pilot
and it is not a local result filter.

```text
Forward-only: start watching for changes after this is turned on.
Historical: look for qualifying changes since <approved date>.
```

- If history was requested without a range, use 14 days only for an ordinary or
  unknown-volume company.
- For a known high-volume company, recommend forward-only monitoring. Use a
  short historical window only after the user chooses it after seeing live price.
- Do not quietly widen days into months or change `updates_since` during a
  calibration run. Changing it can replace the upstream radar and produce new
  billable findings.

### Calibration and observation

Use three to five customer-approved, distinct companies or a similarly small
set of people. Include an expected match, a sparse contrast, and a high-volume
case only when relevant. Check and dry-run the complete manifest, then deploy at
most two monitors concurrently. Stop on an unexpected price or lifecycle failure.

For each deploy or update, record public key, definition, output table, price,
state, elapsed time, and failure. Capture `observation_started_at` immediately
before the mutation.

For Deepline Native output, query only rows where `_dl_monitor_id` equals the
public monitor key and `_dl_received_at >= observation_started_at`. Select only
declared customer-safe fields. This identifies newly received rows for one
monitor, but it does not prove that a row came from a replacement radar during
an update overlap. For monitor types without a documented binding column, show
only monitor state and `last_received_event`.

Use an interactive observation window of at most 50 seconds: read at 0, 25, and
50 seconds. At 50 seconds with no row or failure, say the monitor is active but
the result is inconclusive; historical findings may arrive later. Do not wait
silently, widen the window, or relax filters automatically.

When rows arrive, show a small safe sample as a decision table:

| Target           | Signal  | Why it matched    | When   | Recommendation     |
| ---------------- | ------- | ----------------- | ------ | ------------------ |
| <company/person> | <event> | <filter evidence> | <date> | <keep/refine/stop> |

After the table, ask whether the filters match what the customer considers a
useful signal. Recommend one supported filter adjustment: tighten title, role,
seniority, or domain/person scope only when the live schema exposes it. Preserve
a working filter when the sample is on-target.

When the customer approves the bounded calibration, own the iteration: change
one filter at a time, re-check live price, verify the stored definition, and run
another 50-second observation. Do not change `updates_since`, add new targets,
or exceed the approved pilot scope or cost without asking again.

Scale only when the definition, delivery, and observed Deepline spend are sound
and the signal held across calibration targets. Present the calibration table,
recommended expanded scope, and live pricing, then get explicit customer approval
before deploying the larger batch. For an update, use its read-back as proof of
the definition; do not count overlap rows as proof of the replacement filter.

Delete a rejected temporary scout deliberately:

```bash
deepline monitors delete <key> --dry-run --json
deepline monitors delete <key> --yes --json
deepline monitors list --status active --json
```

Deletion stops future ingestion but leaves existing Customer DB rows.

## Shared streams, reuse, and scope

Monitors write to shared Customer DB streams. A Play subscribes to a `tool` and
`stream`, not one monitor key, so another monitor on that stream can wake the
same Play. `sqlListeners.where` narrows Play behavior but does not prevent the
monitor from ingesting or charging for an event.

Before any lifecycle mutation:

1. Read the type's streams with `deepline tools get <tool-id> --json`. For an
   existing monitor, also read `deepline monitors get <key> --json`; a new key
   does not exist until deployment completes.
2. Read the entire registry with `deepline monitors list --status all --json`.
   Page until `is_truncated` is false before deciding no monitor covers the
   request.
3. Inspect dependent published Plays. Treat these as known dependents; dashboards,
   exports, SQL queries, and warehouse jobs may also consume the table.
4. State whether the mutation adds rows, stops rows, or changes incoming rows;
   name the live `pricing.display` and `charge_timing`.

Reuse a monitor with the same tool and scope. For noisy or event-priced signals,
use a provider payload filter to prevent unwanted events from being ingested.
Use `sqlListeners.where` only to decide which ingested rows wake a Play; it does
not reduce ingestion or event charges. Reactivate a disabled matching monitor
instead of creating another one.

Choose the narrowest provider filter that meets the stated use case. A broad
monitor is appropriate only for stated reuse and carries more event exposure.
For event-priced monitors, every accepted event can consume Deepline credits;
filtering, enrichment, dedupe, or rejection after ingestion does not remove that
charge. A scheduled Play is not automatically cheaper: compare frequency,
pagination, duplicate work, and measured volume.

## Empty pilots and errors

No event in a small pilot is inconclusive. Confirm the monitor is active, stored
filters are correct, and the Play listens to the actual stream. State the sample
and observation window. Then choose one controlled diagnostic: wait, test a
known recent example, or relax one filter on a small paid subset. Do not report
a coverage percentage or call the signal broken from an empty pilot.

For errors: retry a transient read or check once; correct validation failures;
re-browse an unknown type; report a credit shortfall and stop; inspect state for
settlement or cleanup failures. A billing-suspended monitor remains disabled
until the user approves `monitors reactivate <key> --dry-run` and reactivation.

## Mutations and updates

Read-only commands are `status`, `tools list/get`, `monitors list/get`, and
`check`. Deploy, update, reactivate, and delete change state and may spend
credits. When requested, show a short change summary before mutating:

```text
Changes: <field>: <old> → <new>
Stays the same: <key>; <table>; existing rows; <known Play behavior>
Cost: <live pricing.display and charge_timing>; <known lifecycle charge>
```

Use dry-run for deploy, reactivate, and delete. Update has no dry-run: read the
current definition, merge the requested patch locally, run `check` on the full
definition, then call `update` with only the intended patch.

An update keeps the public key and existing rows, but may replace the upstream
resource. A disabled monitor update changes stored definition only; reactivate
to create its upstream resource. If a dependent Play must retain the old scope,
publish its equivalent `sqlListeners.where` change before broadening the
monitor. Read back the update and report future table behavior. On
`provider_monitor_control_state_conflict` (HTTP 409), read again and retry only
if the requested change is still needed.

## Definition and Play

```json
{
  "key": "company-job-openings",
  "tool": "deepline_native.company_radar",
  "name": "Company job openings",
  "payload": {
    "domain": "stripe.com",
    "radar_type": "company_job_openings"
  }
}
```

`key` is the public lifecycle id. `tool` and `payload` must match the live
contract. `name` and `controls` are optional. The same definition shape works in
the CLI and SDK; for SDK details, read
[`../references/monitor-sdk.md`](../references/monitor-sdk.md).

Build a Play with a `sqlListeners` trigger over the output stream from `tools
get`:

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

Bind to an event or signal stream, not binding metadata. Validate and publish the
Play before relying on it. The Play runs when a matching row arrives; it needs no
schedule or polling.

## Spend

Use live `tools get`, `check`, and `get` pricing. A monitor can charge on deploy
or reactivation, per accepted event, or on a recurring interval. Event volume
matters only for event-priced monitors. Never expose provider prices, balances,
or exchange rates.
