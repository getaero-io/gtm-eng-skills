---
name: value-first-cold-email
description: |
  Write value-first B2B cold email for a prospect list, with every first line built on a why-now
  signal that was checked, not guessed. It looks up real signals through Deepline (a new role, hiring
  in a named department, a recent funding round, company news on a named topic), keeps only the
  ones that match the right company and fall inside a stated window, then writes each first touch
  with the R.E.P.L.Y. framework (Relevance, Empathy, Payoff, Low-friction ask, You-focused) so the
  reader gets something useful even if they never reply, plus a 4-touch follow-up stack per
  persona and signal. Use whenever someone asks: write cold emails for this prospect list,
  personalize outbound with real signals, find a reason to reach out to these accounts, write
  first lines from funding or hiring news, build an email sequence for this persona, or our reply
  rate is low, help fix these emails. Do NOT use it to build or source the prospect list, to find
  or verify email addresses, to score or tier accounts, to send email or enroll anyone in a
  sequence, or to write LinkedIn messages.
category: personalize-outbound
personas: [sales-development, founder]
mechanism: functions
touches: writes-own-output
keywords: [cold-email, job-change]
ported_from: clay-run/clay-skill-creator/skills/maja-voje/value-first-cold-email
---

# Value-first cold email (check the why-now, then give before you ask)

The insight: **most cold email fails because it takes.** It asks for attention, time and a meeting
and gives nothing back. Value-first email gives first: the reader gets something useful from the
email itself, whether or not they ever reply. The test is simple. If they read it and did nothing
else, did they still walk away with something worth 20 seconds? If deleting it costs them nothing,
it was a pitch.

Two things follow, and they are why this skill looks up signals before it writes a line. **If no
real why-now exists, there is usually no reason to send yet**, so the why-now is checked, not
assumed. And **an insight, stat or benchmark is never invented to fill a gap.** A modest true
observation beats an impressive invented one, and a first line built on a signal nobody checked is
exactly that kind of invention.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and if an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Prospect list** | a CSV, table or pasted list. Per row at minimum: first name, job title, company domain. A professional profile URL or a work email per person turns on the new-in-role check | no default - there is nothing to write for |
| **Campaign brief** | the minimum five answers in `references/campaign-brief.md`: the persona, the problem in the buyer's own words, one thing to give the reader for free in touch 1, one real proof point with a number, the why-now triggers that matter to this buyer | stop. Copy on a thin brief is confident guessing. If they insist on a draft now, write it and list every assumption made (persona, pain, proof, the give) |
| **Relationship** | cold, warm (1st-degree or known), or referred - for the whole list or per row | ask. Never assume warm |
| **Signal checks** | which of the four checks to run: new in role, hiring (and in which departments), funding round, company news (and on which topics) | no default - each check costs credits, and only this buyer's own triggers are worth paying for |
| **Signal window** | how many days old a signal can be and still count as a why-now | the author's default: 30 days, for all four checks. Offer it; if taken, say it is borrowed. Never leave the window unset, which silently means all time |
| **No-signal rule** | what happens to a prospect when every check ran and nothing passed: hold with no draft, draft on the relationship for warm and referred only, or draft on fit and flag it as having no why-now | no default - ask before the batch runs. The skill never chooses this for the installer |
| **Credit cap** | the most credits this run may spend | no default - asked at the Step 4 gate, and the run stops at it |
| **Sender and voice** | who sends, a writing sample or tone, words the brand always or never uses | the author's defaults: plain peer tone and the checks in `references/copy-checks.md`. Say they are borrowed. The installer's brand rules win where they conflict, and the conflict is said out loud |
| **Sequence shape** | the number of touches and the send days | the author's default: 4 touches on days 1, 4, 8 and 13. Say it is borrowed |
| **First-touch length** | a word range | the author's default: 50 to 90 words, shorter for busy executives. Say it is borrowed |
| **Drafts file** | a folder and file name for the drafts, and the import columns if their sequencer takes a CSV (read one header row they paste; do not ask them to recite it) | deliver in the conversation only, and write nothing to disk |

## What this skill touches

- **Reads** - the prospect list and campaign brief you supply, and the person and company signals it looks up through Deepline tools for those prospects.
- **Writes** - its own output only: touch-1 drafts, follow-up stacks and a prospect ledger, in the conversation and in one drafts file you name.
- **Never** - sends an email, enrolls anyone in a sequence, writes to a CRM or sequencer, or puts a signal, stat or benchmark into a draft that it did not check or that the brief did not supply.
- **Halts** - Step 4 spend-approval, Step 6 sample-review

## Step 0 - Check Deepline works, and say where the work runs

Say this first, before any command: *"This reads your list and brief and looks up signals through Deepline.
It writes only its own drafts. It never sends, enrolls anyone, or writes to your CRM."*

Then:

```
deepline preflight --json                 # name the org out loud, read the balance and say it
deepline tools describe <tool_id> --json  # for each of the four tools below: pricing and inputSchema
```

If `deepline` is missing: `npm install -g deepline && deepline auth register --wait auto`.

**Where the work runs decides what it costs.** The lookups run as Deepline tool calls and bill per
call. The matching, the signal checks, the bucketing and all of the writing run in this agent at
zero Deepline credits.

What `deepline tools describe` returned on 2026-09-30, never run. **The live read at this step wins
over this table, every time**, and no cost below is quoted to the installer as their price:

| Check | Deepline tool | Grain | Inputs | Declared cost per call |
|---|---|---|---|---|
| New in role | `crustdata_person_enrichment` | per person | `linkedinProfileUrl` or `businessEmail` | **calculated after execution** from returned profiles and options |
| Hiring | `predictleads_company_job_openings` | per company | `company_id_or_domain`, `categories`, `first_seen_at_from` | 0.56, fixed |
| Funding | `predictleads_company_financing_events` | per company | `company_id_or_domain`, `first_seen_at_from` | 0.56, fixed |
| News | `predictleads_company_news_events` | per company | `company_id_or_domain`, `categories`, `found_at_from`, `found_at_until` | 0.56, fixed |

- **Use these tool IDs exactly**, never a similar name. If `describe` errors for one, or the call
  returns a not-connected error, that check is unavailable: say which, mark its prospects
  `not-checked`, and never substitute a different tool without telling the installer.
- **Read `pricing.displayText`.** Where it says calculated after execution, the declared figure is
  not known in advance, and the gate says so.
- The new-in-role check needs a profile URL or an email. A name and a company are not enough.
- A `first_seen_at` or `found_at` date is when the provider saw the item, not necessarily when the
  event happened. Read the event's own date field where the payload has one (rule 2 below).

**If the platform check fails, report it and stop.** Name the component, the version required and
the one command that fixes it. Do not install, upgrade, clone or fetch anything to repair it.

**Do not start a step before the steps above it have their answers.** If a declared input is
missing, ask for it. Never assume a default and continue.

## Step 1 - Collect the brief and the list (interview; do not guess)

**If an answer sheet is present beside this skill, load it and ask only for what it does not
cover.** A partial sheet is normal; a value it is missing gets asked for on its own rather than
restarting the interview. **Say which values came from the sheet** before using them - a sheet
applied silently is a wrong field nobody catches. **If there is no sheet, say nothing about
sheets** - run the interview as though the feature did not exist.

1. **The brief.** Run `references/campaign-brief.md`, one block at a time. Capture the buyer's
   words verbatim. "We don't know yet" is a finding, not a failure. Do not write a line until the
   minimum five are answered, plus the relationship.
2. **The list.** Read the header row or one sample row. Show the mapping you found to the fields
   this skill needs (first name, job title, company domain, profile URL, work email, relationship)
   and ask only about what did not match.
3. **The checks.** Map each trigger in brief block 6 to one of the four checks. For hiring, get the
   departments; for news, get the topics. A trigger with no check (a conference, content they
   posted, a tech install, a regulation) is not looked up. It counts only if the installer supplies
   it as a column in the list, and then it is marked as supplied, not checked.
4. **The window.** Ask how old a signal can be and still count, offering 30 days as the author's
   default. Front-load it, because it changes what the checks return and so what gets paid for.
5. **The no-signal rule.** Ask what happens to a prospect when nothing passes: hold with no draft,
   draft on the relationship for warm and referred only, or draft on fit flagged as having no
   why-now. Offer the three; do not pick one.

## Step 2 - Map the stack before writing any copy

A campaign is a cadence, not one email. Map it first, so the cadence and the give per touch are
coherent before a single line exists. The author's default, which the installer may change:

| Touch | Day | Angle | Value | Ask |
|---|---|---|---|---|
| 1 | 1 | the checked signal + the core problem | an insight or observation about their situation | interest check |
| 2 | 4 | proof / case-study angle | a specific result or relevant example from the brief | soft question |
| 3 | 8 | a different pain or persona angle | an ungated resource (teardown, template, one-pager) | "Want me to send it?" |
| 4 | 13 | pattern interrupt / break-up | a parting useful thought | "Wrong person?" or "Should I close the loop?" |

**Personalize at the layer that scales.** Touch 1 is written per prospect and carries the signal
and the observation. Touches 2 to 4 are written once per persona and signal type, reusing the proof
and the offer. Every touch stands on its own, adds new value, and never says "just bumping this".

Name the give for touch 1 now, from the brief. If the brief has nothing to give, stop and say so:
an email with nothing to give is the second most common failure, after writing on guesses.

## Step 3 - Free checks before anything paid

All of this runs in this agent, at zero Deepline credits, and removes rows before anything bills.

1. **Normalize and dedupe.** Lowercase domains and strip protocol, `www` and path. Dedupe people
   on email or profile URL, else on name plus domain. Dedupe companies on domain.
2. **Persona match.** Judge each job title against the brief's personas. A title that matches no
   persona is `off-brief` and gets no spend. Judge the whole title, not a keyword inside it: a
   Chief of Staff to the CFO is not the CFO.
3. **Disqualifiers.** Apply the brief's disqualifiers to fields already in the list. A match is
   `off-brief`.
4. **Supplied signals.** A row whose list already carries a signal the installer supplied skips the
   paid checks and is `supplied-signal`.
5. **Reachability.** A free-mail or missing company domain cannot run a company check. A person
   with no profile URL and no email cannot run the new-in-role check. If no check can run for a
   prospect, it is `not-checked`.
6. **Count and price the ceiling.** People with an identifier, times the person check's declared
   cost, plus unique companies, times the sum of the company checks turned on. That is the most the
   run can spend, because checks stop early (Step 5).

## Step 4 - One gate: the batch, the ceiling, the cap, the ask

One message, then stop and wait:

- what Step 3 removed for free, by reason, with counts;
- **the batch**: 10 prospects spread across personas and checks, and its most-it-can-cost figure;
- **the full run**: its most-it-can-cost figure, arithmetic done, never left for the installer to
  multiply;
- if the new-in-role check is on: *"The new-in-role check is priced after it runs, so its real
  charge is not known in advance. I'll tell you what the batch actually cost."*
- that nothing is sent, enrolled or written anywhere but its own drafts;
- and the one question: *"What's the most you want this run to spend? I'll stop when I reach it,
  and I'll show you the 10 drafts before running the rest."*

## Step 5 - Look up signals, cheapest first, and stop at the first one that passes

**Order, per prospect:**

1. The new-in-role check, if it is on and the row has a profile URL or email.
2. The company checks, once per company, and only while at least one prospect at that company still
   has no passing signal. Run them in ascending declared cost as read at Step 0, and stop at the
   first signal that passes for that company.

**Run and read:**

```
deepline tools execute predictleads_company_job_openings \
  --input '{"company_id_or_domain":"acme.com","first_seen_at_from":"2026-08-31"}' --json
deepline plays run signals.play.ts --input '{"csv":"batch.csv"}' --debug   # more than ~20 rows
deepline runs get <run-id> --full --json                                   # billed cost per step
```

Direct `tools execute` is for the 10-prospect batch. For the full run, author a small play with one
`.withColumn` per check (per `recipes/deepline-plays.md` in the `deepline-gtm` skill), run it with
`--debug`, and export with `deepline runs export <run-id> --out signals.csv`.

**Completion status is not data.** A run can be `complete` and hold nothing. Gate on the values in
each item. For the batch, read the whole payload for every check and **record the exact path to
each field you used** - the company name or website echo, the role and its start date, the posting
title and its date, the round and its date, the news event and its date - in the ledger notes, so
the rest of the run reads the same keys. A field present but empty is a miss.

**A signal passes only if all five hold:**

1. **Right entity.** The payload's own company name or website matches the prospect's domain.
   Compare the registrable name without the TLD, and read the website field rather than the domain
   field. For the new-in-role check, the current role must be at the prospect's company; a role at
   another company means `unconfirmed`, not "changed jobs", because people hold two current roles.
2. **Dated inside the window.** An item with no date is not a match. A crawl or listing date is not
   an event date, and roundup or database pages are not events.
3. **An event, not a mention.** News must be the company doing something - on a topic the brief
   named - not an article that only names it. Measured on Clay's `Company News` function, not by this skill's author:
   a news lookup about one company's hiring returned a different company hiring its former
   employees, which is on-topic text that argues the opposite. For funding, a firm investing in
   someone else is not that firm's funding event.
4. **Relevant to the brief.** Hiring counts only in the departments named. New in role counts only
   for a title that matches a persona.
5. **One event, once.** The same event across several outlets is one signal.

**Budget.** After each run, add declared cost times items run - a miss bills too. Before a run that
would pass the cap, stop and report where the run got to. At the end, run `deepline billing balance` again
and report the balance movement beside the declared total, saying that other people spending in the
same org move the balance too.

**Verdicts, one per prospect, first match wins:**

1. `off-brief` - Step 3 removed it.
2. `supplied-signal` - the installer's own column carries the why-now; not checked.
3. `signal-verified` - one looked-up signal passed all five rules. Record the signal, one evidence
   sentence, the date and the source.
4. `identity-mismatch` - results came back, and they were about a different entity.
5. `not-checked` - no identifier, the check was unavailable, or the cap was reached.
6. `no-signal` - every check that could run ran, and nothing passed. The installer's no-signal rule
   decides what happens next.

## Step 6 - Write touch 1 for the batch, and show it

**Before applying any rule literally, ask: who is this person, how do they buy, and what is the
relationship?** Email for a low-price self-serve tool differs from a committee sale; a warm referral
plays by different rules than a cold list. The principles hold; length, formality and the ask bend.
Where the brief contradicts a default here, follow the brief and say why.

**Build every touch from five moves - R.E.P.L.Y.:**

- **Relevance** - why you, why now. Open with the checked signal, stated plainly, and nothing it
  does not say. No "Hope you're well", no "I came across your profile".
- **Empathy** - the pain this persona feels, in the buyer's words from brief block 3. One sharp
  sentence about their world beats a paragraph about yours.
- **Payoff** - give them something valuable, in the email. One of: an insight about their world, an
  observation about them, a real benchmark, an ungated resource, or a small piece of the work
  already done. It comes from the brief or from the checked evidence, never from invention. "I have
  some ideas to share" is a withheld pitch, not value.
- **Low-friction ask** - one easy yes, answerable in one line from a phone. A question, an opinion
  ask, an interest check, or an offer to send something. No calendar booking in touch 1 for cold.
- **You-focused** - count sentences about them against sentences about you. If "we / our / I built"
  outweighs "you / your", rewrite.

**Anatomy.** Subject: 2 to 5 words, lowercase is fine, reads like one human writing to another,
references the signal or the problem and never the product; write 2 or 3 variants. Line 1 is the
signal. Line 2 is the problem it creates. Line 3 is the give. Line 4 is the ask, as a question.
Sign-off is short and human. Plain text, no images, and ideally zero links in touch 1.

**Cold and warm differ.** Cold earns attention fast, leads with the signal and a real give, and
lowers the ask. Warm or referred drops the pitch posture, names the actual relationship, asks for
their take, and can carry a more direct ask. A warm contact run through a cold template wastes the
warmth.

**Self-edit every draft** against the checklist and the word, structure and opener passes in
`references/copy-checks.md`. Any hit is a rewrite, not a note. Do not narrate the checks; deliver
the fixed draft.

**Show the batch:** each draft first, then one rationale line (the signal, the pain, the value, the
ask) so it is easy to redline, then the 10 ledger rows and the batch spend against its estimate.
If the batch shows something nobody expected - identity mismatches on a large share, one check
returning nothing for every company - say it here, plainly. Then ask: *"Anything to change before I
run the rest?"* and stop.

## Step 7 - Run the rest, write the stacks, deliver

1. Apply the batch corrections, then run Steps 5 and 6 for the remaining prospects, inside the cap.
2. Apply the installer's no-signal rule to every `no-signal` prospect. A fit-only draft, where the
   rule allows one, is marked as having no why-now in its rationale line.
3. Write touches 2 to 4 once per persona and signal type, per the Step 2 map. Each adds new value
   and stands alone.
4. Deliver the prospect ledger, the touch-1 drafts, the follow-up stacks and the run summary. Write
   the drafts file if one was named. The ledger's verdict counts must add up to the list size;
   every held and removed prospect is listed with its reason.
5. Say that nothing was sent: the drafts go into their own sequencer after their own review.
6. Offer to save the answers, in words that explain themselves:

   > "Want me to save your answers to a file alongside this? It isn't part of the skill - it's a
   > short note of what you told me: the brief, the checks, the window, the no-signal rule, the cap,
   > the voice rules. You won't answer these again when you re-run this, and if you send it to a
   > teammate next to the skill, it asks them only what the file doesn't cover. It stays with you,
   > is never submitted or published, and holds no passwords or API keys."

## Representative output

Credit figures in this section and in the worked example are Clay's declared costs the author read
on 2026-09-13 (1 per person check, 2.5 hiring, 6.4 funding), kept to show the arithmetic. They are
not Deepline prices; substitute what Step 0's `describe` returns.

### Prospect ledger

| Prospect | Company | Persona | Verdict | Signal | Evidence | Signal date | Credits |
|---|---|---|---|---|---|---|---|
| Dana Reyes | northwind.example | Enablement lead | signal-verified | new in role | started as Head of Sales Enablement at Northwind | 2026-08-25 | 1 |
| Omar Haddad | contoso.example | Product marketing | signal-verified | hiring: sales | 3 account executive postings for a new EMEA team | 2026-08-28 | 3.5 |
| Priya Nair | fabrikam.example | L&D director | identity-mismatch | - | funding result was for fabrikam-homes.example, a different company | - | 9.9 |
| Leo Brandt | tailspin.example | Enablement lead | no-signal (cold, held) | - | no role change, sales hiring or round inside 30 days | - | 9.9 |

### Touch 1 draft

**To:** Omar Haddad, Contoso · **Subject:** new emea reps · *(variants: emea ramp · three new aes)*

> Omar, saw Contoso is hiring three AEs for a new EMEA team.
>
> New reps in a new region tend to learn the pitch from whatever deck they find first, and the
> positioning drifts inside a quarter.
>
> A pattern we see in teams at this stage: the ones who hold the line hand new reps a one-page
> message map with three buyer quotes per region, and cut the rest.
>
> Want me to send over the template?
>
> Sam

*Signal: 3 EMEA AE postings, checked, 2026-08-28. Pain: messaging drift, brief block 3. Value:
insight from brief block 4. Ask: offer to send a resource.*

### Follow-up stack: product marketing, hiring signal

| Touch | Day | Angle | Value | Ask |
|---|---|---|---|---|
| 2 | 4 | proof | how a comparable team cut new-rep ramp from 9 weeks to 5, from the brief | "Is ramp time on your list this half?" |
| 3 | 8 | a different pain: win-loss drift | the message-map template, attached as plain text | "Want me to send the filled example too?" |
| 4 | 13 | break-up | the one question new EMEA reps get wrong most | "Wrong person for this?" |

### Run summary

120 prospects · 14 off-brief · 61 signal-verified · 5 warm drafted without a why-now · 31 cold held
for no signal · 6 identity-mismatch · 3 not-checked (no company domain) · 356.9 credits declared
against a 600 cap · balance moved 362.3, and other people may have spent in this org.

## What this skill does not claim

- The four Deepline tools' IDs, inputs and declared prices were read with `deepline tools describe` on 2026-09-30 and never run, so the payload paths, the hit rates and how often a signal passes the five rules are unknown. Record the field paths from the batch (Step 5).
- Declared cost is not always the charge: the new-in-role check is priced after execution, so the spend figure is a declared total plus the billed amount from `deepline runs get --full --json`, beside a balance movement that can include other people's spend.
- The 30-day window, the 4-touch cadence on days 1, 4, 8 and 13, and the 50 to 90 word range are the author's working defaults from practice, not measured against reply rates.
- No reply rate or positive-reply rate is claimed for emails this skill writes.
- The copy checks catch listed words and patterns; passing them does not prove a reader will find the email specific or worth their time.
- Triggers outside the four checks - a conference, content they posted, a tech install, a regulation - are never looked up and count only when the installer supplies them, marked as not checked.

## What good looks like

Every touch-1 draft's first line traces to a ledger row whose evidence names a signal that matched
the right company, carries a date inside the window, and is relevant to the brief - or to a
supplied signal that says it was not checked. Every give traces to the brief or to that evidence.
The installer saw 10 drafts and the batch spend before the rest ran. The ledger's counts add up to
the list, and every held or removed prospect is visible with its reason.

A thin run looks different and is still a correct run: most prospects `no-signal`. That is a finding
about the triggers or the window, and the right response is to revisit them, not to write fit-only
emails that pretend to a why-now.

The common failures: a draft opening with "congrats on the raise" where the ledger shows no dated
round in the window; a benchmark in a draft that appears nowhere in the brief; identity mismatches
silently dropped so the counts no longer add up; and a touch 3 that says "just following up".

## Rules

- MUST check a signal for right entity, a date inside the window, an event rather than a mention,
  and relevance to the brief before a draft uses it; NEVER write a first line from an unchecked or
  undated signal.
- MUST take every insight, stat, benchmark and proof point from the brief or the checked evidence;
  NEVER invent one to make an email feel valuable.
- MUST run the free checks first, then one gate with the ceiling and the cap, then a 10-prospect
  batch the installer reviews before the rest runs.
- MUST stop at the credit cap and report declared spend beside the balance movement; NEVER quote
  the declared figure of a variable-priced check as its charge.
- MUST gate on payload values; NEVER treat a `complete` run as a found signal.
- MUST get the no-signal rule from the installer; NEVER decide on their behalf whether a prospect
  with no why-now gets a draft.
- MUST keep one persona, one pain, one give and one ask per email, with exactly one CTA.
- NEVER send, schedule, enroll, or write to a CRM or sequencer. The drafts are the deliverable.
- NEVER run a warm or referred contact through a cold template.
- NEVER substitute a different tool when a named one is unavailable without saying so; mark the check unavailable.

## Worked example

Asked: *"Write cold emails for these 126 leads. We sell a sales-enablement platform; personas are
enablement leads and product marketers; triggers are a new enablement leader, sales hiring, and a
fresh round."*

Brief collected (proof: a comparable team cut new-rep ramp from 9 weeks to 5; give: the message-map
pattern). Checks on: new in role, hiring in sales and marketing, funding. Window: the 30-day
default, stated as borrowed. No-signal rule, the installer's choice: hold cold prospects, draft warm
ones on the relationship. Mostly cold list, 5 warm rows.

Free checks: 6 duplicate rows removed, leaving 120 prospects at 64 companies. 14 titles matched
neither persona (`off-brief`). 3 prospects had a free-mail domain and no profile URL (`not-checked`).
That leaves 103 prospects at 55 companies, 88 with a profile URL.

Ceiling: 88 × 1 + 55 × (2.5 + 6.4) = 88 + 489.5 = **577.5 credits**, with the funding figure flagged
as variable. The installer set a cap of 600.

Batch of 10 prospects at 8 companies: 10 new-in-role runs found 3 passing signals, which covered
2 companies completely. Hiring ran on the other 6 companies (15 credits) and passed at 2. Funding
ran on the remaining 4 (25.6 credits) and passed at 1, returned a different company for 1, and found
nothing for 2. Declared batch total: 10 + 15 + 25.6 = **50.6 credits**. Verdicts: 6 signal-verified,
1 identity-mismatch, 3 no-signal. The installer rewrote the give in the brief because two drafts
read like a pitch.

Full run: 88 new-in-role runs (88), hiring on 41 companies (102.5), funding on 26 companies (166.4),
**356.9 credits declared**, balance moved 362.3 and the gap is reported, not explained away.
Verdicts across the 103 checked: 61 signal-verified (27 new in role, 22 hiring, 12 funding),
6 identity-mismatch, 36 no-signal. Under the installer's rule, the 5 warm no-signal prospects got a
draft built on the relationship and the 31 cold ones were held. Delivered: 66 touch-1 drafts,
8 follow-up stacks (2 personas × 3 signal types, plus a warm stack per persona), and a ledger of all
120.
