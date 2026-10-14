---
name: source-local-businesses
description: |
  Build a deduped, validated list of local businesses with Deepline — gyms, restaurants,
  clinics, retailers, agencies, any physical-location category — from a business type
  plus locations, or from a known brand whose locations you want. Use whenever
  someone asks: find local businesses in a city, source gyms in Brooklyn, build a
  list of HVAC companies near Austin, get all the coffee shops in these zip codes,
  list every location of a franchise brand, or scrape Google Maps listings.
  It asks the franchise question first (location or brand? — that decides the
  dedupe), discovers via the cheapest viable arm, normalizes domains before
  deduping, and ships unique, post-validated survivors. Do NOT use it to source B2B companies by firmographics
  (build-prospect-list), to find people at a company (find-decision-makers-at-company),
  to scrape an arbitrary non-directory page (scrape-any-website), or to research one
  business deeply (company-research-brief). Built on Deepline's Google Maps search
  (Serper, OpenWebNinja), Openmart store and brand records, and Maps detail lookups.
category: build-lists
personas: [founder, sales-development]
mechanism: functions
touches: read-only
keywords: [local-business]
ported_from: clay-run/clay-skill-creator/skills/clay/source-local-businesses
---

# Source local businesses

The insight: **local-business lists die by duplication and staleness, not by
discovery — and the dedupe key is a sales question, not a data question.** Finding
200 "gyms in Brooklyn" is trivial; delivering unique, open, in-category businesses is
the work, and whether 12 Crunch Fitness locations are 12 rows or 1 row depends
entirely on whether you sell to the franchisee or the brand. So this skill asks the
franchise question first, discovers with the cheapest viable arm, normalizes domains
before any dedupe (the same business surfaces under prefixes, subpaths, and vanity
URLs), and spends enrichment credits only on survivors.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **Category and locations** | the business type in their words, plus cities, postcodes or regions — or a known brand whose locations they want | no default; the brand case is a different route entirely |
| **The franchise question** | sell to the location or to the brand | ask. It decides the dedupe grain, and whether franchise-heavy results are signal or noise |
| **Target count and fields** | how many rows, and what each carries | ask — the fields decide whether the review-enrichment arm runs at all |
| **Cost ceiling and hard cap** | credits | state the arm arithmetic — pages × cost, enrichments × survivors — and a hard cap before anything runs |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the category and locations you name, via local business search.
- **Writes** — nothing. The deliverable is handed back to you.
- **Never** — writes to a CRM, enrolls anyone, or contacts a business it sourced.

## Step 0 — Verify Deepline is working

Run `deepline preflight --json`. If the CLI is missing, `npm install -g deepline && deepline auth
register --wait auto`, then re-run preflight. Tell the user which org you're in and the balance.
Verify the arms live before promising them — the catalog changes and the discovery-vs-brand
distinction below is a contract difference, not folklore (`references/sourcing-arms.md`).

**Resolve every arm you intend to use, and read its real price, before quoting anything:**

```
deepline tools search "local business google maps" --json   # the current candidates
deepline tools describe <tool_id> --json                     # real inputs, and the `pricing` block
```

Read the `pricing` unit before pricing a run: an arm billed per result returned (Serper Maps,
Openmart, OpenWebNinja) costs results × rate, not one flat number per call.

## Step 1 — Scope (interview; the franchise question is mandatory)

1. **Category + locations** — the business type in the user's words plus cities/zips/
   regions; OR a known brand whose locations they want (a different arm entirely).
2. **The franchise question** — sell to the LOCATION (each franchisee = a row; dedupe
   on place) or the BRAND (one row per parent; locations become a count)? This
   decides the dedupe grain and whether franchise-heavy results are signal or noise.
3. **Target count + fields** — how many, and what per row (name, address, rating,
   website, phone…). Fields drive whether the review-enrichment arm runs.
4. **Cost + cap** — state the arm arithmetic (pages × cost, enrichments × survivors)
   and a hard cap before anything runs.

## Step 2 — Pick the arm (references/sourcing-arms.md has live configs + costs)

- **Category discovery** → `serper_google_maps_search` (`"<category> in <location>"`,
  ~20 places/page, 0.04 credits per returned place ≈ 0.8/full page). Returns
  structured places (title, address, category, rating, ratingCount, phone, website,
  cid) — no scraping or selectors. `openwebninja_localbusiness_search` (0.06/result)
  is the structured alternative with `subtypes`/`business_status` filters;
  `openmart_search_businesses` (0.13/result) when you need its filters
  (`ownership_type`, `min_locations`/`max_locations`, rating/review bounds).
- **Brand locations** → `openmart_enrich_company` with the parent's `website` plus a
  `location` and `limit`: it resolves a KNOWN brand to its store records in a geo.
  This is not category discovery — the two jobs are different arms.
  `openmart_search_brands` returns one row per brand when the grain is the parent.
- **Depth on survivors only** → `openwebninja_localbusiness_business_details`
  (hours, emails/contacts with `extract_emails_and_contacts`) and
  `openwebninja_localbusiness_business_reviews` (0.06/review) AFTER dedupe — never
  enrich the raw haul.
- **Scale/recurrence honesty**: multi-city bulk (3+ cities or 500+ places) or a
  recurring refresh belongs in a Deepline play over a CSV of (category, location)
  queries — say so and offer the graduation instead of grinding pages ad hoc.

## Step 3 — Discover, bounded

Paginate with an explicit page cap stated up front. Per page: extract name, rating,
review count, address, and any website/detail fields the arm exposes. Every row
carries its source (page URL / call) and the raw fields. Empty or short pages end
pagination honestly — report the boundary, never loop past it.

## Step 4 — Normalize, dedupe, validate (free, in code)

1. **Normalize domains** before comparing: strip protocol/www/tracking, take the
   registrable label (public-suffix aware — naive split kills international TLDs),
   collapse subpaths; a missing website is normal for SMBs, key those rows on
   name+address instead.
2. **Dedupe per the Step-1 grain**: location grain → collapse exact place repeats
   (name+address); brand grain → collapse to parent (shared domain/brand name),
   carrying `location_count` as a column.
3. **Post-validate the category**: SERP keyword matching over-returns (a "gym"
   query returns physio clinics and supplement shops) — a cheap deterministic
   name/category screen first, and only genuinely ambiguous rows to an LLM pass
   that must quote what it ruled on.
4. Rows dropped at each gate are counted by reason — the funnel ships with the list.

## Step 5 — Enrich survivors and deliver

Only survivors get paid depth (hours/emails/review text via the detail and review
arms — costs stated). Deliver: per business `name · address · category-as-evidenced · rating ·
reviews · website (normalized) · phone · source`, plus the funnel summary: pages
pulled, raw rows, dupes collapsed (by grain), category rejects, survivors, credits
spent (measured per call). A shortfall against the target is reported with which
locations/pages were exhausted — never padded with off-category rows.

## What good looks like

- **The grain matches the motion** — a franchisee-seller gets locations; a
  brand-seller gets parents with location counts. One list can't serve both.
- **The funnel is visible** — raw → deduped → validated counts per stage; a list
  without its funnel hides how much noise it started as.
- **Domains are normalized before dedupe** — prefix/subpath variants of one business
  never survive as two rows.
- **Category is evidenced** — survivors match the ask by name/category evidence, not
  by having appeared in the search.
- The common mistake: enriching the raw haul. Dedupe and validation are free;
  enrichment isn't — spend order is the whole economics of this play.

## Rules

- MUST ask the franchise/grain question and state arm costs + a page cap before any
  run; MUST paginate bounded.
- MUST normalize domains (public-suffix aware) before dedupe; MUST post-validate
  category before enrichment; enrichment on survivors only.
- MUST ship the funnel (counts by rejection reason) with the list.
- NEVER pad a shortfall with off-category rows; NEVER present stale/closed
  businesses knowingly (a dead website on a survivor is a flag).
- NEVER grind ad-hoc pages past the cap or for recurring refreshes — graduate to
  a play and say so.

## Worked example

Ask: "Get me 50 independent coffee shops in Providence for our POS pitch."
Franchise question: selling to the LOCATION, but "independent" means franchise
brands are NOISE → location grain + brand-count filter (any brand with >3 locations
drops). Arm: `serper_google_maps_search`, 5 pages × ~20 places × 0.04 credits stated
and approved. Discovery: 96 raw rows. Normalize+dedupe: 81 places; brand filter drops 17 chain locations;
category screen drops 9 (two bakeries, a roastery-only, six restaurants that
serve coffee) → 55 survivors. Websites/phones come back in the Maps rows where
they exist (12 have none — normal for SMBs, keyed on name+address); detail lookup
only on the 50 requested, for hours. Delivered: 50 rows + funnel (96 → 81 → 64 → 55)
+ credits measured. Counter-ask: "list every Crunch Fitness in New England" —
`openmart_enrich_company` with the parent website per state, 0.13 per returned
store, no category search.
