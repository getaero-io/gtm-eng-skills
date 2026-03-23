# Column Execution Ordering

## The Core Rule

The `--with` flag in `deepline enrich` only **declares** a column's schema. The column value is empty until executed via `--execute_cells`. A column that references `{{another_col}}` will get an empty interpolation if `another_col` has not been executed yet.

**Consequence:** Declare all columns upfront, but execute them in dependency order.

---

## Required Execution Pattern

```
Stage 1:  Declare all independent columns (--output)
Stage 2:  Execute run_javascript columns first — they're local, free, fast
Stage 3:  Declare validation/AI columns that reference run_javascript output (--in-place)
Stage 4:  Execute all paid/API columns + the newly-added validation columns
Stage 5:  Declare merge column (--in-place, references stage 2+4 results)
Stage 6:  Execute merge column
Stage 7:  Export
```

### Why this order?

- `run_javascript` executes locally (no API calls, immediate)
- Validation columns need the permutation *value* already computed to interpolate `{{perm_fln}}`
- If you try to execute validation before permutation, `{{perm_fln}}` resolves to empty string → validation runs on empty email → worthless result

---

## Email Pipeline Example

```bash
# Stage 1: Declare schema (perms + providers + job_function)
deepline enrich --input seed.csv --output work.csv \
  --with "perm_fln=run_javascript:{...}" \
  --with "work_email_primary=cost_aware_first_name_and_domain_to_email_waterfall:{...}" \
  --with "job_function=deeplineagent:{...}"

# Stage 2: Execute ONLY the run_javascript column first
deepline csv --execute_cells --csv work.csv --rows 0:N --cols 7:7   # perm_fln col index

# Wait for run_javascript to complete (usually <15s for local JS)
sleep 15

# Stage 3: Add validation column AFTER perm_fln has values
deepline enrich --input work.csv --in-place \
  --with 'valid_fln=leadmagic_email_validation:{"email":"{{perm_fln}}"}'

# Stage 4: Execute providers + job_function + validation together
deepline csv --execute_cells --csv work.csv --rows 0:N --cols 8:11

# Wait for API columns (poll or fixed wait)
# Stage 5-6: Add and execute merge column
deepline enrich --input work.csv --in-place --with "work_email=run_javascript:{...merge logic...}"
deepline csv --execute_cells --csv work.csv --rows 0:N --cols 12:12
```

---

## Column Index Tracking

Column indices are assigned in declaration order, 0-indexed:

| Index range | Source |
|---|---|
| 0 … (seed cols - 1) | Seed CSV columns |
| seed_count | First `--with` column in Stage 1 |
| seed_count + 1 | Second `--with` column in Stage 1 |
| … | … |
| last_declared + 1 | First `--in-place` column (Stage 3) |
| last_declared + 2 | First `--in-place` column (Stage 5) |

Track indices explicitly in comments. The polling/wait loop in Stage 4 should watch all Stage 3+ columns, not Stage 2 columns (those are already done).

---

## Waiting Strategy

The `deepline csv --execute_cells` call *queues* jobs asynchronously. Poll for completion:

```bash
MAX_WAIT=900
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep 30; ELAPSED=$((ELAPSED + 30))
  EMPTY=$(deepline csv show --csv work.csv --format json --summary | python3 -c "
import json, sys
d = json.load(sys.stdin)
stats = d.get('_metadata', {}).get('__summary', {}).get('columnStats', {})
total_empty = sum(
  int(s.get('non_empty','0/0').split('/')[1].split()[0]) - int(s.get('non_empty','0/0').split('/')[0])
  for col, s in stats.items() if col in {'workemailprimary','validfln','jobfunction'}
)
print(total_empty)
" 2>/dev/null || echo "0")
  echo "${ELAPSED}s elapsed, ~${EMPTY} cells remaining"
  [ "$EMPTY" = "0" ] && break
done
```

For `run_javascript`-only columns: a fixed `sleep 15` is sufficient (no async queue needed).

---

---

## Conditional Row Execution (Only Run If Prior Stage Failed)

Running every column on every row wastes credits when a cheaper stage already found the answer. The pattern: after each "find" stage, filter to only the rows still missing a value, then run the next stage on that subset only.

### ⚠️ Critical: Filter BEFORE Adding Schema Columns

**Filter must happen BEFORE any `--in-place` adds the fallback columns.** If you filter after `--in-place`, the subset CSV already contains the fallback columns (empty), and enriching it again with the same column names creates duplicates or index mismatches.

**Correct order:**
```
1. filter_missing → MISSING_CSV   (has only cols added so far)
2. deepline enrich --in-place     (adds schema cols to work.csv)
3. deepline enrich MISSING_CSV → MISSING_WORK  (adds same cols fresh — correct indices)
4. execute on MISSING_WORK
5. merge_back MISSING_WORK → work.csv (fills the schema cols for missing rows)
```

**Wrong order (causes bugs):**
```
1. deepline enrich --in-place     (adds schema cols to work.csv + valid_fln/fallback)
2. filter_missing → MISSING_CSV   (MISSING_CSV now has valid_fln/fallback cols!)
3. deepline enrich MISSING_CSV → MISSING_WORK  (duplicate column names → wrong indices)
```

### Filter → Enrich → Merge Pattern

```bash
# 1. Run primary waterfall on ALL rows
deepline csv --execute_cells --csv work.csv --rows 0:$LAST_ROW --cols 7:7
# wait for completion...

# 2. Filter FIRST — before adding any fallback schema cols
filter_missing work.csv work_email_primary missing_email.csv
# missing_email.csv has cols 0-N (whatever work.csv had before fallback schema)

# 3. Add fallback schema to work.csv (empty; populated by merge_back later)
deepline enrich --input work.csv --in-place \
  --with "valid_fln=leadmagic_email_validation:{...}" \
  --with "work_email_fallback=person_linkedin_to_email_waterfall:{...}"
# work.csv now has cols 10=valid_fln, 11=work_email_fallback (empty for all rows)

# 4. Only proceed with fallback if there are missing rows
if [ -s missing_email.csv ]; then
  MISSING_LAST=$(( $(tail -n +2 missing_email.csv | wc -l | tr -d ' ') - 1 ))

  # missing_email.csv has cols 0-9 — enrich adds valid_fln=10, work_email_fallback=11
  deepline enrich --input missing_email.csv --output missing_work.csv \
    --with "valid_fln=leadmagic_email_validation:{...}" \
    --with "work_email_fallback=person_linkedin_to_email_waterfall:{...}"

  deepline csv --execute_cells --csv missing_work.csv --rows "0:$MISSING_LAST" --cols 10:10
  deepline csv --execute_cells --csv missing_work.csv --rows "0:$MISSING_LAST" --cols 11:11
  # wait...

  # 5. Merge fallback results into work.csv (only updates empty cells)
  merge_back work.csv missing_work.csv valid_fln work_email_fallback
  rm missing_email.csv missing_work.csv
fi
```

### When to Use

| Stage cost | Row count still missing | Use conditional? |
|---|---|---|
| Local (`run_javascript`) | Any | No — run all rows |
| Cheap paid (`leadmagic_email_validation`) | < 20% | Maybe — marginal savings |
| Expensive paid (provider waterfalls) | < 50% | Yes — meaningful savings |

**Rule of thumb:** `cost_aware_first_name_and_domain_to_email_waterfall` typically finds ~85%+ of emails. Running `person_linkedin_to_email_waterfall` (fallback) on only the remaining 15% cuts fallback costs by ~5-6×.

### Deepline `--rows` Limitation

`--execute_cells --rows` only accepts contiguous ranges (`0:5`, `10:20`), not sparse lists (`0,3,7,12`). The filter → separate CSV → merge pattern is the reliable workaround.

---

## Common Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| Validation returns results for empty string | `perm_fln` not executed before `valid_fln` was declared + executed | Execute `perm_fln` first (Stage 2), then add and execute `valid_fln` |
| Merge column returns null for all rows | One of the merge inputs wasn't executed before merge ran | Check that Stage 4 fully completed before Stage 5 |
| `{{col}}` interpolates to empty in prompt | Column declared but not executed | Run `--execute_cells` on that column, or move it to an earlier stage |
| Column index wrong in `--cols N:N` | New `--in-place` column shifted indices | Re-count from seed CSV length + declaration order |
| Fallback CSV has duplicate columns / wrong data | `filter_missing` called AFTER `--in-place` added fallback cols | Filter BEFORE adding schema cols. See "Filter BEFORE Adding Schema Columns" above |
| `merge_back` doesn't populate values | Target CSV missing the column names in `fieldnames` | Add columns via `--in-place` to work.csv before merging, even if empty |
