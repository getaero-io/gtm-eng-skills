# Enriching and Researching (JTBD Draft)

Use this doc for row-level enrichment, research, waterfalls, validation, coalescing, and custom per-row transforms.

This doc does **not** cover list building, source discovery, or TAM/provider scouting before you have rows. If you do not yet have a seed list, source URL, or known entities, stop and use `finding-companies-and-contacts.md`.

## Core rule

If a play exists, use it first. Use manual provider chains only when:
- no play exists
- you need to customize provider order or extractor behavior
- you are testing a niche provider patha
Run deepline enrich in the foreground so you don't waste tokens while it completes. 

## Scenario table

| Scenario | Use when | Default play/tool | Why |
|---|---|---|---|
| Name + company -> work email | You have strong person + account identifiers | `Name + company -> work email` | Stable default for deterministic email recovery |
| LinkedIn URL + name, no domain | You have a LinkedIn URL and name but no company domain (e.g. from a people search result) | `LinkedIn URL only -> work email` | waterfall from specific providers who just need these params; no domain resolution step needed |
| LinkedIn URL -> work email | The LinkedIn profile and domain are both known | `LinkedIn URL -> work email` | Better use of a strong profile identifier when domain is available |
| Email -> person/company context | You have an inbound or work email and need person + company details | `Email -> person/company context` | Good for hydrating context from a single strong identifier |
| First + last + domain -> work email | Company name is missing but the domain is known | `First + last + domain -> work email` | Canonical cost-aware path for weaker but still structured identifiers |
| Company -> persona lookup | You have an account and need candidate contacts by role or seniority | `Company -> persona lookup` | Canonical play for company-to-persona lookup |
| Company name only -> resolve domain first | You need to recover homepage/domain before downstream enrichment | `Company name only -> resolve domain first` | Domain lookup is mechanical and should not start with `call_ai` |
| Validate a recovered email | An email lookup has already run | `Notes` | Validation belongs after recovery or coalescing, not before |
| Manual email waterfall | You need custom provider order or play customization | `Manual email waterfall` | Lets you control ordering and spend |
| Find a LinkedIn URL for a known person | You have name, domain, and role context | `Notes` | Cheap deterministic lookup when the query is specific |
| Pull rich LinkedIn or work-history data | The URL is already known and you need structured profile data | `Notes` | Structured output beats ad hoc web synthesis |
| Find a mobile phone number | A verified person identity already exists | `Notes` | Best later in the pipeline after identity is strong |
| Mechanical company enrichment | You need direct structured account data | `Notes` | Cheaper and cleaner, often more accurate than `call_ai` for firmographics |
| Coalesce competing provider outputs | Multiple columns target the same field | `Notes` | Deterministic canonicalization after parallel providers |
| Per-row factual account research | You need custom research or synthesis that provider fields do not cover | `Custom enrichment with call_ai` | Use only after plays/providers do not cover the job |
| Research pass before writing | You need company or person research to support later copy | `Custom enrichment with call_ai` | Research belongs here and should feed a later writing step |
| Generate copy after research | The research column already exists and you now need messaging, first lines, scoring copy, or sequence text | `writing-outreach.md` | Copywriting should route to the outreach doc, not stay here |

## Notes

- Plays are the default surface for common enrichment jobs.
- Direct provider tools are preferred for mechanical fields when no play exists.
- `call_ai` is for research, synthesis, and custom signals, not for simple deterministic fields a provider already returns.
- Domain lookup / homepage recovery is mechanical. Use `exa_search` with rich context or `google_search_google_search`, not `call_ai`.
- Persona lookup means "find candidate contacts at a company for a target role or seniority." Treat that as a dedicated play, not as generic research.
- Validate after recovery or coalescing, not during each waterfall step.
- For contact-to-email work, route by the strongest identifiers you already have: name + company + domain -> `Name + company -> work email`, LinkedIn URL + name (no domain) -> `LinkedIn URL only -> work email`, LinkedIn URL + name + domain -> `LinkedIn URL -> work email`, name + domain -> `First + last + domain -> work email`.
- If you got contacts from a people search (e.g. dropleads_search_people) and they have LinkedIn URLs but no domains, do NOT try to resolve domains first — use `person_linkedin_only_to_email_waterfall` directly.
- Validation interpretation: `valid` is deliverable, `catch_all` is usable but riskier, `invalid` should be dropped, and `unknown` is unresolved.
- Phone recovery usually comes later in the pipeline than email or LinkedIn recovery.
- Prefer inline code for short `run_javascript` transforms. Only move code into files when the logic is long, reused, or too awkward to keep inline.
- Never start a second enrich run against the same `--output` file while another enrich is still running. The `.deepline.lock` directory is a safety mechanism, not a bug. Wait for the first run to finish or write to a different output path.

## Plays

### Name + company -> work email

Problem category: contact email recovery from person + account identifiers.  
Input profile: `first_name`, `last_name`, `company_name`, `domain`.  
Output target: one best work email.

Play tool: `name_and_company_to_email_waterfall`

Why this play:
- Best default when you already know both the person and the account.
- Keeps the job deterministic and avoids unnecessary research tooling.
- Should be the first move before manual waterfalls or `call_ai`.

Play details:
- Required inputs are `first_name`, `last_name`, `company_name`, and `domain`.
- `linkedin_url` is optional, but it improves fallback depth because some later steps only run when LinkedIn is present.
- Current provider order is `dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> deepline_native_enrich_contact -> crustdata_person_enrichment -> peopledatalabs_enrich_contact`.

Example:

```bash
deepline enrich --input leads.csv --output leads_with_emails.csv --rows 0:1 \
  --with '{"alias":"email_from_name_company","tool":"name_and_company_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company_name}}","domain":"{{domain}}"}}'
```

### LinkedIn URL only -> work email

Problem category: LinkedIn-seeded email recovery with no domain.
Input profile: `linkedin_url`, `first_name`, `last_name`.
Output target: one best work email resolved from LinkedIn URL and name alone.

Play tool: `person_linkedin_only_to_email_waterfall`

Why this play:
- Use when contacts came from a people search (e.g. dropleads_search_people) and have LinkedIn URLs but no company domains.
- Do NOT resolve domains first — this play handles it without domain.
- `dropleads_single_person_enrichment` resolves email from LinkedIn + name alone and hits on the first step in most cases.

Play details:
- Required inputs are `linkedin_url`, `first_name`, `last_name`.
- `company_name` is optional and used as a hint.
- Current provider order is `dropleads_single_person_enrichment -> deepline_native_enrich_contact -> crustdata_person_enrichment -> peopledatalabs_enrich_contact`.

Example:

```bash
deepline enrich --input contacts.csv --output contacts_with_emails.csv --rows 0:1 \
  --with '{"alias":"email","tool":"person_linkedin_only_to_email_waterfall","payload":{"linkedin_url":"{{linkedin_url}}","first_name":"{{first_name}}","last_name":"{{last_name}}","company_name":"{{company_name}}"}}'
```

### LinkedIn URL -> work email

Problem category: LinkedIn-seeded email recovery when domain is known.
Input profile: `linkedin_url`, `first_name`, `last_name`, `domain`.
Output target: one best work email resolved from a strong profile identifier.

Play tool: `person_linkedin_to_email_waterfall`

Why this play:
- Use when you have a LinkedIn URL and already know the company domain.
- Adds domain-dependent providers (dropleads_email_finder, hunter, leadmagic) before the LinkedIn-native fallbacks.
- If you do not have the domain, use `person_linkedin_only_to_email_waterfall` instead.

Play details:
- Required inputs are `linkedin_url`, `first_name`, `last_name`, and `domain`.
- `company_name` is optional.
- Current provider order is `dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> deepline_native_enrich_contact -> crustdata_person_enrichment -> peopledatalabs_enrich_contact`.

Example:

```bash
deepline enrich --input contacts.csv --output contacts_with_emails.csv --rows 0:1 \
  --with '{"alias":"email_from_linkedin","tool":"person_linkedin_to_email_waterfall","payload":{"linkedin_url":"{{linkedin_url}}","first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

### Email -> person/company context

Problem category: reverse enrichment from a known email.  
Input profile: `email`.  
Output target: hydrated person and company context.

Play tool: `person_enrichment_from_email_waterfall`

Why this play:
- Email is a strong identifier; use it directly.
- Good for backfilling person/company fields after email recovery.
- This is hydration, not research.

Example:

```bash
deepline enrich --input inbound.csv --output inbound_enriched.csv --rows 0:1 \
  --with '{"alias":"person_context","tool":"person_enrichment_from_email_waterfall","payload":{"email":"{{email}}"}}'
```

### First + last + domain -> work email

Problem category: pattern-first email recovery.  
Input profile: `first_name`, `last_name`, `domain`.  
Output target: one best work email with cost-aware deterministic checks first.

Play tool: `cost_aware_first_name_and_domain_to_email_waterfall`

Why this play:
- Use when company name is missing but the domain is known.
- Starts with cheaper structured recovery paths before broader enrichment.
- Better fit than ad hoc provider chains for the default case.

Play details:
- Required inputs are only `first_name`, `last_name`, and `domain`.
- The play starts with three validated patterns: `first.last@domain`, `firstlast@domain`, and `first_last@domain`.
- Those pattern steps only yield a result when validation returns `valid`; they do not treat `catch_all` as a hit inside the play.
- `catch_all` can still be operationally usable for outreach, but this native play does not count it as an automatic waterfall win.
- After pattern validation, the play falls through to `dropleads_email_finder -> hunter_email_finder -> leadmagic_email_finder -> deepline_native_enrich_contact -> peopledatalabs_enrich_contact`.

Example:

```bash
deepline enrich --input leads.csv --output leads_with_emails.csv --rows 0:1 \
  --with '{"alias":"email_from_name_domain","tool":"cost_aware_first_name_and_domain_to_email_waterfall","payload":{"first_name":"{{first_name}}","last_name":"{{last_name}}","domain":"{{domain}}"}}'
```

### Company -> persona lookup

Problem category: account-to-contact persona lookup.  
Input profile: `company_name`, `domain`, `roles`, and `seniority`.  
Output target: candidate contacts for the requested persona.

Play tool: `company_to_contact_by_role_waterfall`

Why this play:
- This is the canonical company-to-persona play.
- Use it for both role-targeted and seniority-targeted contact discovery.
- The right default for prompts like "find GTM engineers at these companies".
- `roles` should be broad search phrases plus a few strong title variants that providers can match, for example `security`, `identity`, `fraud`, `ciso`, `head of security`, `vp security`.
- `seniority` is still a first-class input and should be used to constrain level, for example `VP`, `C-Level`, `SVP`, `EVP`, `Head`, `Director`.

Provider behavior to remember:
- `dropleads` and `hunter` work best off domain-first inputs.
- `apollo` seniority enums differ from Dropleads-style seniority labels.
- `icypeas` benefits from exact titles more than broad category terms.
- `crustdata` is a structured fallback, not a reason to jump to `call_ai`.

Operational rule:
- If you only have `company_name`, resolve the domain first, then run persona lookup.
- Do not use `call_ai` as the first pass for persona lookup.
- Use `call_ai` only as a fallback research pass when the play and direct providers miss.
- If provider results are weak or sparse, first re-check the available people/company search tools with category searches, then use Apify if you need a broader employee list.

Category searches:
- Use `people_search` when you need better title- and LinkedIn-oriented contact search options.
- Use `company_search` when you need stronger company identity resolution or company-level inputs before the people search.

Search examples:

```bash
deepline tools search --categories people_search --search_terms "title filters,linkedin"
deepline tools search --categories company_search --search_terms "structured filters,firmographics"
```

Apify fallback:
- Prefer an Apify company-employees actor when the default provider mix is not finding enough good contacts.
- This is especially useful when structured people-search providers have thin coverage for a startup or an unusual title.
- Pull the employee list first, then filter for the target persona rather than trying to force more provider retries.
- Apify is slower, which is why it is a fallback rather than the default first pass.

Example:

```bash
deepline enrich --input accounts.csv --output accounts_with_contacts.csv --rows 0:1 \
  --with '{"alias":"role_contacts","tool":"company_to_contact_by_role_waterfall","payload":{"company_name":"{{company_name}}","domain":"{{domain}}","roles":"{{roles}}","seniority":"{{seniority}}"}}'
```

Apify example:

```bash
deepline tools execute apify_run_actor_sync --payload '{"actorId":"apimaestro/linkedin-company-employees-scraper-no-cookies","input":{"identifier":"{{company_linkedin_url}}","max_employees":100},"timeoutMs":180000}'
```

### Company name only -> resolve domain first

Problem category: domain lookup / homepage recovery.  
Input profile: `company_name` plus any contextual hints you already have.  
Output target: canonical `domain` or homepage for downstream plays.

Default tools: `exa_search` or `google_search_google_search`

Why this play:
- Domain lookup is mechanical.
- It should happen before persona lookup, email recovery, or company enrichment.
- `call_ai` is the wrong default here because this is a search-and-resolve task, not a synthesis task.

Routing rule:
1. Resolve domain/homepage with `exa_search` or `google_search_google_search`.
2. Run the downstream play using the recovered domain.
3. Only use `call_ai` if provider/search outputs still do not cover the factual need.

Example:

```bash
deepline enrich --input accounts.csv --output accounts_with_domains.csv --rows 0:1 \
  --with '{"alias":"homepage_search","tool":"google_search_google_search","payload":{"query":"\"{{company_name}}\" official site","num":5}}'
```

### Manual email waterfall

Problem category: custom provider ordering or custom extraction behavior.  
Input profile: varies by target field.  
Output target: same as the native play, but with explicit provider control.

Default surface: `--with-waterfall` plus direct providers

Why this play:
- Use only when no native play fits or when you need to deliberately customize provider order.
- Keeps mechanical enrichment mechanical.
- This is still preferable to starting with `call_ai` for deterministic fields.

Key waterfall rules:
- Always pilot first with `--rows 0:1`, then scale after the shape looks right.
- Every waterfall step needs its own `extract_js`. Before writing it: run `deepline tools get <tool>` to see the response shape, then confirm the path from `result.data`. Use `@path/to/file.js` for multi-line or regex-heavy JS — inline JS in `--with` JSON breaks on escapes.
- Close each waterfall with `--end-waterfall` before starting another one.
- Do not run email waterfalls without minimum match data: name + company, name + domain, or a strong LinkedIn-seeded identity.
- If you need different validation behavior, remember the native cost-aware play only accepts pattern hits when the validator says `valid`.

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

If extract_js returns raw objects instead of scalars, you can store the raw response and use `run_javascript` in a second pass to parse it — useful when you need to inspect the shape before writing extraction logic.

## Post-enrichment validation

After enrichment, validate data quality before moving to the next phase. Run read-only checks — never modify the enriched CSV during validation.

```bash
# Email domain vs company domain — catches previous-employer or wrong-contact emails
python3 ~/.claude/skills/gtm-meta-skill/scripts/validate-emails.py enriched.csv \
    --email-col email --domain-col domain
```

Flag and investigate mismatched rows — these are often from a previous employer or a wrong-person match. If >20% of rows mismatch, the contact-finding step likely needs re-running with better company disambiguation.

## Custom enrichment with call_ai

Use this section for:
- open-ended factual research
- Claygent alternative
- custom signals
- enrichment that combines multiple sources
- personalization inputs
- prompt-driven enrichment patterns that are not covered by a direct provider field

Default rule:
- use direct providers or plays for mechanical fields
- use `call_ai` when you need research, synthesis, or custom logic
- split research and generation into separate passes when both are needed
- keep research here; route actual copywriting to `writing-outreach.md`

### Prompt library

Before writing a fresh prompt, inspect [`prompts.json`](/Users/ctoprani/src/deepline-api/.skills/gtm-meta-skill/prompts.json).

List the top-level keys first. This is the cleanest way to see what prompts already exist:

```bash
jq -r 'keys[]' .skills/gtm-meta-skill/prompts.json
```

If you want a rough keyword search across the file, use `grep`:

```bash
grep -nE "funding|competitor|personalization|research|signal" .skills/gtm-meta-skill/prompts.json
```

Use `grep` for broad hunting only. It matches inside prompt bodies too, so the output is often noisy.

Print a specific prompt by key with `jq`:

```bash
jq -r '."5 interesting facts about a candidate"' .skills/gtm-meta-skill/prompts.json
```

If the prompt key contains quotes or awkward punctuation, first list keys with `jq -r 'keys[]'`, then copy the exact key into the command above.

### Recommended course of action

1. Check whether a play or direct provider already covers the field.
2. Search `prompts.json` for a close starting point.
3. Run a research pass first if the task requires web lookup or synthesis.
4. If the next step is copy, sequence writing, scoring copy, or messaging, switch to `writing-outreach.md` and use the research column there.
5. Keep outputs structured with `json_mode` when the column is meant to feed later steps.

Practical rule:
- use `jq -r 'keys[]'` to browse prompt names
- use `grep -nE ...` to hunt by keyword
- use `jq -r '."KEY NAME"'` to pull the exact prompt text

### Example: inline custom research column

```bash
deepline enrich --input accounts.csv --in-place --rows 0:1 \
  --with '{"alias":"account_research","tool":"call_ai","payload":{"prompt":"Research {{company_name}} ({{domain}}). Return JSON with what_they_build, who_they_sell_to, recent_news.","agent":"claude","model":"haiku","allowed_tools":"WebSearch","json_mode":{"type":"object","properties":{"what_they_build":{"type":"string"},"who_they_sell_to":{"type":"string"},"recent_news":{"type":"string"}},"required":["what_they_build","who_they_sell_to"]}}}'
```

### Example: research pass before writing

```bash
deepline enrich --input leads.csv --output leads_researched.csv --rows 0:1 \
  --with '{"alias":"company_research","tool":"call_ai","payload":{"prompt":"Research {{company_name}}. Return JSON with key pain points and recent news.","agent":"claude","model":"haiku","allowed_tools":"WebSearch","json_mode":{"type":"object","properties":{"pain_points":{"type":"string"},"recent_news":{"type":"string"}}}}}'
```

### Example: adapt a saved prompt from prompts.json

Start by printing the prompt text:

```bash
jq -r '."5 interesting facts about a candidate"' .skills/gtm-meta-skill/prompts.json
```

Then adapt it into a row-level enrich call for research or custom-signal work:

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with '{"alias":"candidate_facts","tool":"call_ai","payload":{"prompt":"Using the style of the saved prompt \"5 interesting facts about a candidate\", find five short, source-backed facts about {{full_name}} at {{company_name}}. Return JSON {facts: string[]}","agent":"claude","model":"haiku","allowed_tools":"WebSearch","json_mode":{"type":"object","properties":{"facts":{"type":"array","items":{"type":"string"}}},"required":["facts"]}}}'
```

For actual email copy, personalized first lines, sequence writing, or scoring language, stop here and route to `writing-outreach.md` with the research columns you just created.

## Custom provider and tool search

Use `deepline tools search` when:
- no play exists
- you need a niche provider or signal
- you want to extend a waterfall
- you want to compare one or two provider options before spending credits

Common searches:

```bash
deepline tools search email
deepline tools search phone
deepline tools search linkedin
deepline tools search validation
deepline tools search company enrichment
deepline tools search contact enrichment
deepline tools search investor
deepline tools search funding
deepline tools search news
deepline tools search tech stack
deepline tools search job change
```

Then inspect the shortlisted tools:

```bash
deepline tools get leadmagic_email_validation
deepline tools get crustdata_enrich_contact
deepline tools get apify_run_actor_sync
```

## Working directory

First action for non-trivial enrich work:

```bash
mkdir -p tmp && WORKDIR=$(mktemp -d tmp/XXXX) && echo $WORKDIR
```

Use `$WORKDIR` for JS files, logs, and outputs. Prefer relative paths.

## Exit back to discovery

If you realize the task is actually:
- "find the companies first"
- "find the candidate contacts first"
- "where does this data source live?"

Stop and route to `finding-companies-and-contacts.md`. This doc assumes you already have rows or known entities.
