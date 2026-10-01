# Audit arms — Deepline prices, measured payloads, measured contradictions

Deepline arms and prices read from `deepline tools describe <id> --json` on **2026-09-30**. The
payload contradictions further down were measured on **2026-08-13** by probing two enrichment
actions through Clay; they describe the upstream providers' data, not a Deepline run. Re-resolve
before quoting: this file is the shape, not a price list.

## Identify an arm by full tool ID — "enrich company" alone is ambiguous

"Enrich a company" is a capability offered by several vendors in the Deepline catalog, at
different prices and with different payloads. The tool ID names the vendor; a generic name does
not. Same for write-shaped capabilities (`hubspot_batch_update_objects` vs
`salesforce_update_account` vs `attio_update_company_record`) — for a read-only audit the price
ambiguity is the issue; for writes it is a correctness issue, worth knowing even though this
skill never writes.

## Cheap company-enrichment arms (Deepline, 2026-09-30)

| Arm | Price | Input | Notes |
|---|---|---|---|
| `crustdata_v3_company_identify` | **free** | `domains` / `names` / `professional_network_profile_urls` | identity only — use it to re-check the anchor, not as an arm |
| `limadata_enrich_company` | 0.28 / call | `domain` or `linkedin_url` | returns `employee_range`, `industry`, `locations[].is_hq`, and `is_website_working` |
| `leadmagic_company_search` | 0.34 / result | `company_domain` / `company_name` / `profile_url` | same upstream as the arm B probed below; `employee_count`, `headquarter`, `locations[]` |
| `prospeo_enrich_company` | 0.55 / result | `company_website` / `company_name` / `company_linkedin_url` | description, industry, employee range |
| `crustdata_v3_company_enrich` | 0.8 / result | `domains` (+ `fields`) | pass `fields: ["basic_info","headcount","locations","revenue"]`; omitted `fields` returns only `basic_info` |
| `peopledatalabs_enrich_company` | 1.0 / result | `domain` / `name` | `employee_count` **and** `size` band in one payload — check them against each other |

**Cheapest by price is not cheapest by reachability.** An arm that needs a LinkedIn company URL
costs its price plus a resolution call from a domain-anchored list. Every arm above takes a bare
domain.

**Declared output schemas are partial.** `describe` shows an `outputSchema` for most of these, but
the payload often carries more (or differently named) fields than declared. Read the first real
response before writing any comparison against a field name.

## What the two 1-credit arms actually return (measured via Clay, 2026-08)

Probed on the same domain, same day, through Clay's `cpj-enrich-company` (Clay's own data
provider; no Deepline equivalent) and Clay's LeadMagic company action (Deepline:
`leadmagic_company_search` — field names may differ in Deepline's envelope; check the first
response). Field names verbatim from those probes.

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
| Identifiers | `org_id`, `company_id`, `slug` (+ a Clay-internal id) | `linkedin_url`, `b2b_url`, `companyId` (null) |

Two things worth using:

- **`cpj-enrich-company.last_refresh`** is a provider-side freshness timestamp. Where an arm
  offers one, it beats any staleness you could infer, and it is free with the call.
- **`leadmagic.credits_consumed`** reports the provider's own cost inside the payload. Compare it
  to the Deepline charge (`deepline billing usage`); a disagreement would itself be a finding.

Also (Clay pricing, 2026-08): `cpj-enrich-company` returned **12 structured locations for 1
credit**, where a per-location arm billed **0.8 per location** — 9.6 credits for the same count.
The lesson carries: a richer flat-priced enrichment arm can dominate a specialised per-unit arm
outright, so compare `pricing.unit` before picking.

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

**Corroboration on the headcount:** a third arm (Clay's `cpj-get-company-employee-growth`, a
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
