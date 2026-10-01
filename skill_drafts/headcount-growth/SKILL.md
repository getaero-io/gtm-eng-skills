---
name: headcount-growth
description: |
  Measure a company's headcount growth with Deepline — employee count plus percent
  change across 1/3/6/12/24-month windows, bucketed (shrinking / flat / growing /
  high-growth / hyper-growth) with a trajectory read and honest unverifiables.
  Use whenever someone asks: how fast is this company growing, get headcount
  growth for these accounts, which of these companies are hiring or shrinking,
  or filter my list to high-growth companies. Works per company from a
  LinkedIn company URL (best) or domain;
  names resolve to a domain first. It verifies the answer is about the RIGHT
  company, never ships a percentage without its base counts, and reads two
  windows so a recent reversal isn't hidden by a 12-month average. Do NOT use
  it for job postings (Company Job Openings territory), funding or expansion
  events behind the growth (monitor-buying-signals), broad firmographics
  (enrich-account-list), or person-level moves (track-champion-job-changes).
  Built on crustdata_v3_company_enrich (headcount field group) plus entity verification.
ported_from: clay-run/clay-skill-creator/skills/clay/headcount-growth
category: enrich
personas: [revops, sales-leader]
mechanism: workflow
touches: read-only
keywords: []
---

# Company headcount growth

The insight: **a growth percentage is a trajectory claim built on three silent
assumptions — right entity, meaningful denominator, and a window that isn't
hiding a reversal — and the bare enrich call returns a confident number when any of
them is wrong.** +40% over 12 months can mean a 3-person company hired one
engineer, a different company than the one you asked about, or a real grower
that started shrinking last quarter. And a miss is success-shaped: the call
completes, and the only signal is an empty `matches` array. This skill wraps
one cheap tool call with the checks that make its number safe to act on.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **An identifier per company** | a company profile URL for the high-accuracy route, or a domain for the lower-accuracy one | route each row by what it has; the two run as separate calls (the tool takes exactly one identifier type per call). Name-only rows resolve the domain first, and if the resolution returns a profile URL, harvest it — that row then rides the accurate route for free |
| **Which windows** | near-term momentum, sustained trend, or both | **3 and 12 months read together is defensible** and must be stated: one window alone is a number, not a trajectory |
| **Cost ceiling** | Deepline credits | dedupe companies first, state list × the live price from `deepline tools describe`, and say that obscure and very small companies miss more |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — an identifier per company and the windows you choose, via headcount sources.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or reports growth outside a window you declared.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline &&
deepline auth register --wait auto`, then re-run. Tell the user which org you're in.
Confirm the growth tool and read its live price and input schema:
`deepline tools describe crustdata_v3_company_enrich --json` (free). Field names
and prices drift (`references/growth-mechanics.md`); the describe output is the
contract.

## Step 1 — Scope (identifiers, windows, cost)

1. **Identifier per company** — LinkedIn company URL is the high-accuracy
   arm; domain is the documented lower-accuracy arm (route each row by what it
   has — the arms run as separate calls; the tool accepts exactly one
   identifier type per call).
   Name-only rows: resolve the domain FIRST (resolve-company-domain — a wrong
   domain here silently measures the wrong company), and if the resolution's
   corroboration payload carries the company's LinkedIn URL, HARVEST it — the
   resolved row rides the high-accuracy arm for free. `crustdata_v3_company_identify`
   (free) returns the matched profile URL for a domain.
2. **Windows that matter** — near-term momentum (3/6-month) vs. sustained
   trend (12/24-month); default to reading 3 + 12 together (`qoq` + `yoy` in
   the payload; the reversal
   check). One window alone is a number, not a trajectory.
3. **Cost + coverage, stated before spend** — 0.8 Deepline credits per returned
   result at the time of porting (read the live `pricing` from describe);
   obscure SMBs and very small companies miss more. Whether a no-match call
   bills is not stated in the pricing block, so read the first run's billing
   (`deepline runs get <run-id> --full --json` for a play) before scaling.
   Dedupe companies first, state list × cost, get approval.

## Step 2 — Run the tool (surface by list size)

Per unique company, run `crustdata_v3_company_enrich` with
`fields: ["basic_info","headcount"]` — one arm per row:
`professional_network_profile_urls` = LinkedIn company URL, or `domains` =
domain. Without `fields` the headcount section is not returned at all, and the
row reads as a miss. Small lists (≤20): `deepline tools execute` per company.
Larger lists: a play over the CSV with one `.withColumn` per arm
(`references/growth-mechanics.md`). Pilot 3 rows first, read the payload and
billing, then run the rest. `akta_headcount_trends` is an alternative arm (one provider per
cohort, never both); `prebuilt/engineering-team-size` sizes the engineering
function only and is a level, not a growth rate.

## Step 3 — Read the payload honestly (three shapes)

- **Hit**: numeric `headcount.total` + per-window `growth_percent` and
  `growth_absolute`. FIRST check the entity echo: `basic_info.name`,
  `basic_info.professional_network_url` and `basic_info.primary_domain` name the
  company the tool actually matched (plus `confidence_score`) — if they don't match the company you
  asked about, the row is a wrong-entity hit; flag it, don't report its
  numbers.
- **Per-window nulls inside a hit are normal** (a `growth_percent` key that is
  null or absent; short-window and old-window data are often missing even for
  major companies) — a null window is "no
  snapshot", never zero growth.
- **Miss**: the call completes with an empty `matches` array, or a match
  without a `headcount` section. Verdict `unverifiable` — never "flat", never
  0%. Count whatever the run billed for it.

## Step 4 — Interpret (denominator, bucket, trajectory)

- **Denominator gate**: report the base counts next to every percentage
  (base = `headcount.total` − `growth_absolute.<window>`; or read it off
  `headcount.timeseries`). A
  base under ~50 employees never headlines a percentage — `+300%` on 3→12
  people ships as "grew 3→12 (micro-base)", flagged, not as hyper-growth.
- **Bucket** (12-month default): `<0` shrinking · `0–10%` flat · `10–30%`
  growing · `30–100%` high-growth · `>100%` hyper-growth.
- **Trajectory** (the direction-change check, both ways): compare the short
  window against the long one — growing 12-month + shrinking 3-month =
  `reversing`; growing year + a last quarter running well ahead of the year's
  pace = `accelerating`; flat 12-month + strong 3-month = `inflecting up`.
  Say which windows produced the verdict, and read the backdated counts for
  dip-and-rebound shapes the window percentages smooth over.
- **Measurement caveat, always shipped**: counts are professional-profile
  presence, not payroll — hourly, offshore, and contractor-heavy workforces
  undercount. A frozen flat-line on a company whose liveness is in doubt is
  a dead-company artifact, not stability (enrichment-style data persists for
  dead/acquired companies).

## Step 5 — Deliver

Per company: `identity (asked → matched echo) · employee_count · per-window
counts + % · bucket · trajectory · flags (micro-base, wrong-entity,
window-gaps) · verdict (measured / unverifiable)`. Plus the roll-up: companies
in, measured, unverifiable, wrong-entity, Deepline credits measured vs declared
(misses included). Every input company lands somewhere.

## What good looks like

- **Percentages never travel without their base counts** — no micro-base
  booms in the headline.
- **The entity echo was checked on every hit** — a wrong-entity number is
  worse than no number.
- **Unverifiable is honest and costed** — misses are reported as coverage
  (with any credits they billed), never coerced to "flat" or dropped silently.
- **Trajectory over snapshot** — rows read from two windows; a 12-month
  average never hides a last-quarter reversal.
- The common mistake: treating the tool's confident percentage as the
  answer. It answers for whatever entity it matched, at whatever base size,
  for one window — the wrapper's whole job is checking those three.

## Rules

- MUST resolve name-only rows to a domain before measuring; MUST pass the
  LinkedIn URL when available (domain is the lower-accuracy arm).
- MUST check the entity echo (`name`/`url`) on every hit; a mismatched echo is
  a wrong-entity flag, never a reportable number.
- MUST treat an empty `matches` array as `unverifiable` (counted) — never
  zero growth; MUST treat per-window nulls as missing snapshots, never 0%.
- MUST ship base counts with every percentage and flag micro-bases; MUST read
  ≥2 windows before calling a trajectory.
- MUST hold one provider per cohort — growth percentages from two providers are
  different measurements, not a waterfall; NEVER present profile-count growth
  as payroll truth.
- Batch: dedupe companies first, state cost, pilot, get approval.

## Worked example

Ask: "Which of these 30 accounts are actually growing? CSV has name, domain,
some LinkedIn URLs." Scope: dedupe 30 → 28; 9 rows LinkedIn+domain, 16 domain
only, 3 name only → resolved first (1 ambiguous, parked). Approval at ~22.4
Deepline credits (28 × 0.8). Run: a play over the CSV (batch > 20). Read: 24 hits
(entity echo clean on 23 — 1 mismatch flagged: a same-named company matched from
a bare domain), 3 misses → unverifiable, plus the parked ambiguous row.
Interpret: 6 high-growth (12-mo), but 2 of them show negative 3-month deltas →
`stalling` flag; 1 shows +180% on a 14-person base → micro-base flag, not
hyper-growth. Deliver: 23 measured rows with counts + buckets + trajectories,
5 unmeasured (3 unverifiable, 1 wrong-entity, 1 unresolved), credits measured
(from the run's billing) vs declared.
