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

| Value                  | Meaning                           |
| ---------------------- | --------------------------------- |
| `NO_CELL`              | Never ran — build from scratch    |
| `"Status Code: 200"`   | Webhook/HTTP action, NOT AI       |
| `""` (empty)           | Disabled or unfired               |
| Varied generation text | Actual AI output — replicate this |

**Not this**: Assume every column with an AI-sounding name is an AI pass.

**Why**: A 2-pass pipeline you built for a 1-pass table doubles cost and complexity.

---

## Email Match Rate

**Do this**: Use `name_and_domain_to_email_waterfall` as the primary supported email play once you have a domain. Add manual `perm_fln` (run_javascript) + `leadmagic_email_validation` for the 19% fln pattern. If LinkedIn URLs are present, pass `linkedin_url` into the same play on fallback passes.

| Format                  | Example                     | % of Clay emails |
| ----------------------- | --------------------------- | ---------------- |
| `fn.ln@domain`          | rachael.foster@zoominfo.com | 63%              |
| `fln@domain`            | rfoster@zoominfo.com        | 19%              |
| `fn@domain`             | rachael@zoominfo.com        | 3%               |
| Provider waterfall only | —                           | ~12%             |

**Not this**: Depend on a removed LinkedIn-only play name, or use individual provider tools as primary.

**Why**: Clay's ~99% match rate comes from permutation+validation. Individual providers cover only the ~12% that permutation misses.

---

## Email Validation — Accept All Three Valid Statuses

**Do this**:

```js
const result = (
  data.result ||
  data.status ||
  data.email_status ||
  ''
).toLowerCase();
return (
  result === 'valid' ||
  result === 'valid_catch_all' ||
  result === 'catch-all' ||
  result === 'catch_all'
);
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
})();

// Strings: concatenation, not template literals
const url = 'https://api.clay.com/v3/tables/' + TABLE_ID;
```

Use Python subprocess to build `--with` payloads containing JS code. Never hand-write JSON with embedded JS in bash strings.

**Not this**: Top-level `await` (error: "await is only valid in async functions"). Template literals with backticks (bash parses them as subshell commands).

---

## Deepline Interpolation

**Do this**:

- `{{column_name}}` — direct column reference
- `{{col.field_name}}` — only when the stored cell root actually contains `field_name`
- For wrapped AI results or 3+ levels: add a `run_javascript` flatten pass first

**Not this**:

- `{{row.fields.company_name}}` — `row.` prefix → "column 'row' not found"
- `{{strategic_initiatives.top5.value}}` — 3 levels → silently empty

**Why**: template interpolation is based on column aliases like `{{company_name}}`, not the `row` object. Inside `run_javascript`, use `row["company_name"]` or `row.company_name`. For `deeplineagent` structured columns in `deepline enrich`, flatten the field you need into a new column instead of assuming `{{col.field_name}}` will resolve cleanly.

---

## deeplineagent Usage

**Do this**: One `deeplineagent` invocation per column, structured JSON output, all fields in one schema. Use `openai/gpt-5.4-mini` for quick classification/extraction and a larger model like `anthropic/claude-sonnet-4.6` when the prompt genuinely needs more reasoning.

**Not this**: Multiple `deeplineagent` calls where one `jsonSchema` call would return all fields at once. Avoid burying broad research inside a single model call when `exa_search` + synthesis would be clearer.

**Why**: Splitting search from synthesis is more debuggable and usually more stable. Multiple model calls for fields from the same data multiply cost and complexity unnecessarily.

---

## Deepline Enrich Flags

**Do this**:

- First pass: `deepline enrich --input seed.csv --output work.csv --with ...`
- Subsequent passes: `deepline enrich --in-place work.csv --with ...`
- Rerun one column: `deepline enrich --in-place work.csv --with-force col_name --with ...`

**Not this**: Use `--in-place` on the source/input CSV. Use `--output` for passes after the first (creates a second file, loses prior columns).

---

## deeplineagent Direct Execute

**Do this**: Use `deepline enrich --with 'col=deeplineagent:{...}'` for row-by-row execution, or `deepline tools execute deeplineagent` for one-off prompt validation.

**Not this**: Assume a direct one-off success means the full row-by-row pipeline no longer needs staged execution or dependency ordering.

**Why**: `deepline enrich` is still the right surface for repeatable column execution, dependency handling, and interpolation across rows.

---

## Unknown Clay Actions

**Do this**: Run `deepline tools search "<what the action does>"` before writing any placeholder or `deeplineagent` approximation. Deepline adds tools continuously — searching first gets you the right tool automatically.

**Not this**: Hardcode a `deeplineagent` approximation for a Clay action that might have a dedicated Deepline tool.

**Why**: A dedicated enrichment tool is usually cheaper, faster, and more accurate than approximating the job with a general AI step.
