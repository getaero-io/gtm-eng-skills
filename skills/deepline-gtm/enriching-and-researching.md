# Enriching and Researching (JTBD Draft)

Use this doc for row-level enrichment, research, waterfalls, validation, coalescing, and custom per-row transforms.

This doc does **not** cover list building, source discovery, or TAM/provider scouting before you have rows. If you do not yet have a seed list, source URL, or known entities, stop and use `finding-companies-and-contacts.md`.

## Core rule

If a play exists, use it first. Use manual provider chains only when:

- no play exists
- you need to customize provider order or extractor behavior
- you are testing a niche provider path

Run `deepline enrich` in the foreground so you don't waste tokens while it completes.

## Scenario table

| Scenario                                                 | Use when                                                                                                   | Default play/tool                                         | Why                                                                                                                      |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Name + domain -> work email                              | You have name + domain (or can resolve domain from company_name / Sales Nav URL first)                     | `Name + domain -> work email`                             | Canonical deterministic path. Handles both direct and domain-first-then-waterfall cases.                                 |
| LinkedIn URL -> work email                               | Standard `/in/` LinkedIn URL + name. `domain` optional; include if known for extra coverage.               | `LinkedIn URL -> work email`                              | Works with or without domain. Do NOT use for SN `/sales/lead/` URLs — resolve domain first and use the name+domain play. |
| Email -> person/company context                          | You have an inbound or work email and need person + company details                                        | `Email -> person/company context`                         | Good for hydrating context from a single strong identifier.                                                              |
| Personal email -> LinkedIn profile                       | Bare personal email (Gmail/GitHub signup); you need LinkedIn + name + company, not a work email | `Personal email -> LinkedIn profile`                      | Reverse identity resolution; best for personal-email-only lists. |
| Company -> persona lookup                                | You have an account and need candidate contacts by role or seniority                                       | `Company -> persona lookup`                               | Canonical play for company-to-persona lookup                                                                             |
| Company name only -> resolve domain first                | You need to recover homepage/domain before downstream enrichment                                           | `Company name only -> resolve domain first`               | Domain lookup is mechanical and should not start with `deeplineagent`                                                    |
| Validate a recovered email                               | An email lookup has already run                                                                            | `Notes`                                                   | Validation belongs after recovery or coalescing, not before                                                              |
| Manual email waterfall                                   | You need custom provider order or play customization                                                       | `Manual email waterfall`                                  | Lets you control ordering and spend                                                                                      |
| Find a LinkedIn URL for a known person                   | You have name, domain, and role context                                                                    | `Notes`                                                   | Cheap deterministic lookup when the query is specific                                                                    |
| Pull rich LinkedIn or work-history data                  | The URL is already known and you need structured profile data                                              | `Notes`                                                   | Structured output beats ad hoc web synthesis                                                                             |
| Find a mobile phone number                               | A verified person identity already exists                                                                  | `Notes`                                                   | Best later in the pipeline after identity is strong                                                                      |
| Mechanical company enrichment                            | You need direct structured account data                                                                    | `Notes`                                                   | Cheaper and cleaner, often more accurate than `deeplineagent` for firmographics                                          |
| Coalesce competing provider outputs                      | Multiple columns target the same field                                                                     | `Notes`                                                   | Deterministic canonicalization after parallel providers                                                                  |
| Per-row factual account research                         | You need custom research or synthesis that provider fields do not cover                                    | `Custom enrichment with run_javascript and deeplineagent` | Use `deeplineagent` for AI work and `run_javascript` for deterministic transforms                                        |
| Research pass before writing                             | You need company or person research to support later copy                                                  | `Custom enrichment with run_javascript and deeplineagent` | Research belongs here and should feed a later writing step                                                               |
| Generate copy after research                             | The research column already exists and you now need messaging, first lines, scoring copy, or sequence text | `writing-outreach.md`                                     | Copywriting should route to the outreach doc, usually with `deeplineagent` once the research column exists               |
| LinkedIn post URL -> list of engagers                    | You have a LinkedIn post URL and want all reactors/commenters                                              | `linkedin_post_to_engagers`                               | Scrape all reactors/commenters from a LinkedIn post. Returns structured engager list.                                    |
| List of people with name + position -> ICP qualification | You have person rows with name and headline and need tier classification                                   | `engagers_to_icp_qualification`                           | Classify leads against ICP using headline/position via deeplineagent                                                     |
| **Personal email discovery**                             | User explicitly asks for personal emails (Gmail, Hotmail, etc.) - NOT work emails                          | `Personal email discovery`                                | Use Fullenrich or BetterContact. **NEVER use Apollo** - it returns work emails even with `reveal_personal_emails:true`.  |

## Notes

- Plays are the default surface for common enrichment jobs.
- **Personal vs work emails:** When the user asks for personal emails, they mean Gmail/Hotmail/Yahoo, not work emails. Use Fullenrich (`contact.personal_emails`) or BetterContact; do not substitute Apollo, Hunter, LeadMagic, or other work-email providers.
- Direct provider tools are preferred for mechanical fields when no play exists.
- When multiple providers recover the same mechanical field, prefer the route that bills on returned results or successful hits. Use request-priced, page-priced, or broad AI passes only after a tiny pilot proves they return usable rows.
- `run_javascript` is for deterministic transforms, normalization, coalescing, templating, and cheap row-level glue logic.
- `deeplineagent` is the default AI path for research, synthesis, custom signals, and classification when JS is not enough.
- Domain lookup / homepage recovery is mechanical. Use `exa_search` with rich context or `serper_google_search`, not `deeplineagent`.
- Persona lookup means "find candidate contacts at a company for a target role or seniority." Use the dedicated play, not generic research.
- Validate after recovery or coalescing, not during each waterfall step.
- For contact-to-email work, route by your strongest identifiers: name + domain -> `Name + domain -> work email` (or `First + last + domain -> work email`); name + company only (no domain) OR Sales Navigator contacts -> resolve domain first, then `name_and_domain_to_email_waterfall`; standard `/in/` LinkedIn URL + name -> `LinkedIn URL -> work email` (domain optional).
- **Sales Navigator exports**: `linkedin_url` values in `/sales/lead/` format are rejected by every provider (dropleads, crustdata, deepline_native, PDL). Do not pass them directly to any email waterfall. Resolve the company domain first, then use `name_and_domain_to_email_waterfall`.
- Contacts from a people search (e.g. dropleads_search_people) with **standard `/in/`** URLs -> `person_linkedin_to_email_waterfall` (`domain` optional). Does NOT apply to SN `/sales/lead/` URLs.
- Validation interpretation: `valid` is deliverable, `catch_all` is usable but riskier, `invalid` should be dropped, and `unknown` is unresolved.
- Phone recovery usually comes later in the pipeline than email or LinkedIn recovery.
- Prefer inline code for short `run_javascript` transforms. Only move code into files when the logic is long, reused, or too awkward to keep inline.
- Never start a second enrich run against the same `--output` file while another is running. The `.deepline.lock` directory is a safety mechanism, not a bug. Wait for the first run, or write to a different output path.
- In Claude Desktop on Windows, the working directory may look like `C:\Users\...` while the tool executor is still Bash/Git Bash. Use Bash commands such as `rm`, not PowerShell commands such as `Remove-Item`, unless the session context explicitly says the active shell is PowerShell.

## Plays

### Name + domain -> work email

Play tool: `name_and_domain_to_email_waterfall`

**Required payload:** `first_name`, `last_name`, `domain`. `company_name` is not part of the payload.

**Routing by what you have:**

| You have                                                  | Action                                            |
| --------------------------------------------------------- | ------------------------------------------------- |
| name + domain                                             | Use the play directly                             |
| name + company_name (no domain) or SN `/sales/lead/` URLs | Resolve domain first (below), then use the play   |
| standard `/in/` LinkedIn URL + name                       | Skip this play — use `LinkedIn URL -> work email` |

**Play internals.** Runs common validated patterns first; only `valid` hits count. Falls through to `dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> crustdata_persondb_search -> peopledatalabs_enrich_contact`. `catch_all` is usable for outreach but not an automatic win inside the play.

**Example:**

```bash
deepline enrich --input leads.csv --output leads_with_emails.csv --rows 0:1 \
  --with '{"alias":"email","tool":"name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

**Domain-first resolution** — when you only have `company_name` or a SN `/sales/lead/` URL, resolve domain, then run the play (3 passes):

```bash
deepline enrich --input contacts.csv --output out.csv \
  --with '{"alias":"exa_raw","tool":"exa_search","payload":{"query":"{{company_name}} official website","numResults":1}}'
deepline enrich --input out.csv --in-place \
  --with '{"alias":"domain","tool":"run_javascript","payload":{"code":"const cell=row.exa_raw;const raw=(cell&&typeof cell===\"object\"&&\"result\" in cell)?cell.result:cell;const results=Array.isArray(raw?.results)?raw.results:[];const url=(results[0]&&results[0].url)||\"\";const m=url.match(/^https?:\\/\\/(www\\.)?([^\\/]+)/);return row.company_domain||(m?m[2]:null)||null;"}}'
deepline enrich --input out.csv --in-place \
  --with '{"alias":"email","tool":"name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

Exa `extract_js` doesn't work inline here, so `run_javascript` extracts the domain from the saved cell — unwrap `cell.result` first (the cell shape is `{ result, matched_result? }`).

### LinkedIn URL -> work email

Play tool: `person_linkedin_to_email_waterfall`

**Required payload:** `linkedin_url`, `first_name`, `last_name`.
**Optional:** `domain` — include when available to unlock extra deterministic finder steps before LinkedIn-native fallbacks.

Use when contacts have a **standard `/in/`** LinkedIn URL (e.g. from `dropleads_search_people`). Domain is optional — the play works off the LinkedIn URL directly.

**Do NOT use for Sales Navigator `/sales/lead/` URLs** — providers reject them. Resolve the company domain first, then use the name+domain play above.

**Example:**

```bash
deepline enrich --input contacts.csv --output contacts_with_emails.csv --rows 0:1 \
  --with '{"alias":"email","tool":"person_linkedin_to_email_waterfall","payload":{"linkedin_url":"{{linkedin_url}}","first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

### Email -> person/company context

Play tool: `deepline_native_enrich_contact`

Why this play:

- Email is a strong identifier; use it directly.
- This is hydration, not research.

Example:

```bash
deepline enrich --input inbound.csv --output inbound_enriched.csv --rows 0:1 \
  --with '{"alias":"person_context","tool":"deepline_native_enrich_contact","payload":{"email":"{{email}}"}}'
```

### Personal email -> LinkedIn profile

Play tool: `personal_email_to_linkedin_waterfall`. Required payload: `personal_email` only (name/company unknown, unlike the work-email plays).

Use it when a signup list has only personal emails and you want to know who they are. Returns `linkedin_url`, `name`, `company`, `title`; a profile is often more recoverable and useful than a work email here. The play normalizes Gmail first, then waterfalls `deepline_native` -> `forager` -> `findymail` -> `peopledatalabs`, charging per hit.

The same play runs two ways:

```bash
# v1 enrich (--with JSON, per CSV row)
deepline enrich --input signups.csv --output out.csv \
  --with '{"alias":"profile","tool":"personal_email_to_linkedin_waterfall","payload":{"personal_email":"{{personal_email}}"}}'

# v2 play (same keys, real values instead of {{...}})
deepline plays run personal-email-to-linkedin-waterfall --input '{"personal_email":"ada@gmail.com"}'
```

Porting v1 -> v2: v1 `tool` (underscores) becomes the v2 play name (hyphens); v1 `payload` becomes v2 `--input`; drop `{{column}}` placeholders. Bare personal email coverage is ~25-40%, so over-provision. If a row returns a company but no work email, chain `name_and_domain_to_email_waterfall`.

### Contact identity -> phone

Play tool: `contact_to_phone_waterfall`

Why this play:

- Use it when you already know the person identity and want the highest-signal phone lookup order.
- Cost-optimized: starts with the cheapest providers and escalates to expensive ones only as fallbacks.
- All providers charge only on successful hit (post_deduct), so total cost scales with coverage, not attempts.
- Follow up with `trestle_phone_validation` to verify line type, carrier, and activity score before outbound.

Play details:

- Required inputs are `first_name`, `last_name`, and `domain`.
- `email` and `linkedin_url` are optional hints that unlock additional provider paths.
- The play handles the phone provider order internally. Treat the play as the source of truth for exact sequencing.
- LeadMagic runs in two gated forms inside the play: LinkedIn-based when `linkedin_url` exists, and email-based when `email` exists.
- Use async aggregators (BetterContact, FullEnrich) as manual enrichment steps outside the play when the native waterfall misses.

Example:

```bash
deepline enrich --input contacts.csv --output contacts_with_phones.csv --rows 0:1 \
  --with '{"alias":"phone_from_contact","tool":"contact_to_phone_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}","email":"{{email}}","linkedin_url":"{{linkedin_url}}"}}'
```

### Company -> persona lookup

Play tool: `company_to_contact_by_role_waterfall`

Why this play:

- This is the canonical company-to-persona play when you have a company domain.
- Use it for both role-targeted and seniority-targeted contact discovery.
- The right default for prompts like "find GTM engineers at these companies".
- Prefer exact title tokens in `roles` when the user intent is specific, for example `CEO`, `Founder`, `CTO`, `CMO`, `VP Marketing`, `Head of Security`, `Director of Engineering`, `RevOps`.
- Use broader functional roles only when the user intent is genuinely broad, for example `marketing`, `security`, `finance`, `product`, `engineering`, `sales`, `growth`. Broad roles are useful, but they are noisier and often return adjacent titles.
- A good default is 1-3 exact titles, or a broad function plus a strong level hint if exact titles are not known.
- `seniority` is a first-class input, but it is only a level hint. Use portable values like `C-Level`, `Founder`, `VP`, `Head`, `Director`, `Manager`, `Senior`, `Entry`, `Intern`. Do not send raw provider enums like `c_level` unless you are bypassing the play and calling a provider directly.
- Do not assume the play will invent hidden row-level provider fields for you. For interpolated CSV runs, `roles` and `seniority` pass through exactly as provided.
- Clean contract: pass a company domain. If you only have a LinkedIn company URL, resolve the domain first before using this play.

Provider behavior:

- `dropleads` is strongest with exact title tokens.
- `deepline_native` translates portable roles into provider-safe title filters, especially for leadership intent like `CEO`, `Founder`, `CTO`, `VP Marketing`, `Head of Security`, or `Director of Engineering`.
- `apollo` helps with exact title search, but should not be the only source for founder/exec startup cases.
- `icypeas` is a strong exact-profile fallback, especially for founders and startup operators.
- `prospeo` and `crustdata` are structured fallbacks, not reasons to jump to `deeplineagent`.
- For a very specific persona with only a broad function, refine the role phrasing before adding providers.

Persona matching:

- Treat requested `roles` and `seniority` as semantic intent, not raw substring rules. Provider search can return adjacent titles that contain the same words but mean something different.
- Validate that the returned title actually matches the requested persona before treating it as the decision maker. If the match is weak, return no result, broaden intentionally, or mark it low confidence instead of filling the row with a plausible-looking person.
- Common false positives: `Owner` can mean process/product owner, `Sales` can mean Salesforce, `Chief` can mean Chief of Staff, and `Security` can mean physical security.
- Prefer exact title families or explicit role phrases when intent is narrow. For example, use `Founder`, `Co-Founder`, `CEO`, `Chief Executive Officer`, or `Owner/Proprietor` for business-owner intent instead of relying on a loose `owner` token.
- Ambiguous terms need supporting evidence from company/domain fit, full title context, and the requested function. Do not let one overlapping word override a bad persona fit.

Operational rule:

- If you only have `company_name`, resolve the domain first, then run persona lookup.
- Do not use `deeplineagent` as the first pass for persona lookup.
- Use `deeplineagent` only as a fallback research pass when the play and direct providers miss.
- If provider results are weak or sparse, first re-check the available people/company search tools with category searches, then use Apify if you need a broader employee list.

Category searches:

- Use `people_search` when you need better title- and LinkedIn-oriented contact search options.
- Use `company_search` when you need stronger company identity resolution or company-level inputs before the people search.

Search examples:

```bash
deepline tools search --categories people_search --search_terms "title filters,linkedin"
deepline tools search --categories company_search --search_terms "structured filters,firmographics"
```

Example:

```bash
deepline enrich --input accounts.csv --output accounts_with_contacts.csv --rows 0:1 \
  --with '{"alias":"role_contacts","tool":"company_to_contact_by_role_waterfall","payload":{"company_name":"{{company_name}}","domain":"{{domain}}","roles":"{{roles}}","seniority":"{{seniority}}"}}'
```

Apify example:

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"apimaestro/linkedin-company-employees-scraper-no-cookies","input":{"identifier":"https://www.linkedin.com/company/openai/","max_employees":100},"timeoutMs":180000}'
```

### LinkedIn post URL -> list of engagers

Play tool: `linkedin_post_to_engagers`

Scrapes reactors/commenters from a LinkedIn post. No actor discovery or pagination needed. Can be called via `deepline tools execute` (single post) or `deepline enrich` (batch).
Do NOT use if you need comments only (use `unseenuser/linkedin-post-comment-reaction-extractor-no-cookies`) or full profiles (add a separate scraping step after).

```bash
deepline tools execute linkedin_post_to_engagers --payload '{"post_url":"https://www.linkedin.com/posts/...","max_items":1000}'
```

### List of people with name + position -> ICP qualification

Play tool: `engagers_to_icp_qualification`

Classifies a person against an ICP using name + position/headline. Returns `{icp_tier, icp_reason}`. Do NOT use if qualification needs company size, funding, or web research — use a custom `deeplineagent` prompt instead.

```bash
deepline enrich --input engagers.csv --output qualified.csv --rows 0:5 \
  --with '{"alias":"icp","tool":"engagers_to_icp_qualification","payload":{"first_name":"{{FIRST_NAME}}","last_name":"{{LAST_NAME}}","position":"{{POSITION}}","icp_description":"Tier 1: VP/Head of Engineering, CTO at B2B SaaS. Tier 2: Senior engineers. Tier 3: everyone else."}}'
```

### Company name only -> resolve domain first

Problem category: domain lookup / homepage recovery.  
Input profile: `company_name` plus any contextual hints you already have.  
Output target: canonical `domain` or homepage for downstream plays.

Default tools: `exa_search` or `serper_google_search`

Why this play:

- Domain lookup is mechanical.
- It should happen before persona lookup, email recovery, or company enrichment.
- `deeplineagent` is the wrong default here because this is a search-and-resolve task, not a synthesis task.

Routing rule:

1. Resolve domain/homepage with `exa_search` or `serper_google_search`.
2. Run the downstream play using the recovered domain.
3. Only use `deeplineagent` if provider/search outputs still do not cover the factual need and you need tool-backed reasoning to resolve the ambiguity.

Example:

```bash
deepline enrich --input accounts.csv --output accounts_with_domains.csv --rows 0:1 \
  --with '{"alias":"homepage_search","tool":"serper_google_search","payload":{"query":"\"{{company_name}}\" official site","num":5}}'
```

### Manual email waterfall

Problem category: custom provider ordering or custom extraction behavior.  
Input profile: varies by target field.  
Output target: same as the native play, but with explicit provider control.

Default surface: `--with-waterfall` plus direct providers

Why this play:

- Use only when no native play fits or when you need to deliberately customize provider order.
- Keeps mechanical enrichment mechanical.
- This is still preferable to starting with `deeplineagent` for deterministic fields.

Key waterfall rules:

- Always pilot first with `--rows 0:1`, then scale after the shape looks right.
- Stop after the pilot if the first rows show low usable coverage, wrong-person/company matches, missing getters, or high cost per recovered value. Change provider order or gates before full fanout.
- Every waterfall step needs its own `extract_js`. Before writing it: run `deepline tools describe <tool>` and prefer the usage guidance's extracted/list accessors. For raw fallbacks, V2 tool output lives at `toolExecutionResult.toolResponse.raw`; only drill into provider-specific nesting when the tool's own payload truly has a nested field. Use `@path/to/file.js` for multi-line or regex-heavy JS — inline JS in `--with` JSON breaks on escapes.
- Close each waterfall with `--end-waterfall` before starting another one.
- Do not run email waterfalls without minimum match data: name + company, name + domain, or a strong LinkedIn-seeded identity.
- If you need different validation behavior, remember the native cost-aware play only accepts pattern hits when the validator says `valid`.
- Gating: `--with` accepts exactly these keys: `alias`, `tool`, `payload`, `extract_js`. Gate conditional logic with a preceding `run_javascript` step whenever you need row-level conditions.

Example:

```bash
deepline enrich --input leads.csv --in-place --rows 0:1 \
  --with-waterfall "email" \
  --with '{"alias":"dropleads","tool":"dropleads_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company_name}}","company_domain":"{{domain}}"},"extract_js":"(output_data) => extract(\"dropleads_email_finder\", output_data, \"email\")"}' \
  --with '{"alias":"hunter","tool":"hunter_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"},"extract_js":"(output_data) => extract(\"hunter_email_finder\", output_data, \"email\")"}' \
  --with '{"alias":"leadmagic","tool":"leadmagic_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"},"extract_js":"(output_data) => extract(\"leadmagic_email_finder\", output_data, \"email\")"}' \
  --end-waterfall \
  --with '{"alias":"email_validation","tool":"leadmagic_email_validation","payload":{"email":"{{email}}"}}'
```

If `extract_js` returns raw objects instead of scalars, you can store the raw response and use `run_javascript` in a second pass to parse it. When debugging, remember the extractor input is wrapped as `{ result: ... }`, while persisted enrich cells usually contain both `result` and `matched_result`.

## Post-enrichment validation

After enrichment, validate data quality before moving to the next phase. Run read-only checks — never modify the enriched CSV during validation.

```bash
# Email domain vs company domain — catches previous-employer or wrong-contact emails
python3 ~/.claude/skills/deepline-gtm/scripts/validate-emails.py enriched.csv \
    --email-col email --domain-col domain
```

Flag mismatches; if >20% of rows mismatch, rerun contact finding with better company disambiguation.

```bash
# LinkedIn name validation — catches wrong-person matches from search-based lookup
python3 ~/.claude/skills/deepline-gtm/scripts/validate-linkedin-names.py enriched.csv \
    --source-first first_name --source-last last_name --profile-name-col profile_name
```

Null out LinkedIn URLs where names don't match.

```bash
# Current role extraction. Selects latest active work role and repairs artifacts.
python3 ~/.claude/skills/deepline-gtm/scripts/select-current-role.py enriched.csv \
    --scrape-col li_scrape --out-title current_title --out-company current_company
```

Do not trust top-level `jobTitle`; old roles or board/advisor entries can outrank the real current job.

```bash
# Final contact audit. Projects delivery gates into ACTION + flag_reason.
python3 ~/.claude/skills/deepline-gtm/scripts/contact-accuracy-audit.py final.csv \
    > final_audited.csv
```

**For any contact list you will actually send to**, read [references/contact-accuracy.md](references/contact-accuracy.md). It gives the full workflow: resolve the current work role, confirm identity, catch job-changers, validate email independently, preserve lineage, discover current role-holders company-first when accounts are known, audit the final file, and deliver one `ACTION` plus `flag_reason` per row.

## Custom enrichment with run_javascript and deeplineagent

Use this section for:

- open-ended factual research
- Claygent alternative
- custom signals
- enrichment that combines multiple sources
- personalization inputs
- prompt-driven enrichment patterns that are not covered by a direct provider field

Default rule:

- use direct providers or plays for mechanical fields
- use `run_javascript` when the job is deterministic row logic: formatting, normalization, coalescing, templating, parsing, or simple conditional transforms
- use `deeplineagent` when the row needs AI help for classification, extraction, scoring, structured generation, browsing, or multi-step synthesis
- split research and generation into separate passes when both are needed
- keep research here; route actual copywriting to `writing-outreach.md`

### Handmade step shape quick reference

Use this when you are hand-authoring `deepline enrich` steps instead of relying on a native play.

- `run_javascript` payload schema: `{"alias":"x","tool":"run_javascript","payload":{"code":"..."}}`
- Inside `run_javascript`, the current row is available as `row`. Read prior columns with `row["column_name"]` or `row.column_name`.
- `run_javascript` returns whatever your JS returns. For example:
  - scalar: `return "acme.com"`
  - object: `return { domain: "acme.com", source: "exa" }`
  - list: `return [{ email: "ada@example.com" }]`
- Provider step with extractor schema: `{"alias":"x","tool":"some_provider","payload":{...},"extract_js":"(output_data) => ..."}`
- `extract_js` input shape is always wrapped: `output_data = { result: <raw tool output> }`
- So inside `extract_js`, author against `output_data.result.*`, not the raw payload root.
- Use `extract("tool_id", output_data, "field")` and `extractList("tool_id", output_data, { keys: [...] })` when possible instead of manually drilling paths.
- Persisted enrich cell shape is different from extractor input.
- For provider-backed enrich columns, the saved cell usually contains the raw provider payload under `result`.
- `matched_result` is the normalized extracted value when Deepline materializes one, for example from result getters or waterfall extraction. It is not the runtime input to `extract_js`; it is a saved post-extraction convenience field.
- That means:
  - in `extract_js`, read `output_data.result`
  - in later `run_javascript` passes over saved CSV rows, read `row["some_column"].result`
  - if the saved cell also has `matched_result`, prefer it as the normalized value you already extracted
  - only drill into provider-specific nesting after reading the documented raw output root, and only when that provider's raw payload truly has that nested field

Minimal examples:

```bash
deepline enrich --input in.csv --output out.csv \
  --with '{"alias":"domain","tool":"run_javascript","payload":{"code":"return row.company_name ? row.company_name.toLowerCase().replace(/\\s+/g, \"\") + \".com\" : null;"}}'
```

```bash
deepline enrich --input in.csv --output out.csv \
  --with '{"alias":"email_raw","tool":"hunter_email_finder","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"},"extract_js":"(output_data) => extract(\"hunter_email_finder\", output_data, \"email\")"}'
```

```bash
deepline enrich --input out.csv --in-place \
  --with '{"alias":"email_domain","tool":"run_javascript","payload":{"code":"const cell=row.email_raw;const raw=(cell&&typeof cell===\"object\"&&\"result\" in cell)?cell.result:cell;const email=cell?.matched_result||raw?.email||raw?.data?.email||null;return email?email.split(\"@\")[1]:null;"}}'
```

### Tiny disambiguation

- Pick `run_javascript` for deterministic logic and cheap row transforms.
- Pick `deeplineagent` when JS is not enough and you need AI help, whether that's research or reasoning over the row.

### Prompt library

Before writing a fresh prompt, inspect [`prompts.json`](prompts.json):

```bash
jq -r 'keys[]' .skills/deepline-gtm/prompts.json
```

Keyword search:

```bash
grep -nE "funding|competitor|personalization|research|signal" .skills/deepline-gtm/prompts.json
```

Print a prompt by key:

```bash
jq -r '."5 interesting facts about a candidate"' .skills/deepline-gtm/prompts.json
```

### Recommended course of action

1. Check whether a play or direct provider already covers the field.
2. Search `prompts.json` for a close starting point.
3. Run a `deeplineagent` research pass first if the task requires web lookup or synthesis.
4. If the next step is copy, sequence writing, scoring copy, or messaging, switch to `writing-outreach.md` and use the research column there.
5. Keep outputs structured with `jsonSchema` when the column is meant to feed later steps.

### Example: inline custom research column with `deeplineagent`

```bash
deepline enrich --input accounts.csv --in-place --rows 0:1 \
  --with '{"alias":"account_research","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Research {{company_name}} ({{domain}}). Return JSON with what_they_build and who_they_sell_to. Keep it brief and use Deepline-managed tools only if needed.","jsonSchema":{"type":"object","properties":{"what_they_build":{"type":"string"},"who_they_sell_to":{"type":"string"}},"required":["what_they_build","who_they_sell_to"],"additionalProperties":false}}}'
```

### Example: research pass before writing

```bash
deepline enrich --input leads.csv --output leads_researched.csv --rows 0:1 \
  --with '{"alias":"company_research","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Research {{company_name}} ({{domain}}). Return JSON with key pain_points for a buyer considering data enrichment, scoring, or GTM workflow tooling. Keep it brief and use Deepline-managed tools only if needed.","jsonSchema":{"type":"object","properties":{"pain_points":{"type":"string"}},"required":["pain_points"],"additionalProperties":false}}}'
```

### Example: classify an existing research column with `deeplineagent`

```bash
deepline enrich --input leads_researched.csv --in-place --rows 0:1 \
  --with '{"alias":"account_tier","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Using only the provided context, classify {{company_name}} into one of: high_fit, medium_fit, low_fit. Context: {{company_research}}","jsonSchema":{"type":"object","properties":{"tier":{"type":"string","enum":["high_fit","medium_fit","low_fit"]},"reason":{"type":"string"}},"required":["tier","reason"],"additionalProperties":false}}}'
```

### Structured output and interpolation realities

- `deepline tools execute deeplineagent --json` returns the full execute envelope, not just the bare schema object. The structured object lives at `result.result.object` and plain text lives at `result.result.text`.
- In `deepline enrich`, `{{company_research}}` is the safest way to pass a prior `deeplineagent` column into another AI prompt.
- Do not assume `{{company_research.pain_points}}` works for `deeplineagent` structured-output columns in `deepline enrich`. Those cells currently carry an AI result wrapper, so downstream field access is not as clean as a plain flat JSON cell.
- If you need deterministic field-level reuse, add a `run_javascript` flatten pass that emits a new scalar column, then interpolate that scalar column in later steps.
- `row` exists only inside `run_javascript` code. Use `{{company_research}}` in payload templates, and use `row["company_research"]` inside `payload.code`.

### Example: flatten a structured research field before reuse

```bash
deepline enrich --input leads_researched.csv --in-place --rows 0:1 \
  --with '{"alias":"company_pain_points","tool":"run_javascript","payload":{"code":"const research = row[\"company_research\"]; const extracted = research?.output || research?.extracted_json || research?.result?.object || research; return extracted?.pain_points || null;"}}'
```

Then use the flattened scalar in later prompts:

```bash
deepline enrich --input leads_researched.csv --in-place --rows 0:1 \
  --with '{"alias":"account_tier","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Using only the provided context, classify {{company_name}} into one of: high_fit, medium_fit, low_fit. Pain points: {{company_pain_points}}","jsonSchema":{"type":"object","properties":{"tier":{"type":"string","enum":["high_fit","medium_fit","low_fit"]},"reason":{"type":"string"}},"required":["tier","reason"],"additionalProperties":false}}}'
```

### Example: adapt a saved prompt from prompts.json

Start by printing the prompt text:

```bash
jq -r '."5 interesting facts about a candidate"' .skills/deepline-gtm/prompts.json
```

Then adapt it into a row-level enrich call for research or custom-signal work:

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with '{"alias":"candidate_facts","tool":"deeplineagent","payload":{"model":"openai/gpt-5.4-mini","prompt":"Using the style of the saved prompt \"5 interesting facts about a candidate\", find five short, source-backed facts about {{full_name}} at {{company_name}}. Use Deepline-managed tools if needed. Return JSON {facts: string[]}.","jsonSchema":{"type":"object","properties":{"facts":{"type":"array","items":{"type":"string"}}},"required":["facts"],"additionalProperties":false}}}'
```

For actual email copy, personalized first lines, sequence writing, or scoring language, stop here and route to `writing-outreach.md` with the research columns you just created.

## Working directory (guardrail)

**NEVER write to `/tmp/` or any absolute temp directory** — files in `/tmp/` are wiped on reboot and users have lost paid enrichment outputs. Set up a project-local WORKDIR with a task-descriptive slug (e.g. `deepline/data/acme-email-waterfall`) as step zero. See SKILL.md §3.2 for the full rule.

```bash
WORKDIR="deepline/data/<descriptive-slug>" && mkdir -p "$WORKDIR" && echo "$WORKDIR"
```

## Exit back to discovery

If you realize the task is actually:

- "find the companies first"
- "find the candidate contacts first"
- "where does this data source live?"

Stop and route to `finding-companies-and-contacts.md`. This doc assumes you already have rows or known entities.
