# Audit arms — verified costs, verified payloads, verified contradictions

> Measured on Clay's action catalogue, 2026-08. Arm keys, field paths and credit figures below are
> Clay facts, kept as evidence for the example's reasoning; resolve Deepline equivalents with
> `deepline tools search` / `describe` before reusing any of them.

Catalog read and four arms probed live on **2026-08-13**. Costs are each action's own
`metadata.upfrontCreditUsage.totalCost`, which matched the catalog every time. Re-resolve before
quoting: this file is the shape, not a price list.

## Identify an arm by `(packageId, actionKey)` — the key alone is ambiguous

**5 actionKeys in this catalog appear in more than one package**, and one of them differs in
price and in vendor:

| Key | Packages | Consequence |
|---|---|---|
| `enrich-company` | Owler (**10 cr**) · Clearbit (**8 cr**) | different vendor, different data, 25% price gap |
| `update-lead` | Close · Lemlist · Smartlead | **writes to whichever CRM resolves** |
| `create-contact` | Reply.io · Close | same |
| `pull-data` | Bright Data · PhantomBuster | different scraper entirely |
| `lookup-lead-in-campaign` | Lemlist · Smartlead.ai | different platform |

For a read-only audit the cost ambiguity is the issue. For the write-shaped keys it is a
correctness issue, and worth knowing even though this skill never writes.

## Cheap company-enrichment arms

| Arm | Cost | Required input | Notes |
|---|---|---|---|
| `icypeas-enrich-company` | 0.5 | **`linkedin_url`** | cheapest by price, but unreachable from a domain without a prior resolution call |
| `cpj-enrich-company` | 1 | `company_identifier` | accepts a bare domain; richest payload probed |
| `leadmagic-enrich-company` | 1 | none required (`domain` / `company_name` / `company_linkedin_url`) | accepts a bare domain |
| `datagma-enrich-company` | 2 | — | not probed |
| `enrich-company` (Clearbit) | 8 | `domain` | see the collision table |
| `enrich-company` (Owler) | 10 | `domain` | see the collision table |

**Cheapest by `creditCost` is not cheapest by reachability.** `icypeas-enrich-company` is 0.5 but
needs a LinkedIn company URL, so from a domain-anchored list it costs 0.5 plus a resolution call —
more than the 1-credit arms that take a domain directly, and one more failure point.

**`outputParameters` is declared on NONE of the nine arms checked.** There is no declared output
contract for this family at all, so the field lists below exist only because the arms were
executed. Treat any catalog-derived expectation about their output as absent rather than as a
subset.

## What the two 1-credit arms actually return

Probed on the same domain, same day. Field names verbatim.

| | `cpj-enrich-company` | `leadmagic-enrich-company` |
|---|---|---|
| Exact headcount | `employee_count` | `employeeCount` |
| Headcount band | `size` | `employee_range` **and** `employeeCountRange {start,end}` |
| Revenue | `annual_revenue` (band) | `revenue` (int) **and** `revenue_formatted` (band) |
| HQ | `locality`, `country`, `structured_locations[is_headquarters]` | `headquarter{city,country,geographicArea}` |
| All locations | `locations[]` + `structured_locations[]` + `structured_locations_count` | `locations[]` (HQ only in the probe) |
| Industry | `industry` | `industry` |
| Founded | `founded` (int) | `founded_year` (**string**) and `foundedOn.year` (int) |
| Type | `type` | `ownership_status` |
| Freshness | **`last_refresh`** (ISO timestamp) | — |
| Funding | `total_funding_amount_range_usd` (band) | `last_funding_round`, `funding_investor_count` |
| Self-reported cost | — | **`credits_consumed`** inside the result |
| Identifiers | `org_id`, `company_id`, `clay_company_id`, `slug` | `linkedin_url`, `b2b_url`, `companyId` (null) |

Two things worth using:

- **`cpj-enrich-company.last_refresh`** is a provider-side freshness timestamp. Where an arm
  offers one, it beats any staleness you could infer, and it is free with the call.
- **`leadmagic.credits_consumed`** duplicates Clay's cost metadata inside the payload. They agreed
  in the probe (1 = 1). A disagreement between them would itself be a finding.

Also: `cpj-enrich-company` returned **12 structured locations for 1 credit**, where
`enigma-get-operating-location-addresses` bills **0.8 per location** — 9.6 credits for the same
count. A richer flat-priced enrichment arm can dominate a specialised per-unit arm outright.

## The contradictions, measured

This is the evidence the skill is built on, and it is not a worst case — it is one probe of one
well-known company by two mainstream providers.

**Across providers:**

| Field | Arm A | Arm B | Gap |
|---|---|---|---|
| Exact headcount | 17,112 | 11,303 | **5,809 apart — 51% above the lower, 34% of the higher** |
| Location count | 12 | 1 | **92%** |
| Follower count | 1,623,116 | 1,345,345 | 21% |

Neither arm flagged uncertainty. Both returned `success: true`.

**Within a single payload — no second provider needed:**

- Arm A: `employee_count: 17112` with `size: "5,001-10,000 employees"`. **The count is outside
  the band the same payload reports.**
- Arm B: `employeeCount: 11303` with `employee_range: "5001 to 10000"` (**excludes** it) and
  `employeeCountRange: {start: 10001, end: 20000}` (**includes** it). Two range fields in one
  payload that disagree with each other.
- Arm B: `revenue: 999999999` beside `revenue_formatted: "$100M to <$1B"`. The integer is a
  **saturation sentinel** — one below 10⁹ — not a measurement. Any numeric comparison or average
  treats a placeholder as a fact.
- Arm B: `founded_year: "2010"` (string) and `foundedOn.year: 2010` (int). Same value, two types,
  one record.

**Corroboration on the headcount:** a third arm, `cpj-get-company-employee-growth` (1 cr, a
different action in the same package as arm A), independently returned **17,112** — matching arm A
exactly. So arm B's 11,303 is the outlier of the three readings, and arm A's own *band* is the
outlier within arm A. Neither of those conclusions is available from one call.

## What this means for grading

- **Do not pick a winner.** Two mainstream providers 51% apart on a basic firmographic is the
  normal case, not an anomaly, and there is no third source cheap enough to break every tie.
  `disputed` is the honest verdict and the report has to carry it.
- **Withhold the vote of a self-contradicting payload.** An arm that cannot reconcile its own
  count with its own band has no standing to arbitrate the record — and both probed arms failed
  this on headcount.
- **A count inside a band is agreement; a band is never a number.** The one comparison that is
  always safe across representations is containment.
