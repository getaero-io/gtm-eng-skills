---
name: enrich-account-list
description: |
  Enrich a list of accounts with validated firmographics using Deepline — industry,
  headcount, revenue, HQ, founded — one clean row per company, from a CSV or CRM
  export of domains or names. Use whenever someone asks: enrich our accounts, fill
  in firmographics on this list, add industry and employee count to these
  companies, enrich our CRM account records, or build account intelligence on a
  known list. It validates identity FIRST (a
  wrong domain makes every field describe the wrong company), enriches once per
  unique domain, parses what actually comes back (headcount bands, not numbers),
  and reports unknowns as unknowns — never zeros. Do NOT use it to resolve messy
  names to domains (resolve-company-domain — it hands off), to score the enriched
  accounts (score-inbound-leads), to detect tech stacks (detect-tech-stack), to
  watch for signals (monitor-buying-signals), or to source the list
  (build-prospect-list). Built on Deepline's free crustdata_v3_company_identify plus
  crustdata_v3_company_enrich behind identity validation and deterministic
  normalization.
category: enrich
personas: [revops, gtm-engineer]
mechanism: functions
touches: read-only
keywords: []
ported_from: clay-run/clay-skill-creator/skills/clay/enrich-account-list
---

# Enrich an account list

The insight: **the enrichment call is the easy 10% — identity before it and
interpretation after it decide whether the output is intelligence or noise.**
Enrichment matches an ENTITY, not a live business: a stale domain enriches fine on
last-known data, a wrong domain enriches a stranger, and the payload lies politely —
headcount arrives as a band string that parses to garbage in comparisons, and
missing fields read as empty rather than unknown. So this skill validates identity
first on every row (never trusting CRM fields that "look populated"), enriches once
per unique domain, and normalizes the output into values a formula can trust —
with `unknown` as a first-class state, never a silent zero.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The list** | a CSV or CRM export with at least one domain **or** company-name column | no default. Existing industry and headcount columns are stale claims, kept as reference only |
| **The fields they need** | industry, headcount, revenue, HQ country, founded | ask. Tech stack, signals and scores belong to named sibling skills — say so rather than swelling scope |
| **Cost ceiling** | Deepline credits | dedupe to unique domains first, state lookups × declared cost plus resolution for name-only rows, then wait |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the account list you supply and the fields you ask for, via Deepline company enrichment.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes back to the CRM, or enriches a name the resolver flagged ambiguous or acquired.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline &&
deepline auth register --wait auto`, then re-run preflight. Tell the user which org
you're in and the balance. Confirm the two calls exist and read their price:
`deepline tools describe crustdata_v3_company_identify --json` (free) and
`deepline tools describe crustdata_v3_company_enrich --json` (`pricing`; 0.8
credits per matched result on 2026-09-30).

## Step 1 — Scope (interview; do not guess)

1. **The list** — CSV/CRM export; minimum one domain OR company-name column. Extra
   fields (old industry, old headcount) are stale claims, kept as reference only.
2. **The fields they need** — this skill's core: industry, headcount (band +
   ordinal), revenue, HQ country, founded. Tech stack, signals, scores → named
   sibling skills; say so instead of swelling scope.
3. **Cost + cap**: dedupe to unique domains first, state lookups × declared cost
   (+ resolution cost for name-only rows), get approval. Balance: `deepline billing balance`.

## Step 2 — Identity first (always, every row)

- **Dedupe to unique companies** before any spend (47 contacts at one account =
  one enrichment). Normalize domains public-suffix-aware before comparing.
- **Name-only rows** → hand off to resolve-company-domain (its verdicts flow back:
  `resolved` rows proceed; `ambiguous`/`not_found`/`acquired` rows land in the
  output with that status — never enriched on a guess).
- **Domain rows** → `crustdata_v3_company_identify` (free) confirms the domain maps to
  one company entity before any paid call; no match or several candidates →
  `ambiguous`, not enriched. Then the free liveness screen (DNS + the probe whose error channel
  names the status): dead domains get `status: dead-domain` — and remember the
  trap the hard way taught: **a dead or acquired company still enriches fine on
  last-known data**; enrichment presence is never liveness evidence. Never skip
  identity because CRM fields look populated — they are frequently stale, wrong,
  or redirected.

## Step 3 — Enrich once per unique domain

`crustdata_v3_company_enrich` with `domains: [<validated domain>]` and explicit
`fields` (omit them and only `basic_info` comes back), 0.8 credits per matched
result; call envelope + gating rules in `references/enrichment-mechanics.md`. Up to
~20 domains: `deepline tools execute` directly; beyond that, a play over the deduped
CSV. Gate on actual payload values, never call status (a successful call with empty
`matches` is the routine miss shape) — an empty payload is an honest `not_enriched`
row, not a retry loop.

## Step 4 — Normalize what actually came back (free, deterministic)

- **Headcount arrives twice**: `basic_info.employee_count_range` is a band string
  ("1001-5000") and `headcount.total` an integer that can be null. Emit the raw band,
  the parsed ordinal, and the integer when present; unparseable → `unknown`, visibly.
  Never let a band string touch a numeric comparison (parseInt reads it as 1, silently).
- **Missing ≠ zero**: absent revenue/founded/industry → `unknown`, a first-class
  value downstream formulas must handle; a row of unknowns is still an enriched
  identity.
- **Cross-check identity in the payload**: the record's `basic_info.website` /
  `primary_domain` should agree with the input domain (`all_domains` lists aliases;
  a hit there is a match, not a mismatch) — a mismatch flags possible wrong-entity resolution, routed to review,
  never silently kept.
- **Freshness honesty**: enrichment data is last-known, not live — carry the
  enriched-at date; on accounts where currency matters (the user says "current
  headcount"), say the data is as-of, not real-time.

## Step 5 — Deliver

One row per unique company: `input identity · resolved/validated domain · status
(enriched / not_enriched / dead-domain / ambiguous / acquired) · industry ·
headcount band + ordinal · revenue · HQ country · founded · enriched-at ·
identity-mismatch flag`, joined back to the input rows (contacts inherit their
account's enrichment). Summary: rows in, unique companies, enriched %, honest
not-founds, unknowns per field, credits measured (`deepline billing usage`) vs declared. Every input row lands
somewhere — silent drops are the cardinal sin.

## What good looks like

- **Company spend = unique-domain count**, never row count.
- **The unknown column has content on real lists** — a 100% fill rate on messy CRM
  data means something invented values; unknowns are the honest residue.
- **Band strings never meet comparisons raw** — the ordinal column exists so
  downstream scoring (a sibling skill) can gate deterministically.
- **Identity mismatches surface** — the wrong-entity failure is silent by design;
  the cross-check is what makes it visible.
- The common mistake: enriching the raw list. Identity validation and dedupe are
  free; a wrong-company enrichment costs a credit AND poisons every downstream use.

## Rules

- MUST dedupe to unique companies and get cost approval before any spend; MUST
  validate identity on every row — no exceptions for populated-looking CRM fields.
- MUST gate on payload values, never run status; empty payload → honest
  `not_enriched`.
- MUST emit unknowns as unknowns and bands as band+ordinal; NEVER let unparseable
  values flow into comparisons or read enrichment presence as liveness.
- NEVER enrich a name the resolver flagged ambiguous/acquired; NEVER write back to
  a CRM — delivery is a table/CSV; writeback is the user's move.
- Depth beyond firmographics (tech stack, signals, scoring) → hand off to the named
  sibling skill.

## Worked example

Ask: "Enrich our 120-row account export — industry, size, revenue."
Identity: 120 rows → 74 unique companies (46 duplicate-account rows join back
later); 61 have domains, 13 name-only → resolver handoff returns 9 resolved, 2
ambiguous, 1 not_found, 1 acquired (flagged, not enriched). Liveness screen kills 2
dead domains free. Cost stated: 68 enrichments × 0.8 credits ≈ 54 credits, approved. Enrichment:
64 return payloads; 4 come back empty → `not_enriched`. Normalization: 61 industries
fill; headcount bands parse on 58 (6 unknowns visible); one payload's website
disagrees with the input domain → identity-mismatch flag for review. Delivered: 74
company rows joined to 120 input rows · 64 enriched · honest states on the rest ·
≈51 credits measured (64 matches × 0.8) vs ≈54 declared — only matched results bill.
