# Lead Magnet: Snowflake PQL to Campaign Playbook

Slug: `snowflake-pql-campaign-playbook`

Offer line: `Steal the Snowflake -> dbt -> CRM -> campaign workflow behind the Sung speedrun. Includes the query, dbt model, and activation play.`

Primary CTA: `Get the Snowflake PQL playbook`

Secondary CTA: `Comment PQL and I will send the query`

Notion share page: `https://app.notion.com/p/Snowflake-PQL-to-Campaign-Playbook-377da8d1d8eb8128b1bde0d84216bf2a`

## What This Gives The Reader

This is the implementation version of the Snowflake speedrun video.

The reader gets:

- A setup guide for turning product usage into GTM actions.
- A Snowflake query that turns product usage into a PQL queue.
- A dbt model they can adapt inside their own warehouse.
- A Deepline/Aero workflow play that syncs the right records to CRM and drafts a campaign.
- The guardrails that keep this from becoming another CSV upload ritual.

## Who This Is For

This is for the person who gets asked some version of:

> Can we take the product usage data in Snowflake, figure out which accounts sales should touch, and get the campaign drafted without waiting on engineering?

Usually that person is a growth engineer, GTM engineer, technical RevOps person, data-savvy growth lead, or founder who still owns the weird parts of outbound.

The guide assumes you have:

- Product usage events in Snowflake, BigQuery, Redshift, or another warehouse.
- A CRM such as Salesforce, HubSpot, or Attio.
- A campaign tool such as Instantly, Smartlead, Outreach, Salesloft, or HubSpot sequences.
- A rough idea of which product actions signal buying intent.

You do not need a perfect data model. You do need enough discipline to avoid turning every workflow into `final_final_pql_list_v4.csv`.

## The Setup In Plain English

The workflow has five parts:

1. **Define the signal.** Decide which product events suggest sales readiness.
2. **Score the account.** Combine usage, fit, CRM context, and suppression logic.
3. **Materialize the model.** Put the definition in dbt so it can rerun.
4. **Inspect the run.** Preview who will move, why, and what will be blocked.
5. **Draft the action.** Update CRM context and create a campaign draft, not a live blast.

The important part is not that the agent can connect to Snowflake.

The important part is that the workflow can answer:

```text
Why is this account in the campaign?
What data caused it to move?
What did we suppress?
Who approved the run?
Can we rerun this next week?
```

## Step 1: Pick The PQL Motion

Do not start with a universal score. Start with one GTM motion.

Good first motions:

- Trial users who did the setup work but never booked a meeting.
- Free workspaces showing team adoption.
- Accounts with high usage but stale CRM activity.
- Product users at accounts already owned by sales.
- Expansion accounts where usage changed before renewal.

Bad first motions:

- "Score every account in the database."
- "Tell sales who to call."
- "Find all intent."
- "Use AI to rank pipeline."

Those are too broad. You will spend the whole project arguing about the score instead of shipping the workflow.

## Step 2: Map Product Events To Buying Signals

Start with product events that imply effort, collaboration, or readiness.

Example event map:

| Product event | Why it matters | Example score |
| --- | --- | --- |
| `created_sequence` | User is trying to operationalize outbound | +25 |
| `connected_calendar` | Setup work completed | +15 |
| `invited_team_member` | Account is spreading beyond one user | +15 |
| `used_ai_assistant` | User is trying to automate work | +10 |
| `exported_contacts` | User is activating data | +20 |
| `connected_crm` | Account is close to GTM workflow value | +25 |
| `created_api_key` | Technical buyer is integrating | +20 |
| `ran_workflow_successfully` | User reached the product's useful moment | +30 |

The weights are not sacred. They are a starting point.

The better question is:

```text
Which events would make a rep say, "I know why I am reaching out"?
```

## Step 3: Add Fit And CRM Context

Usage alone gets noisy fast.

A student hammering the product for a weekend can look more active than a quiet enterprise account with one buyer doing serious setup.

Add fit and CRM context:

```text
fit signals:
- company domain
- employee count
- industry
- target segment
- existing customer status
- open opportunity status
- account owner

crm context:
- lifecycle stage
- last sales activity
- last sequence date
- open opportunity count
- customer flag
- suppression status
```

This is the difference between a PQL and a product activity report.

## Step 4: Decide The Action Before You Score

Every score needs an action.

If the action is unclear, the score will become dashboard furniture.

Example actions:

| PQL stage | Action |
| --- | --- |
| `sales_ready` | Draft rep-owned outbound campaign |
| `watchlist` | Add to Slack digest or CRM task queue |
| `expansion_signal` | Alert account owner with usage context |
| `implementation_risk` | Notify CS before renewal |
| `no_sales_action` | Keep in model, do not sync to campaign |

The campaign draft is only one option. Sometimes the right action is a Slack alert, CRM note, account owner task, or suppression.

## Step 5: Build The Guardrails First

Do this before writing clever scoring logic.

Minimum guardrails:

- Block customers from outbound campaigns unless the motion is expansion.
- Block accounts with open opportunities.
- Block unsubscribed or bounced contacts.
- Require account owner on sales-routed records.
- Keep new campaigns in draft mode.
- Show a 10-record sample before approval.
- Log which rows were moved, blocked, and updated.

If these are missing, the workflow is not production-ready. It is just a faster CSV.

## Mixmax-Inspired PQL Definition

Use this as the public-safe PQL pattern:

> A PQL is not just "used the product." It is an account or workspace where product usage and account fit predict sales readiness.

The Mixmax angle:

- Product usage signals become propensity scores.
- Reps focus on high-fit accounts before time gets spent on low-fit ones.
- The workflow is valuable because it reallocates rep attention, not because it creates another dashboard.

Public proof points from existing Deepline/Aero positioning:

- Mixmax saw a +53% relative win-rate improvement.
- Focus on high-fit accounts increased by +50%.
- 40% of prior rep activity was going to wrong or low-fit accounts.

Do not present the query below as Mixmax's exact production model. Present it as the implementation template for teams trying to operationalize the same idea.

## Implementation Checklist

Use this before you run the play:

```text
warehouse:
[ ] Product events table exists
[ ] Workspace/account table exists
[ ] Domains are normalized
[ ] Event timestamps are reliable
[ ] dbt can materialize the model

crm:
[ ] Account owner field exists
[ ] Lifecycle stage is trustworthy enough
[ ] Open opportunity flag is available
[ ] Customer suppression can be checked
[ ] Contact email status is available

campaign:
[ ] Campaign tool can create draft lists
[ ] Suppression list is connected
[ ] Sequence stays in draft mode
[ ] Owner can approve before launch

ops:
[ ] Run summary is stored
[ ] Blocked records are visible
[ ] Sample rows are reviewed
[ ] Someone owns follow-up
```

## Assumed Tables

Adapt the table names to the customer warehouse:

```text
analytics.product_events
analytics.workspaces
analytics.users
analytics.crm_accounts
analytics.crm_contacts
analytics.email_activity
analytics.billing_accounts
```

Minimum fields:

```text
product_events: workspace_id, user_id, event_name, event_ts
workspaces: workspace_id, account_domain, workspace_created_at, plan_name
users: user_id, workspace_id, email, role, created_at
crm_accounts: account_id, domain, owner_id, lifecycle_stage, open_opportunity_count, last_activity_at
crm_contacts: contact_id, account_id, email, title, seniority, last_activity_at
email_activity: email, last_reply_at, last_sequence_at, bounced_at, unsubscribed_at
billing_accounts: workspace_id, is_paid, mrr, trial_ends_at
```

## Snowflake Query

```sql
with recent_usage as (
  select
    workspace_id,
    count_if(event_name = 'created_sequence') as created_sequences_14d,
    count_if(event_name = 'connected_calendar') as connected_calendar_14d,
    count_if(event_name = 'invited_team_member') as invited_teammates_14d,
    count_if(event_name = 'used_ai_assistant') as ai_actions_14d,
    count(distinct user_id) as active_users_14d,
    max(event_ts) as last_product_activity_at
  from analytics.product_events
  where event_ts >= dateadd(day, -14, current_timestamp())
  group by 1
),

workspace_fit as (
  select
    w.workspace_id,
    lower(w.account_domain) as domain,
    w.plan_name,
    w.workspace_created_at,
    b.is_paid,
    b.mrr,
    b.trial_ends_at,
    datediff(day, w.workspace_created_at, current_timestamp()) as workspace_age_days
  from analytics.workspaces w
  left join analytics.billing_accounts b
    on b.workspace_id = w.workspace_id
),

crm_context as (
  select
    a.account_id,
    lower(a.domain) as domain,
    a.owner_id,
    a.lifecycle_stage,
    a.open_opportunity_count,
    a.last_activity_at as account_last_activity_at,
    max(c.last_activity_at) as contact_last_activity_at,
    count(distinct c.contact_id) as crm_contacts
  from analytics.crm_accounts a
  left join analytics.crm_contacts c
    on c.account_id = a.account_id
  group by 1, 2, 3, 4, 5, 6
),

best_contact as (
  select *
  from (
    select
      c.account_id,
      c.contact_id,
      c.email,
      c.title,
      c.seniority,
      e.last_reply_at,
      e.last_sequence_at,
      e.bounced_at,
      e.unsubscribed_at,
      row_number() over (
        partition by c.account_id
        order by
          case
            when lower(c.seniority) in ('founder', 'cxo', 'vp', 'head') then 1
            when lower(c.title) like '%sales%' or lower(c.title) like '%growth%' then 2
            else 3
          end,
          c.last_activity_at desc nulls last
      ) as contact_rank
    from analytics.crm_contacts c
    left join analytics.email_activity e
      on lower(e.email) = lower(c.email)
    where e.bounced_at is null
      and e.unsubscribed_at is null
  )
  where contact_rank = 1
),

pql_scoring as (
  select
    wf.workspace_id,
    wf.domain,
    cc.account_id,
    cc.owner_id,
    bc.contact_id,
    bc.email,
    bc.title,
    cc.lifecycle_stage,
    cc.open_opportunity_count,
    ru.active_users_14d,
    ru.created_sequences_14d,
    ru.connected_calendar_14d,
    ru.invited_teammates_14d,
    ru.ai_actions_14d,
    ru.last_product_activity_at,
    cc.account_last_activity_at,
    bc.last_sequence_at,
    wf.is_paid,
    wf.mrr,
    wf.trial_ends_at,
    (
      iff(ru.active_users_14d >= 3, 20, 0) +
      iff(ru.created_sequences_14d >= 2, 25, 0) +
      iff(ru.connected_calendar_14d >= 1, 15, 0) +
      iff(ru.invited_teammates_14d >= 1, 15, 0) +
      iff(ru.ai_actions_14d >= 5, 10, 0) +
      iff(wf.is_paid = false and wf.trial_ends_at between current_date() and dateadd(day, 10, current_date()), 15, 0)
    ) as product_score,
    (
      iff(cc.open_opportunity_count = 0, 15, 0) +
      iff(cc.lifecycle_stage in ('lead', 'marketingqualifiedlead', 'subscriber'), 10, 0) +
      iff(cc.account_last_activity_at is null or cc.account_last_activity_at < dateadd(day, -21, current_timestamp()), 10, 0) +
      iff(bc.last_sequence_at is null or bc.last_sequence_at < dateadd(day, -30, current_timestamp()), 10, 0)
    ) as activation_score
  from workspace_fit wf
  join recent_usage ru
    on ru.workspace_id = wf.workspace_id
  left join crm_context cc
    on cc.domain = wf.domain
  left join best_contact bc
    on bc.account_id = cc.account_id
)

select
  *,
  product_score + activation_score as pql_score,
  case
    when product_score >= 50 and activation_score >= 25 then 'sales_ready'
    when product_score >= 35 then 'watchlist'
    else 'not_ready'
  end as pql_stage,
  object_construct_keep_null(
    'why_now', array_construct_compact(
      iff(active_users_14d >= 3, '3+ active users in last 14 days', null),
      iff(created_sequences_14d >= 2, 'created 2+ sequences', null),
      iff(connected_calendar_14d >= 1, 'connected calendar', null),
      iff(invited_teammates_14d >= 1, 'invited teammate', null),
      iff(account_last_activity_at is null or account_last_activity_at < dateadd(day, -21, current_timestamp()), 'CRM account is stale', null)
    ),
    'recommended_action', iff(product_score + activation_score >= 75, 'draft_owner_followup', 'monitor')
  ) as rep_context
from pql_scoring
where pql_stage in ('sales_ready', 'watchlist')
order by pql_score desc, last_product_activity_at desc;
```

## dbt Model

File: `models/marts/gtm/fct_product_qualified_accounts.sql`

```sql
{{ config(
    materialized = 'incremental',
    unique_key = 'workspace_id',
    on_schema_change = 'sync_all_columns'
) }}

with pqls as (
  -- Paste the Snowflake query above here, or turn each CTE into a staging model.
  select * from {{ ref('int_product_usage_pql_scoring') }}
)

select
  workspace_id,
  domain,
  account_id,
  owner_id,
  contact_id,
  email,
  title,
  lifecycle_stage,
  active_users_14d,
  created_sequences_14d,
  connected_calendar_14d,
  invited_teammates_14d,
  ai_actions_14d,
  product_score,
  activation_score,
  pql_score,
  pql_stage,
  rep_context,
  last_product_activity_at,
  current_timestamp() as scored_at
from pqls
where pql_stage = 'sales_ready'

{% if is_incremental() %}
  and last_product_activity_at >= (
    select coalesce(dateadd(day, -2, max(last_product_activity_at)), '1900-01-01')
    from {{ this }}
  )
{% endif %}
```

Suggested dbt tests:

```yaml
version: 2

models:
  - name: fct_product_qualified_accounts
    columns:
      - name: workspace_id
        tests:
          - not_null
          - unique
      - name: domain
        tests:
          - not_null
      - name: pql_score
        tests:
          - not_null
      - name: pql_stage
        tests:
          - accepted_values:
              values: ['sales_ready']
```

## Deepline/Aero Workflow Play

Use this as the shareable workflow/play:

```yaml
name: snowflake_pql_to_campaign
goal: Turn warehouse PQLs into a CRM-owned campaign draft without hand-uploading CSVs.

inputs:
  snowflake_model: analytics.fct_product_qualified_accounts
  crm: hubspot_or_salesforce
  campaign_tool: instantly_or_smartlead
  approval_mode: draft_only

steps:
  - query_snowflake:
      sql: select * from analytics.fct_product_qualified_accounts where pql_stage = 'sales_ready'
      limit: 250

  - inspect_rows:
      show:
        - domain
        - owner_id
        - email
        - pql_score
        - rep_context
      require_operator_approval: true

  - check_crm:
      match_on: domain
      read_fields:
        - lifecycle_stage
        - owner_id
        - open_opportunity_count
        - last_activity_at
      block_if:
        - open_opportunity_count > 0
        - lifecycle_stage in ['customer', 'opportunity']

  - upsert_crm_context:
      write_fields:
        pql_score: pql_score
        pql_stage: pql_stage
        pql_last_scored_at: scored_at
        pql_reason: rep_context
      require_owner: true

  - draft_campaign:
      tool: instantly_or_smartlead
      mode: draft
      list_name: "Snowflake PQLs - {{ run_date }}"
      suppression:
        - bounced
        - unsubscribed
        - active_opportunity
        - customer

  - verify:
      checks:
        - crm_rows_updated_count
        - campaign_leads_created_count
        - blocked_records_count
        - sample_10_records
      output: run_summary
```

## Operator Checklist

Before pushing live:

- Does every record have a CRM account owner?
- Are customers and active opportunities suppressed?
- Did the campaign stay in draft mode?
- Can a rep see why the account is a PQL?
- Can you rerun the workflow next week without rebuilding the spreadsheet?

## PLG + GTM Engineering Workflow Examples

Use these as examples when adapting the playbook. The pattern is the same: warehouse signal, CRM context, guardrail, action.

### 1. Trial Setup Completed, No Sales Touch

Signal:

```text
connected_crm = true
created_first_workflow = true
active_users_14d >= 2
last_sales_activity_at is null or older than 14 days
```

Action:

```text
Create CRM task for owner.
Draft a two-email sequence.
Mention the setup milestone, not generic "checking in."
```

Guardrail:

```text
Block if account has open opportunity or is already customer.
```

### 2. Free Workspace With Team Adoption

Signal:

```text
invited_teammates_14d >= 2
active_users_14d >= 3
workspace_age_days < 45
```

Action:

```text
Route to growth AE or founder-led sales queue.
Create Slack alert with workspace domain, user count, and top actions.
```

Why it works:

```text
Team adoption usually beats single-user usage as a sales-readiness signal.
```

### 3. High-Usage Account, Stale CRM

Signal:

```text
ran_workflow_successfully >= 3
last_product_activity_at within 7 days
account_last_activity_at older than 30 days
```

Action:

```text
Update CRM with PQL reason.
Draft rep follow-up.
Add account to weekly manager review if no touch happens within 3 days.
```

### 4. Product Champion Changed Jobs

Signal:

```text
former_power_user_email no longer active
linkedin_job_change_detected = true
new_company_domain exists
```

Action:

```text
Create account in CRM if missing.
Draft warm reactivation note.
Suppress if new company is customer or active opportunity.
```

### 5. Expansion Signal Before Renewal

Signal:

```text
usage_up_30d >= 40%
renewal_date within 90 days
new_team_members_added >= 2
```

Action:

```text
Alert CSM and AE.
Draft expansion prep note.
Do not create outbound campaign.
```

### 6. Usage Drop Before Renewal

Signal:

```text
usage_down_30d >= 35%
renewal_date within 120 days
support_tickets_open > 0
```

Action:

```text
Create CS risk task.
Send Slack alert to account team.
Add "usage risk" note to CRM.
```

### 7. Product-Led Inbound Prioritization

Signal:

```text
new_signup = true
company_size >= target_threshold
used_key_feature within 48 hours
pricing_page_viewed = true
```

Action:

```text
Route to rep within same day.
Draft first-touch email with product action context.
```

### 8. Integration Intent

Signal:

```text
created_api_key = true
viewed_docs >= 3
connected_warehouse = false
```

Action:

```text
Create technical onboarding task.
Draft email from solutions engineer or founder.
```

### 9. Failed Workflow Rescue

Signal:

```text
workflow_failed >= 2
active_workspace = true
no_support_ticket = true
```

Action:

```text
Create support-led sales assist task.
Do not route to outbound sequence.
```

Why it works:

```text
Some product signals should create help, not sales pressure.
```

### 10. Dormant High-Fit Account Reactivation

Signal:

```text
pql_score was high in last 180 days
no_product_activity_60d = true
new_external_signal = hiring_or_funding_or_tool_change
```

Action:

```text
Draft reactivation campaign.
Mention the external change and previous product context.
```

### 11. Multi-Threading Target Account

Signal:

```text
one active user
target_account = true
multiple relevant contacts exist in CRM
no_open_opportunity = true
```

Action:

```text
Draft account-owner task to multi-thread.
Do not automatically sequence everyone.
```

### 12. Self-Serve Account Ready For Sales Assist

Signal:

```text
is_paid = true
mrr below sales_assist_threshold
usage_crossed_threshold = true
team_size_estimate >= target
```

Action:

```text
Alert owner.
Draft expansion-assist note.
Add account to sales-assist list.
```

## GTM Engineering Patterns To Reuse

These are the reusable building blocks across the examples:

| Pattern | What it does |
| --- | --- |
| `warehouse_signal` | Finds the product, billing, support, or intent signal. |
| `crm_join` | Adds owner, lifecycle, opportunity, and customer context. |
| `suppression_check` | Blocks customers, open opps, unsubscribes, bounced contacts, and sensitive accounts. |
| `rep_context` | Explains why the account moved. |
| `draft_action` | Creates a campaign, CRM task, Slack alert, or CS note in draft/review mode. |
| `run_summary` | Logs moved, blocked, updated, and sampled records. |

If you only copy one thing, copy this:

```text
signal + context + guardrail + draft action + run summary
```

That is the difference between "we have a score" and "we have a workflow."

## Social CTA Options

Use one depending on platform:

1. `I put the Snowflake query, dbt model, and workflow play in a lead magnet. Comment PQL and I will send it.`
2. `The useful artifact is not the video. It is the query behind it. I packaged the Snowflake PQL query + dbt model + campaign workflow here.`
3. `If your PQL definition still lives in a spreadsheet, steal this: Snowflake query, dbt model, CRM guardrails, campaign draft play.`

## Comment And DM Play

Use this when publishing the LinkedIn video. The point is to make the lead magnet easy to request without sounding like a gated ebook from 2014.

### First Comment

```text
I packaged the implementation version here:

- Snowflake PQL query
- dbt model
- CRM guardrails
- campaign draft workflow

It is not Mixmax's exact production model. It is the template for teams trying to operationalize the same idea: product usage + account fit + CRM context -> rep action.

Comment PQL and I will send the Notion link.
```

### Public Replies

Use these when someone comments `PQL`, `send`, or anything close:

```text
Sent. Start with the guardrails section before you copy the query.
```

```text
Sent. The query is useful, but the boring part is what keeps the CRM alive: suppressions, owner checks, and draft mode.
```

```text
Sent. If you adapt it, swap the product event names first. The scoring weights should come later.
```

### DM Follow-Up

```text
Here you go:

https://app.notion.com/p/Snowflake-PQL-to-Campaign-Playbook-377da8d1d8eb8128b1bde0d84216bf2a

I would not copy the scoring weights blindly. Start by mapping your product events, CRM lifecycle fields, suppressions, and campaign tool. The useful part is making the run repeatable enough that a rep can ask "why is this account in the campaign?" and get a real answer.
```

### Second DM If They Engage

```text
Curious what your stack is here. Snowflake + Salesforce + Outreach? Snowflake + HubSpot + Smartlead? Something weirder?

The handoff usually changes more than the PQL definition.
```

### If Someone Pushes Back On PQLs

```text
Agree with the skepticism. A lot of PQL scoring is just "clicked a button twice" dressed up as intent.

The version I trust has three parts: product usage, account fit, and CRM context. Any one of those alone gets noisy fast.
```

### Manual Tracking

Track comments in a tiny sheet or CRM note:

```text
name | profile_url | company | stack_guess | sent_link_at | follow_up_needed | notes
```

Do not over-automate the first version. The replies are the research.

## Blog CTA Block

```markdown
## Steal The PQL Workflow

Want the implementation version?

We packaged the Snowflake query, dbt model, and Deepline/Aero workflow play behind this walkthrough. It uses a Mixmax-inspired PQL pattern: product usage signals, account fit, CRM context, and campaign guardrails in one rerunnable workflow.

Lead magnet options:

- Get the Snowflake PQL query.
- Copy the dbt model.
- Use the CRM-to-campaign workflow play.
- Ask Deepline to adapt it to your warehouse and campaign tool.
```
