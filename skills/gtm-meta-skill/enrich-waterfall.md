# Enrich and Waterfall

Use this doc for `deepline enrich`, waterfalls, coalescing, and enrichment mechanics. Read when the task involves CSV enrichment, contact recovery, multi-provider fallbacks, or cleaning/merging data from parallel sources.

Read sections 8.1-8.5 for company -> contact, finding email, linkedins, signals, tech stack, etc, generally read if calling deepline enrich. 

## When to use `deepline enrich` vs `deepline tools execute`

| Use `deepline enrich` | Use `deepline tools execute` |
|-----------------------|-----------------------------|
| Any CSV/list with 2+ rows | Single one-off lookup (one company, one person) |
| Per-row operations (each row gets its own result) | Schema inspection, billing, auth, discovery |
| Waterfalls, parallel providers, `call_ai` columns | Quick validation of a tool's output shape |
| Iterative workflows (pilot → approve → full run) | Pre-flight checks in a script |

**Why enrich:** It parallelizes per-row work, resolves `{{column}}` interpolation across steps, opens the Playground for inspection, and batches inference efficiently. One-shot `tools execute` per row wastes turns and loses lineage.

## When to use `call_ai` vs direct provider tools

**Use `call_ai`** (inside `deepline enrich --with 'col=call_ai:...'`) when:
- **Per-row research** — funding stage, YC batch, tech stack, news signals, anything factual that requires web lookup. Individual providers have poor precision/recall; `call_ai` spins up agent instances that call exa, parallel, google search and improve results by ~94%.
- **Custom signals or messaging** — personalized outreach, qualification scoring, ICP-driven content. Check `prompts.json` first for templates.
- **Synthesis across sources** — combining multiple tool outputs into one structured answer.

**Haiku is the default for call_ai when model is omitted.** Only use sonnet or opus when haiku explicitly fails.

**Use direct provider tools** (e.g. `apollo_people_match`, `leadmagic_email_finder`) when:
- The task is mechanical: fetch email, validate email, get LinkedIn URL from known identifiers.
- You have strong identifiers (email, domain, name+company) and need a single structured field.
- Cost/speed matters and the provider's schema is sufficient.
- For paid-media signals, treat `leadmagic` and `adyntel` both have options.

```bash
# Per-row research — canonical call_ai pattern
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with 'yc_batch=call_ai:{"prompt":"What is the YC batch for {{company_name}}? Return only the code e.g. W21 S23.","agent":"claude","model":"haiku"}'
```

Add `"allowed_tools":"WebSearch"` for live web access. Add `"json_mode":{...schema...}` for structured output.

## Signal-first custom search inside enrich

Before custom-signal columns, run `deepline tools search <term>` and use matched fields exactly. Simple search terms like "investor" or "funding" are usually enough.

Flow:
1. Search 2-4 synonyms.
2. Add matched provider calls as `--with` columns.
3. Use `call_ai` only to synthesize/score those outputs.

```bash
deepline tools search investor
deepline tools search funding --prefix crustdata
```

```bash
deepline enrich --input accounts.csv --in-place --rows 0:1 \
  --with 'investor_candidates=crustdata_companydb_search:{"filters":[{"filter_type":"crunchbase_investors","type":"(.)","value":"{{target_investor}}"}],"limit":10}' \
  --with 'investor_signal=call_ai:{"prompt":"Given row data and investor_candidates, return JSON {is_match:boolean,evidence:string}. Keep evidence short and source-backed.","agent":"claude","model":"haiku"}'
```

## Contact enrichment tips

- **Email is king** — If the user has email, start there. Hit rates are highest and all person/company lookup steps can run simultaneously.
- **Parallel by default** — When you have email as input, run hunter, apollo, leadmagic (and others) in parallel. No reason to wait; structure `--with` columns so independent steps execute together.
- **Coalesce after parallel** — When merging data across sources, prefer the most detailed version of each field. See "Coalescing and cleaning" below.
- **Show sources** — Surface which API provided each piece of data so the user knows reliability. Preserve `_metadata` and step columns; in merged outputs, include a `_source` or `source_provider` field per field.

## Working directory

Your very first action (before preflight, before planning) must be: `mkdir -p tmp && WORKDIR=$(mktemp -d tmp/XXXX) && echo $WORKDIR`. Use `$WORKDIR/` for all files — JS extractors, scripts, logs, output CSVs. Always use relative paths — never hardcode absolute paths.

## Coalescing and cleaning (run_javascript)

After running parallel providers (e.g. apollo + leadmagic + crustdata), you often get multiple values for the same field. **Always coalesce** — pick the richest non-null value per field. Use `run_javascript` as a follow-up column.

**Rule:** Prefer the value with more detail (longer string, more structure). Prefer validated over unvalidated (e.g. leadmagic-validated email over raw apollo email). Track `_source` so the user knows provenance.

**Pattern — coalesce a single field from N providers:**

```javascript
// In $WORKDIR/coalesce_email.js — pick first non-null from provider outputs
const apollo = row["apollo_match"]?.data?.person?.email ?? row["apollo_match"]?._value?.data?.person?.email;
const lm = row["leadmagic_email"]?.data?.email ?? row["leadmagic_email"]?._value?.data?.email;
const crust = row["crust_profile"]?.data?.[0]?.email ?? row["crust_profile"]?.data?.[0]?.business_email?.[0];
return apollo || lm || crust || null;
```

**Pattern — coalesce multiple fields and track source:**

```javascript
// In $WORKDIR/coalesce_person.js — return {email, linkedin, _source}
function pick(a, b, c) { return a || b || c || null; }
const apollo = row["apollo_match"]?.data ?? row["apollo_match"]?._value?.data;
const lm = row["leadmagic_profile"]?.data ?? row["leadmagic_profile"]?._value?.data;
const crust = row["crust_profile"]?.data?.[0] ?? null;

const email = pick(apollo?.person?.email, lm?.email, crust?.email ?? crust?.business_email?.[0]);
const linkedin = pick(apollo?.person?.linkedin_url, lm?.linkedin_url, crust?.linkedin_url);
const _source = email ? (apollo?.person?.email ? "apollo" : lm?.email ? "leadmagic" : "crustdata") : null;

return { email, linkedin, _source };
```

**When to coalesce:**
- After parallel `--with` columns that all target the same field (email, phone, LinkedIn, company domain).
- After merging search results from multiple providers into one lead list.
- Before validation — coalesce first, then run `leadmagic_email_validation` on the merged value.

**Anti-pattern:** Do not leave raw provider columns as the final output. The user gets duplicate/conflicting values. Always add a coalesce step that produces a single canonical column per field.

## Verification and routing

### When to use direct Google CSE

**Direct Google CSE (`google_search_google_search`) on its own** is appropriate for one thing: LinkedIn profile lookup when you have highly specific identifiers. Use it when you can build a maximally specific query:
- Include every available row field: name + company + title + geo.
- Use `site:linkedin.com/in` scoping and quoted exact-match phrases.
- If row data is thin (just a name), inject ICP persona titles as search terms (e.g. "revops", "sales ops") to constrain results.
- Bad: `"Jane Smith" site:linkedin.com/in`
- Good: `"Jane Smith" "Acme Corp" "sales ops" site:linkedin.com/in`

If you can't build a specific enough query (missing company AND title AND geo), don't use raw CSE - ask the USER FOR MORE CONTEXT.

### Verification and quality (for enrich/waterfall)

- `leadmagic_email_validation` — deliverability at scale.
- `leadmagic_mobile_finder` — phone discovery when profile/email exists.
- `leadmagic_email_finder` — lower-cost fallback or missing-provider recovery.
- Apollo/PDL enrichment — corroboration before validation when identifiers are strong.

## Output policy: Playground-first for CSV

- Always use `deepline enrich` for list enrichment or discovery at scale (>5 rows). It parallelizes per-row calls, renders nicely for human review, and powers waterfalls. It auto-opens the Playground sheet so you can inspect rows, re-run blocks, and iterate.
- Even when you don't have a CSV, create one and use deepline enrich.
- This process requires iteration; one-shotting results via `deepline tools execute` enrichments is short sighted.
- If a command created CSV outside enrich, run `deepline csv render --csv <csv_path> --open`.
- In chat, send the file path + playground status, not pasted CSV rows, unless explicitly requested.
- Preserve lineage columns (especially `_metadata`) end-to-end. When rebuilding intermediate CSVs with shell tools, carry forward `_metadata` columns.

### Enrich reuse and reruns (canonical)

When `deepline enrich` runs against an existing output CSV:

- Match `--with` steps to existing enrich columns by the same `--with` output column name.
- If a matched cell already has a successful non-empty value, it is not rerun. Empty, errored, or rerunnable misses are rerun. If this is not the desired behavior, use --with-force instead, though this (may) waste money since we lose past enrichments. 
- you may also just create new columns and merge the results later with run_javascript.
- Rename/relabel alone is not new work.

## Waterfalls (short, opinionated). Always use when possible, safest way to enrich.

Default execution stance:

1. Run a real pilot first: `--rows 0:1`.
2. Keep waterfall in one command (`--with-waterfall` + `--end-waterfall`). Prefer a clear `--type` (or at minimum `--result-getters`) per block.
3. Review the `deepline enrich` completion output — it has fill rates, source, and miss reasons. Only use `deepline csv show` for sample rows or debugging a specific cell. See "Understanding results".

Default provider order for contact enrichment waterfalls:

1. `hunter`
2. `apollo`
3. `leadmagic`
4. `deepline_native`
5. `crustdata`
6. `peopledatalabs`

### Type/getter contract (critical)

- In CLI, `--with-waterfall <NAME>` is a label only.
- `--type` is the explicit type for the block and must be one of:
  - `email`, `phone`, `linkedin`, `first_name`, `last_name`, `full_name`
- `--type` says what the block is looking for (`email`, `phone`, etc.).
- `--result-getters` says where in provider output to find that value.
- Use both when possible: `--type` gives intent, `--result-getters` gives extraction path.
- After `--end-waterfall`, the waterfall name becomes a plain-text column with the resolved scalar (e.g. `{{email}}` = `"john@example.com"`).

Waterfall execution model: Each `--with` step inside a waterfall is evaluated as an independent candidate. The waterfall runs each in order and stops at the first step where `--result-getters` or the `--type` fetcher (which under the hood, encodes some bespoke result-getters itself) finds a non-null value. Steps do not see each other's results. A step using `run_javascript` must directly return the target value — it cannot reference another waterfall step's output via `row["step_name"]`, because that row key isn't populated until after the waterfall resolves.

### 8.1 If you have name + company and need email

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "email_recovery" \
  --type email \
  --result-getters '["data.email","email","data.0.email","data.emails.0.value","emails.0.value"]' \
  --with 'hunter_email=hunter_email_finder:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'apollo_match=apollo_people_match:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}"}' \
  --with 'leadmagic_email=leadmagic_email_finder:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'native_contact=deepline_native_enrich_contact:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'crust_profile=crustdata_person_enrichment:{"linkedinProfileUrl":"{{colA.linkedin}}","fields":["email","current_employers"],"enrichRealtime":true}' \
  --with 'pdl_enrich=peopledatalabs_enrich_contact:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --end-waterfall \
  --with 'email_validation=leadmagic_email_validation:{"email":"{{email_recovery}}"}'
```

### 8.2 If you have LinkedIn URL and need email

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "email_recovery" \
  --type email \
  --result-getters '["data.0.email","data.email","emails.0.address","data.emails.0.value"]' \
  --with 'hunter_email=hunter_email_finder:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'apollo_match=apollo_people_match:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}","domain":"{{Company Domain}}"}' \
  --with 'leadmagic_email=leadmagic_email_finder:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'native_contact=deepline_native_enrich_contact:{"linkedin":"{{LinkedIn URL}}","first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'crust_profile=crustdata_person_enrichment:{"linkedinProfileUrl":"{{colA.linkedin}}","fields":["email","current_employers"],"enrichRealtime":true}' \
  --with 'pdl_enrich=peopledatalabs_enrich_contact:{"linkedin_url":"{{colA.linkedin}}","first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --end-waterfall \
  --with 'email_validation=leadmagic_email_validation:{"email":"{{email_recovery}}"}'
```

(catchall email validation is messaged as an error, but really its just inconclusive and you can continue)

### 8.3 If you have email and need person/company context

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with 'email_validation=leadmagic_email_validation:{"email":"{{Email}}"}' \
  --with-waterfall "full_name" \
  --type full_name \
  --result-getters '["person.name","data.person.name","data.name","name"]' \
  --with 'hunter_person=hunter_people_find:{"email":"{{Email}}"}' \
  --with 'apollo_match=apollo_people_match:{"email":"{{Email}}"}' \
  --with 'leadmagic_profile=leadmagic_profile_search:{"profile_url":"{{LinkedIn URL}}"}' \
  --with 'native_contact=deepline_native_enrich_contact:{"email":"{{Email}}"}' \
  --with 'crust_profile=crustdata_person_enrichment:{"linkedinProfileUrl":"{{colA.linkedin}}","fields":["current_employers"],"enrichRealtime":true}' \
  --with 'pdl_identify=peopledatalabs_person_identify:{"email":"{{Email}}"}' \
  --end-waterfall
```

### 8.4 If you have first name + last name + domain and need email (pattern waterfall)

Always validate email at the end. Run pattern checks first (`v1..v4`), then provider fallbacks.

```bash
deepline enrich --input leads.csv --in-place --rows 0:0 \
  --with 'email_patterns=run_javascript:{"code":"const f=(row[\"First Name\"]||\"\").trim().toLowerCase(); const l=(row[\"Last Name\"]||\"\").trim().toLowerCase(); const d=(row[\"Company Domain\"]||\"\").trim().toLowerCase(); if(!f||!l||!d) return {}; return {p1:`${f}.${l}@${d}`,p2:`${f[0]}${l}@${d}`,p3:`${f}${l[0]}@${d}`,p4:`${f}@${d}`};"}' \
  --with-waterfall "email_recovery" \
  --type email \
  --result-getters '["data.email","email","data.0.email"]' \
  --with 'v1=leadmagic_email_validation:{"email":"{{email_patterns.p1}}"}' \
  --with 'v2=leadmagic_email_validation:{"email":"{{email_patterns.p2}}"}' \
  --with 'v3=leadmagic_email_validation:{"email":"{{email_patterns.p3}}"}' \
  --with 'v4=leadmagic_email_validation:{"email":"{{email_patterns.p4}}"}' \
  --with 'hunter_email=hunter_email_finder:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'apollo_match=apollo_people_match:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}","domain":"{{Company Domain}}"}' \
  --with 'leadmagic_email=leadmagic_email_finder:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'native_contact=deepline_native_enrich_contact:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --with 'crust_profile=crustdata_person_enrichment:{"linkedinProfileUrl":"{{colA.linkedin}}","fields":["email","current_employers"],"enrichRealtime":true}' \
  --with 'pdl_enrich=peopledatalabs_enrich_contact:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Company Domain}}"}' \
  --end-waterfall \
  --with 'email_validation=leadmagic_email_validation:{"email":"{{email_recovery}}"}'
```

### 8.5 Company Name / Account List -> Find the specific contact with the right titles.

Apify is the best at this because it has the tighest linkedin integration. Other providers like apollo abstract that away and end up stale / missing data / very bad.

Example (type outcome: can select people like Drew Bredvick at Vercel when present):

```bash
deepline enrich --input companies.csv --in-place --rows 0:0 \
  --with 'apollo_company=apollo_company_search:{"q_organization_name":"{{Company}}","per_page":3,"page":1}' \
  --with 'company_profile=run_javascript:{"code":"const q=(row[\"Company\"]||\"\").trim().toLowerCase(); const d=row[\"apollo_company\"]?.data||{}; const a=(d.accounts||[]).find(x=>((x?.name||\"\").trim().toLowerCase()===q))||(d.accounts||[])[0]||null; if(!a) return null; return {company_name:a.name||null, company_domain:a.primary_domain||a.domain||null, company_linkedin:a.linkedin_url||null};"}' \
  --with 'apify_gtm_people=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-company-employees-scraper-no-cookies","input":{"identifier":"{{company_profile.data.company_linkedin}}","max_employees":60,"job_title":"gtm"},"timeoutMs":180000}' \
  --with 'pick_persona=call_ai_claude_code:{"model":"haiku","json_mode":{"type":"object","properties":{"full_name":{"type":"string"},"headline":{"type":"string"},"linkedin_url":{"type":"string"},"why_fit":{"type":"string"}},"required":["full_name","headline","linkedin_url","why_fit"],"additionalProperties":false},"system":"Pick one best outreach persona for GTM at the target company. Prefer current GTM ownership (growth, revops, partnerships, GTM engineering). If Drew Bredvick is present, choose him.","prompt":"Company: {{Company}}\\nCandidates JSON: {{apify_gtm_people.data}}\\nReturn strict JSON only.","agent":"claude"}' \
  --with 'apify_posts=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-profile-posts","input":"{\"username\":\"{{pick_persona.extracted_json.linkedin_url}}\",\"total_posts\":5,\"limit\":5}","timeoutMs":180000}' \
  --with 'post_research=call_ai_claude_code:{"model":"haiku","json_mode":{"type":"object","properties":{"themes":{"type":"array","items":{"type":"string"}},"signals":{"type":"array","items":{"type":"string"}},"hook":{"type":"string"}},"required":["themes","signals","hook"],"additionalProperties":false},"prompt":"Analyze this person for outbound personalization. Person: {{pick_persona.output}}Recent posts: {{apify_posts.extracted_json}}Return strict JSON.","agent":"claude"}' \
  --with 'custom_message=call_ai_claude_code:{"model":"haiku","json_mode":{"type":"object","properties":{"subject":{"type":"string"},"message":{"type":"string"}},"required":["subject","message"],"additionalProperties":false},"prompt":"Write one concise outbound message (<=90 words) to {{pick_persona.extracted_json.full_name}} at {{company_profile.data.company_name}} using: {{post_research.extracted_json}}. No fluff, specific details only. make is very casual, hook is about something i was interested in the post, about why i cant ignore it because im building gtm tooling."}'
```

Interpolation contract for this flow:
- `company_profile` values are under `{{company_profile.data.*}}`.
- `pick_persona` parsed JSON fields are consumed via `{{pick_persona.extracted_json.*}}`.
- `post_research` input intentionally uses `{{pick_persona.output}}` + `{{apify_posts.extracted_json}}`.

Then continue remaining rows from the same file with in-place (do not re-enrich pilot rows):

```bash
deepline enrich --input companies.csv --in-place --rows 1:2 ...
```

### 8.5.1 Quick domain resolution guide (required before people enrichment)

Use this policy whenever input starts from `Company` name only:

1) Resolver/search step may use name:
- `apollo_company_search` (`q_organization_name`)
- `crustdata_companydb_search` (name filters)

2) Extract a canonical profile object:
- `company_name`
- `company_domain`
- `company_linkedin`

3) All non-resolver company-targeted steps must use strong identifiers:
- Prefer domain (`q_organization_domains_list`, `domain`, `company_domain`)
- Otherwise use stable IDs (`organization_ids`, provider IDs)

Minimal fallback when resolver misses:

```bash
deepline tools execute google_search --payload '{"query":"site:linkedin.com/company \"{{Company}}\"","num":5}' --json
```

Then map to `company_profile` and continue with domain/ID-based steps. Do not run name-only `apollo_people_search` or name-only `crustdata_enrich_company`.

### Hard rules

- Do not chain setup + enrich + snapshot in one line.
- Do not reuse an existing output file path.
- Scale to full rows only after the one-row pilot returns valid shape.
- Always include `leadmagic_email_validation` as the final email-quality gate if doing email enrichment, though it may be inconclusive and you can continue.
- For CLI waterfalls, use canonical type names (`email|phone|linkedin|first_name|last_name|full_name`) in `--type`.
- Always add `--result-getters` so `{{<waterfall_name>}}` resolves to the matched scalar.
- For complex JS logic, do not inline code inside JSON; use `run_javascript:@/path.js`.
- Prefer targeted reruns with `--with-force <alias>` over global `--force` when only specific columns need recompute.

## Pre-flight and shape checks

`deepline auth status`
`deepline billing balance --json`

### Tool shape validation (required before JS extractors)

1. `deepline tools get <tool_id>` for each provider in your plan.
2. Run a real pilot with `--rows 0:1`.
3. Correct interpolation if mismatch before any paid batch.

### `run_javascript` payload safety (critical)

Use this whenever you add JS extractor columns:

- Default to file-backed JS for anything non-trivial:
  - `--with 'post_signals=run_javascript:@$WORKDIR/post_signals.js'`
- Keep inline JSON JS only for very short snippets with minimal escaping.
- If you use inline payloads:
  - Wrap the full `--with` spec in single quotes.
  - Escape only inner double quotes inside JSON code strings (for example `row[\"Company\"]`).
  - Do not insert shell-only escapes like `\!` inside JSON strings.
- If you see `Invalid JSON payload ... (Invalid \\escape ...)`, treat it as quoting/escaping failure, not provider failure:
  1. Move JS into a file.
  2. Re-run with `run_javascript:@/path.js`.
  3. Continue debugging only after parse passes.

### Pilot/preview checklist

- For unknown/modified payloads: run at least one real one-row pilot.
- For direct JSON extraction logic: validate with real tool output first.
- For high-risk parsing/matching: use `--rows 0:1` and inspect returned cell shape.

## Common output paths (quick reference)

| Tool | Input fields | Key output paths |
|------|--------------|------------------|
| `adyntel_facebook_ad_search` | `keyword` | `.data` |
| `leadmagic_b2b_ads_search` | `company_domain` | `.data` |
| `leadmagic_email_finder` | `first_name`, `last_name`, `domain` | `.data.email`, `.data.status` |
| `leadmagic_profile_search` | `profile_url` | `.data.company_website`, `.data.full_name`, `.data.work_experience[0].company_website` |
| `leadmagic_email_validation` | `email` | `.data.email_status`, `.data.is_domain_catch_all`, `.data.mx_provider` |
| `crustdata_person_enrichment` | `linkedinProfileUrl` | `.data[0].name`, `.data[0].email`, `.data[0].current_employers[0].employer_company_website_domain[0]` |

## Understanding results

**`deepline enrich` completion output** (printed automatically, no extra call needed):
- `columnStats` — per-column fill rates (`non_empty`), unique counts, top values
- `{waterfall_name}_source` column — shows which provider won each row (e.g. `"hunter_email": "5 (100%)"`)
- `miss_reasons` — why rows failed per step
- This is usually sufficient. Do not follow up with multiple `csv show | jq` calls for info already here.

**`deepline csv show`** — use when you need more than the completion output:
- `--summary` — same `columnStats` on demand for any CSV
- `--format table --rows 0:4` — readable sample to show the user
- `--format json --verbose --rows N:N 2>/dev/null` — returns `{"rows": [{...}, ...]}`, pipe to `jq '.rows[]'` (not `.[]`)

See [playground-guide.md](playground-guide.md) for re-run blocks (`--execute_cells`), etc.
