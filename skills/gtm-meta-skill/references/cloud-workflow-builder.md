# Cloud Workflow Builder

Build cloud workflow specs with step definitions, data contracts, and expectations, then deploy them via `deepline workflows apply`.

The core loop: **Intent → Discover → Spec → Implement → Deploy → Verify → Iterate**

---

## Capture Intent

Before writing anything, understand what the user wants. Ask about anything that isn't clear:

1. **What does this workflow do?** One sentence. What's the business outcome?
2. **What triggers it?** Webhook (external event), cron (schedule), or API (on-demand)?
3. **What's the input?** What fields arrive in the trigger payload?
4. **What's the output?** What should exist after the workflow runs — DB rows, API calls, notifications?
5. **What are the steps at a high level?** Validate → enrich → score → route → persist, or something else?
6. **Edge cases?** What happens when enrichment returns nothing? When a required field is missing? When a condition could go either way?
7. **Is there an existing workflow to build on?** Check with `deepline workflows list --json`.

Don't proceed until intent is clear. If the user is vague on edge cases, propose likely ones and ask them to confirm.

---

## Anatomy of a Cloud Workflow

### Key Concepts

**Workflow → Revision → Run → Step**

- **Workflow**: Named container with status (`active` | `disabled`). Has a trigger binding.
- **Revision**: Versioned snapshot of the workflow config. Only one published revision is active at a time. Each publish increments the version number.
- **Run**: Single execution instance, triggered by webhook/cron/API call. Tracks input, output, status (`pending` → `dispatched` → `running` → `completed` | `failed`).
- **Step**: Individual command execution within a run. Status: `running` | `skipped` | `completed` | `missed` | `failed` | `retrying`.

### Schema

**WorkflowApplyInput** (what you pass to `deepline workflows apply`):
```
{
  name: string                    # Required. Workflow name.
  status?: 'active' | 'disabled'  # Default: 'active'
  publish?: boolean               # Default: false. Auto-publish after create.
  specification?: string          # Markdown doc with ## Goals, ## Description, ## Inputs, ## Expected Outputs sections.
  config: {
    version: 1                    # Must be 1. Only supported version.
    commands: Command[]           # At least one command required.
  }
  trigger?: {
    type: 'webhook' | 'cron' | 'api'
    cron?: string                 # Required for cron type. 5-field expression.
    trigger_tool?: string         # For webhook: which tool generates events.
    trigger_id?: string           # For webhook: specific trigger identifier.
    trigger_name?: string         # Optional friendly name.
  }
}
```

**Command** (a single workflow step):
```
{
  alias: string                   # Unique name. Referenced by downstream steps.
  description?: string            # Short explanation of what this step does. Rendered in the pipeline UI.
  tool: string                    # Tool ID. Verify with `deepline tools get`.
  payload: Record<string, any>    # Tool input. Supports {{placeholder}} syntax.
  extract_js?: string             # JS to reshape output before storing.
  run_if_js?: string              # JS condition. Step runs only if truthy.
}
```

**Waterfall block** (parallel candidates with convergence):
```
{
  with_waterfall: string          # Group name for convergence tracking.
  description?: string            # Short explanation of what this waterfall does. Rendered in the pipeline UI.
  min_results?: number            # How many must succeed. Default: 1.
  commands: Command[]             # Flat array. No nested waterfalls.
}
```

### Execution Model

Steps execute **sequentially** by default. Each step's output is available to all downstream steps via placeholders.

**Waterfall blocks** are the exception: commands within a waterfall execute as parallel candidates. Once `min_results` commands succeed, remaining candidates are skipped. Results merge into `outputs[group_name]`.

**Placeholder resolution:**
- `{{input.field}}` — from the workflow call input or webhook payload
- `{{alias.result.field}}` — from a previous step's result (in payload templates)
- `{{alias.data.field}}` — from a previous step's data (enrichment tools return data here)
- Inside `run_javascript` code, use `row.alias.result.field` (JS object access, not template syntax)

**Retry policy:** 3 attempts with exponential backoff (1s base, 30s max, jitter enabled). Rate limits can be handled as wait, fallback (in waterfalls), or fail.

### run_javascript Environment

QuickJS runtime. No imports, no async/await, no fetch. Limits: 2s timeout, 16MB memory.

Available globals:
- `row` — all previous step outputs keyed by alias, plus original input
- `input` — original workflow call input
- `context` — alias for row
- `triggerWorkflow(name, input)` — enqueue a child workflow (async, non-blocking)
- `extract(value, data?, selector?)` — extract single value from a result
- `extractList(value, data?, selector?)` — extract array from a result

### Triggers

| Type | How it fires | Input | Constraints |
|------|-------------|-------|-------------|
| `webhook` | External HTTP POST to generated URL | POST body as `{{input.*}}` | Needs `trigger_tool` and `trigger_id` for tool-bound webhooks |
| `cron` | Scheduled via cron expression | None | Cannot reference `{{input.*}}`. Must be self-contained. |
| `api` | Manual via `deepline workflows call` | Call payload as `{{input.*}}` | On-demand only |

---

## Discovery

Before writing a spec, research what's available. Don't hardcode tool IDs or assume schemas — always verify.

### Existing workflows
```bash
deepline workflows list --json          # See what's already built
deepline workflows get --workflow-id <ID> --json  # Study step patterns
```
Look for patterns to reuse: similar enrichment chains, scoring logic, persist patterns.

### Available tools
```bash
deepline tools search "<what you need>"   # e.g. "enrich company", "send email", "scrape website"
deepline tools get <tool_id>              # Check exact input schema and description
```
Search by capability, not by provider name. The tool catalog has 800+ tools — there's likely one for what you need. Waterfall plays (multi-provider enrichment) show up in search results alongside single-provider tools.

### Database state
```bash
deepline customer-db query --sql "SELECT table_name FROM information_schema.tables WHERE table_schema = 'demo_crm'"
deepline customer-db query --sql "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'my_table'"
```
Understand what tables exist before defining new ones or writing to existing ones.

### Existing specs
Check `docs/` for any workflow spec documents. These contain the business logic, expected behavior, and reference configurations that the workflow should implement.

---

## Write the Spec

Save the spec to `docs/` before implementing. The spec is the source of truth — implementation follows from it.

**Always populate `specification` and per-step `description` when building or modifying a workflow.** The specification is a markdown string passed in the `WorkflowApplyInput`. It must include `## Goals`, `## Description`, `## Inputs`, and `## Expected Outputs` sections. Do not include a `## Steps` section — it is auto-generated from per-block `description` fields. Each command should have a `description` field explaining what that step does.

### Spec Template

````markdown
# Workflow: <name>

## Overview
One paragraph: what this workflow does, why it exists, what business outcome it produces.

## Trigger
- **Type:** webhook | cron | api
- **Source:** Where events originate (form submission, reply webhook, scheduled poll, etc.)
- **Input schema:**
  | Field | Type | Required | Description |
  |-------|------|----------|-------------|
  | field_name | string | yes | what this field is |

## Steps

### Step 1: <alias>
- **Tool:** `<tool_id>` (discovered via `deepline tools search`)
- **Purpose:** One line — what this step accomplishes.
- **Inputs:**
  | Field | Source | Type | Required |
  |-------|--------|------|----------|
  | domain | `{{input.email}}` split at @ | string | yes |
- **Outputs:**
  | Field | Type | Description |
  |-------|------|-------------|
  | is_valid | boolean | whether the input passed validation |
- **Condition:** `run_if_js` expression, if conditional. Omit if always runs.
- **On failure:** What happens — skip step, fail workflow, use default value.

(Repeat for each step.)

## Data Flow
```
input → validate → enrich → score → route → persist
         ↓           ↓        ↓       ↓        ↓
      lead_id,    title,    score,  actions,  DB write
      domain      company   reason  plan
```

## Expectations

### Happy path
| Input | Step | Expected Output | Assertion |
|-------|------|-----------------|-----------|
| VP Sales at CPG co, valid email | score | icp_score >= 60 | qualified |
| same lead | route | actions include create_deal | deal flagged |

### Edge cases
| Input | Step | Expected Output | Assertion |
|-------|------|-----------------|-----------|
| missing email | validate | skip: true | skipped early |
| enrichment returns empty | score | fallback score based on input only | graceful degradation |
| all waterfall providers fail | enrich | empty result, workflow continues | no crash |
| duplicate lead (already processed) | persist | upsert, not duplicate row | idempotent |

## Database Schema
```sql
CREATE TABLE IF NOT EXISTS demo_crm.my_results (
  id TEXT PRIMARY KEY,
  -- columns with types and defaults
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```
````

### Spec Conventions

- Every step has explicit input and output tables. No implicit data passing.
- Describe `run_javascript` logic in prose before writing the code.
- For enrichment, note whether you're using a waterfall play or single provider, and why.
- For `ai_inference`, include the prompt template and expected response shape.
- Mark steps as "dry-run" (produces plan but doesn't execute) or "live" (actually writes/sends).
- Explain the *why* behind scoring rules, conditions, and routing logic — not just the *what*.
- Edge case expectations are required, not optional. Cover at minimum: missing required field, empty enrichment, conditional branch both ways, duplicate/idempotent handling.

---

## Migrations

When the source of truth is a system artifact (Clay table export, n8n workflow JSON, etc.) rather than human-described steps, the spec is derived from that artifact — prompts verbatim, scoring logic verbatim, conditional rules verbatim. The spec should cite the source artifact and note any intentional adaptations.

The artifact also provides ground truth data for parity testing. After standard smoke testing, run **dry_run** against extracted ground truth rows and report a parity scorecard. See [cloud-workflow-migrations.md](cloud-workflow-migrations.md) for testing phases, thresholds, and mismatch diagnosis.

---

## Implement

Translate the spec into a `deepline workflows apply` payload.

### Payload structure
```json
{
  "name": "my_workflow",
  "publish": true,
  "config": {
    "version": 1,
    "commands": [
      {
        "alias": "validate",
        "tool": "run_javascript",
        "payload": { "code": "..." }
      },
      {
        "alias": "enrich",
        "tool": "some_enrichment_tool",
        "payload": { "domain": "{{validate.result.domain}}" }
      }
    ]
  },
  "trigger": { "type": "webhook" }
}
```

### Waterfall blocks

When you need multiple providers to attempt the same enrichment:
```json
{
  "with_waterfall": "company_data",
  "min_results": 1,
  "commands": [
    { "alias": "provider_a", "tool": "...", "payload": {...} },
    { "alias": "provider_b", "tool": "...", "payload": {...} }
  ]
}
```
First to return valid data wins. Cannot nest waterfalls inside waterfalls.

### Conditional steps

Use `run_if_js` to gate a step on a previous result:
```json
{
  "alias": "send_notification",
  "tool": "run_javascript",
  "payload": { "code": "..." },
  "run_if_js": "row.score?.result?.routing_decision === 'qualified'"
}
```

### Child workflow dispatch

Inside `run_javascript`, trigger other workflows:
```javascript
const rows = row.find_new?.result?.rows || [];
rows.forEach(r => triggerWorkflow('my_workflow', { lead_id: r.id }));
return { dispatched: rows.length };
```

### Common patterns

**Poll + dispatch** — a cron companion that finds new records and triggers the main workflow per-record:
```json
{
  "name": "my_workflow_poll",
  "config": { "version": 1, "commands": [
    { "alias": "find_new", "tool": "query_customer_db", "payload": { "sql": "SELECT * FROM my_table WHERE processed = false LIMIT 10" } },
    { "alias": "dispatch", "tool": "run_javascript", "payload": { "code": "..." } }
  ]},
  "trigger": { "type": "cron", "cron": "*/15 * * * *" }
}
```

**Execution modes** — test workflows without side effects or external calls:
```bash
# smoke_test: fixture data for enrichment, side-effect tools skipped
deepline workflows call --workflow-name my_workflow --payload '{"email":"test@acme.com"}' --mode smoke_test

# dry_run: real APIs for enrichment, side-effect tools skipped
deepline workflows call --workflow-name my_workflow --payload '{"email":"test@acme.com"}' --mode dry_run
```
Tools classified as side effects (writes to CRM, messaging, campaigns, persistence, LLM inference) are automatically skipped. Skipped steps return `{ __skipped: true, tool, payload }` for inspection — use this to verify prompt construction, payload shapes, and routing logic without external calls. The side-effect registry is in `src/lib/workflows/execution-mode.ts`.

**Disabled steps** — temporarily skip individual steps without changing workflow logic:
```json
{
  "alias": "create_company",
  "tool": "attio_create_company_record",
  "disabled": true,
  "payload": { ... }
}
```
Set `disabled: true` on any command to skip it at runtime. The step appears in the UI grayed out with a "Disabled" badge but remains in the workflow config. Use this during initial live runs to protect systems of record — disable CRM writes, campaign additions, or other hard-to-reverse side effects while validating that enrichment, scoring, and routing logic work correctly with real data. Once confident, remove the `disabled` flag and re-publish. This is more granular than `dry_run` mode (which skips ALL side-effect tools) — disabled lets you selectively control which steps run.

**Enrichment → score → classify** — enrich first, score with JS, confirm with LLM:
```
enrich_contact → enrich_company → score (run_javascript) → classify (ai_inference) → route → persist
```

---

## Deploy & Verify

### Deploy
```bash
deepline workflows apply --payload '<JSON>' --json
```
Check the response for `validation.status` — should be `"valid"`. If `"schema_drift"`, a tool reference couldn't be resolved. Run `deepline tools get <tool_id>` to verify the tool exists.

### Test call
```bash
# Smoke test first (fixture data, no side effects, no API keys needed)
deepline workflows call --workflow-name my_workflow --payload '{...}' --mode smoke_test --json

# Then dry run with real data (real enrichment, no side effects)
deepline workflows call --workflow-name my_workflow --payload '{...}' --mode dry_run --json

# Then live
deepline workflows call --workflow-name my_workflow --payload '{...}' --json
```

### Check run
```bash
deepline workflows runs --workflow-id <WF_ID> --run-id <RUN_ID> --json
```
Inspect per-step status and outputs. Steps skipped by execution mode show `missed` with reason `smoke_test: side_effect tool skipped` or `dry_run: side_effect tool skipped`.

### Check DB outputs
```bash
deepline customer-db query --sql "SELECT * FROM demo_crm.my_results ORDER BY created_at DESC LIMIT 5"
```

### Validate against expectations

Walk through the spec's expectations table:
1. **Happy path**: run with a representative input. Compare each step's actual output to expected.
2. **Edge cases**: run with each edge case input. Verify the workflow handles it per spec (skip, fallback, no crash).
3. **Idempotency**: run the same input twice. Verify upsert behavior, no duplicate rows.

If any assertion fails, identify which step diverged and whether the fix belongs in the spec or the implementation.

---

## Iterate

When expectations don't match:

1. **Identify the divergent step** — check run details to find where actual != expected.
2. **Decide: spec bug or implementation bug?** If the spec's expectation was wrong, update the spec. If the implementation doesn't match a correct expectation, fix the implementation.
3. **Update spec first**, then implementation. Keep them in sync.
4. **Re-deploy and re-verify** against the full expectations table, not just the one that failed.

Generalize fixes rather than patching specific cases. If one edge case exposed a gap, ask whether similar inputs would hit the same gap.
