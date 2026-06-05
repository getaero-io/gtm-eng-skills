# Workflows, Signals, and Automation

Use this when the task is not a simple one-shot company/contact list: ICP signal discovery, won/lost analysis, Clay migration, multi-table workflow reconstruction, recurring runs, webhooks, or CRM/API side effects.

## Niche Signal Discovery

Use for "find signals that separate won vs lost", "discover ICP signals", or "find net-new accounts like these wins." This is not generic company search.

Pipeline:

1. Won/lost domains.
2. Dedupe and apex normalize.
3. Website/jobs enrichment.
4. Differential signal scoring.
5. Cited evidence.
6. Top net-new prospects.

Quality gates:

- >80% website coverage before drawing conclusions.
- For web content, aim for 6-8 pages or 12-20K chars/company when it affects signal quality.
- Spot-check job rows and citation URLs.
- Every top signal needs cited evidence; demote unsupported lift.
- Always include top net-new prospects. Contacts/emails require approval.

Signal hierarchy: jobs, analyst validation, compliance language, buyer pain language, niche tech stack, website content.

Scoring: Core Fit 40, Buying Intent 30, Infrastructure Readiness 30. `60+` = immediate outreach, `35-59` = trigger/nurture.

## Clay Table Migration

Clay migration preserves the dependency graph and business behavior, not cell mechanics.

Target choice:

- Batch/manual rows -> V2 `ctx.csv` + dataset stages.
- Webhook/routing/CRM pushes -> webhook/API play.
- Batch plus push -> batch play first, push play second.

Extraction priority:

1. HAR bulk-fetch.
2. ClayMate export.
3. `clay-extract.py`.
4. Bulk-fetch only.
5. Schema JSON.
6. User description.

Before implementation, produce table summary, Mermaid dependency graph, pass plan, assumptions log, prompt source marking, and ask for confirmation when assumptions affect output.

Rules:

- `clay_record` and `fields` are reserved aliases; other aliases come from Clay column names.
- Prompt recovery order: HAR rendered values, `typeSettings.inputsBinding` prompt/formula, portable schema, approximation last.
- V2 ordering: CSV -> base dataset -> deterministic columns -> paid/provider columns -> AI synthesis -> scalar projection.
- Keep row ids and parent lineage in every child table.
- Parity: deterministic 100%, unambiguous LLM classification >=90%, structured schema fields 100%, email found rate >=95% of Clay where comparable.

## Multi-Table Plays

Use multi-table output when the user needs account grain and contact grain, evidence rows, job rows, or source lineage.

- Parent table: accounts or people from input/source.
- Child table: contacts, jobs, citations, signals, emails, phones, or events.
- Preserve parent keys in every child row: `company_domain`, `company_name`, `source_row_id`, `parent_id`.
- Return/export each table separately; do not flatten many-to-many evidence into one unreadable cell unless the user asked for one CSV only.

## Automation Trigger Shape

Start with the smallest trigger play that works before adding provider fanout.

- Cron: scheduled batch, no webhook payload. Use typed input only for manual/API override.
- Webhook: external event payload, idempotency key, dry-run side-effect gate.
- API/manual: no trigger binding; the JSON input is the API contract.
- CRM or outbound push: prove enrichment batch first, then add push stage and return pushed/skipped/error status.

Keep side effects behind explicit gates. A failed CRM push should not force rebuying company/contact discovery on rerun.

## Durable Workflow Rules

- Stable ids are the cache. Rename ids only when intentionally refreshing wrong/stale data or changed semantics.
- `ctx.dataset` is for row state and CSV/exportable tables.
- `ctx.step` is for pure or bounded deterministic work.
- `ctx.runPlay` is for reusable child workflows.
- `ctx.tools.execute` is for provider calls with declared getters.
- `staleAfterSeconds` belongs where data should expire, not on every step by habit.

If deleting the local play would delete route knowledge, mappings, joins, fallback logic, row-level miss reasons, or side-effect gates, the task belongs in a durable workflow rather than direct provider calls.
