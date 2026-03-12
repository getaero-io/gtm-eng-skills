# Script Templates

## Setup: `.env.deepline` file (one-time)

Create this once per migration project. **Never commit it.** Uses `.env.deepline` (not `.env`) to avoid conflicting with any existing project environment files.

```bash
# .env.deepline — Clay credentials (migration-specific, never commit)
# Get from: browser devtools → Network → any api.clay.com request → Request Headers → Cookie
CLAY_COOKIE="claysession=<value>; ajs_user_id=<id>"
CLAY_TABLE_ID="t_<your_table_id>"
```

```bash
echo '.env.deepline' >> .gitignore
echo 'output/'       >> .gitignore   # output CSVs contain Clay record data — never commit
```

Both scripts source this file at startup. The cookie is accessed inside JS as `process.env.CLAY_COOKIE` — it never gets embedded in the `--with` payload string.

---

## Template 1: `clay_fetch_records.sh`

Replaces Clay's API with `run_javascript` + `fetch()`. Cookie loaded from env at JS runtime.

```bash
#!/usr/bin/env bash
# clay_fetch_records.sh
# Usage: ./clay_fetch_records.sh [schema|pilot|full]
set -euo pipefail

# Load credentials from .env.deepline — NEVER hardcode the cookie here
# Uses .env.deepline (not .env) to avoid interfering with any existing project env files
set -a; source "$(dirname "$0")/.env.deepline"; set +a
: "${CLAY_COOKIE:?Set CLAY_COOKIE in .env.deepline}"
: "${CLAY_TABLE_ID:?Set CLAY_TABLE_ID in .env.deepline}"

INPUT_CSV="./output/records_input.csv"     # CSV with record_id column
OUTPUT_CSV="./output/clay_records.csv"

# ── Schema fetch ─────────────────────────────────────────────────────────────
fetch_table_schema() {
python3 - <<'PYEOF'
import json, os, subprocess

TABLE_ID = os.environ["CLAY_TABLE_ID"]

code = (
    "return (async () => {"
    "  const resp = await fetch('https://api.clay.com/v3/tables/' + '" + TABLE_ID + "', {"
    "    headers: {"
    "      'accept': 'application/json',"
    "      'cookie': process.env.CLAY_COOKIE,"
    "      'origin': 'https://app.clay.com',"
    "      'referer': 'https://app.clay.com/'"
    "    }"
    "  });"
    "  const data = await resp.json();"
    "  const t = data.table;"
    "  return {"
    "    tableId: t.id, tableName: t.name, workbookId: t.workbookId,"
    "    fields: t.fields.map(function(f) { return { id: f.id, name: f.name, type: f.type }; })"
    "  };"
    "})()"
)

result = subprocess.run(
    ["deepline", "tools", "execute", "run_javascript",
     "--payload", json.dumps({"code": code}), "--json"],
    capture_output=True, text=True,
    env={**__import__("os").environ},  # pass CLAY_COOKIE through to JS runtime
)
out = json.loads(result.stdout)
print(json.dumps(out.get("result", out), indent=2))
PYEOF
}

# ── Record fetch (bulk-fetch-records per row) ─────────────────────────────────
run_enrich() {
  local ROWS_FLAG="${1:-}"

python3 - <<'PYEOF'
import json, os, subprocess, sys

TABLE_ID = os.environ["CLAY_TABLE_ID"]
INPUT_CSV = os.environ.get("INPUT_CSV", "./output/records_input.csv")
OUTPUT_CSV = os.environ.get("OUTPUT_CSV", "./output/clay_records.csv")
ROWS_FLAG = os.environ.get("ROWS_FLAG", "")

# Cookie is NOT embedded here — the JS reads process.env.CLAY_COOKIE at runtime
enrich_code = (
    "return (async () => {"
    "  const TABLE_ID = '" + TABLE_ID + "';"
    "  const recordId = row.record_id;"
    "  const resp = await fetch("
    "    'https://api.clay.com/v3/tables/' + TABLE_ID + '/bulk-fetch-records',"
    "    {"
    "      method: 'POST',"
    "      headers: {"
    "        'accept': 'application/json',"
    "        'content-type': 'application/json',"
    "        'cookie': process.env.CLAY_COOKIE,"
    "        'origin': 'https://app.clay.com',"
    "        'referer': 'https://app.clay.com/'"
    "      },"
    "      body: JSON.stringify({ recordIds: [recordId], includeExternalContentFieldIds: [] })"
    "    }"
    "  );"
    "  const data = await resp.json();"
    "  const record = data.results && data.results[0];"
    "  if (!record) return { error: 'record_not_found', record_id: recordId };"
    "  const cells = record.cells || {};"
    "  const v = function(fid) { var c = cells[fid]; return c && c.value !== undefined ? c.value : null; };"
    # FIELD_MAP is generated from the schema fetch (./clay_fetch_records.sh schema).
    # Keys are Clay field IDs; values are the snake_case alias for that column.
    # Replace this map entirely with the fields that exist in YOUR table.
    "  var FIELD_MAP = " + json.dumps(FIELD_MAP) + ";"
    "  var result = { record_id: recordId };"
    "  for (var fid in FIELD_MAP) {"
    "    if (Object.prototype.hasOwnProperty.call(FIELD_MAP, fid)) {"
    "      result[FIELD_MAP[fid]] = v(fid);"
    "    }"
    "  }"
    "  return result;"
    "})()"
)

# FIELD_MAP is built by running ./clay_fetch_records.sh schema, then mapping
# each field id → snake_case(field.name). Example for a contact table:
# FIELD_MAP = {
#   'f_0sy80p3abc': 'first_name',
#   'f_0sy80p3def': 'last_name',
#   'f_0sy80p3ghi': 'job_title',
# }
# The actual map depends entirely on YOUR table's schema — do not hardcode column names.
FIELD_MAP = {}  # ← populate from schema fetch before running
)

with_arg = "clay_record=run_javascript:" + json.dumps({"code": enrich_code})
rows_args = ["--rows", ROWS_FLAG] if ROWS_FLAG else []
cmd = ["deepline", "enrich", "--input", INPUT_CSV, "--output", OUTPUT_CSV] + rows_args + ["--with", with_arg]

result = subprocess.run(cmd, capture_output=False, text=True, env={**os.environ})
sys.exit(result.returncode)
PYEOF
}

case "${1:-pilot}" in
  schema) echo "=== Table schema ===" && fetch_table_schema ;;
  pilot)  ROWS_FLAG="0:3"  run_enrich ;;
  full)   ROWS_FLAG=""     run_enrich ;;
  *)      echo "Usage: $0 [schema|pilot|full]" ;;
esac
```

### Key patterns

- **Cookie in env**: `process.env.CLAY_COOKIE` in JS — cookie never appears in the `--with` payload string, so it's not captured in Deepline's telemetry `command_text`
- **TABLE_ID from env**: `os.environ["CLAY_TABLE_ID"]` — keeps script portable across tables
- **Field IDs from schema**: Run `./clay_fetch_records.sh schema` first, copy field IDs into the `v('<f_xxx_id>')` calls
- **Field ID → value**: `const v = function(fid) { var c = cells[fid]; return c && c.value !== undefined ? c.value : null; };`
- **No template literals**: Use string concatenation for vars injected into JS (avoids bash parse errors)
- **Async wrapper**: All `await` must be inside `(async () => { ... })()`
- **Pass `env={**os.environ}`** to subprocess.run so `CLAY_COOKIE` is available in the JS runtime

---

## Template 2: `claygent_replicate.sh`

Replicates all AI action columns as sequential `deepline enrich --in-place` passes.
No Clay credentials needed here — works on the already-fetched CSV.

```bash
#!/usr/bin/env bash
# claygent_replicate.sh
# Usage: ./claygent_replicate.sh [0:0|0:3|full]
set -euo pipefail

ENRICHED="./output/clay_records.csv"
ROWS="${1:-0:0}"
[[ "$ROWS" == "full" ]] && ROWS_ARGS="" || ROWS_ARGS="--rows $ROWS"

# ── Enrich helpers ────────────────────────────────────────────────────────────
enrich() {
  python3 -c "
import subprocess, sys, os
rows_args = '${ROWS_ARGS}'.split() if '${ROWS_ARGS}' else []
cmd = ['deepline', 'enrich', '--input', '${ENRICHED}', '--in-place'] + rows_args
for arg in sys.argv[1:]:
    cmd += ['--with', arg]
r = subprocess.run(cmd, capture_output=False, text=True, timeout=600)
sys.exit(r.returncode)
" "$@"
}

enrich_force() {
  # Force recompute of a single column without rerunning all others
  local col="$1"; shift
  python3 -c "
import subprocess, sys, os
rows_args = '${ROWS_ARGS}'.split() if '${ROWS_ARGS}' else []
cmd = ['deepline', 'enrich', '--input', '${ENRICHED}', '--in-place',
       '--with-force', '${col}'] + rows_args
for arg in sys.argv[1:]:
    cmd += ['--with', arg]
r = subprocess.run(cmd, capture_output=False, text=True, timeout=600)
sys.exit(r.returncode)
" "$@"
}

echo "=== Claygent Replication | Rows: ${ROWS} ==="

# ─── PASS 1: Flatten clay_record ─────────────────────────────────────────────
# Always first — extracts clay_record cell values to top-level fields.xxx refs.
# FIELD_MAP must match the map used in clay_fetch_records.sh.
# Keys are Clay field IDs; values are the snake_case alias. Derived from schema fetch.
echo "Pass 1/N: flatten clay_record → fields"
FLATTEN=$(python3 -c "
import json
# Populate FIELD_MAP from your schema fetch — same map as clay_fetch_records.sh.
# Do NOT hardcode column names here; derive from actual table schema.
# e.g. {'f_0sy80p3abc': 'first_name', 'f_0sy80p3def': 'last_name', ...}
FIELD_MAP = {}  # ← populate from schema fetch

code = (
    'return (function() {'
    '  var cr = row.clay_record;'
    '  if (!cr || typeof cr !== \"object\") return { error: \"no clay_record\" };'
    '  var FIELD_MAP = ' + json.dumps(FIELD_MAP) + ';'
    '  var result = {};'
    '  for (var fid in FIELD_MAP) {'
    '    if (Object.prototype.hasOwnProperty.call(FIELD_MAP, fid)) {'
    '      result[FIELD_MAP[fid]] = (cr[fid] !== undefined) ? cr[fid] : null;'
    '    }'
    '  }'
    '  return result;'
    '})()'
)
print('fields=run_javascript:' + json.dumps({'code': code}))
")
enrich "\$FLATTEN"

# ─── PASSES 2..N: generated from the actual Clay table schema ─────────────────
# The passes below are EXAMPLES only. The migration skill generates passes specific
# to your table — column aliases, prompts, tools, and json_mode schemas all come
# from the Clay schema fetch + bulk-fetch-records cell values (Phase 1).
#
# DO NOT copy these examples for a different table. Run Phase 1 on your table first.
#
# ── Example: call_ai haiku — simple classify (no web, single-value output) ────
# echo "Pass N: <alias> (call_ai haiku)"
# PASS_N=$(python3 -c "
# import json
# # Prompt comes from the recovered Clay formula cell value (Phase 1 §1.5)
# # or approximated if no HAR available. Replace {{fields.xxx}} with your actual aliases.
# prompt = '<PASTE RECOVERED CLAY PROMPT HERE — from Phase 1 HAR extraction>'
# print('<alias>=call_ai:' + json.dumps({'prompt': prompt, 'model': 'haiku', 'agent': 'auto'}))
# ")
# enrich "\$PASS_N"
#
# ── Example: call_ai sonnet with json_mode — structured output ─────────────────
# echo "Pass N: <alias> (call_ai sonnet, json_mode)"
# PASS_N=$(python3 -c "
# import json
# prompt = '<PASTE RECOVERED CLAY PROMPT HERE>'
# # json_mode schema mirrors the fields the original Clay column output contained.
# # Inspect bulk-fetch-records cell values to determine the actual output shape.
# schema = {
#     'type': 'object',
#     'properties': {
#         # Add fields matching what the original Clay column produced:
#         '<field_name>': {'type': '<string|number|boolean|array>'},
#     },
#     'required': ['<required_field>']
# }
# print('<alias>=call_ai:' + json.dumps({'prompt': prompt, 'model': 'sonnet', 'agent': 'claude', 'json_mode': schema}))
# ")
# enrich "\$PASS_N"
# # Downstream ref: {{<alias>.extracted_json}}, NOT {{<alias>.<field_name>}}
#
# ── Example: exa_search — web research (paid — pilot gate required) ───────────
# echo "Pass N: <alias> (exa_search)"
# PASS_N=$(python3 -c "
# import json
# payload = {
#     # Query should match what the original Clay claygent column was researching.
#     # Derived from the Clay column's prompt/goal, not hardcoded.
#     'query': '<DERIVED FROM CLAY COLUMN RESEARCH GOAL>',
#     'num_results': 5,
#     'contents': {'text': True, 'highlights': True}
# }
# print('<alias>=exa_search:' + json.dumps(payload))
# ")
# enrich "\$PASS_N"

echo ""
echo "=== Done. Output: ${ENRICHED} ==="
echo "Playground: http://127.0.0.1:4174"
```

### Enrich helper notes

- `enrich()` wraps `deepline enrich --in-place` with row scoping — always build `--with` args via `json.dumps()`, never hand-write JSON in bash
- `enrich_force()` forces recompute of a single column — use for reruns without reprocessing the full pipeline
- Downstream `json_mode` columns: reference via `.extracted_json` (e.g. `{{strategic_initiatives.extracted_json}}`), not `.field_name` directly

### Usage

```bash
./claygent_replicate.sh          # pilot: row 0 only (default)
./claygent_replicate.sh 0:3      # rows 0–3
./claygent_replicate.sh full     # all rows
```
