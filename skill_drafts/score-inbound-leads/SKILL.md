---
name: score-inbound-leads
description: |
  Turn enriched inbound leads (person + company + ICP fields) into a composite score,
  an A/B/C/D tier, and a per-lead evidence trail — deterministic weights the user
  approves, every point traceable to a quoted field value, and a contact-validity gate
  so a dead email or departed contact never surfaces as a hot lead. Use whenever
  someone asks: score my inbound leads, tier these leads, rank this lead list by ICP
  fit, prioritize which signups sales works first, or build a lead scoring model in
  Deepline. Input is an ALREADY-ENRICHED lead set. Do NOT use it on raw emails or
  un-enriched signups — run enrich-signup-users first and score its output (if rows
  arrive partially enriched, score what's there to decide which rows earn enrichment —
  see the batch-economics note — but the full triage→enrich→rescore pipeline is its
  own play, not this skill). It classifies persona fit deterministically but does NOT
  source contacts (people search) or dedupe (dedupe-contacts). It STOPS at scores +
  tiers: routing leads to reps, CRM writeback, and sequence enrollment are the
  enrich-and-route-leads play. Scoring is pure computation — zero credits, no data
  sent anywhere, nothing written to any system.
ported_from: clay-run/clay-skill-creator/skills/clay/score-inbound-leads
category: score-and-qualify
personas: [revops, marketing]
mechanism: logic-only
touches: read-only
keywords: [lead-scoring]
---

# Score inbound leads

The insight: **a score nobody can explain is a score nobody trusts — and a score on a
contact who isn't reachable is worse than no score, because it spends a rep's morning
on a ghost.** The naive version multiplies magic constants into a number; a rep sees
"72", disagrees once, and the model is dead. Scoring here is four commitments: every
point **traces to a quoted field value** (evidence or it didn't happen); missing data
scores as **UNKNOWN with a stated policy** — never a silent zero, because "we couldn't
see their headcount" and "they're the wrong size" must never look the same; **weights
are a config the user approves**, not numbers you invented; and **validity gates the
score** — a tier is surfaced only for a contact who is demonstrably reachable and
current. Scoring is deterministic arithmetic — code, never an LLM (an LLM adds
variance to math a formula does for free), and the same input must produce the same
tiers on every re-run.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The enriched leads** | per lead: email and its type, person fields, company fields, any intent signals, and where the pipeline produced them, validity fields | rows that are just raw emails are not scoreable — say so and point at enrichment rather than scoring them anyway |
| **The ICP** | target industries, headcount range, geographies, buyer titles | **stop rather than defaulting.** Fit against an undefined ICP is fiction |
| **Disqualifiers** | competitor domains, blocked geographies, disposable-email domains | ask. An empty list is a real answer on a first run |
| **An account score column** | if one already exists | its presence changes the score shape, so ask rather than detect |
| **Weights and thresholds** | the config | proposed for **explicit sign-off**, never assumed. These are the installer's judgment about their own market |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the enriched leads you supply, your ICP, disqualifiers and weights.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — routes, writes to a CRM, enrolls in sequences, or sends anything — the score is the deliverable.

## Step 0 — Verify Deepline is working (only if needed)

Scoring itself costs zero credits and needs no Deepline call. Deepline matters only if
inputs are missing (route to enrich-signup-users) or the model graduates to a play (see
Output). Then run `deepline preflight --json`; if the CLI is missing, `npm install -g
deepline && deepline auth register --wait auto`, re-run preflight, and say which org
you're in. Don't hunt for a managed scoring tool: scoring is code territory
(`run_javascript` inside a play, or local code).

## Step 1 — Collect inputs (interview; never guess)

1. **The enriched leads** — CSV or table with, per lead: email + type (work/personal),
   person fields (name, title — may be empty), company fields (domain, industry,
   headcount, country), any intent signals (signup source, funding, product actions),
   and — where the pipeline produced them — **validity fields**: email verification
   status and employment currency (is the person still at the company). Rows that are
   just raw emails are not scoreable — run enrich-signup-users first.
2. **The ICP** — target industries, headcount range, geographies, buyer personas
   (title keywords). No stated ICP → stop and help write one; fit against an undefined
   ICP is fiction.
3. **Disqualifiers** — competitor domains, blocked geos, junk/disposable emails.
4. **An account score column, if one exists** — it decides the score shape in Step 2.
5. **Weights + thresholds** — propose the config in Step 2 and get explicit sign-off.

**Batch economics (rows not yet enriched):** the cheap move is to score FIRST on
whatever raw fields exist and enrich only rows above a floor — never enrich a whole
list and then discover 60% was junk. This skill's pass over partial rows (heavy
UNKNOWNs, many UNSCORED) works as that pre-score, but the full pre-enrichment gate —
triage → enrich survivors → rescore — is its own pipeline; route it to a dedicated
skill rather than looping enrichment in here.

## Step 2 — Propose the scoring config, get approval

Present a table the user edits: each component, its weight, what earns points, and the
UNKNOWN policy. A sane default (rescale to taste):

| Component | Weight | Scores on | If missing |
|---|---|---|---|
| Industry fit | 20 | company industry ∈ ICP list | UNKNOWN |
| Headcount fit | 20 | band overlaps ICP range | UNKNOWN |
| Geography fit | 10 | country ∈ ICP geos | UNKNOWN |
| Persona fit | 25 | title matches buyer keywords (seniority AND function) | UNKNOWN |
| Email type | 10 | work email = full; personal = 0 (known, not UNKNOWN) | — |
| Intent signal | 15 | stated signal present (funding, usage, source) | 0 (absence is data) |

Two UNKNOWN policies — the user picks one, in writing:
- **Neutral (default)**: renormalize by observed weight — `score = Σ(wᵢ·sᵢ) /
  Σ(wᵢ observed) × 100`. One line, deterministic, no AI "redistributing weights".
- **Penalty**: UNKNOWN scores 0. Honest only if the user says missing data should
  hurt — state that it conflates unknown with bad.

Guard either way: below half the total weight observed, the lead is **UNSCORED
(insufficient data)** — a fraction computed from two fields dressed as a percentage
is fabrication. Tier thresholds (0–100 score): A ≥ 75, B ≥ 50, C ≥ 25, else D — the
user's to move.

**Two score shapes** — pick by what the caller already has:
- **Flat composite (default)**: the weighted sum above, account and person components
  in one formula. Right for a single lead table with no account-grain scoring.
- **Composed — `account_fit × contact_fit × validity`**: when an account score
  already exists (an account-scoring build, a CRM field), **pull it in by lookup and
  use it as a factor — never recompute account fit per contact**: recomputing drifts
  (two contacts at one account scoring its fit differently is a credibility bug) and
  double-spends. Contact_fit is then persona + email type + intent only (account
  components drop out of the weights; renormalize), composed score =
  `account_fit × contact_fit / 100`, and validity is the Step 4 gate, not a
  multiplier. A row whose account-score cell is EMPTY is **UNSCORED** (the dominant
  factor is unobserved — never silently fall back to flat scoring mid-batch). Same
  evidence rules: the account factor's evidence line quotes the looked-up score and
  its source column.

## Step 3 — Normalize before scoring (deterministic, free)

- **Headcount arrives as a band STRING** ("1,001-5,000 employees"), not a number.
  Parse both ends (strip commas), compare the band against the ICP range as a range
  overlap — never `parseInt` the string and pray (that yields 1). An unparseable
  value is UNKNOWN, never a guess. An integer, if one appears, still gets `Number()`
  coercion: CSV numbers are often strings, and `"30" + "20"` is `"3020"`.
- Lowercase and bare-domain-normalize all domains before comparing.
- Title matching is keyword-anchored, case-folded: seniority terms (chief, VP, head
  of…) AND function terms (from the persona) must both hit. "Account Executive"
  contains no accounting; build exclusions in.
- Empty string, null, and "unknown" all normalize to one UNKNOWN vocabulary.
- **Validity fields normalize to a three-value vocabulary**: `valid` (email verified
  deliverable AND, where employment fields exist, employment current) · `invalid`
  (email verdict invalid/undeliverable, OR employment fields show the person departed
  — e.g. a former-employee relationship, or an employment-end date in the past) ·
  `unverified` (the fields simply aren't in the input). Map each validator's
  vocabulary explicitly — verdict semantics differ per validator, and catch-all hides
  inside "valid" on some; when in doubt, treat catch-all as `unverified`, not `valid`.

## Step 4 — Gates in order: DQ → validity → coverage → score

**Disqualifiers are a gate, not a component.** A lead at a competitor domain with a
perfect fit profile is tier **DQ**, full stop — a disqualifier beaten by a good score
is a policy violation, not a nuance. Check junk/disposable email, competitor domain,
blocked geo before computing anything. Record the tripped rule as the evidence. DQ
runs FIRST: it is a definitive verdict, so it beats both the validity lane and the
coverage guard (a competitor contact with a dead email is DQ, not re-verify).

**Validity gates the score — the departed-contact trap.** A high score on a contact
whose email bounces or who left the company last quarter is the worst output this
skill can produce: it looks hottest exactly when it's most wrong. Per the normalized
validity vocabulary:
- `invalid` → lane **RE-VERIFY** (re-verify the email / re-source a current contact
  at the same account), NEVER a scored tier — not even D. Compute account-fit
  components internally and record them as `refresh_priority` evidence so the
  re-sourcing queue works best-accounts-first, but the row surfaces in the RE-VERIFY
  lane, not the ranking. Re-verifying and re-sourcing are other skills'
  jobs (verify-email-deliverability, people search) — this skill only routes.
- `unverified` → the row scores and tiers normally but carries a visible
  `validity: unverified` flag, and the summary reports validity coverage. Gating on
  absent evidence would conflate unknown with bad — the same principle as the
  UNKNOWN policy — but the flag must survive into the output so nobody reads an
  unverified A as a verified one.
- `valid` → clean; the evidence line quotes the verification verdict and the
  employment field that proved currency.

Validity runs BEFORE the coverage guard: an invalid contact routes to RE-VERIFY even
when coverage is too thin to score — RE-VERIFY is a definitive next action, UNSCORED
is a shrug.

Then, per surviving lead, record a triple per component: **points · weight · the
quoted field value that earned them** ("headcount '1,001-5,000 employees' overlaps
ICP 50–5,000 → 20/20"). The evidence column is the deliverable — the score is just
its sum.

**Identity-miss ≠ account-miss** (the trap that throws away pipeline): a work-email
lead whose person never resolved still has a real company — score the account
components, mark persona fit UNKNOWN, flag `identity: unresolved`, and cap the tier
at B: a rep needs to know who they're calling before it's an A. A personal-email
lead with nothing resolved has no account either — UNSCORED or D, honestly.

## Step 5 — Tier, then prove determinism

Apply thresholds. Then **re-run the entire scoring pass and diff**: every score and
tier must be byte-identical. Any drift means something non-deterministic leaked in
(an LLM call, an unstable sort, a timestamp) — find and remove it. Sort output by
score descending with a stable tiebreak (email asc) so ranks don't shuffle.

## What good looks like

- **The expert reads the evidence column first, not the scores** — a score line that
  can't show its inputs is fabricated.
- **UNKNOWN is visible per component.** The common mistake is silent zeros: a C-tier
  lead that's actually "we know nothing" poisons trust in every real C.
- **The DQ row with great fit numbers is still DQ**, and **the perfect-fit row with a
  dead email is RE-VERIFY, not A** — the two gates catch opposite failure modes
  (wrong lead / unreachable lead).
- **A deliberate divergence from the upstream production canon, stated so
  users can own it**: the upstream playbooks score "cannot determine" as 0. This skill scores it
  as visible UNKNOWN and renormalizes instead, because zeroing conflates "we
  couldn't see it" with "it's bad" and silently demotes in-ICP leads with patchy
  data (live-verified: band-string headcounts make the zero path misfire with no
  error anywhere). Users who want missing-data-hurts choose the Penalty policy —
  explicitly.
- **Distribution sanity**: if >60% of leads are A-tier, the thresholds are flattery,
  not a model — say so and propose moving them.
- Same input, same output, twice.

## Rules

- MUST get explicit approval of weights, thresholds, disqualifiers, the UNKNOWN
  policy, and the score shape before scoring; MUST restate the config in the output.
- MUST score in deterministic code — NEVER let an LLM compute or adjust scores, pick
  weights, or break ties.
- NEVER surface a scored tier on a row with positive invalidity evidence (dead email,
  departed contact) — RE-VERIFY lane, no exceptions.
- NEVER recompute account fit per contact when an account score exists — look it up.
- NEVER score UNKNOWN as 0 silently; NEVER emit a score when observed weight < 50%.
- NEVER route, write to a CRM, enroll in sequences, or send anything — deliverable is
  the scored table; acting on it is the enrich-and-route-leads play.

## Output

Per lead: `email · tier (A/B/C/D/DQ/RE-VERIFY/UNSCORED) · score (0–100) ·
per-component breakdown (points/weight + quoted evidence) · unknowns · validity
(valid/invalid/unverified + the quoted verdict) · flags (identity: unresolved,
validity: unverified, tier-capped) · DQ reason / re-verify reason (+
refresh_priority)`. Plus a summary: config used + score shape, tier distribution,
UNKNOWN rates per component, validity coverage, determinism check result. At
recurring volume, graduate the approved config to a Deepline play: one `run_javascript`
column carrying the scoring code with the weights as named constants at the top so the
user can tune them, outputting `score` + `score_reasons`, run with `deepline plays run
<file>.play.ts --input '{"csv":"leads.csv"}'` and exported with `deepline runs export
<run-id> --out scored.csv`. No LLM column — the determinism rule holds in the play too.

## Worked example

Ask: "Score these 12 enriched trial leads. ICP: B2B SaaS, 50–5,000 employees, NA/EU,
buyer = VP+ marketing." Config approved: default weights, neutral UNKNOWNs, flat
shape (no account score exists). `vp.growth@brightloop.example`: email verified valid,
employment current → gate passes; industry "B2B software" 20/20 · band "201-500
employees" overlaps → 20/20 · US 10/10 · "VP Growth Marketing" 25/25 · work email
10/10 · no signal 0/15 → 85 → **A**, every line quoting its field.
`cto@meridianops.example`: perfect 90-point fit, but email verdict `invalid` →
**RE-VERIFY** ("email undeliverable; refresh_priority: account fit 50/50"), not A.
`vp.eng@stellarbase.example`: fit 85, but employment fields show she left in March →
**RE-VERIFY** (departed contact), not A. `ops@meridiansoft.example`: no validity fields →
scores normally, `validity: unverified` flag; person unresolved + headcount missing
→ both UNKNOWN, renormalized 64 → B (identity-capped anyway). `founder.zx4q19@gmail.example`,
nothing resolved: observed weight 25/100 → **UNSCORED**. `cmo@competitor-corp.example`:
fit would be 90, email also dead → **DQ (competitor domain)** — DQ beats the lane.
Summary: 12 in → 2 A, 3 B, 2 C, 1 D, 1 DQ, 2 RE-VERIFY, 1 UNSCORED; validity
coverage 10/12; re-run identical.
