# Lead Magnet Sequence: Workflows -> Providers -> Waterfall

PLG is already shipped. The next three Sung posts should move from "what is possible" into the infrastructure buyers actually need to copy.

## 1. Workflows

**Comment keyword:** `WORKFLOWS`

**Asset:** Deepline V2 Workflow Implementation Guide

**Video pairing:** Pipeline as Code first. Glue Code can be used as the follow-up clip or supporting post because it explains why the old way breaks.

**Promise:** turn a recurring GTM task into a typed Deepline V2 play instead of another brittle script, Zap, spreadsheet export, or one-off reverse ETL job.

**What the asset should include:**

- V2 mental model: trigger/input -> typed play -> tools/enrichment -> guardrails -> dry run -> approval -> CRM/campaign writeback.
- SDK surfaces: CLI, `client.runPlay(...)`, `ctx.play(name).run(...)`, `ctx.play(name).runSync(...)`, `ctx.runPlay(...)`, and raw `POST /api/v2/plays/run`.
- Runtime surfaces for observability: `GET /api/v2/runs/:runId` and `GET /api/v2/runs/:runId/tail`.
- Why V2 matters: TypeScript, real control flow, autocomplete, `ctx.dataset()` batching, easier debugging, and cloud execution after local testing.
- Starter workflows:
  - Signup -> HubSpot sequence.
  - Product usage spike -> CRM context -> campaign draft.
  - Personal email signup -> LinkedIn/company resolution -> review queue.
  - Event attendee/check-in -> account research -> follow-up draft.
  - Champion job change -> new account map -> warm outbound draft.
- Minimal eval kit: 20-row golden set, deterministic checks first, LLM judge only where judgment is needed, pass/fail thresholds before CRM writes.

**Why this goes next:** it gives technical GTM people the thing they can actually implement. "GTM engineering" gets concrete when the artifact is a play file.

## 2. Providers

**Comment keyword:** `PROVIDERS`

**Asset:** GTM Provider Stack Decision Matrix

**Video pairing:** Provider Sprawl.

**Promise:** stop picking enrichment vendors by vibes. Decide which provider should run for which job, what evidence is enough, when to stop, and what should be sent to review.

**What the asset should include:**

- Provider role matrix: identity, company, role/title, email, mobile, firmographic, technographic, intent, website, event, and social signals.
- Routing rules by input: domain-only, email-only, personal email, LinkedIn URL, company name, phone, event list, product workspace.
- Confidence levels: accepted, needs corroboration, review only, blocked.
- Cost model: cost per attempt, hit rate, cost per accepted record, downstream conversion value.
- CRM writeback rules: what gets written, what gets logged, what needs approval, what is never overwritten.
- Failure modes: stale titles, false personal-email matches, duplicate accounts, low-quality mobile fills, hallucinated company mappings.

**Why this goes second:** once people understand workflows, the next obvious pain is the provider mess inside those workflows.

## 3. Waterfall

**Comment keyword:** `WATERFALL`

**Asset:** Waterfall Cost Optimization Framework

**Video pairing:** Waterfall Complexity.

**Promise:** calculate the cheapest reliable provider order for a GTM workflow instead of firing every vendor on every row.

**What the asset should include:**

- Waterfall design worksheet: input fields, provider order, stop rules, retry rules, confidence thresholds, review queue.
- Expected cost formula: attempt cost, hit rate, accepted-hit rate, and cost per accepted result.
- Backtest template: compare cheap-first, quality-first, hybrid, and segment-specific routing.
- Eval examples: email validity, role match, company match, mobile precision, LinkedIn identity confidence, CRM duplicate prevention.
- Rollout plan: sample first, shadow run, approval gate, limited writeback, production.

**Why this goes third:** it turns the Provider Sprawl conversation into a practical cost-control artifact.

## Why Not GLUE Or EVALS As The Next CTA

`GLUE` and `EVALS` are useful, but they are better as sections inside the above assets:

- Glue code risk belongs inside the Workflows guide as the "why typed plays beat scripts" section.
- Evals belong inside both Workflows and Waterfall as the guardrail layer before CRM writes or campaign launches.

## CTA Language

**Workflows:** Comment `WORKFLOWS` and I will send the Deepline V2 GTM workflow implementation guide.

**Providers:** Comment `PROVIDERS` and I will send the provider stack decision matrix.

**Waterfall:** Comment `WATERFALL` and I will send the waterfall cost optimization framework.
