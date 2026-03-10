# Enrich and Waterfall

Use this doc for `deepline enrich`, waterfalls, coalescing, and enrichment mechanics. Read when the task involves CSV enrichment, contact recovery, multi-provider fallbacks, or cleaning/merging data from parallel sources.

Use native play tool IDs for concise enrich commands whenever possible:
`name_and_company_to_email_waterfall`, `person_linkedin_to_email_waterfall`, `person_enrichment_from_email_waterfall`, `cost_aware_first_name_and_domain_to_email_waterfall`, `company_to_contact_by_role_waterfall`.

## Quick syntax reference (copy-paste ready)

```bash
# run_javascript — always file-backed (required)
--with '{"alias":"col","tool":"run_javascript","payload":{"code":"@$WORKDIR/script.js"}}'

# Provider tool — inline
--with '{"alias":"col","tool":"provider_tool","payload":{"param":"{{FIELD}}"}}'

# Waterfall
--with-waterfall "email"
--with '{"alias":"step1","tool":"dropleads_email_finder","payload":{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company_name":"{{Company}}"},"extract_js":"extract(\"email\")"}'
--with '{"alias":"step2","tool":"hunter_email_finder","payload":{"first_name":"{{First Name}}","last_name":"{{Last Name}}","domain":"{{Domain}}"},"extract_js":"extract(\"email\")"}'
--end-waterfall
```

**WRONG syntaxes (do NOT use):**

- `run_javascript("return ...")` — not a function call
- `run_javascript:'code'` — not valid
- Inline JS in `--with` JSON — do not use. Always use `@file.js`.

## When to use `deepline enrich` vs `deepline tools execute`

| Use `deepline enrich` | Use `deepline tools execute` |
|-----------------------|-----------------------------|
| Any CSV/list with 2+ rows | Single one-off lookup (one company, one person) |
| Per-row operations (each row gets its own result) | Schema inspection, billing, auth, discovery |
| Waterfalls, parallel providers, `call_ai` columns | Quick validation of a tool's output shape |
| Iterative workflows (pilot → approve → full run) | Pre-flight checks in a script |

**Why enrich:** It parallelizes per-row work, resolves `{{column}}` interpolation across steps, opens the Playground for inspection, and batches inference efficiently. One-shot `tools execute` per row wastes turns and loses lineage.

## When to use `call_ai` vs direct provider tools

**Use `call_ai`** (inside `deepline enrich --with '{"alias":"col","tool":"call_ai","payload":{"prompt":"..."}}'`) when:
- **Per-row research** — funding stage, YC batch, tech stack, news signals, anything factual that requires web lookup. Individual providers have poor precision/recall; `call_ai` spins up agent instances that call exa, parallel, google search and improve results by ~94%.
- **Custom signals or messaging** — personalized outreach, qualification scoring, ICP-driven content. Check `prompts.json` first for templates.
- **Synthesis across sources** — combining multiple tool outputs into one structured answer.

**Haiku is the default for call_ai when model is omitted.** Only use sonnet or opus when haiku explicitly fails.

**Use direct provider tools** (e.g. `dropleads_email_finder`, `hunter_email_finder`, `leadmagic_email_finder`) when:
- The task is mechanical: fetch email, validate email, get LinkedIn URL from known identifiers.
- You have strong identifiers (email, domain, name+company) and need a single structured field.
- Cost/speed matters and the provider's schema is sufficient.
- For paid-media signals, treat `leadmagic` and `adyntel` both have options.

**Tool preference ladder — pick the highest-applicable rung:**

1. **Direct provider tools + waterfalls** — For mechanical lookups (email, phone, LinkedIn URL) where you have strong identifiers. Cheapest, fastest, most reliable. Use `dropleads_email_finder`, `hunter_email_finder`, waterfall syntax, etc.
2. **Apify actors** — For LinkedIn profile data, work history, company employees, posts, and profile signals. `apify_run_actor_sync` returns structured data directly and is the best way to get rich LinkedIn context. Prefer this over `call_ai` for any LinkedIn-adjacent task.
3. **`run_javascript`** — For parsing/scoring/extracting signals from structured provider or Apify output. Free and instant. Use for founder detection, title scoring, signal extraction — anywhere you're transforming existing data, not fetching new data.
4. **`call_ai`** — For per-row research, synthesis, and custom signals that no provider tool covers. Good for: funding stage lookup, YC batch, competitive landscape, personalized messaging. Haiku is the default model.

**Known failure modes to avoid:**

- **`call_ai_claude_code`** — Do not use. Spawns nested Claude sessions that error out. Use `call_ai` with `agent:"claude"` instead.
- **`call_ai` with `"allowed_tools":"WebSearch"` for LinkedIn data** — Tends to time out (180s) and returns noisy results. Apify is faster and returns structured data for LinkedIn tasks. Use Exa, Google CSE, or Parallel search directly when you need web data.

```bash
# Per-row research — canonical call_ai pattern
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with '{"alias":"yc_batch","tool":"call_ai","payload":{"prompt":"What is the YC batch for {{company_name}}? Return only the code e.g. W21 S23.","agent":"claude","model":"haiku"}}'
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
  --with '{"alias":"investor_candidates","tool":"crustdata_companydb_search","payload":{"filters":[{"filter_type":"crunchbase_investors","type":"(.)","value":"{{target_investor}}"}],"limit":10}}' \
  --with '{"alias":"investor_signal","tool":"call_ai","payload":{"prompt":"Given row data and investor_candidates, return JSON {is_match:boolean,evidence:string}. Keep evidence short and source-backed.","agent":"claude","model":"haiku"}}'
```

## Contact enrichment tips

- **Email is king** — If the user has email, start there. Hit rates are highest and all person/company lookup steps can run simultaneously.
- **Parallel by default** — When you have email as input, run hunter, leadmagic (and others) in parallel. No reason to wait; structure `--with` columns so independent steps execute together.
- **Coalesce after parallel** — When merging data across sources, prefer the most detailed version of each field. See "Coalescing and cleaning" below.
- **Show sources** — Surface which API provided each piece of data so the user knows reliability. Preserve `_metadata` and step columns; in merged outputs, include a `_source` or `source_provider` field per field.

## Working directory

Your very first action (before preflight, before planning) must be: `mkdir -p tmp && WORKDIR=$(mktemp -d tmp/XXXX) && echo $WORKDIR`. Use `$WORKDIR/` for all files — JS extractors, scripts, logs, output CSVs. Always use relative paths — never hardcode absolute paths.

## Coalescing and cleaning (run_javascript)

After running parallel providers (e.g. leadmagic + crustdata), you often get multiple values for the same field. **Always coalesce** — pick the richest non-null value per field. Use `run_javascript` as a follow-up column.

**Rule:** Prefer the value with more detail (longer string, more structure). Prefer validated over unvalidated (e.g. leadmagic-validated email over unvalidated source email). Track `_source` so the user knows provenance.

**Pattern — coalesce a single field from N providers:**

```javascript
// In $WORKDIR/coalesce_email.js — pick first non-null from provider outputs
const dropleads = row["dropleads_email"]?.data?.email ?? row["dropleads_email"]?._value?.data?.email;
const lm = row["leadmagic_email"]?.data?.email ?? row["leadmagic_email"]?._value?.data?.email;
const crust = row["crust_profile"]?.data?.[0]?.email ?? row["crust_profile"]?.data?.[0]?.business_email?.[0];
return dropleads || lm || crust || null;
```

**Pattern — coalesce multiple fields and track source:**

```javascript
// In $WORKDIR/coalesce_person.js — return {email, linkedin, _source}
function pick(a, b, c) { return a || b || c || null; }
const native = row["native_contact"]?.data ?? row["native_contact"]?._value?.data;
const lm = row["leadmagic_profile"]?.data ?? row["leadmagic_profile"]?._value?.data;
const crust = row["crust_profile"]?.data?.[0] ?? null;

const email = pick(native?.person?.email, lm?.email, crust?.email ?? crust?.business_email?.[0]);
const linkedin = pick(native?.person?.linkedin_url, lm?.linkedin_url, crust?.linkedin_url);
const _source = email ? (native?.person?.email ? "deepline_native" : lm?.email ? "leadmagic" : "crustdata") : null;

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
- `forager_person_reverse_lookup` — phone recovery from an email or phone.
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
2. Keep waterfall in one command (`--with-waterfall` + `--end-waterfall`). Put an explicit extractor on every `--with` step.
3. Review the `deepline enrich` completion output — it has fill rates, source, and miss reasons. Only use `deepline csv show` for sample rows or debugging a specific cell. See "Understanding results".

Default provider order for contact enrichment waterfalls:

{waterfall_default_order}

### Extractor contract (critical)

- Canonical scalar targets for `extract("<target>")`: `email`, `phone`, `linkedin`, `first_name`, `last_name`, `full_name`, `title`
- In CLI, `--with-waterfall <NAME>` is a label only.
- Every step inside the block must declare an extractor:
  - `"extract_js":"extract(\"email\")"`
  - `"extract_js":"extractList({ keys: [\"full_name\", \"linkedin\", \"email\", \"title\"] })"` for list waterfalls used with `--min-results`
- Use `extract("<target>")` only for those canonical scalar targets.
- `extractList({ keys: [...] })` builds each list item from canonical target keys registered on that tool. The keys are not arbitrary JSON paths; they must be supported canonical targets such as `full_name`, `linkedin`, `email`, `title`.
- If you need explicit paths, shaping, filtering, or logic, write JS instead.
- Use `extract(...)` for scalar/object waterfalls. Use `extractList(...)` for list waterfalls collecting toward `--min-results`.

### Native plays (concise, preferred)

Use these first before writing manual `--with-waterfall` blocks.

Native play tools compile to standard enrich waterfall specs (`playExpansion.steps`).
If you need to tune provider order, remove/add providers, or tweak payload params/extractors, inspect the play expansion and copy it into a manual waterfall:

```bash
deepline tools get person_linkedin_to_email_waterfall --json
```

Then edit the returned `playExpansion.steps` into:
- `--with-waterfall ...`
- repeated `--with '{"alias":"...","tool":"...","payload":{...},"extract_js":"..."}'`
- `--end-waterfall`

### 8.1 If you have name + company and need email

Problem category: contact email recovery from person + account identifiers.
Input profile: `first_name`, `last_name`, `company_name`, `domain`.
Output target: one best work email (then validate separately when needed).

Play tool: `name_and_company_to_email_waterfall`
Under the hood this compiles to a waterfall:
`dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> deepline_native_enrich_contact -> crustdata_person_enrichment -> peopledatalabs_enrich_contact`

```bash
deepline enrich --input leads.csv --output /tmp/name_company_email.csv --rows 0:5 \
  --with '{"alias":"email_from_name_company","tool":"name_and_company_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company_name}}","domain":"{{domain}}"}}'
```

Example query (mixed contacts):

```bash
deepline enrich --input /tmp/mixed_contacts.csv --output /tmp/mixed_name_company_to_email.csv --rows 0:5 \
  --with '{"alias":"email_from_name_company","tool":"name_and_company_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company_name}}","domain":"{{domain}}"}}'
```

### 8.2 If you have LinkedIn URL and need email

Problem category: LinkedIn-seeded email recovery.
Input profile: `linkedin_url`, `first_name`, `last_name`, `domain` (optional: `company_name`).
Output target: one best work email resolved from LinkedIn-first enrichment.

Play tool: `person_linkedin_to_email_waterfall`
Under the hood this compiles to a waterfall:
`dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> deepline_native_enrich_contact -> crustdata_person_enrichment -> peopledatalabs_enrich_contact`

`linkedin_url` alone is not valid for this native play. The waterfall starts with deterministic providers that require `first_name`, `last_name`, and `domain`, so provide those fields up front.

```bash
deepline enrich --input leads.csv --output /tmp/linkedin_email.csv --rows 0:5 \
  --with '{"alias":"email_from_linkedin","tool":"person_linkedin_to_email_waterfall","payload":{"linkedin_url":"{{linkedinUrl}}","first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

Example query (mixed Dropleads seed):

```bash
deepline enrich --input /tmp/mixed_dropleads.csv --output /tmp/mixed_linkedin_to_email.csv --rows 0:8 \
  --with '{"alias":"email_from_linkedin","tool":"person_linkedin_to_email_waterfall","payload":{"linkedin_url":"{{linkedinUrl}}","first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

### 8.3 If you have email and need person/company context

Problem category: reverse enrichment from known email.
Input profile: `email`.
Output target: hydrated person/company context (name, company, LinkedIn, source).

Play tool: `person_enrichment_from_email_waterfall`
Under the hood this compiles to a waterfall:
`hunter_people_find -> crustdata_enrich_contact -> prospeo_enrich_person -> apollo_people_match -> deepline_native_enrich_contact`

```bash
deepline enrich --input leads.csv --output /tmp/email_context.csv --rows 0:5 \
  --with '{"alias":"person_context","tool":"person_enrichment_from_email_waterfall","payload":{"email":"{{email}}"}}'
```

Example query (run after 8.1 output):

```bash
deepline enrich --input /tmp/mixed_name_company_to_email.csv --output /tmp/mixed_email_context.csv --rows 0:5 \
  --with '{"alias":"person_context","tool":"person_enrichment_from_email_waterfall","payload":{"email":"{{email_from_name_company}}"}}'
```

### 8.4 If you have first name + last name + domain and need email

Problem category: pattern-first email recovery.
Input profile: `first_name`, `last_name`, `domain`.
Output target: one best work email with deterministic pattern checks before premium lookups.

Play tool: `cost_aware_first_name_and_domain_to_email_waterfall`
Under the hood this compiles to a waterfall:
`leadmagic_email_validation (first.last@, firstlast@, first_last@) -> dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> deepline_native_enrich_contact -> peopledatalabs_enrich_contact`

```bash
deepline enrich --input leads.csv --output /tmp/name_domain_email.csv --rows 0:5 \
  --with '{"alias":"email_from_name_domain","tool":"cost_aware_first_name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

Example query (mixed contacts):

```bash
deepline enrich --input /tmp/mixed_contacts.csv --output /tmp/mixed_name_domain_to_email.csv --rows 0:5 \
  --with '{"alias":"email_from_name_domain","tool":"cost_aware_first_name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

### 8.5 Company Name / Account List -> Find specific contacts by role

Problem category: account-to-contact role targeting.
Input profile: `company_name`, `domain`, `job_titles` (optional: `seniority`, `hunter_seniority`, `hunter_department`, `limit`).
Output target: candidate contacts for the requested function/title.

Play tool: `company_to_contact_by_role_waterfall`
Under the hood this compiles to a list waterfall (`min_results: 3`):
`dropleads_search_people -> hunter_domain_search -> apollo_search_people_with_match -> icypeas_find_people -> crustdata_people_search`

**Key provider notes (tested, validated):**
- **dropleads**: domain-only (`companyDomains`). Do NOT pass `companyNames` or `keywords` — they degrade recall. Minimal payload: `{"filters":{"companyDomains":["domain.com"],"jobTitles":["sales"],"seniority":["c-level","vp","head","director"]},"pagination":{"page":1,"limit":1}}`.
- **hunter**: domain-only. Do NOT pass `company` param — it has no positive effect.
- **apollo**: `person_seniorities` uses a different enum from dropleads. Valid values: `owner`, `founder`, `c_suite`, `partner`, `vp`, `head`, `director`, `manager`, `senior`. Note `c_suite` (not `c-level`). The play hardcodes `["c_suite","vp","head","director"]` — do not pass raw dropleads seniority values. `q_keywords` returns 0 results for this use case — omit it.
- **icypeas** (`icypeas_find_people`): `currentCompanyWebsite.include=["domain.com"]` works with a bare domain. Title specificity matters a lot: broad terms like `sales` return large sets, while exact phrases like `head of sales` or `vp sales` narrow sharply. Pass `job_titles` as one or more exact titles; do not assume separate seniority filtering exists here.
- **crustdata** (`crustdata_people_search`): Structured fallback search on PersonDB using `companyDomain`, `titleKeywords`, optional `seniority`, and `limit`. Less brittle than public-web search and can return email when Crust has coverage.

```bash
deepline enrich --input accounts.csv --output /tmp/company_role_contacts.csv --rows 0:5 \
  --with '{"alias":"role_contacts","tool":"company_to_contact_by_role_waterfall","payload":{"company_name":"{{}}","domain":"{{domain}}","job_titles":"{{job_titles}}"}}'
```

Example query (mixed company roles):

```bash
deepline enrich --input /tmp/mixed_company_roles.csv --output /tmp/mixed_company_role_contacts.csv --rows 0:2 \
  --with '{"alias":"role_contacts","tool":"company_to_contact_by_role_waterfall","payload":{"company_name":"{{company_name}}","domain":"{{domain}}","job_titles":"{{job_titles}}"}}'
```

### Coverage and gaps

Covered by native plays:
- `name_and_company_to_email_waterfall`
- `person_linkedin_to_email_waterfall`
- `person_enrichment_from_email_waterfall`
- `cost_aware_first_name_and_domain_to_email_waterfall`
- `company_to_contact_by_role_waterfall`

Not a single native play (still compose with multiple steps):
- `company_to_contact_domain_resolution`
- `multi_stage_pipeline_search_score_scrape_extract_email`

### company_to_contact_domain_resolution

Use this policy whenever input starts from `Company` name only:

1) Resolver/search step may use name:
- `dropleads_search_people` (`companyNames`)
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
deepline tools execute google_search --payload '{"query":"site:linkedin.com/company \"{{Company}}\"","num":5}'
```

Then map to `company_profile` and continue with domain/ID-based steps. Do not run name-only company-name-only `apollo_*` search as resolver.

### multi_stage_pipeline_search_score_scrape_extract_email

Use this pattern when you need to find contacts matching a specific profile (e.g. second-time founders, GTM engineers) where structured search filters alone are insufficient.

**Stage 1: Search** — See [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md) for search patterns and provider selection. Use `dropleads_search_people` with broad keyword + seniority filters (see "Role-based contact search" in that doc).

**Stage 2: Pre-score** — Use `run_javascript` to score/filter candidates by title keywords before paying for enrichment. Fast and free.

**Stage 3: Scrape** — Prefer `apify_run_actor_sync` with LinkedIn scrapers for work history, posts, or company employees. Apify returns structured data directly — faster and cheaper than `call_ai` with WebSearch for LinkedIn-adjacent tasks.

**Stage 4: Extract signals** — Prefer `run_javascript` to parse structured Apify/provider output (e.g. detect founder status from work history, extract hiring signals from posts). Free and instant. Use `call_ai` when you need synthesis or judgment that JS can't express.

**Stage 5: Email waterfall** — Use `--with-waterfall` for email recovery on qualified contacts only.

```bash
# Stage 1+2: Search and pre-score in one enrich pass
deepline enrich --input seed.csv --in-place --rows 0:1 \
  --with '{"alias":"contacts","tool":"dropleads_search_people","payload":{"filters":{"jobTitles":["Sales","Revenue","Growth"],"seniority":["C-Level","VP"],"industries":["Software"],"personalCountries":{"include":["United States"]}},"pagination":{"page":1,"limit":25}}}' \
  --with '{"alias":"title_score","tool":"run_javascript","payload":{"code":"@$WORKDIR/score_titles.js"}}'

# Stage 3: Scrape LinkedIn profiles for qualified contacts
# BATCHING: Pass all URLs in one profileUrls array instead of one call per row.
# Collect URLs first, then run a single Apify actor call.
deepline tools execute apify_run_actor_sync --payload '{"actorId":"apimaestro/linkedin-profile-scraper","input":{"profileUrls":["https://linkedin.com/in/person1","https://linkedin.com/in/person2","https://linkedin.com/in/person3"]},"timeoutMs":180000}'

# Stage 4: Extract founder signal from work history
deepline enrich --input seed.csv --in-place --rows 0:1 \
  --with '{"alias":"is_founder","tool":"run_javascript","payload":{"code":"@$WORKDIR/detect_founder.js"}}'

# Stage 5: Email waterfall for qualified founders only
deepline enrich --input qualified.csv --in-place --rows 0:1 \
  --with-waterfall "email" \
  --with '{"alias":"dropleads_email","tool":"dropleads_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company}}"},"extract_js":"extract(\"email\")"}' \
  --with '{"alias":"hunter_email","tool":"hunter_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"},"extract_js":"extract(\"email\")"}' \
  --end-waterfall \
  --with '{"alias":"email_valid","tool":"leadmagic_email_validation","payload":{"email":"{{email}}"}}'
```

**Key:** Prefer `run_javascript` (free, fast) for scoring/extraction, `apify_run_actor_sync` for LinkedIn data, and waterfalls for email. These are the right tools for their respective jobs — `call_ai` adds latency and cost when structured alternatives exist.

### 8.7 LinkedIn Profile Validation

LinkedIn URLs from any provider can be stale or wrong. Every LinkedIn lookup is two phases: **find** then **validate**. See [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md) "LinkedIn profile lookup and validation" for the full provider waterfall and validation rules.

Summary: get a candidate URL from the cheapest provider (dropleads → CSE → Exa → Crustdata), then **always** validate it with Apify by scraping the profile and checking name + work history. If confirmed, update the row with fresh data from the profile. If suspect (name matches but company changed), update with the new company/title.

### 8.8 If you need a Phone Number

If you have an email and need a phone, run Forager first as reverse lookup, then fall back to native phone enrichment:

```bash
deepline enrich --input contacts.csv --output /tmp/contacts_phone.csv --rows 0:2 \
  --with-waterfall "phone_recovery" \
  --with '{"alias":"forager_for_phone","tool":"forager_person_reverse_lookup","payload":{"email":"{{Email}}"},"extract_js":"extract(\"phone\")"}' \
  --with '{"alias":"native_phone","tool":"deepline_native_enrich_phone","payload":{"email":"{{Email}}"},"extract_js":"extract(\"phone\")"}' \
  --end-waterfall \
  --with '{"alias":"phone","tool":"run_javascript","payload":{"code":"const f = row[\"forager_for_phone\"]?.data ?? row[\"forager_for_phone\"]?._value?.data; const n = row[\"native_phone\"]?.data ?? row[\"native_phone\"]?._value?.data; return f?.phone_numbers?.[0] ?? f?.person?.phone_numbers?.[0] ?? f?.phone ?? n?.data?.phone ?? n?.person?.phone ?? n?.phone ?? n?.results?.[0]?.phone ?? null;"}}' \
  --with '{"alias":"phone_source","tool":"run_javascript","payload":{"code":"const f = row[\"forager_for_phone\"]?.data ?? row[\"forager_for_phone\"]?._value?.data; const n = row[\"native_phone\"]?.data ?? row[\"native_phone\"]?._value?.data; if (f?.phone_numbers?.[0] || f?.person?.phone_numbers?.[0] || f?.phone) return \"forager\"; if (n?.data?.phone || n?.person?.phone || n?.phone || n?.results?.[0]?.phone) return \"deepline_native\"; return null;"}}'
```

### Hard rules

- Do not chain setup + enrich + snapshot in one line.
- Do not reuse an existing output file path.
- Scale to full rows only after the one-row pilot returns valid shape.
- Always include `leadmagic_email_validation` as the final email-quality gate if doing email enrichment, though it may be inconclusive and you can continue.
- Put `"extract_js":"extract(\"<target>\")"` or `"extract_js":"extract([...paths])"` on every waterfall step so `{{<waterfall_name>}}` resolves to the matched scalar.
- For complex JS logic, prefer file-backed code loaded into `payload.code` over giant one-line inline JS.
- Prefer targeted reruns with `--with-force <alias>` over global `--force` when only specific columns need recompute.

### Tool shape validation (required before JS extractors)

1. `deepline tools get <tool_id>` for each provider in your plan.
2. Run a real pilot with `--rows 0:1`.
3. Correct interpolation if mismatch before any paid batch.

### `run_javascript` payload safety (critical)

Use this whenever you add JS extractor columns:

- **Always use explicit `return` statements.** Expression-style (implicit return) does NOT work — cells will silently write empty. Every JS block must end with `return <value>;`.
- Always use file-backed JS:
  - `--with '{"alias":"post_signals","tool":"run_javascript","payload":{"code":"@$WORKDIR/post_signals.js"}}'`
- If you see `Invalid JSON payload ... (Invalid \\escape ...)`, treat it as quoting/escaping failure, not provider failure:
  1. Move JS into a file.
  2. Re-run with a JSON `--with` spec that sets `payload.code` from that file.
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
| `forager_person_reverse_lookup` | `email` | `phone_numbers`, `person.phone_numbers`, `work_emails`, `personal_emails`, `linkedin_info.public_identifier` |
| `deepline_native_enrich_phone` | `email` | `data.phone`, `person.phone`, `results[0].phone` |

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
