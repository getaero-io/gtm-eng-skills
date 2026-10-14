---
name: build-prospect-list
description: |
  Build a validated prospect list with Deepline from a target definition: an ICP
  (vertical + geography + size band) plus buyer personas → a deduped, suppression-aware
  list of companies and the right people at them, every row carrying its evidence.
  Use whenever someone asks: build me a prospect list, find 50 VPs of Sales at
  mid-market SaaS companies, get me target accounts and decision-makers in this metro,
  source companies matching our ICP and the buyers at each, or build a TAM + contact
  list from scratch. It runs both arms of the motion — company sourcing, then people
  at those companies — and validates every person (still employed, on-persona) before
  they make the list. Do NOT use it to find emails or phones for the list
  (find-work-email / find-work-phone take each row from here), to write outreach
  (that is a personalize-outbound play), to enrich signups you already have
  (enrich-signup-users), or to find one known person (find-linkedin-profile).
  It never pads a short list with off-ICP rows, states cost before any paid
  enrichment, and sends nothing anywhere.
ported_from: clay-run/clay-skill-creator/skills/clay/build-prospect-list
category: build-lists
personas: [sales-development, founder]
mechanism: functions
touches: read-only
keywords: []
---

# Build a prospect list

The insight: **a list's quality is set by its worst validation gate, not its best
source — and a count ask is the standing temptation to skip the gates.** "Get me 50"
tempts every builder to pad: widen the filters silently, keep the departed, keep the
adjacent-but-wrong titles. The searches are recall engines — they hand back companies
outside the size band you asked for and people who left the company months ago, without
erroring. So the deliverable is defined by what survives validation: **38 validated
rows beat 50 padded ones**, and when the honest count falls short you say so and offer
the widening levers (looser geo, adjacent titles, wider size band) — the user chooses,
never the skill silently.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **ICP** | vertical, geography, size band | ask — vague verticals ("tech") produce vague lists. Help them tighten before searching |
| **Personas** | target titles, the seniority floor, and titles to exclude | ask. One persona set per search; multiple personas means multiple searches |
| **Counts** | companies wanted, and people per company | **1–3 people per company is defensible** and must be stated: more inflates downstream cost linearly |
| **Suppression set** | customers, competitors, open pipeline, do-not-contact | ask explicitly. A list that emails a customer is worse than no list |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — your ICP and persona definitions, and Deepline's company and people search indexes
  (`crustdata_v3_company_search`, `crustdata_v3_person_search`).
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, enrolls anyone, or sends anything.
- **Halts** — Step 6 spend-approval.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline &&
deepline auth register --wait auto`, then re-run preflight. Tell the user which org
you're in and the balance. Confirm each tool this skill calls exists and read its
price: `deepline tools describe <tool_id> --json` (`pricing`) for
`crustdata_v3_company_search`, `crustdata_v3_person_search`, their `_autocomplete`
siblings, and (only if Step 5/6 need them) `crustdata_v3_person_enrich`,
`crustdata_v3_company_enrich`, `crustdata_v3_company_identify`. Both search arms bill
0.02 credits per returned row (empty pages free), so a pull's cost is
rows-returned × 0.02 — state it before big pulls.

## Step 1 — Collect the target definition (interview; do not guess)

1. **ICP** — vertical, geography, size band. Vague verticals ("tech") produce vague
   lists; help the user tighten before searching.
2. **Personas** — target titles + seniority floor, and titles to exclude (Assistant,
   Advisor, former). One persona set per search; multiple personas = multiple searches.
3. **Counts** — companies wanted, people per company (default 1–3; more inflates
   downstream cost linearly).
4. **Suppression set** — existing customers, competitors, open pipeline, do-not-contact.
   Ask explicitly; a list that emails a customer is worse than no list.

## Step 2 — Company arm (TAM)

Discover the real filter contract first: `deepline tools describe
crustdata_v3_company_search --json` lists every filterable field. Map the ICP onto it —
`basic_info.industries` / `taxonomy.professional_network_industry` take a **fixed
vocabulary** (get exact values from the free `crustdata_v3_company_search_autocomplete`,
`{"field": "basic_info.industries", "query": "software"}`; free text goes in a `(.)`
fuzzy condition on `basic_info.description`), geo via `locations.country` /
`locations.headquarters`, size via `basic_info.employee_count_range` (`in` a list of
bands) or `headcount.total` (`=>` / `=<`). Run with `deepline tools execute
crustdata_v3_company_search --input '{"filters": {...}, "limit": N}' --json` and page
with `cursor` = the previous `next_cursor`. **`in` arrays hold at most 5 values** —
CrustData can silently ignore longer ones, so split and merge. Pull modestly over the
target (~1.5×) — validation will eat rows. The response carries `total_count` (optional
in the schema — read it defensively), which sizes the universe up front; page until the
target is met or `next_cursor` is null — which is the proof the universe is exhausted,
and turns a shortfall report factual ("3 exist, you asked for 10").

**Post-validate every company against the ICP from its own returned fields.** The
numeric size filter and the record's reported size band can disagree (measured on Clay's
company search, 2026-08: a 50–500 filter returned 11–50 and 501–1,000 rows) — the filter
is recall, the band on the record (`basic_info.employee_count_range`) is the evidence. Check size band, location, industry per row; drop
off-ICP rows with the reason recorded. Dedupe on normalized domain (lowercase, strip
`www`). Keep per-company evidence: domain, LinkedIn URL, size band, location, industry.

## Step 3 — Suppression gate (before the people arm)

Match each surviving company against the suppression set on **normalized domain**
(fall back to normalized name only when a set entry has no domain — never compare one
row's domain to another's name). Suppressed companies are excluded **and recorded**:
`suppressed: customer — acme.example matched customer list`. Silent exclusion is
indistinguishable from a sourcing miss; the user must see what the gate caught. Gate
here, not after: every suppressed company skipped saves its whole people-arm and
enrichment cost downstream.

## Step 4 — People arm

`crustdata_v3_person_search` with
`experience.employment_details.current.company_website_domain` `in` the validated,
unsuppressed domains — **in batches of 5** (the `in` cap), plus title conditions on
`experience.employment_details.current.title` (`(.)` per keyword, grouped under
`"op": "or"`), exclusions as `not_in` / a negated group, and
`experience.employment_details.current.seniority_level` for the floor (exact values from
`crustdata_v3_person_search_autocomplete`). Do NOT reach for a top-N-by-seniority
lister here — measured on Clay's managed "Find People at Company" (2026-08), such a
lister ignored persona filters; it passes famous-company tests coincidentally and
fails everywhere else.

## Step 5 — Validate every person (the people-search-validate discipline)

A returned person is a candidate, not a row. Gates, all mandatory:

- **Employment confirmed** — the search filter is the anchor, not the evidence. Gate
  on an entry in the person's own `experience.employment_details.current[]` whose
  `company_website_domain` (or name, matched tolerantly) resolves to the listed
  company. A mismatch means *unconfirmed*, not *departed* — measured on Clay's people
  search (2026-08): one mismatch was an exec holding two concurrent current roles, the
  listed company still among them; a search record cannot tell that apart from a job
  change. Resolve mismatches with `crustdata_v3_person_enrich`
  (`{"professional_network_profile_urls": ["<url>"], "fields": ["experience"]}`,
  priced per matched record — read `describe`, state the cost): a current experience
  at the listed company in the payload → validated, flagged `multi-role`; none →
  departed, dropped with reason. Not resolving → drop as `employment unconfirmed`;
  never keep an unconfirmed row. Departed people are the padding most lists ship.
- **On-persona** — the title on the listed company's `current[]` entry (not
  `basic_profile.current_title`, which can be a different concurrent role)
  satisfies the persona by meaning: "Head of Revenue" matches a VP-Sales persona;
  "VP Sales Enablement" does not. Keyword filters over-match; judge the title.
- **Dedupe** on the LinkedIn URL
  (`social_handles.professional_network_identifier.profile_url`); one person matching
  two personas appears once, best
  persona kept.

Failed rows are dropped with reasons, never patched. Spot-check 2–3 survivors' URLs
against their claimed employer before delivering; when an enrichment ran, ship its
canonical `url` — search-hit slugs drift (same person, different slug across sources).
For deeper per-person validation, hand rows to find-linkedin-profile.

## Step 6 — Count honesty + optional fill-ins

Compare validated counts to the ask. **Short = report the true number, why (which gate
ate what), and the widening levers** — looser geo, adjacent titles, wider size band,
filtering on `employment_details.past` off the table (that reintroduces departed
people). Let the
user pick a lever; re-run only the affected arm.

Optional paid fill-ins for gaps (missing firmographics, name-only suppression entries
needing domains): `crustdata_v3_company_enrich` (0.8 credits/result) and the free
`crustdata_v3_company_identify` (name → domain). Read each `pricing` via `deepline tools
describe`, state the total, and **wait for explicit approval** before any paid call.
The base motion costs search rows only (0.02 credits each).

## What good looks like

- The expert checks the **near-miss rows first**: the dropped-with-reason list is the
  proof the gates ran. A list with zero drops means the gates didn't run.
- Every row carries evidence a human can spot-check in 10 seconds: person → title,
  employer, LinkedIn URL, start date; company → domain, size band, location, industry.
- Suppression exclusions are visible in the output, not silently absent.
- The common mistake: hitting the count by widening silently. The second-worst:
  validating companies but not people — the people arm is where staleness lives.

## Rules

- MUST post-validate companies against returned fields and people against the
  still-employed + on-persona gates; NEVER trust a search filter as a guarantee.
- MUST deliver the validated count with reasons + levers when short; NEVER pad with
  off-ICP, departed, or off-persona rows.
- MUST record every suppression exclusion; NEVER drop silently.
- MUST state cost and get explicit approval before any paid enrichment call.
- NEVER find emails/phones (route to find-work-email / find-work-phone), write
  outreach, or push the list anywhere — this play ends at the list.

## Representative output

Three things come back. Placeholder rows: `Northwind` and `Contoso` are invented.

### Companies

| Company | Domain | LinkedIn | Size band | Location | Industry | Status |
|---|---|---|---|---|---|---|
| Northwind Systems | northwind.example | /company/northwind | 50–200 | Denver, CO | B2B software | listed |
| Contoso Logistics | contoso.example | /company/contoso | 500–1,000 | Denver, CO | freight | dropped: off-band |
| Fabrikam Cloud | fabrikam.example | /company/fabrikam | 80–250 | Boulder, CO | B2B software | suppressed: customers, matched on domain |

### People

| Name | Title | Company | LinkedIn | Role start | Persona | Validation |
|---|---|---|---|---|---|---|
| A. Rivera | VP Sales | Northwind Systems · northwind.example | /in/a-rivera | 2024-03 | vp-sales | passed |
| B. Osei | VP Revenue Operations | Northwind Systems · northwind.example | /in/b-osei | 2023-11 | vp-sales | passed, flagged multi-role |
| C. Lindqvist | VP Sales Enablement | Fabrikam Cloud · fabrikam.example | /in/c-lindqvist | 2022-06 | — | dropped: off-persona |

### Run summary

Companies: 30 asked · 52 sourced · 41 validated · 3 suppressed.
People: 30 asked · 44 sourced · 31 validated.
Shortfall: none. Levers offered: none needed.
Search rows returned: 96 × 0.02 = 1.92 credits. No enrichment spent — the base motion
buys search rows only.

## Worked example

Ask: "30 VPs of Sales at B2B software companies in Denver, 50–500 employees; we have
40 customers to exclude." Company arm sources 52 → 41 survive post-validation (9
off-band, 2 non-B2B) → 3 suppressed as customers (recorded). People arm across 38
domains (8 batches of 5), title keywords `sales` / `revenue`, seniority floor VP → 44
candidates → 31 validated: 7 dropped departed (no current role at the listed company
on resolution), 1 kept flagged `multi-role`, 3 off-persona ("VP Sales Enablement",
"Advisor"), 2 duplicates. Deliver 31 of 30 asked — covered. Had it come up short:
"24 validated. 7 dropped as departed. Levers: add Boulder metro, add 'CRO' titles,
or widen to 25–1,000 employees — which?"
