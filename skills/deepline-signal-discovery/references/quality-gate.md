# Step 3 — Quality gate

`deepline enrich` returns control to the terminal before OS buffers fully flush to disk. Running `analyze_signals.py` immediately after enrichment can read a partially-written file where job columns for the last N rows haven't synced yet — resulting in `won_with_jobs: 0` or severely undercounted job data. Always verify file completeness before running analysis.

## Verify row count + job coverage

```bash
# 1. Check row count matches input
INPUT_ROWS=$(wc -l < output/{{company}}-icp-input.csv)
OUTPUT_ROWS=$(wc -l < output/{{company}}-enriched.csv)
echo "Input: $INPUT_ROWS rows, Output: $OUTPUT_ROWS rows"
# Output should equal input (both include header)

# 2. Spot-check job data for a known won account with job listings
python3 -c "
import csv, json, sys
csv.field_size_limit(sys.maxsize)
with open('output/{{company}}-enriched.csv') as f:
    rows = list(csv.DictReader(f))
won_rows = [r for r in rows if r.get('status') == 'won']
jobs_col = 'jobs'  # or use column index
has_jobs = sum(1 for r in won_rows if r.get(jobs_col, '').strip() not in ('', '{}', 'null'))
print(f'Won rows with job data: {has_jobs}/{len(won_rows)}')
# If this is 0 and you know won accounts should have listings, wait and re-run
"
```

If `won_with_jobs` is 0 but you expect job data:

1. Wait 5-10 seconds (OS buffer flush)
2. Re-run the verification check
3. If still 0, check column indices — the enriched CSV uses `website` and `jobs` column names, NOT `__dl_full_result__`. Use `--website-col N --jobs-col N` overrides.

## Coverage checks

After file verification:

- **Coverage**: >80% of companies should have website content. If <80%, check domain spelling and retry failed rows.
- **Content depth**: Average should be 6-8 pages per company, 12-20K chars.
- **Job listings**: Won companies should have more job data than lost (expected — larger/scaling companies win more).

If coverage is poor, re-run failed domains with `--rows` targeting specific rows.

## Domain validation (auto-extracted lists)

If customer domains came from automated extraction (CRM exports, Exa API, case study scraping) rather than a manually verified list, validate that domains actually belong to the named companies. **From actual runs: up to 53% of auto-extracted customers can be false positives** — competitors selling the same product, domain mismatches, and unrelated companies.

```bash
# Check for suspicious domain patterns
python3 -c "
import csv, sys
csv.field_size_limit(sys.maxsize)
with open('output/{{company}}-enriched.csv') as f:
    rows = list(csv.DictReader(f))
for r in rows:
    domain = r.get('domain', '')
    # Flag content platforms used as source URLs, not company domains
    if any(x in domain for x in ['blog.', 'medium.com', 'substack.', 'wordpress.']):
        print(f'WARNING: {domain} looks like a content platform, not a company domain')
    # Flag very short domains that might be generic
    if len(domain.split('.')[0]) <= 2:
        print(f'CHECK: {domain} — very short domain, verify it belongs to the expected company')
"
```

**Red flags for false positives:**
- Domain is a subdomain of the target company (blog.target.com)
- Domain belongs to a well-known AI/tech company but the "customer" is a different firm (domain resolution failed)
- Company appears in competitor case studies, not target's own customer list
- Company is itself a vendor in the same product category (they SELL the solution, they don't BUY it)
