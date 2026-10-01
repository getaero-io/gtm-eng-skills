---
name: signal-sourcer
description: |
  Source net-new accounts from live buying signals with Deepline — no starting list:
  define the events that matter (funding, breach/incident, expansion, leadership
  change) plus ICP guardrails, and this play sweeps event-anchored news queries,
  harvests candidate companies from articles and roundups, resolves each name to a
  canonical domain, and re-qualifies every survivor against the ICP before it earns
  a row. Use whenever someone asks: find companies that just raised, source accounts
  hit by X event this week, who just got breached, expanded, or hired a new exec,
  build a list from trigger events, or signal-based prospecting with no seed list.
  Do NOT use it to watch a fixed account list for events
  (monitor-buying-signals), to source by static ICP alone (build-prospect-list), to
  track a known person's job change (track-champion-job-changes), or to score
  inbound leads (score-inbound-leads). Every delivered row carries a dated, sourced
  evidence line; a window with no qualified events is reported as zero, never padded.
ported_from: clay-run/clay-skill-creator/skills/clay/signal-sourcer
category: signals
personas: [sales-development, gtm-engineer]
mechanism: workflow
touches: read-only
keywords: []
---

# Signal-sourcer (signal-first net-new sourcing)

The insight: **signals create rows; qualification creates prospects.** List-first
plays start from accounts whose identity is given — enrichment is the only risk.
Here every row is BORN from a noisy recall channel (an event-vocabulary news query),
so the row itself must earn existence through three gates the naive build skips:
(1) a **real, dated event** — the channel's date stamps are crawl dates, not event
dates, and years-old articles surface inside a one-week window looking fresh;
(2) the **right entity** — a headline names a brand word, not a company; it must
resolve to a canonical domain with corroboration before anything downstream spends
on it; (3) **in-ICP and net-new** — an event proves a state change, never fit, and
an event at an account already in the user's book is monitoring, not sourcing.
The naive build queries news and ships the headline list: rumor-shaped rows.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Signal menu** | which event types create a prospect for them | ask, and test each one: would the event make someone buy sooner? If not it is trivia |
| **ICP guardrails** | vertical, geography, size band | **non-negotiable.** Without them every fired event qualifies and the play degenerates into news clipping |
| **Window and cap** | how recent counts, and how many qualified rows they want | **the past week is defensible**, as is 2–3 query variants per signal type. State both |
| **The book** | existing customers, open pipeline, named accounts | ask — net-new is defined against this list, and without it the play sources their own customers. If they want events on accounts they already know, that is a different skill and say so |
| **Owner mapping** | territory or segment routing rules | optional. Without it rows deliver unrouted, which is a fine outcome |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — your book, the signal menu and ICP guardrails you set, over the window you cap.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or sends outreach on a signal it sourced.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing: `npm install -g deepline &&
deepline auth register --wait auto`. Tell the user which org you're in and the balance.
Confirm the detector arms exist before promising them — read the live catalog, never
your memory of it: `deepline tools describe serper_google_search --json` (and the other
arms in `references/detector-mechanics.md`, which has the contracts). Note what the
company-search tools do NOT have: no event filters beyond static firmographics and
funding fields — the event-anchored news query is the general net-new arm here; for
funding specifically, the `prebuilt/funding-updates` radar feed is a structured
net-new arm. Standing versions graduate to Deepline monitors (industry radar), which
this play does not build.

## Step 1 — Collect the signal definition (interview; do not guess)

1. **Signal menu** — which event types create a prospect for THIS user (funding
   round, security incident, expansion/new market, leadership change, product
   launch…). For each: would the event make them buy sooner? If not, it's trivia.
2. **ICP guardrails** — vertical, geography, size band. Non-negotiable: without
   them every fired event qualifies and the play degenerates into news clipping.
3. **Window + cap** — how recent counts (default: past week) and how many
   qualified rows they want (cap query fan-out accordingly; default 2–3 query
   variants per signal type).
4. **The book (suppression set)** — existing customers, open pipeline, named
   accounts. Net-new is defined against this list; without it you will "source"
   their own customers. If they want events on KNOWN accounts, route to
   monitor-buying-signals instead — say so explicitly.
5. **Owner mapping (optional)** — territory/segment → owner rules if they want
   rows routed; otherwise rows deliver unrouted.

## Step 2 — State cost, get approval

Arithmetic before any spend, with prices read from `deepline tools describe <id>
--json` → `pricing`: (signal types × query variants) × the search arm's price
(`serper_google_search` bills per result returned, so set `num` and multiply; quiet
queries still bill whatever they return); plus per surviving candidate the
resolution/qualification enrichment (`crustdata_v3_company_identify` is free;
`crustdata_v3_company_enrich` is per result); plus optional premium corroboration
(structured funding/jobs lookups such as `predictleads_company_financing_events`,
per call) for a named shortlist only. State the worst case; wait for approval.

## Step 3 — Detector sweep (event-anchored queries)

Per signal type, run 2–3 query variants composed as **event vocabulary × ICP
qualifier** (e.g. funding vocabulary × vertical term; incident vocabulary ×
industry term), each windowed with the tightest relative bucket covering the ask
(`tbs: "qdr:w"` on `serper_google_search`). For funding, also page
`prebuilt/funding-updates` with `since` = window start — structured rows, still
subject to every gate below. Mechanics are in `references/detector-mechanics.md`.
Discipline per call:

- Quiet can mean the results field is ABSENT, not an empty list — gate on
  absence-of-events; read the first response to learn the shape.
- The window bounds when the index SAW the page, not when the event happened —
  treat every returned date as a claim to verify in Step 4, never as the event date.
- Query phrases are recall, not precision: a quoted round name matches adjacent
  rounds and finance-instrument notices. The query's job is candidate flow;
  precision comes from the gates.

## Step 4 — Harvest candidates (article → candidate, deterministic first)

Each result is an ARTICLE; the deliverable unit is a CANDIDATE = (company, claimed
event). Harvest with the source-class rules (full table in
`references/detector-mechanics.md`):

- **Direct event articles** → one candidate each.
- **Roundup/digest pages** → harvest EVERY named company as a candidate (for
  sourcing, roundups are a candidate-rich source — the inverse of the monitoring
  posture, where aggregator pages are dropped). Each harvested candidate carries
  the roundup as provisional source only; it must be corroborated per-company
  before delivery.
- **Social posts, forums** → drop (unverifiable, frequently garbled numbers).
- **Law-firm / investigation PRs** → keep the entity, demote the source; find the
  primary report during corroboration.
- **Dedupe into event clusters first, then date the cluster** — the same breach
  or round appears in 3–4 outlets in one sweep (sometimes naming parent,
  subsidiary, or no company at all): one candidate per event, sources merged on
  event fingerprint, best-primary kept.
- **Event-date derivation** — from the cluster's best source's own content, never
  the crawl stamp; incident signals date from the DISCLOSURE. Out-of-window drops
  with a note; no derivable date → `undated`, deliverable only if corroboration
  dates it.

## Step 5 — Resolve the entity (name → canonical domain)

A harvested name is a brand word with article context, not an identity. Resolve
each candidate with the resolve-company-domain discipline, and start with the FREE
arms: `crustdata_v3_company_identify` (by name — name-only matches are candidates, not
verified) and `free_simple_company_search` (read-only SQL over a ~35M-row company
corpus; filter on description keywords × location to disambiguate a collision name).
The returned records carry name, domain, size band, and location — often enough to
kill an off-ICP candidate before any credit is spent. A paid lookup can return
confident wrong entities on collision names,
and a plausible knowledge-prior domain can belong to a same-brand entity elsewhere —
BOTH are candidates, not answers: corroborate the chosen domain (enrichment/search
echo: name words + registrable label, never the TLD) before promoting. No corroborated domain → the candidate is delivered in the
exceptions tail as `unresolved`, never guessed. Generic brand names ("Moss",
"Bolt") are exactly where wrong-entity rows are minted — partial-stem matches get
a stated reason or get dropped.

## Step 6 — Qualify (the gate that makes it a prospect)

On the RESOLVED entity's own enrichment fields (never the article's claims):

- **ICP gates** — size band, geography, industry vs Step 1 guardrails. Band
  strings, not numbers; enrichment presence ≠ liveness — corroborate liveness for
  anything acted on immediately.
- **Net-new gate** — normalized-domain match against the book; matches are
  excluded AND recorded (`suppressed: existing customer`), with a pointer to
  monitor-buying-signals for watching them.
- **Event corroboration (shortlist only)** — for rows the user will act on today,
  confirm the claimed event: a structured per-company lookup where one exists for
  the signal type (`predictleads_company_financing_events`,
  `predictleads_company_job_openings`, per call) or the primary source
  (`contextdev_get_web_scrape_markdown` fetches an article URL, free);
  roundup-sourced and law-firm-sourced candidates REQUIRE corroboration before
  delivery. **Degraded mode** (the article URL won't scrape — paywall, bot wall,
  removed page — and incident-type signals have NO structured lookup):
  cross-outlet agreement counts — ≥2 independent outlets carrying the same event
  fingerprint corroborates; a candidate with one derivative source and no
  reachable primary drops with `uncorroborated — source unreachable`, and the
  delivery says which corroboration mode ran.

Failed rows drop with reasons, never silently. Zero qualified rows in a window is
a valid, reportable result — an honest zero beats a padded list.

## Step 7 — Deliver and route

Row: `company · domain · signal type · evidence line (≤140 chars, from the
source) · event date (+ how derived) · source URL(s) · ICP verdict · net-new check
· owner (if mapped)`. Summary: queries run, articles seen, candidates harvested,
per-gate drop counts, credits spent (measured from `deepline runs get <run-id> --full
--json` where the sweep ran as a play; declared estimate otherwise). Then the routing
note: this play delivers a POINT-IN-TIME sweep; a standing version of the same ask
should graduate to Deepline monitors (industry radar, monitor-triggered plays) —
offer the hand-off with the arithmetic, never rebuild it as a re-scraping loop.

## What good looks like

- The expert reads the **drop ledger first**: candidates killed per gate (stale
  date, wrong entity, off-ICP, in-book, uncorroborated) prove the gates ran. Zero
  drops means news clipping, not sourcing.
- Every delivered row is verifiable in one click, and its event date has a stated
  basis (in-text date / primary source), never a crawl stamp.
- Duplicate events collapsed: one row per (entity, event), sources merged.
- The common mistake: shipping the headline list. The second-worst: "sourcing"
  the user's own customers because nobody asked for the book.

## Rules

- MUST state cost and get approval before the sweep; quiet queries bill too.
- MUST derive event dates from content, NEVER trust the channel's relative date
  stamps; out-of-window and undated-uncorroborated candidates are dropped/tailed.
- MUST resolve every candidate name to a corroborated domain before enrichment
  spend or delivery; unresolved candidates go to the exceptions tail.
- MUST re-qualify against ICP + the book on resolved-entity fields; suppressed
  and dropped rows are recorded with reasons, never silent.
- MUST report an empty window as zero qualified rows — no padding, no widening
  the window silently.
- NEVER auto-send outreach, write to a CRM, or stand up a permanent re-scraping
  loop — deliver the sweep; graduate standing watches to Deepline monitors.

## Worked example

Ask: "Find healthcare companies hit by a data breach this week — we sell incident
response; 200+ employees, US only. Here are our 60 current accounts." Cost stated:
2 query variants × 10 results × the search arm's per-result price, free identify,
plus `crustdata_v3_company_enrich` per surviving candidate — worst case named, approved.
Sweep returns 10 articles → harvest: 7 candidates after (entity, event) dedupe
(one breach appeared in 3 outlets — merged), 1 social post dropped, 1 "breach
tracker" roundup harvested for 2 additional names flagged corroboration-required.
Resolution: 6/7 corroborated domains; "Meridian Health" stays `unresolved` (three
same-name orgs, article context insufficient). Qualification: 1 dropped off-ICP
(38 employees), 1 suppressed (already a customer — noted for
monitor-buying-signals), roundup-harvested names corroborated via primary
notices — 1 confirmed, 1 uncorroborated → dropped with reason. Deliver 3 qualified
net-new rows, each: domain, "breach exposed 310K patient records", event date from
the notification filing, source links, size/geo verdict, owner per territory map.
Drop ledger shows all 4 kills. Offer: make it standing via a Deepline
`industry_mentions` monitor instead of weekly re-sweeps.
