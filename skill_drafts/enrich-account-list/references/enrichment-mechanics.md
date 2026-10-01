# Enrichment mechanics — call contracts, normalization rules, composition map

Tool contracts verified with `deepline tools describe` 2026-09-30; re-verify per org.

## Identity call (free)

`crustdata_v3_company_identify` takes the same identifiers as enrich (`domains`,
`names`, or `professional_network_profile_urls` — exactly one type per call) and
costs nothing. Use it on every domain row before spend: no match → `not_found`;
several plausible candidates for a name → `ambiguous` (hand to
resolve-company-domain); one match → proceed.

## Enrich call (the core call, 0.8 credits per matched result)

- Input: `domains` (the VALIDATED domain, never the raw CRM value) plus explicit
  `fields`. Without `fields` only `crustdata_company_id` + `basic_info` return. For
  this skill: `["basic_info","headcount","revenue","locations","taxonomy"]`.
  ```bash
  deepline tools execute crustdata_v3_company_enrich --input '{"domains":["acme.com"],"fields":["basic_info","headcount","revenue","locations","taxonomy"]}' --json
  ```
  More than ~20 domains → a play over the deduped CSV with one `.withColumn` calling
  the same tool, then `deepline runs export <run-id> --out enriched.csv`.
- Response: one entry per submitted identifier, each with `matches[]` →
  `{company_data, confidence_score}`. Gate on values: an entry with empty `matches`
  is the routine miss (and does not bill). A low `confidence_score` on a name lookup
  is a review flag, not a match.
- Payload facts that bite (paths under `matches[0].company_data`):
  - `basic_info.employee_count_range` is a BAND STRING — `parseInt` yields the
    lower bound or garbage, `Number()` yields NaN, both flow through ternaries as
    false. Parse bands to ordinals; unparseable → `unknown`. `headcount.total` is an
    integer when present — prefer it for numbers, keep the band for display.
  - Industry: `basic_info.industries[]` and `taxonomy.professional_network_industry`.
    Founded: `basic_info.year_founded`. HQ: `locations.headquarters` /
    `locations.country`.
  - Revenue: `revenue.estimated.lower_bound_usd` / `upper_bound_usd` (a range, not
    a point) — absent on many private companies.
  - Identity cross-check: `basic_info.website` / `basic_info.primary_domain` against
    the input domain; `basic_info.all_domains` lists aliases. Disagreement =
    possible wrong-entity match → review flag.
  - `revenue.acquisition_status` is a hint toward `acquired`, never proof of
    liveness either way.
  - Field coverage (measured on Clay's Enrich Company on a 250-account golden set,
    2026-08, not a Deepline fact): ~80% of live companies enriched; industry filled
    on ~99% of enriched rows, size on ~95%. Plan the unknown column regardless — it
    will have content.
- Cost accounting: `deepline billing usage` shows the recent calls; only matched
  results bill, so measured spend lands at or under the declared estimate.

## Normalization rules (deterministic, free)

- Band → ordinal map: `1-10 → 1 · 11-50 → 2 · 51-200 → 3 · 201-500 → 4 ·
  501-1,000 → 5 · 1,001-5,000 → 6 · 5,001-10,000 → 7 · 10,001+ → 8` (strip commas
  and the "employees" suffix before matching; providers differ); emit BOTH raw band
  and ordinal (+ `headcount.total` or a midpoint when a number is genuinely needed).
- `unknown` is a value: absent/unparseable fields emit it explicitly; downstream
  gates must route unknown to their own state, never through a comparison
  (unknown-scored-as-zero silently disqualifies real accounts).
- Revenue arrives in mixed shapes (exact vs bands vs null per company class) —
  same discipline: raw + parsed + unknown.
- Enriched-at date rides every row: this is last-known data; freshness claims
  belong to a re-enrichment cadence, not to the payload.

## Identity screen (free, before any spend)

1. Public-suffix-aware domain normalization → dedupe to unique companies.
2. DNS: NXDOMAIN → `dead-domain`. HTTP probe (contract: non-2xx ERRORS with the
   status named; 2xx returns body only — canonical/og tags carry the redirect
   destination): dead/broken → `dead-domain`; a redirect to another registrable
   domain → validate the destination and note the hop.
3. Domain rows → `crustdata_v3_company_identify` (free) — one entity or not enriched.
4. Name-only rows → resolve-company-domain (verdicts flow back; only `resolved`
   rows are enriched).

## Composition map (what this skill does NOT do)

| Ask | Owner |
|---|---|
| messy names → domains | resolve-company-domain |
| tier/score the accounts | score-inbound-leads (formula/code discipline) |
| tech stack per account | detect-tech-stack |
| watch accounts for events | monitor-buying-signals |
| deep single-account brief | company-research-brief |
| find the buyers there | find-decision-makers-at-company |
| CRM writeback | the user's move (hubspot_batch_upsert_objects / salesforce_update_account when they ask) |

The play composes: resolver → THIS SKILL → scorer/researchers, each with its own
eval'd contract — a monolith that re-implements the neighbors is how account
builds rot.
