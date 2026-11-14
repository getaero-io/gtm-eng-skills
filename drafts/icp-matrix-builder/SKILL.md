---
name: icp-matrix-builder
description: |
  Turn an ICP described in your own words into an executable matrix — every dimension
  translated into the exact field and allowed value the platform will accept, classified as
  filterable now, verifiable later for a per-row price, or not observable at all. It reports
  what failed to translate instead of quietly dropping it, band-aligns every threshold you
  state, and hands off a filter set that runs and a verify set that is priced. Use whenever
  someone asks: define our ICP, build an ICP matrix or scorecard, turn our ideal customer
  profile into search criteria, which of our ICP criteria can we actually filter on, or set up
  our targeting definition. Translates against Deepline's CrustData company and person
  search vocabularies. Do NOT use it to score or tier a list against an ICP
  (account-tier-scoring), to enumerate the market it defines (tam-builder), to build a working
  prospect list (build-prospect-list), or to classify buyers (buyer-classification). The words
  teams use for their ICP mostly are not in the taxonomy, and it says so.
category: score-and-qualify
personas: [revops, founder]
mechanism: functions
touches: read-only
keywords: []
ported_from: clay-run/clay-skill-creator/skills/clay/icp-matrix-builder
---

# ICP matrix builder (translate, classify, price)

The insight: **an ICP is a vocabulary problem before it is a strategy problem, and the
translation fails silently in both directions.**

Measured on Clay's search taxonomy (2026-08): the industry taxonomy both axes filtered on had
**457 closed values**, and the five words a B2B team is most likely to use for its ICP matched
**none of them**:

| Your word | Values it matches in the taxonomy |
|---|---|
| `SaaS` | **0** |
| `B2B` | **0** |
| `Fintech` | **0** |
| `Healthcare` | **0** |
| `Cybersecurity` | **0** |

`Software` was not a value either — only compounds like `Embedded Software Products`. And short
terms are worse than useless with naive matching: `AI` substring-matched 53 values including
`Air, Water, and Waste Program Management` and `Airlines and Aviation`. Deepline's company search
(`crustdata_v3_company_search`) uses a different taxonomy (`basic_info.industries`,
`taxonomy.professional_network_industry`, `taxonomy.categories`), so the exact counts do not
carry over — but the shape of the problem does, and step 0 re-measures it on the live values.

Now the part that makes this dangerous rather than merely annoying. **Neither failure mode
errors.** A dimension that failed to translate either

- resolves to an unmatched value and **narrows to nothing** (an `in` condition on a value that is
  not in the set returns zero rows, and empty result pages are free, so nothing even shows up on
  the bill) — read downstream as "our market is tiny", or
- is dropped from the filter, or passed as an empty or over-fuzzy condition, and **restricts
  nothing** — read downstream as "our ICP is huge".

Both look like facts about the market. Neither is. So the deliverable is not a strategy
document; it is a **translation with a receipt**: every dimension mapped to a real field and a
real allowed value, everything that failed to map named, and every criterion that cannot be
filtered priced instead of quietly dropped.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The account axis** | what kind of company: industry, size, geography, revenue, funding, ownership | no default. Take it **verbatim**, including the parts that will not survive |
| **The persona axis** | who inside it: titles, seniority, function, tenure | no default |
| **The non-firmographic qualifiers** | tech stack, growth, funding stage, "enterprise-ready", "similar to our best customers" | collect these **explicitly** rather than letting them arrive as adjectives — they need pricing rather than filtering, and that is the finding |
| **Required versus nice-to-have** | which dimensions gate and which only score | their call, and it decides what goes in the filter versus the score |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the account and persona axes you define, and the qualifiers you supply.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM — the matrix is a definition you take elsewhere.

## Step 0 — Verify Deepline and pull the field metadata

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline && deepline auth
register --wait auto`, then re-run preflight. Tell the user which org you're in.

Pull the authoritative field lists and allowed values — **free, and never from memory**, because
taxonomies and allowed-value sets change:

```
deepline tools describe crustdata_v3_company_search --json   # account axis: filter fields + operators
deepline tools describe crustdata_v3_person_search --json    # persona axis: filter fields + operators
deepline tools execute crustdata_v3_company_search_autocomplete --input '{"field":"basic_info.industries","query":"software","limit":50}' --json
deepline tools execute crustdata_v3_person_search_autocomplete --input '{"field":"experience.employment_details.current.seniority_level","query":"","limit":50}' --json
```

Both autocomplete tools are free (verify with `deepline tools describe <id> --json`); they are the
only source of exact enum strings. Fields, operators, and the two axes' dialects are catalogued
in `references/field-vocabulary.md`.

## Step 1 — Collect the ICP in the user's words (do not translate yet)

Take it verbatim, including the parts that will not survive. Ask for:

1. **The account axis** — what kind of company. Industry, size, geography, revenue, funding,
   ownership type.
2. **The persona axis** — who inside it. Titles, seniority, function, tenure.
3. **The qualifiers they care about that are not firmographic** — tech stack, growth, funding
   stage, "enterprise-ready", "well-funded", "similar to our best customers". These are the ones
   that will need pricing rather than filtering, so collect them explicitly rather than letting
   them arrive as adjectives.
4. **Which dimensions are required and which are nice-to-have.** This decides what goes in the
   filter and what goes in the score, and it is the user's call.

Do not correct their vocabulary here. The mismatch is the finding, and you need their original
words to report it.

## Step 2 — Translate, and log every failure

Per dimension, resolve to a real field and real values from step 0's metadata. Three outcomes,
all recorded:

- **Translated** — the field name and the exact allowed values returned by autocomplete. Some
  terms (`Insurance`, `Manufacturing`) tend to exist as literal values; most do not.
- **Approximated** — no exact value exists, so the user chooses from candidates you present. For
  `SaaS`, that means picking specific `basic_info.industries` values, or a `taxonomy.categories`
  value, or a fuzzy `(.)` match on `taxonomy.professional_network_specialities`. **The choice is
  theirs**, presented with what each option costs in recall — never made silently on their behalf.
- **Untranslatable** — no field carries it. Say so, and move it to step 3's classification.

Two rules on matching, because both are verified failure modes:

- **Never substring-match a term under about five characters.** `AI` matching
  `Air, Water, and Waste Program Management` is not a near miss, it is noise that will look like
  a broad industry selection.
- **Never pass a value that autocomplete did not return.** An unmatched value narrows to
  nothing, and nothing is indistinguishable from a small market. `(.)` fuzzy matching is the
  opposite risk: it can match far more than the user meant — check a `limit: 1` count.

## Step 3 — Classify every dimension: filter, verify, or unobservable

This is the step that makes the matrix costable, and the classes differ in price by orders of
magnitude:

| Class | Meaning | Cost |
|---|---|---|
| **filter** | expressible in the search filters — narrows the population *before* you pay | free, inside the query |
| **verify** | not a filter; needs a per-row enrichment call *after* the population exists | credits × rows |
| **unobservable** | no arm carries it at all | declare it; never let it look satisfied |

A `filter` may additionally carry **`refine: verify`** — see below — when band alignment widened it
past the stated bound. That is a modifier on a filter, not a fourth class.

Which dimensions filter depends on the source, and it is not what teams expect. On Deepline's
company search, `funding.last_round_type` (stage), `funding.investors`, headcount growth
(`headcount.growth_percent.6m`), and `technographics.technologies.name` ARE filter fields — while
Fortune 500, unicorn status, "enterprise-ready", and lookalikes ("similar to our best customers")
are not. On the persona axis, contact availability is a filter
(`experience.employment_details.current.business_email_verified`), the addresses themselves are
not. Check every claimed filter against step 0's field list, not this paragraph.

A sparse filter field is still a recall decision: a technographics or funding filter excludes
every company the source never observed. When coverage is the issue, keep the dimension as
`verify` — e.g. `uses Salesforce` checked per row with `bloomberry_get_company_tech_stack` (0.43
credits per call on 2026-09-30) or `builtwith_domain_lookup` (usage-priced), applied to whatever
the filters already returned. Note the ordering consequence: **a verify dimension does not shrink
your spend, it multiplies it.** Put three verify dimensions in an ICP and every row of the eventual
market costs three enrichments before it is even qualified.

State per verify dimension: which arm, its per-row cost, and whether it is required (gates every
row) or nice-to-have (scored, not gated).

**One dimension can be both, and this is the case people miss.** A banded numeric filters coarsely
and verifies precisely: `50–2,000 employees` on a band field (`basic_info.employee_count_range`,
or the persona axis's `company_headcount_range`) selects every band that overlaps it — with LinkedIn-style bands (`51-200` … `1001-5000`) the
ceiling becomes 5,000 — and the stated
ceiling of 2,000 can only be enforced by an exact count. So classify it `filter` and add the modifier
**`refine: verify`**, naming the arm and its per-row cost, whenever band alignment widened the
dimension past what the user asked for. On the account axis there is a third option: the numeric
`headcount.total` field takes `=>`/`=<` directly — exact bounds, but every company with a null
count drops out. That is the same recall trade, moved.

Two things then have to be said out loud, because the alternative is a silent choice:

- **Accepting the band** means the ICP is now the wider range. Say which range.
- **Refining to the stated bound** costs a per-row call across everything the filter returned, and
  those calls are spent on rows that the refinement will then discard.

The classes stay mutually exclusive — `refine` is a modifier on a `filter`, never a third verdict —
and which one the user takes is their decision, priced.

## Step 4 — Band-align every threshold, and declare the rounding

Numeric criteria do not survive as stated wherever the field is banded, and **an arbitrary
threshold rounds to a band edge**:

- A stated `50–2,000 employees` cannot be expressed on a band field. Pull the band strings with
  autocomplete (`basic_info.employee_count_range`); with LinkedIn-style bands the nearest selection runs to
  5,000 (and the `50` edge falls in `11-50`). **That
  is not the ICP the user stated**, and the difference must appear in the output rather than
  being absorbed — or use `headcount.total` with exact bounds and declare the null exclusion.
- Revenue on the account axis is an estimate range (`revenue.estimated.lower_bound_usd` /
  `upper_bound_usd`), not a reported ARR. A stated `$10M ARR floor` becomes a condition on one of
  the two bounds — say which, because `lower_bound_usd => 10M` and `upper_bound_usd => 10M` are
  different markets.
- Funding fields (`funding.total_investment_usd`, `funding.last_round_type`) are null for every
  company whose funding was never recorded. A numeric or `in` condition excludes them. Keeping
  them takes an `or` group with a null-tolerant branch, or moving funding to `verify` — check the
  operator list in step 0 for what null handling the source supports, and state the choice.
  Excluding them is a deliberate tightening the user asks for.

**And the two axes use different dialects for the same bands.** The account axis filters
`basic_info.employee_count_range` / `headcount.total`; the persona axis filters
`experience.employment_details.current.company_headcount_range` /
`company_headcount_latest`. Pull each band vocabulary with its own autocomplete tool and
translate the same stated band twice. A matrix that carries one spelling to both axes fails on
one of them — silently, by narrowing to nothing.

## Step 5 — Emit the matrix

Four parts, and the last two are what make it honest:

1. **The filter set, per axis** — field names and exact allowed values, ready to execute. Account
   axis and persona axis stated separately, in each one's own dialect.
2. **The verify set** — dimension, arm, per-row cost, required or scored.
3. **The unobservable list** — declared, with what the user asked for in their words, so nobody
   later assumes it was applied.
4. **The translation log** — every dimension, its original wording, its outcome (translated /
   approximated / untranslatable), and for approximations which candidate the user chose and what
   was left out.

If the user wants weights and tiers on top, that is `account-tier-scoring`, and this matrix is
its input: the filter set becomes the gate, the verify set becomes the scored dimensions. If they
want to know how big the resulting market is, that is `tam-builder`.

## What this skill does not claim

- No real customer ICP has been translated, so the filter/verify/unobservable mix is unmeasured.
- The 24% taxonomy hit rate was measured on Clay's taxonomy against an author-written term list,
  not real customer briefs, and not re-measured on CrustData's.
- The `taxonomy.categories` / specialities fuzzy routes are named as approximations without
  having been tested for recall.

## What good looks like

- Every dimension in the output names a real field and real values, or is explicitly listed as
  approximated or unobservable.
- The user can see which of their words did not exist in the taxonomy, in a list, before they
  discover it as a strange result count.
- Band rounding is stated, not absorbed — the user knows their `50–2,000` became `51–5,000`.
- The verify dimensions carry per-row prices, so the cost of the ICP is visible at definition
  time rather than at run time.
- The common failure: accepting `SaaS` as an industry, passing it through, and reporting a market
  of zero as a market fact. The second-worst: dropping an untranslatable dimension silently, so
  the user believes a criterion is being applied when nothing is applying it.

## Rules

- MUST pull the field metadata live and translate against it; NEVER recall taxonomy values from
  memory, and never invent an allowed value.
- MUST report every untranslatable and approximated dimension; NEVER drop one silently, and never
  pick an approximation on the user's behalf.
- MUST classify every dimension as filter, verify, or unobservable, and price the verify set per
  row; NEVER let a non-filterable criterion sit in the matrix as though it filters.
- MUST band-align stated thresholds and declare the resulting range; NEVER present a band
  selection as though it matched the number the user said.
- MUST add `refine: verify` with its per-row cost wherever band alignment widened a dimension past
  the stated bound, and let the user choose the wider band or the paid refinement; NEVER pick
  between them silently.
- MUST translate bands separately for each axis, each from its own autocomplete; NEVER carry one
  spelling to both.
- MUST state how a funding filter treats companies with no recorded funding — kept via a
  null-tolerant branch, or deliberately excluded.
- NEVER substring-match a term shorter than about five characters against the taxonomy.
- NEVER pass an empty `in` array to narrow a dimension; omit the condition instead, and record the
  dimension as unapplied.

## Worked example

Stated ICP, verbatim: *"mid-market B2B SaaS in the US and UK, 50–2,000 people, $10M+ ARR, uses
Salesforce, and the buyer is a VP of RevOps or above."*

Translation log, as delivered:

| Their word | Outcome | Resolved to |
|---|---|---|
| `B2B SaaS` | **approximated** | no industry value exists for either word; user picked specific `basic_info.industries` software values from autocomplete, with a `taxonomy.categories` fuzzy match as the alternative they declined |
| `US and UK` | translated | `locations.country` `in` the two autocomplete spellings |
| `50–2,000 people` | **approximated + rounded, `refine: verify`** | account axis `basic_info.employee_count_range` bands → covers **51–5,000**, not 50–2,000 (band strings as autocomplete returned them) (or `headcount.total` `=>50` / `=<2000`, dropping null counts); persona axis needs its own `company_headcount_range` band strings. The user chose the wider band, with the exact ceiling priced as a per-row check |
| `$10M+ ARR` | **approximated** | `revenue.estimated.lower_bound_usd => 10000000` — an estimate, not ARR; the user accepted the lower bound as the stricter reading |
| `uses Salesforce` | **verify, not filter** | `technographics.technologies.name` exists as a filter but its coverage is unmeasured, so the user kept it as verify: `bloomberry_get_company_tech_stack` at 0.43 cr **per row** |
| `VP of RevOps or above` | translated | `experience.employment_details.current.seniority_level` `in` the VP-and-above values from autocomplete, plus `basic_profile.normalized_title.department` or a title condition for the function |

Delivered as: a filter set that runs on both axes in their own dialects; one verify dimension
priced at 0.43 credits per row and flagged as required, which means it gates every row of the
eventual market; nothing unobservable; and the rounding and estimate disclosures stated at the top
rather than buried — because `51–5,000` instead of `50–2,000` changes the market size before anyone
enumerates it.
