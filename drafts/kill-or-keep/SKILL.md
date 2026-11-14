---
name: kill-or-keep
description: |
  Judge every live outbound campaign against thresholds set before anyone looks at the numbers,
  and return one verdict per campaign: fix deliverability first, kill, scale, keep going, or too
  small to judge. One metric decides it, positive replies per send; opens and raw reply counts
  decide nothing. Reads campaign totals, the per-step funnel and per-sender stats through Deepline's sequencer tools,
  flags senders breaching the bounce guardrail, shows which sequence step produces the replies,
  and, when you supply per-variant results, calls A/B tests only when the sample can actually
  support a winner. It only reads and suggests; nothing changes unless you approve one specific
  action for one specific campaign at the end. Needs campaign data to read: a sequencer connected
  to Deepline (Instantly, Smartlead, Lemlist, HeyReach), another connected sending tool, or a
  campaign export file. Use whenever someone
  asks: should I kill this campaign, which campaigns are working, is this A/B test done, which
  variant won, my reply rate dropped what do I do, audit my live campaigns, which sequence step
  gets the replies, is this sender hurting deliverability. Do NOT use it to write or rewrite
  copy, to build or clean a list, to pause, launch or delete a campaign, to change senders or
  sending limits, or to diagnose DNS and authentication.
ported_from: clay-run/clay-skill-creator/skills/matteo-fois/kill-or-keep
---

# Kill or keep (set the threshold first, then read the number)

The insight: **most bad campaigns are not killed because nobody decided in advance what would
kill them.** Without a threshold written down before the results arrive, every number looks
like it might turn around next week, and losers keep sending.

The evidence is the author's own client work. Across 16 outbound engagements run by one agency,
9 ran A/B tests with no kill rule and 8 killed a failing campaign after the data had already
said so. Concretely: a variant ran three weeks at a 0.1% reply rate before anyone stopped it; a
campaign sent for six weeks with zero positive replies; a test of 50 variations across 5
industries was not pruned until week 8. None of these were hard calls. They were calls nobody
had made in advance.

What follows from it: this skill fixes the thresholds at Step 1, before it reads a single
result, and then applies them mechanically. It kills rarely on purpose. A campaign that has
produced any positive reply and is not chronically below its floor is never killed.

**It suggests; it does not act on its own.** The output is a report of what to kill, keep and
scale. Carrying any of it out is a separate, optional last step, one campaign at a time, and only
when you say yes to that campaign and the tool you send from allows that action.

**It needs campaign data it can read,** from one of three places: a sequencer connected to your
Deepline org (Instantly, Smartlead, Lemlist or HeyReach, read through their `deepline tools`); another
sending tool connected to your agent that exposes campaign stats; or an export file from whatever
tool sends your email. Without one of these there is nothing to
judge, and Step 0 says so before anything else happens.

Do not start a step before the steps above it have their answers. If a declared input is
missing, ask for it. Never assume a default and continue.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's. Ask for it, and where a default
is named below, using it means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Campaign source** | where the campaigns live: a sequencer connected to Deepline, another sending tool connected to the agent that it can read campaign stats from, or a campaign export file from whatever tool sends the email (one row per campaign: campaign name, sent, positive replies, bounces, first send date) | ask. Never assume which sequencer they use, or that it is connected to Deepline |
| **First send date per campaign** | when each campaign sent its first email | Deepline source: read from the daily stats where the sequencer has them (`instantly_get_daily_campaign_analytics`), else the campaign's creation date as a floor (Step 5). Connected tool: read it. File source: a first-send column, or ask. If it stays unknown, no kill can fire on that campaign |
| **Minimum age before a kill** | how many days after the first send a campaign must run before it can be killed | 21 days, the author's line, because replies keep arriving for about three weeks after a send; say so if used |
| **Sender export** | only when the campaign source is a file: one row per sender per campaign with sent and bounces | sender guardrails become unavailable for file sources; campaign verdicts still run |
| **Campaigns in scope** | which campaigns to judge: all active ones, a name filter, or specific campaigns | default is every `active` campaign in the sequencer, or every row in the file; say so |
| **Market tier per campaign** | who each campaign targets: independent (1 to 3 people), small SMB (4 to 50), mid-market (51 to 500), enterprise (500+). Deal size breaks ties | no default. Ask per campaign. Thresholds depend on it entirely |
| **Kill and scale thresholds** | the positive-reply floors per tier | the author's tables below; ask, and if they have no view use them and SAY they are borrowed |
| **What counts as positive** | which reply categories count as a positive reply | no default. If only an automatic sentiment label exists, every positive count is marked provisional: nothing is killed on it, and a scale on it is marked provisional |
| **Bounce guardrail** | the bounce rate that flags a sender | 5% is the author's line; say so if used |
| **Per-variant results** | for A/B verdicts only: one row per variant with sent, positive replies, launch date and sender pool, exported from the campaign UI or any sequencer; on Instantly, `instantly_get_campaign_analytics_steps` supplies it | variant verdicts become unavailable; every other verdict still runs |
| **Timezone** | IANA timezone for date boundaries | UTC; say so |

The author's thresholds, offered as a starting point and never applied silently:

| Tier | Cold-dead KILL | Chronic KILL | SCALE |
|---|---|---|---|
| Independent / solo | 0 positives in the first 1,000 sends | after 3,000 sends, still below 1 per 1,500 | at least 1 per 400, with 3 or more positives |
| Small SMB | 0 in 1,500 | after 4,500, below 1 per 2,000 | at least 1 per 600 |
| Mid-market | 0 in 2,500 | after 7,500, below 1 per 3,500 | at least 1 per 1,000 |
| Enterprise | 0 in 4,000 | after 12,000, below 1 per 6,000, and no meetings | at least 1 per 1,500, or any booked meeting |

The cold-dead number is the fair-chance window. Below it, a campaign with fewer than 3 positives
has no verdict yet.

## What this skill touches

- **Reads** - campaign list, campaign settings and variants, campaign analytics (totals, reply
  categories, per-step funnel, per-sender stats), and any campaign, sender or per-variant file
  you supply. A supplied file is read only; it is never modified.
- **Writes** - a report of suggestions in your working directory. Nothing else, unless at Step 8
  you approve one action for one campaign, and the tool you send from provides that action:
  pausing that one campaign through its sequencer's pause tool (Step 8).
- **Never** - acts on a campaign without a yes for that campaign, acts on several campaigns in
  one approval, deletes or launches a campaign, edits sequence copy, changes senders or sending
  limits, sends an email, or runs an enrichment or routine. It never retries an action that failed.
- **Halts** - Step 4 `sample-review`, Step 8 `write-approval`.

## Step 0 - Check the platform works, and say where the work runs

Find out which campaign source is available, and tell the installer before anything else:

- **A sequencer connected to Deepline:** run `deepline preflight --json` and name the org, once.
  Then list campaigns with the sequencer's list tool, all free per `deepline tools describe`:
  `deepline tools execute instantly_list_campaigns --input '{}'`, or `smartlead_list_campaigns`,
  `lemlist_list_campaigns`, `heyreach_list_campaigns`. An auth or "not connected" error means that
  sequencer is not connected to this Deepline org and cannot be a source.
- **A connected sending tool:** check whether the agent has a connection that can read campaign
  stats. Use its read actions only.
- **An export file:** ask whether they have one.

If none is available, stop and say this skill needs one of the three, and what each takes: the
sequencer connected in Deepline, a connection to their sending tool, or an export from it. If the
Deepline check fails on sign-in or version, name the component and the one command that fixes it
(`deepline auth register --wait auto` or `deepline update`). Do not install, upgrade or fetch
anything.

Then tell the installer, in one sentence: this skill reads campaign data and does its arithmetic
in the agent; it runs no enrichment and no routine, and it changes nothing unless, at the end,
they approve a specific action for a specific campaign.

## Step 1 - Collect the thresholds before reading any result (interview; do not guess)

This order is the whole skill. Ask for the declared inputs now, and write the agreed thresholds
into the report header before Step 2 runs. If the installer asks to see the numbers first, say
why not: a threshold chosen after seeing the result is a justification, not a rule.

Collect, in this order:

1. Campaign source: a sequencer connected to Deepline, another connected sending tool, or an export file. If it is a file,
   ask whether its positive column is human-classified or an automatic label, whether it has a
   first send date, and whether a sender export exists. Campaigns in scope.
2. Market tier for each campaign in scope. Do not infer it from the campaign name.
3. Thresholds: theirs, or the author's tables, labelled borrowed.
4. Which reply categories count as positive. Show the category names that exist, then ask:
   Smartlead `smartlead_list_lead_categories`; Instantly's lead interest statuses (the values
   `instantly_update_lead_interest_status` accepts, per `deepline tools describe`); Lemlist's
   interested / not-interested marks. HeyReach has no reply category tool in Deepline; positives
   for a HeyReach source come from a file. Showing category names is
   not reading results; do not show counts yet.
5. Bounce guardrail, and the minimum age before a kill.
6. Whether they have per-variant results to supply, and the file.

## Step 2 - Decide what can be judged, and at which level

Four levels, each with its own source. Say which ones will run.

| Level | Source | Runs when |
|---|---|---|
| Sender guardrail | per-sender stats (`instantly_get_daily_account_analytics`, Lemlist stats filtered by `send_user`), or the sender export | Instantly or Lemlist source; file source only with a sender export |
| Campaign verdict | campaign totals plus positive reply categories, or the campaign export | always, provided positives can be counted |
| Step funnel | per-step sent and replied counts | Instantly source (`instantly_get_campaign_analytics_steps`); descriptive, no verdict |
| Variant verdict | the per-variant file, or Instantly step analytics | only when one of those is available |

The sequencer stats tools return sent, replied and bounced counts, not positives; positives come
from the reply categories agreed at Step 1. **None of them returns positives per variant**
(`lemlist_get_campaign_stats` takes an `ab_selected` filter, but returns replied, not positive). Do
not estimate variant results from totals, from steps, or from sender splits. Variant verdicts come
from the supplied file or not at all.

## Step 3 - Free triage before per-campaign reads

For a Deepline source, list campaigns (Step 0), filter to `status` active (or the installer's
filter), then pull lifetime totals. Instantly takes many campaigns in one free call:
`instantly_get_campaign_analytics` with `ids`. Smartlead, Lemlist and HeyReach are one free call per
campaign (`smartlead_get_campaign_analytics`, `lemlist_get_campaign_stats`,
`heyreach_get_campaign_stats`). The Instantly and Smartlead analytics outputs are raw provider
payloads with no declared schema: name the sent, replied and bounced field from the first response
before reading the rest. For a file source, read the campaign export; there is no tool call.

**If scope resolves to zero campaigns, stop.** Say how many campaigns the source held, which
filter was applied, and that there is nothing to judge. Do not write an empty report: an empty
verdict board reads like a clean bill of health. On a sequencer source, name the statuses you
filtered on, since an account can hold paused or draft campaigns and no active ones.

For each campaign in scope, compare lifetime `sent` against its tier's fair-chance window:

- Below the window: mark **too small to judge** now, without a per-campaign read, unless the
  lifetime replies are 3 or more (a possible early SCALE). Those still get a full read.
- At or above the window: queue for a full read at Step 5.

Do not loop per-campaign analytics over campaigns that cannot yet be judged. That is where rate
limits (exit 4) come from.

## Step 4 - One gate: the plan, the thresholds, and any write

Show the installer, in one message:

- the thresholds that will be applied, and which are borrowed
- the positive categories
- how many campaigns get a full read and how many are too small to judge
- whether variant verdicts will run
- that nothing will be changed: the run ends in a report of suggestions, and any action is
  offered afterwards, one campaign at a time

Wait for a yes. This is the `sample-review` halt.

## Step 5 - Read the numbers

For each queued campaign, read its analytics with no date range, so totals are cumulative since
launch. The verdict keys off the cumulative count.

From each result take:

- sent: `result.sent` on Lemlist, `result.data.sent` on HeyReach; on Instantly and Smartlead the
  field named from the first response at Step 3
- positives: the count of leads in the categories agreed at Step 1 (Smartlead
  `smartlead_get_analytics_lead_category_response`; Instantly leads by interest status via
  `instantly_list_leads`; Lemlist `lemlist_export_campaign_leads` filtered by state)
- bounces, and per-sender sent and bounces where the source has them (Step 2)
- per-step sent and replied counts from `instantly_get_campaign_analytics_steps`
- the first send date: the earliest day in `instantly_get_daily_campaign_analytics` with sends above
  zero; Lemlist's `createdAt` from `lemlist_list_campaigns` is a floor

If a source gives no first send date, the campaign's creation date is a safe floor: the first send
cannot be earlier. Report the days left as "at least N". If all of a campaign's sends fall inside
the minimum age, it is too soon regardless of when it was created.

If the reply categories cannot be read for a campaign, positives cannot be counted for it. Mark it
**unmeasured**, not zero. Zero positives and unknown positives lead to opposite verdicts.

For a connected sending tool, use its read actions only, and take the same fields. **Read every
page.** Sender lists and campaign lists are often paged (15 or 25 per page is common); follow
the pages to the end, and say how many were read. Judging senders from page 1 alone misses
most of them. For a file
source, take sent, positives, bounces and first send date from each campaign row, and per-sender
sent and bounces from the sender export if there is one.

**Check every supplied file before using it.** Numbers often arrive as text, with thousands
separators, percent signs, or blanks. Read "1,480" as 1480. A blank, "n/a" or "-" in the positives
column means **unmeasured**, never zero. A row whose sent value is blank, zero or not a number
is excluded and listed, except a clean zero on a live campaign, which means it has not started:
report it as **not started** rather than as a bad row. A negative number, or positives or bounces larger than sent, means the
row is wrong: exclude it and list it rather than judging it. If a required column is missing
entirely, stop and name it before judging anything.

If a variant file was supplied, read it now and check every row has sent, positives, launch date
and sender pool. A row missing any of them is excluded from variant verdicts and listed as such.
A test left with fewer than two complete variants is not judged; list it as incomplete.

## Step 6 - Verdicts, single-valued, first match wins

**Senders first.** A sender whose bounces divided by sent exceeds the guardrail is flagged
**fix deliverability**, regardless of copy. Report it per sender, since one bad inbox can sit
inside a healthy campaign. If the guardrail differs by sending type, apply the line for the
inbox's own type as the source reports it, not the type the campaign's name suggests. When a
campaign's name says one sending type and its inboxes are another, say so: it is either a
naming slip or a misconfigured pool, and either one makes platform comparisons unreliable.
Sender stats that are lifetime totals across campaigns, not per campaign, must be labelled as
such.

**Then each campaign.** Apply in this order; the first rule that matches is the verdict:

1. **Not started** - live, but 0 sends so far. Nothing to judge; say whether senders are attached.
2. **Unmeasured** - positives could not be counted.
3. **Fix deliverability first** - the campaign's overall bounce rate exceeds the guardrail. Copy
   verdicts on a campaign that is not landing are meaningless.
4. **Scale** - positive rate at or above the tier's SCALE line, with 3 or more positives. This can
   fire before the fair-chance window. For enterprise, a booked meeting the installer confirms
   also qualifies.
5. **Too soon to judge** - the first send was less than the minimum age ago. Replies to the most
   recent sends have not arrived yet, so no kill can fire, however bad the numbers look. Say how
   many days are left.
6. **Too small to judge** - below the fair-chance window with fewer than 3 positives.
7. **Kill, cold-dead** - 0 positives at or past the fair-chance window.
8. **Kill, chronic** - past the chronic sample size and still below the chronic floor. For
   enterprise, only if the installer confirms no meetings were booked; if they do not know, the
   verdict is **keep going** with that stated.
9. **Keep going** - everything else. This is the default.

If the first send date is unknown, rules 7 and 8 cannot fire: report **keep going, age unknown**
where a kill would otherwise have fired. If positives are provisional (automatic sentiment
only), rules 7 and 8 cannot fire either. Report
**keep going, provisional** and say why. A scale on provisional positives is reported as
**scale, provisional**: a person reads the tagged replies before any volume is added, since an
automatic label that over-counts would push budget into a campaign that has not earned it.

**Check the label against the replies.** When a campaign's total replies are far above its
positives (10 or more replies per positive, with 20 or more replies), say so beside the verdict.
Either the offer draws the wrong people or the automatic label is missing positives, and only a
person reading the replies can tell which. On provisional positives this is the first thing to
check before trusting any verdict on that campaign.

**A kill must survive its broken senders.** When sender stats exist and any sender on the
campaign is flagged, re-check a kill using only the sends from unflagged senders, and credit
every positive to them. If the kill no longer holds, the verdict is **fix deliverability first**:
the campaign may be failing because of an inbox, not the copy. Positives are not reported per
sender, so crediting them all to the healthy senders is the generous reading, and a kill that
survives it is safe to act on.

**Then each variant test**, only from the supplied file or Instantly step analytics. A winner is called only if all hold:

- every arm launched on the same day from the same sender pool
- at least 21 days since launch, because replies keep arriving for about three weeks
- every arm has at least 500 sends, and enough for the observed lift:

  | Loser's positive rate | Winner vs loser | Sends needed per arm |
  |---|---|---|
  | about 1% | 2x or more | 500 |
  | about 1% | 1.5x to 2x | 2,000 |
  | about 1% | 1.2x to 1.5x | 10,000 |
  | about 2% or higher | 2x or more | 500 (the floor) |
  | about 2% or higher | 1.5x to 2x | 1,000 |

  **Below a 1% loser rate, the table scales up.** Multiply the 1% row by (1% divided by the
  loser's rate): a 0.5% loser needs twice the sends, a 0.25% loser four times. The sends needed
  for a fixed lift grow as the baseline shrinks, and most cold email positive rates sit under 1%.
  This scaling is a derivation from the table, not a separately measured rule; say so when it
  is used. Compute it from the unrounded rate (1 positive on 740 sends is 0.135%, not 0.14%).
- the winning arm has 3 or more positives

A lift under 1.2x is below what the table can resolve at any practical volume. Report it as
**no difference detected** and say detecting a gap that small needs well over 10,000 sends per arm.

Otherwise the verdict is **not enough data yet**, with the sends still needed per arm. Staggered
launches or different sender pools make the test **not comparable**, not a win.

**The step funnel** gets no verdict. Report each step's share of the campaign's replies, and name
the step producing the most. A sequence where step 1 produces nearly all replies and later steps
produce almost none is worth knowing, not a reason to kill.

## Step 7 - Deliver

Write the report to the working directory as `kill-or-keep-<YYYY-MM-DD>.md` and show it. Lead with
fix-deliverability items, then kills, then scales, then everything else. Every verdict carries the
numbers it was decided on and the rule that fired. End with the coverage line: how many campaigns
were in scope, how many judged, how many too small or too soon, how many unmeasured and why.

The report is a list of suggestions. Say so at the top: nothing has been changed.

## Step 8 - Act, only if asked, one campaign at a time

Only offer this if the installer asks to act on the report, and only for actions the source tool
itself provides. With a file source there is nothing to act through: hand over the list for a
person to carry out.

- **A sequencer connected to Deepline:** the only action is pausing one campaign, with
  `instantly_pause_campaign`, `smartlead_update_campaign_status` (status `PAUSED`), `lemlist_pause_campaign` or
  `heyreach_pause_campaign`. Ending a variant test is only possible on EmailBison, with
  `emailbison_activate_or_deactivate_asequence_step_variant`; on the others a test winner is
  carried out by a person in the sequencer.
- **Another connected sending tool:** pausing a campaign, or ending a test, if that tool offers it.

For each action, stop and show: the campaign, the exact action, what it changes, and the verdict
and rule behind it. For a pause, also say that leads mid-sequence stop receiving steps until
someone resumes it. Run it only on an explicit yes for that campaign. This is the
`write-approval` halt. Never batch it. If the action fails, report the error and stop; do not
retry.

## Representative output

### Verdict board

Thresholds: author's defaults (borrowed). Positive = "Interested", "Meeting request". Bounce guardrail 5% (borrowed).

| Campaign | Tier | Sent | Positives | Rate | Verdict | Rule that fired |
|---|---|---|---|---|---|---|
| Northwind - ops leaders | Mid-market | 3,120 | 0 | 0 per 3,120 | Fix deliverability first | would be cold-dead, but one sender is flagged and the 2,080 healthy sends are under the 2,500 window |
| Adatum - CFOs | Mid-market | 8,000 | 2 | 1 per 4,000 | Kill, chronic | past the 7,500 chronic sample and below 1 per 3,500 |
| Contoso - founders | Small SMB | 1,480 | 4 | 1 per 370 | Scale | at or above 1 per 600 with 4 positives |
| Fabrikam - RevOps | Mid-market | 5,600 | 3 | 1 per 1,867 | Keep going | has positives, not yet past the 7,500 chronic sample |
| Litware - finance leaders | Mid-market | 4,800 | 42 | 1 per 114 | Scale | at or above 1 per 1,000 with 42 positives |
| Tailspin - IT directors | Enterprise | 1,900 | 1 | 1 per 1,900 | Too small to judge | below the 4,000 window with fewer than 3 positives |
| Blue Yonder - COOs | Mid-market | 3,000 | 0 | 0 per 3,000 | Too soon to judge | first send 9 days ago; kills wait 21 days, 12 days left |

### Sender guardrails

| Sender | Campaign | Sent | Bounces | Bounce rate | Flag |
|---|---|---|---|---|---|
| alex@northwind-mail.example | Northwind - ops leaders | 1,040 | 83 | 8.0% | Fix deliverability |
| sam@contoso-hq.example | Contoso - founders | 740 | 9 | 1.2% | none |

### Variant calls

| Campaign | Variants | Sends per arm | Positive rate | Days since launch | Verdict |
|---|---|---|---|---|---|
| Litware - finance leaders | Pain opener vs Proof opener | 2,400 / 2,400 | 1.25% / 0.50% | 28 | Pain opener wins: 2.5x lift, needs 1,000 per arm at a 0.5% loser rate (scaled), has 2,400; 30 positives |
| Contoso - founders | Short opener vs Long opener | 740 / 740 | 0.54% / 0.14% | 26 | Not enough data yet: 4 positives vs 1. At a 0.14% loser rate a 2x lift needs about 3,700 sends per arm (scaled) |
| Fabrikam - RevOps | Case study vs Question | 610 / 590 | 0.33% / 0.34% | 24 | No difference detected: under 1.2x apart |

### Step funnel

| Campaign | Step 1 | Step 2 | Step 3 | Most replies from |
|---|---|---|---|---|
| Fabrikam - RevOps | 61% | 28% | 11% | Step 1 |

### Coverage line

11 active campaigns in scope · 5 judged · 5 too small or too soon · 1 unmeasured (no reply categories returned) · variant verdicts for 3 of 4 tests (1 row missing a launch date).

## What this skill does not claim

- It does not know why a campaign failed. It says which ones to stop and which ones to feed.
  The diagnosis is a separate job.
- It does not measure spam complaints or domain authentication. The sequencer stats tools do
  not return them, so the deliverability check here is bounces only.
- Per-variant numbers come from `instantly_get_campaign_analytics_steps` (step-level rows;
  confirm the variant field on the first response). The other sequencers' stats tools report per
  campaign, so for them variant verdicts need the supplied file.
- It does not replace human classification of replies. On automatic sentiment alone it will not
  kill anything.
- The default thresholds are one agency's numbers from its own client work. They are a starting
  point, not a law of outbound.

## What good looks like

A good run has its thresholds written at the top of the report, with borrowed ones labelled,
before any result appears. Every verdict names the numbers and the rule that fired, so anyone can
check it by hand in under a minute. Kills are few, and each is either past its fair-chance window
with zero positives or past its chronic sample and still under the floor.

A thin run looks like a list of verdicts with no rule attached, kills on campaigns that have
produced positives, a variant "winner" on a few hundred sends, or zeros where the reply
categories were never returned. Unmeasured is a real answer here; a report with no unmeasured,
too-small or not-enough-data rows across a large workspace is more likely wrong than tidy.

## Rules

- Thresholds are fixed at Step 1, before any result is shown. Never adjust a threshold after
  seeing the numbers in the same run.
- One metric decides campaign and variant verdicts: positive replies per send. Opens, clicks and
  total replies never decide anything.
- Unknown is not zero. Missing reply categories make a campaign unmeasured.
- Never kill on provisional positives, and never kill a campaign younger than the minimum age
  or whose first send date is unknown. A scale on provisional positives is marked provisional.
- The report suggests. Nothing is changed without a per-campaign yes at Step 8.
- Never infer variant results from campaign totals, steps or senders.
- Never pause a campaign without a per-campaign yes, and never batch that approval.
- Never launch, resume, complete or delete a campaign, and never edit copy. Outside the one
  approved Step 8 pause, report the verdict; a person acts on it.
- Never infer a campaign's tier from its name.

## Worked example

The installer asks to judge all active campaigns. Step 0: `deepline preflight --json` returns org
"Acme Growth", and `instantly_list_campaigns` succeeds. Step 1: they pick the author's thresholds (labelled borrowed), mark Northwind and
Litware as mid-market and Contoso as small SMB, and choose "Interested" and "Meeting request" as
positive. They supply a variant file covering Contoso and Litware.

Step 3: `instantly_list_campaigns` filtered to active, then `instantly_get_campaign_analytics` with
all their `ids`, returns 11 campaigns. Six
are under their fair-chance window with fewer than 3 replies, so they are too small to judge
without further reads. Five are queued.

Step 4: they approve the plan. Step 5: Northwind's analytics return 3,120 sent and no leads in the
agreed positive interest statuses. `instantly_get_daily_account_analytics` shows one sender with 83
bounces on 1,040 sends.

Step 6: that sender is flagged fix deliverability at 8.0%. Northwind's overall bounce rate is
3.4%, under the guardrail, and 0 positives past the 2,500 window reads as kill, cold-dead. But
the kill has to survive its broken sender: without the flagged inbox, Northwind has 2,080 sends,
short of the window. The verdict is fix deliverability first, not kill. Contoso has 4 positives on 1,480 sends, 1 per 370, above the small SMB SCALE line
of 1 per 600: scale.

The variant file tempts a wrong call on Contoso. Short opener has 4 positives on 740 and Long
opener 1 on 740, a 4x lift. But the loser's rate is 0.14%, so the scaled table asks for about
3,700 sends per arm before a 2x-or-better lift can be trusted. Four against one is noise at this
volume: not enough data yet, and the test keeps running.

Litware is different. Pain opener has 30 positives on 2,400 and Proof opener 12 on 2,400, both
launched the same day from the same pool, 28 days ago. The loser's rate is 0.5%, so a 2x-or-better
lift needs 500 x (1% / 0.5%) = 1,000 sends per arm. Both arms have 2,400, the lift is 2.5x, and
the winner has 30 positives: Pain opener wins.

The Litware winner is handed over for a person to apply in Instantly, since no Deepline tool ends
a variant test. The installer then asks to act on Adatum's chronic kill; the skill stops and shows
the pause: one campaign, active, leads mid-sequence stop receiving steps. The installer says yes;
`deepline tools execute instantly_pause_campaign --input '{"id":"<campaign-id>"}'` runs once. Step 7 writes `kill-or-keep-2026-09-22.md`, leading
with the flagged sender and Northwind behind it, then the scales.
