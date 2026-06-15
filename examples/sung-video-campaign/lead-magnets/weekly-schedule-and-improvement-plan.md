# Sung Lead Magnet Schedule And Improvement Plan

**Review owner:** Jai
**Week:** Monday, June 15, 2026 to Friday, June 19, 2026
**Timezone:** Eastern Time
**Goal:** schedule the next three Sung lead magnets for review and upgrade them from static docs into tactical assets people will actually ask for.

## Schedule

| Date | Lead magnet | Primary post | Video | CTA | Review status |
| --- | --- | --- | --- | --- | --- |
| Tuesday, June 16, 2026 | Deepline V2 GTM Workflow Implementation Guide | LinkedIn native video + X thread + Threads post | Sung Pipeline as Code video included; Glue Code as optional follow-up | Comment `WORKFLOWS` | Ready for Jai review |
| Wednesday, June 17, 2026 | GTM Provider Stack Decision Matrix | LinkedIn native video + X thread + Threads post | Provider Sprawl | Comment `PROVIDERS` | Ready for Jai review |
| Friday, June 19, 2026 | Waterfall Cost Optimization Framework | LinkedIn native video + X thread + Threads post | Waterfall Complexity | Comment `WATERFALL` | Ready for Jai review |

## Recommended Publishing Cadence

### Tuesday: Workflows

- 8:45 AM ET: LinkedIn post with native video.
- 11:15 AM ET: X thread.
- 4:30 PM ET: Threads version.
- Same day: comment on 10-15 GTM engineering / Claude Code / RevOps posts before and after publishing.
- Follow-up comment: "I can also send the 20-row eval template if useful."
- Video: include Sung's Pipeline as Code walkthrough as the native LinkedIn video. Use Glue Code as the follow-up clip only if we want a second post in the thread.

### Wednesday: Providers

- 8:45 AM ET: LinkedIn post with native video.
- 11:15 AM ET: X thread.
- 4:30 PM ET: Threads version.
- Same day: comment on CRM, data quality, RevOps stack, Clay/Apollo/ZoomInfo comparison posts.
- Follow-up comment: "The useful part is the field-level source-of-truth table. Happy to send the editable version."

### Friday: Waterfall

- 8:45 AM ET: LinkedIn post with native video.
- 11:15 AM ET: X thread.
- 2:30 PM ET: Threads version.
- Same day: comment on enrichment, provider cost, Clay waterfall, Apollo/ZoomInfo, and data quality posts.
- Follow-up comment: "We are turning this into a calculator: paste your provider order + costs, get routing recommendations."

## Last30Days Research Summary

### Workflows

The highest-signal finding was from r/gtmengineering: the beginner mistake is treating GTM engineering like a data engineering problem first. The real bottleneck is signal logic, not tooling.

Other patterns:

- The best first workflow is one broken thing fixed end to end: data in, enrichment, verification, sequence trigger, and writeback.
- Lead magnets that work are specific, implementation-oriented, and comment-gated: "Comment SEND and I will send the workflow" outperformed generic guide framing in the social examples.
- Claude Code / skills content performs because it promises leverage: reusable SOPs, reference files, guardrails, and self-improvement loops.
- Trust is the adoption wedge: agents need guardrails, not just more actions.

Implication for our asset:

The `WORKFLOWS` lead magnet should not be framed as "learn GTM engineering." It should be framed as "turn one recurring GTM task into a typed V2 play with evals and guardrails."

## Workflow Learnings To Fold Into Tuesday

These are internal source notes for Jai review. Use the learnings publicly, but anonymize the customer names unless Jai explicitly approves naming them.

### Jai's Workspace / Deepline Workflow Corpus

What keeps repeating:

- Work email waterfalls are usually the first "real" workflow because they expose provider choice, validation, cost, and writeback in one pass.
- Known-account-to-right-contact workflows are more useful than generic list building because the account decision is already made; the workflow just needs to find the right person, verify, and route.
- Messy CSV repair is not a throwaway ops task. It is often the beginning of the data contract: normalize, dedupe, resolve identity, enrich missing fields, and preserve provenance.
- Buying-signal research only matters when it changes the next action: CRM task, Slack approval, campaign draft, or sequence membership.
- The best workflows include reviewability by default: reason payload, source evidence, blocked reason, owner, cost, and run summary.
- "One obvious outbound workflow" keeps showing up as the best validation unit. If the first workflow is not obvious to a rep or marketer, the implementation will drag.

Tuesday framing:

> The first useful GTM workflow is rarely glamorous. It is usually a row that moves from messy input -> trusted identity -> evidence -> guardrail -> owner action.

### nTop / Aerospace Implementation

Public handling: anonymize externally as "a Series B aerospace technology company" unless Jai approves using the customer name.

What we learned:

- The customer did not just need another dashboard. They needed signals to power ABM workflows.
- The real unlock was unifying 15+ data sources in days, then moving from reporting to activation.
- "Trusted enough to act on" mattered more than "perfect." The growth team needed confidence to defend pipeline decisions and make bigger moves.
- Account scoring became useful when it fed prioritized accounts and next-best actions, not when it lived as a metric in a dashboard.
- The public lesson: GTM engineering is the layer that turns analytics into action.

Tuesday framing:

> We learned this building real workflows: reporting is not the win. The win is when trusted signals change what the GTM team does next.

### Broader Implementation Notes

Patterns from customer calls and implementation work:

- CSV-to-Salesforce mappings are often the first symptom of a workflow that needs an owner and a schema.
- Custom objects matter when one contact/account can have multiple scores, packages, segments, or plays attached.
- Salesforce/HubSpot/Marketo writeback rules need to be decided before the workflow runs, not after the first bad sync.
- Slack approval loops are useful because they let humans teach the workflow before automation is trusted.
- Cost estimates and spending caps reduce anxiety when the workflow calls multiple providers.
- Closed-lost backtests are one of the fastest ways to find whether a signal is real or just impressive-looking.

Tuesday framing:

> Most teams do not fail because they cannot automate. They fail because nobody wrote down the input contract, writeback policy, and eval before the workflow touched the CRM.

### Providers

The provider research was thinner, but it reinforced a useful angle: buyers are not looking for another vendor list. They are trying to future-proof their GTM stack and need someone to own CRM/data quality.

Other patterns:

- The sharpest provider question is "who owns this field?" not "which vendor is best?"
- CRM ownership matters. One Reddit thread on startup CRM stacks had the practical insight that a 20-50 person team already needs a person to own CRM discipline.
- TikTok/short-form GTM content is talking about distribution-channel overwhelm and "your GTM stack is talking, but nobody can listen."
- The provider asset should make messy multi-tool stacks legible instead of pretending one provider will solve the whole workflow.

Implication for our asset:

The `PROVIDERS` lead magnet should become a field-level source-of-truth worksheet: CRM owner, lifecycle, title, email, phone, product usage, why-now signals, and campaign destination.

### Waterfall

The market has several waterfall explainers, but very few interactive assets. This is the biggest upgrade opportunity.

Other patterns:

- Recent web pages claim optimized waterfall enrichment can reduce cost per enriched record versus unoptimized multi-provider calls.
- Waterfall explainers mostly stop at "try provider A, then B, then C." They do not help teams pick the order, estimate cost, or decide review thresholds.
- Social discussion frames GTM work as a chain: build list, score ICP, layer intent, find decision-makers, enrich/validate, write copy, push into tools.
- The recurring complaint is tab/tool hopping: Exa, Clay, Gong, CRM, enrichment tools, spreadsheets.

Implication for our asset:

The `WATERFALL` lead magnet should become a calculator/analyzer: paste provider costs, hit rates, accepted-hit rates, review rates, and segment rules; get recommended provider order and stop rules.

## Upgrade Plan

### 1. WORKFLOWS: V2 Workflow Spec Generator

Current asset:

- `lead-magnets/workflows-v2-implementation-guide.md`

Upgrade from static guide to interactive worksheet.

Add a one-page workflow spec template:

```yaml
workflow_name:
owner:
trigger:
input_entity:
source_system:
destination_system:
risk_level:
required_evidence:
suppression_rules:
crm_writeback_fields:
review_queue:
eval_rows:
success_metric:
rollback_plan:
```

Add a 20-row eval CSV template:

| row_type | input | expected_action | expected_block_reason | notes |
| --- | --- | --- | --- | --- |
| obvious_good |  |  |  |  |
| obvious_bad |  |  |  |  |
| ambiguous |  |  |  |  |
| historical_breakage |  |  |  |  |

Better CTA:

> Comment `WORKFLOWS` and I will send the V2 workflow spec + 20-row eval template.

Why this is stronger:

It is not "a guide." It is the artifact a GTM engineer can use the same day.

### 2. PROVIDERS: Provider Ownership Matrix

Current asset:

- `lead-magnets/provider-stack-decision-matrix.md`

Upgrade from matrix to stack-audit worksheet.

Add an editable table:

| Field | Current source | Trusted source | Fallback provider | Review trigger | CRM writeback policy |
| --- | --- | --- | --- | --- | --- |
| CRM owner | CRM | CRM | none | any conflict | never overwrite |
| Lifecycle stage | CRM | CRM | none | any conflict | never overwrite |
| Work email | provider | validated email provider | waterfall | catch-all/unverified | write if empty |
| Mobile | provider | high-precision phone provider | B2B provider | name/company mismatch | review |
| Product usage | warehouse | warehouse | none | missing account match | append evidence |
| Why-now | product/CRM/public source | first-party first | public trigger | no source | append evidence |

Add "provider jobs" as a check:

- identity
- email
- phone
- company
- firmographics
- technographics
- intent/timing
- CRM activation

Better CTA:

> Comment `PROVIDERS` and I will send the provider ownership matrix.

Why this is stronger:

It solves the actual question: which system is allowed to be right?

### 3. WATERFALL: Cost Optimization Calculator

Current asset:

- `lead-magnets/waterfall-cost-optimization-framework.md`

Upgrade into a calculator or lightweight agent prompt.

Input schema:

```json
{
  "workflow": "work_email_enrichment",
  "segments": [
    {
      "name": "high_fit_accounts",
      "rows": 1000,
      "max_cost_per_accepted": 0.45,
      "downstream_value": 25
    }
  ],
  "providers": [
    {
      "name": "provider_a",
      "cost_per_attempt": 0.04,
      "hit_rate": 0.52,
      "accepted_hit_rate": 0.78,
      "review_rate": 0.08,
      "best_inputs": ["name", "domain"]
    },
    {
      "name": "provider_b",
      "cost_per_attempt": 0.11,
      "hit_rate": 0.34,
      "accepted_hit_rate": 0.91,
      "review_rate": 0.03,
      "best_inputs": ["linkedin_url"]
    }
  ],
  "human_review_cost_per_row": 1.50,
  "stop_rules": [
    "stop_on_verified_email",
    "stop_on_customer_suppression",
    "premium_only_for_high_fit"
  ]
}
```

Output:

- recommended provider order by segment
- estimated cost per accepted result
- estimated review burden
- providers to skip
- rows that should go straight to review
- risky CRM writeback fields
- suggested stop rules

Better CTA:

> Comment `WATERFALL` and I will send the cost calculator. Paste in your provider order and we will show where you are wasting money.

Why this is stronger:

The market already has waterfall explainers. A calculator is much harder to ignore.

## Suggested LinkedIn Hooks For Review

### Workflows

Most GTM workflows die after the first successful demo.

The play works, then it becomes a script, Zap, spreadsheet, or reverse ETL job nobody wants to own.

We wrote down the V2 workflow spec we use before turning a GTM idea into production.

This comes from building real workflows across our own workspace and customer implementations: waterfall enrichment, messy CSV repair, product signals, CRM writeback, Slack approvals, and account scoring that actually changes what reps do next.

Comment `WORKFLOWS` and I will send it.

### Providers

The provider question is not "which data vendor is best?"

It is "which system is allowed to be right for this field?"

CRM owner. Lifecycle stage. Work email. Mobile. Product usage. Why-now signal. Campaign destination.

We put together the provider ownership matrix.

Comment `PROVIDERS` and I will send it.

### Waterfall

Most waterfall enrichment advice stops at:

"try provider A, then B, then C."

That is not the hard part.

The hard part is knowing when to stop, when to review, and whether the cheap provider is quietly creating more work than it saves.

We made the cost optimization framework.

Comment `WATERFALL` and I will send it.

## Source Notes

### Last30Days

- Workflows research: Reddit, X, YouTube, TikTok, Instagram; saved raw file in `~/Documents/Last30Days/gtm-workflow-implementation-guide-gtm-engineering-workflow-a-raw.md`.
- Providers research: Reddit, X, TikTok; saved raw file in `~/Documents/Last30Days/gtm-provider-stack-decision-matrix-provider-sprawl-enrichmen-raw.md`.
- Waterfall research: Reddit, X, TikTok, Instagram; saved raw file in `~/Documents/Last30Days/waterfall-enrichment-cost-optimization-calculator-provider-r-raw.md`.

### Web Sources

- Unify: "How to Build a Waterfall Enrichment Workflow (Step-by-Step)".
- Cleanlist: "Data Enrichment [2026]" and "Waterfall vs Single-Source Enrichment".
- GTME Pulse: "Enrichment Waterfall Strategy for GTM Teams".
- Apollo: "What Tools Do GTM Engineers Use to Build and Automate Revenue Workflows".
- Clay: "Best CRM Data Enrichment Tools & Guide".
- Deepline: Pipeline as Code, Provider Sprawl, Waterfall Complexity, Product Usage to GTM Playbook, GTM Data Infrastructure.

## Review Questions For Jai

1. Do we want to ship the current docs as-is this week, or upgrade `WATERFALL` into the calculator first?
2. Should `WORKFLOWS` be framed as "V2 workflow spec" instead of "implementation guide"?
3. Should `PROVIDERS` be framed as "provider ownership matrix" instead of "decision matrix"?
4. Do we want a single Notion page per asset, or one review page with all three?
