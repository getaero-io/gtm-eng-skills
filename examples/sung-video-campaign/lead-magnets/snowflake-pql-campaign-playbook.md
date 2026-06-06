# Lead Magnet: Snowflake PQL to Campaign Playbook

Slug: `snowflake-pql-campaign-playbook`

Offer line: `Steal the Snowflake -> dbt -> CRM -> campaign workflow behind the Sung speedrun. Includes the query, dbt model, and activation play.`

Primary CTA: `Get the Snowflake PQL playbook`

Secondary CTA: `Comment PQL and I will send the query`

Notion share page: `https://app.notion.com/p/Snowflake-PQL-to-Campaign-Playbook-377da8d1d8eb8128b1bde0d84216bf2a`

## What This Gives The Reader

This is the implementation version of the Snowflake speedrun video.

The reader gets:

- A Snowflake query that turns product usage into a PQL queue.
- A dbt model they can adapt inside their own warehouse.
- A Deepline/Aero workflow play that syncs the right records to CRM and drafts a campaign.
- The guardrails that keep this from becoming another CSV upload ritual.

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

## Social CTA Options

Use one depending on platform:

1. `I put the Snowflake query, dbt model, and workflow play in a lead magnet. Comment PQL and I will send it.`
2. `The useful artifact is not the video. It is the query behind it. I packaged the Snowflake PQL query + dbt model + campaign workflow here.`
3. `If your PQL definition still lives in a spreadsheet, steal this: Snowflake query, dbt model, CRM guardrails, campaign draft play.`

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
