# Script Templates

## Setup: `.env` file (one-time)

Create this once per project. **Never commit it.**

```bash
# .env — Clay credentials
# Get from: browser devtools → Network → any api.clay.com request → Request Headers → Cookie
CLAY_COOKIE="claysession=<value>; ajs_user_id=<id>"
CLAY_TABLE_ID="t_<your_table_id>"
```

```bash
echo '.env' >> .gitignore
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

# Load credentials from .env — NEVER hardcode the cookie here
set -a; source "$(dirname "$0")/.env"; set +a
: "${CLAY_COOKIE:?Set CLAY_COOKIE in .env}"
: "${CLAY_TABLE_ID:?Set CLAY_TABLE_ID in .env}"

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
    "  return {"
    "    full_name:      v('<f_full_name_id>'),"
    "    first_name:     v('<f_first_name_id>'),"
    "    job_title:      v('<f_job_title_id>'),"
    "    company_domain: v('<f_company_domain_id>')"
    # ↑ Replace <f_xxx_id> placeholders with actual field IDs from schema fetch
    "  };"
    "})()"
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
# Always first — extracts clay_record subfields to top level for {{fields.xxx}} refs
echo "Pass 1/N: flatten clay_record → fields"
FLATTEN=$(python3 -c "
import json
code = '''return (function() {
  var cr = row.clay_record;
  if (!cr || typeof cr !== 'object') return { error: 'no clay_record' };
  return {
    full_name:      cr.full_name,
    first_name:     cr.first_name,
    job_title:      cr.job_title,
    company_name:   cr.company_name,
    company_domain: cr.company_domain
    // Add all fields from your Clay schema here
  };
})()'''
print('fields=run_javascript:' + json.dumps({'code': code}))
")
enrich "\$FLATTEN"

# ─── PASS 2: call_ai haiku — classify ────────────────────────────────────────
echo "Pass 2/N: job_function (call_ai haiku)"
JOB_FUNCTION=$(python3 -c "
import json
prompt = 'Given this job title: {{fields.job_title}}\n\nClassify the job function into exactly one of: Engineering, Sales, Marketing, Finance, Operations, HR, Legal, Product, Design, Other.\n\nRespond with only the category name.'
print('job_function=call_ai:' + json.dumps({'prompt': prompt, 'model': 'haiku', 'agent': 'auto'}))
")
enrich "\$JOB_FUNCTION"

# ─── PASS 3: exa_search — web research ───────────────────────────────────────
# ⚠️  Paid tool — pilot gate: always run rows 0:0 first and review before full run
echo "Pass 3/N: exa_research (exa_search)"
EXA=$(python3 -c "
import json
payload = {
    'query': '{{fields.company_name}} {{fields.company_domain}} strategic initiatives 2025',
    'num_results': 5,
    'contents': {'text': True, 'highlights': True}
}
print('exa_research=exa_search:' + json.dumps(payload))
")
enrich "\$EXA"

# ─── PASS 4: call_ai sonnet json_mode — structured output ────────────────────
echo "Pass 4/N: strategic_initiatives (call_ai sonnet, json_mode)"
STRAT=$(python3 -c "
import json
prompt = '''Company: {{fields.company_name}} ({{fields.company_domain}})
Job title: {{fields.job_title}}

Web research:
{{exa_research}}

Extract the top 3-5 strategic initiatives this company is currently pursuing based on the research above.'''
schema = {
    'type': 'object',
    'properties': {
        'top_initiatives': {'type': 'array', 'items': {'type': 'string'}},
        'growth_stage': {'type': 'string'},
        'key_priorities': {'type': 'array', 'items': {'type': 'string'}}
    },
    'required': ['top_initiatives']
}
print('strategic_initiatives=call_ai:' + json.dumps({'prompt': prompt, 'model': 'sonnet', 'agent': 'claude', 'json_mode': schema}))
")
enrich "\$STRAT"
# Reference downstream as {{strategic_initiatives.extracted_json}}, NOT {{strategic_initiatives.top_initiatives}}

# ─── PASS 5: call_ai sonnet — ICP qualification ───────────────────────────────
echo "Pass 5/N: qualify_person (call_ai sonnet, json_mode)"
QUALIFY=$(python3 -c "
import json
prompt = '''Score this prospect against our ICP.

Prospect:
- Name: {{fields.full_name}}
- Title: {{fields.job_title}}
- Function: {{job_function}}
- Company: {{fields.company_name}} ({{fields.company_domain}})

Company context:
{{strategic_initiatives.extracted_json}}

ICP Scoring (sum to 10):
1. Persona fit (0-4): Does title/function match target persona?
2. Seniority (0-2): Director-VP range with tooling ownership?
3. Hiring signals (0-2): Actively hiring for target function?
4. Strategic fit (0-2): Initiatives match product value prop?

Tier: A=8-10, B=5-7, C=0-4. Qualified if score >= 6.'''
schema = {
    'type': 'object',
    'properties': {
        'score': {'type': 'number'},
        'tier': {'type': 'string', 'enum': ['A', 'B', 'C']},
        'qualified': {'type': 'boolean'},
        'rationale': {'type': 'string'},
        'disqualifiers': {'type': 'array', 'items': {'type': 'string'}}
    },
    'required': ['score', 'tier', 'qualified', 'rationale']
}
print('qualify_person=call_ai:' + json.dumps({'prompt': prompt, 'model': 'sonnet', 'agent': 'claude', 'json_mode': schema}))
")
enrich "\$QUALIFY"

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
