---
name: check-employment-with-jev
description: |
  Build an always-on Deepline play, "Person Active At Company (Jev)", that answers whether a person
  still works at a given company, and in what capacity: their main job, a side job (fractional,
  contract, a second role), a passive tie (advisor, board seat, investor, honorary title), a former
  role, or nothing at all. It reads an enriched LinkedIn profile with its work history, or buys
  one from a LinkedIn URL when that is all you have (crustdata_v3_person_enrich), and judges each
  role on the profile with Jev, TypeSafe's decision model, through Deepline's ai_evaluate tool,
  while plain code does every date and match. People hold several current roles at once and leave
  jobs without adding an end date, so "is_current" alone is not the answer. Jev costs well under a
  tenth of a cent a person at list price, which is what makes running it on every row sensible.
  Works from a CSV or list of rows, or a webhook from any system, and returns the verdict for each
  person. Use whenever someone asks: is this contact still at the company, detect job changes,
  check if people have left their company, flag contacts who moved on, is this person an advisor
  or an employee, clean up stale contacts, verify current employer, or set up Jev or TypeSafe in
  Deepline for people. Do NOT use it to find new contacts at a company, to find where someone went
  next, to find emails or phones, to score leads, or to update a CRM or a sequencer.
category: verify-and-clean
personas: [revops, sales-development]
mechanism: workflow
touches: writes-records
keywords: [job-change, crm-hygiene]
ported_from: clay-run/clay-skill-creator/skills/shy-rahnama/check-employment-with-jev
---

# Check employment with Jev: judge each role, then let code decide

**The insight: a LinkedIn profile does not have "a current job", so "is this person still at the
company?" cannot be read off one field.** Enrichment providers return current experience as a
*list*, and real profiles show why. Measured on real profiles: a CEO who is also a university
trustee; a CTO who also holds an adjunct university post; a founder whose co-founder title at an
earlier company still has no end date beside two newer roles. And a role nobody closed stays
"current" forever: a person who left in 2025 without editing the profile still reads as employed.
A single `is_current` flag, or a model asked "does this person work at X?", answers these wrong in
both directions.

The evidence for the fix is Jev's own documentation. TypeSafe publishes what Jev 1.13 is bad at:
comparing dates, counting items in a list, and reading loosely. Its advice for a list is to ask one
question per item and combine the answers in code. So:

- **Code finds the roles** that could be at the company: same website, same LinkedIn company page,
  or a name that matches once "Inc" and "LLC" are dropped. It works out every date.
- **Jev answers small questions about one role at a time**: is this the same company, what kind of
  role is it (a job, a contract, an advisory seat, an investment, an honorary title), is it still
  held given the jobs started after it, is it the main job. The person's other current roles are
  classified too, so a trustee seat never makes a CEO look like they left (it did, at 64%, before
  this was added).
- **Code combines the answers into one verdict** from a fixed set, with a confidence and the
  evidence in a sentence.
- **Jev is cheap enough to leave on**: the gateway lists $0.042 per million input tokens, and a
  person runs 800 to 2,500 tokens (measured on jev-1.13.0), so four to ten cents per thousand people
  at list price. Deepline bills it from usage. The real cost is buying a profile
  (`crustdata_v3_person_enrich`, priced per matched record) for a person sent with a LinkedIn URL
  and no profile.

> **This skill is not finished when the play is built.** It is finished when the play is
> published, the invented people and one of the installer's own have gone through it with the
> same verdicts as the local check, and the installer has been shown how to call it. If you stop
> early, say which step you stopped at and the command that resumes it.

## How to talk to the installer

- **Every question is a choice they click**, asked with the host's question tool
  (`AskUserQuestion` in Claude Code), likely answer first, free text only as "Other". Batch the
  questions of one step into one ask.
- **Before any question, apply the test: does the answer change what gets built or what it costs?**
  If not, do not ask it, and do not defer it to a later step either.
- **Never ask what a command can answer.** A file's columns, how many rows have only a URL, the
  workspace: look, then show what you found.
- **Run every command yourself.** The installer only decides.
- Show names, never ids, in anything the installer reads.

## Declared inputs

**Nothing here ships with a value.** Every input is the installer's, read from their files or
asked; where a default is used it is named, and using it is said at delivery.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Where people come from** | a CSV or JSON export of people (from a CRM, a sheet, a list), or "another system" (webhook) | no default: it decides where the preview comes from |
| **A Deepline workspace** | the CLI signed in (`deepline auth status`) with credits for Jev and any profiles bought | stop at Step 0 |

Read and shown, never asked: which columns hold the profile, the LinkedIn URL, the person's name
and the company. The profile column is found by what its cells hold. A file with no company column
is said plainly and does not block anything: the preview uses the invented people instead, and the
mapping is only the installer's to set when they call the play.

**Not asked, ever:** which fields the verdict returns (fixed), what counts as "active" (the verdict
keeps a job, a side job and a passive tie apart; the installer filters on it), the 60% and 40%
cut-offs (fixed in code and stated), a callback URL (the caller's own), any key (there is none:
Jev and the profile lookup are billed to the Deepline workspace), whether to preview (always), and
real people's records in the chat.

### The play's interface, prescribed

Inputs, one flat field each; at least one company field, and a profile or a LinkedIn URL:

| Input | |
|---|---|
| `company_name`, `company_domain`, `company_linkedin_url` | the company to check against. A website or LinkedIn page makes matching exact |
| `profile` | an enriched profile with a work history, as an object or JSON text: a flat `experience` list, a People Data Labs style record, or a `crustdata_v3_person_enrich` response all read |
| `linkedin_url` | the person's LinkedIn URL, used to buy a profile when `profile` is empty |
| `full_name` | optional; any profile, supplied or bought, whose name shares no word with it is flagged and capped at 50% |
| `skip_enrichment` | `true` never buys a profile (the person comes back `not_checked`) |
| `max_profile_age_days` | re-buy a supplied profile last refreshed longer ago than this; blank never does |
| `source_ref` | echoed back, for joining |

Outputs, every key always present, each its own column in the run's export:

| Key | |
|---|---|
| `active_at_company` | `yes` · `passive` · `no` · `unsure` · `not_checked`. Five, no sixth |
| `relationship` | `primary_job` · `side_job` · `advisor_or_board` · `investor` · `honorary` · `former` · `no_record` · `unknown` |
| `verdict_confidence` | 0 to 100, the probability behind the verdict |
| `check_status` | `checked` · `no_profile` · `blocked_missing_input` · `failed` |
| `evidence`, `needs_review`, `check_note` | the verdict in a sentence; the answers worth a second look (`none` otherwise); why a person was not checked (`none` otherwise) |
| `role_title`, `role_company`, `role_started`, `role_ended`, `months_in_role` | the role the verdict rests on |
| `other_current_roles`, `main_employer` | what else they hold now, and where their main job is when it is not here |
| `company_checked`, `profile_source`, `profile_age_days`, `roles_json`, `jev_model`, `jev_input_tokens`, `error`, `source_ref`, `checked_at` | provenance |

The export also carries the play's working columns: `found` (a bought profile, so it is never
bought twice for the same check), `jev` and `verdict`. How each verdict is reached, rule by rule,
is in `references/how-it-decides.md`.

## What this skill touches

- **Reads**: the file the installer names (its columns and 10 rows, up to 50 with `--limit`); the
  Deepline workspace name and balance.
- **Writes**: in Deepline, one play `person-active-at-company-jev` (Step 5), published with a
  webhook, live for the workspace. It writes nothing onto anyone's records: each run returns the
  verdicts as a dataset the caller exports. Locally: the rendered play, preview results and build
  state under `~/.local/state/check-employment-with-jev/`.
- **Sends**: to Jev (TypeSafe's model, through Deepline's `ai_evaluate`), for each person checked,
  the profile's headline and, per role, the company, title, start and end, description (first 300
  characters), work type and company website, plus the company being checked. Name, email and
  phone fields are never sent, though a headline or a company name can contain a name. To
  Crustdata (through `crustdata_v3_person_enrich`), the LinkedIn URL of each person bought.
- **Spends**: one `crustdata_v3_person_enrich` call for each person sent with a LinkedIn URL and
  no usable profile, priced per matched record, whether or not the profile it returns is the right
  person; Jev at four to ten cents per thousand people at the gateway's list price, billed by
  Deepline from usage. Read `deepline billing` before and after the preview for the real figures.
- **Never**: clears or blanks a field; turns a failed Jev call or a person it could not check into
  a verdict; contacts anyone; writes to a CRM or a sequencer; deletes anything.
- **Halts**: Step 1 `other`, Step 3 `sample-review`, Step 3 `spend-approval`, Step 4
  `write-approval`, Step 4 `spend-approval`, Step 6 `sample-review`.
- **Vendor-specific**: Jev, from TypeSafe, reached only through Deepline's `ai_evaluate`. Without
  a Deepline workspace there is nothing to judge the roles with, so the skill stops at Step 0.

## Representative output

The people, companies and numbers are invented; the shapes are what the play returns.

### Verdicts, one row per person

| Person | Checked against | Active | Relationship | Confidence | Evidence |
|---|---|---|---|---|---|
| Dana Ruiz | Northwind Supply | yes | primary_job | 100 | VP Operations at Northwind Supply since April 2021 (works there; main job). Also current: Contoso Robotics: Advisor; Tailspin Toys: Angel Investor |
| Pat Quinn | Northwind Supply | yes | side_job | 79 | Fractional CFO at Northwind Supply since March 2024 (works there as a contractor or consultant; not the main job). Also current: Quinn Finance Partners: Founder & Principal; Contoso Robotics: Fractional CFO |
| Lee Park | Northwind Supply | passive | advisor_or_board | 99 | Board Member at Northwind Supply since May 2022 (advisor or board member). Also current: Adatum: Chief Executive Officer |
| Sam Okafor | Fabrikam Freight | no | former | 84 | Software Engineer at Fabrikam Freight since February 2019, still listed as current, but replaced by a later full-time job at Litware |
| Kim Lau | Acme Corp | no | no_record | 89 | No role at Acme Corp on this profile (Acme Analytics: a different company, 11% same) |
| Ari Moss | Northwind Supply | not_checked | unknown | 0 | Not checked: no profile and no LinkedIn profile URL to enrich |

Sam's profile still lists Fabrikam as current; that is the case a "current employer" field gets
wrong. Ari was sent with nothing to read, and comes back `not_checked` rather than `no`.

### The delivery card

````
"Person Active At Company (Jev)" is live: play person-active-at-company-jev, workspace Northwind GTM

  Jev          typesafe-ai/jev through Deepline ai_evaluate · billed to the workspace, no key
  Profiles     read from your "Enrich person" column; bought (crustdata_v3_person_enrich) only for
               rows with just a LinkedIn URL
  Preview      10 of your people: yes 7, passive 1, no 1, unsure 1 · 14,200 Jev input tokens
  Smoke test   11 invented people + 1 of yours through the published play: 12 match the local check

From a file (columns named as the inputs):
deepline plays run --name person-active-at-company-jev --input '{"csv":"contacts.csv"}'
deepline runs export <run-id> --dataset result.records --out verdicts.csv

From anywhere else (a LinkedIn URL with no profile buys one):
curl -X POST '<the webhook URL>' -H 'Content-Type: application/json' \
  -H 'x-deepline-dedupe-key: crm-4411' \
  -d '{"company_domain":"northwind.example","linkedin_url":"<their LinkedIn URL>",
       "full_name":"Dana Ruiz","source_ref":"crm-4411"}'
````

## Files in this skill

| File | What it is for |
|---|---|
| `scripts/active_lib.py` | the verdict code (one JavaScript source) the play embeds and the preview runs under `node`, the play template, state paths, the `deepline` wrapper |
| `scripts/check_local.py` | the preview: check 10 (up to 50) of the installer's people on this machine with the play's own code |
| `scripts/build_workflow.py` | render the play, `deepline plays check` it, publish it |
| `scripts/smoke_test.py` | send people through the published play and compare each verdict with the local check |
| `scripts/test_offline.py` | the play template, the verdict rules, the profile shapes and the failure paths, with no network or credits |
| `scripts/fixtures.json` | eleven invented people, each with the verdict a correct run gives |
| `scripts/jev_answers.json` | Jev's recorded answers for those people, replayed by the offline test |
| `references/how-it-decides.md` | how roles are matched, the questions, how the answers combine, what was measured |
| `references/play-shape.md` | the play step by step, how to call it, and the traps it avoids |
| `references/jev-api.md` | `ai_evaluate`'s request and answer shapes, price, and what Jev is bad at |

Run every script with `python3 -B`. They need only the standard library, `node` and the
`deepline` CLI.

**Do not start a step before the steps above it have their answers.** If a declared input is
missing, ask for it; never assume one and continue.

## Step 0: Say what this builds, what it costs, and check the platform

Three short paragraphs:

1. **What it builds.** A Deepline play that takes a person and a company and says whether the
   person works there now, as their main job or a side job, holds only an advisory, board,
   investor or honorary tie, used to, or never did, with the evidence. It runs on a file of people
   or on each POST to its webhook.
2. **Where the work runs and what it costs.** Matching and dates run in the play's code, free.
   Judging each role goes to Jev through `ai_evaluate`: four to ten cents per thousand people at
   list price, billed by Deepline. A person sent with only a LinkedIn URL costs one
   `crustdata_v3_person_enrich` lookup, priced per matched record.
3. **What leaves their systems.** For each role on the profile, its company, title, dates, a short
   description and the company's website, plus the headline, go to Jev; name, email and phone
   fields never do. A LinkedIn URL goes to Crustdata only when a profile is bought. There is no
   key to handle.

Then, without asking: `deepline auth status` (say the workspace name back), `deepline billing`
(say the balance), and `python3 -B scripts/test_offline.py --play`. Missing CLI:
`npm install -g deepline && deepline auth register --wait auto`. If a check fails, say which part
and the one command that fixes it, and stop.

## Step 1: Where the people come from

If the ask named a file, skip the question. Otherwise ask **"Where are the people you want
checked?"** (A CSV or JSON export I'll point you to / Another system, by webhook). A CRM is an
export first: pull the contacts with the CRM's Deepline tools or its own export, into a CSV with
the company and the LinkedIn URL (and a profile column if one exists).

- **A file:** nothing more to ask; Step 3 reads it.
- **A webhook:** nothing to read; the interface above is the contract.

## Step 2: Nothing to set up

Jev and the profile lookup are billed to the Deepline workspace; there is no key to find or
save. Go to Step 3.

## Step 3: Preview

- **A file:** `python3 -B scripts/check_local.py --file <path> --show-map`. Show the mapping (the
  profile column is found by what its cells hold, the rest by name) and take corrections as
  `--map input=Column`. If no column holds the company, say so and preview with `--fixtures`
  instead; nothing else changes. Otherwise run it without `--show-map`. If rows have only a
  LinkedIn URL, the output says how many: ask **"Buy those N profiles for the preview? One
  Crustdata lookup each, priced per match."** (No, preview the rest / Yes) and add `--enrich`
  only on yes.
- **Webhook:** `python3 -B scripts/check_local.py --fixtures`, without asking. Show the table as
  how verdicts look; it proves nothing about their people, so do not ask the review question below
  about it.

**Stop here for a preview of their own people.** Show the verdicts and ask **"Do these look right
for people you know?"** (Yes, build it / One is wrong: show me why / Try ten other rows: the same
command with `--skip 10`). "One is wrong" means reading that person's `roles_json` together: which
role was matched, what Jev called it, what code did with it. The fix is a column mapping, a missing
company website, or a profile that is simply out of date; the rules themselves do not change per
installer. Read `deepline billing` again and say what the preview cost.

## Step 4: One gate: the write and the spend

Run `python3 -B scripts/build_workflow.py --plan` (it renders the play and runs `deepline plays
check`, free). Then one message with all of it, and the word *write*:

> This **writes** to your Deepline workspace: one play, "person-active-at-company-jev", published
> and live for the workspace, with a webhook anyone holding its URL can POST to. Each person costs
> well under a tenth of a cent in Jev, and one Crustdata profile lookup when their profile has to
> be bought (priced per match; the preview's bill above is the guide). Nothing runs until you call
> it with a file or something POSTs to the webhook. Proving it (Step 6) runs the eleven invented
> people through it: Jev only, no profiles bought.

Ask **"Go ahead?"** (Yes, build it / Change something first).

## Step 5: Build and publish

**Build it; never check people in the conversation instead.** It has to be a play because it
runs unattended: every file someone runs through it, every POST from another system.

```bash
python3 -B scripts/build_workflow.py
```

It renders the play, checks it again, and publishes it (`deepline plays publish`), printing the
webhook URL. A refused check exits 6 and publishes nothing; relay the errors. The steps and the
traps they avoid are in `references/play-shape.md`. If the installer asks for a schedule (re-check
a list every month), a play can carry a `cron` binding with a fixed input; build that only on
request, and price every run of it first.

## Step 6: Prove it

- `python3 -B scripts/smoke_test.py --fixtures`: the eleven invented people through the published
  play, free apart from Jev; every verdict must match the local check and the expected answer.
- **File installs:** `python3 -B scripts/smoke_test.py --from-preview`: the first person of the
  Step 3 preview, through the play. It buys a profile only if that person had just a LinkedIn URL.

A `failed` verdict's `error` names the cause (billing, rate limit, upstream); fix it and re-run.
Do not call the play live until the smoke test matches.

## Step 7: Deliver, ending with how to call it

The delivery card from "Representative output", with the real numbers, then **how to call it**:

1. **From a file:** `deepline plays run --name person-active-at-company-jev --input
   '{"csv":"<file>"}'`, then `deepline runs export <run-id> --dataset result.records --out
   verdicts.csv`. The columns must carry the inputs' names (the Step 3 mapping says which of theirs
   is which). "`active_at_company` is `no`" in that export is the list of people who have left.
2. **From anything that can POST:** the webhook URL and a `curl` with a real-shaped body and a
   stable `x-deepline-dedupe-key`. The response carries a `run_id`; the verdict is in that run.

Say what was borrowed or not tested. When asked later: **"check another list"** is Step 3 and
the call above; a change to the decision code is `test_offline.py`, then Step 5 again.

## What this skill does not claim

- A LinkedIn profile is self-reported. A person who left without adding an end date, and has not
  listed a new job, still reads as active; nothing here can see past the profile.
- A bought profile can be the wrong person (a made-up LinkedIn URL returned a stranger's profile
  and was billed, measured on Clay's Enrich person); `full_name` catches a mismatch only when it
  is sent.
- Accuracy is measured on eleven invented people and thirteen real profiles, by eye, with the same
  decision code on Clay and jev-1.13.0 (2026-09). It is not a benchmark, and Jev's probabilities
  move a point or two between calls, so a person near a cut-off can flip between runs.
- The Deepline play has passed the offline replay and `deepline plays check`; its first live runs
  are Step 6. The response shapes of `ai_evaluate` and `crustdata_v3_person_enrich` are read from
  their published schemas, and the code accepts them one level up or down.
- `typesafe-ai/jev` is not version-pinned on Deepline's route; the thresholds were set on
  jev-1.13.0, and `jev_model` records what answered.
- Recognising a renamed company, or a brand of a parent, relies on what Jev knows; Facebook and Meta
  matched, a small company's rename may not.

## What good looks like

A good run ends with the play published, the eleven invented people matching through it and
locally, and a preview the installer read in which the hard cases come out right: a person with
an advisory seat elsewhere is still `primary_job`, a board member is `passive` and not `yes`, and a
person whose old job was never closed but who has a newer full-time job is `former`. Every verdict
names the role it rests on and the other roles they hold; a person with nothing to read is
`not_checked`, never `no`.

A thin run looks finished and is not:
- Every row came back `not_checked` because no company column was mapped.
- Every row bought a profile although the file already had one (`profile_source` = `enriched`).
- The play is published but the smoke test never ran.
- A verdict of `no` is being used to delete contacts; `no` is a reason to look, not proof.

## Rules

- **Jev judges one role at a time; code finds the roles, does the dates, and decides.**
- **Keep a job, a side job and a passive tie apart.** Never collapse `passive` into `yes` or `no`.
- **Missing data is `not_checked`, never `no`.** Five verdict values.
- **Send Jev the least that decides the question.** Roles and headline, never contact fields.
- **Always preview before building**, and prove the published play against the local check.
- **One write gate (Step 4).** Say it is a write, name the play and its webhook, price Jev and the
  profiles.
- **Never blank a field; never turn a failed Jev call or an unchecked person into a verdict.**

## Worked example

The workspace, people and companies are invented; the steps and outputs are the real shapes.

**Ask:** "Can you set up something that flags when our customer contacts have left their company?
Here's the export: contacts.csv."

**Step 0.** Workspace *Northwind GTM*, balance read. Offline test passes, play check valid.

**Step 1.** The file was named; no question.

**Step 3.** `--show-map`: company_name ← *Account*, company_domain ← *Website*, linkedin_url ←
*LinkedIn*, full_name ← *Name*, profile ← *Enrich Person* (found by content). Two of ten rows have
only a URL: "Buy those 2 profiles for the preview?" → No. Eight checked: yes 6, passive 1 (a board
member), no 1 (an old role never closed, a newer full-time job elsewhere); two `not_checked`. "Do
these look right?" → Yes.

**Step 4.** The gate names the play, its webhook, and Jev plus a profile lookup per URL-only
person. "Yes, build it."

**Step 5.** Checked and published; webhook URL printed.

**Step 6.** Smoke test: 11 of 11 match; `--from-preview` matches.

**Step 7.** The card, then the `plays run` / `runs export` commands for the full export and the
`curl` for their CRM's webhook.
