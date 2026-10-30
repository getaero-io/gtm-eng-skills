---
name: deepline-monitors
description: 'Deepline Monitors are provider event feeds (job posts, email replies, funding, intent) that stream into your warehouse and trigger plays.'
---

# Deepline Monitors

Monitors are **Deepline-native signal feeds**. The customer launch
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

The lifecycle below is internal. In every message, before or after approval,
never name history windows, dates, wait times or widening steps. The user needs
the next decision, not a monitoring log.

- **Ready to set up:** confirm scope first, then ask the three cards in
  “Sample-first setup,” one at a time. Keep domains, validation, monitor keys, and observation timing out of
  every card.
- **Calibrating from matches:** show the actual attributed rows in a Markdown
  table before any roll-up or recommendation. The table is the thing the user
  is calibrating against—counts and labels such as “relevant” are not enough.
  For new hires, use `Company / Person / Joined as / When` and put a verified
  LinkedIn link on the person's name, not in a separate `Profile` column.

For calibration, follow the artifact with one concrete recommendation and one
question: `Want me to use that, or adjust it?` This applies even when the call is
to leave the filter broad: the user explicitly asked to calibrate. During setup,
a noisy sample uses the improve card in “Sample-first setup” instead. For no
sample, failure, or stop, state that outcome directly; do not invent a scope or
results table.

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
live Deepline price per match, and action step in a short question. For variable
charges, say “charged as matches arrive” rather than estimating an unknown
total. Include any nonzero setup or recurring charge and material downstream
actions; omit zero-cost line items and absent charges. If consumers are unknown,
resolve them or explain the uncertainty before approval.

**Confirm scope first.** Unless the request already names them, ask one scope
card with two multi-select questions: which targets to watch (the named ones,
plus any recommended peers) and which signals count (for example product
reviews, social switching posts, news). Never assume the targets or signals, and
never fold an unconfirmed list into a later card. Then set up in three cards, in
this order (copy in “Sample-first setup”):

1. **Sample.** Ask to pull a small sample so that we can confirm it looks
   correct. The sample covers **one target per signal type**, not every
   target: pick the target most likely to produce a match for that signal (the
   largest or most reviewed company). Two signal types, such as reviews and
   social posts, need two samples. Name no company in the card: approval covers
   the sample deployment, the volume-based loop below, and moving on to the next
   most likely target when one comes back empty, without asking again, until
   each signal type has at least one attributable match. Then show the rows with
   the company each came from. If they are the requested signal, ask whether
   they look right; if most are noise, ask the improve card instead.
2. **Destination.** Ask where matches should go: Slack, CRM or outreach
   sequencer. Choosing one approves turning on every requested target with that
   action at the live per-match price.
3. **Send the sample.** Once the action Play is published, ask whether to send
   the sample through it so that we can see exactly how matches will arrive.

Never show history dates, windows, polling or replacement mechanics to the user.
History is a best-effort sample; say so only when it affects expectations.
Carry each approval through its step; ask again only if scope, price, action or
side effects exceed it. If history is unsupported, say a sample is unavailable
and start at the destination card. Honor an explicit future-only or
preview-only request without the sample card.

Choose each signal type's first window from the volume you expect for **that
signal** at the sample target, not from the company alone: a well-known brand
can be mentioned daily and reviewed a few times a year. Judge it from company
size, the brand's prominence for that signal, filter breadth and rows already in
the shared stream; when unsure, use moderate.

| Expected volume | Examples                                                                         | Start    | Widen if empty       | Wait per window |
| --------------- | -------------------------------------------------------------------------------- | -------- | -------------------- | --------------- |
| Very high       | likes and comments on a well-known brand's posts; mentions of a well-known brand | 1 day    | 7 days               | 3 minutes       |
| High            | mentions of a mid-size company; job openings at a large company                  | 3 days   | 7 → 30 days          | 3 minutes       |
| Moderate        | reviews of a well-known product; filtered roles at mid-size companies            | 30 days  | 180 → 365 → 730 days | 2 minutes       |
| Sparse          | executive hires, funding, a niche product's reviews, small companies             | 180 days | 365 → 730 days       | 2 minutes       |

Busy signals stop at 7 or 30 days: one that finds nothing in that window most
likely has no coverage, and a longer pull is where an unexpected bill comes from.
Even one day of a very high signal can be dozens of matches.

Deploy the sample radar with priority execution so history arrives faster, and
set `updates_since` to the first window's start:

```json
{
  "key": "<target>-<signal>-sample",
  "tool": "deepline_native.company_radar",
  "payload": {
    "domain": "<target domain>",
    "radar_type": "<radar type>",
    "updates_since": "<first window start>"
  },
  "controls": { "execution_type": "priority" }
}
```

Only the sample radar is priority; every other radar is created without
`controls.execution_type`. Priority does not change the price. Poll every 30
seconds for the
tier's wait after provider activation. If no attributable match or pending
finding has arrived and all readiness checks pass, replace through the normal
monitor lifecycle with the tier's next boundary and wait again. Never widen past
the tier's last window unless the user asks, even for a single target, although
the contract allows five calendar years. If the tier's last window produces no
match, tear that attempt down (below), then move to the next most likely target
for that signal type, from its own first window, without asking again; if that target is
also empty, say no sample was found and continue to the destination card. This
is a setup observation budget, not scan completion. Use “Observe and refine.”

**Tear down every sample attempt before the next step.** Sample approval does
not cover ongoing matches, and an empty observation is not a stopped feed:
history can keep arriving for 24 hours. Tear an attempt down as soon as it has
rows, without waiting for other signal types; when its last window comes back
empty, before trying the next target; and when the user skips or abandons
setup, before asking anything else. Its stored rows remain.

1. Stop it with `deepline monitors stop <key>`. The stop returns a Monitor Job;
   wait for it with `deepline monitors jobs wait <job id>`.
2. Confirm `deepline monitors get <key>` reads `inactive`.
3. Release its priority slot, which a stopped monitor still holds:

```bash
deepline monitors update <key> '{"controls":{"execution_type":null}}'
```

Never change `controls` on an active monitor: that replaces the radar with the
same window, and the replacement pulls the history and charges for it again. If
the stop job fails or the monitor does not read `inactive`, report it and do not
patch, restart or move on.

Honor an explicit time boundary or future-only request. Do not replay history
when merely recovering a billing-suspended monitor. For a type without history,
use its documented forward behavior and say historical sampling is unavailable;
do not invent `updates_since` or a substitute provider.

Calculate every candidate date from the same setup time. Where the live
contract uses calendar-month precision, retain requested and effective start
dates in validation output; keep them out of the approval. For
new hires/promotions, validate that the first window's
timestamp is outside the current month. A short window may still be in the
current month: use and validate the previous month's start. Explain exact
dates if the user asks or supplies a boundary that rounding would exceed;
never silently widen that explicit boundary. SDK/API omission remains a
future-only start; this historical default is an agent setup choice.

"Similar companies" is a billable scope decision. Resolve and, when useful,
recommend a small evidence-based candidate list, but do not deploy those
candidates merely because they seem plausible. Show their names and inclusion
decision in the scope table; keep resolved domains with the definition unless
the user needs them.

**Every monitor ends in an action.** Before approval, check what is connected:
`deepline notifications slack channels` for Slack, and
`deepline search "monitor match -> CRM record or task" --categories crm` for a
CRM, and `--categories sequencing` for an outreach sequencer. Recommend the
connected step that fits best—post each match to a named channel, create or
update the matching CRM record or task, or add the matched contact to a named
sequence—and still list the other two as alternatives, marking any that need
connecting first. Ask this as its own card after the sample is confirmed. Build
the chosen step as a Play with a `sqlListeners` trigger on the monitor's stream
and publish it **before** starting the sample monitor or deploying the other
targets: a listener fires only for rows written after it exists. Start the
stopped sample monitor with `deepline monitors start <key>`, which restarts it
at regular execution because its priority was released, and deploy the other
targets without `updates_since` or `controls.execution_type`; the sample already
supplied the history. If
none is connected, say so and ask the user to connect Slack, a CRM or a
sequencer in Dashboard → Integrations before turning it on. Never present the
raw Customer DB table as the destination; it is only the fallback when the user
declines an action.

**Send the sample through the action.** The sample rows were stored before the
Play existed, so the listener never saw them. A manual run skips the listener's
`where` filter, which normally runs in the database before the Play starts, so
select only the stored sample rows the published listener would accept: apply
its `where` conditions in the SQL that reads the sample rows. Skip the rest.
After the user approves, run the published Play once per eligible row with the
event it would have received:

```bash
deepline plays run <play> --input @sample-event.json
```

```json
{
  "tool": "<monitor tool>",
  "stream": "<stream>",
  "operation": "INSERT",
  "before": null,
  "after": { "<the stored row, every column>": "..." },
  "changedAt": "<the row's _dl_ingested_at>",
  "metadata": {
    "outboxId": "sample:<the row's _dl_dedupe_key>",
    "listenerId": "sample",
    "table": "<schema.table>"
  }
}
```

Run each sample row exactly once: a manual run is not deduplicated, so a second
run repeats the action. Read the run back and confirm the action happened (the
Slack post, CRM write or enrollment). For a sequencer, the card must say that these people will be
enrolled; never enroll a sample without that approval.

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
and price lookup directly, then send the sample card below. One choice card per
step is useful; a questionnaire about routine configuration is not. Keep titled plans, diagrams, raw definitions, and
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
- **Time:** for supported history, run the volume-based setup loop on the
  sample target only, waiting the tier's wait per active binding. Other targets
  start without history. Respect explicit time limits and future-only requests.
  Do not exceed the approved boundary without revised approval.
- **Action:** recommend a Slack, CRM or sequencer step on every monitor. Leave
  matches only in the Customer DB stream when the user declines one.
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

## Explain the monitor only when useful

After validation or deployment, use a sentence when the user needs the model:
the monitor keeps watch; a matching event enters the shared signal feed; its
action Play then notifies Slack, updates a CRM, creates a task, or enriches
the company. Do not render a diagram or a setup summary before doing the work.

The important boundary is that a monitor does not itself send Slack messages,
and it does not create a private channel for one workflow. Several monitors can
write to the same feed; each Play decides which new rows deserve action. That
keeps one useful source of truth, but a Play filter controls downstream action
only, not monitor ingestion cost.

## Observe and refine

`updates_since` is a radar boundary, not pagination. Historical widening can
replace the upstream resource and restart billable ingestion. Validate the
widest-boundary definition and its live price before the initial approval, use the
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

Record the setup start time before the first sample deploy, then inspect
monitor state and attributed rows every 30 seconds until the tier's wait ends.
Count rows by monitor key and receive time with exactly this query:

```bash
deepline db query --sql "select count(*) as n, max(_dl_received_at) as last_received from <output table> where _dl_monitor_id = '<key>' and _dl_received_at >= '<setup start time>'"
```

It counts every window since setup started, so replacing a window never hides
rows that are still arriving. Do not filter on `_dl_monitor_binding_version`
during setup: it is stored as text, and comparing it with the numeric
`binding_version` fails. A non-zero exit or error output is **unknown**, never
zero: fix the query and check again before widening. Reset the timer after
widening. `last_received_event` proves raw receipt only; it does not prove typed
storage or downstream Play delivery, but a value newer than the current window's
start means delivery has begun, so keep waiting instead of widening.

| Observation at the cutoff                                                                                               | Action                                                                                                                                                   |
| ----------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Attributable rows arrived                                                                                               | Show the real sample immediately and tear down this attempt; calibrate from the stored rows. Do not widen.                                               |
| Provider findings or callbacks arrived but rows are pending                                                             | Follow their delivery state; investigate a write failure. Do not widen or call it empty.                                                                 |
| Configuration, provider, table, binding or ingestion failed                                                             | Report **Blocked** with the failure; repair through the normal lifecycle. Do not widen or claim no history.                                              |
| A binding short of the tier's widest boundary is ready, with no matching rows or pending findings after the tier's wait | Replace it with the tier's next boundary; setup approval already covers it.                                                                              |
| The widest-boundary binding is ready, with no matching rows or pending findings after the tier's wait                   | Tear down this attempt, then try the next most likely target once; if it is also empty, say **“No sample found during setup.”** and ask the destination. |

If an observed matching finding has an unreadable delivery state, report an
inconclusive sample and investigate it. With no observed matching finding or
known pending delivery, follow the tier's setup cutoffs; a scan-completion
flag is not required. Absence of rows does not prove full historical coverage.
Deepline Native documents historical delivery during the first 24 hours and
has no historical-scan completion flag. Early widening may interrupt remaining
processing of the narrower window. Retain this limitation in operational notes;
describe history to the user as a best-effort sample if needed. The final
message reports only the bounded observation. Later history may still arrive
from the active monitor. Do not claim complete historical coverage or a broken
signal from either timeout.

## How to communicate

Use one decision-shaped response, not a recap. Do not open with deployment,
credits, timing, history, or a checklist; those matter only once a real decision
is ready. Translate internal language: say “first pass,” “matches,” and “look
further back,” not “forward scout,” “accepted events,” or “historical rung.”

### Sample-first setup

Ask these after live validation, one card at a time. Use “we” in the copy.
Keep resolved domains, duplicate checks and monitor plumbing internal.

**1. Sample**

```markdown
I'd like to pull a small sample of recent <signal noun> so that we can confirm
it looks correct. Each <signal noun, singular> costs <live Deepline price>.

- Pull a sample (Recommended)
- Skip the sample
```

Name no company here, so an empty first target can move on to the next one
without another question.

When the sample arrives, show its rows as in “Calibration decision,” with the
company each came from, and for text signals first “Show the full text.” If
the rows are the requested signal, ask:

```markdown
Do these look like the <signal> you want?

- Yes, looks right
- Not quite
```

If most rows are not the requested signal (for example vendor marketing, the
company's own staff or hiring posts instead of complaints), or the user answers
“Not quite,” say what the noise is in one sentence and ask an improve card
before the destination. Offer two to four concrete changes, recommend one, and
say for each what it changes and whether it lowers cost. A Play filter only
changes what reaches the destination; every monitor match is still billed.

```markdown
Only <n> of <N> <signal noun> are <the requested signal>; most are <the noise
pattern>. How should we tighten it?

- <Remove the noise at the source, such as dropping a noisy signal type>
  (Recommended): <what changes>; <cost effect>.
- <Keep the signal and filter what is posted>: only <matching rows> reach
  <destination>; every <signal noun> is still billed.
- Keep it as is: <what the user keeps getting>.
```

Apply the choice, show any rows it changes, then continue to the destination
card.

**2. Destination**

```markdown
Where should <signal> for <every named target> go? Each one costs <live
Deepline price>, charged as it arrives.

- Slack: <connected channel> (Recommended)
- CRM: create or update a record or task. <Needs connecting first.>
- Outreach sequencer: add the person to a sequence. <Needs connecting first.>
```

Recommend the best connected option; mark the others that need connecting.

**3. Send the sample**

```markdown
Want me to send these <N> sample <signal noun> to <destination> so that we can
see exactly how they'll arrive? <M> others don't pass the filter we set.

- Yes, send them (Recommended)
- No, just new ones
```

For a sequencer, say what happens: “Add these <N> people to <sequence>? They'll
start getting emails.” <N> counts only the rows that pass the action's filter;
drop the second sentence when none were filtered out. Skip this card when no
sample was found or no row passes the filter.

Similar companies are a scope recommendation, not a silent expansion: name each
candidate and whether it is in this pass before the destination card.

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

**Show the full text.** For posts, reviews, mentions and replies, the user approves the words, and
your host may bar repeating third-party text in chat. As rows arrive, write
them to a file and display or attach it (with no such tool, run the command
in the user's terminal, then print the file there, because the command itself
prints only the export path); never substitute a summary:

```bash
deepline db query --format markdown --out <key>-sample.md --sql "select <who>, <when>, <url>, <text> from <stream table> where _dl_monitor_id = '<key>' and _dl_received_at >= '<setup start time>'"
```

Ask “Do these look like…” only after that.

Use the “Observe and refine” decision rules: inspect every 30 seconds, show
matches as soon as they arrive, and widen only along the chosen volume tier.
Do not ask for another approval already covered by setup consent.
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

## Operations reference

Deployment verification, finding monitor types and their filters, the command
set, the billing-pause recovery path, error-code recovery and the definition
shape (including priority execution) are in
[monitor operations](../references/monitor-operations.md). Read the matching
section there before running a monitor command you have not used in this session.

## Operate safely

Validate every definition with `check`; use `deploy --dry-run` before a paid
operation. An update has no dry-run: read the stored definition, check the merged
shape, apply only the requested patch and read it back. Public keys and rows
remain, but the upstream resource may be replaced; an ordinary update does not
promise backfill.

Before deployment, page `monitors list --state all` to completion. Reuse matching
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
