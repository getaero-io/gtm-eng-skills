---
name: find-work-email
description: |
  Find and verify a person's work email address using Deepline — from their name and company,
  or their LinkedIn URL. Use whenever someone asks: find someone's email, what is this
  person's work email, get a verified email for this contact, find the email address of a
  person at a company, or turn a short list of names into verified work emails. It screens
  the domain free first (MX check, disposable/trap-domain screen — dead domains cost
  nothing), runs Deepline's prebuilt email waterfall play (cascading sources, stopping at the first valid
  hit, so you only pay for what it finds) plus deliverability verification, switches to a
  recovery track on catch-all domains where validators lie, and ships only addresses that
  plausibly belong to the person — role addresses (info@, sales@) are rejected, catch-all
  and risky results are flagged, and every address names the source that produced it. Do
  NOT use it to check an address you already have (verify-email-deliverability), to
  bulk-clean an existing list or CRM (clean-email-list), to identify who a person is from
  an email you already have (reverse enrichment), or to source net-new prospects by
  persona (people search). It never guesses email patterns.
category: find-contact-data
personas: [sales-development]
mechanism: functions
touches: read-only
keywords: [waterfall]
ported_from: clay-run/clay-skill-creator/skills/clay/find-work-email
---

# Find a work email

The insight that separates this from typing `first.last@company.example` and hoping: **found is
not the same as sendable.** A pattern-guessed or unverified address burns sender reputation
when it bounces. So verification is part of the find, not an afterthought — and an honest
"not found" beats a fabricated address every time. And the deeper version of the trap: on a
catch-all domain, *verification itself lies* — the domain answers "deliverable" for every
address, real or invented, so a validator can neither confirm nor deny the mailbox. Those
domains need a different find, not a stronger validator.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **What they have per row** | a profile URL plus name, a name plus domain, or a name plus company name only | no default. Quality descends in that order, and the third route resolves the domain first — a wrong domain poisons every lookup, silently |
| **A known personal email** | if they have one | optional, and it raises the waterfall's hit rate. Pass it through when present |
| **Cost ceiling** | credits, and whether misses are acceptable | state per-row cost before running, and say plainly that a waterfall bills for attempts, not only for hits |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — what each row already carries, and the provider waterfall plus deliverability checks it runs.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, sends to an address, or guesses an email pattern.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json` (health, auth, and balance in one call). If `deepline` is
missing, run `npm install -g deepline && deepline auth register --wait auto`, then re-run
preflight. Tell the user which org you're in (`auth.org_name`) and the balance.

## Step 1 — Collect what identifies the person

Best → worst input quality:
1. **LinkedIn URL** (plus name/company) — highest match accuracy.
2. **Full name + company domain** — the standard case.
3. **Full name + company name only** — resolve the domain FIRST (`resolve-company-domain`;
   `crustdata_v3_company_identify` is free) and sanity-check it; a wrong domain poisons every downstream
   lookup and the failure is silent.

A personal email, if known, improves the waterfall's hit rate — pass it through.

## Step 2 — Free domain pre-gates (zero credits)

Screen the domain before the first paid lookup — a domain that fails here costs nothing
and poisons nothing downstream:

1. **MX check** (any DNS tool — never hardcode a DoH URL; some networks block them). Three
   shapes: **NXDOMAIN or no MX records** → the domain can't receive mail — report
   `not found (dead domain)` free, skip every paid step. **Null MX** (a single record
   `0 .`) → the domain *declares* it takes no mail — same verdict, even though a record
   "exists". **Real MX** → proceed.
2. **Trap/disposable screen.** Known disposable and spamtrap domains (mailinator,
   guerrillamail, yopmail, …) → `blocked: trap domain` — never find, never email. These
   are honeypots; one send can burn the sender's whole domain reputation.

## Step 3 — Run the prebuilt waterfall play

Pick the play by input (confirm the live contract with `deepline plays describe <id> --json`
— never promise a play you haven't described):

| Input | Play | Required fields |
|---|---|---|
| name + domain (+ LinkedIn URL if on file) | `prebuilt/name-and-domain-to-email-waterfall` | `first_name`, `last_name`, `domain`; optional `company_name`, `linkedin_url` |
| LinkedIn URL only | `prebuilt/person-linkedin-to-email` | `linkedin_url` |
| a CSV of either | the `-batch` twin (`...-waterfall-batch`, `person-linkedin-to-email-batch`) | `{"csv":"leads.csv"}`, plus `"columns":{"domain":"Website"}` when headers differ |

The name+domain play cascades ZeroBounce-gated pattern checks (first@, flast@,
first.last@, firstl@, firstlast@), then hunter → leadmagic → datagma → findymail → icypeas
→ prospeo → Deepline native → fullenrich → lusha → contactout → PDL, and stops at the first
candidate that `zerobounce_validate` grades `valid` **and** whose domain matches the input
domain exactly. Outputs: `email`, `email_source`, `email_validated`, `waterfall_attempts`
(per-leg outcome, including `validation_rejected` candidates with their
`validation_status`). The pattern legs never ship an unverified guess — only a ZeroBounce
`valid` mailbox — so they don't break this skill's no-guessing rule.

Cost: legs bill per their own pricing (`deepline tools describe <leg> --json`; e.g.
`hunter_email_finder` 0.3 credits/result, `zerobounce_validate` 0.28/result), and a miss
has paid for every validation it ran. Check the balance (`deepline billing`); beyond a
handful of lookups, pilot 2–3 rows, read the real charge from
`deepline runs get <run-id> --full --json`, then state the total and get explicit approval.

- **1–20 people:** `deepline plays run prebuilt/name-and-domain-to-email-waterfall --input
  '{"first_name":"Jordan","last_name":"Lee","domain":"northfield.example"}' --watch`.
- **Hundreds, or recurring:** run the `-batch` play on the CSV and
  `deepline runs export <run-id> --out <final.csv>`; the run's storage table keeps per-leg
  columns as provenance.

Set time expectations: a hit returns in seconds (the waterfall stops early), but a
not-found takes longer — the cascade exhausts every provider before giving up. A batch
containing bad rows finishes at the speed of its misses.

## Step 4 — The catch-all branch (where validation lies)

Detect it cheaply. The play already tells you: a `waterfall_attempts` leg with
`outcome: validation_rejected` and `validation_status: catch_all` means ZeroBounce graded
the domain catch-all and the play threw a real candidate away. Or run a validator on a
found address — `leadmagic_email_validation` (0.09 credits) returns `email_status:
catch_all` plus `is_domain_catch_all`; `bounceban_verify_single` (0.06) returns
`result: risky` plus `is_accept_all: true`. Either marks the **domain**, not just the
address. (A deliberately-invalid probe like
`test1234@` + domain validating as deliverable is the same diagnostic — the one place this
skill ever constructs an address, and it never ships: probes diagnose domains, only found
addresses ship.) One trap verified live: catch-all is a *per-validator verdict*, not a
domain fact — one validator resolved a specific mailbox as not-found on the very domain
another graded catch-all. Stay inside one validator's vocabulary end to end: detect with
the same validator whose mailbox probe you'll use for recovery, and never read one
validator's catch-all verdict into another's fields. The play's ZeroBounce `catch_all` is a
trigger only; the recovery validator's own domain flag (`is_domain_catch_all`,
`is_accept_all`) is the verdict you report.

On a catch-all domain the normal machinery breaks in both directions: validator-interleaved
find arms *discard real addresses* (every candidate comes back "unconfirmable"), and naive
acceptance *blesses bounces*. The production answer is a dual track, not a caveat:

- **Valid-domain track** (the default above): validator-interleaved waterfall; accept only
  verified-deliverable.
- **Catch-all track**: a second, WIDER find pass with **no validator interleave** — first
  found address wins, because per-arm validation on these domains only destroys candidates.
  Take the `candidate_email` values the play rejected as `catch_all` from
  `waterfall_attempts`, or run finder tools directly without validation gating
  (`hunter_email_finder`, `leadmagic_email_finder`, `icypeas_email_search`,
  `findymail_find_from_name` via `deepline tools execute`).
  Gate this track on employment confirmed current — an unverifiable address for a possible
  job-changer is a double risk.
- **Mailbox-level recovery**: run one catch-all-aware validator on the candidate and read
  its own pair. `leadmagic_email_validation`: `email_status: valid_catch_all` means
  engagement data confirms the mailbox (ship as valid, probe-confirmed); plain `catch_all`
  stays unconfirmable. `bounceban_verify_single`: `result: deliverable` with
  `is_accept_all: true` is the confirmed case, `risky` stays unconfirmable (it may return
  `status: verifying` — poll `bounceban_get_single_status`, don't resubmit). Check the
  field names in the first response. `allegrow_validate` (`safe` vs `dead_email`) is the
  costlier last layer for high-value contacts. This recovers a meaningful share (Clay
  production builds reported 20–40%, measured with Enrichley) of addresses the
  interleaved track would have thrown away.
- **Coalesce with provenance**: prefer the valid track; the status distinguishes
  `valid` / `valid, catch-all (probe-confirmed)` / `catch-all (found, unprobed — risky)`
  so the send side can throttle instead of treating all addresses alike.

Checking a single address you already have is `verify-email-deliverability`'s job — this
branch exists because on catch-all domains the *find itself* changes shape.

## Step 5 — The email-matches-contact check (anti-info@)

Before shipping, check that the local-part plausibly belongs to the person — a provider
that returns `info@company.example` for "Jordan Lee" found the *company*, not the person:

- Local-part carries a name token — `jordan.lee`, `jlee`, `jordanl`, `jordan` — → pass.
- Role/functional local-parts (info, contact, support, sales, admin, hello, office, team,
  billing, hr, press, marketing, careers, jobs, noreply, postmaster, abuse, webmaster, …)
  → **reject as this person's email**: report `rejected: role address`, never ship it in
  the email column.
- Ambiguous (handle-like, digit-mixed, no recognizable name correspondence) → precision
  over recall: flag for review rather than blessing — a wrong match sends someone's pitch
  to a stranger; a not-found costs nothing.

## What good looks like

- **Only verified-deliverable addresses ship as "valid"** — and on catch-all domains, only
  probe-confirmed ones. A found-but-unverifiable address is a flag, not a result.
- **Every shipped address names its source** — which track and which provider (the play's
  `email_source`) produced it. Provenance is what makes a fill rate auditable and a bad
  provider findable; production builds carry it as a twin column on every waterfall.
- **Not-found stays empty.** Never backfill with a pattern guess (`first.last@domain`) —
  that's fabrication with a bounce risk attached. And know the shape: a no-hit run
  completes successfully with `email: null` — completion is not data; gate on the
  presence of an actual address.
- **Know what the waterfall play does and doesn't tell you.** It returns an address only
  when ZeroBounce grades it `valid` — so its `email` column never carries catch-all/risky
  discrimination, and on a catch-all domain its interleaved verification discards real
  addresses (visible only in `waterfall_attempts`). When the send matters, add the explicit validation step and the catch-all
  branch.
- The common mistake: reporting whatever a single provider returns. One source's confident
  answer is exactly that — the waterfall, verification, and the matches-contact check are
  what make the result real.

## Rules

- MUST run the free domain pre-gates before any paid lookup; NEVER spend on or email a
  dead, null-MX, or trap/disposable domain.
- MUST resolve and validate the company domain before searching when given only a company
  name.
- MUST state cost and get approval before multi-person runs; re-check credits first.
- MUST run the email-matches-contact check; NEVER ship a role address (`info@`, `sales@`…)
  as a person's email.
- MUST ship provenance (track + provider) with every address.
- NEVER guess, construct, or pattern-infer a shippable address — domain probes are
  diagnostics, never results.
- NEVER report a catch-all address without its flag; unprobed catch-all is risky, not
  valid.

## Output

Per person: `name · company domain · email · status (valid / valid, catch-all
probe-confirmed / catch-all risky / rejected: role address / not found / blocked: dead or
trap domain) · source (track + provider)`, plus what identified them (LinkedIn URL or
name+domain). For multi-person runs, add a summary line: found-valid %, probe-confirmed %,
risky %, rejected %, not found %.

## Worked example

Ask: "Get me a verified work email for Jordan Lee at northfield.example."
MX check: real records — proceed. `prebuilt/name-and-domain-to-email-waterfall` with full
name + domain (+ LinkedIn URL if on file) → stops at `hunter_email`, ZeroBounce `valid`,
local-part `jordan.lee` matches the contact → `jordan.lee@northfield.example · valid ·
source: waterfall / hunter`.
Catch-all case: "and Casey Park at initech-consulting.example" — the play returns
`email: null`, but `waterfall_attempts` shows `casey.park@initech-consulting.example`
rejected with `validation_status: catch_all`: the domain accepts everything. Switch tracks:
take that candidate; `leadmagic_email_validation` → `valid_catch_all` → `valid, catch-all
(probe-confirmed) · source: catch-all track + hunter`. Had the probe stayed `catch_all`, the address ships flagged risky — the
user decides.
Counter-example: "someone called Alex at initech-consulting" → resolve domain first; the
waterfall returns only `info@initech-consulting.example` → `rejected: role address`, and with
nothing person-matched left → report `not found` — do not offer
`alex@initech-consulting.example` as a fallback.
