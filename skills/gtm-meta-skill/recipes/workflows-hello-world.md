---
name: workflow-hello-world
description: "Create a cloud Deepline workflow that runs on a recurring cron schedule or via webhook, inspect it, and validate trigger behavior end to end."
---

# Cloud Workflow Triggers

Create a real Deepline cloud workflow with `deepline workflows apply`, trigger it on a recurring schedule or via webhook, inspect runs with `deepline workflows tail`, and verify lifecycle with `disable`, `enable`, and `delete`.

**Order of operations matters: do the basic stuff first.** Build and verify the simple child workflow directly before you build the batch workflow that fans out into it. If you skip that order, you won’t know whether the bug is in the child workflow, the parent workflow, the trigger, or the fanout code.

**State-first rule:** when the user references an existing campaign, workflow, search, or destination system, inspect that live state first. Reuse existing ids, filters, and payload shape before you ask for new ICP criteria. Only ask for targeting inputs if no search definition exists anywhere you can inspect.

## When to use

- "Show me how to create a cloud workflow that runs every day"
- "I want a webhook-triggered workflow, not a local enrich loop"
- "Give me the smallest recurring or webhook workflow I can ship"

## What NOT to do

| Anti-pattern | What happens | Why it fails |
|-------------|-------------|-------------|
| Start with a big provider-heavy workflow | You debug triggers, providers, auth, and output shape all at once | First prove the cloud trigger surface with tiny `run_javascript` steps |
| Push large CSV parsing, XLSX handling, or dependency-heavy JS through default cloud `run_javascript` | The QuickJS cloud runtime hits tight memory/time limits and fails on heavier ETL | For complex cloud workflow compute, set `payload.runInSandbox = true` so `run_javascript` executes in the Daytona sandbox runtime instead |
| Put `row.input.*`, `{{first_name}}`, or CSV fields into a cron workflow | `workflows apply` fails or the run has no useful input | Scheduled workflows must be self-contained because nothing calls them with external row data |
| Omit `trigger_tool` or `trigger_id` on a webhook workflow | Validation rejects the workflow | Webhook triggers require a concrete tool and trigger id binding |
| Treat webhook payload fields as top-level in JS | Your code reads empty values | Workflow calls/webhooks deliver user payload under `row.input` |
| Read prior step output as `row.previous_alias.some_field` | Later steps see `undefined` | Local tool output is wrapped, so read `row.previous_alias.result.some_field` |
| Build the parent fanout workflow before the child workflow works on its own | You cannot tell whether failures come from child logic or dispatch | First make the child workflow callable directly and verify one good run |
| Assume `triggerWorkflow(...)` waits for child results | The parent finishes without child outputs in-line | `triggerWorkflow(...)` is async fanout; inspect child runs separately |
| Ask the user for ICP/search criteria again after they already referenced an existing campaign or search | You lose momentum and ignore recoverable state that already exists | Inspect the current campaign, workflow, and search definition first; only ask for missing targeting inputs if nothing reusable exists |

## Steps

### Step 1: Create a recurring cloud workflow - deliver

Start with a tiny cron workflow that proves the scheduler and output shape.

```bash
python3 - <<'PY'
import json, subprocess

payload = {
  "name": "workflow_cloud_cron_demo",
  "publish": True,
  "trigger": {
    "type": "cron",
    "cron": "0 9 * * 1-5"
  },
  "config": {
    "version": 1,
    "commands": [
      {
        "alias": "build_payload",
        "tool": "run_javascript",
        "payload": {
          "code": "return { source: 'cron', message: 'Scheduled workflow fired', schedule: '0 9 * * 1-5' };"
        }
      },
      {
        "alias": "inspect",
        "tool": "run_javascript",
        "payload": {
          "code": "const payload=(row.build_payload&&row.build_payload.result&&typeof row.build_payload.result==='object')?row.build_payload.result:{}; return { ok: payload.source === 'cron', preview: payload.message || null };"
        }
      }
    ]
  }
}

subprocess.run(
  ["deepline", "workflows", "apply", "--payload", json.dumps(payload), "--json"],
  check=True,
)
PY
```

**Output:** A persisted workflow with a workflow id, published revision, and `cron` trigger.
**Checkpoint:** Save the workflow id immediately.
**Fallback:** If apply fails, validate the cron with standard 5-field syntax like `"0 9 * * 1-5"`.

### Step 2: Verify the recurring trigger is active - inspect

Confirm the workflow is listed as a recurring cloud workflow.

```bash
deepline workflows list
deepline workflows get --workflow-id <WORKFLOW_ID> --json
```

**Output:** The workflow appears with trigger type `cron` and a next scheduled time.
**Checkpoint:** `workflows list` should show a `cron` schedule, not `api`.
**Fallback:** If the workflow appears without a schedule, re-run `apply` and confirm the payload includes `"trigger": { "type": "cron", "cron": "..." }`.

### Step 3: Inspect scheduled runs - deliver

Wait for the next scheduled run or use the workflow detail page after the scheduler fires, then inspect it directly.

```bash
deepline workflows runs --workflow-id <WORKFLOW_ID> --json
deepline workflows tail --workflow-id <WORKFLOW_ID> --run-id <RUN_ID> --interval-ms 1000 --json
```

**Output:** You see the scheduled run progress and final output.
**Checkpoint:** Confirm:
- `build_payload.result.source = "cron"`
- `inspect.result.ok = true`
- `inspect.result.preview = "Scheduled workflow fired"`
**Fallback:** If no run appears yet, check the next scheduled time from `workflows get` and wait for that window.

### Step 4: Create a webhook cloud workflow - deliver

Create a second workflow that runs from an inbound webhook instead of a schedule.

```bash
python3 - <<'PY'
import json, subprocess

payload = {
  "name": "workflow_cloud_webhook_demo",
  "publish": True,
  "trigger": {
    "type": "webhook",
    "trigger_tool": "webhook",
    "trigger_id": "inbound_demo",
    "trigger_name": "Inbound demo webhook"
  },
  "config": {
    "version": 1,
    "commands": [
      {
        "alias": "normalize_input",
        "tool": "run_javascript",
        "payload": {
          "code": "const source=(row.input&&typeof row.input==='object')?row.input:{}; const company=String(source.company||'unknown').trim() || 'unknown'; const event=String(source.event||'webhook').trim() || 'webhook'; return { source: 'webhook', company, event };"
        }
      },
      {
        "alias": "inspect",
        "tool": "run_javascript",
        "payload": {
          "code": "const normalized=(row.normalize_input&&row.normalize_input.result&&typeof row.normalize_input.result==='object')?row.normalize_input.result:{}; return { ok: normalized.source === 'webhook', preview: `${normalized.event}:${normalized.company}` };"
        }
      }
    ]
  }
}

subprocess.run(
  ["deepline", "workflows", "apply", "--payload", json.dumps(payload), "--json"],
  check=True,
)
PY
```

**Output:** A persisted workflow with a webhook binding and workflow id.
**Checkpoint:** Save the webhook workflow id and inspect `webhook_url` from `workflows get`.
**Fallback:** If validation fails, make sure `trigger_tool` and `trigger_id` are both non-empty strings.

### Step 5: Fire the webhook and inspect the run - deliver

Use the webhook URL returned by the workflow detail and send a small JSON payload.

```bash
deepline workflows get --workflow-id <WEBHOOK_WORKFLOW_ID> --json

curl -X POST "<WEBHOOK_URL>" \
  -H "content-type: application/json" \
  -d '{"company":"Rippling","event":"signup"}'
```

Then inspect the triggered run:

```bash
deepline workflows runs --workflow-id <WEBHOOK_WORKFLOW_ID> --json
deepline workflows tail --workflow-id <WEBHOOK_WORKFLOW_ID> --run-id <RUN_ID> --interval-ms 1000 --json
```

**Output:** A webhook-triggered run with the normalized payload.
**Checkpoint:** Confirm:
- `normalize_input.result.source = "webhook"`
- `normalize_input.result.company = "Rippling"`
- `inspect.result.preview = "signup:Rippling"`
**Fallback:** If no run appears, fetch the workflow again and confirm you posted to the exact `webhook_url`.

### Step 6: Validate lifecycle controls for cloud triggers - inspect

Disable each workflow and prove that cron/webhook delivery is blocked until re-enabled.

```bash
deepline workflows disable --workflow-id <WORKFLOW_ID>
deepline workflows disable --workflow-id <WEBHOOK_WORKFLOW_ID>
deepline workflows list

deepline workflows enable --workflow-id <WORKFLOW_ID>
deepline workflows enable --workflow-id <WEBHOOK_WORKFLOW_ID>
deepline workflows list
```

**Output:** Both workflows move to `disabled`, then back to `active`.
**Checkpoint:** The dashboard and CLI should both show disabled state while triggers are blocked.
**Fallback:** If you are unsure which workflow you changed, run `deepline workflows get --workflow-id ... --json` and check `"status"`.

### Step 7: Build the child workflow first - deliver

Before you try any fanout, inspect any existing campaign/search state, then create the single child workflow that does the real unit of work. Prove it directly with a webhook or API trigger and one tiny payload.

If the user already named a destination system or workflow target, inspect that state before asking questions. Examples:
- Existing Instantly campaign: fetch the campaign, confirm the target list/campaign id, and verify whether the expected lead is already present.
- Existing workflow: fetch it and inspect trigger type, status, and payload shape.
- Existing search or source definition: inspect the saved filters before asking for a brand new ICP.

Only ask for targeting criteria when you have checked the existing state and still cannot find a reusable search definition.

Example child workflow shape:

```json
{
  "name": "linkedin_post_to_reactors",
  "publish": true,
  "trigger": {
    "type": "webhook",
    "trigger_tool": "webhook",
    "trigger_id": "linkedin_post_to_reactors",
    "trigger_name": "LinkedIn post to reactors"
  },
  "config": {
    "version": 1,
    "commands": [
      {
        "alias": "inspect_input",
        "tool": "run_javascript",
        "payload": {
          "code": "const source=(row.input&&typeof row.input==='object')?row.input:{}; return { post_url: source.post_url || null, profile_url: source.profile_url || null, max_engagers_per_post: source.max_engagers_per_post || null };"
        }
      }
    ]
  }
}
```

Then call it directly first:

```bash
curl -X POST "<CHILD_WEBHOOK_URL>" \
  -H "content-type: application/json" \
  -d '{"profile_url":"https://www.linkedin.com/in/someone","post_url":"https://www.linkedin.com/feed/update/urn:li:activity:123","max_engagers_per_post":25}'
```

**Checkpoint:** Do not build the parent fanout workflow until the child workflow has one clean successful run with the exact payload shape you intend to fan out.
**Fallback:** If the child workflow is wrong, fix it here before adding any parent workflow.

### Step 8: Add parent fanout only after the child works - deliver

Once the child workflow works alone, create the parent workflow that loops over records and enqueues child workflows with `triggerWorkflow(...)` inside `run_javascript`.

`triggerWorkflow(...)` is the correct helper for workflow fanout from JS:
- Pass a workflow name string: `triggerWorkflow("linkedin_post_to_reactors", {...})`
- Or pass an options object with `workflow_name` / `workflow_id`
- The call is async and queues child workflows without waiting for their results

Good parent-step pattern:

```javascript
const posts = Array.isArray(row.posts?.data) ? row.posts.data : [];
let queued = 0;

for (const post of posts) {
  const postUrl = typeof post.linkedinUrl === 'string' ? post.linkedinUrl.trim() : '';
  if (!postUrl) continue;

  triggerWorkflow("linkedin_post_to_reactors", {
    profile_url: row.profile_url,
    post_url: postUrl,
    post_id: post.id ?? null,
    max_engagers_per_post: row.max_engagers_per_post ?? 100,
  });
  queued += 1;
}

return { total_posts: posts.length, queued_posts: queued };
```

Rules:
- Keep parent fanout logic focused on selecting items and dispatching child workflows
- Keep child workflows responsible for the heavy lifting
- When the destination already exists, wire the parent to that known destination instead of inventing a new campaign or asking for new ids
- Return queue counts or summary data from the parent; do not expect child outputs in the same run
- Inspect child runs separately in the workflow UI or with `workflows runs`

**Checkpoint:** The parent run should prove dispatch count. The child workflows should prove business logic.
**Fallback:** If the parent says it queued N children but nothing happened, verify the child workflow name/id and inspect child workflow run history directly.

### Step 9: Graduate into a real cloud play - enrich

Once the trigger shape is proven, move real logic into the workflow. For cron, keep it self-contained. For webhook, expect dynamic payload under `row.input`.

Good cron examples:
- Daily account research
- Recurring syncs
- Scheduled outbound list refreshes

Good webhook examples:
- Inbound signup enrichment
- CRM event processing
- External automation fan-in

**Checkpoint:** First prove the business logic in a tiny `deepline enrich` or one-step workflow, then move it into the cloud workflow trigger you actually need.

### Step 10: Clean up demo workflows - deliver

Delete the demos when you are finished testing them.

```bash
deepline workflows delete --workflow-id <WORKFLOW_ID>
deepline workflows delete --workflow-id <WEBHOOK_WORKFLOW_ID>
```

**Output:** The demo workflows and related runs are removed.
**Checkpoint:** `deepline workflows get --workflow-id ...` should return `Workflow not found.`
**Fallback:** If you want to keep them for future testing, leave them disabled instead of deleting them.

## Gotchas

| Gotcha | What happens | Fix |
|--------|-------------|-----|
| You try to make a cron workflow depend on request payload | Scheduled runs have no external payload | Keep cron logic self-contained |
| You forget `trigger_tool` or `trigger_id` on webhook workflows | `workflows apply` rejects the config | Set both fields explicitly in the trigger object |
| You read webhook data from `row.company` instead of `row.input.company` | Your step sees empty values | Read inbound payload from `row.input` |
| You inspect only `workflows list` after firing a webhook | You miss the actual step payloads | Use `workflows runs`, `workflows run`, or `workflows tail` |
| You disable a workflow and expect webhook or cron delivery to continue | Triggers stop firing | Re-enable the workflow first |
| You use invalid cron syntax | Validation fails before save | Use standard 5-field cron syntax like `0 9 * * 1-5` |
| You put all scraping + parsing + fanout + enrichment into one workflow first | Debugging becomes opaque immediately | First validate the child workflow alone, then add parent fanout |
| You expect `triggerWorkflow(...)` to return child output to the parent step | The parent has only its own return value | Return dispatch metadata from the parent and inspect child runs separately |
