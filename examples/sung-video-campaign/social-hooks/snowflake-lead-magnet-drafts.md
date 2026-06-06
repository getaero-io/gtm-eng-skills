# Snowflake PQL Lead Magnet Drafts

Lead magnet: `examples/sung-video-campaign/lead-magnets/snowflake-pql-campaign-playbook.md`

Notion: `https://app.notion.com/p/Snowflake-PQL-to-Campaign-Playbook-377da8d1d8eb8128b1bde0d84216bf2a`

Typefully priority video draft: `https://typefully.com/t/C8IlPMK`

## Typefully Drafts Created

| Platform | Draft | Draft ID | Private URL | Share URL |
| --- | --- | --- | --- | --- |
| X | CSV workplace injury | 9399812 | https://typefully.com/?d=9399812&a=299886 | https://typefully.com/t/m0ONA4y |
| X | PQL skeptic | 9399813 | https://typefully.com/?d=9399813&a=299886 | https://typefully.com/t/EzxfxiK |
| LinkedIn | Setup guide launch | 9399814 | https://typefully.com/?d=9399814&a=299886 | https://typefully.com/t/9td9Ovg |
| LinkedIn | PQL skeptic | 9399815 | https://typefully.com/?d=9399815&a=299886 | https://typefully.com/t/XLJmi6q |

## X Drafts

### X 1: CSV Workplace Injury

```text
For 20 users, CSVs are fine.

For 1 million users, CSVs become a workplace injury.

I made the setup guide for the better version:

Snowflake -> dbt -> CRM guardrails -> campaign draft.

Comment PQL and I will send it.
```

### X 2: PQL Skeptic

```text
Most PQL scoring is just "clicked a button twice" dressed up as intent.

The version I trust has 3 parts:

product usage
account fit
CRM context

Then guardrails before anything touches a campaign.

I wrote the setup guide. Comment PQL.
```

### X 3: Agent Finished

```text
"The agent finished" is not the bar.

Did the CRM update?
Did the campaign stay in draft?
Were customers suppressed?
Can the rep see why the account moved?

That is the bar.

I put the Snowflake PQL setup guide together. Comment PQL.
```

### X 4: dbt Is Where The Definition Lives

```text
If your PQL definition lives in a spreadsheet, sales will eventually stop trusting it.

Put it in dbt.

Then route it through CRM context, suppressions, and draft-mode campaigns.

I wrote the Snowflake setup guide. Comment PQL and I will send it.
```

### X 5: Not Another Dashboard

```text
The useful artifact is not another dashboard.

It is a rerunnable workflow:

warehouse signal
CRM context
suppression check
rep explanation
campaign draft
run summary

I packaged the Snowflake PQL guide. Comment PQL.
```

### X 6: Workflow Library

```text
I put 12 PLG/GTM workflow examples into the Snowflake PQL guide:

trial setup
team adoption
stale CRM
job change
renewal expansion
usage drop
integration intent
failed workflow rescue

Comment PQL and I will send it.
```

### X 7: Rep Question

```text
The rep question is simple:

"Why is this account in my campaign?"

If your system cannot answer that, you do not have a PQL workflow.

You have a score with vibes attached.

I wrote the setup guide. Comment PQL.
```

### X 8: Mixmax Angle

```text
The Mixmax lesson:

product usage signals should reallocate rep attention.

Not create one more dashboard.
Not create one more CSV.
Not give sales a mystery score.

I made a Snowflake -> dbt -> CRM -> campaign setup guide. Comment PQL.
```

## LinkedIn Drafts

### LinkedIn 1: Setup Guide Launch

```text
For 20 users, CSVs are fine.

Export from Snowflake. Eyeball the rows. Add a column. Upload to Instantly.

No one needs to make a religion out of it.

But the same workflow at 1 million users is different.

Now you need:

- product usage signals
- account fit
- CRM context
- customer suppressions
- owner checks
- draft-mode campaigns
- a run summary

That is the difference between a hack and a GTM system.

I turned Sung's Snowflake speedrun into a setup guide:

Snowflake query -> dbt model -> CRM guardrails -> campaign draft.

It includes 12 PLG + GTM engineering examples:

- trial setup completed, no sales touch
- free workspace with team adoption
- high usage, stale CRM
- product champion changed jobs
- expansion signal before renewal
- usage drop before renewal
- integration intent
- failed workflow rescue
- dormant high-fit account reactivation

The useful artifact is not another dashboard.

It is the workflow that lets a rep ask, "why is this account in my campaign?" and get a real answer.

Comment PQL and I will send the guide.
```

### LinkedIn 2: PQL Skeptic

```text
A lot of PQL scoring is fake precision.

Clicked a button twice.
Viewed pricing.
Invited one teammate.
Magically becomes "sales ready."

That is how you get reps to ignore the score.

The version I trust has three parts:

1. Product usage
2. Account fit
3. CRM context

Then it needs guardrails before anything touches a campaign:

- block customers
- block open opportunities
- block unsubscribes and bounces
- require account owner
- keep the campaign in draft mode
- show sample rows before approval
- log what moved and what got blocked

Otherwise you did not build a PQL workflow.

You built a faster way to annoy sales.

I wrote the setup guide for the Snowflake version:

Snowflake -> dbt -> CRM -> campaign draft.

Comment PQL and I will send it.
```

### LinkedIn 3: dbt Definition

```text
If your PQL definition lives in a spreadsheet, it will drift.

Someone changes a threshold.
Someone adds a column.
Someone forgets which export was the real one.
Sales starts asking why a random account showed up in the sequence.

Then the whole thing becomes "ops magic."

Put the definition in dbt.

Not because dbt is trendy.

Because the definition should be:

- versioned
- rerunnable
- reviewable
- testable
- explainable

Then use Deepline/Aero to inspect the run, check CRM guardrails, and draft the campaign.

The actual pattern is simple:

signal + context + guardrail + draft action + run summary

I packaged the Snowflake PQL setup guide with the query, dbt model, tests, and 12 PLG/GTM workflow examples.

Comment PQL and I will send it.
```

### LinkedIn 4: Agent Finished Is Not The Bar

```text
"The agent finished" is not the bar.

That is the mistake in a lot of GTM AI demos.

The real questions are worse and more useful:

Did the CRM update?
Did the campaign stay in draft?
Were customers suppressed?
Were open opportunities blocked?
Did the right owner get assigned?
Can the rep see why the account moved?
Can we rerun this next week?

That is the bar.

I turned the Snowflake speedrun into the setup guide I would want if I were implementing this:

- event map
- Snowflake query
- dbt model
- dbt tests
- CRM guardrails
- campaign draft play
- PLG workflow examples

Comment PQL and I will send it.
```

### LinkedIn 5: Workflow Library

```text
The Snowflake PQL guide now has 12 workflow examples.

Not abstract "intent."

Actual PLG + GTM engineering motions:

1. Trial setup completed, no sales touch
2. Free workspace with team adoption
3. High-usage account, stale CRM
4. Product champion changed jobs
5. Expansion signal before renewal
6. Usage drop before renewal
7. Product-led inbound prioritization
8. Integration intent
9. Failed workflow rescue
10. Dormant high-fit account reactivation
11. Multi-threading target account
12. Self-serve account ready for sales assist

Each one follows the same pattern:

warehouse signal
CRM context
suppression check
draft action
run summary

That pattern matters more than the score.

Comment PQL and I will send the setup guide.
```

### LinkedIn 6: Mixmax Lesson

```text
The Mixmax lesson is not "build a PQL dashboard."

It is that product usage signals should change where reps spend time.

That is the part people miss.

A PQL workflow is only useful if it reallocates attention:

away from low-fit accounts
toward high-fit accounts
with enough context that a rep knows why they are reaching out

So the setup guide starts with the workflow, not the score:

What product behavior matters?
What CRM context changes the action?
What gets suppressed?
What stays in draft mode?
What does the rep see?
What gets logged?

I put the Snowflake query, dbt model, CRM guardrails, and PLG workflow examples into a guide.

Comment PQL and I will send it.
```
