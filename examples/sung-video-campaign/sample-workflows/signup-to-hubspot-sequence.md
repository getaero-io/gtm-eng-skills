# Sample Workflow: Signup To HubSpot Sequence

Public-safe illustrative workflow. Not deployed.

## Overview

Adds a new qualified signup to the right HubSpot onboarding or nurture sequence. This is intentionally simple: normalize the signup, check CRM state, apply suppressions, create or update the contact, and enroll only when the record is safe.

## Trigger

- **Type:** Webhook
- **Source:** Product signup event
- **Input schema:**
  | Field | Type | Required | Description |
  | --- | --- | --- | --- |
  | email | string | yes | Signup email |
  | full_name | string | no | Name supplied at signup |
  | workspace_id | string | yes | Product workspace |
  | signup_source | string | no | Campaign, referrer, or source channel |
  | first_product_event | string | no | First meaningful product action |

## Steps

### Step 1: normalize_signup

- **Purpose:** Normalize email, domain, name, workspace ID, and source metadata.
- **Outputs:** clean signup object and personal-email flag.

### Step 2: check_hubspot_context

- **Purpose:** Look up matching contact, company, lifecycle stage, owner, subscription status, active deals, and customer status.
- **Outputs:** CRM context and suppression flags.

### Step 3: choose_sequence

- **Purpose:** Pick the correct HubSpot sequence or list.
- **Rules:**
  - Work email + no open opportunity -> onboarding sequence.
  - Personal email -> identity review queue, not sequence.
  - Existing customer -> customer education or suppress.
  - Enterprise domain + usage signal -> sales-assist task instead of automated sequence.

### Step 4: apply_suppressions

- **Purpose:** Prevent bad enrollments.
- **Guardrails:** suppress unsubscribed contacts, bounced contacts, customers unless explicit customer motion, active opportunities, competitors, internal/test domains, and records without consent status.

### Step 5: upsert_contact

- **Purpose:** Create or update the HubSpot contact with source, workspace ID, product milestone, and provenance fields.
- **Outputs:** HubSpot contact ID.

### Step 6: enroll_or_stage

- **Purpose:** Enroll safe contacts in the chosen sequence, or stage for manual review when the identity or routing is uncertain.
- **Outputs:** enrollment ID or review task ID.

### Step 7: post_run_summary

- **Purpose:** Log enrolled, staged, and suppressed counts with reasons.
- **Outputs:** run summary for Slack/Notion/audit table.

## Data Flow

```text
signup webhook
-> normalize email and domain
-> check HubSpot contact/company/deal state
-> choose sequence or review queue
-> apply suppressions
-> upsert contact
-> enroll or stage
-> run summary
```

## Expectations

| Input | Expected Output | Assertion |
| --- | --- | --- |
| Work email, new contact, no open opportunity | Contact enrolled in onboarding sequence | `status = enrolled` |
| Personal email signup | Staged for identity review | `status = needs_identity_review` |
| Existing open opportunity | Suppressed | `blocked_reason = open_opportunity` |
| Unsubscribed contact | Suppressed | `blocked_reason = unsubscribed` |

