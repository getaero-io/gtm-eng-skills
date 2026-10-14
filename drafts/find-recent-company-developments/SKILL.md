---
name: find-recent-company-developments
description: |
  Summarize what changed at a company inside a lookback window you choose — new leadership who
  started in that window, merger, acquisition and divestiture events, technology transformation
  programs, procurement notices and contract awards, and verified news items — each dated, sourced
  and standardized, by building (once) and running a Deepline play that resolves the company from a
  LinkedIn URL or domain, finds new joiners, and runs the author's four research prompts verbatim
  through `deeplineagent`. Use whenever someone asks: what's new at this account, brief me on this company before
  the call, recent developments at these companies, who joined their leadership recently, has this
  company done any M&A lately, any news on this account in the last quarter, or build me an account
  research brief. Do NOT use it for firmographics or headcount (enrich the company instead), for
  finding a contact's email or phone, for funding-round history as a number, for tracking a named
  person's job change, or for writing the outreach itself — it ends at a dated, sourced summary per
  company that a person reads.
ported_from: clay-run/clay-skill-creator/skills/lorcan-o-rourke/find-recent-company-developments
category: research
personas: [account-executive, sales-development]
mechanism: workflow
touches: writes-own-output
keywords: []
---

# Find recent company developments (fix the window first, then research inside it)

The insight, in the author's prompts: **an account development is only useful if it is dated and
sourced, and only real if it falls inside the window you asked about.** Every prompt says the same
thing three ways — *"only include results dated on or after"* the start date, *"every item must be
traceable to a real, accessible source with a direct URL"*, and *"do not pad with low-confidence or
speculative entries"*. So the skill computes the window before anything runs, hands the same start
date to every research pass, and drops any event that arrives undated or before it. The new-leadership
list is scoped the same way: people whose current role started inside the window.

The judgment lives in four research prompts, carried **verbatim** in `references/prompts.md` with
their output schemas and the author's combine-and-format rules. This skill's job is to stand them up
as a Deepline play, run it per company, and hand back the standardized summary — not to reword them.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The companies** | one company LinkedIn URL or domain per company — pasted, or **a CSV file** with a column holding either (name the column if there are several). A name column is optional and never used to identify a company | no default — a company name alone is refused, because it cannot be resolved to one organization |
| **Leadership seniority** | the title words that count as leadership for the new-joiner search, comma-separated | **the author's default is `Chief, CEO, CFO, CTO, COO, CRO, CMO, CIO, President, VP, Vice President, Director, Head`** — confirm it with the installer before the first run and say it was used |
| **Lookback** | how many months back to look | no default — ask. The window decides what counts as "recent" for every event type, and the author's function required it |
| **Event types** | which of the four research passes to run: M&A, news, procurement, technology transformation | **all four is the default**, matching the author's function; say so, and offer to drop passes the installer does not need, since each is a paid research run |
| **Where the summary goes** | the conversation, a Markdown file per company, or **a CSV** with one row per company (and one per event, if asked) | the conversation |
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

- **Reads** — the companies and lookback you supply, and each play run's step outputs (the resolved company, its recent joiners, and the four research passes' results, which read public web pages during the run).
- **Writes** — one Deepline play file of its own (`recent-company-developments.play.ts`, created once, reused after), its runs and their Customer DB dataset, one provenance comment at the top of that play file, and the summary, to the conversation or the files you name.
- **Never** — edits a play, table or record it did not create, writes to a CRM, contacts anyone, or reports an event without a date and a source URL.
- **Halts** — Step 2 write-approval, Step 2 spend-approval, Step 4 sample-review, Step 4 spend-approval

## Step 0 — Verify Deepline is working, and say what this does

Say this first, as two sentences: *this builds one Deepline play (or reuses it if it is already
there) and runs it once per company to resolve the company, list who joined inside your window, and
research four kinds of developments; it hands back a dated, sourced summary and never writes anywhere
else.*

Run `deepline preflight --json`. If it fails, name what is wrong — the CLI missing, signed out, or no
balance — give the one fix (`npm install -g deepline && deepline auth register --wait auto`, or
`deepline billing` for the balance), and **stop**. Tell the user which workspace (`auth.org_name`) you
are in.

This skill builds and runs its play **per the `deepline-plays` skill** (and
`references/plays-sdk-reference.md` under `deepline-gtm`) — read it before Step 2 and follow it for
every play shape (`.withColumn` steps, `ctx.tools.execute`, `plays check`, runs and export). If the
`deepline-gtm` skill is not available, say it is required and stop.

## Step 1 — Collect the inputs (interview; do not guess)

1. **Companies** — LinkedIn URLs or domains, pasted or from a CSV the installer points you at (read
   the column they name, or the one column that holds URLs or domains; `deepline csv show --csv
   <path> --summary` to see the columns without loading rows). Normalize: lowercase, strip `www.`,
   query strings and trailing slashes; dedupe. Refuse a row that has only a name, and say why. Keep
   the other CSV columns so the output CSV can carry them through unchanged.
2. **Lookback** in months. Compute `lookback_start_date` yourself: today's date minus that many
   months, as `YYYY-MM-DD`, and carry today's date as `run_date`. Both go into every run and into
   the output, permanently.
3. **Event types** — confirm all four, or drop some.
4. **Leadership seniority** — show the author's default title list and ask the installer to confirm or
   edit it; it is the whole definition of "leadership" for the joiner search.
5. **Where the summary goes** — conversation, Markdown files, or CSV.

The spend cap is asked in Step 4, once there is a measured cost to set it against.

## Step 2 — Find or build the play (one gate first)

**Look before building.** `deepline plays list` and `deepline plays grep "recent company
developments"` and look for **recent-company-developments**. If it exists, read it with `deepline
plays get <name> --source --out ./recent-company-developments.play.ts` and check it has the steps
below with the prompts and model in `references/prompts.md`; if so, reuse it and skip to Step 3. If
it exists but differs, say how, and ask whether to use it as-is or build a fresh one alongside —
never edit it.

**Before creating anything, one message:** the play name and workspace, the step list below, that a
provenance comment will be written at the top of the play file so it can be traced back to this
listing, and that the next step runs it on **one** company — whose cost cannot be stated exactly
beforehand, because four `deeplineagent` research passes bill by the model usage and searches they
make on the open web. Give the declared prices for the two data steps, read from `deepline tools
describe <id> --json` (`pricing`) on this machine. For reference only: the author's original test
(2026-09-28, one large company, 12-month window) ran on Clay and reported **5 Clay data credits and 6
action executions in 80 seconds**; that is not a Deepline price. **Wait for an explicit yes.**

Read each tool's real inputs with `deepline tools describe <id> --json` before wiring — parameter
names below were read on 2026-09-30 and can drift. Output field names were not shown by `describe`;
read them off the first real response and fix the mapping before Step 3 completes.

The play's steps, in order:

| # | Step | Tool | What it does |
|---|---|---|---|
| 1 | **Input** | play input | `company_identifier` (required; LinkedIn URL or domain), `lookback_months` (number), `lookback_start_date` (`YYYY-MM-DD`, computed in Step 1), `leadership_titles` (the confirmed list) — one company per run, or one CSV row per company |
| 2 | **Resolve company** | `crustdata_v3_company_identify` (free) | `domains: [<domain>]` or `professional_network_profile_urls: [<linkedin url>]`, whichever the identifier is. Read the company name, website domain and LinkedIn company URL from `company_data.basic_info` in the first response. This is how a domain or a LinkedIn URL becomes the name, domain and URL the prompts need; a missing name ends the run for that company as *not resolved* |
| 3 | **Find new leadership** | `crustdata_v3_person_search` (0.02 credits per returned result; empty pages free) | `filters`: an `and` group of `experience.employment_details.current.company_website_domain` `=` step 2's domain; `experience.employment_details.current.start_date` `=>` `lookback_start_date`; an `or` group with one `experience.employment_details.current.title` `(.)` condition per confirmed leadership title (`(.)` is an all-words match, so one keyword per condition); and `(!)` conditions on the same field for `Office of` and `Assistant`. `limit: 10`. Read each person's name, current title, location, LinkedIn URL and current start date, and `total_count`. **Only 10 people are fetched while `total_count` is the true total**, so the output always says "N shown of M" and never presents the 10 as the whole list. The author's function carried only the two exclusions; the title filter is the author's later correction, made when this skill was written, so "leadership" means the confirmed list and nothing else |
| 4 | **M&A events** | `deeplineagent` | prompt 1 in `references/prompts.md`, model `openai/gpt-4.1-mini`, `jsonSchema` = that prompt's output schema; inputs `company_name`, `company_domain` ← step 2, `lookback_start_date` ← input |
| 5 | **News events** | `deeplineagent` | prompt 2, same model and pattern; inputs as above plus `company_linkedin_url` ← step 2 |
| 6 | **Procurement events** | `deeplineagent` | prompt 3, same model and pattern; inputs as step 4 |
| 7 | **Transformation events** | `deeplineagent` | prompt 4, same model and pattern; inputs as step 4 |

Steps 4 to 7 all follow step 3 and are independent of each other; when the installer dropped an event
type in Step 1, do not build that step. Substitute every `{{variable}}` in each prompt from the step
named in `references/prompts.md`, and pass the prompt's output schema as `jsonSchema` so the result
comes back structured at `toolResponse.raw.result.object`. Confirm `openai/gpt-4.1-mini` is in the
live AI Gateway catalog before the first run (it was on 2026-09-30); if it is not, **say so and ask
which to use** — never substitute one silently. Leave `maxToolCalls` at its default unless a test
run shows a pass stopping short.

Run `deepline plays check
./recent-company-developments.play.ts` and fix every error before running.

## Step 3 — Test on one company

Run the play on one company with `deepline plays run ./recent-company-developments.play.ts --input
'{...}' --debug` carrying the four inputs, then read `deepline runs get <run-id> --full --json`:

- **cost** — the run's reported billing is this run's actual spend. Use it, **never the workspace
  balance**, which moves with everyone else's work.
- **values** — each step's output is in the run's dataset (`deepline runs export <run-id> --out
  sample.csv`, or the Customer DB table the run names). Check values, not status: a research pass
  that completed with an empty array found nothing, which is a real answer; one that completed with
  prose instead of schema-shaped JSON is a build error to fix (schema, wiring), never a prompt to
  reword.

Then run Step 5 on this one company so the sample in Step 4 is the finished summary.

## Step 4 — Show the sample, set the cap, then run the rest

**One message:** the company's full summary in the output shape below, the measured cost for one
company, that cost × the remaining companies, and one question: *what is the most you want to spend
on this list?* Say plainly that research depth varies by company, so later ones can cost more or less
than the first. **Wait** — this is the look at what the passes actually found that no estimate
reveals, and the spend decision in the same breath.

Then run the remaining companies as one CSV through the same play, or a few runs at a time. Keep a
running total of each finished run's reported credits; **stop before the next batch would pass the
cap** and say how many companies remain.

## Step 5 — Combine, window-check and format, in code

Read each research step's structured object. Then apply the author's rules from
`references/prompts.md` exactly, in code and never by judgment: concatenate the four arrays in the
stated order, keep only events whose `eventDate` is on or after `lookback_start_date`, drop any whose
`eventDate` contains `@`, sort newest first, and render the *Events summary* and *New leadership*
blocks in both the plain and Markdown shapes given there. An event with an empty `eventDate` fails
the window test and is dropped; count how many were dropped for that reason and say so. Build the
leadership block from *Find new leadership* only, and every event field from the research step that
produced it.

## Step 6 — Deliver

Per company: the resolved name, domain and LinkedIn URL; run date and lookback start date; the
leadership block headed "N shown of M who joined in the window with a leadership title"; the events block; and a count line — joiners found, events kept, events dropped as
undated or out of window, passes that returned nothing. Then the list-level summary: companies in,
resolved, with at least one event, with at least one joiner, failed runs, and Deepline credits spent
(the sum of each run's reported billing) against the cap. Then the answer-sheet offer from
*Declared inputs*.

## Representative output

### Company brief

**Northwind** · northwind.example · linkedin.com/company/northwind
Run date 2026-09-28 · window from 2026-06-28 (3 months)

New leadership (2 shown of 2 who joined in the window with a leadership title)
- **Dana Whitfield** — Chief Revenue Officer, Austin, TX
  [LinkedIn](…) | Started: 2026-08-01
- **Sam Ortiz** — VP Engineering, Remote
  [LinkedIn](…) | Started: 2026-07-15

Developments (4 kept · 1 dropped as undated)
- **Acquisition — 2026-09-12** Northwind acquires Fabrikam Analytics for $40M [Source](…)
- **Company Announcement — 2026-09-03** Northwind launches Northwind Cloud 3.0 [Source](…)
- **Transformation Program — 2026-08-20** Northwind selects SAP S/4HANA for global ERP replacement [Source](…)
- **Contract Award — 2026-07-02** Northwind awarded 5-year logistics contract by Contoso [Source](…)

Passes with nothing in the window: none. Procurement returned 1, news 2, M&A 1, transformation 1.

### List summary

| Companies in | Resolved | With events | With new joiners | Failed runs | Credits spent / cap |
|---|---|---|---|---|---|
| 25 | 24 | 17 | 11 | 0 | 61.2 / 80 |

## What this skill does not claim

- The leadership title list is a keyword match on current titles, so "Director of Photography" counts and a founder titled only by name does not; no seniority taxonomy was used, though `crustdata_v3_person_search` exposes `experience.employment_details.current.seniority_level` if the installer wants one.
- How complete the four research passes are was never measured — each returns what its searches found, and a quiet pass is not proof that nothing happened.
- Event dates come from the sources the passes found; a source that misdates an event misdates it here.
- The original Clay graph was run end to end once, on one large company over a 12-month window: 5 Clay data credits, 6 action executions, 80 seconds, 11 events found of which 2 fell before the start date and were dropped. The Deepline play has not been run; nothing has measured its cost, a list, a small company, or a short window.
- The joiner list is capped at 10 by the search `limit`; the total is reported beside it, but who the other joiners are is not. Paging with `cursor` fetches more at 0.02 credits per person.
- The joiner search reads a person index, not a live profile; a hire not yet indexed is missed.
- Whether an event the passes report is true is only as good as the source they cite; the author did not verify the test run's events against the sources.
- Whether `gpt-4.1-mini` is the right model for these prompts was never tested against another; it is what the author ran. The author ran it as Clay's research agent; `deeplineagent` searches with a different tool set (Serper, Exa, Firecrawl), so pass completeness on Deepline is unmeasured.

## What good looks like

- Every event carries a date on or after the start date and a source URL; nothing undated survives.
- Every joiner carries a start date inside the window and a profile URL.
- A company with no events says so, per pass, rather than vanishing or being padded.
- The same company run twice with the same window returns the same joiners; the events may differ only by what the web now says.
- The common mistake: rewording the prompts "to fit the skill". They are the product; the skill is the wiring.

## Rules

- MUST use the four prompts in `references/prompts.md` verbatim, on the model listed there; NEVER reword, merge or substitute a model silently.
- MUST compute `lookback_start_date` before the first run and pass the same value to every pass; NEVER let a pass run without a window.
- MUST drop any event that is undated or dated before the start date, and say how many were dropped.
- MUST look for an existing **recent-company-developments** play before building, and NEVER edit a play, table or record this skill did not create.
- MUST get explicit approval (Step 2) before creating the play or running it, and a spend cap (Step 4) before running more than one company.
- MUST resolve each company from a LinkedIn URL or domain through Resolve company; NEVER accept a name alone as the identifier.
- MUST confirm the leadership title list with the installer before the first run, and pass it to the joiner search on every run.
- MUST combine, filter, sort and format in code, from the step that produced each value.
- NEVER contact anyone or write to a CRM — this ends at the summary.

## Worked example

Ask: "Brief me on these 25 accounts — what's changed in the last 3 months?" Step 0: preflight ok,
`deepline-gtm` present. Step 1: a CSV of 25 domains → 24 unique; lookback 3 months, start date computed; all four
passes; the default leadership list confirmed; summary to the conversation and a CSV. Step 2: no existing play; the seven-step play and the
one-company test are approved; built, `plays check` clean, attribution written and read back. Step 3: test on
one company — resolved, 2 joiners of 2, 5 events across the passes; run reports N credits. Step 4:
the brief is shown with "this one cost N credits, about 23 × N for the rest — what's the most you
want to spend?"; cap set. Step 5: 23 runs in batches, totalling reported credits between batches;
combined, windowed, formatted. Step 6: 24 in · 24 resolved · 17 with events · 11 with joiners · 0
failed · credits spent against the cap.
