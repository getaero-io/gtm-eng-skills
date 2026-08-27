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

## User-facing communication

The lifecycle below is internal. The user needs the next decision, not a
monitoring log.

- **Ready to turn on:** for several targets, show a short scope table; for one,
  use a sentence. Recommend the first filter, name the live Deepline price and
  delivery, then ask one yes-or-adjust question. Do not lead with domains,
  validation, a dry-run, monitor keys, or timing.
- **Calibrating from matches:** show the actual attributed rows in a Markdown
  table before any roll-up or recommendation. The table is the thing the user
  is calibrating against—counts and labels such as “relevant” are not enough.
  For new hires, use `Company / Person / Joined as / When` and put a verified
  LinkedIn link on the person's name, not in a separate `Profile` column.

After the artifact, give one concrete recommendation and one question: `Want me
to use that, or adjust it?` This applies even when the first calibration call is
to leave the filter broad: the user explicitly asked to calibrate. For no
access, no sample, failure, or stop, state that outcome directly; do not invent
a scope or results table.

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

## Default-guided setup with paid consent

Treat monitor setup as **infer → validate → approve → deploy → observe**, not a
sequence of choice cards. Resolve company domains from names when necessary,
carry the evidence, and use the request's titles, roles, geography, source
list, and destination as filter inputs. Do not ask the user to supply domains
or choose routine filter values that the request already implies.

Deployment, reactivation, and historical lookback can accept variable numbers
of billable events. A user request is authorization to investigate and prepare
the exact monitor definition, not consent to incur those charges. After the
live contract, registry-reuse check, `monitors check`, and deploy dry-run,
obtain explicit approval before every paid state change in every workspace.
The approval must cover the targets, event signal, live Deepline price and
charge basis, unknown total volume, and which current or historical calibration
step it authorizes. Before consent, disclose any known downstream action and
the unknown-consumer risk in one short `Delivery:` line; those can change what
approval means. Keep raw monitor keys and implementation detail internal. A
dry-run is read-only and does not replace this approval.

For an initial forward scout, inspect safely attributed rows at 30, 60, and 90
seconds. If none arrive, leave the forward monitor active and offer a separately
approved, priced 30-day historical step. Later empty historical steps can only
advance to 60, then 90 days maximum.

Use 30, 60, and 90 days as the calibration rungs, not an invented guarantee of
an exact source cutoff. When a live contract evaluates source dates at
calendar-month precision (including Deepline Native new-hire and promotion
radars), show the provider-effective start date/window in the dry-run and
approval request before it can be billed.

"Similar companies" is a billable scope decision. Resolve and, when useful,
recommend a small evidence-based candidate list, but do not deploy those
candidates merely because they seem plausible. Show their names and inclusion
decision in the scope table; keep resolved domains with the definition unless
the user needs them.

Before asking where to send matches, check Slack with
`deepline notifications slack channels --json`. A successful response supplies
real channels: recommend the best obvious channel, not an invented one. If Slack
is unavailable or has no usable channel, say that plainly. When a CRM destination
is configured, name it and ask: `Want me to turn this on and connect Slack, or
send matches to <CRM>?` Otherwise ask: `Want me to connect Slack and turn this
on?` Routing matches to Slack or a CRM is a downstream action; include it in
the same approval as the monitor.

`job_titles` accepts only the documented Deepline Native input syntax: double-quoted title
terms joined with uppercase `AND`, `OR`, and `NOT`, such as `"VP" OR "Head of
Sales"`. Deepline Native applies the expression upstream. Parentheses and exact
title-match boundaries are not documented, so do not invent substring,
word-boundary, or case-sensitivity semantics. `job_titles` overrides
`departments` and `seniorities`, so do not send both forms. `updates_since` is
the historical boundary for a new radar, not a filter to revise during
calibration. Do not invent a title, department, seniority, or geography filter
when the selected row does not list it.

**Keep approval decision-ready, not procedural.** Do not turn routine monitor
setup into a titled plan, choice-card questionnaire, Mermaid diagram, or a raw
definition dump. Do the read-only validation and price lookup directly, then
send one short approval request for the exact paid scope. If a progress update
is useful, make it one plain sentence.

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

- **Scope:** for a calibration scout, use the named targets and the requested
  event only. Leave title, seniority, department, and geography unset unless
  the user explicitly supplied them. Do not broaden the target set for
  hypothetical future reuse.
- **Time:** start forward from deployment. If there are no safely attributed
  rows at 90 seconds, offer a 30-day historical step; only after an explicit
  approval may the next empty step widen to 60, then 90 days maximum. Do not
  silently select history or widen it during calibration.
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
Put the recommended configuration and live Deepline credit impact in one short
approval question. The validated dry-run explains scope and price; explicit
confirmation authorizes the paid mutation.

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

## First proof of value: a minimally filtered scout

Do not make a customer wait days to discover whether the intended signal has
coverage. After approval, start the approved small scout batch with only the
target and requested event filters, then prove each stored definition after the
write. This is the fastest feedback loop and guards against false success.

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
# After explicit approval of scope, shared-stream impact, and price:
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

`updates_since` is a permanent radar boundary, not pagination. A historical
step can replace an upstream radar and restart billable ingestion, so do not
patch it as a casual filter update. Use the live contract and dry-run to choose
the safe create/replace path, obtain approval for that exact operation, and
then read the resulting definition back. The only calibration ladder is 30,
60, then 90 days; never use more than 90 days without a separate user request
and a revised approval.

Capture `observation_started_at` before deployment. For Deepline Native, read
`data_plane_binding` from `monitors get <key> --json` and use both
`_dl_monitor_id` and `_dl_monitor_binding_version` to inspect this monitor's
current rows. Add `_dl_received_at` only to narrow the observation window.
Without that binding, report monitor state and `last_received_event`; do not
guess which shared-stream rows belong to the monitor. A missing output table or
binding is an operational failure, not an empty sample.

## How to communicate

Use one decision-shaped response, not a recap. Do not open with deployment,
credits, timing, history, or a checklist; those matter only once a real decision
is ready. Translate internal language: say “first pass,” “matches,” and “look
further back,” not “forward scout,” “accepted events,” or “historical rung.”

### First-pass approval

For a multi-company monitor, use this shape after live validation. Keep only
decision-bearing columns; resolved domains, duplicate checks, and monitor
plumbing are internal.

```markdown
Recommendation: Start broad—no title, department, seniority, or location
filter—so the first real matches tell us what belongs.

| Watch | Company     | Why                                |
| ----- | ----------- | ---------------------------------- |
| Yes   | <company>   | <named target or approved peer>    |
| No    | <candidate> | <why it is not in this first pass> |

Cost: <live Deepline price and charge basis>.
Delivery: <recommended connected Slack channel, or Slack/CRM choice>.
Want me to turn this on, or adjust it?
```

For one company, replace the table with a sentence. Similar companies are a
scope recommendation, not a silent expansion: show each candidate and whether
it is in this pass. Ask the delivery question only inside this one approval
question; recommend a real Slack channel when one is connected, otherwise offer
Slack or the configured CRM.

### Calibration decision

Show every decision-bearing returned row when there are 25 or fewer. Above that,
show the rows that support the boundary, state the total, and link or export the
complete user-usable result set. Use only returned values. For a new-hire
monitor:

```markdown
| Company   | Person                            | Joined as        | When            |
| --------- | --------------------------------- | ---------------- | --------------- |
| <company> | [<person>](verified-linkedin-url) | <returned title> | <returned date> |

Recommendation: <keep broad, or name the exact title/signal patterns to include and exclude>.
Why: <the pattern visible in the rows>.
Cost: <live price>, if applying this change affects future billed matches.
Want me to use that, or adjust it?
```

For other signals use `Target / Signal / Detail / When`, limited to returned
fields. Never replace the table with a count or a role roll-up. When the user
asked to calibrate, a recommendation to leave the filter broad still ends with
the same yes-or-adjust prompt; it gives them the smallest useful control.

Read monitor state and safely attributed rows at about 30, 60, and 90 seconds;
this is the live view, not a new `tail` command. Show a small result table as
soon as matches arrive. The initial forward scout ends at 90 seconds.

- At 30 and 60 seconds, report waiting only when useful.
- At 90 seconds with no row or provider error, return **no sample yet** and
  leave the forward monitor active. This is not a filter conclusion. Offer the
  next 30-day historical step with its live price and one approval question;
  do not create, replace, or widen anything before consent.
- A historical step has its own provider completion window. Do not call a
  30- or 60-day step empty, replace it, or offer the next rung until that
  documented window has passed (Deepline Native can deliver matching findings
  during its first 24 hours). Leave the current historical monitor intact
  while it is pending.
- Only after that completed 30- or 60-day historical step is empty may you
  offer the next rung (60 or 90 days) with a new live price and approval. Stop
  at 90 days.
- When rows arrive, keep matching patterns and remove only an observed
  off-target pattern. Verify the stored update, then observe it forward. An
  update does not request new historical matches.

At 90 seconds with no row, say only that no sample has arrived, the watcher is
still on, and offer the next priced historical step. A provider/contract failure
is **Blocked**, not an empty result. A rejected signal is **Stopped**: confirm
future matches stopped and existing rows remain.

Read back the stored definition internally after deployment. In post-deployment
updates, mention a destination or downstream Play only when it helps the user
act; before approval, always disclose it.

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
| `deepline monitors delete <key>`                                    | Delete a deployed monitor and its upstream resource. Prompts y/N in a terminal; non-interactive runs must pass `--yes`. `--dry-run` previews the preflight.                                                                                                                                                                                                        |
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

For a fleet, prove the approved minimally filtered scout on a bounded subset
first, then use bounded concurrency and preserve each deploy/read-back result.
A 409 means another writer changed the monitor: read it again before deciding
whether a retry is needed. For a provider rate limit, return its wait to the
user; never automatically retry a create.

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
