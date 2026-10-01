---
name: find-work-phone
description: |
  Find a person's work phone number — ideally a validated mobile — using Deepline, from their
  LinkedIn URL or name and company. Use whenever someone asks: find someone's phone number,
  get a mobile number for this contact, find a cell or direct-dial number for a person at a
  company, or turn a short list of prospects into callable numbers. It runs Deepline's
  prebuilt phone waterfall play (multiple providers, each candidate checked for line type and
  status before it counts as found) and reports every number with its type — mobile,
  direct-dial, or HQ line — plus a compliance caution before any dialing or texting.
  Do NOT use it to find email addresses (use find-work-email), to identify who owns a phone
  number you already have (reverse lookup), or to source net-new prospects by persona
  (people search). It never fabricates or pattern-guesses numbers, and it never dials,
  texts, or writes numbers anywhere without explicit approval.
category: find-contact-data
personas: [sales-development]
mechanism: functions
touches: read-only
keywords: [waterfall, find-phone-number]
ported_from: clay-run/clay-skill-creator/skills/clay/find-work-phone
---

# Find a work phone number

The insight: **phone is the most expensive and most regulated field in contact data — found
is not the same as dialable.** A mobile lookup costs ~5–10x an email lookup (in Deepline:
`leadmagic_mobile_finder` 1.68 credits/result vs `hunter_email_finder` 0.3), and even a
good waterfall validates a mobile for only about half of senior US contacts, less
elsewhere (measured on Clay's phone waterfall) — misses are normal. An HQ
switchboard is not a direct line, and an unconsented call or text to a mobile carries legal
risk (DNC registries, US TCPA, GDPR) that a cold email doesn't. So the find includes
line-type validation, honest typing, and a compliance flag — never just "here's a number."

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **A profile URL per contact** | the professional profile, not just a name | **treat it as required** — most phone legs are keyed on the profile and skip without it. A name-only row resolves the URL first and confirms it is the right person |
| **A known email** | if they have one | optional; raises the hit rate where accepted |
| **The gate** | which contacts they would actually call | ask before a batch. Phone credits are worth spending only on the right persona at a qualified company |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the profile URL or known email on each contact, and the phone providers it queries.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or dials anything.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json` (health, auth, and balance in one call). If `deepline` is
missing, run `npm install -g deepline && deepline auth register --wait auto`, then re-run
preflight. Tell the user which org you're in (`auth.org_name`) and the balance.

## Step 1 — Collect what identifies the person

Phone waterfalls are keyed on the professional profile, not the name. The Deepline play
technically accepts name + domain or email, but its profile-keyed legs (the
LinkedIn halves of Datagma and LeadMagic) skip without a URL and the rest match worse — so get the URL first (email waterfalls don't
need one).

1. **LinkedIn URL** (plus name/company) — run directly.
2. **Name + company only** — resolve the URL first (find-linkedin-profile) and confirm
   it's the right person; a wrong profile poisons the lookup.

A known email raises the hit rate — pass it through if accepted. On a batch, gate first:
phone credits only on contacts the user would actually call (right persona, qualified
company).

## Step 2 — Run the prebuilt phone waterfall play

`prebuilt/person-to-phone` (one person) or `prebuilt/person-to-phone-batch` (CSV,
`{"csv":"leads.csv"}`, `"columns"` map for odd headers). Confirm the live contract with
`deepline plays describe prebuilt/person-to-phone --json`. Inputs: `first_name`,
`last_name` required; `linkedin_url`, `email`, `domain` optional. Order: `wiza_reveal_person`
→ `datagma_search_phone_numbers` → `deepline_native_enrich_phone` →
`leadmagic_mobile_finder` → `fullenrich_bulk_enrich` → `ai_ark_mobile_phone_finder`, and
each candidate is checked by `trestle_phone_validation` before it counts; a rejected or
stale candidate falls through to the next provider.

**Check cost before running — always.** Leg prices come from
`deepline tools describe <leg> --json` (e.g. `wiza_reveal_person` 1.75 credits for a phone
reveal, `leadmagic_mobile_finder` 1.68, `deepline_native_enrich_phone` 4.90 per matched
number, `trestle_phone_validation` 0.21 per check). Pilot 2–3 rows, read the real charge
from `deepline runs get <run-id> --full --json`, then state the total and get explicit
approval. Run: `deepline plays run prebuilt/person-to-phone --input
'{"first_name":"Priya","last_name":"Raman","linkedin_url":"..."}' --watch`. Timing: hits
return in seconds; a real-person miss takes longer (every provider tries, validations bill
anyway). A batch finishes at the speed and cost of its misses. Export batches with
`deepline runs export <run-id> --out <final.csv>`.

## What good looks like

- **Every number ships with its type.** Validators grade line type — mobile, landline,
  VoIP — plus active/disconnected status; direct-dial vs HQ is a role label on top. The
  play validates each arm's candidate and keeps going past a rejected hit
  (find-until-valid; the common mistake is trusting one provider's answer), and returns
  the evidence: `phone`, `phone_source`, `phone_validated`, `phone_validation_status`,
  `phone_line_type`, `phone_carrier`, `phone_activity_score` / `phone_activity_band`,
  `phone_reject_reason`. Type any other source explicitly with `trestle_phone_validation`
  (0.21 credits; pass `country_hint` for non-US numbers or they can come back falsely
  invalid).
- **Not-found stays empty — completion is not data, at two levels.** A run can complete
  successfully while a leg failed (unresolvable profile URL), or the row completes with
  `phone: null` (waterfall miss). Both are not-founds: gate on an actual number, never on
  run status.
- **Numbers are PII with dialing rules attached.** Report, don't act: flag DNC/TCPA/local
  consent before any call or SMS use. Before a real call block, offer a second independent
  validation: `searchbug_phone_validation` with `include_dnc` (0.19 credits; line status
  plus DNC registry, US/CA only) or `ipqs_phone_validate` (0.07; fraud score, DNC and
  line-type risk). No Deepline tool is a dedicated TCPA litigator list; say so rather than
  implying the screen covers it. Validator disagreement goes to a human, not the dialer.

## Rules

- MUST check the play's leg costs and get approval before any run; re-check the balance.
- MUST resolve and confirm the LinkedIn URL first when given only name + company.
- MUST pre-gate batches on persona/qualification — spend only on callable contacts.
- NEVER fabricate, pattern-guess, or pad a phone number (a switchboard is only ever `HQ`).
- NEVER report a number without its type, or an unvalidated number as "valid."
- NEVER dial, text, or export numbers anywhere without explicit user approval.

## Output

Per person: `name · company · phone (E.164) · type (mobile / direct-dial / HQ; flag VoIP)
· status (valid / not found)` plus what identified them. Batch runs add a summary: found %
by type, not found %, credits spent. Close with the compliance one-liner.

## Worked example

Ask: "Get me a mobile number for Priya Raman at brightloop.example."
URL on file → state the pilot cost (a Wiza phone hit plus one Trestle check ≈ 2 credits),
get approval → `person-to-phone` hits on the first leg → `+1-XXX-XXX-4821 · mobile · valid
· source: wiza`; offer the `searchbug_phone_validation` DNC check before the call block.
Counter-example: an unresolvable profile URL misses every LinkedIn-keyed leg (run still
completes) →
report `not found`; don't substitute the main line unless asked, then only labeled `HQ`.
