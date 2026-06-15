# Lead Magnet Sequence Drafts

Order:

1. `WORKFLOWS`: V2 implementation guide.
2. `PROVIDERS`: provider stack decision matrix.
3. `WATERFALL`: waterfall cost optimization framework.

PLG is already shipped. Do not use `PLG` as the next CTA.

## Post 1: Workflows

Target publish date: Tuesday, June 16, 2026.

Video: Sung Pipeline as Code walkthrough.

CTA: Comment `WORKFLOWS`.

### LinkedIn

Most GTM workflows die after the first successful demo.

Someone proves the play works. Then it becomes a script, Zap, spreadsheet, reverse ETL job, or "ask the ops person" ritual nobody wants to own.

We have seen this pattern across real GTM engineering work:

- messy CSV repair
- signup -> HubSpot sequence
- work email waterfalls
- product signal scoring
- known account -> right contact
- Slack approval loops
- CRM writeback with evidence
- campaign drafts reps can actually inspect

The hard part is not "can we enrich this list?"

It is:

- what triggers the workflow
- what data is allowed to touch the CRM
- what gets blocked
- what needs review
- what evidence gets logged
- how you test it before sales sees it

That is why we are moving more of this into typed Deepline V2 plays.

Input contract. Provider routing. Guardrails. Dry runs. Review queues. Run logs. CRM writeback.

Less "here is a clever demo."

More "here is the workflow you can run again next Tuesday without asking who owns it."

Sung walks through the shape in the video.

Comment `WORKFLOWS` and I will send the V2 GTM workflow implementation guide + 20-row eval template.

### X

Most GTM workflows die after the first successful demo.

The play works, then becomes a script, Zap, spreadsheet, or reverse ETL job nobody wants to own.

The fix is boring:

typed input
provider routing
guardrails
dry run
review queue
CRM writeback
run logs

Comment WORKFLOWS and I will send the V2 guide + 20-row eval template.

### Threads

Most GTM workflows die after the first successful demo.

The play works once. Then nobody knows who owns the script, spreadsheet, Zap, enrichment order, approval step, or CRM writeback.

The useful version is boring:

input contract, guardrails, dry run, review queue, run logs, writeback.

Comment WORKFLOWS and I will send the V2 implementation guide.

## Post 2: Providers

Target publish date: Thursday, June 18, 2026.

Video: Sung Provider Sprawl walkthrough.

CTA: Comment `PROVIDERS`.

### LinkedIn

Provider sprawl is not "we use too many data vendors."

It is "nobody knows which system is allowed to be right."

That is how you end up with:

- one tool for emails
- another for mobile
- another for company data
- another for intent
- another for product usage
- a CRM full of fields nobody trusts
- a spreadsheet explaining which one to believe

The better question is not "which provider is best?"

It is:

- who owns identity?
- who owns work email?
- who owns mobile?
- who owns title?
- who owns company?
- who owns usage?
- what needs corroboration?
- what should never overwrite CRM?

Provider choice gets much easier when every field has an owner, fallback, review trigger, and writeback policy.

Sung's Provider Sprawl video is the cleanest walkthrough of the problem.

Comment `PROVIDERS` and I will send the provider ownership matrix.

### X

Provider sprawl is not "we use too many vendors."

It is "we do not know which system is allowed to be right."

Identity, email, mobile, title, company, usage, intent, CRM writeback.

Each needs an owner, fallback, review trigger, and writeback rule.

Comment PROVIDERS and I will send the matrix.

### Threads

The provider problem is not the number of vendors.

It is running them without a field-level decision matrix.

Which system owns email? Mobile? Title? Product usage? Intent? What gets reviewed? What is safe to write to CRM?

Comment PROVIDERS and I will send the matrix.

## Post 3: Waterfall

Target publish date: Saturday, June 20, 2026.

Video: Sung Waterfall Complexity walkthrough.

CTA: Comment `WATERFALL`.

### LinkedIn

Bad enrichment waterfalls are just expensive loops with better branding.

Every row hits every provider.

Every "maybe" result gets accepted.

Nobody measures review time.

Nobody knows whether the expensive provider was needed.

The useful version is much simpler:

- route by input quality
- use cheap providers when confidence is good enough
- save expensive calls for rows worth saving
- stop when confidence is high
- send ambiguous matches to review
- measure cost per accepted result

Not cost per API call.

Cost per usable GTM action.

That is the number that matters when the workflow writes to CRM, triggers a sequence, or gives sales a reason to act.

Sung walks through the waterfall complexity in the video.

Comment `WATERFALL` and I will send the cost optimization framework. We are turning it into a calculator too: paste your provider order + costs, get routing recommendations.

### X

Bad waterfall:

run every provider on every row and call it automation.

Good waterfall:

route by input quality
stop on confidence
review ambiguity
measure cost per accepted result

Not cost per API call.
Cost per usable GTM action.

Comment WATERFALL and I will send the framework.

### Threads

The waterfall question is not "which provider is cheapest?"

It is "what is the cheapest path to a result we trust enough to use?"

Provider order, confidence, stop rules, review queue, cost per accepted result.

Comment WATERFALL and I will send the framework.
