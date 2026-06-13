# Sample Workflow: Product Usage To Campaign Draft

Public-safe illustrative workflow. Not deployed.

## Overview

Turns product usage from the warehouse into a draft GTM action. The workflow joins product events to CRM context, scores the reason for outreach, applies suppressions, and creates a campaign draft or rep task for review.

## Trigger

- **Type:** API
- **Source:** Internal GTM operator or scheduled workspace selection job
- **Input schema:**
  | Field | Type | Required | Description |
  | --- | --- | --- | --- |
  | workspace_id | string | yes | Product workspace to evaluate |
  | motion | string | yes | Sales assist, expansion, activation assist, or cross-sell |
  | dry_run | boolean | no | Keep all writes in preview mode |

## Steps

### Step 1: load_usage_snapshot

- **Purpose:** Pull recent product milestones and user activity for the workspace.
- **Outputs:** active users, top events, setup milestones, usage trend.

### Step 2: join_crm_context

- **Purpose:** Join workspace identity to CRM account, owner, lifecycle, open opportunity, customer status, and suppression flags.
- **Outputs:** account context and routing owner.

### Step 3: score_reason

- **Purpose:** Produce a score, reason, and recommended action.
- **Outputs:** `score`, `reason`, `recommended_action`, `message_context`.

### Step 4: apply_guardrails

- **Purpose:** Block risky records before activation.
- **Guardrails:** suppress customers unless expansion motion, suppress open opportunities, require owner, require clear reason.

### Step 5: create_draft_action

- **Purpose:** Create a draft campaign, rep task, or lifecycle action for human review.
- **Outputs:** draft ID, sample records, approval URL.

### Step 6: post_run_summary

- **Purpose:** Log moved, blocked, and updated records.
- **Outputs:** Slack/Notion summary and audit record.

## Data Flow

```text
workspace_id
-> usage snapshot
-> CRM context
-> score + reason
-> guardrails
-> draft campaign / task
-> run summary
```

## Expectations

| Input | Expected Output | Assertion |
| --- | --- | --- |
| High usage, no open opportunity, owner exists | Draft action created | `status = draft_created` |
| Customer with no expansion motion | Suppressed | `blocked_reason = customer_suppression` |
| No owner | Suppressed | `blocked_reason = missing_owner` |

