---
name: alert-reps-on-account-signals
description: |
  Turn a rep's target-account list into Slack alerts with Deepline — load the accounts into a
  Customer DB table, watch every account with three Deepline company-radar monitors (news and
  web mentions, new leadership hires at C-suite, VP and director level, and job postings), and post
  one Slack message per event into a channel the rep names, mentioning the account owner. Built once
  per list as a source table, three monitor Fleets and one monitor-triggered alert Play, then it runs
  unattended as events arrive. Use whenever someone asks: alert me when my accounts hire a VP, ping
  Slack when a target account raises money, watch my account list for news, tell me when these
  companies post jobs, set up account signals for my territory, or build a Slack alert on my named
  accounts. Do NOT use it to research one account right now (that is a lookback summary, not a
  watch), to track a named person's job change, to enrich or score the list, to write the outreach,
  or to alert on web or topic intent — it ends at a Slack message per event that a person acts on.
ported_from: clay-run/clay-skill-creator/skills/lorcan-o-rourke/alert-reps-on-account-signals
category: signals
personas: [account-executive, sales-leader]
mechanism: workflow
touches: writes-records
keywords: [job-change]
---

# Alert reps on account signals (watch the list, post the event, name the owner)

The insight, in the author's words: **a rep should not have to go looking — when something happens
at an account they own, the event should find them where they already are, with the account and
the owner named in the first line.** So the list is loaded once, the watches run on their own, and
every event becomes one Slack line shaped like *"@owner — a key new hire has been filled at Acme:
Jane Doe, VP Sales."* Nothing here scores, enriches or writes outreach; the rep decides what to do.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The account list** | a CSV with one row per target account and a column holding the company domain (a company LinkedIn URL is resolved to a domain first) | no default — nothing to watch |
| **List name** | a short label for this list, e.g. the rep's name or territory; it names the source table, the Fleets and the alert Play | no default — ask; two lists with the same label would merge |
| **Slack channel** | the rep's own channel for these alerts, by name — one channel per rep, by the author's design; always ask for it, never assume one. Slack must be connected to Deepline and the channel visible to it (`deepline notifications slack channels --json`) | no default — the alert step cannot be built; the monitors still run and their events stay readable in the Customer DB |
| **Mention** | the rep's own Slack member ID (the `U…` value from their profile) to put at the front of every alert, if they want the ping | none — alerts carry no mention |
| **Leadership seniority** | which new hires count as leadership, from the radar's seniority values (`Owner`, `CXO`, `Vice President`, `Director`, `Manager`, …) | **the author's default is c-suite, vp, director, head** — maps to `CXO`, `Vice President`, `Director`; "head" has no seniority value (see Step 3). Confirm it and say it was used |
| **Job posting titles** | title words a posting must contain to alert, e.g. the roles the rep's product serves | none — **every** posting at every watched account alerts and bills, which at a large account is many per week; say so before accepting it |
| **News topics** | which news topics alert | **the author's default is Fundraising, Investment, Initial Public Offering, Merger & Acquisition, Executive Appointment, New Product Launch, Business Expansion** — confirm it and say it was used. The mentions radar has no topic filter, so topics filter alerts in the Play, not billing (Step 3) |
| **History** | whether to backfill events from before the watch starts (30, then 60, then 90 days max) | **forward-only is the default** — monitors detect events after deployment; a historical step is a separate priced approval |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the CSV you supply, the Slack channels Deepline can see, and each monitor event as it arrives.
- **Writes** — **one Customer DB table** (`storage.target_accounts_<list>`, one row per domain), **three monitor Fleets** (one per radar type, one monitor per account), one Play of its own (the alert Play) with a provenance line in its description, and **one Slack message per event** to the channel you name, through the org's connected Slack.
- **Never** — deletes or edits a table, monitor, Fleet or Play it did not create, writes to a CRM, or messages anyone outside the named channel.
- **Vendor-specific** — Slack is load-bearing for the alert step. Without a connected Slack the monitors still run and events remain readable with `deepline db query`, but no alert is sent.
- **Halts** — Step 2 write-approval, Step 3 spend-approval, Step 4 sample-review

## Step 0 — Verify Deepline is working, and say what this does

Say this first, as three sentences: *this loads your account list into a Deepline table, deploys
three monitors per account that watch for leadership hires, job postings and news, and publishes one
Play that posts a Slack message per event to your channel; it writes to Deepline and Slack and
nowhere else, and it never deletes anything.*

Run `deepline preflight --json`. If it fails, name what is wrong — the CLI missing or signed out —
give the one fix (`npm install -g deepline && deepline auth register --wait auto`), and **stop**.
Tell the user which org you are in and the balance.

Then two free checks, before any interview:

- **Monitors.** `deepline monitors status --json`. If `has_access` is false, monitors are not
  available on this org and the skill cannot do its job; say so (the Deepline team grants access)
  and stop. Exit 3 is auth, exit 5 is config/server — diagnose those, don't call them "no access".
- **Slack.** `deepline notifications slack channels --search <channel> --json`. A returned channel
  means Slack is connected and the channel is visible; keep its **id** — `slack_post_message` takes
  the channel id (`C…`), not the name. No match: say so, give the fix (connect Slack to Deepline and
  add the app to the channel), and offer to continue with the watches only.

This skill builds through the deepline-gtm skill's monitor and Play recipes
(`recipes/deepline-monitors.md`, `recipes/deepline-plays.md`) — read them before Step 2 and follow
them for every CLI shape (Fleets, monitor checks, sqlListeners bindings, publishing).

## Step 1 — Collect the inputs (interview; do not guess)

1. **The CSV** and which column holds the domain or LinkedIn URL. Normalize domains (lowercase, strip
   scheme, `www.`, paths, query strings, trailing slashes) and dedupe. LinkedIn-only rows resolve to a
   domain with `crustdata_v3_company_identify` (free) via `professional_network_profile_urls`; a row
   with neither identifier, or that doesn't resolve, is listed as skipped, never guessed from a name.
2. **List name**, the **Slack channel** (ask for it by name, every time), and whether to **mention**
   the rep.
3. **Leadership seniority**, **job posting titles**, **news topics**, **history** — show each default
   and ask for a yes or an edit. Seniority values must come from the radar's enum
   (`deepline tools get deepline_native.company_new_hires --json` → `payload_schema`); a value outside
   it fails `monitors check`.

## Step 2 — Load the list into the Customer DB (one gate first)

**Look before building.**
`deepline db query --sql "select table_name from information_schema.tables where table_schema='storage'" --json`
— an existing `target_accounts_<list>` table means the list was loaded before; say so and ask whether
to add to it. `deepline monitors list --json` and `deepline plays list --json` — look for Fleets and an
alert Play named for this list and reuse them if they match.

**Before creating anything, one message:** the table name, that N domains will be inserted, the three
Fleets and the alert Play that follow, and that nothing is deleted. **Wait for an explicit yes.**

Then create and fill the table, keyed on domain so a duplicate cannot enter:

```bash
deepline db query --sql "create table if not exists storage.target_accounts_northwind (domain text primary key, company_name text, owner_slack_id text)"
deepline db query --sql @insert_accounts.sql   # INSERT ... ON CONFLICT (domain) DO NOTHING
deepline db query --sql "select count(*) from storage.target_accounts_northwind" --json
```

Compare the count to the deduped CSV row count and report created vs skipped. **The domain key is the
dedupe**: the Clay version of this skill found a workspace holding 20 account records for one
`nvidia.com` row (author's test, 2026-09-28), each of which would have billed and alerted separately;
a primary key on the normalized domain makes that impossible here.

## Step 3 — Validate three Fleets, price them, then one gate to deploy

**Look before building.** `deepline monitors list --json` — a monitor of the same radar type already
watching a domain on this list answers the job for that domain, and a second one doubles the spend;
the deploy dry-run also lists existing monitors that cover the scope. Then write one Fleet per radar
type over the table (`deepline monitors fleets init`), each payload templated on `{{domain}}`:

| Watch | `radar_type` | Payload filters | Price (2026-09-30, re-read with `tools get`) |
|---|---|---|---|
| Leadership hires | `company_new_hires` | `seniorities` ← the confirmed list (default `["CXO","Vice President","Director"]`) | 1.75 credits per accepted event |
| Job postings | `company_job_openings` | `job_titles` ← the confirmed titles as a radar expression, e.g. `"Data" OR "Analytics"` (omit only if the installer accepted "every posting") | 1.25 credits per accepted event |
| News and mentions | `company_mentions` | none — the radar has no topic filter | 1.5 credits per accepted event |

```bash
deepline monitors fleets init northwind-new-hires \
  --source storage.target_accounts_northwind --key domain \
  --tool deepline_native.company_radar \
  --payload '{"domain":"{{domain}}","radar_type":"company_new_hires","seniorities":["CXO","Vice President","Director"]}' \
  --out northwind-new-hires.fleet.json
deepline monitors fleets sync --file northwind-new-hires.fleet.json --dry-run --json
```

The dry-run shows the plan and the credits due without changing state; the real write is the same
command with `--wait` instead of `--dry-run`. For a handful of accounts, single monitors via
`deepline monitors check` / `deploy --dry-run` are fine.

Two filter facts to say plainly. **"Head of" is not a seniority value**: to include it, use
`job_titles` (`"Chief" OR "VP" OR "Vice President" OR "Director" OR "Head of"`) instead — `job_titles`
overrides `seniorities`, so send one form, never both. **News topics don't reduce cost**: every
mention the radar accepts bills; the topic list only decides which ones reach Slack (Step 4).

**Then one message:** the three Fleets as validated, the account count, the per-event prices from the
dry-run, that total volume is unknown because it depends on what happens at the accounts, the history
choice (forward-only unless a priced 30-day step was approved), and the delivery line
(`Delivery: one Slack message per alerted event to #<channel>`). **Wait for an explicit yes**, then
sync each Fleet and read it back (`deepline monitors fleets get <id> --json`; spot-check one member
with `deepline monitors get <key> --json`: `status: active`, the expected domain, radar type and
filters). **Monitors detect changes after deployment**: say plainly that the first alerts arrive as
events are discovered, and that hires and postings that predate the watch do not fire unless a
historical step was approved.

## Step 4 — Build the alert Play, test one message, then publish it

`deepline plays list --json` — look for **account-signal-alerts-<list>**; reuse it if it matches.
Otherwise start from the generator and edit it:

```bash
deepline plays bootstrap monitor-triggered --tool deepline_native.company_radar \
  --stream company_new_hires --name account-signal-alerts-northwind --out alert.play.ts
```

Give it three `sqlListeners` (one per stream: `company_new_hires`, `company_job_openings`,
`company_mentions`, all `operations: ['INSERT']`). **The stream tables are shared by every monitor in
the org**, so each listener must restrict to this list: `where: { after: { domain: { in: [<the
list's domains>] } } }` (regenerate when the list changes), or look the row's domain up in
`storage.target_accounts_<list>` in the handler and return early when absent. The handler builds one
line and calls `slack_post_message` (`channel` ← the channel id from Step 0, `text` ← the line).

The message, one line per event type, in Slack markdown, with the mention first when the rep asked
for one (`<@U…>`), else nothing:

- new hire — `<@owner> A key new hire has been filled at *<account>*: <full_name>, <title>. <profile_url>`
- job posting — `<@owner> *<account>* is hiring: <job_title> (<country>). <job_url>`
- news — `<@owner> News at *<account>* — <topic>: <mention_content, first 140 chars>. <mention_url>`

**The row is the event.** The stream columns are published in the monitor contract
(`deepline tools get deepline_native.<radar_type> --json` → `streams[].columns`); on 2026-09-30:

- `company_new_hires`: `domain`, `full_name`, `first_name`, `last_name`, `profile_url`, `title`, `start_date`, `country`, `discovered_at`
- `company_job_openings`: `domain`, `job_title`, `job_url`, `job_posted_at`, `job_description`, `job_source`, `country`, `discovered_at`
- `company_mentions`: `domain`, `mention_content`, `mention_url`, `mention_channel`, `mention_posted_at`, `author_name`, `author_profile_url`, `discovered_at`

`<account>` comes from `company_name` in the source table (fall back to the domain). The mentions
stream carries no topic: classify `mention_content` against the confirmed topic list with keyword
rules (monitor-buying-signals' `references/signal-menu.md` has the vocabulary) and post only matches;
log non-matches to a dataset rather than dropping them silently. Record the fields you used in the
Play's description.

**Test before publishing.** `deepline plays check ./alert.play.ts`. Then post one test message with
the exact line format and real values — from a stream row if any exist
(`deepline db query --sql "select * from deepline_native.deepline_native_company_new_hires where domain in (...) limit 1" --json`),
else clearly marked sample values — via
`deepline tools execute slack_post_message --input '{"channel":"C…","text":"…"}'` (free). Confirm in
the channel that it arrived and reads as above. **Show the installer the message** and wait for a yes.
Then `deepline plays publish ./alert.play.ts` so the listeners go live, and — in an internal/test org,
or with the installer's explicit approval — `deepline monitors test <key> '<sample_payload from
monitors get>' --json` on one monitor per radar type (validation only: it writes no row and dispatches
no Play, so it proves the event shape, not the Slack path). Stop — from here the monitors and the alert Play run unattended.

## Step 5 — Deliver

One summary: the list name, accounts loaded (inserted vs skipped), the table and its count, the three
Fleets with their filters and per-event prices, the channel, the mention rule, the test message as
posted, and where to look — `deepline monitors health --json` for delivery and silent monitors,
`deepline db query` on the three stream tables for events, `deepline plays triggers --json` and
`deepline runs` for alert runs. Then the answer-sheet offer from *Declared inputs*.

## Representative output

### Setup summary

| List | Accounts loaded | Table count | Watches | History | Channel | Mention |
|---|---|---|---|---|---|---|
| Northwind territory | 49 inserted · 1 skipped (no domain) | 49 (matches deduped CSV) | Leadership hires (CXO, VP, Director) · Job postings (titles: *Data, Analytics*) · News (7 topics, filtered in the Play) | forward-only | #northwind-dana | @Dana |

### Slack alert

```
@Dana Whitfield  A key new hire has been filled at *Contoso*: Priya Raman, VP Data Platform. linkedin.com/in/…
```

### Where to look

- Monitor health: `deepline monitors health --json` — delivery state, deactivation reasons, silent monitors
- Events so far: `deepline db query --sql "select * from deepline_native.deepline_native_company_new_hires where domain in (...) order by discovered_at desc limit 20" --json` (same for `_company_job_openings`, `_company_mentions`)
- Alerts sent: `deepline plays triggers --json`, then `deepline runs get <run-id> --full --json`

## What this skill does not claim

- The logic comes from the author's interview, not from a system that already ran; nothing has checked it in production.
- The author's tests (2026-09-28) were on the Clay version of this skill: a real new-hire payload, two Slack test messages, and the duplicate-record finding. This Deepline port was built from the published monitor contracts (2026-09-30) and has not produced an alert end to end; the stream columns are read from the contract, not from an observed row.
- How many alerts a list produces per week was never measured; a large account with no posting-title filter, or a well-covered account on the mentions radar, can produce many — and each accepted event bills.
- Whether a new hire is truly leadership depends on the radar's seniority classification of the title.
- Slack delivery is only confirmed by the test message; a channel Deepline later loses access to fails at `slack_post_message` until someone checks the Play's runs.
- The default news topic list is the author's reading of "news and fundraising"; it was never tuned against alert volume.

## What good looks like

- Every alert names the account and, when the rep asked, mentions them.
- A rep can read the channel for a week and see only hires at the chosen seniority, postings for the chosen titles, and news on the chosen topics.
- Nothing pre-existing was edited or deleted; the only new objects are the table, the Fleets and the Play.
- No monitor was deployed before the per-event prices and unknown volume were stated and agreed.
- The common mistake: deploying monitors before the table count is confirmed, and paying to watch an empty or wrong list. The second: an alert Play with no domain filter, posting every other team's events into this rep's channel.

## Rules

- MUST validate every Fleet with a dry-run and deploy only after the installer sees the per-event prices and says yes.
- MUST confirm the table's domain count against the deduped CSV before any monitor is deployed.
- MUST restrict every listener to this list's domains; the stream tables are org-wide.
- MUST take the alert message's fields from the stream's published columns, and say when they were not yet observed on a real row.
- MUST look for an existing table, monitors, Fleets and Play for this list name before building, and NEVER edit any it did not create.
- MUST post only to the named channel, through the org's connected Slack.
- NEVER write to a CRM, enrich, score or draft outreach — this ends at the alert.

## Worked example

Ask: "Set up Slack alerts on my 50 target accounts — new execs, jobs, funding." Step 0: signed in;
monitors available; Slack connected, `#northwind-dana` resolved to its id. Step 1: CSV with a `domain`
column; list name *Northwind territory*; mention @Dana; seniority default confirmed (CXO, VP,
Director); posting titles *Data, Analytics*; news topics default confirmed; forward-only. Step 2:
`storage.target_accounts_northwind` created; 49 domains inserted, 1 row skipped (no domain); count 49,
matching. Step 3: three Fleets validated by dry-run, per-event prices shown with unknown volume, yes,
synced and read back. Step 4: alert Play with three listeners filtered to the 49 domains → Slack; one
test message posted with sample values and approved; published. Step 5: summary as above, and the
answer-sheet offer.
