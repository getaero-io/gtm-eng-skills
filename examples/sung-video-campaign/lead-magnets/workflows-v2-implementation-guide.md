# Deepline V2 Workflow Implementation Guide

**Comment keyword:** `WORKFLOWS`

This is the implementation guide for turning GTM work into typed Deepline V2 plays.

The old version of this workflow was usually a script, a Zap, a spreadsheet export, or a reverse ETL job someone was afraid to touch. It worked until the schema changed, the provider returned weird data, or sales asked why the campaign included the wrong accounts.

V2 should feel closer to writing a small product feature:

```text
trigger/input -> typed play -> tools/enrichment -> guardrails -> dry run -> approval -> CRM/campaign writeback
```

## What You Build

A play that can:

- Take a list, event, product-usage segment, CRM view, or CSV as input.
- Enrich the records using the right tools.
- Apply business rules before anything touches a CRM or sequencer.
- Produce an auditable run summary.
- Let you test locally, then run the same logic in the cloud.

## V2 Mental Model

V1 workflow specs were JSON config. V2 plays are TypeScript.

That matters because GTM workflows are rarely linear. You need branching, retries, dedupe, provider fallbacks, suppressions, and row-level explanations.

Use V2 when the workflow needs:

- Conditional logic.
- Provider routing.
- Human approval.
- Run logs.
- Repeatability.
- Safer CRM writes.
- A clean path from prototype to production.

## Public Surfaces

Use whichever surface matches the job:

```bash
deepline plays run ./my-play.play.ts --input '{}' --watch
```

Programmatic SDK:

```ts
client.runPlay(...)
client.runs.get(runId)
client.runs.tail(runId)
ctx.play(name).run(...)
ctx.play(name).runSync(...)
ctx.runPlay(name, input)
```

Raw API:

```http
POST /api/v2/plays/run
GET /api/v2/runs/:runId
GET /api/v2/runs/:runId/tail
```

## Starter Project Shape

```text
gtm-workflows/
  plays/
    signup-to-hubspot-sequence.play.ts
    product-usage-to-campaign-draft.play.ts
    personal-email-to-linkedin-review.play.ts
  evals/
    golden-set.csv
    expected-outcomes.csv
  docs/
    workflow-owner.md
    crm-writeback-rules.md
```

## Minimal Play Skeleton

Use this as the shape, not a copy-paste final. The real implementation should use the exact tools and CRM fields in your workspace.

```ts
import { definePlay } from "deepline";

type Input = {
  source: "signup" | "csv" | "warehouse_segment";
  rows: Array<{
    email?: string;
    domain?: string;
    companyName?: string;
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

## Workflow 1: Signup -> HubSpot Sequence

Use when someone signs up with enough business context to justify fast follow-up.

**Inputs**

- Email.
- Domain.
- Signup source.
- Persona hint.
- Workspace/account ID.

**Steps**

1. Resolve company and contact.
2. Check existing CRM contact/company.
3. Apply suppression rules: customer, open opportunity, competitor, bad domain, unsubscribed, existing sequence.
4. Enrich only what is missing.
5. Score fit using explicit rules.
6. Draft or enroll in the right HubSpot sequence.
7. Log the evidence used.

**Default guardrail:** start with draft-only until the review pass is clean.

## Workflow 2: Product Usage -> Campaign Draft

Use when product activity is trapped in the warehouse and sales only hears about it after someone exports a list.

**Inputs**

- Workspace ID.
- Account domain.
- Product event summary.
- CRM account/opportunity state.
- Owner.

**Steps**

1. Pull the recent product events.
2. Join account and CRM context.
3. Backtest which events happened before real revenue moments.
4. Remove obvious false positives.
5. Generate rep context and a campaign draft.
6. Send high-confidence accounts to review or CRM tasks.

**Important:** if you do not have a semantic layer, the first pass will probably overfit to obvious events like `signed_in` or `signed_up`. Add product context, event definitions, and examples until the output is directionally useful.

## Workflow 3: Personal Email -> LinkedIn Review

Use when PLG signups arrive from Gmail, iCloud, Outlook, or university emails.

**Inputs**

- Personal email.
- Name if available.
- Product workspace.
- IP/company hint if available.
- Referrer or invite source.

**Steps**

1. Generate candidate identity matches.
2. Resolve likely LinkedIn profile and company.
3. Compare name, location, role, domain, and product context.
4. Accept only high-confidence matches.
5. Send ambiguous matches to review.
6. Write verified identity back to CRM or workspace context.

**Default guardrail:** never auto-accept a weak personal-email match.

## Workflow 4: Event Attendee -> Follow-Up Draft

Use when an event list is valuable but too messy to hand directly to sales.

**Inputs**

- Registration list.
- Check-in list.
- Event topic.
- Sponsor/partner context.
- CRM account state.

**Steps**

1. Normalize emails and company names.
2. Match to accounts and contacts.
3. Prioritize checked-in attendees over registrants.
4. Exclude customers and active opportunities unless the play is customer expansion.
5. Draft personalized follow-up using event context.
6. Route to owner or campaign.

## Workflow 5: Champion Job Change -> Account Map

Use when a previous buyer or power user moves companies.

**Inputs**

- Known champion.
- Old company.
- New company.
- Prior relationship context.
- CRM ownership.

**Steps**

1. Verify the job change.
2. Resolve the new company.
3. Check if the new account exists in CRM.
4. Enrich buying committee context.
5. Draft a warm reactivation message.
6. Log the relationship evidence.

## Eval Starter Kit

Do not start by building a giant benchmark. Start with a tiny golden set that catches the expensive mistakes.

**20 rows is enough for V1:**

- 5 obvious good records.
- 5 obvious bad records.
- 5 ambiguous records.
- 5 records that used to break the workflow.

**Check deterministic things first:**

- Did we suppress customers?
- Did we avoid open opportunities?
- Did we preserve the CRM owner?
- Did we avoid overwriting verified fields?
- Did every accepted record have evidence?
- Did every rejected record have a reason?

**Use an LLM judge only where judgment is actually required:**

- Is this account summary useful?
- Is this campaign draft specific enough?
- Does the recommended action match the evidence?
- Is this identity match plausible?

## Production Checklist

- Workflow owner named.
- Input schema documented.
- CRM writeback fields documented.
- Suppression rules agreed with sales/marketing ops.
- Dry run passes the golden set.
- Review queue exists for ambiguous rows.
- Run summary includes accepted, rejected, reviewed, and failed counts.
- Cost per run is visible.
- Rollback path exists.

## The Practical Rule

Prototype fast. Productionize only the winners.

The point is not to turn every GTM idea into infrastructure. The point is to make the ideas that work repeatable, observable, and safe enough to run without a weekly CSV ritual.
