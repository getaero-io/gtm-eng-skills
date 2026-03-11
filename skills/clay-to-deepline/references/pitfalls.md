# Known Pitfalls and Fixes

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
