---
name: gtm-meta-skill
description: |
  Use this skill for GTM workflows: prospecting, account/lead/contact enrichment, verification, scoring, personalization, outbound activation, and batch enrichment. Includes the local batch playground for Clay-style row-by-row execution.
  
  When to use:
  - Any GTM request involving prospecting, enrichment, or outbound list prep.
  - Any task asking for account, lead, or contact sheet creation with custom targeting/messaging data.
  - Any Clay-like or CSV batch enrichment request.
  - finding custom signals like ads, hiring, jobs, etc.
  
  Available providers:
  adyntel (9 actions), apify (9 actions), apollo (11 actions), crustdata (12 actions), deepline_native (9 actions), dropleads (8 actions), exa (8 actions), forager (10 actions), google_search (1 actions), heyreach (3 actions), hunter (8 actions), icypeas (14 actions), instantly (8 actions), leadmagic (12 actions), lemlist (26 actions), parallel (7 actions), peopledatalabs (11 actions), prospeo (7 actions), zerobounce (7 actions)
  
  Outcome: Produce precise account, lead, and contact sheets with unique GTM data for custom targeting and messaging.
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



## 2) Read behavior 

- Start with `SKILL.md`, then open only the relevant sub-doc.
- **Search / discovery** → [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md) (provider catalog, sample calls, Crust filter space, routing).
- **Enrich / waterfall / coalesce** → [enrich-waterfall.md](enrich-waterfall.md). Covers: when to use `deepline enrich` vs `tools execute`, when to use `call_ai` vs direct providers, coalescing parallel outputs with `run_javascript`, waterfall recipes.

has guidance for company -> contact, finding email, linkedins, signals, tech stack, etc, generally read if calling deepline enrich.
- **Per-row research** (funding, batch, tech stack, news) → `call_ai` inside enrich. See [enrich-waterfall.md](enrich-waterfall.md) "When to use call_ai" — no other sub-doc needed. **Haiku is the default when model is omitted.**
- **Custom signals / messaging** → [custom-signals.md](custom-signals.md) (signal buckets, prompts.json, guardrails). Haiku is the default for call_ai.
- **Qualification / sequence** → [qualification-and-email-design.md](qualification-and-email-design.md).
- Use grep/search for navigation, then read the exact sections needed to execute safely.

### 2.1 Tool search for signals/custom filters (mandatory)

For signal-driven discovery (investor, funding, hiring, headcount, industry, geo, tech stack, compliance), start with `deepline tools search "<simple_term>"`. Do not guess fields.

Use this loop:
1. Search 2-4 synonyms, execute in parallel

```bash
deepline tools search investor
deepline tools search investor --prefix crustdata
```

## 3) Core policy defaults

### 3.1 Definitions and defaults

Use [gtm-definitions-defaults.md](gtm-definitions-defaults.md) as the source of truth for GTM time windows, thresholds, and interpretation rules.

## Provider Playbooks

- [adyntel playbook](provider-playbooks/adyntel.md)
  Summary: Use channel-native ad endpoints first, then synthesize cross-channel insights. Keep domains normalized and remember Adyntel bills per request except free polling endpoints.
  Last reviewed: 2026-02-27

- [apify playbook](provider-playbooks/apify.md)
  Summary: Prefer sync run (`apify_run_actor_sync`) for actor execution. Use async run plus polling only when you need non-blocking execution. Known actorIds have typed input contracts.
  Last reviewed: 2026-02-11

- [apollo playbook](provider-playbooks/apollo.md)
  Summary: Cheap but mediocre quality people/company search with include_similar_titles=true unless strict mode is explicitly requested.
  Last reviewed: 2026-02-11

- [crustdata playbook](provider-playbooks/crustdata.md)
  Summary: Start with free autocomplete and default to fuzzy contains operators `(.)` for higher recall.
  Last reviewed: 2026-02-11

- [deepline_native playbook](provider-playbooks/deepline_native.md)
  Summary: Launcher actions wait for completion and return final payloads with job_id; finder actions remain available for explicit polling.
  Last reviewed: 2026-02-23

- [dropleads playbook](provider-playbooks/dropleads.md)
  Summary: Use Prime-DB search/count first to scope segments efficiently, then run finder/verifier steps only on shortlisted records.
  Last reviewed: 2026-02-26

- [exa playbook](provider-playbooks/exa.md)
  Summary: Use search/contents before answer for auditable retrieval, then synthesize with explicit citations.
  Last reviewed: 2026-02-11

- [forager playbook](provider-playbooks/forager.md)
  Summary: Use totals endpoints first (free) to estimate volume, then search/lookup with reveal flags for contacts. Strong for verified mobiles.
  Last reviewed: 2026-02-28

- [google_search playbook](provider-playbooks/google_search.md)
  Summary: Use Google Search for broad web recall, then follow up with extraction/enrichment tools for structured workflows.
  Last reviewed: 2026-02-12

- [heyreach playbook](provider-playbooks/heyreach.md)
  Summary: Resolve campaign IDs first, then batch inserts and confirm campaign stats after writes.
  Last reviewed: 2026-02-11

- [hunter playbook](provider-playbooks/hunter.md)
  Summary: Use discover for free ICP shaping first, then domain/email finder for credit-efficient contact discovery, and verifier as the final send gate.
  Last reviewed: 2026-02-24

- [icypeas playbook](provider-playbooks/icypeas.md)
  Summary: Use email-search for individual email discovery, bulk-search for volume. Scrape LinkedIn profiles for enrichment. Find-people for prospecting with 16 filters. Count endpoints are free.
  Last reviewed: 2026-02-28

- [instantly playbook](provider-playbooks/instantly.md)
  Summary: List campaigns first, then add contacts in controlled batches and verify downstream stats.
  Last reviewed: 2026-02-11

- [leadmagic playbook](provider-playbooks/leadmagic.md)
  Summary: Treat validation as gatekeeper and run email-pattern waterfalls before escalating to deeper enrichment.
  Last reviewed: 2026-02-11

- [lemlist playbook](provider-playbooks/lemlist.md)
  Summary: List campaign inventory first and push contacts in small batches with post-write stat checks.
  Last reviewed: 2026-03-01

- [parallel playbook](provider-playbooks/parallel.md)
  Summary: Prefer run-task/search/extract primitives and avoid monitor/stream complexity for agent workflows.
  Last reviewed: 2026-02-11

- [peopledatalabs playbook](provider-playbooks/peopledatalabs.md)
  Summary: Use clean/autocomplete helpers to normalize input before costly person/company search and enrich calls.
  Last reviewed: 2026-02-11

- [prospeo playbook](provider-playbooks/prospeo.md)
  Summary: Use enrich-person for individual contacts (replaces deprecated email-finder), linkedin-email-finder for LinkedIn-sourced emails, search-person for prospecting with 30+ filters.
  Last reviewed: 2026-02-28

- [zerobounce playbook](provider-playbooks/zerobounce.md)
  Summary: Use as final email validation gate before outbound sends. Check sub_status for granular failure reasons. Use batch for 5+ emails.
  Last reviewed: 2026-02-28

- Apply defaults when user input is absent.
- User-specified values always override defaults.
- In approval messages, list active defaults as assumptions.

### 3.2 Output policy: Playground-first for CSV

- Always use `deepline enrich` for list enrichment or discovery at scale (>5 rows). It auto-opens the Playground sheet so you can inspect rows, re-run blocks, and iterate.
- Even for company → ICP person flows, enrich works: search and filter as part of the process, with providers like Apify to guide.
- Even when you don't have a CSV, create one and use deepline enrich.
- This process requires iteration; one-shotting via `deepline tools execute` is short sighted.
- Before running any Deepline execution command (`deepline enrich`, `deepline tools execute`, `deepline csv --execute_cells`), run `deepline backend start` first in the same session.
- If backend state is unclear, run `deepline backend status --json` and only continue execution when backend is running/healthy.
- If a command created CSV outside enrich, run `deepline backend start` and optionally `deepline csv render --csv <csv_path> --open`; when automating this, manage backend/csv render as separate hook steps and stop them explicitly (`deepline backend stop --just-backend`, then `deepline csv render stop` if needed).
- When execution work is complete, stop backend explicitly with `deepline backend stop --just-backend` unless the user asked to keep it running.
- In chat, send the file path + playground status, not pasted CSV rows, unless explicitly requested.
- Preserve lineage columns (especially `_metadata`) end-to-end. When rebuilding intermediate CSVs with shell tools, carry forward `_metadata` columns.
- Never enrich a user-provided or source CSV in-place. Use `--output` to write to your working directory on the first pass, then `--in-place` on that output for subsequent passes. `--in-place` is for iterating on your own prior outputs — never on source files.
- For reruns, keep successful existing cells by default; use `--with-force <alias>` only for targeted recompute.

See [enrich-waterfall.md](enrich-waterfall.md) for `deepline csv` commands, waterfall recipes, and inspection details.

### 3.3 Final file + playground check (light)

- Keep one intended final CSV path: `FINAL_CSV="${OUTPUT_DIR:-/tmp}/<requested_filename>.csv"`
- Before finishing: Run `deepline csv show --csv "$FINAL_CSV" --summary` and confirm output columns are populated.
- In the final message, always report: exact `FINAL_CSV` and exact Playground URL.

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
deepline billing balance --json
deepline billing limit --json
```

When credits at zero, link to https://code.deepline.com/dashboard/billing to top up.

## 5) Provider routing (high level)

- **Search / discovery** → [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md). Start with `deepline tools search <simple_term>` and execute field-matched provider calls in parallel; when the `deepline-list-builder` subagent is available, use subagent-based parallel search orchestration as the preferred pattern. Use `call_ai` for synthesis/fallback, not as the only first step.
- **Enrich / waterfall / coalesce** → [enrich-waterfall.md](enrich-waterfall.md). Use waterfalls when possible; coalesce parallel provider outputs with `run_javascript`. Default waterfall order: hunter → apollo → leadmagic → deepline_native → crustdata → peopledatalabs.
- **Paid-media signaling** → when checking ad presence, run `leadmagic_b2b_ads_search` and `adyntel_facebook_ad_search` as parallel paid-media paths.
- **Custom signals / messaging** → [custom-signals.md](custom-signals.md). Use `call_ai*`; start from `prompts.json`.
- **Verification** → `leadmagic_email_validation` first, then enrich corroboration.
- **LinkedIn scraping** → Apify actors, by far the best.

Provider path heuristics:
- Broad first pass: direct tool calls for high-volume discovery.
- Quality pass: AI-column orchestration with explicit retrieval instructions.
- For job-change recovery: prefer quality-first (`crustdata_person_enrichment`, `peopledatalabs_*`) before `leadmagic_*` fallbacks.
- Never treat one provider response as single-source truth for high-value outreach.

## 6) Advanced references

| Doc | Use when |
|-----|----------|
| [searching-for-leads-accounts-and-building-lead-lists.md](searching-for-leads-accounts-and-building-lead-lists.md) | Search, discovery, provider sample calls, Crust filter space |
| [enrich-waterfall.md](enrich-waterfall.md) | Enrich vs tools execute, call_ai vs direct providers, coalescing, waterfalls |
| [custom-signals.md](custom-signals.md) | Custom signals, `call_ai`, prompts.json |
| [qualification-and-email-design.md](qualification-and-email-design.md) | Qualification, 4-step sequence, ICP-driven messaging |
| [playground-guide.md](playground-guide.md) | Playground workflow, `deepline csv` commands |
| [actor-contracts.md](actor-contracts.md) | Apify input/output contracts |
| [gtm-definitions-defaults.md](gtm-definitions-defaults.md) | Time windows, thresholds, interpretation rules |
| `prompts.json` | Full `call_ai` template catalog — use for exact titles when building custom signals |

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
deepline tools execute apify_list_store_actors --payload '{"search":"linkedin company employees scraper","sortBy":"relevance","limit":20}' --json
deepline tools execute apify_get_actor_input_schema --payload '{"actorId":"bebity/linkedin-jobs-scraper"}' --json
```

## 7) Feedback & session sharing

When an agent runs into Deepline CLI issues (errors, degraded behavior, or repeated failure to complete the workflow), the agent should send feedback by default:

1. **Always send a text feedback report** — this should happen even without a separate user request.

```bash
deepline provide-feedback "What happened, what was expected, repro steps, tool/provider involved."
```

The feedback text must include enough detail for reproduction and debugging:
- workflow goal (what was trying to be achieved)
- commands attempted (in order)
- key payloads/inputs attempted (redact secrets)
- expected behavior vs actual behavior
- exact error output or failure symptoms
- tool/provider/model/context used

2. **Only send the current session with user permission** — session upload can contain broader context and should remain user-approved.

```bash
deepline session send --current-session
```
