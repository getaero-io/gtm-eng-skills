---
name: gtm-meta-skill
description: "Use this skill for GTM prospecting, enrichment, qualification, and outbound workflows, especially when users mention Deepline, CSV processing, lead/account/contact research, waterfall enrichment, email or LinkedIn lookup, personalization, scoring, or campaign activation. Route CSV-heavy and provider-driven requests through this skill, then rely on linked sub-docs and provider playbooks for execution details. Available providers: adyntel, apify, apollo, crustdata, deepline_native, dropleads, exa, forager, google_search, heyreach, hunter, icypeas, instantly, leadmagic, lemlist, parallel, peopledatalabs, prospeo, zerobounce."
---

# GTM Meta Skill

Use this skill for prospecting, account research, contact enrichment, verification, lead scoring, personalization, and campaign activation.

## 1) What this skill governs

- Route GTM decisions, safety gates, and provider/quality defaults before execution.
- Keep long command chains and tooling nuance in sub-docs; provider-specific implementation detail in `provider-playbooks/*.md`.
- Provide clear entry points for both paid and non-paid workflows, including `--rows 0:1` pilots.

## Process/goal

Customer is generally trying to go from "I have an ICP" to "Here's a list of prospects with email/linkedin and very personalized content or signals". They may be anywhere in this process, but guide them along.

### When ICP context matters (and when it doesn't)

ICP context is required for:
- Prospecting from scratch / choosing who to target
- Persona selection and qualification
- Custom signal discovery and personalized messaging (`call_ai` columns)
- LinkedIn lookup when you don't have enough identifying info (title, company, geo) — ICP persona titles become your search filter


For these: if they have an ICP.md somewhere in this repository (context/), read it; else guide them to create one or just give you base context of who they are (e.g. getting the customers domain is super high value, you can scrape their site and understand them).

ICP is NOT required for mechanical tasks — do not ask for it, do not raise it as an objection:
- Enriching an existing CSV with a specific field (email, phone, LinkedIn when identifiers are strong)
- Validating email addresses
- Scraping profiles from known URLs
- Running a waterfall on a known column
- Any task where the user already picked their targets and is asking for a specific enrichment type

**Heuristic**: if the user hands you a CSV and asks for a concrete field, just execute. ICP becomes required when the agent has to *choose who to target*, *craft what to say*, or *disambiguate a weak lookup*.

### Documentation hierarchy

- Level 1 (`SKILL.md`): decision model, guardrails, approval gates, links to sub-docs.
- Level 2 (task-specific): [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md), [enrich-waterfall.md](enrich-waterfall.md), [custom-signals.md](custom-signals.md), [qualification-and-email-design.md](qualification-and-email-design.md), [playground-guide.md](playground-guide.md), [actor-contracts.md](actor-contracts.md), [gtm-definitions-defaults.md](gtm-definitions-defaults.md), `prompts.json`.
- Level 3 (`provider-playbooks/*.md`): provider-specific quirks, cost/quality notes, and fallback behavior.

No-loss rule: moved guidance remains fully documented at its canonical level and is linked from here.



## 2) Read behavior — MANDATORY before any execution

**STOP. Do not call any provider, run any `deepline tools execute`, or write any search command until you have opened the correct sub-doc for your task.** SKILL.md is the routing layer — it tells you WHERE to go, not HOW to execute. The sub-docs contain provider schemas, filter syntax, parallel execution patterns, and validated sample payloads. Without them you will guess parameters, pick wrong providers, run searches sequentially instead of in parallel, and produce garbage results. This has happened repeatedly.

### Step 1: Check task-specific skills FIRST

If the task matches a pattern below, invoke that skill (via `/skill-name`) **before** opening any sub-doc. These skills contain battle-tested, end-to-end playbooks that override general provider guidance. Using them saves 5-10 tool calls and avoids known pitfalls.

| Task pattern | Skill to invoke | Why — what goes wrong without it |
|---|---|---|
| YC / investor-portfolio / accelerator-backed company prospecting | `/investor-company-prospecting` | VC portfolio data is public and free. Without this skill you'll burn credits on Crustdata investor filters that return inconsistent results. |
| Build TAM from ICP filters | `/build-tam` | Dropleads-first people mapping with proper filter syntax. Without it you'll guess Dropleads/Crustdata field names and get empty results. |
| Find contacts at known companies | `/get-leads-at-company` | Company → contact → outreach chain with dedup. Without it you'll forget validation, scrape wrong profiles, and miss the seniority filter pattern. |
| Find/verify emails for contacts | `/contact-to-email` | Multi-workflow email enrichment with proper waterfall order and validation gates. Without it you'll skip verification and deliver bouncy emails. |
| Resolve LinkedIn URLs | `/linkedin-url-lookup` | Multi-pass waterfall with Apify validation to handle nicknames and false positives. Without it you'll get 54% false positive rate. |

**If a task-specific skill matches, its guidance takes priority over everything below.**

### Step 2: If no skill matched, open the right sub-doc BEFORE executing

**This is not optional.** Read the matching sub-doc. Do not skip this step. Do not "just try Apollo real quick" or "just run one search to see." The sub-docs contain the exact provider filter schemas, parallel execution patterns, canonical sample payloads, and known pitfalls. Every time an agent skips the sub-doc, it guesses field names, picks one provider instead of fanning out in parallel, runs searches sequentially, and delivers worse results while burning more credits.

**Routing rules — match your task to a doc and READ IT:**

| When the task involves... | You MUST read this doc first | What it gives you (that SKILL.md doesn't) | What goes wrong if you skip it |
|---|---|---|---|
| **Finding companies, finding people, building lead lists, company search, people search, prospecting, "find me X companies that Y"** | [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md) | Exact provider filter schemas (Crustdata operators, Apollo fields, Exa query patterns, Dropleads pagination). Parallel execution patterns — run 3-5 providers simultaneously. Provider mix tables by objective. Role-based search rules (never use exact job titles). Multi-step seed→refine→validate flow for hard queries. Subagent orchestration for fan-out. | You'll pick one provider, run it alone, guess field names, use exact job titles (which return 0 results for small companies), skip dedup, and deliver a weak single-source list. This is the #1 failure mode. |
| **Enriching a CSV, adding columns, waterfall enrichment, finding emails/phones/LinkedIn for existing contacts, coalescing data, `deepline enrich` usage** | [enrich-waterfall.md](enrich-waterfall.md) | `deepline enrich` command syntax and all flags. Waterfall column patterns with fallback chains. `call_ai` / `run_javascript` column types. Coalescing patterns for merging provider outputs. Email/phone/LinkedIn waterfall orders. Pre-flight and post-run inspection scripts. | You'll write ad-hoc shell scripts instead of using `deepline enrich`, lose lineage (`_metadata`), skip coalescing, and produce CSVs that can't be iterated on in Playground. |
| **Writing cold emails, rewriting email copy, personalizing outreach, lead scoring, qualification, sequence design, campaign copy** | [qualification-and-email-design.md](qualification-and-email-design.md) | Prompt templates from `prompts.json`. Scoring rubrics. Email length/tone/structure rules. Personalization patterns using company signals. Qualification frameworks. Sequence timing. | You'll write generic emails without signal-based personalization, skip qualification, and produce copy that sounds like every other AI-generated outreach. |
| **Custom signal extraction (tech stack, hiring signals, funding news, competitive intel), research columns** | [custom-signals.md](custom-signals.md) | `call_ai` prompt patterns for signal extraction. `prompts.json` templates. Provider-to-signal mapping (which providers give which signals). Signal scoring patterns. | You'll use `call_ai` with vague prompts, miss provider-native signals that are cheaper and more reliable, and produce inconsistent signal columns. |
| **Inspecting CSVs, debugging Playground, iterating on enrichment results, `deepline csv` commands** | [playground-guide.md](playground-guide.md) | `deepline csv show` / `deepline csv --render-as-playground` commands. Playground iteration workflows. Cell-level re-execution. Debug patterns for failed cells. | You'll read CSVs into context (killing your context window), paste raw rows to the user, and miss the Playground-first output policy. |
| **Scraping LinkedIn/websites with Apify, choosing actors, structuring actor inputs** | [actor-contracts.md](actor-contracts.md) | Known actor IDs with typed input contracts. Cost/quality notes. Actor selection heuristics. Input schema patterns. | You'll run discovery searches for actors that are already documented, pick rental-priced actors, and guess input schemas that fail silently. |
| **Interpreting GTM defaults — time windows, thresholds, recency, freshness** | [gtm-definitions-defaults.md](gtm-definitions-defaults.md) | Canonical definitions for "recent" (90 days), "actively hiring" (3+ jobs posted in 30 days), stale data thresholds, recency windows. | You'll use inconsistent definitions across the session, interpret "recent funding" as 5 years ago, and apply no time bounds to searches. |

### Data

- When the user hands you a CSV, run `deepline csv show --csv <path> --summary` first to understand its shape (row count, columns, sample values) before deciding how to process it.
- **NEVER read a large CSV into context with the Read tool.** Reading CSV rows into the conversation window exhausts context and produces zero output. This is the single most common failure mode.
- Use `deepline enrich` for any row-by-row processing (enrichment, rewriting, research, scoring).
- To explore or understand CSV content without loading it, use `deepline csv show --csv <path> --rows 0:2` for a sample, or spawn an Explore subagent to answer questions about the data.

### Tools

For signal-driven discovery (investor, funding, hiring, headcount, industry, geo, tech stack, compliance), start with `deepline tools search "<intent>"`. Do not guess fields.

Search 2-4 synonyms, execute in parallel:

```bash
deepline tools search investor
deepline tools search investor --prefix crustdata
```

## 3) Core policy defaults

### 3.1 Definitions and defaults

Use [gtm-definitions-defaults.md](gtm-definitions-defaults.md) as the source of truth for GTM time windows, thresholds, and interpretation rules.

{provider_guidance_interpolated}

- Apply defaults when user input is absent.
- User-specified values always override defaults.
- In approval messages, list active defaults as assumptions.

### 3.2 Output policy: Playground-first for CSV

- Always use `deepline enrich` for list enrichment or discovery at scale (>5 rows). It auto-opens the Playground sheet so you can inspect rows, re-run blocks, and iterate.
- Even for company → ICP person flows, enrich works: search and filter as part of the process, with providers like Apify to guide.
- Even when you don't have a CSV, create one and use deepline enrich.
- This process requires iteration; one-shotting via `deepline tools execute` is short sighted.
- If backend state is unclear, run `deepline backend status` and only continue execution when backend is running/healthy.
- If a command created CSV outside enrich, run `deepline csv --render-as-playground start --csv <csv_path> --open`.
- When execution work is complete, stop backend explicitly with `deepline backend stop --just-backend` unless the user asked to keep it running.
- In chat, send the file path + playground status, not pasted CSV rows, unless explicitly requested.
- Preserve lineage columns (especially `_metadata`) end-to-end. When rebuilding intermediate CSVs with shell tools, carry forward `_metadata` columns.
- Never enrich a user-provided or source CSV in-place. Use `--output` to write to your working directory on the first pass, then `--in-place` on that output for subsequent passes. `--in-place` is for iterating on your own prior outputs — never on source files.
- For reruns, keep successful existing cells by default; use `--with-force <alias>` only for targeted recompute.

See [enrich-waterfall.md](enrich-waterfall.md) for `deepline csv` commands, pre-flight/post-run script templates, and inspection details.

### 3.3 Final file + playground check (light)

- Keep one intended final CSV path: `FINAL_CSV="${OUTPUT_DIR:-/tmp}/<requested_filename>.csv"`
- Before finishing: use the post-run inspection script pattern from [enrich-waterfall.md](enrich-waterfall.md). Run it once instead of separate checks.
- In the final message, always report: exact `FINAL_CSV` and exact Playground URL.
- Before closing the session, follow the Section 7 consent step for session sharing.

## 4) Credit and approval gate (paid actions)

### 4.1 Required run order

1. Pilot on a narrow scope (example `--rows 0:1`).
2. Request explicit approval.
3. Run full scope only after approval.

### 4.2 Execution sizing

- Use smaller sequential commands first.
- Keep limits low and windows bounded before scaling.
- For TAM sizing, a great hack is to keep limits at 1 and most providers will return # of total possible matches but you only get charged for 1.
- Do not depend on monthly caps as a hard risk control.

### 4.3 Approval message content

Include all of:

1. Provider(s)
2. Pilot summary and observed behavior
3. Intent-level assumptions (3–5 one-line bullets)
4. CSV preview from a real `deepline enrich --rows 0:1` pilot
5. Credits estimate / range
6. Full-run scope size
7. Max spend cap
8. Approval question: `Approve full run?`

Note: `deepline enrich` already prints the ASCII preview by default, so use that output directly.

Strict format contract (blocking):

1. Use the exact four section headers: Assumptions, CSV Preview (ASCII), Credits + Scope + Cap, Approval Question.
2. If any required section is missing, remain in `AWAIT_APPROVAL` and do not run paid/cost-unknown actions.
3. Only transition to `FULL_RUN` after an explicit user confirmation to the approval question.

Approval template:

```markdown
Assumptions
- <intent assumption 1>
- <intent assumption 2>

CSV Preview (ASCII)
<paste verbatim output from deepline enrich --rows 0:1>

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

- Must run a real pilot on the exact CSV for full run (`--rows 0:1`).
- Must include ASCII preview verbatim in approval.
- If pilot fails, fix and re-run until successful before asking for approval.

### 4.5 Billing commands


```bash
deepline billing balance
deepline billing limit
```

When credits at zero, link to https://code.deepline.com/dashboard/billing to top up.

## 5) Provider routing (high level)

**Reminder: you should have already read the relevant sub-doc from Section 2 before reaching this point. If you haven't, go back and read it now. This section is a quick-reference summary, NOT a substitute for the sub-docs.**

- **Search / discovery** → You MUST have [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md) open. It contains the parallel execution patterns, provider filter schemas, and provider mix tables. Start with `deepline tools search <intent>` and execute field-matched provider calls in parallel; when the `deepline-list-builder` subagent is available, use subagent-based parallel search orchestration as the preferred pattern. Use `call_ai` for synthesis/fallback, not as the only first step.
- **Enrich / waterfall / coalesce** → You MUST have [enrich-waterfall.md](enrich-waterfall.md) open. It contains `deepline enrich` syntax, waterfall column patterns, and coalescing logic. Default waterfall order: dropleads → hunter → leadmagic → deepline_native → crustdata → peopledatalabs.
- **Custom signals / messaging** → Read [custom-signals.md](custom-signals.md). Use `call_ai*`; start from `prompts.json`.
- **Verification** → `leadmagic_email_validation` first, then enrich corroboration.
- **LinkedIn scraping** → Apify actors, by far the best. Read [actor-contracts.md](actor-contracts.md) for known actor IDs.
- For phone recovery, read [enrich-waterfall.md](enrich-waterfall.md) section 8.8 (Forager reverse lookup + `deepline_native_enrich_phone` fallback).

Provider path heuristics:
- Broad first pass: direct tool calls for high-volume discovery.
- Quality pass: AI-column orchestration with explicit retrieval instructions.
- For job-change recovery: prefer quality-first (`crustdata_person_enrichment`, `peopledatalabs_*`) before `leadmagic_*` fallbacks.
- Never treat one provider response as single-source truth for high-value outreach.

## 6) Additional notes

Critical: keep qualification-and-email-design workflow context active when running any sequence task. It is not optional for ICP-driven messaging.

For sequence and qualification-heavy use cases, open both: [qualification-and-email-design.md](qualification-and-email-design.md), [playground-guide.md](playground-guide.md).

### Apify actor flow (short canonical policy)

**Sites requiring auth:** Don't use Apify. Tell the user to use Claude in Chrome or guide them through Inspect Element to get a curl command with headers (user is non-technical).

1. If user provides actor ID/name/URL: use it directly.
2. If not, use actor-contracts.md to find the actor id, or try deepline tools search. 
3. If not present, run discovery search.
4. Avoid rental-priced actors.
5. Pick value-over-quality-fit; when tied, choose best evidence-quality/price balance.
6. Honor `operatorNotes` over public ratings when conflicting.

```bash
deepline tools execute apify_list_store_actors --payload '{"search":"linkedin company employees scraper","sortBy":"relevance","limit":20}'
deepline tools execute apify_get_actor_input_schema --payload '{"actorId":"bebity/linkedin-jobs-scraper"}'
```

## 7) Feedback & session sharing

### 7.1 Proactive issue reporting (mandatory)

Do not wait for the user to ask. If there is a meaningful failure, send feedback proactively using `deepline provide-feedback`.

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
deepline provide-feedback "Goal: <goal>. Tool/provider/model: <details>. Failure: <what broke>. Error: <exact message>. Repro attempted: <steps>."
```

### 7.2 End-of-session consent gate (mandatory)

At the end of every completed run/session, ask exactly one Yes/No question:

`Would you like me to send this session activity to the Deepline team so they can improve the experience? (Yes/No)`

If user says:
- **Yes** -> run:
  ```bash
  deepline session send --current-session
  ```
- **No** -> do not send the session.

Ask once per completed run. Do not nag or re-ask unless the user starts a new run/session.
