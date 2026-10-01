# The search surface — costs, contract, and what it will not tell you

Read from `deepline tools describe crustdata_v3_company_search --json`,
`crustdata_v3_company_search_autocomplete` and `free_simple_company_search` on **2026-09-30**.
Re-read `describe` at the start of every build: pricing and field lists change, and the cost
changes the design rather than only the budget. Observations marked "measured on Clay" come from
the Clay version of this skill (2026-08); they are cautions to re-check, not Deepline facts.

## Costs and caps

| Tool | Cost | Caps |
|---|---|---|
| `crustdata_v3_company_search` | 0.02 credits per **returned** row; empty pages free; billed on rows returned, not on `total_count` | `limit` 1–1000 (default 20); `in`/`not_in` ≤ 5 values |
| `crustdata_v3_company_search_autocomplete` | free | suggestions for one field |
| `free_simple_company_search` | free | one read-only SQL statement; `LIMIT` ≤ 100,000; ~35M-row corpus |

There is one currency: Deepline credits, against the org balance (`deepline billing balance`).
No separate search allowance exists to track.

## What the surface will tell you, and how far to trust it

### 1. A count — as a claim

- `crustdata_v3_company_search` returns `total_count` (`integer|null`, **optional** in the
  schema — read it defensively). A `limit: 1` probe reads it for 0.02 credits.
- `free_simple_company_search` answers `SELECT count(*) ... GROUP BY ...` for free, over coarser
  fields: `industry` (single text value), `location` (a "locality, region, country" string),
  `employee_count` (upper bound of a size bucket: 10, 50, 200, 500, 1000, 5000, 10000+),
  `year_founded`. Good for sizing slices before paying for them; not the same index as the
  search, so expect the numbers to differ.

Neither number is a TAM by itself. The enumerated, exhausted slice is.

### 2. No reliable identity — `domain` is a claimed attribute

Measured on Clay's company search by enumerating `domain = "<a major payment processor>"` to
exhaustion (2026-08):

```
33 records total, ALL carrying that domain
28 distinct company ids on one page alone
```

The records were not one company. They were unrelated micro-businesses, creators and small
organizations across several countries whose company page lists a payment link as its website —
one of them reporting a size band of `10,001+`. Any index built from company pages can carry the
same pollution; on Deepline, count records per `basic_info.primary_domain` (and check
`basic_info.all_domains`) on every build. Consequences:

| You might | It actually |
|---|---|
| dedupe the TAM on `domain` | merges unrelated organizations into one |
| count distinct domains as companies | undercounts wherever pollution clusters |
| dedupe on `crustdata_company_id` | keeps every polluted record — they are distinct records, not duplicates |

There is no key that fixes this at TAM scale. The workable move is to **flag rather than
resolve**: a domain shared by many records whose names, countries and size bands are mutually
unrelated is a pasted-link artifact, not a corporate family. Hold those records out as
`identity_unresolved`, count them, and list them.

## The contract that makes coverage provable

`crustdata_v3_company_search` returns:

```
companies[]      the page of records
next_cursor      pass as `cursor` for the next page; null when the result set is exhausted
total_count      the index's count of matching records (optional)
query            the query as executed
```

`next_cursor: null` with rows returned equal to `total_count` is the proof of completeness for
a slice. `next_cursor: null` with rows short of `total_count` is a contradiction to report, not
a market fact — grade the slice `truncated` and say so.

**`limit` defaults to 20.** The default does not change what you spend — billing is per row —
but it multiplies your call count 50× against a 1000-row page.

**Cursor replay is undocumented.** Assume a page you drop must be bought again; persist on
arrival (in a play, the Customer DB does this for you).

## Row shape (companies)

`basic_info`: `name`, `primary_domain`, `all_domains`, `website`, `professional_network_url`,
`employee_count_range` (**a band string**), `industries` (**an array**), `markets`,
`year_founded`, `company_type`, `description`; plus `crustdata_company_id`. Request more with
`fields` (e.g. `headcount`, `locations`, `funding`, `revenue`, `taxonomy`) — check on the first
page which ones actually populate for your slice.

`headcount.total` gives a number where the index has one; `employee_count_range` is the band.
Filter on the band for disjoint slicing; read the number as evidence, and say when it is
missing rather than promising one.

## Contract facts that change what an ICP can say

- **Function headcount filters**: `roles.distribution.<function>` (engineering, sales,
  marketing, …) filters by headcount in a function — `{"field":
  "roles.distribution.engineering", "type": "=>", "value": 5}`.
- **No null-handling operator.** Operators: `=`, `!=`, `<`, `=<`, `>`, `=>`, `in`, `not_in`,
  `(.)` fuzzy text, `[.]` exact token. A condition on a sparse field drops every record where it
  is null, and there is no `is_null` to OR back in. Keep sparse criteria post-enumeration.
- **`in` / `not_in` ≤ 5 values.** Longer arrays can be silently ignored — split into separate
  slices (which also keeps them disjoint).
- **Exact values come from autocomplete**: `crustdata_v3_company_search_autocomplete`
  `{"field": "basic_info.industries", "query": "software"}`; `query: ""` returns the most
  frequent values.
- Filters nest: `{"op": "and"|"or", "conditions": [ ... ]}`.
