---
name: clay-extraction
description: 'How to extract Clay table configs via MCP or script. Read only when the user needs to extract from Clay — skip if they already provide an extract JSON.'
---

# Clay Table Extraction

Use `scripts/clay-extract.py` (bundled at `.skills/deepline-gtm/scripts/clay-extract.py`, also at repo root `scripts/clay-extract.py`) to pull full table configs from Clay's internal API. Extracts: field definitions, action settings (prompts, models, webhook URLs), formula text, conditional run logic, and up to ~36-66 sample records.

## Three extraction paths

| Path                         | When                                          | Steps                                                                                                                                          |
| ---------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Bookmarklet**              | A human, or an agent with Claude-in-Chrome    | One click on the Clay table tab. Downloads a complete `clay_extract_<table>.json`. Agents run the same source via `javascript_tool` (see below) |
| **Claude-in-Chrome MCP**     | Running inside Claude Code with the extension | Zero steps. Run the bookmarklet source (below), or `fetch(url, {credentials: 'include'})` ad hoc from the authenticated browser session         |
| **`clay-extract.py` script** | Standalone, CI, or no MCP                     | One-time cURL paste for auth, then zero-step extraction                                                                                        |

The bookmarklet and the MCP path share one source of truth: `scripts/clay-extract-bookmarklet.js` (in this skill). It hits the current Clay v3 API (`/v3/tables/{id}` for config+fields+views, `table-schema-v2` for the rendered sample rows, `/count`, `records/ids`, and batched `bulk-fetch-records`) and assembles the same shape `clay-extract.py` produces.

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

## Clay Functions (subroutine tables)

A **Clay Function** is a reusable subroutine packaged as its own table. Other
tables call it with a row of inputs; the function runs its column pipeline and
writes the results back to the caller's cell. Recognize this pattern and migrate
it as a self-contained play with a typed input contract — not as a batch lead
list.

**Signature — how to recognize a function table:**

| Signal | Field | What it means |
| --- | --- | --- |
| **Input source** | a `type: "source"` field named "Function inputs", id `f_subroutine_source`, `typeSettings.sourceIds` (and sometimes `taggedSourceType`) | The function's parameter row. Every other column reads `{{f_subroutine_source}}?.["<Input Name>"]`. |
| **Work action(s)** | one or more `type: "action"` fields (`use-ai`, `hubspot-lookup-object`, an email finder, etc.) | The actual computation. Full config is in `typeSettings` — see below. |
| **Write-back** | a `type: "action"` field with `actionKey: "write-to-cell"` | Returns the function's outputs to the calling cell. Its `inputsBinding` `data` **`formulaMap`** lists every output the function exposes, keyed by output name. **This map is the function's output schema.** |
| **Table type** | `table.tableSettings.BLOCK_TYPE == "SUBROUTINE"` + `SUBROUTINE_INPUTS` | When present, this is conclusive. `SUBROUTINE_INPUTS` is the **typed input schema** — an array of `{inputName, optional, semanticTypeEnum, description}` (e.g. `{"inputName":"Domain","optional":false,"semanticTypeEnum":"company-domain"}`). Use it verbatim as the play's input contract. |

**Fallback when `tableSettings` is absent.** Some extracts (older script runs,
trimmed table objects) drop `tableSettings`, so `BLOCK_TYPE` may be missing even
for a real function. In that case, detect the function by the **field signature**
alone: a `f_subroutine_source` "Function inputs" source field **plus** a
`write-to-cell` action is sufficient. Derive the input schema from the distinct
`{{f_subroutine_source}}?.["…"]` keys referenced across columns, and the output
schema from the `write-to-cell` `data.formulaMap`. Do not require `BLOCK_TYPE` to
proceed.

**Where the function's contract lives in the extract:**

- **Input schema** → `table.tableSettings.SUBROUTINE_INPUTS` when present; otherwise the distinct `{{f_subroutine_source}}?.["First Name"]` / `?.["Domain"]` keys across the columns.
- **Output schema** → the `write-to-cell` action's `inputsBinding` entry `name: "data"` → `formulaMap` (each key is an output name; each value is the `{{f_xxx}}` column that fills it).
- **Body** → every non-source, non-`write-to-cell` field, in dependency order. Actions carry `actionKey`, `actionVersion`, `actionPackageId`, `authAccountId`, `conditionalRunFormulaText`, `inputsBinding` (verbatim prompts, models, JSON schemas), and — when present — `optionalPathsInInputs` and `customRateLimitRules`. Extracted `formula` fields carry `extractedField.{fieldIdExtractedFrom,extractedKeyPath}` and `mappedResultPath`; waterfall fields carry `typeSettings.formulaWaterfall` (an ordered fallback array).

**Migration mental model:** a function table → **one Deepline play** whose input
is the subroutine's declared parameter row (not a scraped lead CSV), whose body
is one `.withColumn(...)` per non-source field in dependency order, and whose
output projection is exactly the `write-to-cell` `data` map. **Drop the
`write-to-cell` action itself** — it is Clay-internal plumbing to return values to
the caller; a Deepline play persists to its own Customer DB table and returns its
columns directly. Callers of the Clay function become callers of the play.

**The bookmarklet is the recommended path for function tables.** It passes the
whole table object through, so `tableSettings` (hence `BLOCK_TYPE` and
`SUBROUTINE_INPUTS`) is captured. The `clay-extract.py` script keeps
`tableSettings` too, but if you inherit a trimmed extract, use the field-signature
fallback above. Function **config** never needs the HAR — `GET /v3/tables/{id}`
carries the full definition. The HAR / `bulk-fetch-records` only add rendered
output cell values for parity validation, and are subject to record truncation
(`_meta.truncated`), which never drops a field or action config. When an extract
has **no sample cell values**, mark any architecture or parity claim
`config-inferred, unvalidated` and defer conclusions that require 3+ real
records.

## Key Clay API endpoints (undocumented, reverse-engineered)

| Endpoint                                                | Method | Returns                                                           |
| ------------------------------------------------------- | ------ | ----------------------------------------------------------------- |
| `/v3/tables/{TABLE_ID}`                                 | GET    | Full table config: fields, typeSettings, prompts, action bindings |
| `/v3/tables/{TABLE_ID}/views/{VIEW_ID}/table-schema-v2` | GET    | Schema tree + example records (up to ~66 rows)                    |
| `/v3/workbooks/{WB_ID}/tables`                          | GET    | List of tables in a workbook `[{id, name, ...}]`                  |
| `/v3/workspaces/{WS_ID}/resources_v2/`                  | POST   | Top-level workspace resources (folders, workbooks)                |
| `/v3/tables/{TABLE_ID}/views/{VIEW_ID}/records/ids`     | GET    | All record IDs (for full data pull)                               |
| `/v3/tables/{TABLE_ID}/bulk-fetch-records`              | POST   | Full cell data for specific record IDs                            |

All require `Cookie: claysession=...` + `origin: https://app.clay.com` headers.

## Important details

- **Formula text location**: `field.typeSettings.formulaText` (NOT `field.formulaText`)
- **Action prompts**: `field.typeSettings.inputsBinding` array → find entry with `name: "prompt"` → `.formulaText`
- **Model**: same array → `name: "model"` → `.formulaText` (e.g. `"claude-sonnet-4-6"`)
- **Field references in formulas**: `{{f_xxx}}` format — map to names via the fields array
- **Folder URLs** (`/home/f_xxx`): the `f_xxx` is a folder ID, not a field. Folder children aren't exposed via API — use workbook URLs or name search instead.
- **Cookie security**: `.clay-session.json` is gitignored. Never log or embed cookies in scripts.

## MCP extraction (for agents with Claude-in-Chrome)

When Claude-in-Chrome MCP is available, skip the script. Run the bookmarklet's logic directly, it pulls everything (config, schema, rendered sample rows, all records) in one shot:

1. `tabs_context_mcp` with `createIfEmpty: true` → get a tab
2. `navigate` → the Clay **table view** URL (`.../tables/t_xxx/views/gv_xxx`)
3. Confirm auth before extracting: `javascript_tool` →
   ```javascript
   fetch('https://api.clay.com/v3/tables/' + location.pathname.match(/t_[A-Za-z0-9]+/)[0], {
     credentials: 'include',
   }).then((r) => r.status); // expect 200; 401 means not logged in
   ```
4. Extract: read `scripts/clay-extract-bookmarklet.js` from this skill and paste its IIFE body into `javascript_tool`. It assigns the full result to `window.__clayExtract` and downloads `clay_extract_<table>.json`.
   - In a headless/automation context the auto-download may not surface a file. Either read the payload off `window.__clayExtract` and write it yourself, or skip the `<a>.click()` and return `JSON.stringify(window.__clayExtract)`.
   - The payload can be large (the TAL Scoring table is ~14 MB). Return a summary from `javascript_tool` (field counts, `exampleRecords.length`, `recordIds.length`), then pull the full object in chunks or via the download, not as one giant tool result.
5. The browser already has the session cookie. `credentials: 'include'` sends it automatically; without it, fetch returns 401. The cookie is never read by the script, only the browser uses it.

**Richest data lives in `exampleRecords`** (from `table-schema-v2`): flat `{ f_xxx: <rendered value> }` rows with formula/action outputs already resolved. `bulkFetchRecords` covers *all* rows but is sparse (only populated cells appear, and un-run rows show just `f_created_at`/`f_updated_at`). For prompt and schema recovery, prefer `exampleRecords` and the `tableSchema` tree; use `bulkFetchRecords` for full-table cell coverage.

## Input data formats

When the user provides data directly (not via extraction), these are the possible formats ranked by richness:

**Priority: HAR > ClayMate Lite > clay-extract.py output > bulk-fetch-records > schema JSON > user description.**

| Input type                 | Key fields                                                                             |
| -------------------------- | -------------------------------------------------------------------------------------- |
| **HAR file**               | `bulk-fetch-records` responses with rendered formula cell values — richest             |
| **ClayMate Lite export**   | `.tableSchema` + `.portableSchema` (full prompts even when `bulkFetchRecords` is null) |
| **clay-extract.py output** | `.fields[].typeSettings.inputsBinding` for prompts; `.exampleRecords` for samples      |
| **Schema JSON**            | Field names, IDs, action types. No cell values or prompts                              |
| **User description**       | Weakest — must approximate everything                                                  |

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
