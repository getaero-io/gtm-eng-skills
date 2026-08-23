---
name: deepline-monitors
description: 'ACCESS-GATED beta. Deepline Monitors are provider event feeds (job posts, email replies, funding, intent) that stream into your warehouse and trigger plays. Only use if you have monitor access: run `deepline monitors status` first; if it reports no access, do NOT use this recipe — tell the user to contact the Deepline team.'
---

# Deepline Monitors

Monitors are **access-gated Deepline-native signal feeds**. The customer launch
includes Company Radar and Contact Radar. A monitor provisions a Deepline-managed
feed; events land in a Customer DB table. There is **no run to kick off** — it
streams as events arrive.

## The job: turn a future signal into a useful decision

A monitor is not a dashboard setting. It is a promise that a future real-world
event will reach the right workflow. Earn that trust: show the route, give a
small piece of evidence now, prove the stored definition says what was asked,
then let live events validate delivery over time. Each step answers a different
question; do not pretend one proves all four.

## Read the deployed monitor spec first

Every `deepline monitors get <key> --json` response includes `monitor_spec`.
When `monitor_spec.available` is true, use its `fields` as the field list for
that monitor type before you write a definition, patch, or dependent Play. Each entry names the exact
`payload.*` path and carries its description, type, required flag, enum,
format/pattern constraints, plus provider-specific applicability, precedence,
semantics, and grammar where relevant. Never guess a monitor filter from a
similar tool or a different monitor type. When `available` is false, it is a
legacy monitor without a current capability spec: use the stored definition and
run `monitors check` before an update.

Read the stored `definition` beside `monitor_spec`: the definition tells you
what this monitor currently uses; the spec tells you what each field means and
which values are legal. `conditional_requirements`, when present, states fields
required only for a particular payload selection.

## Default-guided setup, not a questionnaire or plan

Treat monitor setup as **infer → validate → deploy → report**, not a sequence
of choice cards. A user who says "monitor job changes at these accounts" has
already given enough to draft the event type, targets, and filters. Resolve
company domains from names when necessary, carry the evidence, and use the
request's titles, roles, geography, source list, and destination as filter
inputs. Do not ask the user to supply domains or to choose routine filter
values that the request already implies.

`job_titles` accepts only the documented Deepline Native input syntax: double-quoted title
terms joined with uppercase `AND`, `OR`, and `NOT`, such as `"VP" OR "Head of
Sales"`. Parentheses and title-match boundaries are not documented. Do not
claim exact, substring, word-boundary, or case-sensitivity behavior; validate
real rows before widening a paid monitor. `job_titles` overrides `departments`
and `seniorities`, so do not send both forms. `updates_since` is the historical
boundary for a new radar, not a filter to revise during calibration. Do not
invent a title, department, seniority, or geography filter when the selected
row does not list it.

**Do not create a plan artifact.** Never answer an explicit monitor request
with a titled plan, a "Summary" card, a phase/step outline, a Mermaid diagram,
or a pre-action configuration write-up. Those make the user approve work they
already asked for. Do the read-only validation, price lookup, and requested
mutation directly. If a progress update is useful, make it one plain sentence;
afterward, report only the monitor key, active scope, live Deepline credit
terms, and any unresolved targets.

**A dry-run is not a test.** It proves a definition can be deployed, not that a
deployed monitor accepts its event shape. For an internal/test workspace, read
back every monitor the user explicitly asked to create or reactivate and run the
safe validation-only test whenever `monitors get` returns a `sample_payload`.
In a customer workspace, run it only after the user explicitly approves that
diagnostic. It writes no rows, dispatches no Plays, and does not spend event
credits. Mark the monitor as tested only when the response confirms `accepted: true`,
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
question. If the user asked to create or deploy the monitor, the validated
dry-run is the scope-and-price explanation, not a second approval gate.

## Step 0 — access gate (do this first)

Monitors are an access-gated beta. Before any monitor command, confirm access:

```bash
deepline monitors status --json
```

- **You have access** → proceed.
- **No access** → stop. Do not run other monitor commands; tell the user to
  contact the Deepline team to request access.

The response is `{ "has_access": boolean, "reason": string }`; branch on
`has_access`. Other failures need diagnosis, not reinterpretation as rollout
denial.

## Explain the monitor only when useful

After validation or deployment, use a sentence when the user needs the model:
the monitor keeps watch; a matching event enters the shared signal feed; a
requested Play can then notify Slack, update a CRM, create a task, or enrich
the company. Do not render a diagram or a setup summary before doing the work.

The important boundary is that a monitor does not itself send Slack messages,
and it does not create a private channel for one workflow. Several monitors can
write to the same feed; each Play decides which new rows deserve action. That
keeps one useful source of truth, but a Play filter controls downstream action
only, not monitor ingestion cost.

## First proof of value: one filtered monitor

Do not make a customer wait days to discover whether the intended filter took
effect. Start with one narrow monitor and prove the stored definition after the
requested write. This is the fastest feedback loop and guards against false success.

**Example outcome:** “Tell me when Stripe posts a Chief Financial Officer job,
then let a Play react.” Read the live tool contract before using this example.

### Optional: test the closest real signal

Offer a small live probe when it helps the customer decide whether to deploy.
Do not make every monitor pretend it has one. A credible proxy has the same
**thing** (job, job change, review, post) and the same **moment** (new or
current) as the monitor. An adjacent lookup can be useful research, but it is
not evidence that the monitor will fire.

| Monitor is watching for…                             | Find a credible probe with…                                                 | Do not mistake this for…      |
| ---------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------- |
| Job postings                                         | `deepline tools search "job postings" --json`                               | A people or title search      |
| A tracked contact changing jobs                      | `deepline tools search "job change" --json`                                 | The contact's current profile |
| A provider webhook, campaign event, or website visit | The connected provider's test event or a deliberate test visit after deploy | A separate provider REST read |
| Any other signal                                     | `deepline tools search "<signal in plain English>" --json`                  | A loosely related enrichment  |

Read the shortlisted tool's live contract and price. Only run a one-result or
one-event probe after the customer approves its cost. Prefer the same provider
as the monitor when it exposes a callable read/search surface; otherwise say
that no faithful preflight exists instead of inventing one.

A probe tests current coverage, not future delivery. Read its identity, date,
and URL before calling it a match; an empty result proves only that nothing was
found now. The durable proof is a stored definition and a real delivered event.

### Verify every requested deployment

After creating or reactivating a monitor, read its stored definition and run
the first applicable verification below. This is execution evidence, not a
proposal or a substitute for a future provider event:

1. **Safe callback diagnostic.** When `monitors get <key> --json` returns a
   `sample_payload`, run it through the deployed monitor without writing a row
   or waking a Play in an internal/test workspace. In a customer workspace,
   first obtain explicit approval for this diagnostic:

   ```bash
   deepline monitors test <key> '<sample_payload from monitors get>' --json
   ```

   Require `accepted: true`, `test_mode: validation_only`,
   `persisted_rows: 0`, and `dispatched_bound_plays: 0`. This proves Deepline
   accepts that event shape against the monitor's real binding; it does not
   prove the upstream provider emitted it.

2. **No safe payload test.** When `sample_payload` is absent, state the test is
   unavailable. A current-signal probe may still help assess coverage, but it
   is not a monitor test and may consume credits, so keep it opt-in.

Do not fabricate a provider webhook body just to fill the gap. `monitors test
--dispatch` writes rows and can wake Plays, so use it only when the customer has
explicitly approved a real end-to-end test.

```bash
# Learn the live job-opening payload fields, output stream, and event price.
deepline tools get deepline_native.company_job_openings --json
MONITOR='{
  "key": "stripe-cfo-job-openings",
  "name": "Stripe CFO job openings",
  "tool": "deepline_native.company_radar",
  "payload": {
    "domain": "stripe.com",
    "radar_type": "company_job_openings",
    "job_titles": "\"Chief Financial Officer\""
  }
}'
# These are safe. They validate the exact definition and show cost/reuse.
deepline monitors check "$MONITOR" --json
deepline monitors deploy --dry-run "$MONITOR" --json
# After showing scope, shared-stream impact, and price:
deepline monitors deploy "$MONITOR" --json
deepline monitors get stripe-cfo-job-openings --json
# In an internal/test workspace, or after explicit customer approval:
deepline monitors test stripe-cfo-job-openings '<sample_payload from get>' --json
```

The deployment proof is the final `get` plus the safe test when available: the
definition must show `definition.payload.job_titles` as `"Chief Financial
Officer"`, the expected domain/radar type, and `status: active`; the safe test
must accept the provider-shaped sample without persistence or dispatch. If any
check fails, report a failed deployment. Do not wait for events to infer the
filter.

## Observe and refine

`updates_since` is a permanent radar boundary, not pagination. Use one
price-approved, contract-supported historical window. Do not change it during
calibration: doing so replaces the upstream radar and can restart billable
historical ingestion.

Capture `observation_started_at` before deployment. For Deepline Native, read
`data_plane_binding` from `monitors get <key> --json` and use both
`_dl_monitor_id` and `_dl_monitor_binding_version` to inspect this monitor's
current rows. Add `_dl_received_at` only to narrow the observation window.
Without that binding, report monitor state and `last_received_event`; do not
guess which shared-stream rows belong to the monitor. A missing output table or
binding is an operational failure, not an empty sample.

### Customer communication

Explain the small paid preview before starting: what will be watched, what a
useful match looks like, where it will go, and that the filters will be tuned
before a wider rollout. Keep it plain. For person-specific monitoring, prefer
a LinkedIn profile URL when available; Deepline Native can target that person
directly rather than infer from the company alone.

Use a bounded two-minute first check. Read monitor state and safely attributed
rows about every 10 seconds; this is the live view, not a new `tail` command.
Send one useful update at about 45 seconds and show a small result table if
there are matches. If not, say that no match has arrived yet and continue the
check. Historical matching can continue afterward.

- At 45 and 90 seconds, report waiting only when useful.
- At 120 seconds with no row or provider error, return **no sample yet** and
  leave the monitor active. Do not call the filter wrong, replace the monitor,
  mutate `updates_since`, or run a generic same-signal probe.
- When rows arrive, keep matching patterns and remove only an observed
  off-target pattern. Verify the stored update, then observe it forward. An
  update does not request new historical matches.

One useful waiting update is enough:

> I turned on the first few monitors and am checking whether the recent window
> produces useful matches. Nothing has arrived yet, so I’m leaving the filter
> alone for now.

When rows arrive, show a small safe sample as a decision table:

| Target           | Signal  | Why it matched    | When   | Recommendation     |
| ---------------- | ------- | ----------------- | ------ | ------------------ |
| <company/person> | <event> | <filter evidence> | <date> | <keep/refine/stop> |

After the table, state **keep**, **refine**, or **stop**. Change one supported
filter at a time, based on real off-target rows. Do not add targets beyond the
requested scope.

## Return the decision

Lead with the decision. The user needs evidence and the resulting watcher, not
a log of monitor plumbing.

| Outcome | Return |
| --- | --- |
| Needs a paid preview | One sentence: targets, broad filter, lookback, live Deepline price, and one approval question. |
| Real matches fit | **Keep.** State the signal, active filter, 2–5 safe examples, and ongoing Deepline price. |
| Real matches reveal noise | **Refine.** State the observed off-target pattern, the one filter change, 2–5 safe examples, and forward-observation caveat. |
| No row by 120 seconds | **No sample yet.** State the filter, window, active status, and that this is not a filter conclusion. |
| Provider or contract failure | **Blocked.** State the failed component and what must be fixed. Do not call it an empty result. |
| User rejects the signal | **Stopped.** Confirm the deleted key, that future ingestion stopped, and that existing rows remain. |

Use this shape when examples exist:

```text
Recommendation: <keep | refine | stop>
Observed: <count> matching events in <window>; <one-line pattern>
Change: <none | one supported filter change>
Ongoing watcher: <signal + target + final filter>
Cost: <live Deepline pricing>; <unknown volume when applicable>
```

After deployment, add the public key and destination table. Mention a Play only
when it exists or the user asked for one. Never present a titled plan, raw
definition, provider spend, or a list of routine implementation choices.

For an expanded scope the user explicitly requests, validate its live price and
deploy directly. For an update, use its read-back and safe validation-only test
as proof of the definition; do not count overlap rows as proof of the
replacement filter.

Delete a rejected temporary scout deliberately:

For a requested filter change, use the same tight loop:

```bash
deepline monitors update stripe-cfo-job-openings \
  '{"payload":{"job_titles":"\"Chief Financial Officer\" OR \"VP Finance\""}}' --json
deepline monitors get stripe-cfo-job-openings --json
```

When managing a fleet, prove this loop on one monitor first. Keep workers
bounded and save each requested patch/read-back result. A
`provider_monitor_control_state_conflict` (HTTP 409) means another writer changed
the monitor first: read it again and retry only if needed. Never treat a 409 as
success or retry it blindly.

## Find monitor types and read their filters

Monitor types live on the `tools` surface, alongside every other capability.
Browse them, then read one type's exact filters + stream columns:

```bash
# Browse the monitor types you can deploy
deepline tools list --categories monitors
deepline tools search "company radar"

# Read one specific monitor variant's full contract
deepline tools get deepline_native.company_job_openings
```

(`deepline monitors available [tool-id]` is a legacy alias for the same
discovery — prefer `tools`.)

The contract for a type gives you everything you need to deploy and to filter:

- **payload_schema** — the deploy-time filters you set in the monitor `payload`
  (typed: required fields, allowed values).
- **stream columns** — the row fields a play filters on with `sqlListeners.where`
  (the post-ingestion filter surface).
- **pricing** — live Deepline price, charge timing, and pricing basis.
- **a deploy example** — `deepline monitors deploy '<def>'`.

A monitor type is deployed, not executed: `deepline tools execute <monitor-type>`
is rejected and points you at `deepline monitors deploy`.

## Command set

All commands accept `--json` (also automatic when stdout is piped).

| Command                                                             | What it does                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `deepline monitors status`                                          | Report whether you have monitor access (`has_access`). **Run first.**                                                                                                                                                                                                                                                                                              |
| `deepline tools list --categories monitors` / `tools get <tool-id>` | **Preferred** discovery. Browse the monitor types you can deploy, and read one type's payload schema + stream columns + pricing. See "Find monitor types and read their filters".                                                                                                                                                                                  |
| `deepline monitors available [tool-id]`                             | Legacy alias of the `tools` discovery above (still works). Read-only; `--full` or a tool id for one type's full contract.                                                                                                                                                                                                                                          |
| `deepline monitors check '<definition>'`                            | Validate a monitor definition without deploying. Read-only; spends nothing. Also accepts `--file <path>` or `--file -` (stdin).                                                                                                                                                                                                                                    |
| `deepline monitors deploy '<definition>'`                           | Deploy a monitor (positional JSON, `--file <path>`, or `--file -`). Mutates workspace state and may spend Deepline credits. `--dry-run` shows the preflight (validity, deploy cost in Deepline credits, existing monitors that may already cover the scope) without deploying.                                                                                     |
| `deepline monitors list`                                            | List the monitors you HAVE deployed. `--status active\|disabled\|all` (default `active`), `--limit`, `--cursor`, `--compact`. Response carries `total` (true registry count, not the page size), `returned`, `is_truncated`, and `next_cursor`. When `is_truncated` is true, page with `--cursor <next_cursor>` until it is false — see "Reuse before you deploy." |
| `deepline monitors get <key>`                                       | Show one deployed monitor by its public key. Read-only. When `monitor_spec.available` is true, `monitor_spec.fields` lists every deployable payload field with its description and constraints; legacy records may report it unavailable.                                                                                                                          |
| `deepline monitors update <key> '<patch>'`                          | Update a deployed monitor (`<patch>` is a JSON object of fields; also `--file`).                                                                                                                                                                                                                                                                                   |
| `deepline monitors delete <key>`                                    | Delete a deployed monitor. Deprovisions the upstream resource by default; `--local-only` removes just the Deepline record. Prompts y/N in a terminal; non-interactive runs must pass `--yes`. `--dry-run` previews the preflight.                                                                                                                                  |
| `deepline monitors reactivate <key>`                                | Reactivate a previously disabled deployed monitor. May spend Deepline credits; `--dry-run` shows the cost first.                                                                                                                                                                                                                                                   |

## Recover from errors by code

Read the returned state before retrying. For validation errors, correct every
reported field against the live contract and rerun `check`. For insufficient
credits, report the required credits, balance, and shortfall, then stop. Retry a
transient read or check once; do not blindly repeat a create, settlement, or
cleanup failure.

## Operate safely

Use `check` for every definition and `deploy --dry-run` before deployment,
reactivation, or deletion. An update has no dry-run: read the full definition,
validate the merged result with `check`, update only the requested patch, then
read it back. An update keeps the public key and existing rows, but may replace
the upstream resource. It does not promise a backfill.

Before a paid deployment, list the whole registry with `--status all`. Follow
`next_cursor` until `is_truncated` is false. Reuse a monitor with the same tool
and scope; reactivate a disabled match instead of creating a duplicate. Monitors
write to shared streams, so inspect the stream and known dependent Plays before
changing scope. `sqlListeners.where` can narrow a Play's reaction, but cannot
prevent a monitor from accepting a billable event.

For a fleet, prove one narrow monitor first, then use bounded concurrency and
preserve each deploy/read-back result. A 409 means another writer changed the
monitor: read it again before deciding whether a retry is needed. For a provider
rate limit, return its wait to the user; never automatically retry a create.

If a pilot is empty, confirm the stored definition, active state, output stream,
and Play filter. A zero-result sample is inconclusive. Keep the monitor active
or run one approved, priced diagnostic; do not widen several filters or call the
signal broken. `check` validates a definition, not provider coverage.

Only report live Deepline credit terms. The contract can price deployment,
reactivation, accepted events, or recurring renewal. For event-priced monitors,
future total is unknown without measured volume. Never expose provider cost.

## Update and downstream automation

When the user changes a monitor, report the requested change, the active scope,
known downstream Plays, and live Deepline pricing. Do not claim an arbitrary
title expression is broader or narrower. A disabled monitor stores updates but
does not contact the provider until reactivated.

A monitor writes event rows; a Play can react to each row with a `sqlListeners`
trigger for the tool and stream shown by `tools get`. Use a `where` clause only
when the stream schema documents the field. Validate and publish the Play before
reactivating a monitor when that Play must be ready for new events. The SDK uses
the same definition and lifecycle contract; see
[`../references/monitor-sdk.md`](../references/monitor-sdk.md).

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

### Priority radar exception

Use `controls.execution_type: "priority"` only for an urgent preview or
calibration. Deepline adds the provider-facing marker; do not put
`custom_fields` in `payload`. Regular and bulk creation stay normal. An org has
ten active-or-in-flight priority slots. At the cap, report it and get the
user's choice; never delete a customer radar automatically. To retain a radar
but release its slot, patch `{"controls":{"execution_type":null}}`.

```json
{
  "key": "stripe-job-openings-preview",
  "tool": "deepline_native.company_radar",
  "payload": {
    "domain": "stripe.com",
    "radar_type": "company_job_openings"
  },
  "controls": { "execution_type": "priority" }
}
```
