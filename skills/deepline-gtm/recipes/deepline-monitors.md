---
name: deepline-monitors
description: 'ACCESS-GATED beta. Deepline Monitors are provider event feeds (job posts, email replies, funding, intent) that stream into Customer DB and can trigger Plays. Run `deepline monitors status` first; if it reports no access, stop and tell the user to contact Deepline.'
---

# Deepline Monitors

Monitors turn a future company or person change into an action. A monitor watches
for the signal, writes a row to Customer DB, and a Play can send the useful hits
to Slack, update a CRM, or create a task. Change the filters or destination as
the team learns what a useful hit looks like.

## Default-guided setup, not a questionnaire or plan

Treat monitor setup as **infer → validate → deploy → report**, not a sequence
of choice cards. A user who says "monitor job changes at these accounts" has
already given enough to draft the event type, targets, and filters. Resolve
company domains from names when necessary, carry the evidence, and use the
request's titles, roles, geography, source list, and destination as filter
inputs. Do not ask the user to supply domains or to choose routine filter
values that the request already implies.

**Do not create a plan artifact.** Never answer an explicit monitor request
with a titled plan, a "Summary" card, a phase/step outline, a Mermaid diagram,
or a pre-action configuration write-up. Those make the user approve work they
already asked for. Do the read-only validation, price lookup, and requested
mutation directly. If a progress update is useful, make it one plain sentence;
afterward, report the monitor key, active scope, live Deepline credit terms, any
unresolved targets, and provider-required `setup_guidance` (including a callback
URL and setup steps) when the read-back returns it. Do not call a monitor active
and ready to receive events until any returned provider setup is complete.

**A dry-run is not a test.** It proves a definition can be deployed, not that a
deployed monitor accepts its event shape. For every monitor the user explicitly
asked to create or reactivate, read it back and run the safe validation-only
test whenever `monitors get` returns a `sample_payload`. Do this automatically
in an internal/test workspace. In a customer workspace, run it only after the
user explicitly authorizes this diagnostic for that monitor. It writes no rows,
dispatches no Plays, and does not spend event credits. Mark the monitor as
tested only when the response confirms `accepted: true`,
`test_mode: validation_only`, `persisted_rows: 0`, and
`dispatched_bound_plays: 0`. If no sample payload exists, report that the
provider offers no safe payload test and do not claim the monitor was tested.

Use these defaults unless the request says otherwise:

- **Scope:** use the narrowest provider-side filters that express the user's
  stated signal and target set. Do not broaden for hypothetical future reuse.
- **Time:** monitor forward from deployment. Do not request historical matching
  or a backfill window unless the user explicitly asks for history, recent
  findings, a lookback, or backfill.
- **Action:** preserve the monitor's event feed. Add a downstream Play only
  when the user asks for a notification or another side effect; otherwise leave
  the event in its Customer DB stream for review.
- **Ambiguity:** use the available company/person context to resolve it. Keep an
  unresolved target with a reason rather than stopping the whole setup.

Treat the following as implementation decisions, not user questions: company
domain recovery, monitor type selection, exact provider-side filter syntax,
narrow-versus-broad scope when the defaults above decide it, forward-only
operation, validation-only testing, and the monitor key/name. A downstream
destination is a requirement only when the user asks for an alert or other side
effect; otherwise use the Customer DB stream. A spend cap is optional: when the
user gives none, obtain the live price and proceed within the requested scope
instead of asking them to invent one.

Before presenting a recommendation, read the live monitor contract, build the
definition, run `monitors check`, and run `monitors deploy --dry-run`. Report
the actual deploy/reactivation charge, recurring charge, and/or Deepline credits
per accepted event returned by those commands. Do not ask the user whether they
want a more expensive option before looking up its price. When event volume is
unknown, say that future total is unknown; do not invent an estimate.

Ask only to complete a missing requirement: which signal matters, which targets
belong in scope, or where an explicitly requested alert/action should go. Ask
when a deployment check exposes an unaffordable or invalid configuration too.
Put the recommended configuration and live Deepline credit impact in that one
question. If the user stated the monitor scope and asked to create or deploy it,
that request authorizes the validated mutation; the dry-run is the scope-and-
price explanation, not a second approval gate.

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
3. Run `check` and `deploy --dry-run`; use the resulting scope, stream impact,
   and live Deepline pricing to validate the requested mutation.
4. Deploy or update only the requested definition, then run `get` to verify the
   stored filters and active state. In an internal/test workspace, run the safe
   validation-only test when the read-back provides a sample payload; in a
   customer workspace, do so only with explicit diagnostic-test permission.
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
deepline monitors test <key> '<sample_payload from monitors get>' --json
```

`check` validates a definition and selected pricing. It does not prove provider
coverage or wait for an event. The final `get`, not the deploy response, proves
what was stored. If the stored payload differs from the requested scope, report
a failed write.

If a live preflight helps, use a one-result or one-event read from the same
signal type within the requested scope only in an internal/test workspace, or
after the user explicitly authorizes that diagnostic in a customer workspace.
A current-data lookup is not proof that a future monitor will fire. Do not use a
people search as proof of job-post or job-change delivery.

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

### Explain the monitor only when useful

After validation or deployment, use a sentence when the user needs the model:
the monitor keeps watch; a matching event enters the shared signal feed; a
requested Play can then notify Slack, update a CRM, create a task, or enrich
the company. Do not render a diagram or a setup summary before doing the work.

To start in Slack, publish a Play that sends matching monitor rows to the chosen
channel. The monitor gathers the signal; the Play handles delivery. The team can
change filters, recipients, or destination later without replacing the monitor.

### `updates_since`: history, not a temporary switch

`updates_since` tells the source how far back to look when a radar is created.
Omit it for forward-only monitoring. It does not turn itself off after a pilot
and it is not a local result filter.

```text
Forward-only: start watching for changes after this is turned on.
Historical: look for qualifying changes since <approved date>.
```

- If history was explicitly requested without a range, use 14 days only for an
  ordinary or unknown-volume company and report the live price.
- For a known high-volume company, use forward-only monitoring unless the user
  explicitly requires history.
- Do not quietly widen days into months or change `updates_since` during a
  calibration run. Changing it can replace the upstream radar and produce new
  billable findings.

### Calibration and observation

Use the requested targets and the narrowest filters that express the stated
signal. Do not force a pilot or ask the user to approve a small calibration when
they asked to deploy the full stated scope. Check and dry-run the complete
manifest, then stop on an unexpected price or lifecycle failure.

For each deploy or update, record public key, definition, output table, price,
state, elapsed time, and failure. Capture `observation_started_at` immediately
before the mutation.

For Deepline Native output, query only rows where `_dl_monitor_id` equals the
public monitor key and `_dl_received_at >= observation_started_at`. Select only
declared customer-safe fields. This identifies newly received rows for one
monitor, but it does not prove that a row came from a replacement radar during
an update overlap. For monitor types without a documented binding column, show
only monitor state and `last_received_event`.

Use the validation-only payload test when it is available. It is the immediate,
safe proof that the stored monitor accepts its event shape. An observation window
is optional diagnostic work, not a deployment prerequisite. If it is used, limit
it to 50 seconds and say that no resulting live row is inconclusive.

When rows arrive, show a small safe sample as a decision table:

| Target           | Signal  | Why it matched    | When   | Recommendation     |
| ---------------- | ------- | ----------------- | ------ | ------------------ |
| <company/person> | <event> | <filter evidence> | <date> | <keep/refine/stop> |

After the table, report whether the filters match the user's stated signal.
Recommend one supported filter adjustment only when the sample is off-target:
tighten title, role, seniority, or domain/person scope when the live schema
exposes it. Preserve a working filter when the sample is on-target.

When follow-up refinement is requested, change one filter at a time, re-check
live price, verify the stored definition, and run another safe validation-only
test when available and permitted by the workspace rule above. Do not change
`updates_since` or add targets beyond the requested scope without asking.

For an expanded scope the user explicitly requests, validate its live price and
deploy directly. For an update, use its read-back and safe validation-only test
as proof of the definition; do not count overlap rows as proof of the
replacement filter.

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

Choose the narrowest provider filter that meets one stated use case. A broad
monitor is appropriate only when the user explicitly asks for multiple existing
use cases and carries more event exposure. Ask only when those requirements
conflict and the live contract cannot express both safely.
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
credits. Do not turn a requested deployment into a plan or second approval
gate. Report the result after the mutation; when a concise progress update is
needed, use one plain sentence:

```text
Changes: <field>: <old> → <new>
Stays the same: <key>; <table>; existing rows; <known Play behavior>
Cost: <live pricing.display and charge_timing>; <known lifecycle charge>
```

Use dry-run for deploy, reactivate, and delete. Update has no dry-run: read the
current definition, merge the requested patch locally, run `check` on the full
definition, then call `update` with only the intended patch. After every
requested deploy or reactivation, read back the monitor. Run its safe
validation-only test if a sample payload is available in an internal/test
workspace, or in a customer workspace only after explicit diagnostic-test
permission.

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
