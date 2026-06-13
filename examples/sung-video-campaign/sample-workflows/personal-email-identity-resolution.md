# Sample Workflow: Personal Email To LinkedIn Identity Resolution

Public-safe illustrative workflow. Not deployed.

## Overview

Resolves high-intent personal-email signups into verified LinkedIn/profile context without polluting CRM. The workflow searches candidate profiles, validates identity with corroborating signals, and stages uncertain matches for review.

## Trigger

- **Type:** Webhook
- **Source:** New signup or product activation event
- **Input schema:**
  | Field | Type | Required | Description |
  | --- | --- | --- | --- |
  | email | string | yes | Signup email |
  | full_name | string | no | Name supplied at signup |
  | workspace_id | string | yes | Product workspace |
  | product_context | object | no | Recent activation events |

## Steps

### Step 1: detect_personal_email

- **Purpose:** Check whether the email domain is personal.
- **Outputs:** `is_personal_email`, normalized username, available hints.

### Step 2: gather_context

- **Purpose:** Collect name, location, workspace domain hints, product usage, and any linked social/profile clues.
- **Outputs:** identity search context.

### Step 3: search_linkedin_candidates

- **Purpose:** Search for possible LinkedIn profiles using name, handle clues, company hints, and location.
- **Outputs:** candidate URLs with raw evidence.

### Step 4: validate_identity

- **Purpose:** Require strong name match and at least two corroborating signals before writeback.
- **Valid signals:** company/domain match, location match, matching social handle, personal site/GitHub link, title/role fit.

### Step 5: route_or_stage

- **Purpose:** Write back only verified identity; otherwise stage for review.
- **Outputs:** verified LinkedIn URL, likely company, confidence reason, or review queue item.

### Step 6: log_decision

- **Purpose:** Keep provenance and explain why a record was written, staged, or suppressed.

## Data Flow

```text
personal email signup
-> identity hints
-> LinkedIn candidates
-> validation gate
-> verified writeback or review queue
-> audit log
```

## Expectations

| Input | Expected Output | Assertion |
| --- | --- | --- |
| Personal email + high usage + validated profile | LinkedIn staged or written back | `confidence >= threshold` |
| Name mismatch | Suppressed | `blocked_reason = name_mismatch` |
| One weak signal only | Review queue | `status = needs_review` |

