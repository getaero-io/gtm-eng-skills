---
name: renewal-risk-radar
description: |
  Watch the accounts whose renewal is coming up and surface the ones that got riskier this week,
  each with its evidence, as a ranked digest waiting for you on Monday rather than requested. Per
  account it re-derives three independent risk signals: whether the champion changed employer,
  whether headcount fell, and whether the company went quiet. Runs unattended weekly as a Deepline
  play on a cron trigger; reads your CRM and public signals, writes
  only its digest, and never writes a record or contacts a customer. Use whenever someone asks: which of my
  renewals are at risk, build me a weekly churn-risk digest, tell me which accounts got riskier
  this week before their renewal, watch my renewing accounts for warning signs, or send me a
  Monday at-risk-renewals report. Do NOT use it for alerting the moment any champion changes jobs
  across your whole base (track-champion-job-changes), for positive buying signals like funding or
  expansion on a prospect list (monitor-buying-signals), for measuring one company's headcount
  trend on its own (headcount-growth), for auditing whether your CRM fields are accurate
  (account-health-audit), or for scoring or tiering accounts by fit (account-tier-scoring).
category: signals
personas: [revops, sales-leader]
mechanism: workflow
touches: writes-own-output
keywords: [job-change]
ported_from: clay-run/clay-skill-creator/skills/sung-jo/renewal-risk-radar
---

# Renewal-risk radar (surface what changed this week, not what is standing bad)

The insight: **renewal risk that matters is a *delta*, not a *level*.** An account that has been
small and quiet for a year is not news on the Monday before its renewal — you already priced that in.
An account that was fine last quarter and lost its champion, shed headcount, and went dark **this
week** is the one you did not see coming, and it is the only kind a weekly digest can add anything to.
So this skill is built to answer "what got worse recently", not "what looks bad right now" — and that
choice forces everything below it: each signal is measured against a recent window (or a prior
reading), misses are marked `unmeasured` rather than counted as "fine", and the rank is dominated by
how many signals *newly* fired, not by how big or small the account is.

A radar that ranks on the level instead quietly rebuilds a firmographic sort — the biggest or oldest
accounts float to the top every week — and labels it a risk signal. The whole point is the change.

> **Do not start a step before the steps above it have their answers.** If a declared input is
> missing, ask for it — never assume a default and continue. A numbered step below does not begin
> until every step above it has what it needs.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it means
saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **CRM + account object** | which CRM they run, and which object/field holds the account record. Read the schema and show the mapping you found (see Step 1) | no default — there is nothing to watch |
| **Renewal-date field** | the field that holds each account's renewal (or contract-end) date | no default — without it the book cannot be scoped or ranked by proximity |
| **Renewal window** | how far ahead a renewal counts as "coming up" — N days | ask. **90 days is defensible** as a first pass and must be stated in the output; never leave it unset, which silently means "the whole book" |
| **Champion identity** | how the champion is recorded per account — a contact role, a field, or a named contact | no default — the champion-change signal becomes `unmeasured` for accounts with no champion on file, and says so |
| **Headcount-drop rule** | how much of a fall counts — any decline, or ≥ X% vs the trailing reading | ask. Default: **any decline vs the company's own trailing-90-day headcount**, reported with both figures; flag the magnitude as your call |
| **Quiet rule** | what "went quiet" means — no public event (news / hiring / exec posts) dated in the last N days, ideally where the prior period had one | ask. Default: **no detectable public activity in the last 30 days**; flag the window as your call |
| **"This week" model** | whether a signal counts because it *newly appeared since last run* (stateful) or because its event *falls in a recent window* (stateless). This decides the play's architecture — see Step 2 | **confirmed: recent-window (stateless)** — a signal counts when its event falls in a recent window, so the run needs no stored state and a missed Monday costs nothing. Re-ask only if the installer wants strict since-last-week comparison |
| **Digest destination** | where the Monday digest lands — a Customer DB table / CSV export, a Slack channel you connect, or both | ask. Default: **the play's Customer DB table** the installer owns, plus a CSV export. Never a destination they did not name |
| **Schedule** | day and time the weekly run fires | ask. Default: **Monday 07:00 in the cron binding's timezone** |

All of these also travel in the output next to each account, so a reader knows what was measured and
against what.

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — your CRM's account and contact objects (renewal dates, owners, the champion contact),
  and public company signals through Deepline tools (job change, headcount, news/activity).
- **Writes** — its own output only: a ranked risk digest in a Customer DB table / CSV you own, and, if
  you connect one, a Slack delivery. Nothing is written back to your CRM.
- **Never** — writes, updates, deletes, or clears any CRM field; contacts a customer or champion in any
  way; enrolls anyone in a sequence; or moves your account data to any destination you did not name.

## Step 0 — Verify the platform, say where the work runs, and state the posture out loud

Run `deepline preflight --json`. `status: ok` with `auth.connected: true` → continue and say which
org, out loud. If the CLI is missing, run `npm install -g deepline && deepline auth register --wait auto`
and re-run — do not proceed without a connected org.

Say the posture to the installer before anything runs, in one breath: *this reads your CRM and public
signals and writes a digest to a table you own; it never writes to your CRM and never contacts a
customer.* That is the thing someone most wants to hear before pointing a standing, unattended job at
their customer base, and the end of the run is too late to hear it.

**Where the work runs, because that is what it costs.** The book-scoping (which renewals are in
window), the signal combination, and the ranking are arithmetic — do them in the agent / play code,
where they are free. Only the three per-account signal derivations are paid enrichment calls, one set
per in-window account per week. Price the run as `in-window accounts × (cost of the three calls)`, per
week, and see Step 3 for how to get the real per-call numbers.

## Step 1 — Collect the definition (interview; do not guess)

Show the installer the **shape** this skill needs, read their CRM's schema, show the mapping you found,
and ask only about what you could not match — never ask them to recite field names from memory.

The shape:

| Field this skill needs | What it is for |
|---|---|
| account id + name | the unit of the digest |
| renewal / contract-end date | scopes the book and sets renewal proximity in the rank |
| account owner | so the digest can be read by the right person (display only — never contacted) |
| champion contact | the person the champion-change signal is measured on |

Then: read the CRM object schema through the connected account, show which of their fields you mapped
to each row above and which you could not, and invite corrections. Gate the judgment calls that cannot
be looked up — the renewal window, the headcount and quiet rules, the "this week" model — and stop for
each rather than defaulting silently. See `references/build-notes.md` for how to ask which CRM and read
its schema without demanding a recital.

## Step 2 — Decide what "got riskier this week" means (this sets the architecture)

Two honest readings build differently. **This skill uses recent-window (stateless)** — the installer
confirmed it. The stateful alternative is documented so the trade is visible if someone wants to flip
it.

- **Recent-window (stateless) — the chosen model.** A signal counts if its event falls inside a recent
  window: the champion's job change is dated in the last N days, the current headcount reading is below
  the trailing-90-day figure, the last public activity is now older than the quiet window. Needs **no
  stored state**, so a missed weekly run costs nothing and re-runs are idempotent. It reads "this week"
  as "recently".
- **Compare-to-last-week (stateful) — not used here.** The play would store each account's signal
  state every run and flag a signal only when it *newly* turns risky since the prior run — truest to the
  literal words, and it suppresses a signal that has been true for months. The cost is real: it must
  persist and read back last week's snapshot per account, and a skipped or duplicated run has to be
  handled so a gap does not read as a change. Switch to it only if the installer asks for strict
  since-last-week comparison.

Whichever is chosen, **a signal the source could not measure is `unmeasured`, never a quiet "fine".**
Treating a coverage miss as "no risk" is how an at-risk account stays invisible the week it matters.

## Step 3 — Verify the signal tools and their real costs, live (never from memory)

Each of the three signals is one or more paid tool calls. Names and prices drift, so resolve them
against the live catalogue at build time and record what you find — do not carry a frozen list:

```
deepline --version
deepline tools search "job change" --json            # candidates per signal
deepline tools search "headcount growth" --json
deepline tools search "company news" --json
deepline tools describe <tool_id> --json             # the real inputs, and `pricing`
```

Identify every tool by its exact **tool ID**. Read `pricing.unit` before `pricing.creditsPerUnit`:
some tools are "Free through Deepline" because they run on the installer's own provider credentials
(they still bill the provider account), some charge **per result** rather than per call (pass an
explicit `limit`, or a build can understate cost many times over), and some are "calculated after
execution from returned usage" — price those from a pilot's measured charge, not a guess.
`references/build-notes.md` carries the starting routing table with tool IDs.

For each signal, four things must be written into the build (per `references/build-notes.md`): **what
runs** (the tool ID), **what goes in** (which field, from which declared input), **what to verify in the
response** (a call can succeed and return `{}` — gate on payload content, never on completion status),
and **what it costs** (the unit you are quoting, and that a miss can still bill).

The three signals, as jobs to route to a function — not vendors:

1. **Champion changed employer** — detect a job change for the champion contact. Input: the champion's
   identity from the declared input. Verify: the new employer differs from the account, and the change
   is dated (carry the provider's own signal date; consecutive weekly runs can otherwise re-report the
   same change). If no champion is on file → `unmeasured`.
2. **Headcount fell** — read the company's current headcount and its trailing-90-day figure. Input: the
   account domain. Verify: both figures are present (a `null` horizon is not a zero); compare as numbers,
   and prefer an exact count over a band string. Fire per the headcount-drop rule.
3. **Company went quiet** — detect recent public activity (news, hiring, executive posts). Input: the
   account domain. Verify: distinguish "no activity found" from "arm returned nothing"; fire per the
   quiet rule. A waterfall across activity sources is fine for the *boolean* and the *evidence*; never
   waterfall a *count* you intend to rank on.

## Step 4 — Free checks first, then a small real batch, then ONE gate

Everything free runs before anything bills: scope the book to the renewal window (a read + a date
comparison), drop accounts already renewed or out of window, and resolve which accounts even have a
champion on file. Name what that saves — an account out of window costs nothing to skip.

This skill is **read-only and reversible** (it writes only its own digest), so the batch is a **real
10-row batch**: run the three signals on ten in-window accounts and show the installer the output —
the fired signals, the evidence, and the rank. That catches a field mapped to the wrong column or an
arm returning noise, which no estimate reveals.

Then **one gate, carrying everything**: the 10-row output, the full weekly cost (`in-window accounts ×
the three calls`, with the unit stated and misses budgeted), exactly where the digest will be written,
and the ask to (a) run the full book once now and (b) install the weekly schedule. Then stop and wait.
There is no CRM-write gate because there is no CRM write — say so; do not invent a second halt.

## Step 5 — Build the weekly play

Because the digest must be waiting on Monday with no one present, this is a **Deepline play with a
`cron` binding**, not an agent loop that only runs while someone is in the conversation. Author it per
`references/build-notes.md`, which records the play shape and the traps to design around (every
signal column emits a row, including an explicit `unmeasured`; carry account fields forward
explicitly; a cron trigger receives `{}` unless its binding declares `input`). Run
`deepline plays check <file>.play.ts` before any run. Keep judgment — the combination and the rank —
in **play code** (`run_javascript` or the play's TypeScript), never a `deeplineagent` call; the agent
is for prose, never for comparison or routing.

## Step 6 — Rank the book, single rule, resolved in order

Emit a rank per in-window account. The default rule (flag it as the author's call — see the gap below):

1. **Number of signals fired**, most first (3 > 2 > 1 > 0), counting only `measured` signals.
2. Ties broken by **renewal proximity** — the sooner the renewal, the higher.
3. An account with **zero fired signals** is not in the risk digest; it is listed separately as
   "watched, no change this week", so the reader can see coverage rather than a silent omission.

Never emit a blended numeric "risk score" that hides which signals fired — the evidence per signal *is*
the deliverable. An account whose only fired signal is `unmeasured`-adjacent (e.g., headcount fell but
champion could not be checked) is ranked on what was measured and flagged for what was not.

## Step 7 — Deliver the digest, with coverage stated

Per at-risk account: the rank, the fired signals with one line of evidence and a date each, the renewal
date and days-to-renewal, the owner (display only), and any `unmeasured` signals named as such. At the
top of the digest, in one line: the renewal window used, the headcount and quiet rules used, the "this
week" model, and how many accounts were watched, how many fired at least one signal, and how many had a
signal that could not be measured. A reader must be able to see the shape of what is missing, not just
the hits.

## What this skill does not claim

- **Its logic came from an interview, not from a table that already ran.** No threshold here — the
  renewal window, the headcount-drop rule, the quiet window, the ranking rule — has been validated
  against a system with ground truth. They are the installer's stated intent, and the digest says so
  rather than implying a check that never happened.
- **The ranking rule (count-of-signals, then renewal proximity) is a default, not a measured optimum.**
  No study says three fired signals beats one severe signal; the installer can reweight, and should say
  they did.
- **The three signals are correlated and are not a complete risk model.** A champion move, a headcount
  fall, and public quiet do not add up to a churn probability, and the skill never presents them as one.
  Product usage, support tickets, and payment health — the strongest churn signals in most businesses —
  are not read here at all.
- **"Went quiet" measures *public* activity only.** A company can be busy privately and dark publicly;
  absence of news is weak evidence, and the digest labels it as a signal, not a verdict.
- **Signal freshness depends on the provider's own signal date, which can lag the run by weeks.** A
  change reported "this week" may have happened earlier; the evidence carries the provider's date, not
  the run date.

## What good looks like

- Every account in the risk digest names **which** signals fired, with a dated line of evidence for each
  — no bare "at risk" and no blended score standing in for the evidence.
- The top of the digest states the renewal window, the headcount and quiet rules, and the "this week"
  model, so next week's digest is comparable to this one.
- Accounts the sources could not measure are `unmeasured`, listed, and never counted as "fine"; accounts
  with no change are shown as watched-no-change, so coverage is visible.
- The rank is dominated by what *changed*, not by account size — sort the same book by headcount and it
  should look different.
- A thin week reads honestly: "42 renewals in window, 3 fired a signal, 5 unmeasured" is a good outcome,
  not a failure to pad.
- Nothing was written to the CRM and no customer was contacted — the digest is the only artifact, plus
  the schedule.

## Rules

- MUST scope to the renewal window before any paid call, and rank by what changed — NEVER rank on the
  account's level (size, age, ARR), which rebuilds a firmographic sort and calls it risk.
- MUST mark a signal the source could not measure as `unmeasured` — NEVER count a coverage miss as "no
  risk".
- MUST name each paid signal's tool ID, its inputs, what to verify in the response, and
  its cost, confirmed live against the installed version — NEVER carry a frozen function catalogue.
- MUST run the combination and rank in play code or the agent — NEVER put comparison or routing in an
  LLM (`deeplineagent`) step.
- MUST gate once, before the first paid call, showing the batch, the full weekly cost, and the
  destination — NEVER schedule a recurring paid run without that approval.
- NEVER write, update, clear, or delete a CRM field; NEVER contact a customer or champion; NEVER move
  account data to a destination the installer did not name.
- MUST carry the provider's own signal date and diff runs on it — NEVER re-report the same dated change
  as new each week.

## Worked example

Asked: *"which of my renewals are at risk, and tell me before the renewal, not after."* Renewal window
**90 days**, headcount rule **any decline vs trailing 90d**, quiet rule **no public activity in 30d**,
model **recent-window**, destination **the play's Customer DB table + Slack**, schedule **Monday 07:00**.

Book scoped free: 610 accounts → **48 in window**. Ten-row batch shown; installer corrects the champion
mapping (they store it as a contact role, not a field) and approves. Full run, 48 accounts × three
calls. Monday's digest:

| Rank | Account | Renewal in | Signals fired | Evidence |
|---|---|---|---|---|
| 1 | Northwind | 21 days | champion moved · headcount fell | champion now VP at a competitor (2026-08-19); 512 → 470 vs trailing 90d |
| 2 | Contoso | 40 days | headcount fell · went quiet | 1,180 → 1,090; no news/hiring since 2026-07-14 |
| 3 | Fabrikam | 66 days | champion moved | champion left, no successor on file (2026-08-22) |
| — | Acme | 12 days | *(champion `unmeasured` — none on file)* | headcount flat; not in risk list, flagged for missing champion |

Stated at the top: *48 renewals in the next 90 days; 3 fired at least one signal; 1 had a signal that
could not be measured. Ranked by signals fired, then by how soon the renewal lands. No CRM record was
written and no customer was contacted.*
