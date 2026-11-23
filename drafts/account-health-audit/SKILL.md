---
name: account-health-audit
description: |
  Audit what your account records CLAIM against independently re-derived evidence, and deliver
  a reviewable field-by-field delta — never a silent overwrite. Point it at an account list or
  CRM export and the fields you actually rely on, and it re-derives each one from providers
  that did not populate it (Deepline company-enrichment tools from different vendors), then grades every field confirmed / contradicted / disputed /
  unverified with both values and their sources side by side. Use whenever someone asks: audit
  our account data, is our CRM telling us the truth, check whether our firmographics are
  stale, which accounts have bad data, or verify our account fields before we act on them. Do
  NOT use it to fill missing fields (enrich-account-list), to score or tier accounts
  (account-tier-scoring), to clean contact records (clean-and-refresh-contact-data), to merge
  duplicate records (dedupe-contacts), or to answer a question about accounts
  (account-intelligence-analyst). It writes nothing back: the delta is the deliverable.
category: verify-and-clean
personas: [revops]
mechanism: functions
touches: read-only
keywords: [crm-hygiene]
ported_from: clay-run/clay-skill-creator/skills/clay/account-health-audit
---

# Account health audit (claims vs independently re-derived evidence)

The insight: **re-running the provider that filled the field is not an audit — agreement with
yourself is not evidence.** Most "data audits" re-enrich from the same source that populated
the record, get the same answer, and report the book as clean. The record was never tested;
one function was asked to confirm itself.

But independence alone is not enough either, and this is the part that decides the design.
Two 1-credit enrichment providers (measured on Clay's enrichment actions, 2026-08), queried on
the same domain on the same day, returned
headcounts of **17,112 and 11,303** — 5,809 people apart, 51% above the lower figure, neither
flagged as uncertain. And worse:
**each provider contradicted itself inside its own payload.** One returned an exact count of
17,112 alongside a size band of `5,001-10,000`. The other returned 11,303 alongside a band of
`5001 to 10000` — which excludes it — *and* a second range field of `10001–20000`, which does
not. Three headcount claims in one record, two of them mutually exclusive.

So there is no source of truth to overwrite toward, and the deliverable cannot be a corrected
record:

1. **The delta is the finding.** The moment you overwrite, you have destroyed the evidence
   that a discrepancy existed. A field where two providers disagree by 51% is not a field to
   silently replace — it is a field nobody should be making decisions on until a human looks.
2. **Read the whole payload, not the field you asked for.** You do not need two providers to
   find a contradiction; you need to stop reading one key. Self-inconsistency is free, it is
   common, and it invalidates that provider's vote on the field.
3. **"Confirmed" requires agreement between independent sources**, not a successful API call.
   A call that returns a value has verified nothing.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Fields under audit** | only the fields they actually act on | ask what breaks when a field is wrong; auditing 40 produces a report nobody reads |
| **The record's claims** | the stored value per field per account | no default — this is the claim under test, and without it there is nothing to test |
| **Record scope** | all of them, or the segment that matters | ask — open pipeline, named accounts, the territory being replanned |
| **Per-field tolerance** | what counts as agreement for a count, a band, a location, a name | defaults are in step 6 and the installer overrides them: a 10% headcount gap is noise to one team and a tier change to another |
| **Budget ceiling** | credits | ask before any paid arm; step 3 states the cost and waits |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the fields under audit on the records you point it at, and the live sources it re-derives them from.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes back to the CRM or the source list — the delta is the deliverable.

## Step 0 — Verify Deepline and resolve the arms

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline && deepline auth
register --wait auto`, then re-run preflight. Tell the user which org they're in and the balance.

Find the candidate arms and resolve every arm you intend to use:

```
deepline tools search --categories company_enrich --json
deepline tools describe <tool_id> --json        # pricing + input/output schema
```

Two resolution rules that are not optional here:

- **Identify an arm by its full tool ID, never by a generic name.** "Enrich company" exists
  under several vendors at different prices (`crustdata_v3_company_enrich`,
  `prospeo_enrich_company`, `limadata_enrich_company`, `peopledatalabs_enrich_company`,
  `leadmagic_company_search`); the vendor is the arm, and the vendor decides both the data and
  the price.
- **Read each arm's `pricing` unit before pricing it.** Some arms bill per call, some per
  returned result, some per matched record, and some only after execution from usage. Details
  and the audit-relevant arms: `references/audit-arms.md`.

## Step 1 — Scope the audit (interview; do not guess)

1. **Which fields.** Only the fields the user actually acts on. Auditing 40 fields produces a
   report nobody reads; auditing the 5 that route territories or gate spend produces a
   decision. Ask what breaks when a field is wrong.
2. **What the record claims.** The stored value per field per account, as the audit's **claim
   under test** — never as a starting point to be improved.
3. **Which records.** All of them, or the segment that matters (open pipeline, named accounts,
   the territory being replanned).
4. **Per-field tolerance.** What counts as agreement for a count, a band, a location, a name.
   Defaults are in step 6; the user overrides them, because a 10% headcount gap is noise to
   one team and a tier change to another.
5. **Budget ceiling** in credits.

Say plainly at this point: **this skill writes nothing back.** If the user wants repair rather
than audit, they want a backfill motion, and the audit's delta is its correct input.

## Step 2 — Choose independent arms (the load-bearing choice)

Per audited field, pick **at least two arms that did not populate the record**. Independence
is what makes the check a check:

- If the record was filled by a provider, that provider's re-run is **not** a second opinion.
  Where the user knows the original source, exclude it and say you excluded it.
- Where the original source is unknown — the common case with an inherited CRM — use two arms
  from different vendors and state that provenance was unavailable, so "independent" means
  independent of each other rather than independent of the record.
- **Two arms is the minimum for a verdict, not a nicety.** With one arm every field is
  `unverified`, and the honest report says so rather than promoting a single opinion.

`references/audit-arms.md` lists the cheap company-enrichment arms with their Deepline prices
and the fields each returns. Two sub-1-credit arms are enough for a firmographic audit.

## Step 3 — State the cost and get approval

```
per account = Σ (cost of each arm, priced at the cap you will pass)
total       = per account × accounts
```

The audit has no early exit — a delta needs both readings, so every arm runs on every
in-scope account. That makes the quote exact rather than a ceiling, which is unusual and worth
stating. `limadata_enrich_company` (0.28 credits/call) plus `leadmagic_company_search` (0.34
credits/result) across 400 accounts is **248 Deepline credits**; give the number and get a yes
before spending. Re-read `pricing` from `describe` before quoting — this is the 2026-09 price.

Where a single richer arm returns several audited fields at once, prefer it over one arm per
field — one enrichment call (measured on Clay's `cpj-enrich-company`, 2026-08) returned
headcount, industry, HQ, founding year, revenue band, location count and a provider-side
freshness timestamp in a single call. `crustdata_v3_company_enrich` does the same in one call
when you pass the field groups you need (`basic_info`, `headcount`, `locations`, `revenue`);
omit `fields` and you only get `basic_info`.

## Step 4 — Free pre-gate: is the record even about a live company?

Before any paid arm, per account: a DNS/status probe on the stored domain (`dig +short`,
`curl -sIL` locally — free), then fetch the company's own site (`curl` locally, or
`firecrawl_scrape` at 0.02 credits/page when the site needs rendering). Three outcomes, all findings in their own right:

- **Dead or parked domain** → `anchor_failed`. This is the most severe audit finding available
  and it is free to obtain: every other field on that record is about a company that may no
  longer trade under that domain. Report it first, and do not spend paid arms on it.
- **Live but different entity** → `entity_mismatch`. The site does not match the stored
  company name — a rebrand, an acquisition, a holdings-vs-operating split, or a name
  collision. Also terminal for the record's other fields.

  **The arms can trigger this too, and they do not tell you.** Measured (on Clay's LeadMagic
  company action, 2026-08): a domain for a French
  medical-device company returned another country's company by name, LinkedIn slug, HQ and
  founding year — while echoing the input domain back in `websiteUrl` and `logo_url`, with
  `message: "Company found"` and no confidence or resolution field anywhere in the payload. So
  re-check identity **on the arm's own output**, not only on the stored record, and compare the
  arm's returned name/country against the anchor before using any of its field values.
- **Live and matching** → proceed to paid arms.

## Step 5 — Re-derive, and read the whole payload

Run the chosen arms: `deepline tools execute <tool_id> --input '{...}' --json` for up to ~20
accounts, a play with one `.withColumn` per arm beyond that (CSV in, both arms' raw payloads
kept as columns so the delta is reproducible). Then, per arm, **before comparing anything to the record**, check that
arm against itself on each audited field:

- Does an exact count fall **inside** the band the same payload reports? **Name which band —
  this is measured and it matters.** One arm (LeadMagic's payload, measured via Clay, 2026-08)
  returns two range fields; across six real accounts
  one of them contained the count **6 times out of 6** (it is evidently *derived* from the count,
  so checking against it is a tautology, not a check) while the other — the human-readable band —
  **contradicted the count in 3 of 6**. So compare against the band that is NOT derived, and
  verify which is which before trusting either.
- A stale band is **a defect in one field, not a disqualification of the arm.** Withhold the
  arm's vote on the FIELD that is inconsistent, never on the record — a count that a third arm
  corroborates is worth reporting with a caveat, not discarding.

  **Why this holds regardless of the rate.** Six real accounts had the human-readable band
  contradict its own count 3 times: a point estimate of 50% with an exact 95% interval of
  **[11.8%, 88.2%]**, which is too wide to publish as a rate and is not the argument. The
  argument is structural: whichever way the frequency falls, per-record withholding discards
  whole records over one stale field, and the derived range cannot discriminate anything.
- Does the payload report the same field twice under different names, with different values?
  Two range fields disagreeing with each other is the same defect.
- Is a numeric field a **saturation sentinel** rather than a measurement? A revenue of
  `999999999` next to a formatted range of `$100M to <$1B` is an encoding of "at the ceiling",
  and averaging or comparing it numerically treats a placeholder as a fact.
- Does a provider-side freshness timestamp exist? Where it does, use it — it is a better
  staleness signal than anything you can infer, and it costs nothing extra.

Never coerce across representations to force a comparison. A band is a band, a count is a
count, and a count inside a band is agreement — but a band never becomes a number.

## Step 5b — When arms agree on the band but differ on the count, the band arbitrates

Measured on two real accounts, one of each outcome. Both cases had **both arms reporting the same
band** and **counts 25–29% apart**, and they resolve differently:

| | shared band | counts | outcome |
|---|---|---|---|
| account A | 501–1,000 | 503 and **391** — one outside the shared band | **resolvable**: the outside count is the outlier, the other is corroborated |
| account B | 1,001–5,000 | 2,061 and 1,554 — both inside | **not resolvable at band granularity** |

So before grading, apply this:

- **Exactly one count outside the band both arms report** → that arm's count is the outlier for
  this field. The remaining count is corroborated *by the shared band*, and no third arm is
  needed. Grade on the surviving count and record which arm was set aside and why.
- **All counts inside the shared band** → the disagreement is real and the band cannot settle it.

And in the second case, **report two verdicts at two granularities rather than one shrug**: the
band is `confirmed` (both arms agree) while the count is `disputed`. "1,001–5,000 employees, and
two sources disagree on the exact figure within that band" is a usable answer; "cannot verify
headcount" is not, and it discards corroboration the arms actually produced.

Note the derived range cannot do this job. An arm's own `{start,end}` object brackets its own
count by construction, so it never contradicts its own arm and never arbitrates another's. Only a
band that two arms independently report has arbitrating power.

## Step 6 — Grade each field, in this order, stopping at the first match

The order matters and is not cosmetic: a payload can be both self-contradictory and in conflict
with the record, and the self-contradiction has to be resolved first because it changes who
gets a vote.

0. **`arm_entity_mismatch`** — an arm's returned identity (name, country, founding year,
   LinkedIn slug) does not match the anchor. **That arm is excluded entirely for this record**,
   because every field it returned describes a different company. This must be its own outcome
   and must never collapse into `disputed`: reporting "sources disagree" when one source is
   describing another company tells the reader their data is contested when it is not. Measured
   consequence of collapsing it — against a record that was CORRECT, the mismatched arm's
   `hq_country` would have produced `contradicted`, a false accusation rather than a shrug.
1. **`internally_inconsistent`** — at least one arm contradicts itself on **this field**,
   compared against its non-derived band. Recorded against that arm **for that field only**, and
   its vote on that field is withheld. Its votes on other fields stand. Then continue grading
   with the remaining votes.
2. **`unverified`** — fewer than two arms returned a usable value after withholding. No
   verdict on the record is possible; say so.
3. **`disputed`** — the arms returned usable values that do not agree with each other. **No
   majority means no verdict about the record**, whatever the record says — and a 51% gap
   between two providers lands here, which is the honest outcome.
4. **`contradicted`** — the arms agree with each other and differ from the stored value.
5. **`confirmed`** — the arms agree with each other and with the stored value.

Default agreement tests, overridable in step 1:

| Field type | Agreement means |
|---|---|
| Count (headcount, locations) | `|a − b| / max(a, b) ≤ 0.10` |
| Band string | identical after normalizing case, spacing and separators |
| Count vs band | the count falls inside the band's range |
| Name | matches after normalizing case, punctuation and legal suffixes |
| Location | same city and country; street-level differences are not disagreement |
| Domain | identical after normalizing scheme, `www.`, trailing slash, case |

Every verdict is exactly one of the five: the order makes them mutually exclusive, and rule 2
catches every case the later rules cannot reach, so no field is ungraded.

## Step 7 — Deliver the delta

Per account, per audited field: `stored value · each arm's value with its arm named · verdict
· the agreement test applied`. Never a single "correct" column — the point is that the reader
sees the disagreement.

Then the roll-ups that make it actionable:

- **By verdict**, counted: how much of the book is confirmed, contradicted, disputed,
  unverified, and how many records failed the free anchor.
- **By field**, because the pattern is usually per-field not per-account: a field that is
  `disputed` on 80% of records has a provider problem, not an account problem, and the fix is
  to choose a different arm rather than to correct 300 rows.
- **The anchor failures first.** A dead domain outranks every field-level finding on that
  record.
- **What it cost**, against the quote.

Then stop. The delta goes to a human, and a repair motion is a separate decision with a
separate approval.

## What this skill does not claim

- Two company arms were probed live (via Clay, 2026-08); none of the Deepline arms named here has
  been probed for the self-contradiction rates. Re-check field names and band behavior on the
  first response of each arm. The verdict mix across a real book is unmeasured.
- The free pre-gate stage is carried over from a sibling skill, not verified here.
- Where the audited record's original source is unknown — the common case — independence degrades to "independent of each other", and the output says so.

## What good looks like

- The user learns something they can act on about **a field**, not just about rows.
- No field is reported `confirmed` on the strength of one provider.
- Self-contradicting payloads are named, and their votes are visibly withheld.
- Nothing was written back, and the report says so.
- The common failure: re-enriching from the source that filled the record and reporting the
  book as clean. The second-worst: picking whichever provider agrees with the record.

## Rules

- MUST use at least two arms that did not populate the field; NEVER report `confirmed` from a
  single source, and NEVER treat a successful call as verification.
- MUST check each payload against itself before comparing to the record, and withhold the vote
  of any arm that contradicts itself on that field.
- MUST run the free anchor before any paid arm; NEVER spend on a record whose domain is dead.
- MUST grade in the stated order and report exactly one verdict per field.
- MUST show every arm's value next to the stored value; NEVER collapse them into one corrected
  column.
- MUST report `disputed` when arms disagree; NEVER break the tie toward the stored value, and
  never toward the provider that happens to agree with it.
- MUST identify arms by full Deepline tool ID and price them from `describe` `pricing` at the
  unit it states; NEVER name an arm by a generic action name.
- MUST treat a saturation sentinel as an encoded ceiling, not a measurement; a band never
  becomes a number.
- NEVER write back to the CRM or the source list. The delta is the deliverable.

## Worked example

Four fields audited on 400 accounts: headcount, industry, HQ city, domain. Two arms from
different vendors (`limadata_enrich_company` + `leadmagic_company_search`) → **0.62 credits per
account, 248 credits**, quoted exactly because the audit has no early exit. Approved. (The
payload values below were measured on Clay's `cpj-enrich-company` and LeadMagic actions,
2026-08; the shape of the reasoning is what carries over.)

The free anchor drops 11 records before any spend: 7 dead or parked domains, 4 entity
mismatches where the site belongs to a different company than the record names. Those 11 are
reported first and cost nothing.

On one account storing 8,000 employees: arm A returns an exact count of 17,112 alongside its
own band of `5,001-10,000`; the count is outside its own band, so arm A is
`internally_inconsistent` on headcount and its vote is withheld. Arm B returns 11,303 with one
range that excludes it and another that includes it — also `internally_inconsistent`, also
withheld. Two arms ran, both self-contradicted, so headcount grades **`unverified`**, and the
report says the field could not be audited rather than that the record is wrong. That is a
finding about the two providers, and the by-field roll-up is where it becomes visible.

HQ city: both arms return the same city and country as the record → **`confirmed`**. Location
count: arm A reports 12 sites, arm B reports 1 — a 92% gap, so **`disputed`**, and any
"do they have EMEA presence" decision resting on this field is not currently supportable.
Domain normalizes identically across both arms and the record → **`confirmed`**.

Across the book: headcount is `unverified` on 71% of records, entirely because both arms
self-contradict on it. That single line is the audit's most valuable output — it says stop
tiering on headcount from these two providers, which no per-account row would have revealed.
