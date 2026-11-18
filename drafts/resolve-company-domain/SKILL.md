---
name: resolve-company-domain
description: |
  Resolve a company name to its single canonical operating-company domain with Deepline —
  validated, evidence-backed, or an honest "ambiguous", "not found", or "acquired"
  flag with the candidates listed. Use whenever someone asks: find the domain for this company,
  resolve the real domains for these company names, clean this messy company list
  before enriching it, what is the actual website of X, which domain is the operating
  entity, or verify these domains belong to these companies. The keystone task: a
  wrong domain poisons every downstream enrichment, so this skill validates that
  the domain actually belongs to the operating company and refuses to guess on
  ambiguous names. Do NOT use it to enrich the resolved company
  (enrich-account-list / company-research-brief), to find people there
  (find-decision-makers-at-company), or to source new companies
  (build-prospect-list). Built on Deepline's free company-identify lookup as candidate
  generator, wrapped with free validation probes and ambiguity refusal.
ported_from: clay-run/clay-skill-creator/skills/clay/resolve-company-domain
category: find-contact-data
personas: [gtm-engineer, revops]
mechanism: functions
touches: read-only
keywords: []
---

# Resolve a company's domain

The insight: **a wrong domain poisons every row downstream — refusing beats
guessing.** The naive version takes the first search hit or whatever a lookup
returns; the failure is silent, and every enrichment, signal, and email built on it
inherits the wrong company. So this skill treats any looked-up domain as a
CANDIDATE, validates it actually belongs to the operating company (not a parent, a
brand redirect, or a similarly-named stranger), and returns `ambiguous` or
`not_found` — with candidates — when the name doesn't pin one entity. An honest
refusal costs a re-ask; a confident wrong domain costs the whole row, invisibly.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **What they have per row** | a name plus a claimed domain, a name only, a domain only, or a company profile URL | no default — each route costs differently, and a claimed domain is validated rather than looked up, which is free |
| **Cost ceiling** | credits | dedupe names first, then state paid corroboration × its `describe` price per survivor (lookups and probes are free), and wait |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — what each row already carries, and the resolution ladder it runs.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or returns a domain it could not validate.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, run
`npm install -g deepline && deepline auth register --wait auto`, then re-run preflight.
Tell the user which org you're in and the balance. Confirm the arms and read their
live prices with `deepline tools describe <id> --json` (`pricing`) — the arm table in
`references/validation-ladder.md` names them.

## Step 1 — Route by what you have

| You have | Path |
|---|---|
| Name + a claimed domain | validate the claim (Step 3) — no lookup spend |
| Name only | candidate lookup (Step 2) → validate |
| Domain only | validate (Step 3), entity name comes from the site |
| Neither, but a LinkedIn company URL | `crustdata_v3_company_identify` with `professional_network_profile_urls` (free) → validate |

Batch input: dedupe names first; state cost (lookups are free; paid corroboration and
news screens × their `describe` price per survivor that needs them) and get approval
before running.

## Step 2 — Candidate lookup (paid, name-only rows)

Run `crustdata_v3_company_identify` (`{"names":["<name>"]}`, free). Its output
is a CANDIDATE, never a result — the lookup resolves *a* company for the name,
not necessarily *the* company (name collisions are the #1 failure), and lookups on
ambiguous or common-word names return confident wrong answers (name-only matches
can come back at `confidence_score: 1.0` for an unrelated company). Optional second
candidate source when hints exist (a known country/region, industry):
`crustdata_v3_company_search` with those filters — noting its identifier filter is recall-not-exact and can miss the
canonical entity entirely (gate on match confidence, never take position as truth).

## Step 3 — Validate the candidate (the lever; mostly free)

Run the ladder in `references/validation-ladder.md` — in order, cheap first:

1. **Normalize** (free, code): strip scheme/www/paths, registrable label
   (public-suffix aware).
2. **Liveness + redirect probe** (free): real HTTP status and final URL via
   `generic_http_request`; NXDOMAIN/dead → `not_found` evidence; a redirect landing on social media
   or a parking page → inactive candidate; a redirect to ANOTHER domain → follow it
   and validate the destination (brand → corporate redirects are common).
3. **Site-content check** (free, survivors only): fetch the homepage with
   `contextdev_get_web_scrape_markdown`; the site
   must plausibly BE the company — name/brand present, business coherent with any
   hints. A parked/for-sale/soft-404 body fails (a scraper's SUCCESS is not
   page-existence).
4. **Operating-entity check**: is this the entity the user means — the operating
   company, not the holding parent or a regional clone? Name-boundary discipline
   applies ("X Partners"/"X Group" are different entities). **Acquisition is a
   verdict, not a pass**: if the evidence says the company was acquired or absorbed
   (site redirects to the acquirer, "now part of Y" content, acquirer branding),
   the old-name domain is NOT the canonical answer — return `acquired` with both
   the stale domain and the acquirer's domain named; a REBRAND of the same entity
   (same company, new name/site) may still resolve, with the reasoning stated.
   Enrichment corroboration when needed (`crustdata_v3_company_enrich`, priced in
   `describe`): the payload's company website field, read off the first response —
   never a link field that can echo a shortener — and remember
   enrichment PRESENCE proves the entity exists in data, never that the domain is
   alive: dead and acquired companies enrich fine on last-known data.

## Step 4 — Verdict (five values, no sixth)

- **resolved** — one candidate survived all gates → `canonical_domain` +
  `operating_entity_name` + `confidence` (validated / corroborated) + `provenance`
  (which gates it passed, quoting evidence).
- **acquired** — the named company was absorbed → the stale domain is never the
  answer; emit `acquired` + the acquirer's domain as the actionable candidate
  (resolving to the acquirer is a USER decision — the entity changed).
- **ambiguous** — the name pins multiple real entities → the candidate list with
  one line each; the USER picks. Common-word names land here by default.
- **not_found** — no living candidate → say what was tried.
- **mismatch** (claimed-domain path) — the claim failed validation → the evidence,
  plus the best candidate if one emerged.
Never a guessed domain asserted as fact; never "probably". Per-row provenance
always; batch output adds a summary (resolved / ambiguous / not_found / mismatch
counts, credits measured from `deepline billing`).

## What good looks like

- **Resolved rows are load-bearing** — downstream enrichment can key off them
  blindly; that's the whole point of the gates.
- **The ambiguous bucket has content on messy lists** — a 100% resolution rate on
  common-word names means the skill guessed; refusal IS the feature.
- **Provenance per row** — which gates passed, what the site showed; a domain
  without provenance is a rumor.
- **Free gates run first** — most candidates die (or pass) on normalization and the
  status probe before any credit is spent.
- The common mistake: treating the lookup function's answer as the answer. It
  resolves A company, confidently, every time — including for names that belong to
  three companies or none.

## Rules

- MUST treat every lookup output as a candidate; MUST run the validation ladder
  cheap-first; MUST follow redirects to the destination before judging.
- MUST refuse (ambiguous, with candidates) when the name doesn't pin one entity;
  MUST return not_found rather than a best guess when nothing survives.
- MUST read enrichment corroboration from the website field, never a shortener-prone
  link field; MUST apply
  name-boundary discipline to candidate entities.
- NEVER assert an unvalidated domain, pattern-guess a domain from the company name,
  or let a parked page pass as an operating site.
- NEVER assert a stale old-name domain for an acquired company (the `acquired`
  verdict exists for exactly this); NEVER let enrichment presence stand in for
  liveness — dead companies enrich fine on last-known data; only the probe answers
  "is this domain alive".
- Batch: dedupe names first, state cost, cap the run; per-row provenance ships.

## Worked example

Ask: "Clean these 5 company names into real domains: Brightloop, Meridian, Subway,
Quartzlane Systems, Zzyqx Dynamics."
- **Brightloop** → lookup → brightloop.example → probe live, homepage says
  "Brightloop — workflow automation", entity matches → **resolved** (validated).
- **Meridian** → lookup returns a fintech's domain confidently — but the name pins
  a fintech, a consultancy, and a medical group → **ambiguous**, 3 candidates
  listed, user picks (the lookup's confidence changed nothing).
- **Subway** → subway.com resolves, but entity check notes it's the BRAND/franchise
  parent — flagged so the user confirms brand vs franchisee intent → **resolved
  (operating-entity note)**.
- **Quartzlane Systems** → lookup → a domain that redirects to
  quartzlane-holdings.example (a parent) → destination validated, holding-vs-
  operating flagged → **resolved (corroborated, entity note)**.
- **Zzyqx Dynamics** → lookup empty, no living candidate → **not_found** (tried:
  lookup, search, direct .com probe).
- Counter-case: "Loopwise" → lookup returns loopwise.example, which redirects to
  its acquirer's site ("Loopwise is now part of OrbitStack") → **acquired** — the
  stale domain is never asserted; the acquirer's domain ships as the candidate.
Summary: 3 resolved · 1 ambiguous · 1 not_found · only the Quartzlane corroboration
was paid (free gates settled the rest).
