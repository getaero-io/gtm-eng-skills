# Researched Typefully drafts

Updated 2026-06-05 with final Deepline URLs and YouTube draft links.

Live Typefully update status: blocked by local `TYPEFULLY_API_KEY` returning HTTP 403. Use this file as the source of truth for the existing Typefully drafts until the key is regenerated.

## Publish links

| Video | YouTube draft | Blog page |
| --- | --- | --- |
| Waterfall Complexity | https://www.youtube.com/watch?v=OBgolIUXLhQ | https://deepline.com/blog/waterfall-enrichment-workflow-engineering |
| Provider Sprawl | https://www.youtube.com/watch?v=3gtXZ6UwimE | https://deepline.com/blog/provider-sprawl-gtm-workflows |
| Speedrun Time to Integration | https://www.youtube.com/watch?v=rckDRNylVg8 | https://deepline.com/blog/snowflake-crm-campaign-workflow |
| Pipeline as Code | https://www.youtube.com/watch?v=qecZWS4DerQ | https://deepline.com/blog/pipeline-as-code-account-mapping |

Publishing note: for LinkedIn, upload the video natively and put the YouTube/blog URLs in the first comment. For X and Threads, use the YouTube URL in the final post when publishing the thread.

Created from `last30days` research on 2026-06-01 plus the three Sung transcripts.

Research angles that should resonate:

- Claude/MCP is hot, but people are worried about prompt drift, permission scope, and cost walls.
- The credible enemy is not "manual work." It is fragile GTM systems that only work because one operator remembers the ritual.
- Apollo, Clay, and MCP are familiar references. Do not dunk on them. Use them as the old workflow primitives.
- The funniest pain is "CSV Sherpa": the technical GTM operator as pack animal for files, fields, and failed matches.
- People like terminal-first workflows, but the grown-up question is whether the list is valid and the campaign survives week two.
- "Access" is not the same as guardrails. MCP gets tools talking. It does not decide what should happen, what should be approved, or what should stay in draft mode.

## Waterfall Complexity

### Draft 1: Apollo is not the workflow

X:

Apollo is useful.

Apollo is not the workflow.

The workflow is what happens after Apollo gives you 65% coverage and everyone pretends the other 35% will resolve itself through vibes.

Provider fallback.
Cost approval.
Verification.
CSV output.

That is the actual product surface.

LinkedIn:

Apollo is useful.

Apollo is not the workflow.

The workflow is what happens after Apollo gives you partial coverage and the team still needs a real list.

Now you need provider fallback, cost approval, verification, and a clean output someone can trust enough to put into a campaign.

That is the part most GTM teams hide in a spreadsheet, a Slack thread, and one person's memory.

Sung's waterfall video is good because it shows the boring part directly: Deepline previews the run, asks before the paid enrichment, shows which provider verified the email, and returns the CSV.

The interesting part is not "AI found an email."

The interesting part is that the workflow has receipts.

Threads:

Apollo is useful.

Apollo is not the workflow.

The workflow starts when coverage runs out and someone has to decide what happens next.

### Draft 2: Enrichment roulette

X:

Most enrichment workflows are just casino games with CSV export.

Swipe card.
Try provider.
Try another provider.
Ask Claude.
Squint at the output.
Wonder if that cost $10 or $50.

This is fine if your GTM motion is managed by a sleep-deprived operator with 14 tabs open.

LinkedIn:

Most enrichment workflows are more like roulette than teams want to admit.

Try one provider.
Try another.
Ask Claude to clean it up.
Export the CSV.
Check ten rows by hand.
Hope the paid run did not quietly burn money on bad matches.

The mature version is less exciting:

Show the path.
Estimate the spend.
Ask for approval.
Verify the result.
Return the output.

That is what I like about the Deepline waterfall demo. It turns "go enrich this" into a run you can actually inspect.

Much less magical.

Much more useful.

Threads:

Enrichment should not feel like roulette.

If the workflow spends money, I want to know where, why, and what came back.

Wild preference, apparently.

### Draft 3: The 35% problem

X:

The annoying part of enrichment is not the first 65%.

It is the remaining 35% where the system starts asking the nearest GTM person to become:

data engineer
vendor manager
CSV janitor
deliverability risk officer
and part-time therapist for the sales team

LinkedIn:

The first 65% of enrichment is usually not the problem.

The problem is the rest.

That is where the workflow starts asking one GTM operator to become a data engineer, vendor manager, CSV janitor, deliverability risk officer, and part-time therapist for the sales team.

This is why "just connect Apollo to Claude" is not enough.

The missing layer is what happens when coverage stops being easy:

- Which provider goes next?
- What will it cost?
- Which rows should be skipped?
- Which emails are verified?
- What is safe to use in outbound?

That is the layer Sung is showing in the Deepline waterfall walkthrough.

Threads:

The first 65% of enrichment is not the problem.

The other 35% is where GTM operators age in dog years.

## Provider Sprawl

### Draft 4: CSV Sherpa

X:

A lot of GTM engineering is just being a CSV Sherpa.

Apollo to Crustdata.
Crustdata to Clay.
Clay to Claude.
Claude to enrichment.
Enrichment to Instantly.

Then someone asks, "why is this account in the campaign?"

And the whole room looks at the spreadsheet like it killed a man.

LinkedIn:

"CSV Sherpa" is the best phrase in Sung's provider sprawl video.

Because that is what a lot of GTM engineering has become.

Move the file here.
Add a column.
Export again.
Paste into Claude.
Run a score.
Export again.
Import into Instantly.
Hope nothing broke.

That can work once.

It does not work as an operating model.

The sharper question is not "which provider has the data?"

The sharper question is "where does the run get explained?"

If the answer is "in three CSVs and the mind of the operator," you do not have a system yet.

Threads:

CSV Sherpa is not a GTM strategy.

It is a cry for help with column headers.

### Draft 5: The space between tools

X:

The problem is not Apollo.

Or Clay.

Or Crustdata.

Or Claude.

The problem is the haunted hallway between them where CSVs go to become "pipeline."

LinkedIn:

The problem is usually not Apollo.

Or Clay.
Or Crustdata.
Or Claude.
Or Instantly.

Each tool can make sense on its own.

The problem is the space between them.

That is where the TAM build turns into a ritual:

export here, enrich there, score over there, personalize somewhere else, then push the final CSV and pray the field mapping survived.

Sung's Provider Sprawl walkthrough is useful because it does not pretend the world needs one more database.

It shows the actual problem: no one owns the run.

Threads:

Every GTM tool looks reasonable in isolation.

The workflow breaks in the haunted hallway between them.

### Draft 6: House of cards

X:

If your TAM build only works because one person remembers which CSV went where, you do not have a system.

You have a house of cards with HubSpot permissions.

LinkedIn:

If your TAM build only works because one person remembers which CSV went where, you do not have a system.

You have a house of cards with HubSpot permissions.

The test is simple:

Can someone explain why an account made the list?
Which provider found the contact?
Which rule scored it?
Which email was verified?
Which rows got skipped?
What changed from the last run?

If those answers live in someone's head, the workflow is already too fragile.

This is the provider sprawl problem.

The fix is not always fewer tools.

Sometimes it is one place where the run gets explained.

Threads:

If one person has to remember how the TAM build worked, the TAM build did not work.

It performed.

Like theater, but with worse field mapping.

## Speedrun Time to Integration

### Draft 7: MCP is access, not adulthood

X:

MCP gives you access.

It does not give you adulthood.

You still need permissions, approvals, draft mode, retries, field mapping, and someone checking that the campaign did not become a small act of violence against your CRM.

LinkedIn:

MCP gives you access.

It does not give you adulthood.

That is the cleanest way I can describe the next phase of GTM engineering.

Connecting tools is getting easier. Good.

But a real GTM workflow still needs permissions, approvals, draft mode, retries, field mapping, and a way to verify the output before it touches customers.

That is what Sung shows in the Speedrun video.

Snowflake to Attio to Instantly is not impressive because the APIs exist.

It is impressive if the workflow is safe enough to rerun.

Threads:

MCP gives you access.

It does not give you adulthood.

The boring stuff still matters: permissions, approvals, drafts, and checking the output.

### Draft 8: For 20 users, CSVs are fine

X:

For 20 users, CSVs are fine.

For 1 million users, CSVs become a workplace injury.

LinkedIn:

For 20 users, CSVs are fine.

Export from Snowflake. Eyeball the rows. Add a column. Upload to Instantly.

No one needs to make a religion out of it.

But the same workflow at 1 million users is different.

Now you need scoped access, synced CRM attributes, campaign creation, approval steps, and a way to check the result.

That is the difference between a hack and a system.

Sung's Speedrun video is basically this exact line: product data in Snowflake, lifecycle attributes in Attio, campaign in Instantly, all through a run you can inspect.

Threads:

For 20 users, CSVs are fine.

For 1 million users, CSVs become a workplace injury.

### Draft 9: The agent finishing is not the bar

X:

"The agent finished" is not the bar.

The bar is:

Did the CRM update?
Did the campaign draft?
Did the right leads move?
Can I verify it?
Will this destroy deliverability in week two?

The confetti animation can wait.

LinkedIn:

"The agent finished" is not the bar.

That is the mistake in a lot of GTM AI demos.

The real questions are:

Did the CRM update?
Did the campaign draft instead of launching?
Did the right leads move?
Can I verify the source data?
Will this destroy deliverability in week two?

The Speedrun video gets this right because Sung works backward from the output.

Campaign exists in Instantly.
Leads are there.
Sequence exists.
CRM attributes updated.

That is the bar.

Not "the agent completed."

"The system did the right thing."

Threads:

"The agent finished" is not the bar.

"The system did the right thing and I can prove it" is the bar.

Less confetti. More receipts.

## Category / meta posts

### Draft 10: GTM engineer as buyer

X:

The buyer for GTM tools is changing.

Less:
"does this dashboard look nice?"

More:
"can I wire this into Snowflake, inspect the run, keep it in draft mode, and avoid turning my CRM into soup?"

LinkedIn:

The buyer for GTM tools is changing.

It used to be easy to imagine the buyer as someone comparing dashboards.

Increasingly, it is a technical GTM operator asking different questions:

Can I wire this into Snowflake?
Can I inspect what happened?
Can I keep the campaign in draft mode?
Can I see provider cost before the run?
Can I rerun this next week without rebuilding it?
Can I avoid turning my CRM into soup?

That buyer does not want magic.

They want leverage with guardrails.

Threads:

The GTM buyer is changing.

Less "nice dashboard."

More "can I wire this into the system without turning Salesforce into soup?"

### Draft 11: Prompt drift

X:

Relying on Claude for GTM without a real workflow is how you get prompt drift wearing a Patagonia vest.

It looks productive.

Then week two arrives and nobody knows why the list changed.

LinkedIn:

One of the better comments from the GTM engineering research was simple:

Relying entirely on Claude for GTM can turn into prompt drift fast.

I think that is right.

Claude is great at helping an operator move quickly.

But if the scoring logic, enrichment path, approvals, and campaign rules only live in the prompt, the workflow is going to mutate.

It will still feel productive.

That is the dangerous part.

The goal is not to stop using Claude.

The goal is to make the run explicit enough that Claude has rails.

Threads:

Prompt drift is scarier in GTM than people admit.

The workflow still looks productive.

It just quietly becomes a different workflow.

### Draft 12: Week two deliverability

X:

The coolest GTM demo in the world does not matter if week two turns your sending domain into a crime scene.

Invalid lists are not a tooling problem.

They are a reputation problem with invoices.

LinkedIn:

The funniest critique of terminal-first GTM demos is also the most useful one:

Cool workflow.

But what happens in week two?

If the list is invalid, the personalization does not matter. If the domains are sketchy, the campaign does not matter. If the workflow cannot explain what got verified, the demo was mostly theater.

This is why I think the next wave of GTM engineering content has to move past "look what the agent did."

The better question is:

Would you trust this campaign after the demo ends?

Threads:

The coolest outbound demo does not matter if week two turns your sending domain into a crime scene.

Validity beats vibes.

## Pipeline as Code

### Draft 13: Spreadsheets are where workflow logic goes to hide

X:

Spreadsheets are a great place to inspect a GTM workflow.

They are a terrible place to own one.

If the targeting logic lives in a tab, the real system is whoever remembers which column means "good enough to send."

Video: https://www.youtube.com/watch?v=qecZWS4DerQ

LinkedIn:

Spreadsheets are a great place to inspect a GTM workflow.

They are a terrible place to own one.

That is the quiet problem with a lot of account mapping.

The targeting logic starts as a reasonable exercise: define an ICP, find signals, score accounts, route contacts, prepare a campaign.

Then it slowly becomes a tab with 47 columns and one person who knows which three columns actually matter.

Sung's Pipeline as Code walkthrough is useful because it points at the grown-up version:

make the logic editable, repeatable, and inspectable.

Not because every GTM person needs to become a software engineer.

Because the workflow should survive the person who built the first version.

Video: https://www.youtube.com/watch?v=qecZWS4DerQ

Blog: https://deepline.com/blog/pipeline-as-code-account-mapping

Threads:

Spreadsheets are a great place to inspect a GTM workflow.

They are a terrible place to own one.

If the targeting logic lives in a tab, the real system is whoever remembers the tab.

### Draft 14: Pipeline as code is just "please make this repeatable"

X:

"Pipeline as code" sounds intense until you translate it.

It means:

can we rerun this account mapping workflow next week without rebuilding the whole thing from vibes, Slack messages, and an ancient CSV named final_FINAL.csv?

Video: https://www.youtube.com/watch?v=qecZWS4DerQ

LinkedIn:

"Pipeline as code" sounds more intense than it is.

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

Video: https://www.youtube.com/watch?v=qecZWS4DerQ

Blog: https://deepline.com/blog/pipeline-as-code-account-mapping

Threads:

"Pipeline as code" mostly means:

please let me rerun this workflow without reconstructing it from vibes and a CSV called final_FINAL.csv.

### Draft 15: The ICP should not live in one operator's head

X:

Your ICP should not live in one operator's head.

Neither should:

account scoring
contact routing
field mapping
campaign creation
the reason a company made the list

That is not strategy.

That is undocumented folklore with API keys.

Video: https://www.youtube.com/watch?v=qecZWS4DerQ

LinkedIn:

Your ICP should not live in one operator's head.

Neither should account scoring, contact routing, field mapping, campaign creation, or the reason a company made the list.

But this is exactly how a lot of GTM systems work.

The workflow looks modern from the outside because it uses Apollo, Clay, Claude, a CRM, and a sending tool.

Inside, it is still undocumented folklore with API keys.

The interesting thing about Sung's Pipeline as Code video is that it makes a boring point well:

the workflow is only real when someone else can inspect it, change it, and rerun it.

That is the line between clever automation and an actual GTM system.

Video: https://www.youtube.com/watch?v=qecZWS4DerQ

Blog: https://deepline.com/blog/pipeline-as-code-account-mapping

Threads:

Your ICP should not live in one operator's head.

Neither should the reason an account made the campaign.

Undocumented folklore with API keys is still folklore.
