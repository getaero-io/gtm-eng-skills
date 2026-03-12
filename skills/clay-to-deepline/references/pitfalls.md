# Known Pitfalls and Fixes

## Approximated Prompts When Actual Prompts Were in the HAR

### Symptom
Generated prompt produces noticeably different output from Clay — wrong structure, wrong length, missing specific requirements (e.g., Clay prompt had 7 numbered requirements and a verbatim example output, but script used a 2-sentence approximation).

### Root cause
Phase 1 wrote approximated prompts (reverse-engineered from outputs) without checking whether the bulk-fetch-records response contained rendered formula field values. Clay formula fields often render the full prompt template as a cell value alongside the record data.

### How to detect
In the bulk-fetch-records `results[].cells` array, look for `formula` type fields whose cell values read like instructions: numbered requirements, "You are writing...", tone descriptions, "Example Output:" lines. Field IDs are usually adjacent to the corresponding AI action column in the schema.

```bash
# In HAR or bulk-fetch-records JSON: look for cells where value starts with "You are"
grep -o '"value":"You are[^"]*"' har_response.json
```

### Fix
1. Find formula fields adjacent to the AI action column in the schema
2. Copy the cell value verbatim as the system prompt
3. Fix any Clay formula bugs present in the template:
   - Wrong variable reference: e.g., `{{last_name}}` where `{{job_title}}` was intended — visible when comparing cell value to column name
   - Unresolved single-brace syntax: `{field_name}` (not interpolated) — Clay uses `{{double_braces}}` only
4. Update prompt file header: `# RECOVERED FROM HAR — field f_xxx`

---

## Wrong Pipeline Architecture (Assumed N AI Passes, Actual Was Different)

### Symptom
Built a 2-pass draft→refine AI pipeline, but Clay only did 1 AI pass. Or vice versa.

### Root cause
Multiple columns with AI-looking names were assumed to each represent one AI pass. Actual cell values were not checked — some were `NO_CELL` (never ran) or `"Status Code: 200"` (webhook to n8n/Zapier, not AI).

### How to detect
Check bulk-fetch-records cell values across 3+ rows for each column:
- `NO_CELL` → column never ran
- `"Status Code: 200"` or similar HTTP status → webhook/HTTP action, NOT AI output
- Empty string `""` → disabled or unfired
- Varied generation-shaped text → actual AI output

### Fix
1. Map every column: empty/NO_CELL, HTTP/webhook, or actual AI output
2. Only replicate columns with actual AI output
3. For webhook columns sending to n8n/Zapier: ask user for the endpoint and payload format, or stub with a `run_javascript` placeholder
4. Collapse to minimum AI passes actually observed (often 1 pass, not 2)

---

## Email Match Rate — Wrong Waterfall Tool

### Symptom
Deepline finds emails for ~13% of rows vs Clay's ~99%.

### Root cause
Using individual provider tools (`hunter_email_finder`, `leadmagic_email_finder`, etc.) instead of the `cost_aware_first_name_and_domain_to_email_waterfall` native play. Clay's primary path is **email permutation + ZeroBounce validation** (covers ~83% of emails). The individual provider tools are Clay's enterprise *fallback* path only.

### Pattern breakdown (validated on 300-row real dataset)
| Format | Example | % of Clay emails |
|---|---|---|
| `fn.ln@domain` | rachael.foster@zoominfo.com | 63% |
| `fln@domain` (firstinitial+lastname) | rfoster@zoominfo.com | 19% |
| `fn@domain` | rachael@zoominfo.com | 3% |
| `fnln@domain` | rachaelfoster@zoominfo.com | 3% |
| Provider waterfall only | — | ~12% |

### Fix
Use the 3-pass email approach from the Pass Plan (passes 5a–5e):
1. `cost_aware_first_name_and_domain_to_email_waterfall` — covers fn.ln + fnln + first_last + providers
2. Manual `perm_fln` (run_javascript) + `leadmagic_email_validation` — adds the fln (19%) pattern
3. `person_linkedin_to_email_waterfall` — LinkedIn-based fallback

**Never use `person_linkedin_to_email_waterfall` as the primary email step** — it skips permutation validation entirely.

---

All errors discovered in real Clay → Deepline migration runs.

## run_javascript Errors

### Top-level await
**Error**: `"await is only valid in async functions"`
**Fix**: Wrap all async code:
```js
// WRONG
return await fetch(url);

// RIGHT
return (async () => {
  const resp = await fetch(url);
  return await resp.json();
})()
```

### Template literal conflict with bash
**Error**: Bash parses backticks inside JS code as subshell commands, breaking the script
**Fix**: Avoid template literals entirely. Use string concatenation:
```js
// WRONG (breaks bash)
const url = `https://api.clay.com/v3/tables/${TABLE_ID}`;

// RIGHT
const url = 'https://api.clay.com/v3/tables/' + TABLE_ID;
```
And use Python subprocess to build payloads — never hand-write JSON with embedded JS in bash strings.

### Cookie injection into JS string
**Pattern**: Inject bash vars into Python heredoc, then Python r-string into JS:
```python
COOKIE = "${CLAY_COOKIE}"
enrich_code = r"""...'cookie': '""" + COOKIE + r"""'..."""
```
The `r"""..."""` + concatenation pattern avoids all escaping conflicts.

---

## Deepline Interpolation Errors

### `{{row.column.field}}` not supported
**Error**: `"column 'row' not found"` or silent empty value
**Fix**: Never use `row.` prefix. Use `{{column_name}}` directly.
- Works: `{{fields.company_name}}`
- Fails: `{{row.fields.company_name}}`

### 3+ level nesting fails
**Error**: `E2BIG` arg too long, or column resolves to empty
**Fix**: Add a `run_javascript` flatten pass to hoist nested fields to top level.
- Works: `{{strategic_initiatives.extracted_json}}` (2 levels)
- Fails: `{{strategic_initiatives.extracted_json.top5_initiatives}}` (3 levels)

### `call_ai` json_mode output structure
**Issue**: `{{my_col.field_name}}` returns empty — the field isn't at top level
**Root cause**: `call_ai` with `json_mode` wraps output as `{output: "...", extracted_json: {...}}`
**Fix**: Always reference json_mode output via `.extracted_json`:
```
{{strategic_initiatives.extracted_json}}   ✓
{{strategic_initiatives.top5_initiatives}} ✗ (fails)
```

### Column dependency validation failure
**Error**: `"base column 'exa_research' not found"`
**Cause**: Referencing a column being defined in the same `--with` block
**Fix**: Split into separate `deepline enrich` invocations. Each pass can only reference columns that already exist from prior passes.

---

## call_ai Errors

### `agent: "claude"` blocked in direct execute
**Error**: `"Claude CLI does not support sub-calls in the same session"`
**Context**: Happens when running `deepline tools execute call_ai` directly from Claude CLI
**Fix**: This is expected. Use `deepline enrich --with 'col=call_ai:{...}'` instead — each row runs in a separate subprocess session.

### Timeout on WebSearch
**Error**: 180s timeout hit on `call_ai` with `allowed_tools: "WebSearch"`
**Fix**: Switch to `exa_search` as a separate column, then pass `{{exa_research}}` into `call_ai` without WebSearch. Faster and cheaper.

### Prompt too large (E2BIG) via interpolation
**Error**: `E2BIG` when interpolating a large JSON field into a prompt
**Fix**: Reference via `.extracted_json` path (deepline resolves this server-side, doesn't expand inline into the shell arg).

---

## Security Pitfalls

### Clay cookie embedded in `--with` payload → sent to Deepline telemetry
**Symptom**: Clay session cookie appears in Deepline's `telemetry/activity` logs
**Root cause**: `deepline enrich` sends `command_text = "deepline enrich " + " ".join(args)` to `POST /api/v2/telemetry/activity`. If the cookie is in the `--with` arg payload, it's in `command_text`.
**Fix**: Never embed the cookie in the JS code string. Use `process.env.CLAY_COOKIE` in JS and pass `env={**os.environ}` to subprocess:
```python
# WRONG — cookie in telemetry
enrich_code = r"""...'cookie': '""" + COOKIE + r"""'..."""

# RIGHT — cookie stays in env, never in command string
enrich_code = "...'cookie': process.env.CLAY_COOKIE..."
```
The `run_javascript` tool executes locally (never sent to Deepline's server), but the command-line string IS sent to telemetry. Keep credentials out of the command string.

### `valid_catch_all` treated as invalid

**Symptom**: Valid emails getting filtered out for catch-all domains; fln permutations rejected even when the format is correct.

**Root cause**: LeadMagic returns four distinct statuses. Scripts that only check for `valid` or `catch_all` miss `valid_catch_all`, which is the highest-confidence result (engagement-confirmed, <5% bounce rate):

| Status | Meaning | Accept? |
|---|---|---|
| `valid` | SMTP-verified deliverable | ✅ Yes |
| `valid_catch_all` | Catch-all domain + engagement signal confirms address | ✅ Yes (best for catch-all) |
| `catch_all` | Domain accepts all; unverifiable | ✅ Yes (same as Clay) |
| `unknown` | Server no response | ❌ No |
| `invalid` | Will bounce | ❌ No |

**Fix**: Accept all three in validation checks:
```js
const result = (data.result || data.status || data.email_status || '').toLowerCase();
return result === 'valid' || result === 'valid_catch_all' || result === 'catch-all' || result === 'catch_all';
```

---

### Cookie hardcoded in script file → git exposure
**Symptom**: Accidental `git add clay_fetch_records.sh` commits real session cookie
**Fix**: Use `.env` file only. Add `echo '.env' >> .gitignore` at top of every generated script block. Never set `CLAY_COOKIE=` inside the bash script itself.

---

## Clay API Errors

### Session cookie expired
**Symptom**: `run_javascript` returns `{error: "Unauthorized"}` or redirect HTML
**Fix**: Refresh `CLAY_COOKIE` from browser devtools:
1. Open `app.clay.com` in browser
2. DevTools → Network → filter `api.clay.com`
3. Click any request → Headers → Request Headers → Cookie
4. Copy the full `claysession=...` value

### `NO_CELL` vs error
**Clay data**: `NO_CELL` in a cell means the action was never triggered (cell never initialized), not that it failed. The entire Claygent replication exists because these cells were never run in Clay.

### `record_not_found` in bulk-fetch
**Symptom**: `{error: "record_not_found", record_id: "r_xxx"}`
**Cause**: Record ID doesn't exist or was deleted from the table
**Fix**: Skip these rows; they're not recoverable from Clay's API.

---

## Deepline Enrich Flags

### `--in-place` vs `--output`
- `--output path.csv`: First pass — writes new file from source CSV
- `--in-place`: Subsequent passes — updates the existing output file
- **Never** use `--in-place` on the source/input CSV — always on your own output

### `--with-force col` for reruns
Forces recompute of a single column without rerunning all others:
```bash
enrich_force "strategic_initiatives" "$STRAT"
```
