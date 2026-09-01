# Enriching and Researching (JTBD Draft)

Use this doc for row-level enrichment, research, waterfalls, validation, coalescing, and custom per-row transforms.

This doc does **not** cover list building, source discovery, or TAM/provider scouting before you have rows. If you do not yet have a seed list, source URL, or known entities, stop and use `finding-companies-and-contacts.md`.

## Core rule

If a play exists, run it with `deepline plays run`. Waterfall prebuilts run
their whole provider cascade internally and stop on the first valid hit — when
you use one, say so: state the play's provider order (from `deepline plays
describe`) and point at the output's source column (`email_source`,
`phone_source`) as the stop-on-found evidence. Never re-implement a waterfall
a prebuilt already encodes. Every prebuilt below has a
batch form that takes a CSV directly:

```bash
deepline plays run prebuilt/name-and-domain-to-email-waterfall-batch --input '{"csv":"leads.csv"}'
deepline runs export <run-id> --out leads_with_emails.csv
```

Column names differ from the play's defaults? Pass a `columns` map from play
field to CSV header — check `deepline plays describe prebuilt/<name>` for the
required fields and default column map:

```bash
deepline plays run prebuilt/name-and-domain-to-email-waterfall-batch \
  --input '{"csv":"leads.csv","columns":{"first_name":"fname","last_name":"lname","domain":"company_domain"}}'
```

Discover plays with `deepline plays search <query>` and `deepline plays list
--show-cost`; read contracts with `deepline plays describe <name>`. Do not
hardcode a provider list a play already encodes.

Use something else only when:

- a prebuilt is close but not exact → fork it (`deepline plays get
prebuilt/<name> --source --out ./<name>.play.ts`, then `plays check`) or
  wrap it (`plays bootstrap ... --using play:prebuilt/<name>`)
- no play exists → author one per
  [recipes/deepline-plays.md](recipes/deepline-plays.md)
- you are testing a niche provider path → direct `deepline tools execute`

`deepline enrich` is deprecated; do not reach for it — the sections below are
all plays.

Billing recovery: if `deepline billing balance` or any paid Deepline command
reports zero credits, `no_billing`, or an insufficient-credits failure, stop
paid work and ask the user whether they want to add Deepline credits. If the
response includes a `recovery` object, quote `recovery.top_up_command` and
`recovery.checkout_command` exactly in your answer, including `--json` and
`--no-open`. Do not shorten them, and do not run either command until the user
explicitly approves.

## Scenario table

Every play named in this table runs via `deepline plays run prebuilt/<name>`
(batch: `prebuilt/<name>-batch`) — never through `enrich --with`.

| Scenario                                                 | Use when                                                                                                   | Default play/tool                                         | Why                                                                                                                      |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Name + domain -> work email                              | You have name + domain (or can resolve domain from company_name / Sales Nav URL first)                     | `Name + domain -> work email`                             | Canonical deterministic path. Handles both direct and domain-first-then-waterfall cases.                                 |
| LinkedIn URL -> work email                               | Standard `/in/` LinkedIn URL + name. `domain` optional; include if known for extra coverage.               | `LinkedIn URL -> work email`                              | Works with or without domain. Do NOT use for SN `/sales/lead/` URLs — resolve domain first and use the name+domain play. |
| Email -> person/company context                          | You have an inbound or work email and need person + company details                                        | `Email -> person/company context`                         | Good for hydrating context from a single strong identifier.                                                              |
| Personal email -> LinkedIn profile                       | Bare personal email (Gmail/GitHub signup); you need LinkedIn + name + company, not a work email            | `Personal email -> LinkedIn profile`                      | Reverse identity resolution; best for personal-email-only lists.                                                         |
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
| **Personal email discovery**                             | User explicitly asks for personal emails (Gmail, Hotmail, etc.) - NOT work emails                          | `Personal email discovery`                                | Use Fullenrich or BetterContact. Do not substitute work-email providers.                                                 |

## Notes

- **Personal vs work emails:** When the user asks for personal emails, they mean Gmail/Hotmail/Yahoo, not work emails. Use Fullenrich (`contact.personal_emails`) or BetterContact; do not substitute Hunter, LeadMagic, or other work-email providers.
- Direct provider tools are preferred for mechanical fields when no play exists.
- When multiple providers recover the same mechanical field, prefer the route that bills on returned results or successful hits. Use request-priced, page-priced, or broad AI passes only after a tiny pilot proves they return usable rows.
- `run_javascript` is for deterministic transforms, normalization, coalescing, templating, and cheap row-level glue logic.
- `deeplineagent` is the default AI path for research, synthesis, custom signals, and classification when JS is not enough.
- Domain lookup / homepage recovery is mechanical. Use `exa_search` with rich context or `serper_google_search`, not `deeplineagent`.
- For local SMB or restaurant contact emails, do not start with name + domain work-email waterfalls unless you have a named person. Prefer the small-business prospecting recipe first: Maps identity, website/contact extraction, then optional Facebook/Instagram profile contact fields when the row or pilot suggests social profiles are the best public source. ScrapeCreators profile tools are candidate routes, not required steps.
- Persona lookup means "find candidate contacts at a company for a target role or seniority." Use the dedicated play, not generic research.
- Validate after recovery or coalescing, not during each waterfall step.
- For contact-to-email work, route by your strongest identifiers: name + domain -> `Name + domain -> work email` (or `First + last + domain -> work email`); name + company only (no domain) OR Sales Navigator contacts -> resolve domain first, then `name-and-domain-to-email-waterfall`; standard `/in/` LinkedIn URL + name -> `LinkedIn URL -> work email` (domain optional).
- **Sales Navigator exports**: `linkedin_url` values in `/sales/lead/` format are rejected by every provider (dropleads, crustdata, deepline_native, PDL). Do not pass them directly to any email waterfall. Resolve the company domain first, then use `name-and-domain-to-email-waterfall`.
- Contacts from a people search (e.g. dropleads_search_people) with **standard `/in/`** URLs -> `person-linkedin-to-email` (`domain` optional). Does NOT apply to SN `/sales/lead/` URLs.
- Validation interpretation: `valid` is deliverable, `catch_all` is usable but riskier, `invalid` should be dropped, and `unknown` is unresolved.
- Phone recovery usually comes later in the pipeline than email or LinkedIn recovery.
- Prefer inline code for short `run_javascript` transforms. Only move code into files when the logic is long, reused, or too awkward to keep inline.
- In Claude Desktop on Windows, the working directory may look like `C:\Users\...` while the tool executor is still Bash/Git Bash. Use Bash commands such as `rm`, not PowerShell commands such as `Remove-Item`, unless the session context explicitly says the active shell is PowerShell.

## Plays

### Name + domain -> work email

Play tool: `name-and-domain-to-email-waterfall`

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
# One contact
deepline plays run prebuilt/name-and-domain-to-email-waterfall \
  --input '{"first_name":"Ada","last_name":"Lovelace","domain":"acme.com"}'

# A CSV — pilot on a slice first, then the full file, then EXPORT TO THE REQUESTED PATH
head -3 leads.csv > pilot.csv
deepline plays run prebuilt/name-and-domain-to-email-waterfall-batch --input '{"csv":"pilot.csv"}'
deepline runs export <pilot-run-id> --out pilot_out.csv   # inspect quality + cost
deepline plays run prebuilt/name-and-domain-to-email-waterfall-batch --input '{"csv":"leads.csv"}'
deepline runs export <full-run-id> --out "$FINAL_CSV"     # the deliverable — never skip this
```

A user-stated scope is already approved (SKILL.md §4.1): after the pilot
checks out, run the full file and export to `$FINAL_CSV` without stopping to
ask. For a small stated input (≤ ~25 rows), skip the slice entirely and run
the full file once. The pilot is never the deliverable.

**Domain-first resolution** — when you only have `company_name` or a SN `/sales/lead/` URL, resolve domains before the email play. For a handful of companies, resolve each directly and patch the CSV:

```bash
deepline tools execute exa_search --input '{"query":"Acme Corp official website","numResults":1}'
```

For a list, author a two-column custom play per [recipes/deepline-plays.md](recipes/deepline-plays.md) — `exa_search` column, then a `run_javascript` column extracting the registrable domain — and feed its export to `prebuilt/name-and-domain-to-email-waterfall-batch`.

### LinkedIn URL -> work email

Play tool: `person-linkedin-to-email`

**Required payload:** `linkedin_url`.

Use when contacts have a **standard `/in/`** LinkedIn URL (e.g. from `dropleads_search_people`). The play works off the LinkedIn URL directly.

**Do NOT use for Sales Navigator `/sales/lead/` URLs** — providers reject them. Resolve the company domain first, then use the name+domain play above.

**Example:**

```bash
deepline plays run prebuilt/person-linkedin-to-email --input '{"linkedin_url":"https://www.linkedin.com/in/example/"}'

# CSV: pilot a slice, then the full file
deepline plays run prebuilt/person-linkedin-to-email-batch --input '{"csv":"contacts.csv"}'
deepline runs export <run-id> --out contacts_with_emails.csv
```

### Email -> person/company context

Play tool: `deepline_native_enrich_contact`

Why this play:

- Email is a strong identifier; use it directly.
- This is hydration, not research.

Example:

```bash
deepline tools execute deepline_native_enrich_contact --input '{"email":"ada@acme.com"}'
```

For a CSV of inbound emails, author a one-column custom play calling the same tool per row ([recipes/deepline-plays.md](recipes/deepline-plays.md)).

### Personal email -> LinkedIn profile

Play tool: `personal-email-to-linkedin`. Required payload: `personal_email` only (name/company unknown, unlike the work-email plays).

Use it when a signup list has only personal emails and you want to know who they are. Returns `linkedin_url`, `name`, `company`, `title`; a profile is often more recoverable and useful than a work email here. The play normalizes Gmail first, then waterfalls `deepline_native` -> `forager` -> `findymail` -> `peopledatalabs`, charging per hit.

The same play runs two ways:

```bash
deepline plays run prebuilt/personal-email-to-linkedin --input '{"personal_email":"ada@gmail.com"}'

# CSV of signups
deepline plays run prebuilt/personal-email-to-linkedin-batch --input '{"csv":"signups.csv"}'
deepline runs export <run-id> --out signups_with_profiles.csv
```

Bare personal email coverage is ~25-40%, so over-provision. If a row returns a
company but no work email, chain `name-and-domain-to-email-waterfall-batch` on
the export.

### Contact identity -> phone

Play tool: `person-to-phone`

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
deepline plays run prebuilt/person-to-phone \
  --input '{"first_name":"Ada","last_name":"Lovelace","domain":"acme.com","email":"ada@acme.com","linkedin_url":"https://www.linkedin.com/in/example/"}'

# CSV: pilot a slice, then the full file
deepline plays run prebuilt/person-to-phone-batch --input '{"csv":"contacts.csv"}'
deepline runs export <run-id> --out contacts_with_phones.csv
```

### Company -> persona lookup

Play tool: `company-to-contact`

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

```bash
deepline plays run prebuilt/company-to-contact \
  --input '{"domain":"acme.com","roles":["VP Marketing"],"seniority":"VP"}'

# CSV of accounts: pilot a slice, then the full file
deepline plays run prebuilt/company-to-contact-batch --input '{"csv":"accounts.csv"}'
deepline runs export <run-id> --out accounts_with_contacts.csv
```

Use the native prebuilt for repeatable domain-to-roster work:

```bash
deepline plays describe prebuilt/company-domain-to-linkedin-employees-harvestapi
deepline plays run prebuilt/company-domain-to-linkedin-employees-harvestapi \
  --input '{"domain":"openai.com","max_items":25}'
```

Use the direct operations below only when you need a custom result shape:

```bash
deepline tools describe harvestapi_get_company --schema-only
deepline tools execute harvestapi_get_company --input '{"url":"https://www.linkedin.com/company/openai/"}' --json
deepline tools describe harvestapi_search_leads --schema-only
deepline tools execute harvestapi_search_leads --input '{"currentCompanies":"https://www.linkedin.com/company/openai/","sessionId":"STABLE_RANDOM_SESSION_ID","page":1}' --out openai-employees.csv
```

Generate the stable random `sessionId` before page 1 and reuse it on every page. Because HarvestAPI matches `currentCompanies` by company name, keep only results whose `currentPositions[].companyId` matches the target `element.id` returned by `harvestapi_get_company`.

### LinkedIn post URL -> list of engagers

Use the native HarvestAPI prebuilt. It fetches both reactors and commenters,
paginates each operation, unions their `elements` by actor identity, and returns
the established engager-row schema:

```bash
deepline plays describe prebuilt/linkedin-post-to-engagers-harvestapi
deepline plays run prebuilt/linkedin-post-to-engagers-harvestapi \
  --input '{"post_url":"https://www.linkedin.com/posts/...","max_items":1000}'
```

Call the native operations directly only when you need a custom result shape:

```bash
deepline tools describe harvestapi_get_post_reactions
deepline tools describe harvestapi_get_post_comments
deepline tools execute harvestapi_get_post_reactions --input '{"post":"https://www.linkedin.com/posts/...","page":1}' --out post-reactions.csv
deepline tools execute harvestapi_get_post_comments --input '{"post":"https://www.linkedin.com/posts/...","page":1}' --out post-comments.csv
```

### List of people with name + position -> ICP qualification

Play tool: `engagers_to_icp_qualification`

Classifies a person against an ICP using name + position/headline. Returns `{icp_tier, icp_reason}`. Do NOT use if qualification needs company size, funding, or web research — use a custom `deeplineagent` prompt instead.

```bash
deepline plays run prebuilt/engagers-to-icp-qualification \
  --input '{"first_name":"Ada","last_name":"Lovelace","position":"VP Engineering at Acme","icp_description":"Tier 1: VP/Head of Engineering, CTO at B2B SaaS. Tier 2: Senior engineers. Tier 3: everyone else."}'
```

For a CSV of engagers, wrap the tool in a small custom play mapping over the
rows ([recipes/deepline-plays.md](recipes/deepline-plays.md)).

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
deepline tools execute serper_google_search --input '{"query":"\"Acme Corp\" official site","num":5}'
```

For a list of companies, author a two-column custom play (search + extract) per [recipes/deepline-plays.md](recipes/deepline-plays.md).

### Custom email waterfall

Problem category: custom provider ordering or custom extraction behavior.

Use only when no native play fits, or you need to deliberately customize
provider order. Fork the nearest prebuilt and edit its step order:

```bash
deepline plays get prebuilt/name-and-domain-to-email-waterfall --source --out ./email-waterfall.play.ts
# edit: drop/reorder legs, change gating
deepline plays check ./email-waterfall.play.ts
deepline plays run --file ./email-waterfall.play.ts --input '{"first_name":"Ada","last_name":"Lovelace","domain":"acme.com"}'
```

If `plays check` fails on a missing local import, that prebuilt is multi-file:
wrap it with `plays bootstrap ... --using play:prebuilt/<name>` instead, or
author the waterfall fresh per
[recipes/deepline-plays.md](recipes/deepline-plays.md) (a `steps()` cascade:
sequential legs, stop on first valid hit, validation after recovery).

Rules that carry over from the native plays: pilot before scale; do not run
email waterfalls without minimum match data (name + company, name + domain, or
a strong LinkedIn-seeded identity); validation belongs after recovery, and the
cost-aware plays only accept pattern hits the validator marks `valid`.

## Post-run validation

After a play run, validate data quality before moving to the next phase. Run read-only checks — never modify the enriched CSV during validation.

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

## Custom columns are plays

Open-ended factual research, Claygent-style enrichment, custom signals,
multi-source columns, personalization inputs: author a custom play per
[recipes/deepline-plays.md](recipes/deepline-plays.md) — a dataset over your
CSV with one `withColumn` per field.

Routing inside the play:

- `run_javascript` for deterministic row logic: formatting, normalization,
  coalescing, templating, parsing, conditional transforms.
- `deeplineagent` for AI work: classification, extraction, scoring, structured
  generation, browsing, multi-step synthesis. Keep outputs structured with
  `jsonSchema` when a later column consumes them.
- Split research and generation into separate columns; keep research here and
  route copywriting to `writing-outreach.md`.
- Start prompts from [`prompts.json`](prompts.json): list keys with
  `jq -r 'keys[]' .skills/deepline-gtm/prompts.json`, print one with
  `jq -r '."<key>"' ...`, adapt it into the `deeplineagent` column's prompt.
- Reading tool output inside a play: use the documented getters and
  `extracted*` accessors from `deepline tools describe <tool>` before drilling
  into raw provider nesting.

The iterate loop applies with force here: run the play on 2-3 rows, read the
per-column outcomes in the storage table, fix prompts/providers, then scale.

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
