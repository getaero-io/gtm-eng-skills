# Growth mechanics — tool contract, payload shapes, surfaces, interpretation

Contract read from `deepline tools describe` on 2026-09-30. Re-verify per run —
prices, field names and payload shapes drift. The payload-shape findings below
marked "measured on Clay" came from Clay's `cpj-get-company-employee-growth`
action (2026-08-12); they are kept because the failure modes are provider-neutral,
but check them against the first Deepline response.

## The tool contract

| Fact | Value |
|---|---|
| Primary tool | `crustdata_v3_company_enrich` |
| Inputs | exactly ONE identifier type per call: `professional_network_profile_urls` (LinkedIn company URL — the high-accuracy arm) · `domains` (lower accuracy) · `names` (do not use; resolve first) · `crustdata_company_ids`. Each takes one or more values. Plus `fields` and `exact_match` |
| `fields` | **must include `headcount`** (and `basic_info` for the entity echo). Omitted, only `crustdata_company_id` and `basic_info` come back and every row looks like a miss |
| Cost | 0.8 Deepline credits / result at the time of porting — read `pricing` from describe; whether a no-match call bills is not stated, so read the pilot's billing |
| Outputs | per submitted identifier: `match_type`, `matched_on`, `matches[]` → `confidence_score`, `company_data.basic_info.{name, primary_domain, professional_network_url}`, `company_data.headcount.{total, growth_percent, growth_absolute, timeseries[]{date, employee_count}, by_function_timeseries, …}` |
| Window keys | `growth_percent` / `growth_absolute` keys: `mom` (1 mo), `qoq` (3 mo), `six_months`, `yoy` (12 mo), `two_years`. `crustdata_v3_company_search` returns the same data under `1m`, `3m`, `6m`, `12m` — do not mix key sets in one cohort |

Free helpers: `crustdata_v3_company_identify` (resolve domain/name → matched
profile URL and id, free; treat name-only results as unverified).

Alternative arm: `akta_headcount_trends` (input `company` = website or Akta UUID;
returns `data.total_employees`, `data.headcount_growth[]`, `data.growth_periods`,
`data.linkedin_official_name` as the entity echo; priced after execution from
usage). A different provider is a different measurement — pick one arm per
cohort, never waterfall the percentage.

Function-level engineering size only: `prebuilt/engineering-team-size`
(`deepline plays describe prebuilt/engineering-team-size --json`; input `domain`,
optional `company_headcount`, `method`). It is a level, not a growth rate.

## Payload shapes

**Hit** — numeric values:

```json
[{ "match_type": "professional_network_profile_url",
   "matched_on": "https://www.linkedin.com/company/acme-robotics",
   "matches": [{
     "confidence_score": 1,
     "company_data": {
       "basic_info": { "name": "Acme Robotics", "primary_domain": "acmerobotics.example",
                       "professional_network_url": "https://www.linkedin.com/company/acme-robotics" },
       "headcount": {
         "total": 412,
         "growth_percent":  { "mom": null, "qoq": 3.52, "yoy": 37.33 },
         "growth_absolute": { "mom": null, "qoq": 14,   "yoy": 112 } } } }] }]
```

(Illustrative shape built from the declared schema; values invented.)

- `basic_info.name` / `professional_network_url` / `primary_domain` echo the
  entity the tool MATCHED — the entity check compares them against the company
  you asked about. This echo is the wrong-entity detector; it matters most on
  domain-arm rows. Compare the asked identity's registrable LABEL (and name
  words), NEVER its TLD — a token like `com` substring-matches "company" in every
  LinkedIn URL and washes out the check. Shared-stem collisions (asked
  `meridianfintech.example`, matched "Meridian Health Group") are exactly what
  the check exists to catch: disjoint echo → wrong-entity flag; partial-stem
  overlap → judgment, say why you accepted it. A low `confidence_score` is a
  second reason to look.
- **Per-window nulls occur inside healthy hits** (measured on Clay: the 1-month
  and oldest windows were null even for large public companies). Null or absent
  window = no snapshot, never 0%.
- Base count for a window = `total − growth_absolute.<window>`. If
  `growth_absolute` is null for that window, read the nearest
  `timeseries` point instead and say so.

**Miss** — the call completes and `matches` is empty, or a match comes back with
no `headcount` section. Gate on payload VALUES (`headcount.total` present and
numeric), never on the call's success status.

**Wrong-entity hit** — shaped exactly like a hit; only the entity echo betrays
it. There is no error channel for "found a different company".

## Surfaces

| Surface | When | Notes |
|---|---|---|
| `deepline tools execute crustdata_v3_company_enrich --input '{...}'` | small lists (≤20 companies) | one call per arm; a call can carry several identifiers of the same type |
| A play over the CSV | batches | one dataset, route each row to its arm, persists to the Customer DB so reruns reuse filled cells |

Single row:

```bash
deepline tools execute crustdata_v3_company_enrich --input \
  '{"professional_network_profile_urls":["https://www.linkedin.com/company/acme-robotics"],"fields":["basic_info","headcount"]}'
```

Batch play sketch (check with `deepline plays check`, pilot on 3 rows with
`--debug`, then run the full file and `deepline runs export <run-id> --out <final.csv>`):

```ts
import { definePlay } from 'deepline';

type Row = { company_domain?: string; company_linkedin_url?: string };

export default definePlay('headcount-growth', async (ctx, input: any) => {
  const seed = await ctx.csv(input.csv);
  const rows = await ctx
    .dataset('headcount_growth', seed)
    .withColumn('growth', (row: Row, rowCtx) =>
      rowCtx.tools.execute({
        id: 'growth',
        tool: 'crustdata_v3_company_enrich',
        // one identifier type per call: URL arm when present, else domain arm
        input: row.company_linkedin_url
          ? { professional_network_profile_urls: [row.company_linkedin_url], fields: ['basic_info', 'headcount'] }
          : { domains: [String(row.company_domain)], fields: ['basic_info', 'headcount'] },
        description: 'Headcount and per-window growth for one company.',
      }),
    )
    .run({ key: 'company_domain', description: 'Headcount growth per company.' });
  return { rows };
}, { description: 'Headcount and 1/3/6/12/24-month growth per company from crustdata_v3_company_enrich.' });
```

Confirm `ctx.csv` / dataset signatures against
`deepline-gtm/references/plays-sdk-reference.md` before running; the
interpretation rules below run on the exported rows, not inside the play.

## Interpretation rules (deterministic — code, not judgment)

```javascript
// Bucket (12-month window default = growth_percent.yoy)
pct < 0    → "shrinking"
0 ≤ pct 10 → "flat"
10 ≤ pct 30 → "growing"
30 ≤ pct 100 → "high-growth"
pct ≥ 100  → "hyper-growth"

// Denominator gate — base = the window's backdated count (total − growth_absolute)
base < 50  → verdict carries "(micro-base: X→Y)"; the bucket label NEVER
             ships alone; sort/filter on absolute delta for micro-base rows

// Trajectory (short window S = qoq, long window L = yoy; both non-null)
// L/4 ≈ the year's average quarterly rate — S compares against it
L ≥ 10 && S < 0            → "reversing"   (grew over the year, shrinking now)
L ≥ 10 && S > L/2          → "accelerating" (last quarter is running ≥2x the
                             year's average quarterly pace — speed-ups are a
                             verdict too, not just slowdowns)
L ≥ 10 && 0 ≤ S < L/8      → "decelerating"
L < 10 && S ≥ 2.5          → "inflecting up"
otherwise                  → "steady <bucket>"
S or L null                → trajectory "single-window" — say which window
                             the bucket came from; never infer the missing one
// Backdated-count shape check: when headcount.timeseries shows a dip-and-
// rebound (12mo > 3mo-ago < now), say so — the windows alone smooth it out.
```

Thresholds are conventions, not truths — state them in the delivery so the
user can re-cut. The un-negotiable parts: base counts travel with every
percentage; two windows before a trajectory word; nulls never coerce to 0.

## Measurement caveats (ship with every delivery)

- Counts are professional-profile presence, not payroll: hourly, offshore,
  contractor-heavy, and franchise workforces undercount badly; consulting
  firms overcount alumni-heavy pages. Growth DIRECTION is more trustworthy
  than the absolute level; cross-provider count disagreement is normal.
- Data persists for dead and acquired companies (the enrichment-presence ≠
  liveness rule): a flat-line on a company with liveness doubts is an
  artifact, not stability — corroborate liveness separately before reading
  stability into it.
- New-hire counts and job postings measure GROSS adds / intent; this tool
  measures NET headcount. They diverge exactly when attrition is the story —
  don't substitute one for the other.
