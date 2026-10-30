# Monitor operations

Lookup material for the [monitors recipe](../recipes/deepline-monitors.md):
deployment verification, monitor types and filters, commands, recovery paths and
the definition shape. Follow the recipe for setup, approval and observation.

## First proof of value: a minimally filtered scout

Do not make a customer wait days to discover whether the intended signal has
coverage. After approval, start the approved small scout batch with only the
target and requested event filters and the volume-based first window when
history is supported, then prove each stored definition after the write. This is the fastest feedback loop and guards against false success.

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
# CFO openings at one company are sparse: start 180 days back.
UPDATES_SINCE=$(node -e 'console.log(new Date(Date.now() - 180 * 86400000).toISOString())')
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
| `tools list --categories monitors` / `describe <tool-id>` | Discover live payload fields, streams and prices.                                                                   |
| `monitors check '<definition>'`                           | Validate without deployment or spend.                                                                               |
| `monitors deploy '<definition>'`                          | Apply a full desired definition; `--dry-run` previews validity, price and reuse.                                    |
| `monitors list`                                           | Page the registry with `--state` (`active` by default, or `all`), `--limit` and `--cursor`.                         |
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
calibration, such as the setup sample radar, and never for the targets turned on
after it. Deepline adds the provider-facing marker; do not put
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
