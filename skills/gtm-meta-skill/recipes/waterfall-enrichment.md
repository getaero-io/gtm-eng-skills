# Waterfall Enrichment

The waterfall pattern runs multiple enrichment providers in sequence and stops as soon as one returns a valid result. This maximizes coverage while minimizing cost — you only pay for lookups that actually run.

## Key concepts

- `--with-waterfall <NAME>` — start a waterfall block named `<NAME>`
- `--with '{"alias":"step","tool":"tool","payload":{...},"extract_js":"extract(\"email\")"}'` — each waterfall step declares its own extractor
- `extract("email")` uses registry defaults; `extract(["data.email","email"])` uses explicit fallback paths
- `--end-waterfall` — close the block; the waterfall name becomes a column with the resolved value
- After `--end-waterfall`, use `{{<waterfall_name>}}` to reference the resolved scalar

## Always pilot first

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "email" \
  --with '{"alias":"provider_a","tool":"tool_name","payload":{"param":"{{Column}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"provider_b","tool":"tool_name","payload":{"param":"{{Column}}"},"extract_js":"extract(\"email\")"}' \
  --end-waterfall
```

Review output, then scale to `--rows 1:` for remaining rows.

## Phone waterfall

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "phone" \
  --with '{"alias":"mobile_finder","tool":"leadmagic_mobile_finder","payload":{"email":"{{Email}}"},"extract_js":"extract(\"phone\")"}' \
  --end-waterfall
```

## Email waterfall (name + company)

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "email" \
  --with '{"alias":"dropleads","tool":"dropleads_email_finder","payload":{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company_name":"{{Company}}","company_domain":"{{Company Domain}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"crust_profile","tool":"crustdata_person_enrichment","payload":{"linkedinProfileUrl":"{{LinkedIn}}","fields":["email","current_employers"],"enrichRealtime":true},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"pdl_enrich","tool":"peopledatalabs_enrich_contact","payload":{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"},"extract_js":"extract(\"email\")"}' \
  --end-waterfall \
  --with '{"alias":"email_validation","tool":"leadmagic_email_validation","payload":{"email":"{{email}}"}}'
```

## LinkedIn URL waterfall

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "linkedin" \
  --with '{"alias":"dropleads_people","tool":"dropleads_search_people","payload":{"filters":{"keywords":["{{First Name}} {{Last Name}}"],"companyNames":["{{Company}}"]},"pagination":{"page":1,"limit":1}},"extract_js":"extract(\"linkedin\")"}' \
  --with '{"alias":"pdl_identify","tool":"peopledatalabs_person_identify","payload":{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company":"{{Company}}"},"extract_js":"extract(\"linkedin\")"}' \
  --end-waterfall
```

## Pre-flight validation

Before running any waterfall, validate your input data:

```bash
# Check for required columns and empty values
python3 -c "
import csv, sys
with open('leads.csv') as f:
    rows = list(csv.DictReader(f))
cols = rows[0].keys() if rows else []
print(f'Columns: {list(cols)}')
print(f'Total rows: {len(rows)}')
# Check for empty required fields
for col in ['First Name', 'Last Name', 'Company']:
    empty = sum(1 for r in rows if not r.get(col, '').strip())
    if empty: print(f'WARNING: {empty} rows missing {col}')
# Check for duplicates (same person appears multiple times)
keys = [(r.get('First Name','').strip().lower(), r.get('Last Name','').strip().lower(), r.get('Company','').strip().lower()) for r in rows]
from collections import Counter
dupes = {k: v for k, v in Counter(keys).items() if v > 1}
if dupes: print(f'WARNING: {len(dupes)} duplicate contacts — deduplicate before enrichment to avoid paying for the same lookup twice')
"
```

**Skip rows that can't match:** If a row is missing both email AND name+company, no provider will find a match. Remove these before running to save credits.

## Realistic coverage expectations

Don't assume 100% fill rates. Actual coverage per provider:

| Data type | Single provider | 2-provider waterfall | 3-provider waterfall |
|-----------|----------------|---------------------|---------------------|
| Email | ~50% | ~65% | ~75% |
| Phone | ~30% | ~40% | ~45% |
| LinkedIn URL | ~65% | ~75% | ~85% |

Set expectations with stakeholders before running. Diminishing returns after 2-3 providers.

## Hard rules

- Always end with `leadmagic_email_validation` when the waterfall resolves email
- Use `--rows 0:1` pilot before any full run
- Do not reuse an existing output CSV path
- Chain one waterfall at a time; close `--end-waterfall` before starting another
- Use `extract("email")`, `extract("phone")`, `extract("linkedin")`, `extract("full_name")`, etc. on every waterfall step
- **Never call enrichment without minimum data**: email waterfalls need name + company OR LinkedIn URL. Phone waterfalls need a verified email. Don't waste credits on rows missing required fields.

## After a waterfall run

The Playground auto-opens for inspection:

```bash
deepline playground start --csv leads.csv --open
```

Use `--rows 0:1` in the playground to re-run a single block for debugging.
