---
name: deepline-sdk
description: 'Use for Deepline SDK/CLI V2 GTM work: route, build, run, debug, and export durable plays; find companies or contacts; enrich email, phone, LinkedIn, or custom signals; migrate Clay-like tables; configure cron/webhook/API plays; control Deepline spend; and recover from play/tool shape failures. Triggers on deepline CLI work, CSV enrichment, prospecting, waterfalls, outbound lists, provider routing, play authoring, SDK V2 syntax, staleAfterSeconds, datasets, and eval-style GTM tasks.'
---

# Deepline SDK Dense V3 Bootstrap
Deepline GTM work is paid uncertainty reduction. The play is the notebook, stable ids are the cache, datasets are durable row state, getters are the interface, and CSV is only an input/output boundary. Build a route-shaped V2 play, not a pile of console probes.

This is a multi-file skill suite: `SKILL.md` is the router, and `references/` holds job-to-be-done docs.

Names in this skill are starting hints. The CLI is the source of truth: search, describe, check, then run. Preserve useful alpha as categories, contracts, failure modes, and gates rather than stale provider syntax.

**Failure Modes**
- **Console archaeology:** direct provider calls produce useful rows, then the agent hand-builds CSVs from rendered output. Guard: use direct prebuilt export when it fits; otherwise put composed work in a `.play.ts` with stable ids.
- **Route replacement:** a `company-people-email` task silently becomes raw people search. Guard: preserve start entity and stage order; write the mismatch before changing route.
- **Dataset-backed child loop:** `ctx.runPlay` tries to call a prebuilt that owns `ctx.dataset()` state. Guard: if `plays check` reports direct-run/dataset-backed, run/export it as a boundary or copy the underlying described contract.
- **Getter archaeology:** code reads `result.result.*`, raw payload guesses, or optional chains instead of declared getters. Guard: `tools describe` owns `extractedValues.*.get()` and `extractedLists.*.get()`.
- **Healthcare/vertical drift:** provider `industry` says "Healthcare" but no user-facing category/evidence column exists. Guard: add `<vertical>_category` or `category` early and keep fit evidence through export.
- **People-before-account:** contact tasks for an ICP start with broad people search. Guard: source and fit domains first when account/category/portfolio/vertical matters.
- **Fanout surprise:** a small final CSV buys hundreds of people/email calls. Guard: cap source rows and people/account before row-level paid work; estimate before scale.
- **Stale cell reuse:** changing filter/getter/export logic does not rerun because persisted cells reused old values. Guard: change the affected column id or `staleAfterSeconds`.
- **Replay corruption:** play bodies use `Date.now()`, `Math.random()`, local `fs`, raw `fetch`, env reads, or shell files. Guard: use `ctx.step`, `ctx.fetch`, `ctx.csv`, `ctx.tools.execute`, `ctx.runPlay`, `ctx.secrets`.
- **Validation as discovery:** validators are used to find channels. Guard: recover email/phone first, validate second, and skip nulls.

**Operating Loop**
1. **Preflight:** run compact health/auth/balance checks once at the start. Use one command group only when shell syntax is allowed by the user/eval; otherwise run the three commands back-to-back without analysis loops.
2. **Route:** search/describe plays before tools. Mark route `candidate`, `confirmed`, or `rejected`.
3. **Load domain alpha:** for company/contact/TAM/portfolio/lead-list asks, open the repo file `.skills/deepline-gtm/finding-companies-and-contacts.md` (in this repo: `/Users/ctoprani/src/deepline-api/.skills/deepline-gtm/finding-companies-and-contacts.md`); for TAM, also open `.skills/deepline-gtm/recipes/build-tam.md`. Do not guess sibling docs under the installed dense skill path.
4. **Bootstrap middle path:** for durable deliverables, prefer `plays bootstrap` when the task involves CSV mapping, provider source rows, company->people->channel, multiple stages, row-level gates, custom output columns, or eval-style CSV export. Bootstrap wraps prebuilts; it is not anti-prebuilt.
5. **Direct only when perfect:** run a prebuilt directly only when `plays describe` already covers start entity, inputs, filters, output, and export with no mapping/custom stage needed.
6. **Scratchpad by scaffold:** create the local V2 play through bootstrap whenever a route family fits. Hand-author only when bootstrap cannot express the start entity, bridge, or output shape.
7. **Pilot:** run `plays check` on custom/local plays before `plays run`. For prebuilts, `plays describe` is the contract check; if you cloned/bootstrapped or edited a file, `plays check <file>` is mandatory. Then run a watched 1-3 row pilot and export/inspect the pilot rows.
8. **Economic gate:** cap rows, people/account, fallback legs, and spend before paid fanout. Prefer result-priced or `post_deduct` tools when coverage is uncertain; avoid per-attempt/request/page tools for exploratory fanout unless their quality advantage is clear in the pilot.
9. **Scale:** show route, pilot result, fanout estimate, stop conditions, and Deepline-visible price. Ask if cost is unknown or beyond pilot.
10. **Export:** flat user-facing columns with evidence, source, status, and miss_reason. Do not ship nested provider objects.
11. **Repair by class:** route, contract, getter, row key, credentials, infra callback, timeout. After two same-class failures, change branch or export partials with miss reasons.

Run one Deepline command at a time when you need its output. Do not add `jq`, `head`, `tail`, grep, Python parsing, shell redirection, `curl`, env spelunking, or background jobs around Deepline commands. JSON output is for reading directly.

**Scratchpad and Durable Execution**
The scratchpad is not notes. It is the local `.play.ts` file that turns composed paid provider calls into durable checkpoints. Prefer creating it with `plays bootstrap` so the play preserves route family, start entity, stage order, getters, and child prebuilt calls.

Do not hand-author a scratchpad just because output matters. If direct prebuilt is perfect, run/export it. If anything needs mapping, joining, row gates, staged company->people->email, or custom projection, bootstrap the route family and edit the generated TODOs.

Durable execution means reruns should reuse expensive work while cheap logic evolves:

- `ctx.tools.execute` checkpoints provider calls by stable `id`.
- `ctx.runPlay` checkpoints reusable child workflows by stable key.
- `ctx.dataset(...).withColumn(...)` checkpoints row-level work and isolates row failures.
- `ctx.step` checkpoints pure or bounded deterministic work.
- `staleAfterSeconds` refreshes data intentionally instead of accidentally rebuying or reusing forever.

1. Put the first useful source/enrichment probe into the play with the exact payload that worked.
2. Keep source/enrichment ids stable while changing downstream scoring, getters, filters, null handling, and export columns.
3. Rename an id only when intentionally refreshing wrong/stale provider data or changed column semantics.
4. Return datasets, not loose arrays, when the output must become a CSV or inspectable table.
5. Add receipt columns while iterating: `source`, `status`, `miss_reason`, evidence, and getter/source names.

If deleting the play would delete what you learned about custom provider composition, row-level fallbacks, joins, cost gates, or misses, the work belongs in the scratchpad. Otherwise keep the prebuilt/direct route sticky.

**Iterative Build Order**
Build in layers. Do not jump from route selection to a 100-row paid fanout.

1. **Static skeleton:** write `definePlay`, typed input, bindings/billing cap, helper functions, and final output column names.
2. **Tiny source:** add one source call or 2-3 inline rows. Prove `plays check` and watched run.
3. **Normalize:** add pure columns for domain, name, category, persona terms, row key, and requested export names.
4. **Fit gate:** add cheap evidence/status/miss columns. Slice to pilot rows before any mapped paid enrichment.
5. **One enrichment leg:** add one described provider or child play for one row-level field. Prove getter and null semantics.
6. **Fallback/validation:** add fallback legs only behind `runIf`/null gates. Validate recovered channels as a later stage.
7. **Projection:** add flat export columns; remove nested raw provider objects.
8. **Scale:** only after row progress, coverage, errors, and fanout are understood.

```text
Pilot must show:
- rows processed > 0 in the mapped dataset
- required export columns present
- representative non-null values for the core deliverable, or explicit miss_reason
- no repeated same-class runtime failure
- estimated paid calls = source rows * people/account * fallback legs
- billing shape favors hits/results over attempts where possible
```

For hard company-contact asks, run 1-3 and 5-10 row pilots before full scale. If the pilot has empty contact_name/title/LinkedIn coverage, or the requested identity field is only present under a different alias, do not scale the same route yet: export/inspect pilot rows, normalize aliases, change contact/person route, or mark the route rejected. Email can be sparse; missing title/contact identity is a route failure.

**Situation-to-Play Routing**
Classify the starting entity and requested output before choosing a play.

| Situation | First route | Customize when | Main risk |
| --- | --- | --- | --- |
| Find ICP/company list by funding/headcount/HQ/category/hiring | Describe/run structured company discovery prebuilt; bootstrap `company-list` if needed. | Category evidence, hiring definition, source, or geography differs. | People search before company fit. |
| Contacts at known companies | Company-to-contact play; bootstrap `company-people` for CSV/account rows. | Persona ranking or row-specific role mapping needed. | Exact-title filters miss adjacent titles. |
| Find companies then contacts | Company play first, then contact play; bootstrap `company-people`. | Single scratchpad/pilot desired. | Enriching people before account quality is proven. |
| Existing people rows to email | `people-email` with described name/domain or LinkedIn email play. | Custom validation, provider order, or mixed identifiers. | Calling finders without enough identity. |
| Existing people rows to phone | `people-phone` or described person-to-phone play. | Country/channel filters needed. | Phone lookup without LinkedIn/email anchor. |
| Companies to contacts plus email/phone | `company-people-email` or `company-people-phone`. | Account-grain slots, channel fallback, export projection. | Losing account grain when one row/company was requested. |
| Name + company to LinkedIn | Person-to-LinkedIn prebuilt or Serper -> Apify validation pattern. | Strict nickname/current-employer/location gates. | Using reverse profile enrichment as search. |
| Portfolio/investor/accelerator companies | Extract official/source list first, then enrich. | Source is incomplete; add supplement branch after dedupe. | Reconstructing source lineage from generic search. |
| Niche signals | Won/lost -> source discovery -> cited signals -> score/lift -> net-new prospects. | Need multi-table evidence and prospect outputs. | Generic company search with no citation/lift gate. |
| Clay-like table | V2 play with `ctx.csv`, dataset stages, and original dependency graph. | Add cron/webhook/API only if original table had triggers/pushes. | Preserving cell mechanics instead of business dependencies. |
| Cron/webhook/API automation | `definePlay(name, fn, bindings)` with trigger bindings. | Add child plays after tiny trigger play works. | Debugging trigger auth, providers, side effects together. |

Routing protocol:

1. `deepline plays search "<job words>" --json` or `--compact`.
2. `deepline plays describe prebuilt/<candidate> --json`.
3. If the deliverable is one-stage and exact, direct-run the prebuilt.
4. Otherwise bootstrap the nearest route family with concrete `--from` and confirmed stage refs, then edit TODO mappings.
5. If bootstrap cannot express start entity, bridge, or stage order, record the mismatch, then direct-run/export the nearest prebuilt or hand-author the missing wrapper.
6. Export with `deepline runs export <run-id> --dataset result.rows --out file.csv` when a dataset path is needed. Do not add `--format`; inspect `runs export --help` if unsure.

Route families: `people-list`, `company-list`, `people-email`, `people-phone`, `company-people`, `company-people-email`, `company-people-phone`.

Bootstrap ratchet:

- Rows/CSV -> email/phone/LinkedIn/job-change: bootstrap a row route unless a published batch prebuilt already does the whole CSV contract.
- Company list only: direct structured-company prebuilt is fine only if it preserves requested evidence columns. Bootstrap `company-list` when filters, source, fit evidence, hiring evidence, or export columns need edits.
- Companies -> contacts -> email/phone: bootstrap `company-people-email` or `company-people-phone`; do not stitch by shell.
- Provider-source search -> enrichment: bootstrap from `provider:<tool-id>` so source shape, getters, and row keys live in a play.
- If bootstrap flag syntax fails, run `deepline plays bootstrap --help` or the route help, then retry with explicit stage flags (`--people`, `--email`, `--phone`) instead of abandoning bootstrap.
- Infra failures are not route failures. `workers_edge` scheduler 503, callback failure, receipt lock, timeout, and persistence failure mean inspect/retry/export; they do not justify raw provider loops.

Bootstrap examples after refs are confirmed. Bootstrap can wrap prebuilts with `play:prebuilt/...` or ordered finder tools with `providers:...`.

```bash
deepline plays bootstrap people-email --from csv:data/leads.csv --using play:prebuilt/name-and-domain-to-email-waterfall --limit 5 --out email-flow.play.ts
deepline plays bootstrap people-email --from provider:dropleads_search_people --using providers:hunter_email_finder,leadmagic_email_finder --limit 5 --out prospecting.play.ts
deepline plays bootstrap company-people-email --from provider:apollo_company_search --people play:prebuilt/company-to-contact --email play:prebuilt/name-and-domain-to-email-waterfall --limit 5 --out account-contacts.play.ts
deepline plays bootstrap company-list --from provider:apollo_company_search --limit 5 --out companies.play.ts
```

Bootstrap validates route category/getters; it does not map CSV/provider fields for you. Generated bootstrap plays should pass `plays check` before provider execution, but same-name field defaults still need business review. Fill TODOs, run `plays check`, then a watched pilot. CSV bootstrap bakes `ctx.csv(...)`; do not pass the CSV again unless `plays describe` says so.

Keep normalization at the declared contract boundary. Finder play/provider outputs should flow through described output fields or `extractedValues.*.get()`, where no-result becomes `null`; do not replace that with raw response parsing, shape guessing, or local trim/spelunking in the scratchpad.

## Provider Discovery

Tools are fallback ingredients after play routing. Use category search, not provider memory:

```bash
deepline tools search "company search funding headcount hq" --categories company_search --json
deepline tools search "people search title seniority linkedin domain" --categories people_search --json
deepline tools search "work email finder name domain" --categories email_finder --json
deepline tools search "phone finder person company" --categories phone_finder --json
deepline tools describe <tool-id> --json
```

Read live `inputSchema`, cost, `billingMode`, Deepline credits/USD, pricing model, target getters, list getters, and enum hints. When two providers are plausible and quality is unproven, prefer the one that charges on returned results or successful hits (`post_deduct`) over per-attempt/request/page pricing. Direct executes before a play are capped at three total, including autocomplete/count/shape probes.

Provider routing scar tissue:

- Structured firmographic TAM: structured company search for funding, headcount, HQ, exact stage/category.
- Small fuzzy/niche category: semantic/web account seed can beat rigid taxonomies; keep citations/evidence.
- People search: use only after domains are seeded when account fit matters.
- Domain search: domain/company discovery, not named-person email.
- Email finder: requires described person identity plus company/domain/LinkedIn context and `extractedValues.email`.
- Phone finder: requires strong person anchor; validate known phones with verifier tools after recovery.
- Geography: validate provider country vocabulary before scale. Prefer ISO-3 where provider expects HQ filters. Serper locale affects results.

## Linked Alpha Docs

Load only the doc matching the task; the main skill is the router. These relative docs live under this installed skill's base directory. Repo GTM docs such as `.skills/deepline-gtm/finding-companies-and-contacts.md` are separate source docs; do not invent `.skills/deepline-gtm/references/...` paths.

- `references/tam-sizing-and-company-lists.md`: TAM sizing, company sourcing, structured search, hiring-qualified accounts, geography, healthcare account seeds.
- `references/contacts-and-personas.md`: known-company contacts, persona/title gates, email/phone/LinkedIn, clinical leaders, local SMB and org charts.
- `references/workflows-signals-and-automation.md`: niche signal discovery, Clay migration, multi-table outputs, cron/webhook/API automation, durable side effects.

For hard company+contact asks, load both TAM/company and contacts/personas docs. Scout before durable build: probe plausible company sources and contact routes on 3-5 rows, compare company quality, contact/title/LinkedIn/email coverage, misses, and cost, then bootstrap/scale the winning route.

## V2 Play Authoring

Use the current documented V2 surface from `docs/play-syntax-spec.md`: `definePlay(name, fn, bindings?)`. Do not copy older object-form snippets unless the current docs or `plays bootstrap` output show them and `plays check` passes.

```ts
import { definePlay } from "deepline";

type Input = { limit?: number };

export default definePlay(
  "gtm-play",
  async (ctx, input: Input = {}) => {
    return { ok: true, limit: input.limit ?? 5 };
  },
  { billing: { maxCreditsPerRun: 50 } },
);
```

Trigger bindings are the third argument:

```ts
export default definePlay(
  "daily-company-sync",
  async (ctx, input: { domain: string }) => {
    const company = await ctx.tools.execute({
      id: "company_lookup",
      tool: "test_rate_limit",
      input: { key: input.domain },
      description: "Look up company by domain",
    });
    return { domain: input.domain, company };
  },
  {
    cron: { schedule: "0 9 * * *" },
    webhook: {},
    secrets: ["HUBSPOT_TOKEN"],
    billing: { maxCreditsPerRun: 100 },
  },
);
```

API/manual plays need no trigger binding; the JSON input is the API contract.

Inputs are inferred from TypeScript. Before importing `v` or `deepline/values`, confirm the current package export in docs or generated bootstrap output. If `deepline/values` does not resolve, remove it and use typed input as shown above. Webhook plays need typed payload, idempotency key, and a dry-run side-effect gate. Cron plays should use the documented schedule shape; add timezone only if current docs/describe supports it.

Durable freshness belongs on work that should expire:

```
await ctx.step("normalize", () => value, { staleAfterSeconds: 86400 });
await ctx.fetch("page", url, init, { staleAfterSeconds: 21600 });
await ctx.runPlay("email", "prebuilt/name-and-domain-to-email-waterfall", input, { staleAfterSeconds: 2592000 });
await ctx.tools.execute({ id: "email", tool, input, staleAfterSeconds: 2592000 });
dataset.withColumn("validated_email", resolver, { staleAfterSeconds: 86400 });
```

For dataset cells whose refresh depends on the returned value, use object-column authoring. `previousCell.value` is the previous returned value for that row+column; `previousCell.completedAt`, `previousCell.staleAt`, and `previousCell.staleAfterSeconds` are metadata. Returning `null` from `staleAfterSeconds(value)` means the stored cell has no next expiry.

```
dataset.withColumn("job_change", {
  run: async ({ row, ctx, previousCell }) => {
    if (previousCell?.value.status === "stale_contact") {
      return previousCell.value;
    }
    ctx.log("job_change_detection_run domain=" + String(row.domain));
    return { status: "checking", domain: String(row.domain) };
  },
  staleAfterSeconds: (value) =>
    value.status === "stale_contact" ? null : 2592000,
});
```

Do not put non-determinism in play bodies. If you need authenticated HTTP, use secret handles:

```
const token = ctx.secrets.get("HUBSPOT_TOKEN");
const res = await ctx.fetch("hubspot_company", url, { auth: ctx.secrets.bearer(token) }, { staleAfterSeconds: 900 });
```

CSV and datasets:

```
const rows = await ctx.csv("data/accounts.csv", {
  required: ["Company", "Website"],
  rename: { Company: "company_name", Website: "domain" },
});

const accounts = await ctx.dataset("accounts", rows)
  .withColumn("domain_normalized", (row) => cleanDomain(row.domain))
  .withColumn("fit_status", (row) => scoreAccount(row))
  .run({ key: "domain_normalized", description: "Account fit table" });
```

`ctx.dataset` is row-preserving. For account-grain deliverables, store `contact_1_*`, `contact_2_*`, `contact_3_*` slots. Create a second contact table only when the user asked for contact-grain output; keep `account_domain`, `account_name`, evidence, and source lineage.

Before `.run({ key })`, verify the key exists after CSV normalization and is non-null in the pilot row. For large datasets, avoid flattening everything in memory; keep nested child results on account rows, materialize bounded pilots, then split contact-grain later.

Getter-safe access:

```
const list = search.extractedLists.companies.get();
const email = finder.extractedValues.email.get();
const status = verifier.extractedValues.email_status.get();
const raw = result.toolResponse.raw; // debugging only when no getter exists
```

If a getter is missing, fix tool choice/metadata or describe another provider. Do not hide with raw fallbacks or `?.get?.()` in final logic.

## Row and Export Contracts

Final company CSV: `company_name`, `domain`, requested `category`/`<vertical>_category`, `company_fit_evidence`, source, status, miss_reason. For hiring-qualified asks, include `hiring_evidence`/`hiring_status`; requested column lists are minimums, not permission to omit qualification evidence.

Final contact CSV: `company_name`, `domain`, `contact_name`, `title`, `linkedin_url`, requested email/phone, source, status, miss_reason.

Keep the user's exact column names in the final CSV even if a play returns aliases. Normalize aliases before writing:

- `contact_title` or `matched_role` -> `title` only when it contains the real title/persona evidence; otherwise leave `title` null and explain `miss_reason`.
- `contact_linkedin_url` -> `linkedin_url`.
- `work_email` -> `email` when the user asked for email.
- vertical/category evidence -> `company_fit_evidence`; do not omit evidence because the seed CSV has a category.

Final write checklist:

1. Confirm the final CSV is exported from the play dataset that encodes the deliverable contract. If you need cleanup, add projection/status columns to the play and re-export; do not hand-author a separate final artifact from partial terminal output.
2. Compare the requested columns to the play-advertised `rowOutputSchema`/export header; no required column may be missing.
3. Compare raw play export columns to final columns; do not drop evidence, status, source, or miss fields during cleanup.
4. Count non-empty core fields before writing: for contacts, `contact_name`, `title`, `linkedin_url`; for company lists, `company_name`, `domain`, category, evidence.
5. If a required core field is empty in the pilot or final export, either repair the route/projection or preserve the null with an explicit `miss_reason`; do not silently ship a blank column.
6. If aliases exist, normalize them in the play projection when possible; otherwise normalize in a minimal export step and remove duplicate/confusing alias columns unless the user asked for raw output.

For persona asks, title/headline must match requested function and seniority. Generic sales/product/finance/engineering leaders are misses for clinical/security/legal/data asks unless the prompt allowed adjacent functions.

For email/phone: recover first, validate second. Skip nulls before validators. Export validation status as scalar columns.

For LinkedIn URL lookup: use name/company search plus profile validation; require name match and current employer match. Wrong-person URLs are worse than nulls.

For outreach/copy: separate research from generation, use structured schema, and keep unsupported claims out of final copy.

Outreach output contracts:

- Qualification: score 0-10, label, fit band, rationale, and question-by-question Yes/No/Unknown with confidence.
- Email sequence: exactly 4 steps, each with subject, core value prop, body, and sequence rationale. No markdown or unsupported claims.
- Personalization: each email must reference specific evidence; first-name/company-only changes are template output.
- Subject variants: max 8, max 7 words, no clickbait, all caps, or exclamation marks.
- Campaign activation: if activation is manual-required, return the UI link and do not claim API activation succeeded.

## Cost and Scale Gate

Before paid scale, write:

```text
Plan before paid scale:
- Goal:
- Pilot result:
- Route:
- Source rows after cheap filters:
- Limits: max accounts, people/account, fallback legs
- Paid fanout estimate: rows * calls/row * fallback legs
- Expected Deepline credits/USD:
- Stop conditions:
- Inspection: deepline runs get <run-id> --json --full
```

Ask for approval when cost is unknown, user did not provide budget, or the run exceeds pilot scale. Never expose provider spend to customers; expose Deepline spend.

Pilot-to-scale stop rules:

- If source rows are dominated by sentinel headcount values, org units, directories, non-company domains, or broad taxonomy noise, reject that source or add a disjoint source before contact fanout.
- If a 1-3 row pilot returns names/LinkedIn but zero titles, inspect/export the pilot and fix projection or route before scale.
- If a pilot returns good contacts but zero emails, scale only if email was optional and the CSV preserves contact identity plus `miss_reason`.
- If the final user asked for 30 rows, use a slightly larger seed only to offset expected misses, then slice the final CSV to the requested row count.

## Debugging Runs

Use `ctx.log("message")` inside custom plays for lightweight breadcrumbs around route choice, row gates, getter shape, and fallback decisions. Inside dataset columns, use the row context (`rowCtx.log("message")`) so the log lands in the same run stream. Do not log secrets, credentials, raw large provider payloads, provider spend, or full CSV rows.

Logs are run-ledger facts, not final data. Keep customer-facing outputs in dataset columns with `status`, `source`, evidence, and `miss_reason`; use logs to explain why a branch ran or skipped.

Inspect logs with Deepline commands, one at a time:

```text
deepline runs get <run-id> --json --full
deepline runs logs <run-id> --json
```

During pilots, a watched run is usually enough for live progress:

```text
deepline plays run --file <file.play.ts> --input '<json>' --watch
```

## Recovery

- Zero rows: change source strategy, relax inputs, or add a disjoint branch. Do not inspect raw receipt tables for normal GTM work.
- Short count: relax fuzzy filters, add branches, export best rows with `miss_reason`/confidence.
- Off-category: strengthen fit evidence before people/email fanout.
- Empty getter: re-describe tool/play; choose a provider with the needed getter.
- Placeholder values: normalize to null with `miss_reason`.
- Infra failure: `workers_edge` scheduler 503, callback failure, receipt lock, timeout, or persistence failure means inspect health/auth/run/logs once, stop stale run if needed, retry the same direct route with adjusted input/limit, or export partials. Custom play authoring does not fix scheduler persistence.
- Contract failure: missing required output, wrong start entity, unsupported route family, bad CSV mapping, missing getter, or failed `plays check`. Only these justify bootstrap/custom-authoring after two same-class failures.
- Repeated same-class failure twice: stop tuning that branch and choose a new route.

## Plan-Only Mode

When the prompt says dry run, simulate, bootstrap-plan, or do not run provider tools, do not call provider tools or `plays run`. Safe commands: `health`, `auth status`, `billing balance`, `plays search`, `plays describe`, `plays check`, `plays bootstrap`, `tools search`, `tools describe`.

Examples in plans must obey command discipline: no shell parsing, redirection, `curl`, env/config spelunking, or old CSV-enrich syntax.
