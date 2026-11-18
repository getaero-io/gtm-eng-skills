---
name: score-contacts-with-jev
description: |
  Build a contact lead-scoring play in Deepline that uses Jev, TypeSafe's decision model, to
  judge each person (their likely role in the purchase, their seniority, whether they are a
  prospect at all) and plain code for everything numeric, including the company's own fit tier.
  The agent starts from what it already knows about your buyers (memory, notes, persona docs in
  your folder), interviews you only for the gaps, and turns that into a rubric of rules and Jev
  questions: yes/no Nouls, categories and scales. It previews the rubric on ten of your real
  contacts, then publishes a Deepline play that takes a person's context from a CSV, a list of
  rows or any webhook and returns a 0 to 100 score, a tier, the reasons, and the answers worth a
  second look. It can carry in the account's tier from your account scoring, so a VP at a
  poor-fit company does not outrank a manager at your best one. Jev is called through Deepline's
  ai_evaluate tool and billed to your Deepline workspace: no Jev key to manage. A few cents per
  thousand contacts. Use whenever someone asks: score my contacts or leads, persona fit score,
  rank the people on my list, which of my contacts is the decision maker, lead scoring for people
  in Deepline, qualify contacts with Jev, or set up Jev or TypeSafe scoring for contacts. Do NOT
  use it to score companies (score-accounts-with-jev does that), to find or enrich people, to
  route or assign leads, to push scores into a CRM or sequencer, or to train a model on won and
  lost deals.
category: score-and-qualify
personas: [revops, sales-development]
mechanism: workflow
touches: writes-records
keywords: [lead-scoring]
ported_from: clay-run/clay-skill-creator/skills/shy-rahnama/score-contacts-with-jev
---

# Score contacts with Jev (Jev judges the person, code counts the rest)

**The insight: a contact score is two different kinds of fact, and only one of them is about the
person.** "Would this title own the budget?", "is this a recruiter?", "how senior is 'Head of Fleet
Ops'?" are judgments about the person, and titles are messy enough that only a model reads them
well. "Is their company an A?", "did they start this role in the last four months?", "how many
points is that?" are lookups and arithmetic. Ask a model for "a lead score from 0 to 100" and it
blends both into a number nobody can decompose, and quietly lets a VP at a poor-fit company outrank
a manager at your best account.

The evidence is Jev's own documentation. TypeSafe publishes what Jev 1.13 is bad at, and the top of
the list is numbers, counting and comparing dates; it reads literally; it degrades when the record
carries fields the question does not need. Its recommended pattern for scoring is to break the
judgment into atomic questions and **combine them with weights in code**. And Jev returns a
probability for every option, so a score can use how sure it was.

What follows is the whole design:

- **Rules** (account tier, time in role, lists) are worked out in the play's code. Free, exact.
  The account's tier from account scoring is one of them.
- **Questions** (Jev's Noul, Choice and Score) are sent in **one `ai_evaluate` call per contact**,
  with only the fields they read. About $0.042 per million input tokens at the gateway's list
  price, output free: a few cents per thousand contacts.
- **Points are expected values over Jev's probabilities.** A 30-point "decision maker" Jev is 60%
  sure of adds 18. An unsure answer moves the score less than a sure one, in either direction; it
  never flips a verdict outright.
- **Missing data never poses as a verdict.** A contact without a title is `not_scored`; one the data
  cannot judge is `insufficient_data`, not a D; above that bar, every criterion with no data earns
  nothing and is named. A recruiter comes back `disqualified`.
- **The preview is the play.** The ten-contact preview runs the identical scoring code the play
  embeds, so what the installer approves is what they get.

> **Measured, and what is not yet.** On Clay, calling Jev directly (2026-09-29), a VP of
> Operations at an A-tier account scored 96 A in the hosted workflow and the local preview alike,
> and a recruiter was disqualified. The Deepline play passes `deepline plays check` and every
> offline check; no `ai_evaluate` call or play run has been observed yet, so the first preview is
> also the first live test of the answer parsing. Details in `references/live-checks.md`.

> **This skill is not finished when the rubric is agreed.** It is finished when the play is
> published, one contact has gone through it and matched the local preview, and the installer has
> been shown how to call it. If you stop early, say which step you stopped at and the command that
> resumes it.

## How to talk to the installer

- **Every question is a choice they click**, asked with the host's question tool (`AskUserQuestion`
  in Claude Code), one decision at a time, likely answer first, free text only as "Other". Never a
  paragraph of questions.
- **Never ask what you already know or can look up.** Your memory, this conversation, and files in
  the working folder come first (Step 2). A file's columns are a command.
- **Before any question, apply the test: does the answer change the rubric or the build?** If not,
  do not ask it, and do not defer it to a later step either.
- **Run every command yourself**, in the background when it waits on the installer. The installer
  only does what needs a person: exporting a file, and deciding.
- Show names, never ids, in anything the installer reads.

## Declared inputs

**Nothing here ships with a value.** Where a default is offered it is named, and accepting it is
recorded as borrowed (`"origin": "default"`) and said at delivery.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Where contacts come from** | a CSV or JSON export of people (from a CRM, a sheet, a list build), or "another system" (webhook). Read, never typed | no default. It decides which fields exist, so which criteria are possible |
| **What they sell** | a line or two, **found in the agent's context first**; asked only if not | stop: no rubric can be written without it |
| **The buying roles** | who signs, who champions, who is consulted, described by function and title | stop at Step 2. Never invented |
| **Seniority that matters** | whether senior is better, or a level is the sweet spot | a 0-to-top seniority scale is offered, recorded as borrowed if accepted |
| **People who are never prospects** | recruiters, students, consultants, competitors' staff, or "none" | "none" is a real answer; ask, never assume |
| **The account's fit** | a column carrying the company's tier or score, usually from the account skill's scored export | the criterion is left out, and the card says a poor-fit company's VP can outscore a best-fit manager |
| **Signals worth points** | only those the data carries (new in role, recent job change) | left out |
| **Tier cut-offs** | what an A must reach | A≥70, B≥45, C≥25 offered, recorded as borrowed if accepted |
| **A Deepline workspace** | the CLI signed in (`deepline auth status`), with credits for `ai_evaluate` | stop at Step 0 |

**Not asked, ever:** column or field names (read and shown as a mapping to correct), which fields
the score writes (fixed), a callback URL (the caller's own), whether to preview (always), point
values for every option (proposed in the draft and corrected there), and any key (none is needed).

### The play's interface: prescribed by the rubric

Inputs are the rubric's `inputs`, one flat field each, plus `source_ref` (echoed back for joining).
A typical contact rubric reads `full_name` and `title` (required), `headline`, `company_name`,
`account_tier` and `started_role_on`. Output, every key always present:

| Key | |
|---|---|
| `lead_score` | 0 to 100 integer |
| `lead_tier` | the rubric's tiers (A, B, C, D by default), or the status when not `scored` |
| `score_status` | `scored` · `disqualified` · `insufficient_data` · `not_scored` · `failed`. Five, no sixth |
| `score_reasons` | what counted for the record "(+25)", what counted against it "(2 of 25)", and what had no data |
| `needs_review` | answers under the confidence floor, with Jev's split; `none` otherwise |
| `coverage_pct` | how much of the rubric the data let Jev and the rules judge |
| `criteria_json` | every criterion: answer, confidence, points, status |
| `rubric`, `jev_model`, `jev_input_tokens`, `error`, `source_ref`, `scored_at` | provenance |

## What this skill touches

- **Reads**: the agent's own context (memory, this conversation, files in the working folder) for
  what the installer sells and who buys it; a saved account rubric under
  `~/.local/state/score-accounts-with-jev/`, if one exists; the columns and up to ten (at most 50)
  records of the file the installer picks (Step 1, Step 4); the Deepline workspace name.
- **Writes**: a rubric, the confirmed column mapping, preview results, the rendered play file and
  build state under `~/.local/state/score-contacts-with-jev/<workspace>/`. In Deepline: one play
  "jev-lead-score-contacts-<rubric>", published with a webhook trigger (Step 5). The play returns
  scores; it writes them nowhere else. When the account tier is joined in from the account skill's
  export, the joined file is a new file in the working folder; the original is not edited.
- **Sends**: for each scored contact, the fields the rubric's questions read (typically job title
  and profile headline) to Jev through Deepline's `ai_evaluate` (the Vercel AI Gateway, then
  TypeSafe). Names, emails and phone numbers are not sent unless a question reads them, and a
  rubric should not need them.
- **Spends**: Deepline credits for `ai_evaluate`, billed from token usage; nothing for a record a
  rule disqualifies or that has nothing to ask.
- **Never**: asks for or stores a key; clears or blanks a field; overwrites a score when Jev failed;
  edits the installer's file; contacts anyone; writes to a CRM or a sequencer; deletes anything
  outside its own state folder and play.
- **Halts**: Step 1 `other`, Step 2 `other`, Step 3 `other`, Step 4 `sample-review`, Step 5
  `write-approval`, Step 5 `spend-approval`.
- **Vendor-specific**: Jev, from TypeSafe, reached through Deepline's `ai_evaluate`. Without a
  signed-in Deepline workspace there is nothing to call, so the skill stops at Step 0.

## Representative output

The people, companies and numbers are invented.

### The rubric card (Step 3, what the installer corrects)

What `rubric_tool.py check` prints for `scripts/rubric.example.json`, saved under the installer's
own name with the seniority scale and cut-offs accepted as defaults.

```
Rubric: Route-planning buyer fit (v1) — scores contacts, 0 to 100

Worked out in code (free, no Jev call):
  Account fit                from Account tier (account scoring): A → +30; B → +20; C → +8; anything
                             else → +0
  New in role                from Started current role: under 120 days ago → +10;
                             120–364 days ago → +5; 365+ days ago → +0

Asked of Jev (one request per contact, all questions together):
  Buying role                Choice on Job title, Profile headline or summary: decision_maker +30;
                             champion +25; influencer +10; not_involved +0;
                             not_enough_information +0
  Seniority                  Score (5 levels) on Job title: 0 to +15
  Not a prospect             Noul (yes/no) on Job title, Profile headline or summary: yes at
                             80%+ DISQUALIFIES

Most points possible: 85. Tiers: A ≥ 70, B ≥ 45, C ≥ 25, D ≥ 0.
Below 50% coverage (too little data to judge) a contact is 'insufficient_data', not a low tier.
Answers under 60% confidence are listed in needs_review.
Borrowed defaults you accepted rather than chose: Seniority, tier cut-offs.
Jev through Deepline (ai_evaluate): about 660 input tokens per contact, roughly $0.028 per 1,000
contacts at the gateway's list price. Deepline bills it from usage; the preview's real
charge shows in `deepline billing`.
```

### The preview (Step 4)

Scores and tiers are from a live run of the example rubric against Jev on Clay (2026-09-29); the
reasons are shortened (the tool writes "Buying role: likely decision maker (+30) | …"), and the
people are invented. A reason counts for the person as "(+30)" and against them as "(0 of 30)", so
a low score names what pulled it down.

| Contact | Score | Tier | Why |
|---|---|---|---|
| Dana Ruiz, VP Operations, Northwind Supply | 96 | A | at an A-tier account (+30) · likely decision maker (+30) · Vice president (+11) · started this role in the last 4 months (+10) |
| Sam Okafor, Fleet Manager, Northwind Supply | 69 | B | at an A-tier account (+30) · likely champion (+25) · against: Manager or team lead (4 of 15), in this role over a year (0 of 10) |
| Priya Shah, Head of Fleet Ops, Adventure Works | 69 | B | likely champion (+26) · at a B-tier account (+20) · Director or head of a function (+8) |
| Lee Park, VP Marketing, Tailspin Toys | 13 | D | Vice president (+11) · against: at a low-fit or unscored account (0 of 30), not involved in this purchase (0 of 30) |
| Jo Brandt, Talent Partner, Contoso | 25 | disqualified | Disqualified: not a prospect (recruiter, student or outsider) |
| Ari Moss (no title on record) | 0 | not_scored | Not scored: missing title |

Lee Park is senior and still a D: the title says marketing and the company is a poor fit, which is
the case a single "fit score" column gets wrong.

### The delivery card and how to call it

````
Contact scoring is live: play "jev-lead-score-contacts-route-planning-buyer-fit" (published)

  Rubric       Route-planning buyer fit v2 · 2 rules, 3 Jev questions · tiers A/B/C/D (cut-offs borrowed)
  Jev          ai_evaluate, typesafe-ai/jev · billed to workspace Northwind GTM
  Account fit  read from each contact's "Account tier" column (your account scoring's lead_tier)
  Smoke test   Dana Ruiz: local 96 A · Deepline 96 A · answers match ✓
  Preview      10 contacts: A 2, B 3, C 1, D 2, disqualified 1, not_scored 1

Score a file (columns as in the preview; names need not match the inputs):
deepline plays run jev-lead-score-contacts-route-planning-buyer-fit --input '{"csv":"ops-leaders.csv"}'
deepline runs export <run-id> --dataset result.records --out ops-leaders-scored.csv

From anywhere else:
curl -X POST 'https://code.deepline.com/api/v2/webhooks/inbound/…' -H 'Content-Type: application/json' \
  -d '{"full_name":"Dana Ruiz","title":"VP Operations","company_name":"Northwind Supply",
       "account_tier":"A","started_role_on":"2026-07-01","source_ref":"row-2210"}'
````

## Files in this skill

| File | What it is for |
|---|---|
| `scripts/jev_lib.py` | the rubric check, the scoring code the play embeds (`CORE`, JavaScript), the play renderer, state paths, the `deepline` wrapper |
| `scripts/rubric_tool.py` | check, save (with version bumps), show and export a rubric |
| `scripts/rubric.example.json` | a complete, invented contact rubric to start from |
| `scripts/score_local.py` | the preview: score up to 50 real contacts on this machine with the exact play code |
| `scripts/build_scorer.py` | render the play, `deepline plays check` it, publish it |
| `scripts/smoke_test.py` | one contact through the published play, compared with the local score |
| `scripts/test_offline.py` | the scoring code, the arithmetic and the renderer, with no Deepline call |
| `references/jev-api.md` | Jev through `ai_evaluate`: request and answer shapes, price, limits, what it is bad at |
| `references/rubric-format.md` | the rubric file, how a score is worked out, writing questions Jev answers well |
| `references/play-shape.md` | the play step by step, how it is called, and the traps it avoids |
| `references/live-checks.md` | what was run live, on Deepline and earlier on Clay, and what was not |

Run every script with `python3 -B`. They need the standard library, `node` (18+) and the
`deepline` CLI.

**Do not start a step before the steps above it have their answers.** If a declared input is
missing, ask for it; never assume one and continue.

## Step 0: Say what this builds, what it costs, and check the platform

Three short paragraphs:

1. **What it builds.** A scoring rubric for contacts, previewed on their own records, then a
   Deepline play that scores any person sent to it, or a whole file, and says why.
2. **Where the work runs and what it costs.** Lookups and arithmetic are worked out in the play's
   code, free. Judgments about the person go to Jev through Deepline's `ai_evaluate`, one call per
   contact: about $0.04 per million input tokens at list price, a few cents per thousand contacts,
   billed to their Deepline workspace from usage.
3. **What leaves their systems.** The fields the questions read, typically title and headline, go
   to Jev (through Deepline and the Vercel AI Gateway to TypeSafe). No key is involved.

Then, without asking: `deepline auth status --json` (say the workspace name back),
`node --version`, `python3 -B scripts/test_offline.py` and `python3 -B scripts/rubric_tool.py
list`. A saved rubric means those steps are offered as done. If the platform check fails, say which
part and the one command that fixes it (`npm install -g deepline && deepline auth register --wait
auto`), and stop.

## Step 1: Where the contacts come from

Ask **"Where will the contacts you want scored come from?"** (A CSV or export file / A CRM list /
Another system, by webhook). Then look, never ask:

- **A file:** find candidate files in the working folder by name and extension and ask **"Which
  file?"** with up to four names. Read its header (`score_local.py --file <f> --show-map` prints
  it as a mapping).
- **A CRM list:** have it exported to CSV, or pull it with the CRM's Deepline tools (`deepline
  tools search "<crm> list contacts" --json`, then `describe` the one you use), into a CSV in the
  working folder. Then as a file.
- **Webhook:** no fields to read; the rubric's inputs will be the interface.

Note whether a column carries the **company's tier or score**. If it does not, but the account
skill has a scored export (`lead_tier` per company), offer to join it on: match each person to their
company by domain (or exact company name when there is no domain), add an `account_tier` column, and
write the result as a new file beside the original. Say how many people found no company in the
export: they score without account fit. The fields that exist decide which criteria are possible;
carry the list into Step 2.

## Step 2: Build the buyer brief from what you already know, then ask only the gaps

**Before asking anything, write the brief from your own context.** Look in: your memory files and
the project instructions loaded in this session; this conversation; a saved account rubric (the
account skill keeps them under `~/.local/state/score-accounts-with-jev/<workspace id>/rubrics/`, and
a rubric's `about` says what they sell); and documents in the working folder a person would keep
about who buys (a persona doc, an ICP or positioning doc, a strategy or "anchor context" document,
win notes). Read, do not guess.

The brief has six parts:

| Part | Becomes |
|---|---|
| What they sell | the frame for every question's wording |
| Buying roles: who signs, who champions, who is consulted, who is irrelevant | a Choice with described options |
| Seniority that matters | a Score over the title, or a Choice when a middle level is the sweet spot |
| People who are never prospects | a disqualifying Noul (and a match rule for known domains) |
| The account's fit | a lookup rule over the account tier column |
| Signals worth points | rules (time in role) or Nouls (the headline says they are hiring for a team) |

Show the brief as a short table: each part, what you found, and **where it came from**, or
*missing*. Then ask only for the missing parts that change the rubric, one click at a time, with
options drawn from what you found. For example **"Who usually signs off on buying this?"** (options
from their persona doc, plus Other) and **"Anyone who should never count as a prospect?"**
(Recruiters and students / Consultants and agencies / Competitors' staff / None). If no account tier
exists in their data, say plainly what that costs (a senior person at a poor-fit company scores
high) and ask **"Score people without their company's fit, or set up account scoring first?"**
(Without it for now / Account scoring first). If the brief is complete from context, ask one
question instead: **"I built this from <sources>. Anything wrong or missing?"**

Never invent a buying role, a disqualifier or a signal the installer did not state or a source did
not say. If what they sell cannot be found or answered, stop.

## Step 3: Draft the rubric, and have it corrected

Write the rubric JSON following `references/rubric-format.md`, from the brief and the fields Step 1
found:

- **The account's fit is a `lookup` rule**, tier letter to points, never a question.
- **Time in role is a `days_since` rule.** Never ask Jev about a date.
- **Every judgment about the person is a Jev question** reading the title (and headline when there
  is one), stating one condition, describing every option. Three to eight questions is typical.
- A Choice gets `not_enough_information` automatically. Level 0 of a Score is the most junior.
- Keep names, emails and phone numbers out of every question's `reads`: they add nothing to a
  judgment and send personal data for no reason.
- Mark anything accepted rather than chosen with `"origin": "default"`; put what they sell and the
  sources in `about`.

Run `python3 -B scripts/rubric_tool.py check draft.json` and show the card. Ask **"Does this match
how you would judge a contact?"** (Looks right / Change the points or cut-offs / Change a criterion
/ Other). Edit and re-check until it does, then `rubric_tool.py save draft.json`.

## Step 4: Preview on ten real contacts

Run `python3 -B scripts/score_local.py --file <file>` with **`--show-map` first**, show the
mapping, take corrections as `--map key=Column`, then run it for real and show the table. The
confirmed mapping is saved and baked into the play at build time. Then read the real charge with
`deepline billing` and use it in Step 5's price.

If every record comes back `failed` with "Jev returned no answers", the `ai_evaluate` answer shape
differs from the one this skill reads: run one `deepline tools execute ai_evaluate --input
@body.json --json`, compare with `references/jev-api.md`, and fix `_answer_item` in `CORE` before
going on.

**Stop here.** Ask **"Do these scores look right for people you know?"** (Yes, build it / Some are
off: adjust the rubric / Try ten different contacts). "Some are off" goes back to Step 3 with the
specific people in hand: which criterion moved them, and whether the fix is points, an option's
description (titles are where literal reading bites: say "Head of Fleet counts as a champion" in the
option), or a missing criterion. Rescore after every change.

## Step 5: Build and publish, after one gate

**Build it; never score in the conversation instead.** It has to be a play because it runs
unattended: every file sent to it, every POST from another system, long after this session ends.

Run `python3 -B scripts/build_scorer.py --plan`. It renders the play from the saved rubric and
mapping and runs `deepline plays check` on it (free); a check failure stops here with the reason.
The play's steps and the traps they avoid are in `references/play-shape.md`. Then one message with
everything, and the word *write* in it:

> This **writes** to your Deepline workspace: one play, "jev-lead-score-contacts-route-planning-
> buyer-fit", published, with a webhook URL that scores any person POSTed to it. Each contact
> scored costs about $0.00003 in Deepline credits for Jev (from the preview's charge). Nothing is
> scored until you call it [or: scoring the 3,400 people in ops-leaders.csv now is a separate run,
> about $0.10].

Ask **"Go ahead?"** (Yes, publish it / Publish it, but don't score the file yet / Change something
first). On yes:

```bash
python3 -B scripts/build_scorer.py
```

It publishes the exact bytes the check passed (`--expected-artifact`) and records the webhook URL.
If no URL comes back in the publish output, `deepline plays get <play> --json` shows it under
`triggerBindings[].endpointUrl`.

If they approved scoring the file now: `deepline plays run <play> --input '{"csv":"<file>"}'`,
then `deepline runs export <run-id> --dataset result.records --out <file>-scored.csv`.

## Step 6: Prove it with one contact

`python3 -B scripts/smoke_test.py --from-preview` sends the first preview contact through the
published play (the live revision) and scores it locally again. **Match** proves the published
rubric, the baked-in mapping and the Jev route. If the run fails, the script names the run id;
`deepline runs get <run-id> --json` shows the step and the error. Do not call the play live until
it matches.

## Step 7: Deliver, ending with how to call it

The delivery card from "Representative output", with the real numbers, then **end with how to call
it**, all three ways:

1. **A file:** `deepline plays run <play> --input '{"csv":"<file>"}'` and `deepline runs export
   <run-id> --dataset result.records --out <scored.csv>`. If the account skill also scores the
   companies, join its `lead_tier` on as `account_tier` first so the account's verdict flows into
   the person's.
2. **Rows from a script or another play:** `{"rows": [...]}` keyed by the rubric's inputs.
3. **From anything that can POST:** the webhook URL and a `curl` with a real-shaped body. The
   response carries a `run_id`; the score is in that run.

Say what was borrowed rather than chosen, and what was not tested. When asked later: **"change the
rubric"** is Steps 3, 4, 5 and 6; **"score the companies too"** is the sibling account skill.

## What this skill does not claim

- The rubric is the installer's judgment written down, not a model trained on won and lost deals.
  Nothing here measures whether A-tier contacts reply or convert more.
- Jev reads titles literally. Unusual titles ("Chief Moving Officer") land where the option
  descriptions send them; the preview is the only accuracy check, and it is by eye.
- Without an account-fit input, company quality does not enter the score at all.
- Jev's probabilities move slightly between calls, so a re-run can differ by a point or two and a
  tier can flip at a cut-off.
- `typesafe-ai/jev` is not version-pinned on this route; a TypeSafe release can shift answers.
  `jev_model` on each result says which model answered.
- The confidence behind `needs_review` is this skill's own (top probability minus the runner-up),
  because the evaluation API returns no confidence field.
- The Deepline route has not been run live yet (`references/live-checks.md`); the Clay-era results
  quoted here were measured calling Jev directly.
- A profile written to argue for its own classification can move Jev's answer; TypeSafe says so.
- `insufficient_data` means the record lacked fields, not that the person is a poor lead. The skill
  does not enrich.

## What good looks like

A good run ends with **one contact scored identically by the published play and locally**, a play
that `deepline plays check` calls valid, and a preview the installer read and agreed with, in which
a senior person at a poor-fit company scores below a hands-on champion at a best-fit one. Every
score names the criteria that moved it with their points; a person with no title is `not_scored`; a
recruiter is `disqualified`.

A thin run looks finished and is not:
- The account's fit is missing from the rubric and nobody said so.
- A question asks Jev a date or a number ("in the role under six months?"). That is a rule.
- Every contact lands in one tier; the points were never checked against the preview.
- The play is published but the smoke test never ran.
- A question's `reads` includes email or phone, sending personal data for nothing.
- The rendered play was edited by hand, so it no longer matches the preview.

## Rules

- **Jev judges the person; code counts the rest.** Account tier, dates and numbers are rules.
- **Context before questions.** Memory, conversation, a saved account rubric and folder docs first;
  ask only gaps that change the rubric.
- **Never invent** a buying role, disqualifier, signal or cut-off. Accepted proposals are marked
  borrowed.
- **Send Jev the least personal data that decides the question.** Titles and headlines, not contact
  details.
- **Always preview on real contacts before building**, and rescore after every rubric change.
- **Missing data is `insufficient_data` or `not_scored`, never a low tier.** Five statuses.
- **Never publish a play `deepline plays check` did not pass**, and never edit the rendered play.
- **One write gate (Step 5).** Say it is a write, name the play, price it from the preview's real
  charge.
- **Never blank a field; never overwrite a score because Jev failed.**
- **Do not call it live until the smoke test matches.**

## Worked example

The workspace, people and company are invented; the steps and outputs are the real shapes.

**Ask:** "We scored our accounts with Jev last week. Now I want the people in our Ops leaders export
scored too."

**Step 0.** Workspace *Northwind GTM*. `test_offline.py` passes. No contact rubric yet; an account
rubric is saved.

**Step 1.** A file, named in the ask: *ops-leaders.csv*, with Name, Job title, Headline, Company,
Domain and Started role. No tier column, but the account skill's scored export is in the folder:
joined on domain into *ops-leaders-with-tier.csv*; 3,310 of 3,400 people matched a company.

**Step 2.** The brief, from context: *what they sell* from the saved account rubric's `about`;
*buying roles* from `personas.md` in the folder (the COO signs, fleet and dispatch managers
champion). Missing: who is never a prospect. "Anyone who should never count as a prospect?" →
Recruiters and students. Seniority scale and cut-offs: the defaults, accepted, so borrowed.

**Step 3.** Two rules, three questions (the card above). "Does this match how you would judge a
contact?" → Looks right. Saved as v1.

**Step 4.** `--show-map`: `account_tier` ← *account_tier*, `started_role_on` ← *Started role*, all
matched. Ten contacts scored; `deepline billing` shows the charge. "Some are off": a *Head of Fleet
Ops* came out `influencer`. The champion option's description gains "Head of Fleet"; rescored, now
champion. Saved as v2, the version the delivery card shows.

**Step 5.** `--plan`: the play renders and `plays check` says valid. The gate names the play,
$0.00003 a contact, and the 3,400 people in the file as a separate run of about $0.10. "Publish it,
but don't score the file yet." Published; the webhook URL is recorded.

**Step 6.** Smoke test: Dana Ruiz, local 96 A, Deepline 96 A, answers match.

**Step 7.** The card, then: run the play on *ops-leaders-with-tier.csv* and export when ready, or
POST the curl shown. Borrowed: the seniority scale and the cut-offs.
