---
name: score-accounts-with-jev
description: |
  Build an account lead-scoring play in Deepline that uses Jev, TypeSafe's decision model, for
  the judgment calls and plain code for everything numeric. The agent starts from what it
  already knows about your business (memory, notes, docs in your folder), interviews you only
  for the gaps, and turns that into a rubric of rules and Jev questions: yes/no Nouls,
  categories and scales. It previews the rubric on ten of your real accounts, then publishes a
  Deepline play that takes a company's context from a CSV, a list of rows or any webhook and
  returns a 0 to 100 score, a tier, the reasons, and the answers worth a second look. Jev is
  called through Deepline's ai_evaluate tool and billed to your Deepline workspace: no Jev key to
  manage. A few cents per thousand accounts. Use whenever someone asks: score my accounts, build
  an account or ICP fit score, lead scoring for companies in Deepline, tier my target accounts,
  qualify companies with Jev, replace an AI column that grades accounts, or set up Jev or
  TypeSafe scoring. Do NOT use it to score individual people (score-contacts-with-jev does that),
  to find or enrich companies, to route or assign leads, to push scores into a CRM, or to train a
  model on won and lost deals.
category: score-and-qualify
personas: [revops, gtm-engineer]
mechanism: workflow
touches: writes-records
keywords: [lead-scoring]
ported_from: clay-run/clay-skill-creator/skills/shy-rahnama/score-accounts-with-jev
---

# Score accounts with Jev (Jev decides, code counts)

**The insight: a lead score is a handful of judgments plus arithmetic, and the arithmetic must never
be asked of the model.** "Is this a distributor?", "do they run their own fleet?", "how strong is
this growth signal?" are judgments. "Are they between 200 and 2,000 staff?", "is the HQ in North
America?", "how many points is that, and is it an A?" are arithmetic. An AI column that is asked for
"a fit score from 0 to 100" mixes the two and returns a number nobody can decompose, audit or
reproduce.

The evidence is Jev's own documentation. TypeSafe publishes a list of what Jev 1.13 is bad at, and
the top of it is numbers, counting and comparing dates; it reads instructions literally; it degrades
when the record is padded with fields the question does not need. Its recommended pattern for
scoring is to break the judgment into atomic questions and **combine them with weights in code**.
And what Jev returns is not a label but a probability for every option, so a score can use how sure
it was.

What follows is the whole design:

- **Rules** (numbers, dates, lists) are worked out in the play's code. Free, exact.
- **Questions** (Jev's Noul, Choice and Score) are sent in **one `ai_evaluate` call per account**,
  with only the fields they read. About $0.042 per million input tokens at the gateway's list
  price, output free: a few cents per thousand accounts.
- **Points are expected values over Jev's probabilities.** A 25-point category Jev is 60% sure of
  adds 15. An unsure answer moves the score less than a sure one, in either direction; it never
  flips a verdict outright.
- **Missing data never poses as a verdict.** An account the data cannot judge comes back
  `insufficient_data`, not a D; above that bar, every criterion it had no data for earns nothing and
  is named in the reasons. A competitor comes back `disqualified` before any Jev call.
- **The preview is the play.** The ten-account preview runs the identical scoring code the play
  embeds, so what the installer approves is what they get.

> **Measured, and what is not yet.** On Clay, calling Jev directly (2026-09-29), a distributor
> scored 98 A in the hosted workflow and the local preview alike, and a competitor was
> disqualified without a Jev call. The Deepline play passes `deepline plays check` and every
> offline check; no `ai_evaluate` call or play run has been observed yet, so the first preview is
> also the first live test of the answer parsing. Details in `references/live-checks.md`.

> **This skill is not finished when the rubric is agreed.** It is finished when the play is
> published, one account has gone through it and matched the local preview, and the installer has
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
| **Where accounts come from** | a CSV or JSON export (from a CRM, a sheet, a list build), or "another system" (webhook). Read, never typed | no default. It decides which fields exist, so which criteria are possible |
| **What they sell and to whom** | a line or two, **found in the agent's context first**; asked only if not | stop: no rubric can be written without it |
| **Best-fit, OK and poor-fit kinds of company** | categories with a sentence each | stop at Step 2. Never invented |
| **Size, region and other numeric cuts** | only for fields the source actually carries | the criterion is left out, and the card says so |
| **Disqualifiers** | competitors, partners, excluded segments, or "none" | "none" is a real answer; ask, never assume |
| **Signals worth points** | only those the data carries (hiring, funding, news, tech) | left out |
| **Tier cut-offs** | what an A must reach | A≥70, B≥45, C≥25 offered, recorded as borrowed if accepted |
| **A Deepline workspace** | the CLI signed in (`deepline auth status`), with credits for `ai_evaluate` | stop at Step 0 |

**Not asked, ever:** column or field names (read and shown as a mapping to correct), which fields
the score writes (fixed), a callback URL (the caller's own), whether to preview (always), point
values for every option (proposed in the draft and corrected there), and any key (none is needed).

### The play's interface: prescribed by the rubric

Inputs are the rubric's `inputs`, one flat field each, plus `source_ref` (echoed back for joining).
A typical account rubric reads `company_name` (required), `domain`, `description`, `industry`,
`employee_count`, `country` and one free-text signals field. Output, every key always present:

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
  what the installer sells and to whom; the columns and up to ten (at most 50) records of the file
  the installer picks (Step 1, Step 4); the Deepline workspace name.
- **Writes**: a rubric, the confirmed column mapping, preview results, the rendered play file and
  build state under `~/.local/state/score-accounts-with-jev/<workspace>/`. In Deepline: one play
  "jev-lead-score-accounts-<rubric>", published with a webhook trigger (Step 5). The play returns
  scores; it writes them nowhere else. Scoring a file produces a run whose export is a CSV the
  installer keeps.
- **Sends**: for each scored account, the fields the rubric's questions read (typically name,
  description, industry, a signals field) to Jev through Deepline's `ai_evaluate` (the Vercel AI
  Gateway, then TypeSafe). Nothing else leaves the installer's systems.
- **Spends**: Deepline credits for `ai_evaluate`, billed from token usage; nothing for a record a
  rule disqualifies or that has nothing to ask.
- **Never**: asks for or stores a key; clears or blanks a field; overwrites a score when Jev failed;
  edits the installer's file; writes to a CRM or a sequencer; deletes anything outside its own
  state folder and play.
- **Halts**: Step 1 `other`, Step 2 `other`, Step 3 `other`, Step 4 `sample-review`, Step 5
  `write-approval`, Step 5 `spend-approval`.
- **Vendor-specific**: Jev, from TypeSafe, reached through Deepline's `ai_evaluate`. Without a
  signed-in Deepline workspace there is nothing to call, so the skill stops at Step 0.

## Representative output

The companies, domains and numbers are invented.

### The rubric card (Step 3, what the installer corrects)

What `rubric_tool.py check` prints for `scripts/rubric.example.json`, saved under the installer's
own name with the cut-offs accepted as defaults.

```
Rubric: Route-planning fit (v1) — scores accounts, 0 to 100

Worked out in code (free, no Jev call):
  Company size               from Employees: under 50 → +0; 50–199 → +10; 200–1,999 → +15;
                             2,000+ → +5
  Region                     from HQ country: is one of united states, us, usa, canada → +10,
                             otherwise +0
  Competitor                 from Website domain: is one of routewise.example,
                             fleetplan.example → DISQUALIFIES

Asked of Jev (one request per account, all questions together):
  Runs its own fleet         Noul (yes/no) on What the company does, Industry: yes +25; no +0
  Segment                    Choice on What the company does, Industry: distributor +25;
                             field_service +15; retailer +8; logistics_provider +0 (disqualifies);
                             other +0; not_enough_information +0
  Growth signal              Score (4 levels) on Recent news or signals: 0 to +15

Most points possible: 90. Tiers: A ≥ 70, B ≥ 45, C ≥ 25, D ≥ 0.
Below 50% coverage (too little data to judge) an account is 'insufficient_data', not a low tier.
Answers under 60% confidence are listed in needs_review.
Borrowed defaults you accepted rather than chose: tier cut-offs.
Jev through Deepline (ai_evaluate): about 799 input tokens per account, roughly $0.034 per 1,000
accounts at the gateway's list price. Deepline bills it from usage; the preview's real
charge shows in `deepline billing`.
```

### The preview (Step 4)

Scores, tiers and review notes are from a live run of the example rubric against Jev on Clay
(2026-09-29); the reasons are shortened (the tool writes "Segment: a distributor (+25) | …"), and
the companies are invented. A reason counts for the record as "(+25)" and against it as "(2 of
25)", so a low score names what pulled it down.

| Account | Score | Tier | Why |
|---|---|---|---|
| Northwind Supply | 98 | A | a distributor (+25) · runs its own delivery fleet (+24) · 200–1,999 staff (+15) · explicit fleet expansion (+15) |
| Adventure Works HVAC | 58 | B | a field service business (+15) · 50–199 staff (+10) · in North America (+10) · against: no own fleet (8 of 25); **review: Runs its own fleet: unsure (32% yes)** |
| Contoso Home | 39 | C | 200–1,999 staff (+15) · in North America (+10) · against: no own fleet (2 of 25), a retailer (8 of 25) |
| Fabrikam Freight | 51 | disqualified | Disqualified: a logistics provider · runs its own delivery fleet (+16) |
| RouteWise | 22 | disqualified | Disqualified: a competitor (a rule; Jev was never called) |
| Tailspin Tools | 11 | insufficient_data | 50–199 staff (+10) · No data for: Region, Runs its own fleet, Segment, Growth signal |

`insufficient_data` is not a D: Tailspin's record had no description, so Jev was never asked.
Adventure Works' technicians drive vans but it delivers no goods, and Jev was unsure which that
counts as, so the answer is flagged rather than silently scored.

### The delivery card and how to call it

````
Account scoring is live: play "jev-lead-score-accounts-route-planning-fit" (published)

  Rubric       Route-planning fit v1 · 3 rules, 3 Jev questions · tiers A/B/C/D (cut-offs borrowed)
  Jev          ai_evaluate, typesafe-ai/jev · billed to workspace Northwind GTM
  Smoke test   Northwind Supply: local 98 A · Deepline 98 A · answers match ✓
  Preview      10 accounts: A 2, B 3, C 1, D 1, disqualified 2, insufficient_data 1

Score a file (columns as in the preview; names need not match the inputs):
deepline plays run jev-lead-score-accounts-route-planning-fit --input '{"csv":"target-accounts.csv"}'
deepline runs export <run-id> --dataset result.records --out target-accounts-scored.csv

From anywhere else:
curl -X POST 'https://code.deepline.com/api/v2/webhooks/inbound/…' -H 'Content-Type: application/json' \
  -d '{"company_name":"Northwind Supply","domain":"northwind.example",
       "description":"Regional foodservice distributor with 60 refrigerated trucks.",
       "employee_count":"501-1,000","country":"United States","source_ref":"row-1041"}'
````

## Files in this skill

| File | What it is for |
|---|---|
| `scripts/jev_lib.py` | the rubric check, the scoring code the play embeds (`CORE`, JavaScript), the play renderer, state paths, the `deepline` wrapper |
| `scripts/rubric_tool.py` | check, save (with version bumps), show and export a rubric |
| `scripts/rubric.example.json` | a complete, invented account rubric to start from |
| `scripts/score_local.py` | the preview: score up to 50 real accounts on this machine with the exact play code |
| `scripts/build_scorer.py` | render the play, `deepline plays check` it, publish it |
| `scripts/smoke_test.py` | one account through the published play, compared with the local score |
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

1. **What it builds.** A scoring rubric for accounts, previewed on their own records, then a
   Deepline play that scores any account sent to it, or a whole file, and says why.
2. **Where the work runs and what it costs.** Numbers and lists are worked out in the play's code,
   free. Judgments go to Jev through Deepline's `ai_evaluate`, one call per account: about $0.04
   per million input tokens at list price, a few cents per thousand accounts, billed to their
   Deepline workspace from usage.
3. **What leaves their systems.** The fields the questions read go to Jev (through Deepline and
   the Vercel AI Gateway to TypeSafe). No key is involved.

Then, without asking: `deepline auth status --json` (say the workspace name back),
`node --version`, `python3 -B scripts/test_offline.py` and `python3 -B scripts/rubric_tool.py
list`. A saved rubric means those steps are offered as done, which is how "change the rubric" and
"rebuild" resume. If the platform check fails, say which part and the one command that fixes it
(`npm install -g deepline && deepline auth register --wait auto`), and stop.

## Step 1: Where the accounts come from

Ask **"Where will the accounts you want scored come from?"** (A CSV or export file / A CRM list /
Another system, by webhook). Then look, never ask:

- **A file:** find candidate files in the working folder by name and extension and ask **"Which
  file?"** with up to four names. Read its header (`score_local.py --file <f> --show-map` prints
  it as a mapping).
- **A CRM list:** have it exported to CSV, or pull it with the CRM's Deepline tools (`deepline
  tools search "<crm> list companies" --json`, then `describe` the one you use), into a CSV in the
  working folder. Then as a file.
- **Webhook:** no fields to read; the rubric's inputs will be the interface.

The fields that exist decide which criteria are possible. A size rule needs a headcount field; a Jev
question about what the company does needs a description. Carry that list into Step 2.

## Step 2: Build the scoring brief from what you already know, then ask only the gaps

**Before asking anything, write the brief from your own context.** Look in: your memory files and
the project instructions loaded in this session; this conversation; and documents in the working
folder a person would keep about their go-to-market (an ICP or persona doc, a positioning or
messaging doc, a strategy or "anchor context" document, sales notes, case studies). Read, do not
guess.

The brief has seven parts:

| Part | Becomes |
|---|---|
| What they sell, the problem it solves | the frame for every question's wording |
| Best-fit kinds of company, and OK and poor fits | a Choice with described options |
| Traits that make an account a fit (runs X, uses Y, sells to Z) | Nouls |
| Size, region, other numeric or list cuts | rules (only for fields Step 1 found) |
| Disqualifiers | a match rule (domains, names) or a disqualifying Noul or option |
| Signals worth points | a Score over the signals field (only if one exists) |
| What an A must be, and what the tiers are used for | cut-offs |

Show the brief as a short table: each part, what you found, and **where it came from** (a memory
file, the doc name, "this conversation"), or *missing*. Then ask only for the missing parts that
change the rubric, one click at a time, with options drawn from what you found. For example **"Which
kinds of company are your best fit?"** (options from their case studies or docs, plus Other),
**"Anything that should rule an account out entirely?"** (Competitors / Existing customers / A
segment you don't serve / None). If the brief is complete from context, ask one question instead:
**"I built this from <sources>. Anything wrong or missing?"** (Looks right / Correct something).

Never invent a segment, a disqualifier or a signal the installer did not state or a source did not
say. If "what they sell" cannot be found or answered, stop: there is nothing to score against.

## Step 3: Draft the rubric, and have it corrected

Write the rubric JSON following `references/rubric-format.md`, from the brief and the fields Step 1
found:

- **Every number, date or list is a rule.** Headcount bands, region, a competitor's domain.
- **Every judgment is a Jev question**, stating one condition, naming the fields it reads in
  backticks, describing every option. Three to eight questions is typical; more rarely helps.
- A Choice gets `not_enough_information` automatically. Level 0 of a Score means "no evidence".
- Mark anything the installer accepted from you rather than chose with `"origin": "default"`.
- Put what they sell and where each part came from in `about`.

Run `python3 -B scripts/rubric_tool.py check draft.json` and show the card. Ask **"Does this match
how you would judge an account?"** (Looks right / Change the points or cut-offs / Change a criterion
/ Other). Edit and re-check until it does, then `rubric_tool.py save draft.json`. The card's cost
line is the list-price estimate per thousand accounts.

## Step 4: Preview on ten real accounts

Run `python3 -B scripts/score_local.py --file <file>` (for a webhook installer, a sample file of a
few records they describe) with **`--show-map` first**: it prints how their columns map onto the
rubric's inputs. Show it, take corrections as `--map key=Column`, and never ask them to type field
names from memory. Then run it for real (ten accounts, a fraction of a cent) and show the table:
score, tier, top reasons, anything to review. The confirmed mapping is saved and baked into the play
at build time. Then read the real charge with `deepline billing` and use it in Step 5's price.

If every record comes back `failed` with "Jev returned no answers", the `ai_evaluate` answer shape
differs from the one this skill reads: run one `deepline tools execute ai_evaluate --input
@body.json --json`, compare with `references/jev-api.md`, and fix `_answer_item` in `CORE` before
going on.

**Stop here.** Ask **"Do these scores look right for accounts you know?"** (Yes, build it / Some are
off: adjust the rubric / Try ten different accounts). "Some are off" goes back to Step 3 with the
specific accounts in hand: which criterion moved them, and whether the fix is points, an option's
description, or a missing criterion. Rescore after every change; it costs almost nothing. Point out
any `insufficient_data` rows: that is missing data, not a bad account.

## Step 5: Build and publish, after one gate

**Build it; never score in the conversation instead.** It has to be a play because it runs
unattended: every file sent to it, every POST from another system, long after this session ends.

Run `python3 -B scripts/build_scorer.py --plan`. It renders the play from the saved rubric and
mapping and runs `deepline plays check` on it (free); a check failure stops here with the reason.
The play's steps and the traps they avoid are in `references/play-shape.md`. Then one message with
everything, and the word *write* in it:

> This **writes** to your Deepline workspace: one play, "jev-lead-score-accounts-route-planning-
> fit", published, with a webhook URL that scores any account POSTed to it. Each account scored
> costs about $0.00003 in Deepline credits for Jev (from the preview's charge). Nothing is scored
> until you call it [or: scoring the 1,240 accounts in target-accounts.csv now is a separate run,
> about $0.04].

Ask **"Go ahead?"** (Yes, publish it / Publish it, but don't score the file yet / Change something
first). On yes:

```bash
python3 -B scripts/build_scorer.py
```

It publishes the exact bytes the check passed (`--expected-artifact`) and records the webhook URL.
If no URL comes back in the publish output, `deepline plays get <play> --json` shows it under
`triggerBindings[].endpointUrl`.

If they approved scoring the file now: `deepline plays run <play> --input '{"csv":"<file>"}'`,
then `deepline runs export <run-id> --dataset result.records --out <file>-scored.csv`. Rows that
come back `failed` (a Jev outage, a rate limit) can be re-run on their own; nothing else changes.

## Step 6: Prove it with one account

`python3 -B scripts/smoke_test.py --from-preview` sends the first preview account through the
published play (the live revision) and scores it locally again. **Match** means the published
rubric, the baked-in mapping and the Jev route are all right. If the run fails, the script names the
run id; `deepline runs get <run-id> --json` shows the step and the error. Do not call the play live
until it matches.

## Step 7: Deliver, ending with how to call it

The delivery card from "Representative output", with the real numbers, then **end with how to call
it**, all three ways:

1. **A file:** `deepline plays run <play> --input '{"csv":"<file>"}'` and `deepline runs export
   <run-id> --dataset result.records --out <scored.csv>`. Columns as in the preview.
2. **Rows from a script or another play:** `{"rows": [...]}` keyed by the rubric's inputs.
3. **From anything that can POST:** the webhook URL and a `curl` with a real-shaped body,
   including `source_ref`. The response carries a `run_id`; the score is in that run.

Say what was borrowed rather than chosen, and what was not tested. When asked later: **"change the
rubric"** is Steps 3, 4, 5 and 6 (the version bumps, results say which version scored them);
**"score contacts too"** is the sibling contact skill, which can take this score as an input.

## What this skill does not claim

- The rubric is the installer's judgment written down, not a model trained on won and lost deals.
  Nothing here measures whether A-tier accounts convert better.
- Jev's accuracy on the installer's accounts is not measured beyond the ten-account preview they
  review by eye. TypeSafe publishes its own weaknesses; `references/jev-api.md` lists them.
- Jev's probabilities move slightly between calls on the same input, so a score can differ by a
  point or two on a re-run, and a tier can flip at a cut-off.
- `typesafe-ai/jev` is not version-pinned on this route; a TypeSafe release can shift answers.
  `jev_model` on each result says which model answered.
- The confidence behind `needs_review` is this skill's own (top probability minus the runner-up),
  because the evaluation API returns no confidence field.
- The Deepline route has not been run live yet (`references/live-checks.md`); the Clay-era results
  quoted here were measured calling Jev directly.
- A record written to argue for its own classification can move Jev's answer; TypeSafe says so.
- `insufficient_data` means the record lacked fields, not that the account is poor. The skill does
  not enrich; feeding it better data is the installer's move.

## What good looks like

A good run ends with **one account scored identically by the published play and locally**, a play
that `deepline plays check` calls valid, and a preview the installer read and agreed with. Every
score it returns names the criteria that moved it with their points, and an account with too little
data says `insufficient_data` with the fields it lacked rather than posing as a D. A competitor is
`disqualified` without a Jev call.

A thin run looks finished and is not:
- The rubric asks Jev a numeric question ("more than 500 employees?"). That belongs in a rule.
- Every account lands in one tier. The points or cut-offs were never checked against the preview.
- The play is published but the smoke test never ran, so the live revision is unproven.
- The installer was asked what they sell when a doc in the folder said it, or asked to type column
  names.
- The rendered play was edited by hand, so it no longer matches the preview.

## Rules

- **Jev decides, code counts.** Never put a number, a date comparison or a count in a question.
- **Context before questions.** Memory, conversation and working-folder docs first; ask only gaps
  that change the rubric.
- **Never invent** a segment, disqualifier, signal or cut-off the installer did not give or a source
  did not state. Accepted proposals are marked borrowed.
- **Always preview on real accounts before building**, and rescore after every rubric change.
- **Missing data is `insufficient_data`, never a low tier.** Five statuses, no sixth.
- **Never publish a play `deepline plays check` did not pass**, and never edit the rendered play.
- **One write gate (Step 5).** Say it is a write, name the play, price it from the preview's real
  charge.
- **Never blank a field; never overwrite a score because Jev failed.**
- **Do not call it live until the smoke test matches.**

## Worked example

The workspace, company and accounts are invented; the steps and outputs are the real shapes.

**Ask:** "Can you set up account scoring with Jev? We'll feed it our target accounts export."

**Step 0.** What it builds, the cost (a few cents per thousand), what goes to Jev; workspace
*Northwind GTM*. `test_offline.py` passes. No saved rubric.

**Step 1.** A file, named in the ask. "Which file?" → *target-accounts-q4.csv*. Its columns include
Company, Website, About, Industry, Employees, HQ Country, Recent news.

**Step 2.** The brief, from context: *what they sell* and *best-fit segments* from `positioning.md`
in the folder; *disqualifiers* (two competitor domains) from the agent's memory of an earlier
session. Missing: signals and cut-offs. "Should recent news about new locations or fleet growth add
points?" → Yes. Cut-offs: the defaults, accepted, so marked borrowed.

**Step 3.** Three rules, three questions (the card above). "Does this match how you would judge an
account?" → Looks right. Saved as v1.

**Step 4.** `--show-map`: every input matched except `description`, which no column is called; they
point it at *About* (`--map description=About`). Ten accounts scored: A 2, B 3, C 1, D 1,
disqualified 2, insufficient_data 1; `deepline billing` shows the charge. "Some are off": one
field-service company scored C because its About column was one line. That is data, not the rubric;
they accept it.

**Step 5.** `--plan`: the play renders and `plays check` says valid. The gate: one play, published,
about $0.00003 an account, nothing scored until called. Yes. Published; the webhook URL is recorded.

**Step 6.** Smoke test: local 98 A, Deepline 98 A, answers match.

**Step 7.** The card, then: run the play on *target-accounts-q4.csv* and export, or POST the curl
shown. Borrowed: the tier cut-offs. Said plainly: a Jev outage or rate limit that outlasts Deepline's own
retries leaves those rows `failed`, and they are re-run.
