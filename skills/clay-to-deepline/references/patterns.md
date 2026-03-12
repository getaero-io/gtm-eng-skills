# Clay → Deepline Patterns

Prescriptive patterns first, antipattern second. Format: Do this → Not this → Why.

---

## Prompt Recovery

**Do this**: Extract prompts from the richest available source in priority order: (1) `portableSchema.columns[].typeSettings.inputsBinding[name=prompt].formulaText`, (2) `bulkFetchRecords results[].cells` formula field values that start with "You are..." or contain numbered requirements, (3) approximate from column outputs only as last resort. Mark prompt files with `# RECOVERED FROM HAR — field f_xxx` or `# ⚠️ APPROXIMATED`.

**Not this**: Approximate prompts from output text when the actual prompt template was sitting in the export.

**Why**: Clay formula fields render the full prompt as a cell value. A 2-sentence approximation vs. a 7-requirement verbatim prompt produces structurally different output.

```bash
# Find rendered prompts in bulk-fetch-records:
grep -o '"value":"You are[^"]*"' har_response.json
```

---

## Pipeline Architecture Verification

**Do this**: Check actual cell values across 3+ rows for every column before counting AI passes.

| Value | Meaning |
|---|---|
| `NO_CELL` | Never ran — build from scratch |
| `"Status Code: 200"` | Webhook/HTTP action, NOT AI |
| `""` (empty) | Disabled or unfired |
| Varied generation text | Actual AI output — replicate this |

**Not this**: Assume every column with an AI-sounding name is an AI pass.

**Why**: A 2-pass pipeline you built for a 1-pass table doubles cost and complexity.

---

## Email Match Rate

**Do this**: Use `cost_aware_first_name_and_domain_to_email_waterfall` as the primary email tool. Add manual `perm_fln` (run_javascript) + `leadmagic_email_validation` for the 19% fln pattern. Use `person_linkedin_to_email_waterfall` as a LinkedIn-based fallback only.

| Format | Example | % of Clay emails |
|---|---|---|
| `fn.ln@domain` | rachael.foster@zoominfo.com | 63% |
| `fln@domain` | rfoster@zoominfo.com | 19% |
| `fn@domain` | rachael@zoominfo.com | 3% |
| Provider waterfall only | — | ~12% |

**Not this**: Use `person_linkedin_to_email_waterfall` as the primary step, or use individual provider tools as primary.

**Why**: Clay's ~99% match rate comes from permutation+validation. Individual providers cover only the ~12% that permutation misses.

---

## Email Validation — Accept All Three Valid Statuses

**Do this**:
```js
const result = (data.result || data.status || data.email_status || '').toLowerCase();
return result === 'valid' || result === 'valid_catch_all' || result === 'catch-all' || result === 'catch_all';
```

**Not this**: Check only for `valid` or only for `valid` + `catch_all`, omitting `valid_catch_all`.

**Why**: `valid_catch_all` is the highest-confidence status (engagement-confirmed, <5% bounce). Filtering it rejects valid emails.

---

## Cookie Security

**Do this**:
```js
// In run_javascript code:
'cookie': process.env.CLAY_COOKIE

// In .env.deepline (single quotes — prevents $o7 GA cookie expansion):
CLAY_COOKIE='claysession=abc; _ga_X=GS2.1.$o7.1....'
```
Add `.env.deepline` and `output/` to `.gitignore` in every generated script block.

**Not this**: Embed cookie literal in JS code string, or store with double quotes in `.env.deepline`.

**Why**: `deepline enrich` sends the full command string to `POST /api/v2/telemetry/activity`. A cookie in `--with` args appears in Deepline's logs. GA cookies contain `$` characters that bash expands silently with double quotes.

---

## Clay API Calls

**Do this**: Always use the `clay_curl` wrapper with required headers. Get `VIEW_ID` dynamically from `.table.firstViewId`. Parse response with `.get('results', [])`. Access record ID as `.id`.

```bash
# View ID from schema:
VIEW_ID=$(clay_curl "https://api.clay.com/v3/tables/${TABLE_ID}" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['table']['firstViewId'])")

# Record IDs:
ids = data.get('results', [])         # NOT 'recordIds'
record_id = result.get('id')          # NOT 'recordId'

# Paginated bulk fetch:
GET /v3/tables/{TABLE_ID}/views/{VIEW_ID}/records/ids   # NOT /records/ids (404)
```

**Not this**: Use bare `curl` (returns 401). Use `GET /v3/tables/{ID}/records/ids` without view ID (returns 404). Parse with `recordIds` or `recordId`.

**Why**: Clay's API requires `x-clay-frontend-version` and other headers. The viewless records/ids endpoint doesn't exist.

---

## run_javascript Code

**Do this**:
```js
// Async: wrap in IIFE
return (async () => {
  const resp = await fetch(url);
  return await resp.json();
})()

// Strings: concatenation, not template literals
const url = 'https://api.clay.com/v3/tables/' + TABLE_ID;
```

Use Python subprocess to build `--with` payloads containing JS code. Never hand-write JSON with embedded JS in bash strings.

**Not this**: Top-level `await` (error: "await is only valid in async functions"). Template literals with backticks (bash parses them as subshell commands).

---

## Deepline Interpolation

**Do this**:
- `{{column_name}}` — direct column reference
- `{{col.extracted_json}}` — json_mode output (2 levels max)
- For 3+ levels: add a `run_javascript` flatten pass first

**Not this**:
- `{{row.fields.company_name}}` — `row.` prefix → "column 'row' not found"
- `{{strategic_initiatives.extracted_json.top5}}` — 3 levels → silently empty

**Why**: `call_ai` with `json_mode` outputs `{output, extracted_json}` — the fields you want are one level deeper than the column name. 3+ level nesting isn't supported; flatten first.

---

## call_ai Usage

**Do this**: One `call_ai` invocation per column, structured JSON output, all fields in one schema. Use `call_ai` haiku for classification/extraction, sonnet for generation/research.

**Not this**: Multiple `call_ai` calls where one json_mode call would return all fields at once. Use `call_ai` with `allowed_tools: "WebSearch"` for research.

**Why**: WebSearch via `call_ai` hits 180s timeout. Use `exa_search` as a separate prior pass instead. Multiple `call_ai` calls for fields from the same data multiply cost unnecessarily.

---

## Deepline Enrich Flags

**Do this**:
- First pass: `deepline enrich --input seed.csv --output work.csv --with ...`
- Subsequent passes: `deepline enrich --in-place work.csv --with ...`
- Rerun one column: `deepline enrich --in-place work.csv --with-force col_name --with ...`

**Not this**: Use `--in-place` on the source/input CSV. Use `--output` for passes after the first (creates a second file, loses prior columns).

---

## call_ai Blocked in Direct Execute

**Do this**: Use `deepline enrich --with 'col=call_ai:{...}'` for all `call_ai` passes — each row runs in a separate subprocess session.

**Not this**: Run `deepline tools execute call_ai` directly from Claude CLI.

**Why**: Claude CLI blocks sub-calls in the same session: "Claude CLI does not support sub-calls in the same session." This is expected behavior, not a bug.

---

## Unknown Clay Actions

**Do this**: Run `deepline tools search "<what the action does>"` before writing any placeholder or `call_ai` approximation. Deepline adds tools continuously — searching first gets you the right tool automatically.

**Not this**: Hardcode a `call_ai` approximation for a Clay action that might have a dedicated Deepline tool.

**Why**: A `call_ai` approximation for `validate-email` costs ~0.5¢/row; `leadmagic_email_validation` costs ~0.002¢/row — 250× cheaper, more accurate.
