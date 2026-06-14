# Lead Magnet Sequence Drafts

Order:

1. `WORKFLOWS`: V2 implementation guide.
2. `PROVIDERS`: provider stack decision matrix.
3. `WATERFALL`: waterfall cost optimization framework.

PLG is already shipped. Do not use `PLG` as the next CTA.

## Post 1: Workflows

### LinkedIn

Most GTM workflows die in the same place:

someone proves the play works, then it gets buried in a script, Zap, spreadsheet, or reverse ETL job nobody wants to own.

The hard part is not "can we enrich this list?"

It is:

- what triggers the workflow
- what data is allowed to update the CRM
- what gets sent to review
- what evidence gets logged
- what happens when the provider is wrong
- how you test it before sales sees it

That is why we are moving more of this into typed Deepline V2 plays.

Think:

signup -> enrichment -> suppressions -> CRM context -> campaign draft -> approval -> writeback

Same workflow you used to hack together across five tools, but with TypeScript, run logs, guardrails, and a path from local test to production.

Sung walks through the shape in the video.

Comment `WORKFLOWS` and I will send the V2 GTM workflow implementation guide.

### X

Most GTM workflows die after the first successful demo.

The play works, then it becomes a script, Zap, spreadsheet, or reverse ETL job nobody wants to own.

The fix is boring:

typed workflow
clear inputs
guardrails
dry run
approval
CRM writeback
run logs

Comment WORKFLOWS and I will send the V2 implementation guide.

### Threads

The least glamorous part of GTM engineering is the part that matters:

making the workflow repeatable after the first hacked-together version works.

Signup -> enrichment -> suppressions -> CRM context -> campaign draft -> approval -> writeback.

Comment WORKFLOWS and I will send the V2 guide.

## Post 2: Providers

### LinkedIn

Provider sprawl is what happens when every GTM workflow starts with:

"let's just add one more enrichment vendor."

Then six months later nobody knows:

- which provider is trusted for which field
- why a row was accepted
- why two vendors disagree
- whether the expensive provider was even needed
- what should be written back to CRM

The answer is not fewer providers. It is a provider decision matrix.

Which tool runs for identity?
Which runs for mobile?
Which runs only after LinkedIn is present?
Which result needs corroboration?
Which fields should never be overwritten?

Sung's Provider Sprawl video is the cleanest explanation of this problem.

Comment `PROVIDERS` and I will send the provider stack decision matrix.

### X

Provider sprawl is not "we use too many data vendors."

It is "we do not know which vendor is trusted for which job."

Identity, mobile, company, title, email, intent, CRM writeback.

Each needs different routing + confidence rules.

Comment PROVIDERS and I will send the decision matrix.

### Threads

The provider problem is not the number of vendors.

It is running them without a decision matrix.

Which vendor owns which field? When do you stop? What gets reviewed? What is safe to write to CRM?

Comment PROVIDERS and I will send the matrix.

## Post 3: Waterfall

### LinkedIn

Waterfalls are where GTM engineering starts to pay for itself.

If every row hits every provider, you are not building a workflow. You are lighting money on fire with better logging.

The better version:

- cheap provider first when precision is good enough
- expensive provider only when the row is worth it
- stop when confidence is high
- route ambiguous matches to review
- backtest cost per accepted result, not cost per API call

That last part matters.

The cheapest provider can be expensive if it creates review work, bad CRM writes, or weak campaigns.

Sung walks through the waterfall complexity in the video.

Comment `WATERFALL` and I will send the cost optimization framework.

### X

Bad waterfall:

run every provider on every row and call it automation.

Good waterfall:

route by input quality, stop on confidence, review ambiguity, measure cost per accepted result.

Not cost per API call.
Cost per usable GTM action.

Comment WATERFALL and I will send the framework.

### Threads

The waterfall question is not "which provider is cheapest?"

It is "what is the cheapest path to a result we trust enough to use?"

Provider order, confidence, stop rules, review queue, cost per accepted result.

Comment WATERFALL and I will send the framework.
