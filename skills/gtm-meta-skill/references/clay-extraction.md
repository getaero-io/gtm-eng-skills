---
name: clay-extraction
description: "How to extract Clay table configs via MCP or script. Read only when the user needs to extract from Clay — skip if they already provide an extract JSON."
---

# Clay Table Extraction

Use `scripts/clay-extract.py` (bundled at `.skills/gtm-meta-skill/scripts/clay-extract.py`, also at repo root `scripts/clay-extract.py`) to pull full table configs from Clay's internal API. Extracts: field definitions, action settings (prompts, models, webhook URLs), formula text, conditional run logic, and up to ~36-66 sample records.

## Two extraction paths

| Path | When | Steps |
|---|---|---|
| **Claude-in-Chrome MCP** | Running inside Claude Code with the extension | Zero steps — use `javascript_tool` with `fetch(url, {credentials: 'include'})` directly from the authenticated browser session |
| **`clay-extract.py` script** | Standalone, CI, or no MCP | One-time cURL paste for auth, then zero-step extraction |

## Script setup (one-time)

```bash
python3 -m venv .venv/clay-extract
.venv/clay-extract/bin/pip install requests

# Auth: paste a cURL from any api.clay.com request in Chrome DevTools
.venv/clay-extract/bin/python3 scripts/clay-extract.py --auth
```

Session is saved to `.clay-session.json` and reused until it expires (~24h).

## Extraction commands

```bash
PYTHON=.venv/clay-extract/bin/python3

# By table URL or ID
$PYTHON scripts/clay-extract.py https://app.clay.com/workspaces/502058/workbooks/wb_xxx/tables/t_xxx
$PYTHON scripts/clay-extract.py t_0t5pj9mqNnpxxjM6jaV

# By workbook URL (resolves to all tables in the workbook)
$PYTHON scripts/clay-extract.py https://app.clay.com/workspaces/502058/workbooks/wb_0t5pj9dg5C7fGNTajyw

# By name (fuzzy matches workbook and table names)
$PYTHON scripts/clay-extract.py --workspace 502058 "Demo Request"
```

Output goes to `tmp/clay_extract_<table_name>.json`. Never overwrites existing files.

## What the extract contains

```
{
  "_meta": { "extractedAt", "method", "tableId" },
  "table": { "id", "name", "workbookId", "workspaceId", "firstViewId", "tableSettings" },
  "fields": [
    {
      "id": "f_xxx",
      "name": "AI Message Generator",
      "type": "action",                          // source | formula | action | text | date
      "typeSettings": {
        "actionKey": "use-ai",                   // Clay action type
        "inputsBinding": [                       // Action config (prompts, models, etc.)
          { "name": "prompt", "formulaText": "You are writing..." },
          { "name": "model", "formulaText": "\"claude-sonnet-4-6\"" }
        ],
        "formulaText": "...",                    // Formula/prompt text (for formula fields)
        "conditionalRunFormulaText": "!!{{f_xxx}}"  // Conditional execution
      }
    }
  ],
  "tableSchema": { ... },                        // Schema tree from table-schema-v2
  "exampleRecords": [ ... ]                       // Up to ~36-66 sample rows with cell values
}
```

## Key Clay API endpoints (undocumented, reverse-engineered)

| Endpoint | Method | Returns |
|---|---|---|
| `/v3/tables/{TABLE_ID}` | GET | Full table config: fields, typeSettings, prompts, action bindings |
| `/v3/tables/{TABLE_ID}/views/{VIEW_ID}/table-schema-v2` | GET | Schema tree + example records (up to ~66 rows) |
| `/v3/workbooks/{WB_ID}/tables` | GET | List of tables in a workbook `[{id, name, ...}]` |
| `/v3/workspaces/{WS_ID}/resources_v2/` | POST | Top-level workspace resources (folders, workbooks) |
| `/v3/tables/{TABLE_ID}/views/{VIEW_ID}/records/ids` | GET | All record IDs (for full data pull) |
| `/v3/tables/{TABLE_ID}/bulk-fetch-records` | POST | Full cell data for specific record IDs |

All require `Cookie: claysession=...` + `origin: https://app.clay.com` headers.

## Important details

- **Formula text location**: `field.typeSettings.formulaText` (NOT `field.formulaText`)
- **Action prompts**: `field.typeSettings.inputsBinding` array → find entry with `name: "prompt"` → `.formulaText`
- **Model**: same array → `name: "model"` → `.formulaText` (e.g. `"claude-sonnet-4-6"`)
- **Field references in formulas**: `{{f_xxx}}` format — map to names via the fields array
- **Folder URLs** (`/home/f_xxx`): the `f_xxx` is a folder ID, not a field. Folder children aren't exposed via API — use workbook URLs or name search instead.
- **Cookie security**: `.clay-session.json` is gitignored. Never log or embed cookies in scripts.

## MCP extraction (for agents with Claude-in-Chrome)

When Claude-in-Chrome MCP is available, skip the script:

1. `tabs_context_mcp` → get tab context
2. `navigate` → Clay URL (any table/workbook page)
3. `javascript_tool` with `credentials: 'include'`:
   ```javascript
   fetch('https://api.clay.com/v3/tables/{TABLE_ID}', {
     headers: { 'accept': 'application/json' },
     credentials: 'include'
   }).then(r => r.json()).then(data => { window.__clayConfig = data; });
   ```
4. Read result, download as JSON blob

The browser already has the session cookie — `credentials: 'include'` sends it automatically. Without this flag, fetch returns 401.

## Input data formats

When the user provides data directly (not via extraction), these are the possible formats ranked by richness:

**Priority: HAR > ClayMate Lite > clay-extract.py output > bulk-fetch-records > schema JSON > user description.**

| Input type | Key fields |
|---|---|
| **HAR file** | `bulk-fetch-records` responses with rendered formula cell values — richest |
| **ClayMate Lite export** | `.tableSchema` + `.portableSchema` (full prompts even when `bulkFetchRecords` is null) |
| **clay-extract.py output** | `.fields[].typeSettings.inputsBinding` for prompts; `.exampleRecords` for samples |
| **Schema JSON** | Field names, IDs, action types. No cell values or prompts |
| **User description** | Weakest — must approximate everything |

**When `bulkFetchRecords` is null:** Fall back to `portableSchema`:
- Prompts: `.portableSchema.columns[].typeSettings.inputsBinding` → `{name: "prompt"}` → `.formulaText`
- JSON schemas: `{name: "answerSchemaType"}` → `.formulaMap.jsonSchema` (double-escaped — `JSON.parse` twice)
- Conditional run: `.typeSettings.conditionalRunFormulaText`

**Extract bulk-fetch-records from HAR:**

```bash
python3 - <<'EOF'
import json, base64, gzip
with open('your-export.har') as f:
    har = json.load(f)
for entry in har['log']['entries']:
    url = entry['request']['url']
    if 'bulk-fetch-records' in url:
        body = entry['response']['content'].get('text', '')
        enc  = entry['response']['content'].get('encoding', '')
        data = base64.b64decode(body) if enc == 'base64' else body.encode()
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
        print(json.dumps(json.loads(data), indent=2)[:5000])
EOF
```
