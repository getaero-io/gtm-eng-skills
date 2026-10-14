---
name: find-decision-makers-at-company
description: |
  Find the actual decision-makers at a specific company with Deepline — the named people,
  with title, LinkedIn, seniority, and current-employment evidence — for the thing
  YOU sell, not just whoever ranks highest. Use whenever someone asks: who are the
  decision makers at this company, find the VP of engineering at X, who owns
  marketing budget there, who would buy our product at this account, find the CFO or
  head of finance, build the buying committee for this account, or who should I
  reach out to at company Y. Works from a company domain plus what you sell or the
  function you target. Do NOT use it to source people across MANY companies by
  persona (build-prospect-list), to find a KNOWN person's profile
  (find-linkedin-profile) or email (find-work-email), or to research the company
  itself (company-research-brief). Built on role-scoped Deepline people search
  (crustdata_v3_person_search, or the company's real title roster via company_titles →
  search_contact) plus deterministic seniority/department mapping and employment
  verification — it never trusts a seniority ranking to answer a role question.
ported_from: clay-run/clay-skill-creator/skills/clay/find-decision-makers-at-company
category: find-contact-data
personas: [sales-development, account-executive]
mechanism: functions
touches: read-only
keywords: []
---

# Find decision-makers at a company

The insight: **the obvious tool answers the wrong question.** A "top people at this
company" lister returns the company's people ranked by seniority — it answers "who is
important here," while the buyer
of your product is a FUNCTION × SENIORITY pair ("who owns the budget for this
category"). A famous-CEO test passes coincidentally; for any real persona the
top-N list is confidently wrong. So this skill searches role-scoped from the start,
maps titles to seniority/department with deterministic rules, verifies current
employment on the person's own record, and frames who's the economic buyer vs the
champion — because "decision-maker" is a claim about budget authority, not fame.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The company** | a domain, preferably | a bare name is resolved to a domain and confirmed first — a wrong domain finds a different company's people |
| **What they sell** | the function they target, which is what defines the buyer | ask. This maps to target departments and a seniority floor; without it "decision maker" has no meaning |
| **How many people** | one economic buyer, or the committee | **up to five with roles framed is defensible** and must be stated |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the company you name and what you sell, plus Deepline people search.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or contacts anyone it finds.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline &&
deepline auth register --wait auto`, then re-run preflight. Tell the user which org
you're in and the balance. Confirm each tool this skill calls exists and read its
price: `deepline tools describe <tool_id> --json` (`pricing`) for
`crustdata_v3_person_search`, `company_titles`, `search_contact`,
`crustdata_v3_person_enrich`, and `crustdata_v3_company_identify`.

## Step 1 — Scope the target (interview; do not guess)

1. **The company** — domain preferred; a bare name resolves and confirms the domain
   first with the free `crustdata_v3_company_identify` (`{"names":["<name>"]}`) — a
   wrong domain finds the wrong company's people.
2. **What you sell / the function you target** — this defines the buyer. Map it to
   target departments + the seniority floor
   (`references/finding-mechanics.md` §Buyer mapping): e.g. spend management →
   Finance & Accounting, Director+; security → IT & Security, Director+.
3. **How many people** — one economic buyer, or the committee (buyer + champion
   candidates)? Default: up to 5 with roles framed.

## Step 2 — Search role-scoped (cents, not dollars)

Default arm: `crustdata_v3_person_search` filtered on the person's CURRENT employer
domain + the target function's title vocabulary (0.02 credits per returned row; empty
pages free — exact filter JSON and field paths in the reference). Widen the title
vocabulary before widening seniority — the miss is usually vocabulary ("Head of",
localized titles), not absence. When the role is nuanced and vocabulary guessing keeps
missing, switch to the roster arm: free `company_titles` for the company's real title
strings → pick the matching titles → `search_contact` with `title_lists` (0.56
credits per returned row). NEVER substitute a seniority-ranked lister for a role
question (the reference's §Why not the obvious function).

## Step 3 — Classify each candidate (deterministic first)

Map every returned title with the canonical rules — seniority by title-token
overrides (Chief/Founder/Owner → C-level; Director/VP → Executives; Senior/Lead/
Group → Non-Exec Management; product/program/project managers are ICs, the classic
misread), department by the 12-value enum. Keep candidates whose department matches
the target AND seniority clears the floor. Ambiguous titles go to an LLM pass only
after the deterministic rules, and its verdict must quote the title it ruled on.

## Step 4 — Verify employment (the anchor lies two ways)

- Your search anchor is a filter, not evidence — read the person's own current
  experience entries (`experience.employment_details.current[]`) for employer, title,
  and start date, and quote those (measured on Clay's people search, 2026-08: the
  record's `domain` field simply echoed the anchor).
- A mismatch may be a job change OR a concurrent role — multiple current roles are
  real; resolve through person enrichment, emit `multi-role` / `departed` /
  `unconfirmed` explicitly, never silently drop or keep.
- Ship the canonical LinkedIn URL (enrich the raw search hit if needed — the same
  person carries different slugs across sources); note role start date (a new-in-
  seat decision maker is a hook, not a defect).

## Step 5 — Frame the committee and deliver

Per person: `name · title · seniority · department · buying-committee role (economic
buyer / champion candidate / influencer) · LinkedIn (canonical) · employment
(current/multi-role/unconfirmed, with start date) · evidence (the record fields that
earned the row)`. Run summary: candidates examined, kept, rejected-by-reason, and —
when fewer than asked — an honest shortfall with which vocabulary/seniority was
searched. Zero matches is a RESULT: "no identifiable [function] leadership" beats
promoting whoever ranked first. Getting their email is find-work-email's job — hand
off, don't inline.

## What good looks like

- **Role fidelity** — every kept person's department matches what the user sells
  into; a CEO shows up only when the CEO is genuinely the buyer (tiny companies).
- **Employment is evidenced, not echoed** — the row quotes the person's own current
  employer + start date, never the search anchor.
- **The committee framing is explicit** — economic buyer vs champion changes the
  outreach; a flat list of five VPs isn't a committee.
- **Shortfalls are honest** — "found the Controller, no CFO identifiable" with the
  vocabulary searched, not a padded list.
- The common mistake: running the company lister and taking the top five. That
  produces the org chart's peak, not your buyers — measured live on Clay's managed
  "Find People at Company" function (2026-08): it ignored every name and role filter
  it accepted.

## Rules

- MUST search role-scoped (title vocabulary), never seniority-ranked, for role
  questions; MUST map titles with the deterministic overrides before any LLM call.
- MUST verify employment on the person's own record fields; mismatches resolve to
  multi-role/departed/unconfirmed explicitly.
- MUST gate on match count per role: multiple plausible economic buyers → present
  candidates, never silently pick one.
- NEVER fabricate a person, promote a role mailbox or a guessed name to a person, or
  pad a shortfall; NEVER present the top-N-by-seniority list as decision-makers.
- Cost posture: the search arm costs cents (0.02 credits per returned row on
  `crustdata_v3_person_search`); any further credit-bearing call (roster-arm
  `search_contact`, person enrichment for canonical URL / employment resolution) is
  stated per person first.

## Worked example

Ask: "Who would buy our spend-management platform at brightloop.example?"
Mapping: Finance & Accounting, Director+. Search: company anchor + title vocabulary
(CFO, VP Finance, Controller, Head of Finance) → 3 candidates. Classification:
CFO (C-level, Finance) → economic buyer; VP Finance (Executives, Finance) →
champion candidate; "Finance Program Manager" → IC by the manager-override rule,
dropped with reason. Employment: CFO's own record shows current role since 2025-11
(new in seat — noted as a hook); VP shows a second concurrent advisory role →
multi-role, kept with flag. Delivered: 2 kept + 1 rejected-with-reason + handoff
note ("emails: find-work-email"). 3 returned rows × 0.02 = 0.06 credits; no
enrichment spent.
