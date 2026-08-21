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
- **pricing** — Deepline credits per accepted event.
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

## Monitors as code (SDK)

The CLI and SDK use the same monitor model. Use the typed SDK in scripts, agent
loops, or play repositories. Read
[`../references/monitor-sdk.md`](../references/monitor-sdk.md); this recipe's
access, cost visibility, read-back, shared-stream, and pricing rules still apply.

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
- **Source rate limited during deploy**: show the provider's stated wait and
  let the user decide whether to retry. Do not retry a create automatically:
  the provider may have applied it even though Deepline could not confirm it.

A monitor suspended for insufficient credits stays disabled until you explicitly
reactivate it. Ask the user to add credits, run `monitors reactivate <key>
--dry-run`, show the impact summary, then reactivate when they ask. While
suspended, connected plays do not run.

**Edit existing monitors; do not delete and recreate them manually.**
`deepline monitors update <key> '<patch>'` and `client.monitors.update(key,
patch)` are the supported filter-edit paths. A changed definition keeps the
public monitor key and existing Customer DB rows, but the current provider
lifecycle may replace the upstream resource by creating the new resource before
deleting the previous one. Describe this as an update with upstream replacement,
not as a requirement to delete every monitor and start over.

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
5. Explain the published pricing basis, state that total future spend is unknown
   without measured event volume, and describe downstream behavior. When the
   change can affect another consumer, name that impact before doing it.

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

A cron is not automatically cheaper. Compare measured monitor event volume,
when available, with the scheduled action's frequency, pagination, duplicate
work, and follow-up enrichment. When volume is unknown, state that instead of
estimating spend. `net_new` output or a downstream dedupe protects the
destination; it does not prove the provider call was free.

When the request names one monitor use case, use the narrow provider monitor;
do not invent future reuse or make the user choose it. When the user already
named multiple use cases, or an existing monitor covers them, recommend the
shared broader feed and state the live price consequence. Ask only when the
request contains genuinely conflicting scope signals that neither default can
resolve. In that case, first run the check and dry-run, then ask one question
that leads with the recommended scope and its known Deepline-credit impact.

## Empty pilots and monitor testing

`deepline monitors check` validates the definition, selected pricing, and
whether the monitor type is available. It does not test provider coverage, wait
for a live event, or prove that a target segment will produce findings.

A small sample with zero relevant events is **inconclusive**. It can mean the
filters excluded the available events, the provider has weak coverage for that
sample, no qualifying event occurred during the observation window, or the
delivery path needs diagnosis. Do not call the signal "not working" from a
zero-result pilot alone.

When a pilot is empty:

1. Run `monitors get <key>` and confirm the monitor is active and the stored
   payload matches the intended filters.
2. Confirm the play binding watches the monitor's actual output stream and that
   its `sqlListeners.where` clause is not excluding received rows.
3. State the observation window and sample size. Do not turn absence of events
   into a coverage percentage.
4. Propose one controlled diagnostic at a time: keep the monitor and wait for
   future events, test a known recent ground-truth example, or relax one filter
   on a small subset. State scope and live price before a paid diagnostic.
5. Report the result as provider coverage evidence for that sample, not a
   universal verdict on the signal.

There is no customer-facing end-to-end monitor test command that proves live
coverage. Do not describe `monitors check` as one.

## Managing many monitors

The public SDK and CLI expose lifecycle operations for one monitor at a time.
A script may call `client.monitors.deploy(...)` or
`client.monitors.update(...)` across many definitions with bounded concurrency.
Do not issue an unbounded `Promise.all` across hundreds of paid mutations.
Preserve each monitor's result, retry only explicit transient failures, and run
the full-registry reuse check before creating new monitors.

## Make mutations legible, not ceremonial

`status`, `tools list`/`tools get` (type discovery), `monitors list`,
`monitors get`, `check`, and dependency inspection are read-only. Creating,
updating, reactivating, or deleting a monitor changes workspace or provider
state and can spend credits. When the customer asks for that change, validate
the live scope and cost, execute it, then report what changed. Do not turn the
following compact result format into a pre-execution plan. If they asked only
to design or review, stay read-only.

```text
Changes
- <field>: <old value> → <new value>
- <broader/narrower only when this is clear>

Stays the same
- Monitor: <key>
- Table: <tool.stream → Customer DB table>
- Existing rows stay in the table.
- Known plays: <list and whether their behavior changes>

Cost
- <live deploy, reactivation, event, or recurring price in Deepline credits>
- <known lifecycle charge; future volume is unknown unless measured>
- <replacement note; mention backfill only when provider evidence proves one>
- Check: <result; update has no dry-run>
```

For deploy, reactivate, and delete, include the built-in dry-run result. Update
has no dry-run, so use the read-only validation sequence below. A request to create
or change a monitor is the authorization to make that requested change; do not
insert a second confirmation gate after the scope and price are known.

## Update a monitor

Use `monitors update`. Do not tell the user to delete and recreate monitors just
to change a filter.

An update keeps the public monitor key. Deepline may replace the upstream
provider resource behind it. Existing Customer DB rows stay. If the tool and
output stream are unchanged, future events keep going to the same table. If the
output stream changes, name the old and new destinations.

For a disabled monitor, update only changes the stored definition. It does not
contact the provider, activate the monitor, or charge credits. Publish any
dependent Play changes first, then use `monitors reactivate` to run the normal
preflight and create the upstream monitor from the updated definition.

Replacement does not guarantee a backfill. If the provider emits initial,
replayed, or backfill events, each event Deepline accepts is billed at the live
per-event price. A play filter or dedupe does not remove that ingestion charge.
Read the current price from `monitors get` and the checked definition.

Example:

```text
Changes
- Job title: CEO → CEO OR CFO

Stays the same
- Monitor: goldman-sachs-new-hires
- Signal and Customer DB table are unchanged.
- Existing rows stay in that table.

Cost
- Ongoing price: <live credits per accepted event>
- Deepline will update the upstream provider resource.
- A backfill is not guaranteed. If the provider emits initial or replayed findings, accepted findings use the normal event price.
```

Before updating:

1. Run `deepline monitors get <key> --json` to read the current definition,
   selected price, billing state, outputs, and dependent published plays.
2. Merge the requested patch into that full definition locally, then run
   `deepline monitors check '<full-definition>' --json`. `check` validates the
   definition and selected pricing; it does not simulate the provider-side
   update.
3. Show the `Changes / Stays the same / Cost` summary above. Do not call an
   arbitrary Boolean expression broader or narrower unless that relationship is
   clear.
4. For each dependent play, say whether it should keep the old behavior, adopt
   the new scope, or needs user direction. Do not silently make one choice for
   every dependent.
5. If a play must preserve the old restriction, prepare and publish its
   equivalent `sqlListeners.where` change before broadening the monitor. This
   preserves play behavior; apply the per-event pricing callout above when
   explaining spend.
6. Pass only the intended patch to `monitors update`. Read its `change_summary`
   when present. Then verify with `monitors get` and the live play bindings.
   Report what changed, what stayed the same, and which table receives future
   events.

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
