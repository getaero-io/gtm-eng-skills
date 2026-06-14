# Deepline V2 GTM Workflow Implementation Guide

**Comment keyword:** `WORKFLOWS`

This is the guide for turning a GTM idea into a repeatable Deepline V2 workflow.

The old version was usually a script, a Zap, a Clay table, a spreadsheet export, or a reverse ETL job someone was afraid to touch. It worked until the schema changed, the provider returned bad data, sales asked why a record was routed, or the one person who understood the workflow went on vacation.

The V2 version should feel closer to shipping a small product feature:

```text
trigger -> typed input -> play -> tools/enrichment -> guardrails -> dry run -> approval -> writeback -> run summary
```

## The Rule

Do not automate the whole GTM motion first.

Automate one obvious workflow that already happens manually.

The best first workflows are boring:

- New signup -> CRM context -> safe HubSpot sequence.
- Product usage spike -> account research -> campaign draft.
- Personal email signup -> LinkedIn/company resolution -> review queue.
- Event check-in -> same-day follow-up draft.
- Closed-lost account shows new trigger -> owner task.

If the manual version is not clear, the automated version will be worse.

## The Architecture

### 1. Input Contract

Write down the shape of the data before you write the play.

Example:

```ts
type SignupInput = {
  email: string;
  fullName?: string;
  workspaceId: string;
  signupSource?: string;
  firstProductEvent?: string;
  dryRun?: boolean;
};
```

Minimum fields to define:

| Field | Why it matters |
| --- | --- |
| Primary entity | Account, contact, workspace, event attendee, or opportunity |
| Source system | Product, CRM, warehouse, CSV, event platform, support tool |
| Owner | Who receives the task or approves the action |
| Destination | HubSpot, Salesforce, Marketo, Smartlead, Slack, review queue |
| Risk level | Draft only, approval required, safe writeback, never auto-write |
| Required evidence | What must be true before this action is allowed |

### 2. Typed Play

V2 plays are TypeScript. That matters because GTM workflows are not linear.

You need:

- branching
- retries
- suppressions
- provider routing
- dedupe
- review queues
- field-level overwrite rules
- row-level explanations

Public Deepline V2 surfaces:

```bash
deepline plays run ./my-play.play.ts --input '{}' --watch
```

SDK:

```ts
client.runPlay(...)
client.runs.get(runId)
client.runs.tail(runId)
ctx.play(name).run(...)
ctx.play(name).runSync(...)
ctx.runPlay(name, input)
```

HTTP:

```http
POST /api/v2/plays/run
GET /api/v2/runs/:runId
GET /api/v2/runs/:runId/tail
```

### 3. Guardrail Layer

Most bad GTM automation is not bad because the AI wrote a weird sentence.

It is bad because the workflow touched the wrong record.

Minimum guardrails:

| Guardrail | Default |
| --- | --- |
| Existing customer | Suppress unless customer/expansion motion |
| Open opportunity | Suppress or route to owner, never auto-sequence |
| Unsubscribed/bounced | Suppress |
| Missing owner | Review queue |
| Personal email identity | Review unless high confidence |
| Low evidence | Draft only |
| Duplicate account/contact | Review or merge by explicit rule |
| CRM overwrite | Never overwrite verified fields without provenance |

### 4. Reason Payload

Every routed record needs a reason payload. Otherwise sales sees a score and ignores it.

```json
{
  "why_now": [
    "completed setup in last 48 hours",
    "pricing page viewed twice",
    "no sales activity in 30 days"
  ],
  "suggested_action": "draft_owner_followup",
  "blocked_reasons": [],
  "source_tables": ["product_events", "crm_accounts"],
  "scored_at": "2026-06-14T12:00:00Z"
}
```

### 5. Run Summary

Every production run should answer:

- How many records were read?
- How many qualified?
- How many were blocked?
- Why were they blocked?
- How many drafts/tasks/writebacks were created?
- Which providers ran?
- What did it cost?
- Who approved it?

The test is simple: if someone asks what happened yesterday, you should not need six tabs and a guess.

## Minimal V2 Play Skeleton

Use this as the shape, not final copy-paste code. The real implementation should use the exact tool IDs, CRM fields, and suppressions in your workspace.

```ts
import { definePlay } from "deepline";

type Input = {
  rows: Array<{
    email?: string;
    domain?: string;
    companyName?: string;
    workspaceId?: string;
    productSignal?: string;
  }>;
  dryRun?: boolean;
};

export default definePlay("gtm-workflow-starter", async (ctx, input: Input) => {
  const rows = await ctx.dataset("input_rows", input.rows)
    .withColumn("account", (row, ctx) =>
      ctx.tools.execute({
        id: "company_lookup",
        tool: "company_search",
        input: {
          domain: row.domain,
          companyName: row.companyName,
        },
        description: "Resolve the best matching company.",
      })
    )
    .withColumn("crm_context", (row, ctx) =>
      ctx.tools.execute({
        id: "crm_lookup",
        tool: "hubspot_search_objects",
        input: {
          object_type: "contacts",
          query: row.email || row.domain || row.companyName,
        },
        description: "Check existing CRM state before action.",
      })
    )
    .withColumn("decision", (row) => {
      if (!row.email && !row.domain && !row.companyName) {
        return { action: "review", reason: "missing_identity_fields" };
      }

      if (input.dryRun) {
        return { action: "preview", reason: "dry_run" };
      }

      return { action: "ready", reason: "passes_basic_checks" };
    });

  return {
    dryRun: input.dryRun ?? true,
    totalRows: input.rows.length,
    rows,
  };
});
```

## Five Workflows To Ship First

### 1. Signup -> HubSpot Sequence

Use when a new signup has enough context to justify follow-up.

**Inputs**

- Email.
- Name if available.
- Workspace/account ID.
- Signup source.
- First meaningful product event.

**Steps**

1. Normalize email, domain, name, and workspace.
2. Check HubSpot for contact, company, lifecycle stage, owner, active deal, unsubscribe, and customer status.
3. Resolve identity if the signup used a personal email.
4. Pick the correct route:
   - work email + no open opp -> onboarding sequence or draft
   - personal email -> identity review queue
   - enterprise domain + usage -> sales-assist task
   - customer -> customer education or suppress
5. Upsert only safe fields.
6. Enroll, draft, or stage for review.
7. Post a run summary.

**Eval cases**

| Case | Expected |
| --- | --- |
| New work email, no open opportunity | Enroll or draft |
| Personal email | Identity review |
| Existing open opportunity | Suppress or route to owner |
| Unsubscribed | Suppress |
| Customer | Suppress unless customer motion |

### 2. Product Usage -> Campaign Draft

Use when product activity is trapped in the warehouse and sales only hears about it after a manual export.

**Inputs**

- Workspace ID.
- Account domain.
- Product event summary.
- CRM account/opportunity state.
- Owner.

**Steps**

1. Pull recent product usage.
2. Join to CRM account, owner, opportunity, and customer state.
3. Define the business meaning of the event.
4. Backtest against historical outcomes.
5. Generate a reason payload.
6. Draft a campaign or rep task.
7. Route high-confidence actions to review.

**Important**

If you do not have a semantic layer, the first pass will probably overfit to obvious events like `signed_in` or `signed_up`. That is not intelligence. Users cannot buy before they sign up.

Add product context, event definitions, and examples until the output is directionally useful.

### 3. Personal Email -> LinkedIn Review

Use when serious product users sign up with Gmail, iCloud, Outlook, university, or other personal emails.

**Inputs**

- Personal email.
- Name if available.
- Workspace ID.
- Product context.
- IP/company hint if available.

**Steps**

1. Detect personal email.
2. Collect name, handle, product, workspace, and referrer hints.
3. Search for candidate LinkedIn/company matches.
4. Require strong name match and corroborating evidence.
5. Write back only verified identity.
6. Send ambiguous records to review.

**Default guardrail**

Never auto-accept a weak personal-email match.

### 4. Event Attendee -> Follow-Up Draft

Use when an event list is useful but too messy to hand directly to sales.

**Inputs**

- Event ID.
- Registration/check-in status.
- Attendee email.
- Name.
- Event topic.

**Steps**

1. Normalize attendee identity.
2. Enrich account and role.
3. Segment checked-in vs registered vs no-show.
4. Apply suppressions.
5. Draft same-day follow-up for high-fit checked-in attendees.
6. Send the rest to nurture or review.

### 5. Closed-Lost Trigger -> Re-Engagement Draft

Use when closed-lost accounts show new reasons to care.

**Inputs**

- Closed-lost account list.
- Loss reason.
- Old opportunity date.
- New trigger: hiring, funding, product launch, competitor mention, tech-stack change, leadership change, product usage.

**Steps**

1. Pull closed-lost history.
2. Find current trigger evidence.
3. Compare trigger to loss reason.
4. Suppress bad-fit and recent-touch accounts.
5. Draft a specific re-engagement note.
6. Route to owner with evidence.

## Backtest Prompt

Use this before the workflow writes to CRM or creates a campaign.

```text
Take the workflow rule we just defined and apply it to the last 100 historical records.

Use 50 records that produced the desired outcome and 50 that did not.

For each record, use the product, CRM, and enrichment state as it existed at the time. Do not use future information.

Return:
- would_act, blocked, or incomplete
- which guardrail fired
- evidence used
- owner/action that would have been created
- whether the historical outcome matched the workflow decision
- the 5 worst false positives
- the 5 worst false negatives
- changes needed before production
```

Ship only when the workflow beats the current manual process and the false positives are explainable.

## Cost-Effective Eval Starter Kit

Do not start with a giant benchmark. Start with 20 rows.

| Row type | Count |
| --- | ---: |
| Obvious good records | 5 |
| Obvious bad records | 5 |
| Ambiguous records | 5 |
| Records that used to break the workflow | 5 |

Check deterministic rules first:

- Did we suppress customers?
- Did we avoid open opportunities?
- Did we preserve the CRM owner?
- Did we avoid overwriting verified fields?
- Did every accepted record have evidence?
- Did every rejected record have a reason?

Use an LLM judge only where judgment is actually required:

- Is this campaign draft specific enough?
- Does the recommended action match the evidence?
- Is this identity match plausible?
- Is the summary useful to a rep?

## Production Checklist

- Workflow owner named.
- Input schema documented.
- CRM writeback fields documented.
- Suppression rules agreed with sales/marketing ops.
- Dry run passes golden set.
- Review queue exists for ambiguous rows.
- Run summary includes accepted, rejected, reviewed, failed, and cost counts.
- Rollback path exists.
- First production version is draft-only or approval-gated.

## Sources And Basis

Public sources:

- Deepline video page: Pipeline as Code for GTM Account Mapping, `https://deepline.com/blog/pipeline-as-code-account-mapping`.
- Deepline guide: GTM Data Infrastructure Workflows, `https://deepline.com/blog/gtm-data-infrastructure`.
- Deepline guide: Product Usage to GTM Workflow Playbook, `https://deepline.com/blog/product-usage-to-gtm-playbook`.
- Deepline guide: 30 Claude Code GTM Workflows, `https://deepline.com/blog/claude-code-gtm-workflows`.

Internal sources used to build this asset:

- Deepline V2 SDK + CLI README.
- Deepline V2 Play Runtime README.
- Anonymized customer-call field notes from March-May 2026 covering workflow automation, account scoring, enrichment, CRM/Marketo/Salesforce handoffs, closed-lost backtesting, implementation risk, and provider consolidation.
- Sung video campaign assets and sample workflows in this repo.

## Send Copy

Here is the V2 GTM workflow implementation guide.

The shortest version: pick one manual workflow, write down the input contract, run it as a typed play, keep the guardrails boring, and do not let it touch CRM until it passes a small backtest.

Start with the simple plays: signup -> HubSpot sequence, product usage -> campaign draft, personal email -> LinkedIn review, event attendee -> follow-up, closed-lost trigger -> owner task.
