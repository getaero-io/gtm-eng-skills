# Lead Magnet: Product Usage To GTM Workflow Playbook

Slug: `snowflake-pql-campaign-playbook`

Offer line: `Turn product usage into GTM workflows without manual exports. Includes the Snowflake query, dbt model, CRM guardrails, and 26 PLG + GTM engineering plays.`

Primary CTA: `Get the product usage to GTM workflow playbook`

Secondary CTA: `Comment PLG and I will send the workflow`

Notion share page: `https://app.notion.com/p/Snowflake-PQL-to-Campaign-Playbook-377da8d1d8eb8128b1bde0d84216bf2a`

## What This Gives The Reader

This is the implementation version of the Snowflake speedrun video.

The reader gets:

- A setup guide for turning product usage into GTM actions.
- A Snowflake query that turns product usage into an activation queue.
- A dbt model they can adapt inside their own warehouse.
- A Deepline workflow play that syncs the right records to CRM and drafts a campaign.
- The guardrails that keep this from becoming another CSV upload ritual.
- A library of 26 PLG + GTM engineering plays across activation, sales-assist, expansion, retention, integration intent, revenue routing, and reactivation.

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

## Anonymized Examples This Pattern Comes From

These are the examples to use in the post and comments. They make the guide feel real instead of sounding like another "AI GTM" abstraction.

| Pattern | What changed | Number to cite |
| --- | --- | --- |
| Sales engagement account focus | Rep activity was getting spent on the wrong accounts, so the workflow reallocated attention toward higher-fit accounts | 40% of prior rep activity was on wrong or low-fit accounts; relative win rate improved +53% |
| High-volume inbound next-best action | Product and account context fed a ranked playbook instead of another static report | +17% higher lead-to-meeting conversion; ranked plays refreshed every 2-4 hours |
| Enterprise account reallocation | High-value accounts with no meaningful activity were surfaced and routed back into rep focus | 5,972 A-tier accounts had no logged meetings in 2 years; ~500 rep hours could be reallocated toward 40-80 new A accounts |
| Contact and account signal monitoring | First-party signals changed routing and follow-up, not just reporting | +17% lead-to-opportunity conversion lift |

The point is not "PQLs are magic."

The point is that product usage and account context should change the next GTM action.

## What We Have Learned From Warehouse-Native GTM Implementations

This section is the part most public PLG guides skip.

Everyone can say "connect product usage to sales." The hard part is knowing what breaks when you actually connect warehouse data, CRM records, campaign tools, rep activity, and product telemetry.

The pattern across PLG, enterprise sales, and high-volume inbound customer work is:

```text
raw signal -> identity graph -> semantic definition -> backtest -> guardrail -> draft action -> feedback loop
```

If you skip the middle, you get a faster version of the same spreadsheet mess.

### 1. The warehouse is not the workflow

Snowflake, BigQuery, Redshift, or Postgres can hold the data. They do not decide what should happen next.

The useful artifact is the decision layer on top:

```text
Which account is this?
Which user matters?
Which CRM owner owns it?
Which lifecycle stage is it in?
Which actions are suppressed?
Which next action should be drafted?
Which records were changed?
```

If the workflow cannot answer those questions, it is not ready for sales or CS.

### 2. The first warehouse project is usually an identity project

A high-volume inbound event-stream project made this obvious.

Before you can analyze "what happened before an upgrade," you need a canonical customer identity across:

- GA4 anonymous IDs.
- HubSpot contacts and form submissions.
- Salesforce leads, contacts, accounts, opportunities, and owners.
- Product users and workspaces.
- Campaign recipients.
- Calendar meetings.
- Gong or call transcripts.
- Support tickets.
- Billing records.

The boring table is the important one:

```text
anonymous_id | user_id | email | contact_id | lead_id | account_id | domain | workspace_id
```

Do this before you get clever with scoring.

If the identity graph is weak, every downstream workflow gets weird:

- A product user does not match the CRM account.
- A demo form submit gets counted twice.
- GA4 says the lead came from one campaign, HubSpot says another.
- The agent cannot tell whether "form submitted" means a web event, a HubSpot form event, or a Salesforce-created lead.
- The rep sees an account in a campaign and asks, "why am I seeing this?"

### 3. Source-of-truth priority matters more than source count

You will often have the same business event in multiple places.

Example from inbound funnel work:

```text
form_submitted could exist in GA4
form_submitted could exist in HubSpot
lead_created could exist in Salesforce
demo_booked could exist in Chili Piper or Salesforce
demo_held could exist in calendar, Gong, or Salesforce
```

The semantic layer needs to define priority.

Example:

```text
If HubSpot has form_submit, use HubSpot.
Else if GA4 has form_submit, use GA4.
Else mark event as missing.
```

Do not let the agent infer this from table names. It will sometimes get it right. That is not enough.

### 4. A semantic layer is a product manual for the agent

The public AI story is "ask questions in natural language."

The implementation story is "the agent needs business definitions."

The semantic layer should include:

- Metrics: `lead_to_demo_rate`, `pql_to_closed_won_rate`, `trial_activation_rate`.
- Dimensions: source, segment, plan, owner, region, product, account tier.
- Business objects: account, workspace, user, contact, opportunity, campaign, meeting.
- Event definitions: form submit, AQL, MQL, PQL, demo booked, demo held, opportunity created, upgrade, expansion, churn risk.
- Source priority rules.
- Verified query examples.
- Known exclusions and suppression logic.

One technical team wanted the semantic definitions in dbt and Snowflake so they could reuse them across Snowflake Intelligence, Hex, Sigma, Slack, and Deepline. That is the right instinct.

The more mature the customer, the more they should own the definitions in their dbt repo. Deepline can layer workflows on top.

### 5. Freshness depends on the action

Not every workflow needs real-time data.

Use this rule:

| Workflow | Freshness needed | Why |
| --- | --- | --- |
| Same-day lead routing | 5-30 minutes | Paid social and low-intent leads decay quickly |
| Product activation assist | 1-6 hours | Fast enough to catch onboarding drift |
| Sales-assist PQL queue | 2-24 hours | Rep prioritization can run daily unless motion is very high velocity |
| Expansion and renewal risk | Daily | Weekly is often too slow, real-time is usually unnecessary |
| Revenue import / forecast sync | Daily or monthly replacement | Forecasts can update retroactively; append-only is wrong |
| Win/loss signal discovery | Weekly or monthly | Backtesting does not need streaming |

Conversion tracking workflows benefit from 30-60 minute incremental updates.

Manual revenue import workflows do not need real-time streaming. They need reliable replacement semantics, auditability, and Slack/run summaries.

### 6. Reverse ETL is not the enemy. Unowned reverse ETL is.

Census, Hightouch, Zapier, custom scripts, and Deepline workflows all solve variations of "move this modeled data into the operating system."

The failure mode is not the tool.

The failure mode is:

```text
model changed -> sync still runs -> CRM field is stale -> sales trusts it -> nobody knows who owns the fix
```

Before you sync anything to CRM, define:

- Who owns the model.
- Who owns the sync.
- Which rows should be blocked.
- What happens when the row disappears from the model.
- Whether CRM values should be overwritten, appended, or only updated when blank.
- How reps can see the reason.
- How to roll back a bad run.

### 7. Manual CSVs are a staging pattern, not an operating model

Manual exports are fine for the first backtest.

They are not fine for production.

Use manual CSVs when:

- You are validating whether a signal is worth modeling.
- The customer does not know which event names matter.
- You need a one-off benchmark against Sigma, Salesforce, or HubSpot.
- You are reconciling metric differences.

Stop using manual CSVs when:

- The same export happens every week.
- A rep action depends on the result.
- The workflow affects CRM, campaigns, routing, or attribution.
- Someone asks "why is my number different?" more than once.

That is the point where the workflow needs a real model, run log, and owner.

### 8. Backtesting is where AI becomes useful

The best agent task is not "score these accounts."

The better task is:

```text
Look at the 30-90 days before opportunity creation, expansion, upgrade, churn risk, or renewal loss.
Find which product events, CRM context, support signals, and account traits appeared before the outcome.
Separate prerequisite events from predictive events.
Suggest a workflow that would have changed the GTM action earlier.
```

That is how you avoid fake insights like:

```text
signed_up is correlated with purchase
```

Of course it is. Users cannot buy before they exist.

The useful backtest excludes prerequisites and looks for effort, collaboration, integration, admin intent, repeated usage, workflow success, limits, risk, and owner context.

### 9. The action has to be smaller than the model

Most teams try to build a universal score.

The implementations that work start with one action:

- Route same-day high-fit demos.
- Draft a sales-assist sequence.
- Create an AE/CS task.
- Alert Slack when usage drops before renewal.
- Sync one CRM field with reason codes.
- Build a weekly manager review queue.

One narrow action beats one broad score.

### 10. The rep needs the "why," not just the rank

Every routed account should carry a reason payload.

Minimum reason object:

```json
{
  "why_now": [
    "3 active users in last 14 days",
    "CRM connected",
    "pricing page viewed twice",
    "no sales activity in 30 days"
  ],
  "suggested_action": "draft_owner_followup",
  "blocked_reasons": [],
  "source_tables": [
    "analytics.product_events",
    "salesforce.accounts",
    "hubspot.contacts"
  ],
  "scored_at": "2026-06-07T12:00:00Z"
}
```

Without reason codes, sales adoption dies.

### 11. The workflow needs a run summary

Every production run should output:

```text
records_read
records_qualified
records_blocked
records_updated_in_crm
campaign_drafts_created
sample_records
blocked_reason_counts
run_started_at
run_finished_at
approved_by
```

This is not bureaucracy. This is how you debug trust.

When someone asks "what happened yesterday?" you should not open six tabs and guess.

## Source Systems We Keep Seeing

Use this as a mental map when scoping a warehouse-to-GTM workflow.

| Category | Common tools | What they contribute | Common failure mode |
| --- | --- | --- | --- |
| Warehouse | Snowflake, BigQuery, Redshift, Postgres | Raw source of truth and modeled tables | Data exists but nobody can activate it |
| Transformation | dbt, SQL, Python, Sigma data models | Business definitions, semantic layer, reusable models | Definitions split across tools |
| CRM | Salesforce, HubSpot, Attio | Owners, lifecycle, opportunities, contacts, stage | Ownership is stale or not trusted |
| Product analytics | PostHog, Mixpanel, Amplitude, Heap, GA4 | Product events, page views, onboarding funnels | Events lack business meaning |
| Reverse ETL / sync | Census, Hightouch, Zapier, custom scripts, Deepline | Moves modeled data into operating systems | Sync runs without ownership or rollback |
| Campaigns | Outreach, Salesloft, HubSpot sequences, Instantly, Smartlead, HeyReach, Lemlist | Drafted actions and outbound execution | Leads are uploaded without suppression context |
| Sales activity | Gong, Outreach, Salesloft, Apollo, Smartlead, HeyReach | Meetings, replies, calls, emails, sequence events | Activity volume is measured without outcome context |
| Enrichment | Apollo, People Data Labs, Clay, Clearbit, ZoomInfo, Bloomberry, TheirStack, PredictLeads, Exa | Fit, hiring, tech stack, news, account research | Provider outputs are treated as truth without provenance |
| Support/CS | Zendesk, Intercom, Vitally, Gainsight | Tickets, health, renewal risk, blockers | Sales campaigns fire while support issues are open |
| Finance/billing | Stripe, Chargebee, Adaptive, NetSuite | MRR, plan, renewal, forecast, usage limits | Imports are manual and retroactive changes are mishandled |
| Collaboration | Slack, Notion, Google Drive, Sheets | Approval, staging, manual recovery, playbooks | Decisions happen outside the system of record |

The highest-value GTM engineering work is usually not adding one more source.

It is deciding which source wins when two disagree.

## Customer Implementation Notes

### Semantic layer, customer event stream, and ownership

The lesson is that product usage, marketing analytics, and sales data only become useful after they share definitions.

The implementation pattern:

```text
GA4 + HubSpot + Salesforce + product/custom data + transcripts
-> identity graph
-> customer event stream
-> semantic definitions
-> dashboards, Slack answers, workflows, and analysis
```

Key lessons:

- Define `form_submitted`, `demo_booked`, `demo_held`, `AQL`, `MQL`, `PQL`, and `closed_won` explicitly.
- Put preference rules in the semantic layer. Example: use HubSpot form submissions over GA4 when both exist.
- Keep the customer's dbt/semantic repo as the source of truth when their data team is mature enough.
- Keep freshness aligned to the operating motion. Conversion tracking wants 30-60 minute updates; strategic analysis does not.
- Treat event streaming as a single customer timeline, not a pile of disconnected raw tables.
- When leadership asks about SDR headcount, lead routing, or funnel conversion, the answer must be explainable enough to change staffing decisions.

Anti-patterns to avoid:

- Dashboard numbers that do not match internal Sigma/Salesforce numbers.
- AQL or lead assignment counts that differ by 30+ records without an explanation.
- Ownership fields that change constantly and create survivorship bias.
- PLG traffic getting mixed with inbound/marketing leads because the funnel definitions are too loose.
- "If this field is true, subtract 50,000" scoring logic that nobody trusts.

### Signal discovery, scoring, and rep attention

The lesson is that GTM scoring is valuable when it reallocates rep attention.

The implementation pattern:

```text
company domain
-> news and company events
-> tech stack
-> open AE/SDR roles
-> CRM and outbound stack signals
-> ICP score
-> playbook
-> why_now / first_move
-> persisted account enrichment row
```

The account enrichment workflow uses:

- PredictLeads for company news events.
- Exa as a coverage fallback.
- Bloomberry for tech stack.
- TheirStack for AE/SDR hiring.
- Deeplineagent for score, playbook, `why_now`, signal summary, and first move.
- A persistent account enrichment table for activation.

Key lessons:

- Score against the action, not the abstract account.
- A "high score" should become a playbook: AE growth, CRM user, enablement, SDR team, outbound motion, or no-fit.
- Store the why-now and first-move fields alongside the score.
- Public enrichment is not enough; compare the scored model against actual win/loss, rep activity, and product/customer context.
- If a third-party score says low but manual review says high, capture why. That is training data for the next model.
- Track outbound events from tools like Smartlead and HeyReach into Snowflake so you can compare campaign activity to revenue outcomes.

Anti-patterns to avoid:

- Reps checking 5-6 screens before trusting a lead.
- Common Room-style scores that are not explainable enough to act on.
- Account fit scores that do not become a concrete next action.
- Treating "uses Salesforce" as sufficient intent without sales hiring, outbound motion, or lifecycle context.

### Revenue imports, replacement semantics, and manual recovery

The lesson is that not every data workflow starts with clean APIs.

Sometimes the correct first workflow is:

```text
emailed XLSX
-> Google Drive staging
-> webhook metadata
-> Python transform
-> Snowflake table
-> run summary
-> Slack notification
```

This matters because warehouse GTM work often starts with messy operating data, not pristine event streams.

Key lessons from the import architecture:

- Large XLSX files should not be shoved through webhook JSON. A 56K-row file can turn into a 26MB payload.
- Use Drive or another staging layer for audit trail and manual recovery.
- Parse binary files in Python when the workflow runtime is not built for it.
- Forecast and revenue files often update historical months. Do not append blindly.
- Incremental logic should delete and replace the affected months, not duplicate revised forecasts.
- Keep product-key mapping explicit and make missing products visible.
- Send run summaries to Slack so people know whether the import actually happened.

Anti-patterns to avoid:

- Treating every file as append-only.
- Losing the original file after transforming it.
- No dry-run mode.
- No schema-change checklist.
- Silent failure when a new product appears in the export.

### Cross-customer pattern: the operating layer beats the model

Across these implementations, the model matters less than the operating loop:

```text
define the business object
join identity
choose source priority
backtest against revenue outcomes
draft the smallest useful action
block risky records
show reasons
log the run
collect feedback
iterate
```

That is the repeatable GTM engineering motion.

## Workflow Inventory From Customer Work

Use this as the implementation menu. These are the workflow shapes we have built, scoped, or repeatedly seen across customer work.

| Workflow | Source systems | Processing layer | Activation target | What it proves |
| --- | --- | --- | --- | --- |
| Customer event stream | GA4, HubSpot, Salesforce, product data, custom tables, transcripts | Identity graph, event definitions, semantic layer | Dashboards, Slack answers, funnel analysis, workflow triggers | Product, marketing, and sales data only become useful after the business definitions match. |
| CRM contact enrichment | HubSpot contact trigger, Apollo, Crustdata, Serper, Apify | Provider waterfall, LinkedIn validation, company matching | HubSpot contact/company updates and associations | Enrichment should be auditable, validated, and written back only when confidence is high enough. |
| Lead response and SDR funnel | Forms, meetings, HubSpot/Salesforce owners, routing, duplicates | Lead lifecycle definitions, response-time windows, same-day booking logic | Staffing and routing decisions | The valuable question is not "how many leads" but which leads became real meetings under which owner and response path. |
| Account enrichment and scoring | Domain seed list, PredictLeads, Exa, Bloomberry, TheirStack | Account enrichment table, ICP prompt, playbook prompt, score evaluation | Rep-ready account rows with score, why-now, first move | A score is only useful when it tells a rep what to do next. |
| Product usage and sales qualification | Product usage, CRM integrations, Chrome extension activity, sequencing activity | Usage-to-fit scoring and sales handoff rules | Prioritized sales follow-up | Product activity needs enough CRM context that sales can trust the handoff. |
| Outbound event stream | Smartlead, HeyReach, campaign activity, reply/meeting outcomes | Snowflake event tables, campaign-to-outcome joins | Campaign QA, scoring feedback, rep attention | Outbound tools need outcome context or they become activity dashboards. |
| Revenue import | Monthly Adaptive XLSX, product key XLSX, email/Drive/Zapier | Python transform, date normalization, product mapping, replacement semantics | Snowflake revenue table and Slack run summary | The right first workflow is often messy-file automation, not a clean API integration. |
| Propensity and white-space prioritization | Salesforce accounts, wins/losses, firmographics, public signals, enrichment | Backtest, tiering, untouched-account detection | Rep allocation and enterprise account prioritization | Rev teams need to know which high-fit accounts are being ignored, not just which accounts look good. |
| Account and org-chart research | Target account, exec names, account pages, social signals, contact data | Account research, contact classification, org chart generation | Rep prep and account strategy | Research is useful when it becomes a decision about who to contact and why. |
| Lead-to-meeting driver analysis | Lead, meeting, revenue, owner, response-time data | Causal driver analysis, time-to-first-touch decay, conversion decomposition | Growth lever prioritization | Teams often need to find the bottleneck before they need a new model. |
| Meeting likelihood scoring | Product/account data, distinct users, revenue, renewal dates, ARR, lead context | Meeting probability model, clean sales handoff | Sales prioritization | Scoring should predict a specific operating outcome, like a meeting, not a vague MQL. |
| Rep execution monitoring | Model output, Slack actions, CRM tasks, lead status | Action tracking, stale-lead detection, verification loop | Manager visibility and rep follow-up | A workflow is not done until the recommended action actually happened. |
| Self-serve lifecycle analytics | Product stage definitions, customer/product activity, Mode/Snowflake data | SQL generation, lifecycle stage classification | Lifecycle reporting and CS/GTM actions | Product lifecycle stages have to be operationalized, not only visualized. |
| Won/lost signal discovery | Salesforce opportunities, won/lost labels, Exa website extraction, Crustdata jobs | Signal lift analysis, anti-fit flags, scorecard | ICP scoring and outbound targeting | The best signals often come from comparing won and lost accounts, not brainstorming keywords. |
| Niche signal discovery | Won/lost proxy set, websites, jobs, Facebook ads, Google ads, firmographics | Lift analysis, buyer persona mapping, search recipes | Apollo searches, scoring, personalized outbound | ICP work gets sharper when it turns into search recipes and skip rules. |
| Deepline event follow-up | Luma registrations, check-ins, HubSpot lists, SMS qualification | Event attendee enrichment, check-in segmentation, list sync | HubSpot lists, SMS/email follow-up | Event data is a high-intent GTM source only if it gets synced before the window closes. |
| Snowflake messaging and customer-story matching | Warehouse/account data, customer stories, persona context, campaign history | Snowflake Cortex/RAG, company summary generation, QA prompts | Persona-specific outbound drafts | Warehouse context can make outbound more relevant when it chooses the right customer story and explains the match. |

The workflow names change by customer. The shape repeats:

```text
raw source
-> business definition
-> enrichment or model
-> backtest / QA
-> activation draft
-> system writeback
-> run summary
-> feedback loop
```

The most common mistake is skipping straight from `raw source` to `activation draft`.

That is where bad PQLs, bad account scores, and bad outbound campaigns come from.

## Step 1: Pick The PLG Motion

Do not start with a universal score. Start with one GTM motion.

Good first motions:

- Trial users who did the setup work but never booked a meeting.
- Free workspaces showing team adoption.
- Accounts with high usage but stale CRM activity.
- Product users at accounts already owned by sales.
- Expansion accounts where usage changed before renewal.
- Power users ready for a new product or feature.
- Accounts hitting usage limits or integration milestones.
- Customers showing usage risk before renewal.

Bad first motions:

- "Score every account in the database."
- "Tell sales who to call."
- "Find all intent."
- "Use AI to rank pipeline."

Those are too broad. You will spend the whole project arguing about the score instead of shipping the workflow.

The Sung video is closer to a product-led expansion motion than a narrow PQL motion:

```text
Power users of Pulse exist in Snowflake.
The team wants to promote Spark.
Deepline syncs the relevant attributes into Attio.
The campaign gets drafted in Instantly.
The operator answers clarifying questions before launch.
```

That is the real wedge: product usage should not die in analytics because nobody wants to wire Snowflake, CRM, and a campaign tool together.

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

This is the difference between a GTM workflow and a product activity report.

## Connect Product Usage To CRM Outcomes And Backtest It

Once product usage and CRM data live in the same workflow, use the agent to look backward before asking it to route accounts forward.

The useful question is:

```text
Which product events usually happened before an upgrade, opportunity creation, expansion conversation, renewal risk flag, or sales-qualified handoff?
```

Have the agent join product events to CRM outcomes and inspect the pre-outcome window.

Example backtest:

| CRM outcome | Lookback window | Product usage to inspect |
| --- | --- | --- |
| Opportunity created | 7-30 days before opp creation | Setup completed, team invites, integration events, workflow runs |
| Closed-won upgrade | 30-90 days before upgrade | Seat growth, usage-limit hits, power-user behavior, feature depth |
| Expansion conversation | 14-60 days before meeting | New teams joining, heavier usage, repeated exports, new integration activity |
| Renewal risk | 30-120 days before risk flag | Usage drop, failed workflows, fewer active users, champion inactivity |
| Sales-qualified handoff | 7-30 days before handoff | High-intent actions plus firmographic fit and clean CRM ownership |

Ask for patterns, not magic. A good first pass should produce something like:

```text
Accounts that upgraded usually had:
- 3+ active users in the prior 30 days
- at least one integration event
- repeated usage of the feature being upsold
- no open support blocker
- a known CRM owner
```

**If you do not have a semantic layer in place, it probably will not get this right on the first pass. The agent does not know how your product works, so it will often find something silly like `signed_in` being correlated with purchases. Obviously people who buy the product also sign in. You will need a few iterations, but eventually you should get something directionally predictive.**

The fastest way to improve the backtest is to give the agent more product context:

- What each event means.
- Which events are passive telemetry versus meaningful user effort.
- Which features map to activation, expansion, retention, or risk.
- Which events are prerequisites and should not be treated as intent.
- What counts as a real upgrade, opportunity, renewal risk, or expansion signal in the CRM.
- Which customer segments should be analyzed separately.

Documented product events help a lot here. Even a rough event dictionary is better than asking the agent to infer product meaning from event names alone.

## Step 4: Decide The Action Before You Score

Every score needs an action.

If the action is unclear, the score will become dashboard furniture.

Example actions:

| Motion stage | Action |
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

## Product Usage Signal Definition

Use this as the public-safe pattern:

> A product usage signal is not just "used the product." It is a product behavior that should change the next GTM action.

The account-focus angle:

- Product usage signals become propensity scores.
- Reps focus on high-fit accounts before time gets spent on low-fit ones.
- The workflow is valuable because it reallocates rep attention, not because it creates another dashboard.

Public-safe proof points from existing Deepline positioning:

- One sales engagement workflow saw a +53% relative win-rate improvement.
- Focus on high-fit accounts increased by +50%.
- 40% of prior rep activity was going to wrong or low-fit accounts.
- One high-volume inbound workflow saw +17% higher lead-to-meeting conversion with prioritized next-best-action workflows.
- One enterprise account prioritization workflow surfaced 5,972 A-tier accounts with no logged meetings in 2 years and a path to reallocate roughly 500 rep hours.

Do not present the query below as a customer's exact production model. Present it as the implementation template for teams trying to operationalize the same idea: usage signals should change rep action.

## PLG Motions To Cover

Do not make this only about PQLs. PQLs are one routing motion inside a broader PLG operating system.

| Motion | What product usage tells you | GTM action |
| --- | --- | --- |
| Activation assist | User did setup work but has not reached the useful moment | In-app nudge, lifecycle email, or CS assist |
| Sales assist | High-fit account shows serious usage | Rep-owned outreach or account owner task |
| Team expansion | More users join the workspace | Multi-threading or team plan conversation |
| Usage-limit upsell | Account repeatedly hits limits | Upgrade prompt or sales-assist campaign |
| Feature cross-sell | Power users are ready for a new module | Draft targeted campaign with product context |
| Integration intent | User creates API keys, views docs, or connects warehouse/CRM | Technical onboarding or solutions assist |
| Renewal risk | Usage drops, support issues rise, or champion disappears | CS risk workflow, not sales spam |
| Expansion readiness | Usage grows before renewal or across teams | AE/CS expansion task |
| Reactivation | Dormant high-fit account shows new activity or external signal | Re-engagement campaign |
| Enterprise routing | Large company reaches meaningful usage | Route to enterprise owner with context |
| Personal email identity resolution | A high-intent user signed up with Gmail, Outlook, iCloud, or another personal email | Resolve likely work identity and LinkedIn profile, then route only after validation |

The point is not to name everything a PQL.

The point is to make product usage operational.

Research note from the 2026-06-07 PLG scan:

- Current PLG/product-led sales writing keeps coming back to sales-assist triggers, not only PQLs.
- Common triggers include team invites, repeated usage-limit hits, enterprise domain usage, personal-email identity resolution, integration setup, activation milestones, pricing-page visits, and expansion behavior.
- Lifecycle strategy advice is converging on the same idea: product usage should route to self-serve prompts, sales-assist, CS risk workflows, or expansion nudges depending on account context.
- Sung's transcript matches this broader framing because the demo is a product-led cross-sell/expansion play from Pulse power users to Spark credits, not a generic lead score.
- The strongest 2026 PLG pattern is hybrid: self-serve adoption first, then sales or CS intervention when usage, fit, admin/security intent, renewal risk, or expansion context says a human should step in.
- The newer AI/PLG discussion also makes usage caps, onboarding drift, reverse trials, and workflow stickiness more important. Those show up in the added plays for usage limits, activation stalls, SSO/SCIM intent, workflow failure, and automation adoption readiness.

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
[ ] Account owner can approve before launch

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

## Deepline Workflow Play

Use this as the shareable workflow/play:

```yaml
name: snowflake_pql_to_campaign
goal: Turn warehouse product usage signals into CRM-owned GTM actions without hand-uploading CSVs.

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
      list_name: "Snowflake Product Usage Signals - {{ run_date }}"
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
- Can a rep see why the account moved?
- Can you rerun the workflow next week without rebuilding the spreadsheet?

## PLG + GTM Engineering Workflow Examples

Use these as examples when adapting the playbook. The pattern is the same: warehouse signal, CRM context, guardrail, action.

The expanded library below pulls from the current PLG/product-led sales research pattern: self-serve adoption first, then human sales/CS layered in when usage, fit, lifecycle, or risk says a person should intervene. The goal is not to make every signal a campaign. Some signals should create a rep task, some should create a CS action, some should trigger lifecycle automation, and some should stay suppressed.

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
Update CRM with usage reason.
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

### 5. Personal Email To LinkedIn Identity Resolution

Signal:

```text
signup_email_domain in ('gmail.com', 'outlook.com', 'icloud.com', 'yahoo.com')
meaningful_product_activity = true
work_email is null
linkedin_url is null
```

Action:

```text
Search by name, personal email clues, company hints, location, and product context.
Return candidate LinkedIn profiles with confidence reasons.
Stage the best candidate for review or write back only above the verified threshold.
If company identity is strong, attach the contact to the likely CRM account.
```

Guardrail:

```text
Never write a guessed LinkedIn URL directly into CRM.
Require at least two corroborating signals:
- exact name match plus company/domain match
- exact name match plus location match
- personal site/GitHub/social profile links to the same LinkedIn
- email username matches a known profile handle
```

Why it works:

```text
Some of the best PLG users sign up with personal email.
Without identity resolution, they stay trapped as "random Gmail user" in product analytics.
The goal is not enrichment for its own sake.
The goal is to recover enough identity to route the account correctly without polluting CRM.
```

### 6. Expansion Signal Before Renewal

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

### 7. Usage Drop Before Renewal

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

### 8. Product-Led Inbound Prioritization

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

### 9. Integration Intent

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

### 10. Failed Workflow Rescue

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

### 11. Dormant High-Fit Account Reactivation

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

### 12. Multi-Threading Target Account

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

### 13. Self-Serve Account Ready For Sales Assist

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

### 14. Usage Limit Hit, Upgrade Path Obvious

Signal:

```text
usage_limit_hit_count_14d >= 2
plan_name in ('free', 'starter')
active_users_14d >= 2
open_opportunity_count = 0
```

Action:

```text
Draft upgrade-assist campaign.
Include the exact limit hit and what becomes available on the next plan.
Create CRM note for owner if account fit is high.
```

Guardrail:

```text
If account fit is low, route to lifecycle email instead of sales.
```

### 15. SSO Or SCIM Intent

Signal:

```text
viewed_sso_docs = true
created_api_key = true
company_size >= enterprise_threshold
no_enterprise_owner_assigned = true
```

Action:

```text
Route to enterprise AE or solutions owner.
Draft technical discovery note.
Ask one clear question: "Are you planning SSO/SCIM for a broader rollout?"
```

Why it works:

```text
Enterprise readiness often shows up as security, provisioning, and admin workflows before a formal sales conversation.
```

### 16. High-Intent Pricing Page Plus Real Usage

Signal:

```text
pricing_page_views_7d >= 2
ran_workflow_successfully >= 1
active_users_14d >= 1
crm_owner_id exists
```

Action:

```text
Draft owner follow-up.
Mention the product action first, pricing second.
```

Guardrail:

```text
Block if pricing page view is the only signal.
```

### 17. Activation Stalled After Setup

Signal:

```text
completed_setup_step = true
reached_aha_moment = false
days_since_signup between 3 and 10
support_ticket_open = false
```

Action:

```text
Send lifecycle nudge or create support-assist task.
Include the next one action needed to reach first value.
```

Why it works:

```text
This is not a sales play. It is an activation rescue play.
```

### 18. New Use Case Detected Inside Existing Customer

Signal:

```text
is_customer = true
new_feature_category_used = true
feature_usage_depth_14d >= threshold
current_contract_does_not_include_feature = true
```

Action:

```text
Alert AE and CSM.
Draft cross-sell prep note with product evidence.
Do not sequence end users directly.
```

Guardrail:

```text
Require CSM review before any customer-facing message.
```

### 19. Department Expansion

Signal:

```text
new_email_domains_same_company = false
new_departments_detected >= 2
active_users_30d increased >= 50%
customer_health not in ('red', 'at_risk')
```

Action:

```text
Create expansion-readiness task.
Summarize which teams adopted and what workflows they ran.
```

Why it works:

```text
Expansion often starts as lateral adoption before procurement asks for a larger contract.
```

### 20. Champion Risk Before Renewal

Signal:

```text
renewal_date within 120 days
champion_activity_down_30d >= 50%
account_usage_still_active = true
no_new_champion_identified = true
```

Action:

```text
Create CS task to identify a new champion.
Draft internal account brief, not an outbound campaign.
```

Guardrail:

```text
Do not contact the old champion if they left the company or stopped using the product for a sensitive reason.
```

### 21. Product Usage Up, Business Review Missing

Signal:

```text
is_customer = true
usage_up_60d >= 30%
last_qbr_at is null or older than 180 days
account_tier in ('strategic', 'enterprise')
```

Action:

```text
Create QBR prep task.
Draft usage summary and expansion hypotheses.
```

Why it works:

```text
The right action is often a business review, not a sales sequence.
```

### 22. Low-Fit Power User

Signal:

```text
active_users_14d >= 3
feature_depth_score >= threshold
account_fit_score < minimum_sales_threshold
```

Action:

```text
Keep in lifecycle nurture.
Do not route to sales.
Use aggregate behavior to improve onboarding or content.
```

Why it works:

```text
Usage without fit can waste rep time even when the product behavior looks impressive.
```

### 23. High-Fit Quiet Account

Signal:

```text
account_fit_score >= target_threshold
signup_completed = true
activation_score low
no_sales_touch_14d = true
```

Action:

```text
Send founder/rep note offering help with first setup.
Keep message framed around removing friction, not "noticed you are inactive."
```

Guardrail:

```text
Use only for high-fit accounts. Otherwise automate.
```

### 24. Multi-Product Cross-Sell From Power Users

Signal:

```text
power_users_of_product_a >= 2
product_b_not_adopted = true
product_b_use_case_matches_account = true
crm_customer_stage = 'customer'
```

Action:

```text
Draft cross-sell campaign in review mode.
Add account-owner approval before launch.
Mention the workflow in product A that makes product B relevant.
```

Why it works:

```text
This is the pattern Sung shows: product usage creates context for a specific next product motion.
```

### 25. Workflow Failure At High-Fit Account

Signal:

```text
account_fit_score >= target_threshold
workflow_failed >= 2
user_retried_workflow = true
support_ticket_open = false
```

Action:

```text
Create support-led assist task.
Draft technical help note.
Mark as "do not sell until resolved."
```

Guardrail:

```text
Never turn product frustration into a sales campaign.
```

### 26. Agent Or Automation Adoption Readiness

Signal:

```text
manual_workflow_runs_30d >= 5
export_or_csv_usage_30d >= 2
automation_feature_not_enabled = true
admin_user_active = true
```

Action:

```text
Draft enablement note for admin or technical buyer.
Create CRM task with before/after workflow summary.
Offer a setup session or implementation guide.
```

Why it works:

```text
Repeated manual usage is often the strongest signal that an automation or agent workflow is worth introducing.
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

1. `Product usage is mostly trapped in analytics. I wrote up the GTM engineering workflow for getting it into CRM and campaign drafts. Comment PLG and I will send it.`
2. `The useful artifact is not the video. It is the workflow behind it: Snowflake signal, dbt model, CRM guardrails, campaign draft.`
3. `If product usage still becomes a manual CSV export before sales sees it, this is the workflow to steal.`

## Comment And DM Play

Use this when publishing the LinkedIn video. The point is to make the lead magnet easy to request without sounding like a gated ebook from 2014.

### First Comment

```text
I packaged the implementation version here:

- Snowflake product usage query
- dbt model
- CRM guardrails
- campaign draft workflow

It is not a customer's exact production model. It is the template for teams trying to operationalize the same idea: product usage + account fit + CRM context -> rep action.

Comment PLG and I will send the Notion link.
```

### Public Replies

Use these when someone comments `PLG`, `usage`, `send`, or anything close:

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

The handoff usually changes more than the usage definition.
```

### If Someone Pushes Back On Usage Signals

```text
Agree with the skepticism. A lot of usage scoring is just "clicked a button twice" dressed up as intent.

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
## Steal The Product Usage Workflow

Want the implementation version?

We packaged the Snowflake query, dbt model, and Deepline workflow play behind this walkthrough. It turns product usage signals, account fit, CRM context, and campaign guardrails into one rerunnable GTM workflow.

Lead magnet options:

- Get the Snowflake product usage query.
- Copy the dbt model.
- Use the CRM-to-campaign workflow play.
- Ask Deepline to adapt it to your warehouse and campaign tool.
```
