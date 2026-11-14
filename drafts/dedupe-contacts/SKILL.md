---
name: dedupe-contacts
description: |
  Find duplicate contacts in a CSV, a Deepline play dataset, or a CRM export and produce a merge plan —
  which records are the same person, which record survives, and the evidence for every
  decision. Use whenever someone asks: dedupe my contacts, find duplicate leads, merge
  duplicate records, clean up duplicates in my CRM export, or "why does this person
  appear three times". It expands company domains to alias sets (regional TLDs,
  acquisitions, rebrands) so exact matching doesn't miss them, matches in confidence
  layers (exact email → email variants → personal identifiers → name+company fuzzy),
  picks a survivor per group by a 5-rule ladder, and delivers a dry-run merge plan for
  human approval. Do NOT use it to verify or clean email addresses on a list
  (clean-email-list / verify-email-deliverability), to mass-update CRM fields
  (CRM hygiene plays), or to dedupe accounts/companies by hierarchy (that is an
  account-level play). It never deletes or merges anything itself — no CRM writes, ever.
ported_from: clay-run/clay-skill-creator/skills/clay/dedupe-contacts
category: verify-and-clean
personas: [revops]
mechanism: logic-only
touches: read-only
keywords: [crm-hygiene]
---

# Dedupe contacts

The insight: **a duplicate is a claim that needs evidence, and a merge is a
destructive act.** An email or identifier match is near-certain; a name+company match
is only a *candidate* until a second signal corroborates it. Exact company matching
misses ~40% of true duplicates — companies carry many domains (regional TLDs,
acquisitions, rebrands) — so anchors must be alias-expanded first. And a merged
record must be ONE person's coherent state: mixing conflicting fields across records
fabricates a person who never existed. This skill flags; a human merges — the CRM
tools in Deepline are never called with a merge or delete here. This skill outputs a merge *plan* with
per-decision evidence and executes nothing.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The contact list** | a CSV, a table, or a CRM object pulled out first | no default — never dedupe a CRM blind |
| **Which fields exist** | email, name, company or domain, plus tiebreakers: created date, owner, profile URL, phone, opportunities | ask. Fewer fields means fewer match layers, not a failed run |
| **Domain knowledge** | parent and canonical domains, acquisitions, rebrands | this is the seed of the alias map. Without it, one company reads as several |
| **Where merges execute** | native CRM merge, a merge tool, or by hand | ask. This skill produces the merge plan; executing it is theirs |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the contact list you supply and the fields you say exist on it.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — executes a merge or deletes a record — it proposes the merges and you run them.

## Step 0 — Verify Deepline is working

A local CSV dedupe needs no Deepline at all and costs zero credits — skip to Step 1.
Deepline serves only the CRM-pull and redirect-probe arms: for those, run
`deepline preflight --json` (missing CLI → `npm install -g deepline && deepline auth
register --wait auto`) and say which org you're in.

## Step 1 — Collect inputs

1. **The contact list** — CSV, play dataset, or CRM object (pull CRM contacts out
   first, don't dedupe blind: `salesforce_list_contacts`, or `hubspot_list_objects`
   with `object_type: "contacts"` — both free through Deepline on your own CRM
   connection; page until done).
2. **Which fields exist** — email, name, company/domain, tiebreak fields (created
   date, owner, LinkedIn URL, phone, opportunities).
3. **Domain knowledge** — parent/canonical domains, acquisitions, rebrands: the seed
   of the alias map.
4. **Where merges will execute** — CRM native merge, merge tool, or by hand.

A full CRM cleanup runs dedupe FIRST: dedupe → hierarchy repair → field backfill —
repairing fields on records about to merge is wasted spend.

## Step 2 — Normalize before comparing (free, deterministic)

In code, never an LLM:
- **Emails**: lowercase; strip `+tag`; fold local-part dots ONLY on dot-insensitive
  providers (Gmail) — corporate mail treats `a.b` ≠ `ab`.
- **Names**: casefold, trim, strip initials/suffixes; map nicknames (Bob↔Robert).
  Keep raw values for evidence.
- **Company**: strip legal suffixes; normalize domains to apex. Keep BOTH keys per
  record — domain and name.
- **Identifiers**: normalize LinkedIn URLs and phones (E.164).

Inside a Deepline play the same transforms run as `run_javascript` columns — pure
string ops, no provider spend.

## Step 3 — Expand company anchors to alias sets

Per distinct domain, build an alias set with provenance, strongest first:
- **Deterministic**: the user's acquisition/rebrand/parent map, and redirect-follow
  (`generic_http_request` with `follow_redirects`, free — a `final_url` on another apex
  is proof). Full anchors.
- **Registrable-label family**: same label across TLDs (`kirivale.com` ↔ `kirivale.co.uk`).
  An ordinary anchor — the L3 pair still needs its second signal, as always.
- **AI-suggested** (candidates only, NEVER match-deciding): AI/web research may
  propose aliases (product domains, unlisted rebrands). Pairs matched only via an AI
  alias go to **review** even with a second signal; a human confirms the alias into
  the deterministic map and the pass re-runs. AI widens what gets *considered* —
  match decisions stay deterministic.

## Step 4 — Match in layers, tag every pair

- **L1 — exact**: identical normalized email → duplicate, **high**.
- **L2 — email variant**: same mailbox after plus-tag strip / provider-aware dot fold
  → duplicate, **high**; evidence = both raw strings.
- **L2-id — personal identifier**: same normalized LinkedIn URL → duplicate, **high**,
  even when names disagree (changed surnames). Phone is NOT a standalone identifier
  (company mainlines are shared); a slug mismatch never proves two people (one person
  carries different slugs across sources).
- **L3 — name+company**: names equal after normalization (or nickname-equivalent, or
  edit distance ≤ 2) AND company anchors match — like-for-like (domain↔domain,
  name↔name; bridge a domain-only row to a name-only row via the domain's first
  label) or through the alias sets, with the derivation in evidence. →
  **candidate, medium**; merges only with a second corroborating signal (same phone,
  LinkedIn, or title); otherwise **review**. If distinguishing fields *conflict*
  (different LinkedIn URLs, different direct phones) → **do-not-merge**: same name,
  same company, different humans is real.
- Same name at a different company (no alias path) is not a match at all.

## Step 5 — Pick the survivor, merge without mixing

Survivor per group by a deterministic 5-rule ladder — first rule that discriminates
wins:
1. **Parent-domain match** — exactly one record's domain equals the group's
   canonical/parent domain.
2. **Opportunity count** — most CRM opportunities/activity.
3. **Human owner** — over system/integration owners.
4. **Completeness** — most fields populated.
5. **Age** — oldest created date, final tiebreaker.

Merge semantics — the distinction that keeps records coherent:
- **Gap-fill is fine**: losers' non-empty values fill the survivor's EMPTY fields
  (highest-ladder-ranked loser first), with provenance.
- **Conflicts are never mixed**: where survivor and loser both hold differing values
  (title, company, phone…), the survivor's whole value set ships intact and losing
  values are recorded as conflicts in the plan. Never resolve conflicts
  field-by-field across records ("title from A, phone from B") — even
  most-recent-per-field fabricates a state no record ever held. If the user prefers
  freshest data, recency may reorder the *ladder* (whole-record), never per-field.

## What good looks like

- Every merge group carries: layer, evidence (raw values + alias derivation),
  confidence, the ladder rule that decided the survivor, per-field conflicts.
- The merged record is coherent — every non-gap-filled field traces to the survivor —
  and counts reconcile: input rows = survivors + merged-away (review and
  do-not-merge pairs stay separate rows).
- The collision pair is still two records; the AI-alias pair is still in review;
  nothing was deleted or written anywhere.

## Rules

- MUST deliver the dry-run merge plan for explicit approval; execution happens in
  the CRM/merge tool, never here.
- MUST require a second corroborating signal on L3, and reconcile row counts in the
  summary.
- MUST NOT mix conflicting field values across records — the survivor's block ships
  intact; conflicts are recorded, not resolved.
- NEVER let AI decide a match or merge — it may only *suggest* alias candidates,
  which stay in review until a human confirms them.
- NEVER delete records, execute merges, or write to a CRM.
- Scale note: matching needs every row in view, so keep grouping in one local pass
  over the full CSV (or a `deepline runs export` of a play's dataset); per-row play
  columns can normalize, never group.

## Output

A merge plan: `group · survivor (id) · merged records (ids) · layer (L1/L2/L2-id/L3)
· evidence (incl. alias derivation) · confidence · ladder rule · field conflicts`, a
**review** list (candidates + AI-alias pairs), a **do-not-merge** list (collisions,
with conflicting evidence), and a summary line: `N in → S survivors, M merged,
R review pairs, C do-not-merge pairs`.

## Worked example

Ask: "Dedupe this 14-row export; we acquired BrandX last year." L1 catches
`Ana.Ruiz@northfield.example` = `ana.ruiz@northfield.example`; L2-id merges `Maria Santos` /
`Maria Lee` on one LinkedIn URL. Alias pass: `Priya Nair / kirivale.com` merges with
`P. Nair / kirivale.co.uk` (label family + same phone); `Chris Doyle / brandx.example` with
`Chris Doyle / acme-corp.example` (acquisition map); an AI-suggested alias pair stays in
**review**. Ana's survivor wins on rule 2 (open opportunity); her title conflict
(`Manager` vs `Director`) is recorded — the survivor's `Manager` ships, the loser's
phone fills her empty phone field. Summary: `14 in → 9 survivors, 5 merged, 1 review
pair, 0 do-not-merge pairs`. No writes; the plan goes to the CRM merge screen.
