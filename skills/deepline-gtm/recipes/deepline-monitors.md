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
  delivery, then offer the setup choices in “First-pass approval.” Keep
  domains, validation, monitor keys, and observation timing out of that question.
- **Calibrating from matches:** show the actual attributed rows in a Markdown
  table before any roll-up or recommendation. The table is the thing the user
  is calibrating against—counts and labels such as “relevant” are not enough.
  For new hires, use `Company / Person / Joined as / When` and put a verified
  LinkedIn link on the person's name, not in a separate `Profile` column.

For calibration, follow the artifact with one concrete recommendation and one
question: `Want me to use that, or adjust it?` This applies even when the call is
to leave the filter broad: the user explicitly asked to calibrate. For no
access, no sample, failure, or stop, state that outcome directly; do not invent
a scope or results table.

## Read the deployed monitor spec first

Read `deepline monitors get <key> --json` before a patch or dependent Play.
Its stored `definition` gives current values; `monitor_spec.fields` gives exact
payload paths, types, constraints, applicability, precedence and grammar. Follow
`conditional_requirements` for the selected payload. Never borrow filters from
another monitor type. If `monitor_spec.available` is false, use the legacy
stored definition and validate the merged change with `monitors check`.

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
obtain explicit approval covering the paid setup. Name the targets, signal,
live Deepline price per match, and delivery in a short question. For variable
charges, say “charged as matches arrive” rather than estimating an unknown
total. Include any nonzero setup or recurring charge and material downstream
actions; omit zero-cost line items and absent charges. If consumers are unknown,
resolve them or explain the uncertainty before approval.

Offer “With recent history” (recommended when supported), “Future hires only,”
and “Preview only.” State the maximum historical scope in the history option,
using the earliest effective month/date when calendar rounding applies. This
approves the initial backfill and one widening within that scope at the quoted
price. Keep the 30-day/90-day sequence, polling intervals, replacement mechanics,
and interruption caveat in operational notes, not the approval question or its
preamble. History is a best-effort sample and may arrive later; explain that
when it affects the user's expectations, without promising complete coverage.
A preview validates configuration without activation or event charges. Carry
approval through the loop; ask again only if scope, price, destination or side
effects exceed it.

For a new monitor whose live contract supports historical lookback, start with
`updates_since` 30 days before setup. Poll every 30 seconds for 90 seconds after
provider activation. If no attributable match or pending finding has arrived,
all readiness checks pass, and widening is approved, replace through the normal
monitor lifecycle with a 90-day boundary. Skip 60 days. Poll for another 90
seconds after the replacement activates. Keep the monitor active if neither
window produces a sample; this is a setup observation budget, not provider scan
completion. Use the decision rules in “Observe and refine.”

Honor an explicit time boundary or future-only request. Do not replay history
when merely recovering a billing-suspended monitor. For a type without history,
use its documented forward behavior and say historical sampling is unavailable;
do not invent `updates_since` or a substitute provider.

Calculate both candidate dates from the same setup time. Where the live
contract uses calendar-month precision, retain both requested and effective
start dates in validation output. In the history choice, summarize only the
earliest effective boundary, such as “available matches since July,” so the
approved scope includes rounding without exposing the internal sequence. For
new hires/promotions, validate that the 30-day timestamp is outside the current
month. On a 31st it may still be in the current month: use and validate the
previous month's start within the approved historical scope. Explain exact
dates if the user asks or supplies a boundary that rounding would exceed;
never silently widen that explicit boundary. SDK/API omission remains a
future-only start; this historical default is an agent setup choice.

"Similar companies" is a billable scope decision. Resolve and, when useful,
recommend a small evidence-based candidate list, but do not deploy those
candidates merely because they seem plausible. Show their names and inclusion
decision in the scope table; keep resolved domains with the definition unless
the user needs them.

When notifications are requested, check Slack with
`deepline notifications slack channels` before recommending a channel. Use a
real connected channel or configured CRM, and include that downstream action
in the same setup approval. If the requested destination is unavailable, say
so and resolve it. Otherwise use the existing data feed; routine monitor setup
does not need an extra Slack or CRM decision.

`job_titles` accepts only the documented Deepline Native input syntax: double-quoted title
terms joined with uppercase `AND`, `OR`, and `NOT`, such as `"VP" OR "Head of
Sales"`. Deepline Native applies the expression upstream. Parentheses and exact
title-match boundaries are not documented, so do not invent substring,
word-boundary, or case-sensitivity semantics. `job_titles` overrides
`departments` and `seniorities`, so do not send both forms. `updates_since` is
the historical boundary for a new radar. Widening it requires the normal
create/replace lifecycle covered by setup approval; it is not a query filter. Do not invent a title, department, seniority, or geography filter
when the selected row does not list it.

**Keep approval decision-ready, not procedural.** Do the read-only validation
and price lookup directly, then send one short approval request with the three
setup choices below. A single choice card is useful; a questionnaire about
routine configuration is not. Keep titled plans, diagrams, raw definitions, and
operational timing out of the handoff. If a progress update is useful, make it
one plain sentence.

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
- **Time:** for supported history, use the approved 30-day → 90-day setup loop,
  waiting 90 seconds per active binding. Respect explicit time limits and
  future-only requests. Do not exceed 90 days without revised approval.
- **Action:** preserve the monitor's event feed. Add a downstream Play only
  when the user asks for a notification or another side effect; otherwise leave
  the event in its Customer DB stream for review.
- **Ambiguity:** use the available company/person context to resolve it. Keep an
  unresolved target with a reason rather than stopping the whole setup.

Before presenting a recommendation, read the live monitor contract, build the
definition, run `monitors check`, and run `monitors deploy --dry-run`. Report
the actual deploy/reactivation charge, recurring charge, and/or Deepline credits
per accepted event returned by those commands. Do not ask the user whether they
want a more expensive option before looking up its price. For unknown event
volume, explain that charges accrue as matches arrive; do not invent a total.

Ask only to complete a missing requirement: which signal matters, which targets
belong in scope, or where an explicitly requested alert/action should go. Ask
when a deployment check exposes an unaffordable or invalid configuration too.
Put the recommended configuration and live Deepline credit impact in one short
approval question. The validated dry-run explains scope and price; explicit
confirmation authorizes the paid mutation.

## Step 0 — access gate (do this first)

Monitors are an access-gated beta. Before any monitor command, confirm access:

```bash
deepline monitors status
```

- **You have access** → proceed.
- **No access** → stop. Do not run other monitor commands; tell the user to
  contact the Deepline team to request access.

It exits 0 with access and 1 without, with a reason; branch on that.
Other failures need diagnosis, not reinterpretation as rollout
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
target and requested event filters and the approved 30-day historical boundary
when supported, then prove each stored definition after the write. This is the fastest feedback loop and guards against false success.

**Example outcome:** “Tell me when Stripe posts a Chief Financial Officer job,
then let a Play react.” Read the live tool contract before using this example.

### Optional: test the closest real signal

A paid current-signal probe is optional and needs approval of its live price.
Discover one with `deepline search "<tracked subject -> exact signal>" --type tools`;
prefer the monitor's provider. It must match both the event and its timing:
a contact's current profile does not prove a job change; a separate REST read
does not prove webhook delivery. If no faithful probe exists, say so. Inspect
identity, date and URL before calling a result a match. Empty coverage is
inconclusive, and current coverage does not prove future delivery.

### Verify every requested deployment

Read back every created/reactivated monitor. When `get` supplies `sample_payload`,
run the safe diagnostic in an internal/test workspace; obtain explicit approval
first in a customer workspace:

```bash
deepline monitors test <key> '<sample_payload from monitors get>' --json
```

Require `accepted: true`, `test_mode: validation_only`, `persisted_rows: 0`
and `dispatched_bound_plays: 0`. This checks event shape against the real binding,
not upstream emission. If no sample exists, report that no safe payload test is
available. Never fabricate a webhook body. A real event → DB → Play test needs
its own approved delivery path; `monitors test` has no dispatch mode.

```bash
# Learn the live job-opening payload fields, output stream, and event price.
deepline describe deepline_native.company_job_openings
UPDATES_SINCE=$(node -e 'console.log(new Date(Date.now() - 30 * 86400000).toISOString())')
MONITOR=$(node - "$UPDATES_SINCE" <<'JS'
console.log(JSON.stringify({
  key: 'stripe-cfo-job-openings',
  name: 'Stripe CFO job openings',
  tool: 'deepline_native.company_radar',
  payload: {
    domain: 'stripe.com',
    radar_type: 'company_job_openings',
    job_titles: '"Chief Financial Officer"',
    updates_since: process.argv[2],
  },
}));
JS
)
# These are safe. They validate the exact definition and show cost/reuse.
deepline monitors check "$MONITOR"
deepline monitors deploy --dry-run "$MONITOR"
# After explicit approval of scope, shared-stream impact, and price:
deepline monitors deploy "$MONITOR"
deepline monitors get stripe-cfo-job-openings
# In an internal/test workspace, or after explicit customer approval:
deepline monitors test stripe-cfo-job-openings '<sample_payload from get>'
```

The deployment proof is the final `get` plus the safe test when available: the
definition must show `definition.payload.job_titles` as `"Chief Financial
Officer"`, the expected domain/radar type, and `status: active`; the safe test
must accept the provider-shaped sample without persistence or dispatch. If any
check fails, report a failed deployment. Do not wait for events to infer the
filter.

## Observe and refine

`updates_since` is a radar boundary, not pagination. Historical widening can
replace the upstream resource and restart billable ingestion. Validate the
90-day definition and its live price before the initial approval, use the
normal owned create/replace path, and read back the new definition and binding.
Keep targets and signal filters unchanged while widening; preserve existing
rows. Do not use direct provider calls, manual deletion or a second monitor key
as a shortcut. If replacement/cleanup fails, report the failure and inspect the
retained state rather than starting another radar.

Verify four separate facts after activation: the stored definition matches,
the provider resource is active, every selected output table is readable, and
real events are delivered. Activation provisions selected tables even with zero
findings. Readiness does not depend on the first callback. An empty readable
table is a valid outcome; a missing table, read failure, missing binding, or
provider/ingestion error is an operational failure. Never fabricate event rows
or manually create a guessed provider schema to hide it.

Capture the current activation time, then inspect monitor state and attributed
rows at 30, 60, and 90 seconds. For Deepline Native, read `data_plane_binding`
from `monitors get <key> --json` and use both `_dl_monitor_id` and
`_dl_monitor_binding_version` in shared-stream queries. Reset the timer and use
the new binding after widening. `last_received_event` proves raw receipt only;
it does not prove typed storage or downstream Play delivery.

| Observation at the cutoff                                                                   | Action                                                                                                                    |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Attributable rows arrived                                                                   | Show the real sample immediately; keep the monitor and calibrate from evidence. Do not widen.                             |
| Provider findings or callbacks arrived but rows are pending                                 | Follow their delivery state; investigate a write failure. Do not widen or call it empty.                                  |
| Configuration, provider, table, binding or ingestion failed                                 | Report **Blocked** with the failure; repair through the normal lifecycle. Do not widen or claim no history.               |
| 30-day binding is ready, with no matching rows or pending findings after 90 seconds         | Use the already-approved 90-day replacement; otherwise obtain approval first. Skip 60 days.                               |
| 90-day binding is ready, with no matching rows or pending findings after another 90 seconds | Leave it active and say: **“No matching historical events found during setup. Monitoring is active for future matches.”** |

If an observed matching finding has an unreadable delivery state, report an
inconclusive sample and investigate it. With no observed matching finding or
known pending delivery, follow the 90-second setup cutoffs; a scan-completion
flag is not required. Absence of rows does not prove full historical coverage.
Deepline Native documents historical delivery during the first 24 hours and
has no historical-scan completion flag. Early widening may interrupt remaining
30-day processing. Retain this limitation in operational notes; describe
history to the user as a best-effort sample if needed. The final message reports
only the bounded observation. Later history may still arrive from the
active 90-day monitor. Do not claim complete historical coverage or a broken
signal from either timeout.

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

Turn on <signal> tracking for <named targets>? Matches cost <live Deepline
price> each, charged as they arrive, and appear in <validated destination>.

- With recent history (recommended): include available past matches <maximum
  approved scope; use “since July” rather than rolling-day counts for month precision>.
- Future hires only: watch for new matches from now on.
- Preview only: validate the configuration without activating or spending credits.
```

For one company, replace the table with a sentence. Use the signal's own noun
for the future-only choice, such as “Future job openings only.” If history is
unsupported or the user already chose future-only, omit the history choice.
Honor preview-only requests without asking to activate. Selecting history
approves the internal setup loop within the displayed boundary; selecting
future-only omits `updates_since`; selecting preview-only performs no paid
mutation. Do not ask the same setup question again after a choice is approved.

Similar companies are a scope recommendation, not a silent expansion: show each
candidate and whether it is in this pass. Include delivery in this same handoff;
recommend a real Slack channel when connected or the existing data feed when no
external destination was requested. Mention a missing Slack connection only if
it prevents requested delivery, rather than forcing another setup decision.

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

Use the “Observe and refine” decision rules: inspect every 30 seconds, show
matches as soon as they arrive, and use only the approved 30-day → 90-day
widening. Do not ask for another approval already covered by setup consent.
When rows arrive, keep matching patterns and remove only an observed off-target
pattern. Verify the stored update and observe it forward; an ordinary filter
update does not request new historical matches. A rejected signal is **Stopped**:
confirm future matches stopped and existing rows remain.

Read back the stored definition internally after deployment. In post-deployment
updates, mention a destination or downstream Play only when it helps the user
act; before approval, always disclose it.

For a requested filter change, use the same tight loop:

```bash
deepline monitors update stripe-cfo-job-openings \
  '{"payload":{"job_titles":"\"Chief Financial Officer\" OR \"VP Finance\""}}'
deepline monitors get stripe-cfo-job-openings
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
deepline search "company domains -> ongoing company event feed" --type tools

# Read one specific monitor variant's full contract
deepline describe deepline_native.company_job_openings
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

Monitor commands use readable text by default; pass `--json` when parsing output.
Use `deepline describe <tool-id>` without `--json` for discovery.

| Command                                                   | Purpose                                                                                                             |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `monitors status`                                         | Check beta access first.                                                                                            |
| `tools list --categories monitors` / `describe <tool-id>` | Discover live payload fields, streams and prices.                                                                   |
| `monitors available [tool-id]`                            | Legacy alias for tool discovery.                                                                                    |
| `monitors check '<definition>'`                           | Validate without deployment or spend.                                                                               |
| `monitors deploy '<definition>'`                          | Apply a full desired definition; `--dry-run` previews validity, price and reuse.                                    |
| `monitors list`                                           | Page the registry with `--status active\|inactive\|all`, `--limit` and `--cursor`.                                  |
| `monitors get <key>`                                      | Read stored definition, current binding and `monitor_spec`.                                                         |
| `monitors test <key> '<payload>'`                         | Validate callback shape without rows, charges or Play dispatch.                                                     |
| `monitors validate <key>`                                 | Validate provider configuration; does not prove delivery.                                                           |
| `monitors update <key> '<patch>'`                         | Apply a patch; may replace the resource. Validate the merged definition first.                                      |
| `monitors delete <key>`                                   | Delete upstream and local resources; supports `--dry-run`; requires `--yes` non-interactively.                      |
| `monitors reactivate <key>`                               | Resume a disabled monitor; inspect cost with `--dry-run`.                                                           |
| `monitors health [--fleet <id>]`                          | Inspect desired/provider state and delivery. Wait for `refresh.state: "completed"` before using whole-scope counts. |
| `monitors audit [--fleet <id>]`                           | Read upstream evidence; `--watch` waits for completion. Does not resume billing-paused ingestion.                   |
| `monitors repair [--fleet <id>]`                          | Converge observed state disagreements; audit and dry-run first. Does not bypass billing recovery.                   |
| `monitors fleets init` / `sync` / `get`                   | Define, converge or inspect a Fleet; `sync --dry-run` plans, `sync --wait` follows its durable operation.           |
| `monitors fleets deactivate <id>`                         | Stop the owned Fleet; supports `--dry-run`, `--yes` and `--wait`.                                                   |
| `monitors fleets reactivate <id>`                         | Explicit recovery after credit suspension; inspect costs before `--yes --wait`.                                     |

Prefix these commands with `deepline`. Use live `--help` for flags. Definition
commands accept positional JSON or `--file <path>` / `--file -`. When listing,
read `total`, `returned`, `has_more` and `next_cursor`; continue while `has_more`
is true. `--include-consumers` is limited to 20 rows. A top-up alone does not
recreate deleted Fleet resources.

## Billing pause: current safe operator path

`status: active` is control-plane intent, not delivery proof; start with
`health` when a feed is quiet. `audit` records provider evidence and `repair`
converges existing intent. Neither resumes a zero-credit pause.

There is no org-wide direct-monitor resume. After credits or a cap are fixed:

1. Read `deepline monitors health` until it no longer reports refreshing.
2. Reactivate a credit-suspended Fleet through its retained owner:

   ```bash
   deepline monitors fleets reactivate <fleet-id> --yes --wait
   ```

3. For a fully disabled direct monitor, read its cost before recovery:

   ```bash
   deepline monitors reactivate <key> --dry-run
   deepline monitors reactivate <key>
   ```

Do not fan out direct recovery while suspension is still stopping resources: it
can race delete/create. Report that gap rather than inventing bulk recovery.

## Recover from errors by code

Read the returned state before retrying. For validation errors, correct every
reported field against the live contract and rerun `check`. For insufficient
credits, report the required credits, balance, and shortfall, then stop. Retry a
transient read or check once; do not blindly repeat a create, settlement, or
cleanup failure.

## Operate safely

Validate every definition with `check`; use `deploy --dry-run` before a paid
operation. An update has no dry-run: read the stored definition, check the merged
shape, apply only the requested patch and read it back. Public keys and rows
remain, but the upstream resource may be replaced; an ordinary update does not
promise backfill.

Before deployment, page `monitors list --status all` to completion. Reuse matching
tool/scope; explicitly reactivate a disabled match rather than duplicate it.
Inspect shared streams and known consumers: `sqlListeners.where` limits a Play's
reaction, not ingestion charges.

For Fleet work, prove a bounded scout first and save each deploy/read-back result.
On a 409, read the new state before retrying. Return provider rate-limit waits;
never blindly repeat a create. For an empty pilot, use “Observe and refine”
readiness checks and the approved history loop; do not widen unrelated filters
or claim broken coverage. Report live Deepline pricing only, with unknown total
volume where event-priced; never expose provider spend.

## Update and downstream automation

When the user changes a monitor, report the requested change, the active scope,
known downstream Plays, and live Deepline pricing. Do not claim an arbitrary
title expression is broader or narrower. A disabled monitor stores updates but
does not contact the provider until reactivated.

A monitor writes event rows; a Play can react to each row with a `sqlListeners`
trigger for the tool and stream shown by `deepline describe`. Use a `where` clause only
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
  `deepline describe <tool-id>`.
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
