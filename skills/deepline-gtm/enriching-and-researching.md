# Enriching and Researching (JTBD Draft)

Use this doc for row-level enrichment, research, waterfalls, validation, coalescing, and custom per-row transforms.

This doc does **not** cover list building, source discovery, or TAM/provider scouting before you have rows. If you do not yet have a seed list, source URL, or known entities, stop and use `finding-companies-and-contacts.md`.

## Core rule

Interim local SDK mode: row orchestration commands are bugged/unavailable for agent-run batch work. Do not use `deepline enrich` or batch `deepline plays run` as the CSV execution path.

Call provider tools or scalar prebuilt plays from a local Node/TypeScript script using the Deepline SDK. Use manual provider chains only when:

- you need to customize provider order or extractor behavior
- you are testing a niche provider path
- no single provider tool covers the field
- the prebuilt play is not directly runnable for the shape you need

For CSV work, write or use a project-local script that loops rows, calls `client.executeTool(...)` or a scalar prebuilt play per row, writes outputs incrementally, and persists per-row status.

## Local SDK Surface

Use SDK calls until orchestration commands are healthy again:

- `new DeeplineClient().searchTools(...)` / `.getTool(toolId)` to discover contracts.
- `new DeeplineClient().executeTool(toolId, input)` for execution.
- `const ctx = await Deepline.connect(); await ctx.tools.execute(toolId, input)` is the higher-level equivalent.
- `const output = await ctx.play('<described-play-name>').runSync(input)` is fine for scalar prebuilt plays after `plays search/describe` confirms the name and input contract.
- The SDK resolves auth from `DEEPLINE_API_KEY`, `DEEPLINE_HOST_URL`, `.env.deepline`, or saved CLI auth. Do not source `.env.local`.

Minimal one-row pilot:

```ts
import { DeeplineClient, RateLimitError } from 'deepline';

const client = new DeeplineClient();
const result = await client.executeTool('<tool-id>', { field: 'value' });
console.log(JSON.stringify(result.toolResponse?.raw ?? result, null, 2));
```

Direct `client.executeTool(...)` calls are caller-owned for rate limits: pass an explicit retry option when appropriate and still wrap row execution yourself. Catch `RateLimitError`, wait `error.retryAfterMs`, persist the retry state, and resume from saved row state instead of restarting the file.

## Local SDK command/script shape

Write the local command or script that fits the job. Do not look for a bundled runner. The agent is expected to inspect the input CSV, inspect the SDK/tool contract, then author the smallest useful Node/TypeScript command or project-local script that calls `client.executeTool(...)` inline.

```bash
WORKDIR="deepline/data/<descriptive-slug>" && mkdir -p "$WORKDIR"
cd "$WORKDIR" && npm init -y && npm install deepline
node ./run.mjs
```

Use the package manager already present in the user's project when possible. The only hard requirement is that the script can resolve `import { DeeplineClient } from 'deepline'`: install `deepline` locally in the work directory, use the project's existing dependency, or point the command at the repo-local SDK package when working inside the Deepline repo. Do not assume the globally installed `deepline` CLI makes the SDK importable.

For CSVs and multi-step waterfalls, write the script yourself: read rows, call one or more executable `executeTool(...)` steps or scalar prebuilt plays per row, write JSONL/CSV output incrementally, and persist row status for resume. Keep concurrency `1` or low while providers 429. Honor `RateLimitError.retryAfterMs` and make retry/backoff explicit in the local loop.

Billing recovery: if `deepline billing balance` or any paid Deepline command
reports zero credits, `no_billing`, or an insufficient-credits failure, stop
paid work and ask the user whether they want to add Deepline credits. If the
response includes a `recovery` object, quote `recovery.top_up_command` and
`recovery.checkout_command` exactly in your answer, including `--json` and
`--no-open`. Do not shorten them, and do not run either command until the user
explicitly approves.

## What to use when

Names below are starting hints. Confirm the live name and schema with play/tool discovery before calling. Scalar prebuilt calls are fine for concrete one-offs; CSV/batch work should loop over rows locally with durable state.

| You have / need                                      | Start with                                        | Decompose to provider tools when...                            |
| ---------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------- |
| first + last + domain -> work email                  | `name-and-domain-to-email-waterfall` scalar play  | You need custom provider order, validation, or fallback gating   |
| Sales Nav URL or company name only -> email          | resolve domain with `exa_search`, then email play | Domain resolution is ambiguous or you need evidence columns      |
| standard `/in/` LinkedIn URL -> work email           | `person-linkedin-to-email` scalar play            | You need custom matching, domain gating, or provider inspection  |
| personal email -> LinkedIn/company/title             | `personal-email-to-linkedin` scalar play          | You need provider-specific evidence or custom fallback behavior  |
| company/domain -> people by role/seniority           | `company-to-contact` scalar play                  | You need exact title logic, unusual personas, or provider choice |
| verified person identity -> mobile phone             | `person-to-phone` scalar play                     | You need custom validation, line-type gating, or cheaper probes  |
| LinkedIn post -> reactors/commenters                 | `linkedin-post-to-engagers` scalar play           | You need comments-only, full profiles, or custom actor settings  |
| name + position/headline -> ICP tier                 | `engagers-to-icp-qualification` scalar play       | You need web/company research before scoring                    |
| direct firmographics, search, transforms, validation | executable provider/local tools                   | No prebuilt covers the field cleanly                            |
| research/synthesis/personalization inputs            | `deeplineagent` plus local transforms             | A mechanical provider field already answers the question         |

## Notes

- Interim local SDK mode supersedes older batch orchestration defaults for agent-run row work. Scalar prebuilt play calls are still fine when they have concrete input and a confirmed contract.
- **Personal vs work emails:** When the user asks for personal emails, they mean Gmail/Hotmail/Yahoo, not work emails. Use Fullenrich (`contact.personal_emails`) or BetterContact; do not substitute Hunter, LeadMagic, or other work-email providers.
- Direct provider tools are preferred for mechanical fields when no play exists.
- When multiple providers recover the same mechanical field, prefer the route that bills on returned results or successful hits. Use request-priced, page-priced, or broad AI passes only after a tiny pilot proves they return usable rows.
- `run_javascript` is for deterministic transforms, normalization, coalescing, templating, and cheap row-level glue logic.
- `deeplineagent` is the default AI path for research, synthesis, custom signals, and classification when JS is not enough.
- Domain lookup / homepage recovery is mechanical. Use `exa_search` with rich context or `serper_google_search`, not `deeplineagent`.
- For local SMB or restaurant contact emails, do not start with name + domain work-email waterfalls unless you have a named person. Prefer the small-business prospecting recipe first: Maps identity, website/contact extraction, then optional Facebook/Instagram profile contact fields when the row or pilot suggests social profiles are the best public source. ScrapeCreators profile tools are candidate routes, not required steps.
- Persona lookup means "find candidate contacts at a company for a target role or seniority." Use the dedicated play, not generic research.
- Validate after recovery or coalescing, not during each waterfall step.
- For contact-to-email work, route by your strongest identifiers: name + domain -> manual SDK work-email waterfall; name + company only (no domain) OR Sales Navigator contacts -> resolve domain first, then the manual SDK work-email waterfall; standard `/in/` LinkedIn URL + name -> inspect the executable LinkedIn-to-email provider chain before calling SDK tools.
- **Sales Navigator exports**: `linkedin_url` values in `/sales/lead/` format are rejected by every provider (dropleads, crustdata, deepline_native, PDL). Do not pass them directly to email tools. Resolve the company domain first, then run the manual SDK work-email waterfall.
- Contacts from a people search (e.g. dropleads_search_people) with **standard `/in/`** URLs -> inspect the current scalar LinkedIn-to-email prebuilt play and executable provider tools before calling SDK tools. Use the scalar prebuilt when it fits the exact row input; decompose to provider tools when you need custom ordering or extractor logic.
- Validation interpretation: `valid` is deliverable, `catch_all` is usable but riskier, `invalid` should be dropped, and `unknown` is unresolved.
- Phone recovery usually comes later in the pipeline than email or LinkedIn recovery.
- Prefer inline code for short `run_javascript` transforms. Only move code into files when the logic is long, reused, or too awkward to keep inline.
- Never start a second enrich run against the same `--output` file while another is running. The `.deepline.lock` directory is a safety mechanism, not a bug. Wait for the first run, or write to a different output path.
- In Claude Desktop on Windows, the working directory may look like `C:\Users\...` while the tool executor is still Bash/Git Bash. Use Bash commands such as `rm`, not PowerShell commands such as `Remove-Item`, unless the session context explicitly says the active shell is PowerShell.

## Plays

### Interim local-SDK translation

Some older examples were authored for row orchestration commands. That path is bugged for current agent-run batch work. Translate payloads into SDK calls only after resolving a real executable tool id with `searchTools(...)` / `getTool(...)` or a real scalar prebuilt with `plays search/describe`.

Use the right surface:

- Direct provider/local tool: `await client.executeTool(toolId, input)` or `await ctx.tools.execute(toolId, input)`.
- Scalar prebuilt play with concrete input: `await ctx.play('<described-play-name>').runSync(input)` or a scalar CLI play command after describe confirms the contract.
- CSV/batch work: your own local loop over rows, calling the scalar tool/play per row with persisted status and retry/backoff.

If `executeTool(...)` rejects a name as `PLAY_ALIAS_USED_AS_TOOL`, that does not mean the prebuilt is unusable. Use the play surface for a scalar call or decompose it into provider tools for a custom row loop.

```ts
const result = await client.executeTool('<tool-id>', {
  field: row.field,
});
```

For CSV scale, write a local row loop that fills the JSON with each row's values, calls the SDK, writes output incrementally, and records row status for resume.

### Name + domain -> work email

Current/legacy prebuilt hint: `name-and-domain-to-email-waterfall`. Confirm the live name and input contract with play discovery before use. For a scalar one-off, run the prebuilt through the play surface. For CSV scale or custom provider ordering, use the manual SDK waterfall below.

**Required payload:** `first_name`, `last_name`, `domain`. `company_name` is not part of the payload.

**Routing by what you have:**

| You have                                                  | Action                                            |
| --------------------------------------------------------- | ------------------------------------------------- |
| name + domain                                             | Run the manual SDK waterfall below                |
| name + company_name (no domain) or SN `/sales/lead/` URLs | Resolve domain first (below), then run the waterfall |
| standard `/in/` LinkedIn URL + name                       | Skip this pattern — use `LinkedIn URL -> work email` |

**Manual SDK waterfall.** Call executable provider tools in order and stop on the first strong hit: `dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> crustdata_persondb_search -> peopledatalabs_enrich_contact`. Only treat `valid` hits as wins; `catch_all` is usable for outreach but not an automatic win.

**Example:** call `client.executeTool('dropleads_email_finder', { first_name, last_name, company_domain: domain })`; if it misses or returns only weak evidence, call the next executable provider tool from the waterfall with its inspected input schema.

**Domain-first resolution** — when you only have `company_name` or a SN `/sales/lead/` URL, resolve domain, then run the play (3 passes):

Use `client.executeTool('exa_search', { query, numResults: 1 })`, extract the domain locally in JS, then run the manual work-email waterfall.

Exa `extract_js` doesn't work inline here, so `run_javascript` extracts the domain from the saved cell — unwrap `cell.result` first (the cell shape is `{ result, matched_result? }`).

### LinkedIn URL -> work email

Current/legacy prebuilt hint: `person-linkedin-to-email`. Confirm the live name and input contract with play discovery. For a scalar one-off with a standard `/in/` URL, the prebuilt is fine; for CSV scale or custom matching, inspect executable provider tools and wrap the calls in your local loop.

**Required payload:** `linkedin_url`.

Use when contacts have a **standard `/in/`** LinkedIn URL (e.g. from `dropleads_search_people`). The play works off the LinkedIn URL directly.

**Do NOT use for Sales Navigator `/sales/lead/` URLs** — providers reject them. Resolve the company domain first, then use the name+domain play above.

**Example:**

_Legacy row-command example removed. Use the local-SDK translation above._

### Email -> person/company context

Executable tool: `deepline_native_enrich_contact`

Why this play:

- Email is a strong identifier; use it directly.
- This is hydration, not research.

Example:

_Legacy row-command example removed. Use the local-SDK translation above._

### Personal email -> LinkedIn profile

Current/legacy prebuilt hint: `personal-email-to-linkedin`. Required payload: `personal_email` only (name/company unknown, unlike the work-email flows). Confirm the live name and input contract with play discovery; use it directly for scalar one-offs and wrap it per row for CSV scale.

Use it when a signup list has only personal emails and you want to know who they are. Returns `linkedin_url`, `name`, `company`, `title`; a profile is often more recoverable and useful than a work email here. The play normalizes Gmail first, then waterfalls `deepline_native` -> `forager` -> `findymail` -> `peopledatalabs`, charging per hit.

The same play runs two ways:

_Legacy row-command example removed. Use the local-SDK translation above._

Bare personal email coverage is ~25-40%, so over-provision. If a row returns a company but no work email, chain the manual name+domain work-email waterfall above.

### Contact identity -> phone

Current/legacy prebuilt hint: `person-to-phone`. Confirm the live name and input contract with play discovery. Use the scalar prebuilt when the native ordering fits; inspect executable phone provider tools first when you need custom ordering, validation, or gating.

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

_Legacy row-command example removed. Use the local-SDK translation above._

### Company -> persona lookup

Current/legacy prebuilt hint: `company-to-contact`. Confirm the live name and input contract with play discovery. Use the scalar prebuilt when the native company-to-persona behavior fits; inspect executable company/persona provider tools first when you need custom role logic or provider ordering.

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
- Exact-title provider search should not be the only source for founder/exec startup cases.
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

_Legacy row-command example removed. Use the local-SDK translation above._

Apify example:

```ts
await client.executeTool('apify_run_actor_sync', {
  actorId: 'apimaestro/linkedin-company-employees-scraper-no-cookies',
  input: {
    identifier: 'https://www.linkedin.com/company/openai/',
    max_employees: 100,
  },
  timeoutMs: 180000,
});
```

### LinkedIn post URL -> list of engagers

Executable tool: `linkedin_post_to_engagers`

Scrapes reactors/commenters from a LinkedIn post. No actor discovery or pagination needed. Call it with `client.executeTool(...)`; for batches, loop over rows in a script.
Do NOT use if you need comments only (use `unseenuser/linkedin-post-comment-reaction-extractor-no-cookies`) or full profiles (add a separate scraping step after).

```ts
await client.executeTool('linkedin_post_to_engagers', {
  post_url: 'https://www.linkedin.com/posts/...',
  max_items: 1000,
});
```

### List of people with name + position -> ICP qualification

Executable tool: `engagers_to_icp_qualification`

Classifies a person against an ICP using name + position/headline. Returns `{icp_tier, icp_reason}`. Do NOT use if qualification needs company size, funding, or web research — use a custom `deeplineagent` prompt instead.

_Legacy row-command example removed. Use the local-SDK translation above._

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

_Legacy row-command example removed. Use the local-SDK translation above._

### Manual email waterfall

Problem category: custom provider ordering or custom extraction behavior.  
Input profile: varies by target field.  
Output target: same as the native play, but with explicit provider control.

Default surface: a local SDK loop that calls direct executable provider tools with `client.executeTool(...)`.

Why this play:

- Use only when no native play fits or when you need to deliberately customize provider order.
- Keeps mechanical enrichment mechanical.
- This is still preferable to starting with `deeplineagent` for deterministic fields.

Key waterfall rules:

- Always pilot one row first, then scale after the shape looks right.
- Stop after the pilot if the first rows show low usable coverage, wrong-person/company matches, missing getters, or high cost per recovered value. Change provider order or gates before full fanout.
- Every waterfall step needs local extraction logic after `executeTool(...)`. Before writing it: inspect the tool contract with `client.getTool(toolId)` or `deepline tools describe <tool>` and prefer the tool's documented extractors/list accessors. For raw fallbacks, SDK output lives at `toolExecutionResult.toolResponse.raw`; only drill into provider-specific nesting when the tool's own payload truly has a nested field.
- Model waterfall control flow in ordinary code: call provider A, extract a usable value, return early on success, otherwise call provider B, then provider C. Persist each attempted provider and final value per row so retries can resume without duplicating successful calls.
- Do not run email waterfalls without minimum match data: name + company, name + domain, or a strong LinkedIn-seeded identity.
- If you need different validation behavior, remember the native cost-aware play only accepts pattern hits when the validator says `valid`.
- Gating: implement row-level conditions in local code before calling a paid tool. Skip rows with insufficient inputs and record the skip reason.

Example:

_Legacy row-command example removed. Use the local-SDK translation above._

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

### Legacy row-command shape reference

Use this only to translate old examples to direct scripts. Do not execute legacy row commands during interim direct mode.

- `run_javascript` old payloads put JS in `payload.code`; in local scripts, just write JS directly.
- Old `extract_js` saw `{ result: <raw tool output> }`; SDK scripts should inspect `toolResponse.raw` and extract in ordinary code.
- Old persisted cells may contain `result` plus `matched_result`; prefer `matched_result` when present, then fall back to the raw provider payload.

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

### Structured output and direct-call realities

- SDK `client.executeTool(...)` returns an execution envelope, not just the bare provider object. For most tools, read provider output from `toolResponse.raw`. `deeplineagent` currently returns its AI payload at top-level `result` on the prod SDK CLI, so normalize with `const raw = result.toolResponse?.raw ?? result.result ?? result`; structured JSON then lives at `raw.result.object` or `raw.extracted_json`, and plain text lives at `raw.result.text` or `raw.output`.
- Direct tool/play paths have their own JSON shape; inspect actual output before writing flattening JavaScript.
- If you need deterministic field-level reuse, add a local JS/Python flattening step that emits a scalar column, then pass that scalar into later direct calls.

### Example: adapt a saved prompt from prompts.json

Start by printing the prompt text:

```bash
jq -r '."5 interesting facts about a candidate"' .skills/deepline-gtm/prompts.json
```

Then adapt it into a direct `deeplineagent` SDK call for research or custom-signal work.

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
