---
name: deepline-gtm
description: "Use for GTM prospecting, enrichment, qualification, CSV processing, lead/account/contact research, public/social pre-research, waterfall enrichment, email/LinkedIn lookup, personalization, scoring, campaigns, and custom Deepline plays/scripts. Providers: adyntel, ai_ark, allegrow, apify, attio, aviato, bettercontact, bloomberry, bluesky, builtwith, cloudflare, contactout, crustdata, crustdata-v2, crustdata-v3, customer_db, dataforseo, datagma, deepline_native, deeplineagent, discolike, dropleads, emailbison, enformion, exa, findymail, firecrawl, forager, fullenrich, generic_http, google_ads_audiences, hackernews, heyreach, hubspot, hunter, icypeas, instantly, ipqs, leadmagic, lemlist, limadata, linkedin_ads_audiences, linkedin_scraper, lusha, meta_audiences, openmart, opensosdata, openwebninja, parallel, peopledatalabs, predictleads, prospeo, rocketreach, salesforce, scrapecreators, serper, slack, smartlead, snowflake, tamradar, theirstack, trestle, twitterapi, upcell, wiza, wizleads, zerobounce."
---

# GTM Meta Skill

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

Use this skill for prospecting, account research, contact enrichment, verification, lead scoring, personalization, and campaign activation.

## 1) What this skill governs

- Route GTM decisions, safety gates, and provider/quality defaults before execution.
- Keep long command chains and tooling nuance in sub-docs; provider-specific implementation detail in `provider-playbooks/*.md`.
- Provide clear entry points for both paid and non-paid workflows, including one-row pilots.

## Process/goal

Customer is generally trying to go from "I have an ICP" to "Here's a list of prospects with email/linkedin and very personalized content or signals". They may be anywhere in this process, but guide them along.

**Discovery order: companies first, then people.** When the task requires finding contacts at companies matching criteria (portfolio, ICP, hiring signal), discover the company set first, then find people at each company. Do not start with broad people-search queries.

### Documentation hierarchy

- Level 1 (`SKILL.md`): decision model, guardrails, approval gates, links to sub-docs.
- Level 2 (phase docs): [finding-companies-and-contacts.md](finding-companies-and-contacts.md), [enriching-and-researching.md](enriching-and-researching.md), [writing-outreach.md](writing-outreach.md), `prompts.json`.
- Level 2.5 (`recipes/*.md`): step-by-step playbooks for specific tasks (email lookup, LinkedIn resolution, waterfall patterns, contact finding, actor contracts). Search like code with Grep.
- Level 3 (`provider-playbooks/*.md`): provider-specific quirks, cost/quality notes, and fallback behavior.

No-loss rule: moved guidance remains fully documented at its canonical level and is linked from here.

### CLI family fallback

If Deepline CLI V2 or SDK mode seems broken while running a GTM task, check `deepline switch status`. Use `deepline switch sdk` to move an installer-managed CLI to SDK mode, or `deepline switch python` to roll back to the Python CLI. Auth is host-scoped and should carry across both families.

### Execution contract

GTM requests are operational work: execute direct Deepline calls yourself once inputs and approval gates are satisfied.

**Interim local SDK mode:** treat `deepline enrich` and batch/CSV `deepline plays run` usage as unavailable/bugged for agent-run row work. Do not use row orchestration as your batch engine. Write the local shell command, Node/TypeScript snippet, or project-local script needed for the task. Import the Deepline SDK and call `new DeeplineClient().executeTool(toolId, input)` directly, or `const ctx = await Deepline.connect(); await ctx.tools.execute(toolId, input)` for the higher-level SDK context.

Scalar prebuilt plays are allowed. If the task is a concrete one-off with literal input, use the play surface (`await ctx.play('<described-play-name>').runSync(input)` or the scalar CLI play command) after `plays search/describe` confirms the current name and input contract. For row/CSV scale, wrap the scalar play/tool call in your own stateful loop instead of delegating the batch to `deepline enrich` or `deepline plays run`.

For full CSV runs, paginated exports, or flaky tools, persist row state, skip already-successful keys on resume, and make local retry/backoff explicit for `RateLimitError`/429/5xx/timeout failures. Honor `retryAfterMs`. Keep concurrency low while providers are rate-limiting. If auth, credits, missing inputs, or an SDK/runtime bug blocks direct execution, report the exact blocker instead of replacing it with static research or guessed rows.

## 2) Read behavior — MANDATORY before any execution

**STOP. Do not call any provider through the SDK or write any search command until you have opened the correct sub-doc for your task.**

These skill docs and sub-docs are not generic documentation — they are distilled from hundreds of real runs and encode exactly what works, what fails, and why. They contain validated parameter schemas, correct filter syntax, parallel execution patterns, tested sample payloads, and known pitfalls that took many iterations to discover. Think of them as shortcuts: reading a doc for 5 seconds saves you from 10 failed tool calls, wasted credits, and garbage output. Every time an agent skips reading the docs and tries to "figure it out" from first principles, it re-discovers the same failure modes that are already documented and solved.

SKILL.md is the routing layer — it tells you WHERE to go, not HOW to execute. The sub-docs and task-specific skills contain the HOW. Without them you will guess parameters, pick wrong providers, run searches sequentially instead of in parallel, and produce garbage results. This has happened repeatedly.

### Open the right doc BEFORE executing

**This is not optional.** Read the matching doc. Do not skip this step. Do not "just try one provider real quick" or "just run one search to see." These docs exist because the correct approach was non-obvious and had to be learned through trial and error — they are shortcuts that let you skip straight to what works.

!important READING MULTIPLE DOCS IS A GREAT IDEA AND OFTEN SUPER ESSENTIAL. JUST READ MORE.

**Routing rules — match your task to a doc and READ IT:**

| When the task involves...                                                                                                                                                                                                                                                                                                                                                          | You MUST read this doc first                                                 | What it gives you (that SKILL.md doesn't)                                                                                                                                                                                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Finding companies, finding people, building lead lists, prospecting, portfolio/VC sourcing, contact finding at known companies, coverage completion at scale**                                                                                                                                                                                                                   | [finding-companies-and-contacts.md](finding-companies-and-contacts.md)       | Provider filter schemas, parallel execution patterns, provider mix tables, role-based search rules, subagent orchestration, at-scale coverage completion, portfolio/VC shortcuts, contact finding patterns.                                                                                                                          |
| **Researching companies or people, understanding what they build, figuring out use cases, personalizing based on mission/product/industry, enriching a CSV, adding data columns, waterfall enrichment, finding emails/phones/LinkedIn, coalescing data, custom signals, SDK tool calls, Apify actors — any task that adds or transforms row-level data** | [enriching-and-researching.md](enriching-and-researching.md)                 | Interim local-SDK rules, provider routing, row-script patterns, waterfall fallback order, coalescing logic, custom signal buckets, Apify actor selection, GTM definitions, and defaults. |
| **Creating custom Deepline plays/scripts that combine multiple tools and/or other plays**, map over CSV rows, add fallback logic, joins/projections, durable datasets, custom run/export behavior, webhook/cron-style orchestration, or a reusable `.play.ts` scratchpad. This is for composition and control flow, not ordinary single-column enrichment. | [recipes/deepline-plays.md](recipes/deepline-plays.md)                       | Direct vs compose decision, play search/describe discipline, bootstrap/wrap/fork rules, durable authoring basics, webhook/cron replacement routing, run/export/repair routing, and exact SDK/API reference pointers.                                                                                                                |
| **Writing cold emails, personalizing outreach, lead scoring, qualification, sequence design, campaign copy, inspecting CSVs in Playground.** If the task also requires researching companies/people to inform the writing, read [enriching-and-researching.md](enriching-and-researching.md) too — it has the multi-pass pipeline pattern.                                         | [writing-outreach.md](writing-outreach.md)                                   | Prompt templates from `prompts.json`. Scoring rubrics. Email length/tone/structure rules. Personalization patterns. Qualification frameworks. Playground inspection commands.                                                                                                                                                        |
| **Deepline Monitors / Signal Radars** — continuously capturing a provider's webhook events (email replies, new job postings, intent signals) into a Customer DB table, or deploying/listing/managing those upstream provider pipes. Event-driven streaming, NOT an on-demand enrich/sourcing run. **Conditional gate — only read the `deepline-monitors` recipe if BOTH hold:** (a) the task is actually about monitors/Signal Radars, AND (b) `deepline monitors status` exits 0 (the user has access). Run that status check FIRST; if it exits non-zero, do NOT read the recipe or attempt monitor commands — tell the user monitors access is granted by a Deepline admin via Admin → Rollouts. | [recipes/deepline-monitors.md](recipes/deepline-monitors.md) | What monitors/Signal Radars are, when to use them vs plays, the full `deepline monitors` command set (status, available, check, deploy, list, get, update, delete, reactivate), monitor definition shape, the provider-webhook → Customer DB → triggered-play data flow, and the access gating. |

If you are hand-authoring row scripts instead of using a native play, jump straight to the direct execution section in [enriching-and-researching.md](enriching-and-researching.md). It spells out how to call SDK tools inline and persist row state.

### Recipes: step-by-step playbooks for specific tasks (check before executing)

The `recipes/` directory contains battle-tested playbooks. **Before you start executing, scan this list and read any recipe that matches your task.**

When a recipe matches: **follow it step-by-step as your execution plan.** Recipes encode hard-won sequencing and provider choices — trust them over generic guidance or your own intuition. If the user's request doesn't perfectly fit, adapt the recipe using the phase docs above, but keep the recipe's structure and ordering as your baseline.

| Recipe                          | Use when...                                                                                                                                |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `account-orgchart.md`           | Building an org chart, account map, buying committee, stakeholder map, or multi-threading plan around a target person or company          |
| `build-tam.md`                  | Building a total addressable market list or large company list from ICP criteria                                                           |
| `clay-to-deepline.md`           | Converting a Clay table into local Deepline enrich scripts (extraction, mapping, parity validation)                                        |
| `deepline-monitors.md`          | **ACCESS-GATED.** Deepline Monitors (dashboard: Signal Radars): continuously capturing a provider's webhook events (email replies, new job posts, funding, intent) into a Customer DB table and triggering plays. Run `deepline monitors status` first; if it reports no access, do NOT use it. |
| `deepline-plays.md`             | Creating custom `.play.ts` scripts that compose multiple tools/plays, durable datasets, fallback logic, joins/projections, webhook/cron-style orchestration, and custom run/export behavior |
| `find-qualified-titles.md`      | "Find all job titles at these companies" / "find the marketing-ops/RevOps/Salesforce buyers": pull each company's real title roster (free `company_titles`), LLM-filter to the ICP, then find contacts with tiered (LinkedIn, email, phone) reveal |
| `linkedin-url-lookup.md`        | Resolving a person's LinkedIn profile URL from their name and company with strict identity validation                                      |
| `portfolio-prospecting.md`      | Finding companies backed by a specific investor or accelerator, then finding contacts and building personalized outbound                   |
| `public-social-research.md`     | Finding public community language, launch feedback, competitor mentions, and market signals across X/Twitter, Hacker News, and Bluesky    |
| `small-business-prospecting.md` | Finding local small businesses or storefront/service-area companies using Maps-style search. Doctors, services business, restaurants, etc. |

If none match, grep for more specific keywords: `Grep pattern="<keyword>" path="<directory containing this SKILL.md>/recipes/" glob="*.md" output_mode="files_with_matches"`

### Data

- When the user hands you a CSV, run `deepline csv show --csv <path> --summary` first to understand its shape (row count, columns, sample values) before deciding how to process it.
- **NEVER read a large CSV into context with the Read tool.** Reading CSV rows into the conversation window exhausts context and produces zero output. This is the single most common failure mode.
- For row-by-row processing, do not use `deepline enrich` or batch `deepline plays run` during interim local SDK mode. Use SDK scripts that call `DeeplineClient.executeTool` or scalar prebuilt plays per row with durable state.
- For any full CSV run or repeatable command, persist row/run state so retries, 429 backoff, and resume are durable.
- To explore or understand CSV content without loading it, use `deepline csv show --csv <path> --rows 0:2` for a two-row sample, or spawn an Explore subagent to answer questions about the data.
- For CSV work, run a one-row SDK pilot first, inspect the output, then scale through the same stateful script after approval. If the SDK surface is unclear, inspect `sdk/README.md` or `references/plays-sdk-reference.md` before the first call.

### Tools

For signal-driven discovery (investor, funding, hiring, headcount, industry, geo, tech stack, compliance), start with `deepline tools search`. Do not guess fields.

Search 2-4 synonyms, execute in parallel:

```bash
deepline tools search investor
deepline tools search investor --prefix crustdata
deepline tools search --categories company_search --search_terms "structured filters,icp"
deepline tools search --categories people_search --search_terms "title filters,linkedin"
```

### Tool search categories

Use category filters when tool type matters more than provider breadth. Common categories:

- `company_search`: account/company discovery tools
- `people_search`: people/contact discovery tools
- `company_enrich`: company enrichment on known companies
- `people_enrich`: person/contact enrichment on known people
- `email_verify`: email verification / deliverability
- `email_finder`: email lookup / discovery
- `phone_finder`: phone lookup / discovery
- `research`: company research, ad intel, job search, technographics, web research
- `automation`: workflow-style tools, browser/actor runs, batch automation
- `outbound_tools`: all Lemlist/Smartlead/Instantly/HeyReach style actions
- `autocomplete`: canonical filter value discovery before search
- `admin`: credits, monitoring, logs, schemas, local/dev utilities

Use `--search_terms` for extra ranking hints like `structured filters`, `title filters`, `api native`, `autocomplete`, or `bulk`.

Good:

- `deepline tools search --categories company_search --search_terms "investors,funding"`
- `deepline tools search --categories research --search_terms "ads,technographics"`

Avoid:

- `deepline tools search stuff`
- `deepline tools search search across filters`

## 2.5) Interim row-work mode

Until orchestration commands are healthy again, use local SDK execution for row work:

- Discover the live tool contract with `DeeplineClient.searchTools()` / `getTool()`. CLI `deepline tools search` / `tools describe` is acceptable for discovery only, not execution.
- Pilot one row by running a local script that imports `deepline` and calls `client.executeTool(toolId, input)`.
- Scale with a project-local script that reads the CSV, writes an output CSV/JSONL, persists per-row status, and handles 429/5xx/timeouts with explicit `retryAfterMs`-aware backoff.
- Keep provider concurrency conservative. A slower resumable script is better than blasting parallel calls into 429s and losing row state.

## 3) Core policy defaults

### 3.1 Definitions and defaults

GTM time windows, thresholds, and interpretation rules are defined in the Definitions section of [enriching-and-researching.md](enriching-and-researching.md).

## Provider Playbooks

Provider-specific playbooks are bundled as separate reference files. Open the relevant playbook when provider-specific behavior, pricing, caveats, or payload conventions matter.

[adyntel](provider-playbooks/adyntel.md), [ai_ark](provider-playbooks/ai_ark.md), [allegrow](provider-playbooks/allegrow.md), [apify](provider-playbooks/apify.md), [attio](provider-playbooks/attio.md), [aviato](provider-playbooks/aviato.md), [bettercontact](provider-playbooks/bettercontact.md), [bloomberry](provider-playbooks/bloomberry.md), [bluesky](provider-playbooks/bluesky.md), [builtwith](provider-playbooks/builtwith.md), [cloudflare](provider-playbooks/cloudflare.md), [contactout](provider-playbooks/contactout.md), [crustdata](provider-playbooks/crustdata.md), [crustdata-v2](provider-playbooks/crustdata-v2.md), [crustdata-v3](provider-playbooks/crustdata-v3.md), [dataforseo](provider-playbooks/dataforseo.md), [datagma](provider-playbooks/datagma.md), [deepline_native](provider-playbooks/deepline_native.md), [deeplineagent](provider-playbooks/deeplineagent.md), [discolike](provider-playbooks/discolike.md), [dropleads](provider-playbooks/dropleads.md), [emailbison](provider-playbooks/emailbison.md), [enformion](provider-playbooks/enformion.md), [exa](provider-playbooks/exa.md), [findymail](provider-playbooks/findymail.md), [firecrawl](provider-playbooks/firecrawl.md), [forager](provider-playbooks/forager.md), [fullenrich](provider-playbooks/fullenrich.md), [generic_http](provider-playbooks/generic_http.md), [google_ads_audiences](provider-playbooks/google_ads_audiences.md), [hackernews](provider-playbooks/hackernews.md), [heyreach](provider-playbooks/heyreach.md), [hubspot](provider-playbooks/hubspot.md), [hunter](provider-playbooks/hunter.md), [icypeas](provider-playbooks/icypeas.md), [instantly](provider-playbooks/instantly.md), [ipqs](provider-playbooks/ipqs.md), [leadmagic](provider-playbooks/leadmagic.md), [lemlist](provider-playbooks/lemlist.md), [limadata](provider-playbooks/limadata.md), [linkedin_ads_audiences](provider-playbooks/linkedin_ads_audiences.md), [lusha](provider-playbooks/lusha.md), [meta_audiences](provider-playbooks/meta_audiences.md), [openmart](provider-playbooks/openmart.md), [opensosdata](provider-playbooks/opensosdata.md), [openwebninja](provider-playbooks/openwebninja.md), [parallel](provider-playbooks/parallel.md), [peopledatalabs](provider-playbooks/peopledatalabs.md), [predictleads](provider-playbooks/predictleads.md), [prospeo](provider-playbooks/prospeo.md), [salesforce](provider-playbooks/salesforce.md), [scrapecreators](provider-playbooks/scrapecreators.md), [serper](provider-playbooks/serper.md), [smartlead](provider-playbooks/smartlead.md), [snowflake](provider-playbooks/snowflake.md), [tamradar](provider-playbooks/tamradar.md), [theirstack](provider-playbooks/theirstack.md), [trestle](provider-playbooks/trestle.md), [twitterapi](provider-playbooks/twitterapi.md), [upcell](provider-playbooks/upcell.md), [wiza](provider-playbooks/wiza.md), [wizleads](provider-playbooks/wizleads.md), [zerobounce](provider-playbooks/zerobounce.md)

- Apply defaults when user input is absent.
- User-specified values always override defaults.
- In approval messages, list active defaults as assumptions.

### 3.2 Working directory — set up BEFORE any file writes

**NEVER write files to `/tmp/` or any absolute temp directory.** Files in system `/tmp/` are wiped on reboot — users permanently lose enriched CSVs, research outputs, and hours of paid enrichment work. This is a critical data-loss risk.

Set up a descriptive project-local working directory as your first action:

```bash
WORKDIR="deepline/data/<descriptive-task-slug>" && mkdir -p "$WORKDIR" && echo "$WORKDIR"
```

The slug must describe the task (e.g. `deepline/data/yc-cmo-outbound`, `deepline/data/acme-email-waterfall`). Do NOT use random names like `mktemp` generates — the user needs to find these files later. See [enriching-and-researching.md](enriching-and-researching.md) for full details.

### 3.3 Output policy and User Interaction Pattern

- Interim local SDK mode supersedes older row-command examples in this skill. Use local SDK tool execution for list enrichment or discovery at scale.
- Even for company → ICP person flows, SDK execution works: search, inspect contracts, and call the provider tool directly from a stateful script.
- Even when you don't have a CSV, create one, then run your own row loop over it.
- This process requires iteration; one-shotting a single direct call is only the pilot, not the full workflow.
- For deterministic transforms, write local JS/Python in the row script instead of relying on row-command transform helpers.
- In chat, send the file path and run/play URL when available, not pasted CSV rows, unless explicitly requested.
- Preserve lineage columns (especially `_metadata`) end-to-end. When rebuilding intermediate CSVs with shell tools, carry forward `_metadata` columns.
- Never enrich a user-provided or source CSV in-place. Use `--output` to write to your working directory on the first pass, then `--in-place` on that output for subsequent passes. `--in-place` is for iterating on your own prior outputs — never on source files.
- For reruns, keep successful existing cells by default; use `--with-force <alias>` only for targeted recompute.

See [enriching-and-researching.md](enriching-and-researching.md) for `deepline csv` commands, pre-flight/post-run script templates, and inspection details.

### 3.4 Final file + playground check (light)

- Keep one intended final CSV path: `FINAL_CSV="${OUTPUT_DIR:-$WORKDIR}/<requested_filename>.csv"`
- Before finishing: use the post-run inspection script pattern from [enriching-and-researching.md](enriching-and-researching.md). Run it once instead of separate checks.
- In the final message, always report: exact `FINAL_CSV` and the run/play URL when the CLI reports one.
- Before closing the session, follow the Section 7 consent step for session sharing.

## 4) Credit and approval gate (paid actions)

### 4.1 Required run order

1. Pilot on a narrow scope (one exact row from the user's input).
2. Request explicit approval.
3. Run full scope only after approval.

### 4.2 Execution sizing

- Use smaller sequential commands first.
- Keep limits low and windows bounded before scaling.
- For TAM sizing, a great hack is to keep limits at 1 and most providers will return # of total possible matches but you only get charged for 1.
- Prefer providers and plays that charge on returned results or successful hits when coverage is uncertain. If a provider bills per attempt/request/page, prove quality on a tiny pilot before letting it fan out.
- Stop after the pilot when the first rows show low usable coverage, wrong-person/company matches, missing getters, or high cost per usable row. Change route/provider order before buying the same failure at full scale.
- Do not depend on monthly caps as a hard risk control.

### 4.2.1 Over-provision, then filter — never chase missing rows

When the user asks for N rows, start with ~1.4×N (e.g., 35 for 25). Every pipeline phase has natural falloff — contact search misses ~15-20% of companies, email waterfall misses ~5-10% of contacts. Fighting to complete the hard rows is almost always a waste: the companies that providers can't find contacts for are the same ones that won't have email coverage either.

**Do this:**

1. Pull more candidates than needed at the top of funnel.
2. Run the full pipeline (contacts → emails → outbound).
3. At the end, filter to the best N complete rows and deliver those.
4. Drop incomplete rows — don't retry or manually patch them.

**Do NOT do this:**

- Trim results to exactly N before running the pipeline.
- Spend turns retrying failed lookups with fallback providers, `deeplineagent` research passes, or manual patching.
- Run enrichment on all rows just to fill gaps in a few (especially broad `deeplineagent` research passes).

Provider coverage is a property of the company, not something you can overcome with more effort. Tiny startups with 5 people will have zero coverage across all providers — no amount of retrying changes that. Over-provision at the top and let incomplete rows fall off naturally.

### 4.3 Approval message content

Include all of:

1. Provider(s)
2. Pilot summary and observed behavior
3. Intent-level assumptions (3–5 one-line bullets)
4. CSV/JSON preview from a real one-row direct-call pilot
5. Credits estimate / range
6. Full-run scope size
7. Max spend cap
8. Approval question: `Approve full run?`

Use the direct-call pilot output or your row script's preview as the ASCII preview.

Strict format contract (blocking):

1. Use the exact four section headers: Assumptions, CSV Preview (ASCII), Credits + Scope + Cap, Approval Question.
2. If any required section is missing, remain in `AWAIT_APPROVAL` and do not run paid/cost-unknown actions.
3. Only transition to `FULL_RUN` after an explicit user confirmation to the approval question.
4. `run_javascript` is the non-AI path. `ai_inference` is for general classification/structured reasoning, and `deeplineagent` is for context gathering / web research / signal extraction.

Approval template:

```markdown
Assumptions

- <intent assumption 1>
- <intent assumption 2>

CSV Preview (ASCII)
<paste verbatim output from the one-row direct-call pilot>
Credits + Scope + Cap

- Provider: <name>
- Estimated credits: <value or range>
- Full-run scope: <rows/items>
- Spend cap: <cap>
- Pilot summary: <one short paragraph>

Approval Question
Approve full run?
```

### 4.4 Mandatory checkpoint

- Must run a real pilot on the exact CSV for full run (one exact input row, selected in the local script).
- Must include ASCII preview verbatim in approval.
- If pilot fails, fix and re-run until successful before asking for approval.
- Ask for approval in chat after the pilot. Include the row count, estimated credits, and a small ASCII preview so the user can approve or redirect without opening another surface.

### 4.5 Billing commands

```bash
deepline billing balance  # Show current credit balance
deepline billing usage    # Show recent billing activity and grouped recent usage
deepline billing limit    # Show the current monthly billing cap
```

When credits are zero or unavailable, stop paid work and ask whether the user
wants to add Deepline credits. If the balance or failure output includes a
`recovery` object, quote its `top_up_command` and `checkout_command` exactly,
including `--json` and `--no-open`; do not run them until the user approves.
Do not hardcode a USD-to-credit exchange rate in the skill. Use live billing,
pricing, or tool output when quoting credit costs.

## 5) Provider routing (high level)

**Reminder: you should have already read the relevant sub-doc from Section 2 before reaching this point. If you haven't, go back and read it now. This section is a quick-reference summary, NOT a substitute for the sub-docs.**

- **Search / discovery** → You MUST have [finding-companies-and-contacts.md](finding-companies-and-contacts.md) open. It contains the parallel execution patterns, provider filter schemas, and provider mix tables. Start with `deepline tools search <intent>` and execute field-matched provider calls in parallel; when the `deepline-list-builder` subagent is available, use subagent-based parallel search orchestration as the preferred pattern. Use `deeplineagent` only for synthesis or ambiguity resolution after the direct discovery path is exhausted.
- **Enrich / waterfall / coalesce** → You MUST have [enriching-and-researching.md](enriching-and-researching.md) open. It contains interim local-SDK routing, tool execution script patterns, waterfall column patterns, and coalescing logic. Do not restate provider contracts from memory; inspect live tool metadata before execution.
- **Custom signals / messaging** → Read [enriching-and-researching.md](enriching-and-researching.md) (custom signals section). Use `run_javascript` for deterministic transforms/template logic and `deeplineagent` for AI work. Start from `prompts.json`.
- **Verification** → `leadmagic_email_validation` first, then enrich corroboration.
- **LinkedIn scraping** -> Apify actors, by far the best. Use deepline tools describe apify_run_actor_sync to see the available actors or search for more.
- For phone recovery, read [enriching-and-researching.md](enriching-and-researching.md) and follow the notes/provider guidance there rather than relying on deleted numbered sections.

Provider path heuristics:

- Broad first pass: direct tool calls for high-volume discovery.
- Quality pass: AI-column orchestration with explicit retrieval instructions.
- For job-change recovery: prefer quality-first (`crustdata_person_enrichment`, `peopledatalabs_*`) before `leadmagic_*` fallbacks.
- Never treat one provider response as single-source truth for high-value outreach.

## 6) Additional notes

Critical: keep [writing-outreach.md](writing-outreach.md) workflow context active when running any sequence task. It is not optional for ICP-driven messaging.

### Apify actor flow (short canonical policy)

### Operational troubleshooting: rate limits and CLI health

- Interim local SDK mode: do not use row/play orchestration commands for heavy row-by-row work. Call SDK tools from a stateful script, and explicitly implement adaptive retries/backoff for 429s and transient upstream failures.
- If enrichment or CLI behavior is unstable, rerun the installer to ensure the latest CLI/client wiring is in place:

```bash
curl -s "https://code.deepline.com/api/v2/cli/install" | bash
```

**Sites requiring auth:** Don't use Apify. Tell the user to use Claude in Chrome or guide them through Inspect Element to get a curl command with headers (user is non-technical).

1. If user provides actor ID/name/URL: use it directly.
2. If not, search `deepline tools describe apify_run_actor_sync` for the actor id, or try deepline tools search.
3. If not present, run discovery search.
4. Avoid rental-priced actors.
5. For LinkedIn post scraping, prefer `supreme_coder/linkedin-post` for generic posts/search URLs and `harvestapi/linkedin-post-reactions` when the goal is engagers/reactions. Avoid `silentflow/linkedin-posts-scraper-ppr` and `alizarin_refrigerator-owner/linkedin-post-scraper` unless the user explicitly asks for them.
6. Pick high rating plus high usage/run count; when tied, choose best evidence-quality/price balance.
7. Honor `operatorNotes` over public ratings when conflicting.

```ts
await client.executeTool('apify_list_store_actors', {
  search: 'linkedin company employees scraper',
  sortBy: 'relevance',
  limit: 20,
});
await client.executeTool('apify_get_actor_input_schema', {
  actorId: 'bebity/linkedin-jobs-scraper',
});
```

## 7) Feedback & session sharing

### 7.1 Proactive issue reporting (mandatory)

Do not wait for the user to ask. If there is a meaningful failure, send feedback proactively using `deepline feedback send`.

Trigger when any of these happen:

- A provider/tool call fails repeatedly.
- Output is clearly wrong for the requested task.
- A CLI/runtime bug blocks completion.
- You needed a significant workaround to finish.

Run once per issue cluster (avoid spam), and include:

- workflow goal
- tool/provider/model used
- failure point and exact error details
- reproduction steps attempted

```bash
deepline feedback send "Goal: <goal>. Tool/provider/model: <details>. Failure: <what broke>. Error: <exact message>. Repro attempted: <steps>."
```

### 7.2 End-of-session consent gate (mandatory)

At the end of every completed run/session, ask exactly one Yes/No question:

`Would you like me to send this session activity to the Deepline team so they can improve the experience? (Yes/No)`

If user says:

- **Yes** -> run:
  ```bash
  deepline sessions send --current-session
  ```
- **No** -> do not send the session.

Ask once per completed run. Do not nag or re-ask unless the user starts a new run/session.
