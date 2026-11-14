---
name: track-champion-job-changes
description: |
  Build a recurring Deepline watcher over your champions — past buyers, power users, and
  key contacts at existing customers — that tells you the moment one changes jobs, then
  turns each move into two plays: FOLLOW the mover into their new company (your warmest
  possible outbound) and BACKFILL the seat they left (protect the existing account).
  Use whenever someone wants to: track job changes for champions, get alerted when a champion
  or past buyer moves companies, follow champions to their new company, detect when a key
  contact leaves a customer account, turn customer alumni into pipeline, or monitor buying
  contacts for role changes. Runs on the Deepline CLI: a contact job-change monitor or a
  scheduled play.
  Do NOT use for general CRM contact cleanup or re-verifying a whole list's emails and titles
  (that is a contact-refresh job), or for sourcing net-new prospects by persona (people search).
  It sends nothing and writes nothing to your CRM without explicit approval.
category: signals
personas: [account-executive, sales-leader]
mechanism: workflow
touches: writes-own-output
keywords: [job-change]
ported_from: clay-run/clay-skill-creator/skills/clay/track-champion-job-changes
---

# Track champion job changes

A champion who moves is the warmest pipeline you will ever get — someone who already bought
or used your product, now sitting inside a new account with fresh budget authority and a
honeymoon window in which tooling decisions are open. And every move is TWO plays, not one:
the new company becomes a target (FOLLOW), and the vacated seat at your existing customer
becomes a relationship risk (BACKFILL). Most teams run neither because nobody is watching.
This skill builds the watcher: a standing Deepline job-change feed (or a scheduled play)
that checks each champion's current employer, flags real moves, and produces a play-ready
digest.

Deepline Monitors are an access-gated beta — run `deepline monitors status --json` and say
which route (monitor or scheduled play) you are on before building, so the user can
calibrate expectations.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The champion list** | where champions live today, and per row a name, a profile URL and the account they are known from | if there is no profile URL, an email works and gets resolved. A list that is not yet a re-checkable file or table needs to become one, or nothing can run on a schedule |
| **What counts as a champion** | past buyer, power user, or deal contact on a closed-won | ask, and **do not expand it silently** — this defines the list |
| **The ICP filter for the follow play** | industry, size, region | ask. A mover whose new company sits outside ICP gets logged, not pursued |
| **Cadence** | how often the list is re-checked | **weekly is defensible**, monthly for smaller lists. State which. On the monitor route the feed is continuous and cadence only sets when the digest is cut |
| **Destination** | a CSV, a Customer DB table they read, or a Slack channel they own | the conversation is the fallback, and nothing is pushed anywhere they have not named |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — your champion list and your definition of a champion, plus the job-change sources it checks.
- **Writes** — only its own output, to the destination you name (a CSV, a Customer DB table, a
  Slack channel, or the conversation). It never changes a record that already exists.
- **Never** — sends outreach automatically — the digest ends at play-ready.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, run
`npm install -g deepline && deepline auth register --wait auto`, then re-run preflight.
Confirm which org you are signed into and tell the user before touching anything. Then run
`deepline monitors status --json`: `has_access: true` makes the monitor route available;
otherwise use the scheduled-play route.

## Step 1 — Collect the inputs (interview the user; do not guess)

1. **The champion list.** Where do champions live today? A CRM export (CSV), a CRM
   (HubSpot `hubspot_search_objects`, Salesforce `salesforce_list_contacts`), or a Customer DB
   table. Minimum viable row: name + LinkedIn URL + the account (domain) you know them from.
   If there's no LinkedIn URL, ask for email instead — the check will resolve it. Inspect a
   CSV with `deepline csv show --csv <path> --summary`, never by reading it into context.
2. **What counts as a champion.** Past buyer? Power user? Deal contact on closed-won?
   This defines the list; don't expand it silently.
3. **The ICP filter for the FOLLOW play.** Industry, size, region — a mover whose new company
   is outside ICP gets logged, not pursued.
4. **Cadence.** Weekly is the sensible default; monthly for lists under ~200.
5. **Where the digest goes.** A CSV, a Customer DB table the user reads, or a Slack channel
   the user owns (`deepline notifications slack channels --json` lists connected ones).

## Step 2 — Plan the watcher and get approval

Two routes; price both from live `describe` before recommending one.

- **Monitor route (continuous).** One `deepline_native.contact_job_changes` monitor per
  champion (`tool: deepline_native.contact_radar`, payload `radar_type: contact_job_changes`,
  `profile_url`, `domain`, optionally `email` / `full_name`). Billing is a recurring
  subscription — 3.5 Deepline credits per tracked contact per month at the time of writing,
  charged on deploy and every 30 days (confirm with
  `deepline tools get deepline_native.contact_job_changes --json`). Events land in the
  Customer DB stream `deepline_native.deepline_native_contact_job_changes`; a bound play
  turns them into the digest. Follow the `deepline-monitors` skill for check / dry-run /
  approval / read-back.
- **Scheduled-play route (batch).** A play with a `cron` binding that runs
  `prebuilt/job-change-check` over the champion CSV (`deepline plays describe
  prebuilt/job-change-check --json`). Its rows carry `job_change.status`, `job_change.date`,
  `job_change.new_company`, `job_change.company_domain`, `job_change.new_title`,
  `validation_status` and `miss_reason`. The underlying `job_change` tool is listed at
  1.96 credits/result; read its pricing note in `describe` for whether non-moves bill.

Present this plan, mapped to the user's inputs, and wait for approval before building:

```
TRIGGER: contact_job_changes monitor events  OR  cron (weekly) over the champion list
         + a manual run on 3-5 rows for testing
  1. [detect]      Current employment per champion. Resolution order matters:
                   (a) LinkedIn URL on file → job_change / prebuilt/job-change-check;
                   (b) no URL → name + last-known company domain (contact_full_name +
                       company_domain), or datagma_job_change_detection (fullName +
                       companyName) as a second arm;
                   (c) email-only LAST (weakest coverage; fails often).
                   → current employer name, domain, title, change date
  2. [code]        Extract + compare, deterministically — never an LLM. In play code
                   (or run_javascript), normalize both domains and emit flat string
                   fields: verdict (current / moved / unverified), evidence with dates,
                   new-company domain/name/title/start. Use non-empty sentinels ("none")
                   so an empty response cannot be read as "no change".
  3. [branch]      Route on the verdict string:
                   → current: digest row, end
                   → unverified: "could not verify" digest row, end
                   → moved: continue. Genuinely ambiguous cases (rebrand/acquisition
                   suspicion) belong in the digest flagged for human review.
  4a. FOLLOW branch (real move):
      [tool]        Enrich the NEW company: crustdata_v3_company_enrich
                    (domains: [new_domain], fields: ["basic_info","headcount"])
      [code]        ICP gate — outside ICP: log "moved, out of ICP", end
      [agent]       deeplineagent (with jsonSchema): compose the play — champion-arrival
                    note anchored on the shared history (which product, which account,
                    when), plus 2-3 suggested buying-committee titles (company_titles on
                    the new domain gives the real roster, free)
  4b. BACKFILL branch (real move, runs in parallel):
      [tool]        Find people at the OLD account matching the vacated title/persona:
                    company_titles (free) to pick exact titles, then
                    crustdata_v3_person_search filtered on employer + those titles
      [agent]       Pick the most likely successor + note why; flag "seat vacated"
  5. [output]      One digest row per champion: verdict, evidence, plays → CSV export
                   (deepline runs export), Customer DB table, and/or slack_post_message
```

Confirm every tool's live shape with `deepline tools describe <id> --json` before wiring
it, run `deepline plays check <file>.play.ts`, and show the user the plan. Where more than
one tool can do a step (several person-search and job-change tools exist), list the options
with their `describe` prices and let the user choose.

Build notes:
- Column resolvers call `rowCtx.tools.execute({ id, tool, input, description })`; read
  declared getters first, raw payload only when no getter carries the field.
- Gate on the presence of an actual employer value, never on `status: completed`.
- A cron trigger receives `{}` unless the binding declares `input` — put the champion CSV
  path / table name and cadence arguments in the binding's static `input`.
- After publishing a cron play, add a failure notification
  (`deepline notifications add ... --for play.cron.failed`) so a broken weekly run is seen.
- Keep agents on a cheap model while wiring, then graduate only the steps that write prose;
  comparisons and routing stay in code — an LLM asked to compare domains may wander off to
  the web instead.

## Step 3 — Test small, then scale

1. Run 3–5 champions through (`deepline plays run ... --debug` on a sliced CSV) — include at
   least one you know has NOT moved (the no-change path must terminate cheaply) and, if
   possible, one known mover.
2. Walk the user through each row's path (`deepline runs get <run-id> --full --json`). Fix,
   re-test.
3. Before the first full run or monitor deploy: compute cost from the live prices (per
   champion per check on the play route; per champion per month on the monitor route,
   plus FOLLOW/BACKFILL enrichment on movers only), read the pilot's actual charge,
   check `deepline billing`, state the total, and get explicit approval.
4. Publishing the cron binding or deploying monitors is a paid, standing change — get an
   explicit yes for it separately from the pilot.

## What good looks like

- **Join and compare on domains, never company-name strings.** Names differ across sources
  ("Initech Ltd" vs "Initech"); domains don't. If the enriched employer has no domain,
  validate one before deciding anything.
- **A move verdict must trace to evidence in the provider payload** — quote the old and
  new employer with dates in the digest. Never infer a move from a name mismatch alone, and
  never fabricate a change to have something to report. Empty or errored detection = "could
  not verify", not "no change" and not "moved" — and watch for the sneaky version: a call
  can complete with an empty payload. Gate on the presence of an actual employer value,
  never on the run status.
- **Use the current-role start date.** A mover who started < 12 months ago is in the
  honeymoon window — tooling decisions are open. Rank the FOLLOW digest by recency.
- **Both plays evaluated for every real move.** A digest that only follows movers and never
  flags vacated seats is half the value.
- **The FOLLOW note leans on the shared history** — which product, at which account, roughly
  when. "Congrats on the new role" with no history is generic outbound wearing a costume.
- The common mistake: treating every domain mismatch as a move. Acquisitions and rebrands
  produce mismatches constantly; the verdict step exists because of them.

## Rules

- MUST get explicit user approval before the first full run, any monitor deploy, any CRM
  write, and any cron publish — and NEVER send outreach automatically; the digest ends at
  play-ready.
- MUST re-check `deepline billing` before scaling a run to the full list.
- NEVER drop a champion silently: every input row lands in the digest as verified-current,
  moved (with plays), out-of-ICP, or could-not-verify.

## Output

Per scheduled run, one digest with a row per champion:
`champion · old account · verdict (current / moved / could-not-verify) · evidence · new company ·
new title · ICP fit · FOLLOW note draft · suggested committee titles · BACKFILL successor ·
seat-vacated flag`
plus a summary line: champions checked, moves found, plays generated, rows needing human review.

## Worked example

Input: 120 champions exported from the CRM as "Champions — Closed Won", weekly cadence,
ICP = B2B software 100–5,000 employees, digest to a CSV plus a Slack summary.
First test run of 5: 4 verified current, 1 real move — Jordan Lee, former Head of RevOps at
longtime customer acme.example, now VP RevOps at northfield.example (2,300-person B2B software firm,
in ICP). Digest row: verdict MOVED with dated job-change evidence; FOLLOW note referencing the
three years Jordan ran your product at Acme; suggested committee: CFO, Director of Sales Ops;
BACKFILL: Priya Shah, current Director of RevOps at Acme, flagged as likely successor;
seat-vacated alert on the Acme account. Cost stated from live prices before the full run:
monitor route 120 × 3.5 = 420 credits/month, or play route up to 120 × 1.96 ≈ 235 credits
per weekly check, plus FOLLOW/BACKFILL enrichment on movers only; user picked a route and
approved before the first full run.
