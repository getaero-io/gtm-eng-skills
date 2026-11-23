---
name: prepare-job-application
description: |
  For each company and role on a job seeker's list, find the open posting and the recruiter
  attached to it, rewrite the resume in that posting's own vocabulary without inventing any
  experience, and draft a short LinkedIn note to the recruiter — by writing (once) and running a
  Deepline play that finds active openings, complete with each posting's description, and finds
  the recruiters to contact — talent-acquisition staff at the company — then running the author's two prompts in your agent on the results. Use whenever
  someone asks: find the recruiter for these roles, tailor my resume to this job, write a LinkedIn
  message to the recruiter, help me apply to these companies, prep my applications for this list,
  or who is hiring for X at these companies and how do I reach them. Do NOT use it to source
  candidates as a recruiter, to find anyone's email or phone number, to send messages or
  connection requests, to submit an application, or to write cold sales emails — it ends at a
  reviewed draft folder per role that a person sends.
category: personalize-outbound
personas: [gtm-engineer, sales-development]
mechanism: workflow
touches: writes-own-output
keywords: []
ported_from: clay-run/clay-skill-creator/skills/lorcan-o-rourke/prepare-job-application
---

# Prepare a job application (find the posting's recruiter, then write in the posting's words)

The insight, in the author's prompts: **a resume is read first by software scanning for the
posting's exact terms, and a recruiter note is read on a phone in one glance.** So the resume
rewrite lifts *verbatim* terms from the job description and never adds experience the candidate
does not have — *"only reference experience and skills explicitly stated in the resume — do not
invent or assume anything"* — and the message is four short lines that *"get a RESPONSE through
genuine personalization"*, under a hard ceiling of 187 characters. Why 187 was never established
by the author (see *What this skill does not claim*).

The judgment lives in two prompts, carried **verbatim** in `references/prompts.md` with their
output schemas and the message assembly rule. This skill's job is to stand up the data side as a
Deepline play, run the prompts in your agent on what it returns, and hand back
one reviewed folder per role — not to reword them.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The companies** | a list of company domains or company LinkedIn URLs, one per company | no default — nothing to search |
| **The roles** | job-title keywords, comma-separated, the way the seeker would type them into a job board (e.g. *Software Engineer, Backend Engineer*) | no default — ask. Without it the search returns every open role and the cost is unbounded |
| **Seniority** *(optional)* | one of the postings' seniority levels, e.g. entry level, when the seeker wants only that band | not applied — title keywords alone return every level, and the test run on *Software Engineer* returned a senior role beside a junior one |
| **Title words to exclude** *(optional)* | comma-separated words a title must not contain, e.g. *Senior, Staff, Principal* | not applied |
| **Recency window** | how many days back a posting may be | **30 days is defensible** and must be stated: the author's table fired only on newly posted roles, so unbounded age was never the intent |
| **Roles per company** | the most postings to keep per company, 1 to 10 | no default — ask, because it multiplies every later cost |
| **The seeker's LinkedIn URL** | their own profile URL | the message runs on the resume text alone, without career history; say so in the output |
| **The resume** | a Google Doc link (read through your agent's Drive connector when one is present), a PDF, Word or Markdown file, or pasted text | no default — without it the recruiter list is still delivered, and the resume and message steps do not run |
| **Where drafts go** | a local folder path; optionally also a Google Drive folder, when the connector is present, to receive each tailored resume as a new Google Doc | **a local `applications/` folder beside the conversation is the default**; nothing is written to Drive unless asked |
| **Spend cap** | the most Deepline credits they will spend on this list | asked after the one-company test (Step 4), in credits, with the measured per-company cost beside it. No cap, no full run |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the companies, roles and resume you supply; your own profile through one Deepline person-enrichment call; each play run's step outputs (open postings with their descriptions, and the recruiters found at each company).
- **Writes** — one play file of its own, `find-role-recruiters.play.ts`, in your working directory (created once, reused after), its runs and their Customer DB table, and the draft files in the folder you name (and, only if you ask, a new Google Doc per tailored resume in a Drive folder you name).
- **Never** — sends a message or connection request, applies or submits anything, edits your original resume, edits a play, table or record it did not create, or writes to a CRM or applicant-tracking system.
- **Halts** — Step 2 write-approval, Step 2 spend-approval, Step 4 sample-review, Step 4 spend-approval

## Step 0 — Verify Deepline is working, and say what this does

Say this first, as two sentences: *this writes one Deepline play (or reuses it if it is already
there) and runs it once per company to find open roles and their recruiters; it then drafts a
tailored resume and a recruiter note per role into a folder for you to review, and never sends,
applies or writes anywhere else.*

Run `deepline preflight --json`. If it fails, name what is wrong — the CLI missing, out of date,
or signed out — give the one fix (`npm install -g deepline && deepline auth register --wait auto`,
or `deepline update`), and **stop**. Tell the user which org you are in.

This skill writes and runs its play **per the `deepline-gtm` skill's `recipes/deepline-plays.md`**
— read it before Step 2 and follow it for the play shape, `deepline plays check`, runs and export.

## Step 1 — Collect the inputs and read the resume (interview; do not guess)

1. **Companies** — domains or company LinkedIn URLs. Dedupe on the normalized domain.
2. **Roles** — the title keywords, comma-separated, exactly as they will be matched against posting titles; ask whether to filter by seniority or exclude title words (e.g. *Senior*), since keywords alone return every level.
3. **Recency window** and **roles per company** — offer 30 days for the window and say it is a
   default; ask for the per-company count with no default.
4. **The seeker's LinkedIn URL.**
5. **The resume.** A Google Doc link is read through the agent's own Drive connector if one is
   present; if not, say so once and ask for a PDF, Word or Markdown file or pasted text. Read the
   full text into `resume_text`. Never pass the document through Deepline, and never edit the original.
6. **Where drafts go**, and whether tailored resumes should also become new Google Docs.

Then enrich the seeker once, so the message prompt has their career history:
`deepline tools execute crustdata_person_enrichment --input '{"linkedinProfileUrl":"<the seeker's URL>"}' --json`.
Do not request email or phone fields. Verify **the name is non-empty** in the output — a call can
complete around an empty result — and keep name, location, experience and education for the message
prompt (read the field paths from this first response). If it returns no person, say so and continue
on the resume text alone. `deepline tools describe` declares **0.4 Deepline credits per returned
profile** at the database rate; read your own figure.

## Step 2 — Find or write the play (one gate first)

**Look before building.** Check the working directory for `find-role-recruiters.play.ts`, and
`deepline plays grep "role recruiters"` for a saved copy. If one exists, read it and check it has
the steps below; if so, reuse it and skip to Step 3. If it exists but differs, say how, and ask
whether to use it as-is or write a fresh one alongside — never edit it.

**Before creating anything, one message:** the play file name, the step list below, and that the
next step runs it on **one** company. Give the declared per-call figures you read for each step.
For reference only, the author's original Clay build (2026-09-28, three companies, up to 3
postings each) reported **1 Clay data credit and 2 action executions per company**; that is not a
Deepline price. **Wait for an explicit yes.**

Read each tool's real inputs with `deepline tools describe <id> --json` before writing the play —
parameter names below were read on 2026-09-30 and can drift.

The play, in order — one row per company, with `domain`, `job_title_keywords`,
`job_title_exclude_keywords`, `days` and `limit` on every row:

| # | Step | Deepline tool | What it does |
|---|---|---|---|
| 1 | **Find active job openings** | `predictleads_company_job_openings` | `company_id_or_domain` ← `domain`; `first_seen_at_from` ← today minus `days`; `active_only: true`; `with_description_only: true`. **It has no title-keyword filter**, so a `run_javascript` step keeps postings whose title contains any keyword and none of the exclusions, and the optional seniority, then caps at `limit`. Keep the pre-filter count of active postings and the post-filter count as the `jobCount` equivalents. Each kept posting carries title, description, location, seniority, salary, first-seen date and URL; the response is JSON:API-shaped (`data[]` with `attributes`), so pin the exact paths from the first response. **0.56 Deepline credits per call**, per `describe` |
| 2 | **Find recruiters at company** | `crustdata_v3_person_search` | `filters` (`op: "and"`): `experience.employment_details.current.company_website_domain` `=` the domain, and an `or` group of `experience.employment_details.current.title` `contains` `Recruiter`, `Talent Acquisition`, `Recruiting`; `limit: 3`. Read `profiles[]` (name, current title, profile URL) and `total_count`. PredictLeads postings do not name a recruiter, so this is the recruiter for every posting — which in the author's original test was all nine anyway. **0.02 Deepline credits per returned result**, per `describe` |
| 3 | **Recruiter's recent posts** *(optional — off unless the installer turns it on)* | `harvestapi_get_profile_posts` per recruiter from step 2 | `profile` ← the recruiter's profile URL, `postedLimit: "month"`. Read each post's text, URL and date from the first response. **0.03 Deepline credits per page**, per `describe`. It exists because the message prompt's highest-priority hook is *"Saw your post about the [Job Title] role"*; the author's table carried this step but never wired its output into the prompt, so its value is unmeasured |

Run `deepline plays check ./find-role-recruiters.play.ts` before any run.

## Step 3 — Test on one company

Take one company from the list into a one-row CSV and run
`deepline plays run ./find-role-recruiters.play.ts --input '{"csv":"one.csv"}' --debug`, then read
`deepline runs get <run-id> --full --json`:

- **cost** — the run's reported billing is its actual spend. Use it, **never the org balance**,
  which moves with everyone else's work.
- **values** — each step's output for the row: the kept postings and their counts, and the
  recruiter profiles. A company with no matching posting returns an empty list. Check values,
  not status: a company with no recruiter profiles has no one to write to, and its postings are
  listed with a resume and no message. A pre-filter count above the cap means roles were left
  behind — say how many.

If a step errored or came back empty, fix the build (filters, field paths, parameter names) and
re-test. Then run Step 5's two writing steps on this one company's postings, so the sample in
Step 4 is the complete deliverable and not just data.

## Step 4 — Show the sample, set the cap, then run the rest

**One message:** this company's full application folder for each posting (the queue row, the
resume change log, the assembled message with its character count), the measured cost for one
company and how many postings it covered, the cost the remaining companies would reach if each
returned the same number of postings — and one question: *what is the most you want to spend on
this list?* Say plainly that companies return different numbers of postings, so the total is a
range and the cap is what stops it. **Wait** — this is the look at resume taste and message tone
that no estimate reveals, and the spend decision in the same breath.

Then run the remaining companies in batches (a CSV slice per run). Keep a running total of each
finished run's reported billing; **stop before the next batch would pass the cap** and say how
many companies remain. Export each with `deepline runs export <run-id> --out <file>`.

## Step 5 — Do the work: two prompts per posting, in this agent

Both prompts are in `references/prompts.md`. Run them **verbatim**, filling the variables from the
step that produced each value, exactly as the wiring table there says. You are the model here;
the author ran both on a Claude Sonnet-class model, and the message prompt's character budget is
enforced in code below because a model alone cannot be trusted to count.

**A. Resume analysis → tailored resume.** Fill `{{job_description}}` from the posting row's
`description` (strip its HTML line breaks first) and `{{resume_text}}` from Step 1. The prompt returns `job_analysis` and 3 to 5
`suggestions`, each quoting the resume line it addresses (`issue`) with a paste-ready replacement
(`update`) and the reason (`fix`). Then build the tailored copy:

1. Start from the original text, untouched.
2. For each suggestion whose `issue` quotes a line that exists in the resume, replace that line
   with `update`. Mark it **applied**.
3. For each suggestion that would **add** something not in the resume — a technology the posting
   names that the resume never mentions, or a bullet for experience no line supports — do **not**
   apply it. Mark it **needs your confirmation** and carry the suggested text. The author's rule
   is that such additions go in *"only if the candidate has real exposure"*, and only the seeker
   knows.
4. Write the result as Markdown; also as `.docx` when a converter (pandoc or python-docx) is
   available on this machine, and as a new Google Doc only when Step 1 asked for it. Say which
   formats were produced.

If the prompt returns an empty result (its own rule when the description is missing), write no
resume for that posting and say why.

**B. Recruiter message.** Pick the recruiter: the posting's own named recruiter if the posting
text names one, otherwise the first person from *Find recruiters at company*, and say in the output
which it was. Fill the variables from the posting row (`job_title`, `company_name`,
`job_description`), the chosen recruiter (`recruiter_name`), the seeker's enrichment from Step 1
(`sender_name`, `sender_location`, `sender_experience`, `sender_education`) and `resume_text`.
When the posts step is on, paste that recruiter's most recent relevant post text into the prompt's
`RECRUITER_POST` slot; otherwise leave the slot as the prompt has it. The prompt returns
`opening_line`, `message_body` (3 or 4 lines) and its own `character_counts`. **Recount in
code:** opening ≤ 12, lines ≤ 45 / 50 / 45 / 35, and the sum of all of them ≤ 187. If any limit
fails, re-run the prompt with the failing line and its count stated, up to twice; if it still
fails, deliver the message flagged `over budget` with the count — never trim it silently.
Assemble it as the author's table did: `opening_line`, a blank line, line 1 and line 2 joined by
a space, a blank line, line 3, a blank line, line 4.

A posting whose company returned no recruiter at all gets a resume but no message, and is listed
as such.

## Step 6 — Assemble one folder per posting

`<drafts folder>/<Company> - <Role>/` holding `role.md` (title, location, seniority, salary range
as the posting gives it, posted date, posting URL and application URL, recruiter name and profile
URL, the `job_analysis` terms), `resume - <Company>.md` (and `.docx` / Google Doc link when
produced), `resume-changes.md` (every suggestion with its status), and `message.txt`. Build each
field **from the step that produced it** — posting facts from the search row, the recruiter's name,
title and profile from the posting or the company recruiter search (and say which), the posting
counts from *Find active job openings* —
never from the prompts' copies. A failed run is listed with its error, never dropped.

## Step 7 — Deliver

The queue table below, the folder path, and a summary: companies in, companies with at least one
matching posting with a recruiter, postings kept versus `jobCount` found, resumes written,
suggestions applied versus needing confirmation, messages within budget versus flagged, failed
runs, and credits spent (the sum of each run's reported billing, plus the one seeker
enrichment) against the cap. Then the answer-sheet offer from *Declared inputs*.

## Representative output

### Application queue

| Company | Role | Posted | Recruiter | Recruiter source | Resume | Message | Posting |
|---|---|---|---|---|---|---|---|
| Northwind | Backend Engineer | 6 days ago | Priya Raman · linkedin.com/in/… | named on the posting | 4 applied · 1 to confirm | 171 chars ✓ | linkedin.com/jobs/view/… |
| Contoso | Software Engineer, Platform | 12 days ago | Marcus Hale · linkedin.com/in/… | company search, Talent Acquisition | 3 applied · 0 to confirm | 189 chars · over budget | linkedin.com/jobs/view/… |
| Fabrikam | — | — | — | — | — | — | 0 matching postings in 30 days |

### Resume change log

| Section | Original line | Replacement | Why | Status |
|---|---|---|---|---|
| Work Experience | Designed data pipeline architecture in team of 5; scaled 0 to 100,000 DAU | Built and maintained data pipeline architecture in a team of 5, scaling from 0 to 100,000 daily active users | the posting asks for "building and maintaining data pipelines" | applied |
| Skills | Advanced: SQL, PHP, JavaScript; Proficient: Python | Advanced: SQL, Python, PHP, JavaScript | the posting treats SQL and Python as co-equal | applied |
| Skills | — | add dbt | named as preferred in the posting; absent from the resume | needs your confirmation |

### Recruiter message

```
Hey Priya,

The Kafka focus on the Backend Engineer role caught my eye. 6 years at Contoso building event pipelines.

Streaming at your scale is what I've been solving.

Open to a quick chat if relevant?
```

*Opening 10 · lines 47 / 45 / 44 / 31 · total 177 of 187.*

## What this skill does not claim

- Why the message ceiling is 187 characters was never established by the author; the skill enforces it as written.
- The recruiter's recent posts step was in the author's table but its output was never wired into the message, so whether a post-based hook improves replies is unmeasured — the step ships off by default.
- The original Clay build was run end to end on three companies (nine postings, 1 Clay credit and 2 action executions per company), and both prompts were run on all nine by the author. The Deepline play has not been run, and nothing has measured a longer list or a company that returns no recruiters.
- Title keywords return every seniority level unless the seniority filter or exclusions are set; the author's test for *Software Engineer* returned one senior role.
- A tailored resume is the original with lines replaced by the prompt's paste-ready rewrites; it is not re-laid-out, and formatting from a PDF or Word original may not survive the round trip.
- Reply rates for messages written this way have never been measured.
- PredictLeads job openings carry no recruiter field, so a posting-named recruiter is only found when the description text names one; otherwise the recruiter is a company search result.
- The author's table enriched the posting's recruiter profile; this skill does not, because none of the nine test postings named one.
- A company recruiter found by title is not the recruiter on the posting; how much that weakens the message was never measured.

## What good looks like

- Every role in the queue traces to a posting URL with a posted date inside the window, and every recruiter to a profile URL with a note of whether they were on the posting or found at the company.
- Every changed resume line sits next to the original and the posting term that motivated it; nothing was added without the seeker's yes.
- Every message shows its count, and none was trimmed by hand to pass.
- Companies with no matching posting say so with the `jobCount` that was found, rather than vanishing.
- The common mistake: rewording the prompts "to fit the skill". They are the product; the skill is the wiring.

## Rules

- MUST use the two prompts in `references/prompts.md` verbatim; NEVER reword, merge or shorten them.
- MUST look for an existing `find-role-recruiters.play.ts` before writing one, and NEVER edit a play, table or record this skill did not create.
- MUST get explicit approval (Step 2) before creating the play or running it, and a spend cap (Step 4) before running more than one company.
- MUST pass an explicit recency window on every search, and NEVER filter to postings with a named recruiter — most postings name none, and the company recruiter search is the fallback.
- MUST report each run's own reported billing; NEVER quote a list total before the one-company test.
- MUST apply only rewrites of lines that exist in the resume, and hold every addition for the seeker's confirmation; NEVER invent experience.
- MUST recount the message in code and flag any message over budget; NEVER trim one silently.
- MUST assemble each field from the step that produced it.
- NEVER send a message or connection request, apply, submit, or write to a CRM or applicant-tracking system — this ends at the drafts.

## Worked example

Ask: "Help me apply to these 12 companies for backend and platform engineering roles." Step 0:
`deepline preflight` passes. Step 1: 12 domains → 12 unique; roles *Backend Engineer, Platform
Engineer*; 30-day window (default, stated); 2 roles per company; LinkedIn URL given; resume as a
Google Doc read through the agent's Drive connector; drafts to `./applications/`; seeker
enriched once, name present. Step 2: no existing play; the two-search play
(posts step off) and the one-company test are approved; written, `plays check` passes. Step 3: test on one company — 2 postings of `jobCount` 5, none naming
a recruiter, 3 talent-acquisition staff found; the run reports its cost (this example's credit figures are the original Clay run's); both resumes and messages drafted.
Step 4: the two folders are shown with "1 credit for one company with 2 postings, 11 for the other 11 — what's
the most you want to spend?"; cap set at 15. Step 5:
11 runs in batches, totalling reported credits between batches; 9 companies with matches, 2 with
none (their `jobCount` shown), 17 postings, 17 resumes, 15 messages within budget, 2 flagged, and
every message addressed to a company recruiter, since no posting named one.
Step 7: 12 in · 10 with a recruiter-backed posting · 19 postings kept of 41 found · 19 resumes ·
61 lines applied, 14 to confirm · 17 messages in budget, 2 over · 0 failed · 12 credits of 15.
