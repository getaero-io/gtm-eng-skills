---
name: tam-builder
description: |
  Enumerate a total addressable market from an ICP definition with Deepline and report how
  much of it you can prove you have — a population figure with a per-slice coverage receipt,
  not a list of whatever fitted in one search. It partitions the ICP into disjoint slices,
  enumerates each to exhaustion, and marks every slice exhausted or truncated, so the TAM is
  stated exact where it is exact and a lower bound where it is not. Use whenever someone asks:
  how big is our TAM, size this market, enumerate every company matching our ICP, how many
  accounts are addressable, or build the full target-account universe. Do NOT use it to build
  a working prospect list of companies plus buyers (build-prospect-list), to source local
  businesses by place (source-local-businesses), to enrich a list you already have
  (enrich-account-list), or to audit stored fields (account-health-audit). Enumeration bills
  Deepline credits per returned row; the free corpus count costs nothing, and the quote states
  both.
ported_from: clay-run/clay-skill-creator/skills/clay/tam-builder
category: build-lists
personas: [revops, founder]
mechanism: functions
touches: read-only
keywords: []
---

# TAM builder (enumerate, then prove coverage)

The insight: **a TAM is a coverage claim, and a search surface sells you rows, not
coverage.** A market size needs a population count and a reliable identity, and neither
comes free of caveats:

- **A count is a provider's claim, not a population.** `crustdata_v3_company_search` returns
  a `total_count` (optional in its schema), and the free corpus (`free_simple_company_search`)
  answers `count(*)` with `GROUP BY`. Both are useful — and both are one index's opinion on
  fields with their own coverage holes. Two indexes will disagree, and neither is "the market".
  The count you can defend is the one you enumerated and checked against the claim.
- **The obvious identity key is polluted.** Measured on Clay's company search (2026-08): a
  query for one well-known payment processor's domain returned **33 organizations, all carrying
  that domain**, with 28 distinct company ids — micro-businesses and creators whose company page
  lists a payment link as their website, one of them claiming 10,001+ employees. Every index
  built from company pages inherits this. So `domain` is a *claimed attribute*, not a key.
  Deduping a TAM by domain merges unrelated companies; keeping every id keeps the junk.

What the search does give you is the one thing that makes an honest TAM possible: paging with
`cursor` until **`next_cursor` comes back null**, with rows returned matching `total_count`, is
a per-slice **proof of completeness**, not an estimate. So the whole design follows:

**Partition the ICP into disjoint slices, enumerate each to exhaustion, and report the TAM as a
sum of proven-complete slices plus explicitly-declared lower bounds.** A slice you stopped
paging early has not told you the market is smaller — it has told you your plan stopped
counting.

And the failure this prevents: one broad search returns 500 rows, someone writes "TAM: 500" on
a slide, and the number is the page size wearing a market's clothes.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The ICP dimensions** | industry, headcount band and HQ country are required; revenue band and tech or signal criteria as applicable | **stop rather than defaulting.** Mid-build ICP changes are the largest source of re-work here, and every enumerated row already billed |
| **Which dimensions are required versus nice-to-have** | the split | their call — it decides what filters and what merely scores |
| **The spend ceiling** | credits they will put into enumeration | ask. Enumeration bills per returned row, so the ceiling bounds which slices can be proven exhaustively |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the ICP dimensions you define, against Deepline's company search
  (`crustdata_v3_company_search`) and the free company corpus (`free_simple_company_search`).
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, or reports a market size beyond what the search actually returned.

## Step 0 — Verify Deepline, and read the costs before designing anything

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline && deepline
auth register --wait auto`, then re-run preflight. Tell the user which org they're in and the
balance.

Then read the contracts, because **the costs and caps change the design, not just the budget**:

```
deepline tools describe crustdata_v3_company_search --json
deepline tools describe crustdata_v3_company_search_autocomplete --json
deepline tools describe free_simple_company_search --json
# what those contracts mean for the design, and what they will NOT tell you:
# references/search-surface.md
```

| Tool | Cost | Cap that shapes the design |
|---|---|---|
| `crustdata_v3_company_search` | 0.02 credits per **returned** row; empty pages free | `limit` 1–1000 per page (default 20); `in`/`not_in` arrays ≤ 5 values |
| `crustdata_v3_company_search_autocomplete` | free | exact filter values only |
| `free_simple_company_search` | free | one SQL statement, `LIMIT` ≤ 100,000; coarse fields (industry, location string, employee-count bucket) |

**Enumerating a slice costs its row count × 0.02 credits**, so the balance and the user's
ceiling decide how many slices can be proven exhaustively. Say this before designing the
partition; do not design a 40,000-row enumeration and discover the ceiling mid-run.

## Step 1 — Lock the ICP in testable criteria (interview; do not guess)

Per the KB spine's stage 0, and for the same reason: **mid-build ICP changes are the largest
source of re-work**, and here every row enumerated under the old ICP is already paid for.

| Dimension | Operator | Value | Required? |
|---|---|---|---|
| Industry | IN | … | required |
| Headcount band | BETWEEN | … | required |
| HQ country | IN | … | required |
| Revenue band | ≥ | … | nice-to-have |
| Tech / signal criteria | HAS / WITHIN | … | as applicable |

Map every value through `crustdata_v3_company_search_autocomplete` (`{"field":
"basic_info.industries", "query": "software"}`) — the filter matches the index's vocabulary,
not the user's words. Two contract facts that change what you can ask for:

- **Function headcount is a filter.** `roles.distribution.engineering` (and the other
  `roles.distribution.*` fields) filters companies by headcount *in a function* — "companies
  with ≥ 5 engineers" is `{"field": "roles.distribution.engineering", "type": "=>", "value":
  5}`, a rich ICP criterion at no extra cost.
- **A filter on a low-coverage field silently shrinks the TAM, and there is no `is_null`
  operator to stop it.** The operators are `=`, `!=`, `<`, `=<`, `>`, `=>`, `in`, `not_in`,
  `(.)`, `[.]`. Filter on a sparse field (revenue estimates, funding, technographics) and every
  record where it was never populated is excluded — a *sparse field* becomes a *smaller
  market*. The recall-preserving default: keep sparse criteria OUT of the filter, request the
  field in `fields`, and apply it after enumeration, counting the nulls as their own bucket.
  Filtering on it is a deliberate tightening the user asks for.

## Step 2 — Partition into DISJOINT slices

The partition is the whole method. Slice on a dimension whose values cannot overlap, so that
every matching company falls in exactly one slice and the slice counts are summable:

- **Good partition keys**: HQ country, headcount band (`basic_info.employee_count_range`),
  founding-year range (`basic_info.year_founded`).
- **Bad partition keys**: anything semantic or multi-valued — keyword matches, descriptions,
  `(.)` fuzzy predicates, and `basic_info.industries` (an array per company: one company can
  sit in two industry slices). Two such slices overlap, and overlap is not just
  double-counted, it is **double-billed**.

Size each slice from the free count first (Step 3) so you know its enumeration cost before
paying it. When a slice is too large for the ceiling, step 4 subdivides it — the partition is
iterative, and that is expected rather than a failure.

**Disjointness by construction, never by dedupe-after.** You cannot fix an overlapping
partition after the fact: the rows are already paid for, and the identity field you would
dedupe on is the polluted one (see step 5).

## Step 3 — Size free, quote in credits, then get approval

Two free or near-free reads per slice, before any enumeration:

```
free corpus:   SELECT count(*) FROM companies WHERE <slice> LIMIT 1        ← free
search claim:  crustdata_v3_company_search {filters: <slice>, limit: 1}    ← 0.02 credits, read total_count
```

```
credits = Σ (search total_count per slice) × 0.02     ← enumeration
        + Σ (per-row cost of any validation or enrichment) × surviving rows
```

**State the free-corpus count and the search claim side by side** — when they disagree by a
wide margin the slice definition is matching different things in the two indexes, and that is
worth fixing before paying. Quote the enumeration credits against the balance and the user's
ceiling, and note that enumeration spend is not recoverable if the ICP changes afterwards.

Note also what search returns: rows carry `basic_info` (`name`, `primary_domain`,
`all_domains`, `employee_count_range` **as a band**, `industries`, `year_founded`,
`professional_network_url`, `description`), `crustdata_company_id`, and — when requested in
`fields` — `headcount.total`, `locations`, `funding`, `revenue.estimated`. Check which ICP
fields actually populate on the first page; a field that comes back null on most rows cannot
carry a filter (Step 1).

## Step 4 — Enumerate each slice to exhaustion

Per slice: call `crustdata_v3_company_search` with the slice's filters and `limit` set
explicitly (up to 1000; **the default is 20**, so leaving it unset multiplies your call count
without changing what you spend), then repeat with `cursor` = the previous `next_cursor` while
it is non-null. At more than a handful of pages, run it as a Deepline play (one row per slice,
paging inside) so pages persist in the Customer DB as they land.

Three rules, and the first is operational rather than analytical:

1. **Persist every page the moment it arrives.** Write each page to disk before requesting the
   next. Whether an old cursor can be replayed is not documented — assume it cannot, and treat
   a dropped page as paid-for data you must pay for again.
2. **Stop on a billing or rate-limit error and do not blind-retry.** Report how far the
   enumeration got, per slice, and the balance left.
3. **Record, per slice, the rows returned, the last `next_cursor`, and the `total_count`.** This
   is the measurement; the rows are just the by-product.

## Step 5 — Resolve identity WITHOUT the domain field

Measured on Clay's company search (2026-08): 33 organizations shared one payment processor's
domain, with 28 distinct company ids among them. Check the same thing on every Deepline build —
count records per `basic_info.primary_domain` — before trusting any domain. So:

- **Never dedupe a TAM on `domain`.** It merges unrelated organizations, and the more popular
  the platform whose URL got pasted, the worse the collapse.
- **Never treat one `domain` as one company** when counting. The count is of records, and
  records-per-domain is not one.
- **`crustdata_company_id` distinguishes records but does not identify companies** — many ids
  on a polluted domain are different organizations, not duplicates of one. Deduping on id keeps
  the junk; deduping on domain destroys the signal.
- The honest move at TAM scale is to **flag domain collisions rather than resolve them**:
  report how many records share a domain with other records, treat those records as
  `identity_unresolved`, and exclude them from the headline figure while listing them. A
  cheap tell for the specific pollution above: a domain shared by many records whose names,
  countries and size bands are unrelated is a pasted-link artifact, not a corporate family.

## Step 6 — Grade coverage, per slice then overall

Per slice, exactly one verdict, in this order:

1. **`exhausted`** — `next_cursor` came back null and the rows returned match `total_count`
   (or `total_count` was absent and the cursor still ran out). Every matching record has been
   returned. This slice's count is **exact** for this index.
2. **`truncated`** — enumeration stopped by your choice (ceiling reached, slice too big) while
   `next_cursor` was still non-null, or the cursor ran out with rows returned short of
   `total_count`. **Subdivide the slice on a disjoint key and re-enumerate**, or declare the
   slice a lower bound and say which.
3. **`incomplete`** — enumeration stopped for any other reason: a billing or rate-limit error,
   a failed call, an abandoned run. Not a statement about the market at all.

Then the overall figure, and its status is determined, not chosen:

| Condition | TAM figure |
|---|---|
| every slice `exhausted` | **exact** — the sum is the population matching the ICP in this index |
| any slice `truncated` or `incomplete` | **lower bound** — the sum plus "and at least this much more, unmeasured" |

The three slice verdicts are mutually exclusive by construction (cursor exhausted and
consistent with the claim, stopped short, or not finished), and the two overall states
partition on whether any slice is non-exhausted, so both ladders are single-valued.

**Never report a lower bound as a TAM.** "We found 2,140 accounts" and "the market is 2,140
accounts" are different claims, and only one of them is supportable when a slice was capped.
And never report an un-enumerated `total_count` or a free-corpus `count(*)` as the TAM — those
are claims to check, labeled as such when shown.

## Step 7 — Deliver

- **The figure, with its status** — exact or lower bound — stated in the first line.
- **The coverage receipt**: one row per slice with its criteria, free-corpus count, search
  `total_count`, rows returned, verdict, and for truncated slices what it was subdivided into or
  why it was not.
- **The list**, with `identity_unresolved` records separated out and counted, not silently
  dropped and not silently included.
- **The spend**: credits consumed on enumeration and on any validation, and the balance after.
- **What was excluded and why** — sparse criteria applied post-enumeration (with their null
  counts), slices declared lower bounds, records held out for identity collisions.

Hand the list on: `build-prospect-list` finds the buyers at these accounts,
`account-tier-scoring` tiers them, `enrich-account-list` fills them out. This play sizes and
enumerates; it does not enrich, score or contact.

## What this skill does not claim

- The multi-slice partition loop and the truncation rate are unexercised on Deepline.
- Whether `total_count` is exact or approximate on large slices has not been measured — check it
  against an enumerated slice on the first build.
- People-side TAM is out of scope for this version and not claimed.

## What good looks like

- The headline number carries "exact" or "lower bound", and the reader knows which without
  asking.
- Every slice has a verdict, and a truncated slice was either subdivided or declared.
- Nobody deduped on domain.
- The quote named the free counts, the enumeration credits, and the balance remaining.
- The common failure: one broad search, 500 rows returned, "TAM = 500" — the page size reported
  as a market. The second-worst: a filter on a sparse field, quietly excluding every company
  whose field was never populated.

## Rules

- MUST read the tool contracts and the balance before designing the partition; NEVER design a
  slice plan the ceiling cannot execute.
- MUST partition on disjoint, single-valued keys; NEVER partition on semantic or multi-valued
  predicates, and never fix an overlapping partition by deduping afterwards.
- MUST record rows returned, `total_count` and the final `next_cursor` per slice and grade it;
  NEVER treat a slice you stopped paging as evidence the market is small.
- MUST report the TAM as a lower bound whenever any slice is truncated or incomplete; NEVER
  present a capped enumeration, a `total_count` claim, or a free-corpus count as a population.
- MUST persist each page on arrival; a dropped page is paid data lost.
- MUST keep low-coverage criteria out of the filter (no `is_null` fallback exists) and apply
  them post-enumeration, or state that filtering on them was a deliberate tightening.
- MUST quote enumeration credits with the free counts and the balance remaining; NEVER quote an
  enumeration as free.
- NEVER dedupe or count on `domain`, and never treat one domain as one company.
- NEVER put more than 5 values in an `in` / `not_in` array — the provider can silently ignore
  longer arrays, which corrupts the slice without an error.
- MUST stop on a billing or rate-limit error and report progress; NEVER blind-retry it.

## Worked example

ICP: software companies, 50–2,000 headcount band, HQ in US / CA / UK. Balance: 600 credits; the
user caps enumeration at 50 credits and any single slice at 1,000 rows.

Partition on the two disjoint keys the ICP already names: 3 countries × 3 headcount bands =
**9 slices**. Free corpus counts per slice come back in the hundreds; a `limit: 1` probe per
slice reads `total_count` (9 × 0.02 = 0.18 credits) and sums to ~2,600. Cost quote: **~2,600
rows × 0.02 = ~52 credits** of enumeration — just over the ceiling, flagged up front, plus **0 credits** of enrichment because none is
requested — and the quote says so explicitly rather than omitting the line.

Eight slices end with `next_cursor: null` and rows matching `total_count` → `exhausted`, exact
counts. The ninth — US, largest band — claims 1,900; the per-slice cap stops paging at 1,000
with the cursor still live → `truncated`. It is subdivided on a third disjoint key
(founding-year range) into three sub-slices; two exhaust, one is declared a lower bound rather
than enumerated further, because the 50-credit ceiling for this run is nearly spent and saying
so is better than spending more without asking.

Identity: 47 records share a `primary_domain` with at least one other record. Sixteen of those
are clearly one corporate family; 31 carry a payment-platform domain alongside unrelated names,
countries and size bands, and are held out as `identity_unresolved`.

Delivered: **"At least 2,412 accounts match this ICP — a lower bound. 8 of 9 slices are
exhaustively enumerated; one is capped."** Then the nine-row coverage receipt (free count,
search claim, rows, verdict), the 31 held-out records listed, and ~49 credits consumed with ~551
remaining.
