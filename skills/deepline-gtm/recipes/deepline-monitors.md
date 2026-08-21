---
name: deepline-monitors
description: 'ACCESS-GATED beta. Deepline Monitors are provider event feeds (job posts, email replies, funding, intent) that stream into Customer DB and can trigger Plays. Run `deepline monitors status` first; if it reports no access, stop and tell the user to contact Deepline.'
---

# Deepline Monitors

Monitors capture future events in Customer DB. A downstream Play is optional:
add one only when the user asks for an alert or another action.

## Choose the signal

Start with Deepline Native monitors. Confirm the live catalog before deploying;
names and pricing can change.

| User needs | Deepline Native monitor |
| --- | --- |
| Company job openings | Company radar: `company_job_openings` |
| New hires | Company radar: `company_new_hires` |
| Promotions | Company radar: `company_promotions` |
| News or web mentions | Company radar: `company_mentions` |
| Reviews | Company radar: `company_reviews` |
| Company social activity | Company radar: `company_social_posts` or `company_social_engagements` |
| Industry-wide mentions | Industry radar: `industry_mentions` |
| Industry-wide hiring | Industry radar: `industry_job_openings` |

Do not offer job-change monitors in this flow. If the user asks to track job
changes for known people, use the existing prebuilt instead:
`deepline plays search "job change" --json`, then
`deepline plays describe prebuilt/job-change-check --json`. It is billed only
for a confirmed move, which is the more cost-effective default for that request.

## Available filters

Use the live contract as the final authority:
`deepline tools get <tool-id> --json`. The current Deepline Native surface is:

| Signal | Target | Provider-side filters |
| --- | --- | --- |
| Company job openings | `domain` | `job_titles` **or** `departments` and `seniorities`; `updates_since` |
| New hires | `domain` | `job_titles` **or** `departments` and `seniorities`; `updates_since` |
| Promotions | `domain` | `job_titles` **or** `departments` and `seniorities`; `updates_since` |
| Company mentions, reviews, social posts, social engagements | `domain` | `updates_since` only |
| Industry mentions, industry job openings | `industry` | `countries`; `updates_since` |

`job_titles` is a Boolean expression with uppercase `AND`, `OR`, and `NOT`;
quoted phrases and parentheses work. It overrides `departments` and
`seniorities`, so do not send both forms. `updates_since` is the historical
boundary for a new radar, not a filter to revise during calibration. Do not
invent a title, department, seniority, or geography filter when the selected
row does not list it.

## Calibrate the filter

A deployed filter is still a hypothesis. Test the same target, signal, and
provider-side filters that the ongoing watcher will use before calling it done.

1. Infer domains, monitor type, and filters from the request. Ask only when a
   missing signal, target, or requested destination changes the outcome.
2. Build the broadest filter that still expresses the signal. This applies to
   any live filter: title, department, seniority, geography, event category, or
   another supported field. For GTM hiring, a broad title set is only one case.
3. Read the live contract, run `check`, then `deploy --dry-run`. Report actual
   Deepline pricing. A dry-run validates configuration, not signal quality.
4. When history is supported, use one price-approved historical preview. Start
   Deepline Native at 30 days unless the live price calls for a narrower window.
   In a customer workspace, ask one approval question after showing its price.
   In an internal/test workspace, proceed. Skip the preview only for an explicit
   forward-only request or a forward-only contract.
5. Inspect real rows. Keep a fit, refine a demonstrated off-target pattern, or
   stop a bad signal. Do not invent examples or substitute a people search.

For a monitor with no provider-side filter, calibrate the event type, target,
and time boundary instead. Do not invent a filter the live schema does not
support.

## Keep the conversation out of the way

Do the domain recovery, filter syntax, key/name, and monitor selection yourself.
Do not make a plan, configuration card, or implementation questionnaire. A
useful progress update is one sentence. The only extra customer approval is the
priced historical preview; forward monitoring stays within the requested scope.

## Access

Before any monitor command:

```bash
deepline monitors status --json
```

Proceed only when `has_access` is true. `has_access: false` is a rollout denial;
other failures need diagnosis.

## Execute

1. Read the live monitor contract and all deployed monitors. Reuse a matching
   monitor; do not create a second monitor for the same provider identity.
2. Check and dry-run the complete definition. Use the returned price, stream,
   and replacement plan.
3. Deploy after the required preview approval. Read it back. If a Play consumes
   the stream, state how incoming rows change.
4. Run a validation-only payload test only when `get` supplies a
   `sample_payload` and the workspace rule permits it. This proves payload
   acceptance, not filter quality.

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

## Observe and refine

`updates_since` is a permanent radar boundary, not pagination. Use one
price-approved, contract-supported historical window. Do not change it during
calibration: doing so replaces the upstream radar and can restart billable
historical ingestion.

Capture `observation_started_at` before deployment. For Deepline Native, read
only rows with the monitor's `_dl_monitor_id` and a later `_dl_received_at`.
Use the live schema for all fields. A missing output table or monitor-to-row
binding is an operational failure, not an empty sample.

### Customer communication

Explain the small paid preview before starting: what will be watched, what a
useful match looks like, where it will go, and that the filters will be tuned
before a wider rollout. Keep it plain. For a person, a LinkedIn URL lets a
Deepline Native monitor watch that person directly; a company domain watches the
company.

Use a bounded two-minute first check. Send a short update at about 45 seconds;
show a small result table if there are matches. If not, say that no match has
arrived yet and continue the check. Historical matching can continue afterward.

- At 45 and 90 seconds, report waiting only when useful.
- At 120 seconds with no row or provider error, return **no sample yet** and
  leave the monitor active. Do not call the filter wrong, replace the monitor,
  mutate `updates_since`, or run a generic same-signal probe.
- When rows arrive, keep matching patterns and remove only an observed
  off-target pattern. Verify the stored update, then observe it forward. An
  update does not request new historical matches.

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

```bash
deepline monitors delete <key> --dry-run --json
deepline monitors delete <key> --yes --json
deepline monitors list --status active --json
```

Deletion stops future ingestion but leaves existing Customer DB rows.

## Shared streams

Monitors write to shared streams. A Play subscribes to a tool and stream, not a
monitor key. `sqlListeners.where` controls which rows wake a Play; it does not
reduce event ingestion or charges. Inspect existing monitors and dependent Plays
before any mutation, then state the stream impact and live Deepline price.

## Empty pilots and errors

No event in a small pilot is inconclusive. Confirm the monitor is active, stored
filters are correct, and the Play listens to the actual stream. State the sample
and observation window. If the first historical window is too thin to decide
and the contract supports more history, offer the next farther-back window with
its live price. In a customer workspace, get approval for that additional paid
preview. Do not rewrite `updates_since` to simulate it. Otherwise, wait for
forward observation. Do not report a coverage percentage or call the signal
broken from an empty pilot.

For errors: retry a transient read or check once; correct validation failures;
re-browse an unknown type; report a credit shortfall and stop; inspect state for
settlement or cleanup failures. If a deploy says the monitor source is rate
limited, show that result and let the customer decide whether to retry after the
stated wait. Do not quietly retry a create: the source may have applied it even
when Deepline could not confirm completion. A billing-suspended monitor remains
disabled until the user approves `monitors reactivate <key> --dry-run` and
reactivation.

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
