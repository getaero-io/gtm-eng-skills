---
name: enrich-signup-users
description: |
  Turn raw product signups — often just an email, frequently a personal one — into
  routed, evidence-backed leads using Deepline: classify every email into a routing enum
  first, identify the person, resolve and dedupe the company, score ICP fit, and route
  each signup to sales, sales-review, self-serve, or disqualify. Use whenever someone
  asks: enrich our signups, who are these trial users, de-anonymize our PLG signups,
  turn free-tier emails into pipeline, which signups should sales call, or
  reverse-enrich people from a list of emails. Works from a CSV with nothing but an
  email column. Do NOT use it to find a known person's email (find-work-email), to
  check an address's deliverability (verify-email-deliverability), to bulk-clean a
  list with no routing intent (clean-email-list), or to source net-new prospects by
  persona (people search); it writes nothing to a CRM and triggers no sequences —
  acting on the route is the enrich-and-route-leads play. It never fabricates an
  identity and states cost before any batch spend.
category: enrich
personas: [revops, founder]
mechanism: functions
touches: writes-own-output
keywords: [plg]
ported_from: clay-run/clay-skill-creator/skills/clay/enrich-signup-users
---

# Enrich signup users

The insight: **a signup email is an identity claim, not an identity — and the email's
TYPE changes the entire resolution path, including what a miss means.** A work email
carries a company candidate in its domain; a personal email carries nothing (the domain
belongs to Google); an academic email carries a school, not an employer. So classify
first — into one routing enum every later step gates on — and each row gets the only
path that can resolve it. And when a row doesn't resolve, say so: **honest
disqualification ("could not identify") beats fabricated fit** — a sales queue padded
with guessed identities is worse than a shorter, true one.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The signups** | a CSV or pasted list with at least an email column | no default. Name, company and plan columns are corroboration — claims, not truth |
| **The ICP** | industry, headcount band, region | **stop rather than defaulting.** If they cannot state it, help them write it down first: fit against an undefined ICP is fiction |
| **The routing policy** | which tier goes to sales, self-serve, or disqualified | a default policy is proposed and must be confirmed, not assumed |
| **Where the digest goes** | a table, a CSV, or a summary in the conversation | the conversation is the destination if they say nothing. Nothing is ever pushed anywhere |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the signups you supply, your ICP, and the enrichment it runs per email.
- **Writes** — only its own output, to the destination you name (a table, a CSV, or the
  conversation). It never changes a record that already exists.
- **Never** — writes to a CRM, enrolls anyone in a sequence, or sends anything.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline &&
deepline auth register --wait auto`, then re-run preflight. Tell the user which org
you're in and the balance. Confirm each tool this skill calls exists and read its
price: `deepline tools describe <tool_id> --json` (`pricing`) for
`crustdata_v3_person_enrich`, `crustdata_v3_person_search`,
`crustdata_v3_company_identify`, `crustdata_v3_company_enrich`, and (optional)
`leadmagic_email_validation`; `deepline plays describe
prebuilt/personal-email-to-linkedin --json` for the personal-email arm. Trust declared
input schemas, never description prose — it drifts.

## Step 1 — Collect the inputs (interview the user; do not guess)

1. **The signups** — a CSV or pasted list, minimum one email column. Extra columns
   (name, company, plan) are corroboration — claims too, not truth.
2. **The ICP** — industry, headcount band, region. If the user can't state it, stop and
   help them write it down first; fit against an undefined ICP is fiction.
3. **The routing policy** — confirm or adjust the default in Step 6.
4. **Where the digest goes** — a table, CSV, or summary. Nothing is pushed anywhere.

## Step 2 — Classify every email into the routing enum (free, before any spend)

No Deepline tool classifies email type; do it locally and deterministically (a short
script, or `run_javascript` inside a play): split local-part / domain, match the domain
against a freemail list and `.edu`-class suffixes, then run the screens on top (a
"company" class is only a residual, role local-parts need their own screen, and a name
parsed from a handle is a hint — see `references/email-triage.md` for the semantics, the
~40-token generic-mailbox blocklist, and the enum table). Tag every row with one **Input Email Type** value:

`work` · `personal` · `education` · `generic` (role mailbox: info@, support@, admin@…) ·
`junk` (disposable provider, dead/nonexistent domain, malformed) · `no-email`

Optionally — when the user wants sendable addresses, not just routing — add a cheap
deliverability check per row (`leadmagic_email_validation`, 0.09 credits) and the enum
gains validated tiers
(`valid` / `catch-all` / `invalid`); unvalidated rows carry `validity: unverified`, an
honest flag, never a gate. `generic`, `junk`, and `no-email` rows route to disqualify
with **zero spend**. Personal and education rows get their domain blanked as a company
candidate (gmail is not a company; an `.edu` domain is a school, not an employer).

## Step 3 — State cost and get approval (mandatory gate)

Before any enrichment call: report batch size after the Step-2 filter, **the count of
unique company domains** (Step 5 enriches domains, not rows), each tool's `pricing`
from `deepline tools describe`, and the worst-case total. **Wait for explicit
approval.** Some tools price "after execution" (person enrichment varies by field
group) — report the declared estimate up front and actual usage after (`deepline
billing usage`).

## Step 4 — Identify the person

First try a reverse lookup on the **email**: work rows →
`crustdata_v3_person_enrich` with `business_emails`; personal rows →
`prebuilt/personal-email-to-linkedin` (an email tie, not a name guess). Gate on values
at two levels: a successful call with an empty match list is routine — completion is
not data. A row is **identified** only when the payload contains an actual person.
**Expect the email arm to miss a lot** (measured on Clay's Enrich Person, 2026-08:
low-yield even on real corporate addresses — re-measure on your first pilot). On a
miss, branch by enum:

- **work — recover via search**: `crustdata_v3_person_search` with the best
  available name (CSV name, else the handle-parsed name as a hint) + the email domain
  as the current-employer anchor. Gate on match count: exactly one match = a candidate identity with evidence;
  multiple = narrow or flag for review — never pick one silently. Mechanics + field
  paths: `references/identity-recovery.md`.
- **education — recover with the school as corroborator, not employer**: if a name is
  available, search with it and corroborate the candidate via the school in their
  *education* history — never require (or claim) employment at the `.edu` domain. The
  person's current employer, if identified, becomes the company candidate.
- **personal — no name recovery**: beyond the email-tied
  `prebuilt/personal-email-to-linkedin` lookup there is no anchor to disambiguate a
  bare name — a name+nothing search is a guess factory. Honestly
  **could-not-identify**, unless the CSV carries a claimed company (then search with
  the claim, marked unverified).

## Step 5 — Resolve the company (dedupe by domain FIRST)

**Collapse rows to unique company domains before any company spend** — ten signups from
one company are one enrichment, not ten (and multiple signups per domain is itself a
PLG buying signal — count it, surface it, weight it up in Step 6). Company candidate by
branch: **work** → the email domain, cross-checked against any identified person's
current employer (match on domains, never name strings; a mismatch may be a job change
or subsidiary — record both, flag for review); **personal/education** → only the
identified person's employer. No person → no company → honestly unresolved. An employer
name with no domain resolves through the free `crustdata_v3_company_identify`
(`{"names": ["<employer>"]}`) first — a wrong domain poisons everything downstream.

Run `crustdata_v3_company_enrich` (`{"domains": [...], "fields": ["basic_info",
"headcount", "locations", "taxonomy"]}`, 0.8 credits/result) once per unique resolved
domain; join results back to rows. Its required input is the gate: rows with no
resolved domain never fire it.

## Step 6 — ICP fit and route (deterministic)

Score fit in code/formula against the stated ICP — comparisons, not judgment; an LLM
adds only variance. Parse what actually comes back: `basic_info.employee_count_range`
is a **band string** ("1001-5000"), not a number — compare on `headcount.total` when
present, parse the band otherwise; route unparseable values to
`unresolved`, never through a silent comparison. Verdict: `fit` / `no-fit` /
`unresolved` (its own honest state, not a soft no-fit), each quoting the payload values
compared. Route by the Step 1 policy — on **what resolved**, not just the person:

- person identified + company fit → **sales** (rank: domain-corroborated work-email
  identities first; multi-signup accounts to the top)
- work email + company fit + person unidentified → **sales-review** ("known account,
  unknown person" — real pipeline, weaker evidence)
- real person or real company, out of ICP or half-resolved → **self-serve**
- personal email with nothing resolved, generic, junk → **disqualify**

## What good looks like

- **Every input row lands in the digest** — routed or disqualified-with-reason. Silent
  drops are the cardinal sin.
- **The expert checks the personal-email rows first** — that's where naive builds
  fabricate: a gmail signup "resolved" via an unanchored name search is a guess wearing
  a suit.
- **Company spend scales with unique domains, not rows** — credits ≈ row count on a
  shared-domain batch means the dedupe didn't happen.
- **Two-level status gates everywhere** — call status AND returned value; empty-payload
  SUCCESS is routine, and misses return in seconds (normal, not an error).
- **Could-not-identify is a result** — in a PLG funnel it's actionable: self-serve
  nurture, not a rep's morning.
- The common mistake: enriching everything, then classifying. The fork exists so spend
  happens *after* routing.

## Rules

- MUST classify (Step 2) before any paid call; MUST get explicit approval (Step 3)
  before batch spend; MUST dedupe company enrichment by domain (Step 5).
- MUST gate every verdict on actual payload values, never run/completion status.
- NEVER fabricate or backfill an identity — no promoting a handle-parsed name or a CSV claim
  to a person, no "probably works at" from a domain, no silently picking one of several
  search matches.
- NEVER treat an `.edu` domain as an employer, or a validator's `valid` on a freemail
  address as an identity or policy pass.
- NEVER write to a CRM, enroll in sequences, or send anything — this play ends at the
  digest; acting on it is the enrich-and-route-leads play.

## Output

Per signup:
`email · type (the Step-2 enum value, + validity if checked) · identity (name, title,
LinkedIn) · identity source (reverse-lookup / search-recovery / could-not-identify) ·
company (name, domain) · ICP verdict (fit / no-fit / unresolved) · route (sales /
sales-review / self-serve / disqualify) · evidence`
plus a summary: signups in, identified %, fits, route counts, unique domains enriched
vs rows, multi-signup accounts flagged, credits spent (actual).

## Worked example

Input: 40 trial signups, one email column. ICP: B2B software, 50–5,000 employees,
NA/EU. Step 2 (free): 23 work, 12 personal, 1 education, 1 generic (`info@…`), 3 junk
(`test@test.com`, two disposables) → generic+junk disqualified, $0. The 23 work rows
share **17 unique domains — 4 rows from brightloop.example** (flagged as a PLG account
signal). Approval given: 17 company enrichments + person lookups, not 23.
`maya.torres@brightloop.example` (work): reverse lookup empty → search recovery on
"Maya Torres" + brightloop.example → one match, Head of Growth; brightloop.example enriches once
to a 300-person B2B SaaS → fit → **sales**, top of queue (multi-signup account).
`jordan@ashgrove-polytechnic.edu` (education): search with the CSV name; candidate corroborated
via Calverton University in education history; current employer is a 40-person
startup → below ICP band → **self-serve**.
`kc.builds.zq77x2@gmail.example` (personal): reverse lookup empty, no anchor → nothing resolved →
**disqualify**, evidence: "no person resolved from personal email".
Summary: 40 in · 33 enriched · 19 identified · 17 domains enriched for 23 work rows ·
1 multi-signup account · routes: 10 sales, 4 sales-review, 14 self-serve, 12
disqualified (4 pre-spend + 8 unresolved) · actual credits from run usage.
