# Sample Workflow: Event Attendee Follow-Up

Public-safe illustrative workflow. Not deployed.

## Overview

Turns event registrations or check-ins into timely GTM follow-up. The workflow normalizes attendee identity, enriches account context, segments by attendance and fit, suppresses risky records, and drafts follow-up for review.

## Trigger

- **Type:** Webhook
- **Source:** Event registration or check-in provider
- **Input schema:**
  | Field | Type | Required | Description |
  | --- | --- | --- | --- |
  | event_id | string | yes | Event identifier |
  | attendee_email | string | yes | Attendee email |
  | attendee_name | string | no | Attendee name |
  | attendance_status | string | yes | Registered, checked_in, no_show |

## Steps

### Step 1: normalize_attendee

- **Purpose:** Normalize email, domain, name, event status, and source metadata.
- **Outputs:** clean attendee object.

### Step 2: enrich_account_and_role

- **Purpose:** Hydrate account, company, title, seniority, and CRM context.
- **Outputs:** account context and contact role.

### Step 3: segment_event_signal

- **Purpose:** Decide whether the person needs same-day follow-up, nurture, sales routing, or suppression.
- **Outputs:** segment and recommended action.

### Step 4: apply_suppressions

- **Purpose:** Block customers, active opportunities, unsubscribed contacts, and low-confidence identity matches.

### Step 5: draft_follow_up

- **Purpose:** Create a draft email, CRM task, or list membership using event context.
- **Outputs:** draft ID or list ID.

### Step 6: sync_and_summarize

- **Purpose:** Sync approved records and post a run summary.
- **Outputs:** moved count, blocked count, suppression reasons.

## Data Flow

```text
registration/check-in
-> normalized attendee
-> account + role enrichment
-> event segment
-> suppressions
-> draft follow-up
-> list sync + run summary
```

## Expectations

| Input | Expected Output | Assertion |
| --- | --- | --- |
| Checked-in, high-fit prospect | Draft same-day follow-up | `segment = same_day_sales_assist` |
| No-show, low-fit account | Nurture or suppress | `segment != sales_assist` |
| Active opportunity | Suppressed | `blocked_reason = open_opportunity` |

