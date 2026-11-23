---
name: competitive-intelligence-radar
description: |
  Run a standing radar on a named competitor set with Deepline — sweep each competitor's
  public exhaust (announcements, pricing and positioning changes, leadership hires,
  funding/M&A, hiring patterns) in bounded windows and deliver a classified intel
  digest: what changed, the evidence, and the move each change opens for you. Use
  whenever someone asks: watch our competitors, what did competitor X announce this
  month, track competitor pricing or product launches, competitor intel digest for the
  sales team, tell me when a rival raises or loses an exec, or set up competitive
  monitoring. Do NOT use it to watch YOUR OWN target accounts for buying signals
  (monitor-buying-signals), to source net-new accounts from events (signal-sourcer),
  for a one-time deep dive on a single company (company-research-brief), or for a
  point-in-time tech snapshot of one domain (detect-tech-stack). Every item ships a
  dated source; facts are separated from interpretation; a quiet week is reported
  quiet, never padded.
category: signals
personas: [sales-leader, marketing]
mechanism: workflow
touches: read-only
keywords: []
ported_from: clay-run/clay-skill-creator/skills/clay/competitive-intelligence-radar
---

# Competitive intelligence radar

The insight: **competitor intel is only actionable as a dated delta plus the move it
opens — and facts must never blend into reads.** The naive build re-summarizes the
competitor's website and greatest-hits funding news every week: archive re-heated as
"intel," the same Series B surfacing each sweep, opinion woven through fact until the
sales team can't tell which sentence is sourced. This radar diffs bounded windows over
public exhaust, classifies each event by what it lets YOU do (displacement window,
positioning counter, roadmap tell), and keeps two registers — FACT (dated, sourced,
quoted) and READ (your interpretation, labeled as such). One fabricated or stale item
read aloud in a deal costs the whole digest its trust.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The competitor set** | names plus canonical domains | resolve and corroborate any name given. **Five is a defensible cap** and must be stated: a twenty-competitor radar produces noise nobody reads |
| **The angles that matter** | which changes are actionable for this team: pricing, launches, logo wins, leadership churn | **launches, pricing, exec changes and funding is a defensible default**, stated as such |
| **Window and cadence** | the first-sweep lookback, then sweep-to-sweep | **30 days is defensible** for the first sweep; record the sweep date in every digest |
| **Audience** | sellers, founders, or marketing | ask — it changes the classification, not just the wording. Sellers want displacement ammo, founders want roadmap tells |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the competitor set you name and the public sources it watches.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or reports a movement it cannot cite.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, run
`npm install -g deepline && deepline auth register --wait auto` and re-run preflight. Tell
the user which org you're in and the balance it reports. Confirm the sweep arms exist with
`deepline tools describe <id> --json` before promising them (`references/radar-arms.md` — the news arm is the backbone; the hiring
and product-page arms are optional escalations with their own costs).

## Step 1 — Collect the radar definition (interview; do not guess)

1. **The competitor set** — names + canonical domains (resolve and corroborate any
   name you're given; a wrong domain poisons every downstream read). Cap it (default
   5; a 20-competitor radar produces noise nobody reads).
2. **The angles that matter to THEM** — which changes are actionable for this team:
   pricing/packaging? product launches? enterprise-logo wins? leadership churn?
   Default: launches + pricing + exec changes + funding/M&A.
3. **Window + cadence** — first sweep lookback (default 30 days), then
   [last sweep → today]. Record the sweep date in every digest.
4. **Audience** — sellers want displacement ammo; founders want roadmap tells;
   marketing wants positioning shifts. The classification table
   (`references/classification.md`) maps events to each.

## Step 2 — State cost, get approval

Per sweep: competitors × query variants × the news arm's live per-call price (quiet
queries bill the same); optional arms priced separately in `references/radar-arms.md`.
Read every price from `deepline tools describe <id> --json` (`pricing`), state the worst
case, wait for approval, then build the sweep as one play and reuse it (a `cron` binding
makes it standing; a `deepline_native.company_mentions` monitor per competitor is the
event-driven alternative, priced per accepted finding).

## Step 3 — Sweep (entity-anchored, windowed)

Per competitor, run the news arm (`serper_google_search` with a `tbs` date bucket such
as `qdr:w` / `qdr:m`, or the free `contextdev_post_news_search`) with entity-anchored
queries (competitor name × angle vocabulary), windowed to the sweep bucket. Discipline per call — the full
mechanics and traps are in `references/radar-arms.md`:

- Quiet can come back as a missing results field rather than an empty list — gate on
  absence of events, not on shape; quiet still bills.
- The channel's date stamps are crawl dates, not event dates — derive every event's
  date from content before it enters the digest; out-of-window items are dropped
  with a note, and a years-old story can surface looking fresh.
- Name-boundary discipline: the competitor's name as a prefix of a longer org name
  (or a product/vessel designation) is a different entity — drop, don't report.
- Dedupe into event clusters across outlets before classifying; one launch covered
  by four blogs is ONE item.

## Step 4 — Classify: FACT, then READ

Each surviving event gets, in this order (rules + full taxonomy in
`references/classification.md`):

1. **FACT line** — what happened, event date (with derivation basis), source URL,
   a ≤140-char quote from the source. No adjectives.
2. **Event class** — launch / pricing / positioning / exec-change / funding-M&A /
   customer-win-loss / hiring-pattern / other. `other` goes to the digest tail,
   never promoted.
3. **READ line (labeled)** — the implication for YOUR motion, from the class →
   implication mapping: pricing change → displacement window at their renewals;
   security-exec departure → objection ammo has a shelf life; VP-AI hire →
   roadmap tell, 2-3 quarters out. Reads are marked `READ:` and never cite
   themselves as fact.

## Step 5 — Deliver the digest

Per competitor: `act-on-now items (FACT + READ) · logged items · quiet note if
quiet`, then a set-level summary: sweeps run, events found by class, credits spent
(measured from `deepline runs get <run-id> --full --json` or `deepline billing`). Unchanged/quiet competitors are one line
each — quiet is a result. Offer the standing cadence, and re-verify the competitor
set quarterly (competitors get acquired; domains change hands).

## What this skill does not claim

- No evaluation has been run yet — this skill is the packaging canary, and its first full evaluation runs through the real submission pipeline.
- Arm mechanics were observed on Clay's equivalent actions (2026-08) and mapped to Deepline
  tool IDs by contract, not re-probed live; re-verify the traps on the first sweep.

## What good looks like

- A rep can read one act-on-now item aloud in a deal and survive the prospect
  checking the link.
- FACT and READ never blend: every interpretive sentence is labeled and every
  factual sentence is dated and sourced.
- No repeats across sweeps — the window boundary is the dedupe.
- The common mistake: shipping a beautifully-written competitor essay with three
  unsourced claims in it. The second-worst: a 20-competitor radar nobody reads —
  small set, sharp angles, every week.

## Rules

- MUST anchor every item on a content-derived event date inside the window; NEVER
  trust the channel's date stamps or report an undated item as current.
- MUST separate FACT (dated, sourced, quoted) from READ (labeled interpretation);
  NEVER ship a read disguised as a fact.
- MUST dedupe into event clusters before classifying; MUST report quiet as quiet.
- MUST state sweep cost and get approval; quiet queries bill too.
- NEVER auto-send, auto-post, or write conclusions into a CRM — the digest is the
  deliverable; acting on it is the user's move.

## Worked example

Ask: "Watch our 4 main competitors — we sell workflow automation; pricing moves and
launches matter most, monthly." Cost stated: 4 competitors × 3 angle queries on
`serper_google_search` at its live per-result price (0.02 credits/result at the time of
writing, `num: 10`) ≈ 2.4 credits/sweep — approved. First sweep, 30-day window: 31 articles → 9 event clusters
after dedupe (one launch covered by 5 outlets = 1 item). Digest highlights:
`kirivale.example — FACT: usage-based pricing tier announced 2026-07-28 (in-text
date), source linked, "teams under 50 seats now start free" — READ: displacement
window at their per-seat renewals; lead with switching-cost calculator.` One
competitor quiet (one line). One story dropped with a note: a 2024 funding
retrospective surfacing with a fresh crawl stamp — out of window by content date.
Tail: 2 `other` items (conference talks). Spend read back from the run. Next sweep window
starts 2026-08-12.
