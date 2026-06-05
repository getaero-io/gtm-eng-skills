# Social hooks for Sung video campaign

Use these as hooks or first drafts. Add the clip natively on each platform. Keep links out of the main LinkedIn post.

Final publish links:

| Video | YouTube draft | Blog page |
| --- | --- | --- |
| Waterfall Complexity | https://www.youtube.com/watch?v=OBgolIUXLhQ | https://deepline.com/blog/waterfall-enrichment-workflow-engineering |
| Provider Sprawl | https://www.youtube.com/watch?v=3gtXZ6UwimE | https://deepline.com/blog/provider-sprawl-gtm-workflows |
| Speedrun Time to Integration | https://www.youtube.com/watch?v=rckDRNylVg8 | https://deepline.com/blog/snowflake-crm-campaign-workflow |
| Pipeline as Code | https://www.youtube.com/watch?v=qecZWS4DerQ | https://deepline.com/blog/pipeline-as-code-account-mapping |

## Waterfall Complexity

Core conversation: enrichment is no longer a lookup. It is workflow engineering.

### X hooks

1. Waterfall enrichment used to mean "try another provider."

Now it means Apollo, MCP, CSVs, cost approval, failed matches, provider routing, and someone checking whether the final email is real.

That is not a lookup.

It is workflow engineering.

2. Apollo is useful.

Apollo is not the workflow.

The workflow is everything that happens when Apollo does not return a verified email.

3. A CSV is a weird place to hide an enrichment workflow.

Provider tried.
Provider failed.
Fallback used.
Email verified.
Spend approved.

All of that should be visible.

### LinkedIn hooks

1. Waterfall enrichment got mislabeled.

People talk about it like the question is "which provider should we use?"

That is only the first question.

The real workflow is:

- which provider goes first
- when to stop spending
- what to do when coverage stalls
- how to verify the result
- whether a human approves the full run
- what gets written back to the CSV

Apollo can be useful and still not be the workflow.

Sung walked through the cleaner version: run it from Claude Code, preview the path, approve the cost, see which provider verified each email, and get the final CSV.

The interesting part is not enrichment.

The interesting part is making enrichment explain itself.

2. I think a lot of GTM teams are underestimating how much process is hidden inside "just enrich the list."

There is provider choice.
There is cost control.
There is fallback logic.
There is verification.
There is human approval.
There is output formatting.

If those steps live in someone's head, the workflow is not real yet.

This Sung video shows what it looks like when the waterfall becomes visible.

### Threads hooks

1. "Just enrich the list" hides a lot.

Provider choice.
Fallback logic.
Cost approval.
Verification.
CSV output.

That is the workflow.

2. Apollo can find some emails.

The hard part starts when Apollo does not.

3. The better waterfall is not more providers.

It is a visible path to a valid result.

## Provider Sprawl

Core conversation: TAM builds break because every tool owns one step and nobody owns the run.

### X hooks

1. A lot of GTM engineering is just being a CSV Sherpa.

Apollo to Crustdata.
Crustdata to Clay.
Clay to Claude.
Claude to enrichment.
Enrichment to Instantly.

Then someone asks "how did we build this list?"

Silence.

2. The problem is not Apollo.

Or Clay.

Or Crustdata.

The problem is the space between them.

That is where the workflow breaks.

3. If your TAM build only works because one person remembers which CSV went where, you do not have a system.

You have a ritual.

### LinkedIn hooks

1. Most TAM builds are house of cards.

The request sounds simple:

"Find companies that match this ICP, get the right contacts, verify emails, score them, and push the campaign live."

Then reality shows up:

- Apollo for the first pull
- Crustdata for company signals
- Clay for enrichment
- Claude Code for scoring
- Prospeo or LeadMagic for email
- Salesforce or Attio for CRM
- Instantly for the campaign

Every tool can make sense.

The weak point is the handoff between them.

That is what Sung's Provider Sprawl walkthrough gets right. The enemy is not any one vendor. The enemy is the process living in CSVs and memory.

2. "CSV Sherpa" is the best description I have heard for a surprising amount of GTM work.

Move the file here.
Add a column.
Export again.
Paste into Claude.
Run a score.
Export again.
Import somewhere else.
Hope nothing broke.

That can work once.

It does not work as an operating model.

The next version of GTM tooling has to own the run, not just one cell in the table.

### Threads hooks

1. CSV Sherpa is not a GTM strategy.

It is a symptom.

2. A TAM build should answer one basic question:

"How did this company make the list?"

If the answer lives in a Slack thread and three CSVs, the workflow is already too fragile.

3. Provider sprawl is not having too many tools.

It is having no single place where the run is explained.

## Speedrun Time to Integration

Core conversation: GTM teams do not need more clever API glue. They need safe, repeatable runs across product data, CRM, and campaign tools.

### X hooks

1. For 20 users, CSVs are fine.

For 1 million users, CSVs are a bug.

2. Connecting Snowflake to a CRM to a campaign tool is not the hard part.

The hard part is making the run safe enough that you trust it.

3. MCP gives you access.

GTM teams also need permissions, approvals, drafts, and a way to verify what happened.

4. The brag is not "I stitched together three APIs."

The brag is "I built a repeatable campaign system and can prove it did the right thing."

### LinkedIn hooks

1. I like this framing from Sung's Speedrun video:

Your bragging rights are not that you stitched together cool code.

Your bragging rights are that you created a repeatable, auditable system that works.

That is exactly where GTM engineering is going.

The Snowflake to CRM to Instantly workflow is not hard because APIs exist. It is hard because the system needs guardrails:

- scoped permissions
- clarifying questions
- draft mode
- CRM attributes
- campaign creation
- end-to-end verification

The agent finishing is not the bar.

The system doing the right thing is the bar.

2. A lot of GTM workflows start as a spreadsheet shortcut.

For 20 users, that is fine.

Export from Snowflake. Eyeball the rows. Add a column. Upload to Instantly.

But the same workflow at 1 million users is a different animal.

Now you need scoped access, synced CRM attributes, campaign creation, approval steps, and a way to check the output.

That is the difference between a hack and a system.

### Threads hooks

1. The agent finishing is not the bar.

The system doing the right thing is the bar.

2. Snowflake to CRM to campaign tool should not require a new mini engineering project every time.

3. MCP is useful.

But access is not the same thing as guardrails.

## Pipeline as Code

Core conversation: account mapping breaks when ICP logic, scoring rules, and campaign routing live in one operator's head.

### X hooks

1. "Pipeline as code" sounds intense until you translate it.

It means: can we rerun this account mapping workflow next week without rebuilding the whole thing from vibes, Slack messages, and final_FINAL.csv?

2. Your ICP should not live in one operator's head.

Neither should account scoring, contact routing, field mapping, campaign creation, or the reason a company made the list.

3. Spreadsheets are a great place to inspect a GTM workflow.

They are a terrible place to own one.

### LinkedIn hooks

1. "Pipeline as code" sounds more intense than it is.

The practical version is simple:

Can we rerun this account mapping workflow next week without rebuilding it from vibes, Slack messages, and an ancient CSV named final_FINAL.csv?

That is the actual bar.

GTM teams do not need more religious arguments about no-code versus code.

They need workflows where the logic is visible:

- which accounts qualify
- which signals matter
- which contacts get pulled
- which fields get written
- which campaign gets drafted
- what changed since last time

If that logic is invisible, the workflow is fragile.

If it is inspectable, the team can improve it.

2. Your ICP should not live in one operator's head.

Neither should account scoring, contact routing, field mapping, campaign creation, or the reason a company made the list.

But this is exactly how a lot of GTM systems work.

The workflow looks modern from the outside because it uses Apollo, Clay, Claude, a CRM, and a sending tool.

Inside, it is still undocumented folklore with API keys.

The workflow is only real when someone else can inspect it, change it, and rerun it.

That is the line between clever automation and an actual GTM system.

### Threads hooks

1. Your ICP should not live in one operator's head.

Neither should the reason an account made the campaign.

2. Spreadsheets are a great place to inspect a GTM workflow.

They are a terrible place to own one.

3. Pipeline as code mostly means:

please let me rerun this workflow without reconstructing it from vibes and a CSV called final_FINAL.csv.
