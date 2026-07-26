---
name: deepline-plays
description: "Use this skill for any GTM Engineering work in Deepline — prospecting, list-building, account research, contact enrichment, email/phone/LinkedIn lookup, ICP qualification, lead scoring, outreach copy, CSV-driven row work, and verifying enriched data. Triggers on phrases like 'enrich this CSV', 'find contacts at these companies', 'build a TAM list', 'waterfall emails for these leads', 'detect job changes', 'is this data accurate', 'write a sequence for', and on any request that mentions Deepline, plays, or named GTM providers (Crustdata, Hunter, Dropleads, etc.). Use this even when the user does not explicitly say 'GTM' — most CSV-with-leads tasks and most provider-driven enrichment tasks are GTM tasks. SKIP only when the request is a Clay table extraction (use clay-to-deepline) or has no Deepline / outbound / data-enrichment dimension at all."
---

# Deepline Plays

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

Deepline is a TypeScript SDK and CLI for GTM execution: durable, typed workflows (plays) that call providers, create row datasets, run waterfalls, validate, and produce CSVs. The job: take an ICP and turn it into an enriched, scored dataset the customer trusts enough to act on. Every AI-filled or provider-filled cell is a claim until verified, so correctness is a phase of the work, not an afterthought.

> **Names of plays and tools are starting hints. The CLI is the live source of truth.**
>
> Tool IDs and play names get renamed, deprecated, and added constantly. Confirm any name before spending:
>
> - `deepline tools list --json` — enumerate the tool categories; `deepline tools list <category> --json` lists EVERY tool in one category. **Browse first**: enumerate categories → exhaustive category listing → `describe`. This is complete recall — use it before concluding a provider class doesn't exist.
> - `deepline tools search <query> --json` — ranked search, for a cross-cutting filter, not an inventory.
> - `deepline plays search <category> --json` — find the current canonical play for a pattern.
> - `deepline plays describe <name> --json` / `deepline tools describe <id> --json` — confirm the input contract before invoking.
> - **Prefer `prebuilt/<name>` refs over a plain play name.** A plain name can resolve to a stale workspace-owned copy the runtime rejects ("legacy runtime contract… Republish this play"), whose `describe` may advertise a wrong input key. That error is a config artifact, not a real failure — re-run against the `prebuilt/` ref.
>
> When unsure about command shape, run `deepline <command> --help` before guessing flags.

## The lifecycle: EXPLORE → SCORE → EXPLOIT → VERIFY

This is the spine. Every provider-backed request runs these four stages in order. The failure mode it fixes: an agent classifies a familiar task as "known," jumps straight to a prebuilt, and never measures the alternatives, so a lone default provider's coverage becomes the customer's ceiling, unexamined. Explore first, always. A prebuilt is a **candidate you score**, never a reason to skip scoring.

**1. EXPLORE. One parallel pass, not a serial probe.** Pilot 3-5 rows across every viable route at once. Fork `plays/route-fanout.play.ts` in search mode (`mode:'search'`), set `strategy`, and list the candidate routes for the field. A category is complete recall (`deepline tools list <category> --json`), not a famous-name shortlist. Prebuilts enter here as candidates, compared head to head with the raw routes; they never bypass the bake-off. This is FASTER than jumping to a prebuilt, not slower: N routes fire concurrently, so you measure the whole market at the wall-clock of a single route. Uncredentialed bring-your-own providers (labeled `requires_connection` in `tools describe`/`list`) are NOT candidates. Surface "connect X to add this route" instead; do not bake off a route that fails closed and scores a false 0.

**2. SCORE. Rank the routes, cheap judge only.** Rank each route by three numbers. **Coverage**: read the native `dataset_execution_stats[<column>].non_empty` fill rate from `deepline runs get <id> --full --json`, never a hand-tallied count. **Correctness**: against golden truth where you have it (`shared/correctness.md`). **Marginal cost per row**: credits/row at scale, never the pilot's inflated total. Any model-side ranking or tie-break uses the **cheap Haiku-class judge**, the batched rerank subagent (`plays/shared/rerank.ts` / `plays/shared/rerank-cli.ts`). NEVER `deeplineagent`, never the expensive main model for grunt scoring (LAW 6). Emit a compact route scorecard: route × coverage × correctness × cost/row.

**3. EXPLOIT. Run the winner at production size.** Take the winning route or fused waterfall to the full row set. A covered pattern is a prebuilt (`prebuilt/<name>`) or the fused route-fanout winner in exploit mode (`mode:'exploit'`, the default); a genuinely novel composition is a hand-authored `*.play.ts` (the SLOW path; see § Surface lifecycle). Discover the exact current play name and confirm its contract before spending (`deepline plays search`, `plays describe`), then run it.

**4. VERIFY. Validate, export, report provenance.** Validate the filled cells (`shared/correctness.md`), export to a user-controlled path, and report the native coverage number (`dataset_execution_stats[<column>].non_empty`, formatted `"N/M (X%)"`) plus per-route provenance. A number without a source is a claim, not data (LAW 7).

**The single-route exception (skip EXPLORE):** a genuinely closed, single-value task, like validate ONE email or look up ONE known domain. That is the only reason to skip the bake-off. Everything provider-backed with coverage uncertainty (discovery, contact recovery, research) enters at EXPLORE. "Familiar" is not "closed": "find CTOs + emails" feels known and still has a coverage ceiling you have not measured, so it explores.

Optimize in one order across all four stages: **trust, then correctness, then price. Never trade the first two for the third.** Trust is the session itself (route map up front, real rows early, a scoreboard at each checkpoint); correctness is whether the cells survive verification; price is the refactor-phase concern the golden loop handles last. The standing question, asked on every route and after every delivery: **can this be more trustworthy, more accurate, cheaper?**

### Worked example: "Find 10 CTOs + work emails"

The failing case. It feels known, so the old flow ran a prebuilt and never explored. Under the spine it enters at EXPLORE.

**EXPLORE.** Discovery has two legs. The email/contact-recovery leg bakes off cleanly in the scorer: fork `route-fanout` in search mode and fire the email routes concurrently on a 3-row pilot with known-truth emails.

```
deepline plays run plays/route-fanout.play.ts \
  --input '{"strategy":"email","mode":"search"}' \
  --csv pilot.csv --watch
```

Pilot rows carry an `email__truth` column so the scorer measures each route against real answers. The DISCOVERY leg (which people-search provider finds the CTOs at each domain) is a lighter multi-route pilot for now, not the same one-shot bake-off. Name it honestly and pilot the 2-3 candidate people-search providers over the same 3 rows rather than pretending it's frictionless.

**SCORE.** Read `dataset_execution_stats[email].non_empty` from `deepline runs get <id> --full --json` for each route; check correctness against the `email__truth` column; quote marginal cost/row. The Haiku judge (`rerank-cli.ts`) breaks ties on the discovery leg. The scorecard:

| route | coverage (`non_empty`) | correct vs truth | cost/row |
| --- | --- | --- | --- |
| finder + validator waterfall | 3/3 (100%) | 3/3 | ~4 cr |
| people-search aggregator | 2/3 (67%) | 2/2 | ~6 cr |
| finder-only, no validator | 3/3 (100%) | 2/3 | ~2 cr |

The waterfall wins: full coverage AND correct, and the validator is worth its marginal cost because finder-only shipped one wrong email.

**EXPLOIT.** Run the winning waterfall on the full 10.

```
deepline plays run plays/route-fanout.play.ts \
  --input '{"strategy":"email","mode":"exploit"}' \
  --csv ctos.csv --watch
```

**VERIFY.** Validate the fills, export to the user's path, report coverage from the native stat: "9/10 work emails (90%), each with its resolving route and validation verdict; the one miss is an honest null with a reason." Provenance travels with every cell.

## Laws (non-negotiable — these dominate every other rule below)

1. **Pilot before scale.** Show real pilot rows and get an explicit go before any paid full run. A misshaped payload burns credits across hundreds of rows; a pilot exposes it on row 1 for cents.
2. **Take the human along — the session is the product.** Announce the route map + expected cost *before* spending, show real rows within minutes, checkpoint each phase with a compact scoreboard (coverage / validation / credits / next), deliver increments. A run that goes silent until a final CSV is a black box even when it's correct.
3. **Null over invention.** When tools come up empty, return null (or fewer rows). Never pattern-complete a name, email, company, or fact from training data — that ships unverifiable rows that look like success and fail at outreach time.
4. **Confirm before you spend.** The live CLI is the source of truth for tool/play names and input shapes (`tools describe`, `plays describe`). Dynamic `ctx.tools.execute` refs are NOT preflight-checked — a wrong id fails only at run time.
5. **The judge is task-shaped.** Relevance ranks *which source to read*; validation decides *is this contact real* (identity gate + validator); corroboration decides *which number is true* (agreement across independent sources). Never trust a reranked #1 as a verified fact.
6. **You are the judge, not deeplineagent.** The agent plans and judges; the play is the deterministic executor. The model step (rerank) is a cheap subagent — never `deeplineagent`, never inside the durable play (`shared/reranking.md`).
7. **Every value travels with its evidence.** Preserve provider evidence columns; deliver research findings with their source URL. A number without a source is a claim, not data.
8. **Only Deepline spend is customer-facing.** Never surface provider USD. Never test on customer accounts, workspaces, keys, or credits — internal/test only.
9. **Coverage and cost are decisions you surface, not defaults you hide.** Quote cost as **marginal per unit** (~X credits/email), never the pilot's run total — a small batch's total is dominated by fixed compute and expensive validators that amortize over scale, so "11 credits for 2 emails" misleads. And report **coverage as a number** the runtime already computed: read `dataset_execution_stats[<column>].non_empty` (fill rate, formatted `"N/M (X%)"`) from `deepline runs get <id> --full --json`. Do not recompute a scorecard by hand. When it's low, don't ship a thin result silently — proactively offer (or, when it's clearly inadequate, auto-escalate to) a wider provider fan-out. A cheap single-provider result at 40% coverage is a finding, not a delivery. See `jobs/enriching.md` § Start cheap, measure coverage, escalate.

## Field notes — failures to not repeat (from real runs, 2026-07-23)

- **Hand-authoring a play for a standard task is the tax.** A CTO-email pilot ran 4.5 minutes because the default was a custom `*.play.ts` — a blank-LinkedIn data-shape bug, a row-key repair, three edit→preflight→run loops. The enrichment itself was seconds. Accuracy was perfect; speed was the failure. A prebuilt (or a route-fanout sweep) would have skipped the debug loop entirely. Reach for authoring last, at EXPLOIT, only for a genuinely novel composition (see § The lifecycle).
- **A plain play name can shadow a stale copy.** A run against `name-and-domain-to-email-waterfall` hit "legacy runtime contract… Republish this play" — a stale workspace-owned copy whose `describe` advertised a wrong input key. It is a config artifact, not a data failure. Re-run against the `prebuilt/<name>` ref.
- **A dead tool ref ships silently.** A research route used `serper_search` (nonexistent; the real id is `serper_google_search`) — preflight passed, it errored only at run time. Confirm every route's tool id with `tools describe` before shipping a route (LAW 4).
- **A low fill rate is usually a credentials gap, not a data gap.** Email/research recall collapsed because `hunter`/`findymail`/`prospeo`/`fullenrich`/`exa` were uncredentialed and short-circuited to 0ms. Check *which routes actually executed* before concluding coverage is poor.
- **A reranked #1 is not a true fact.** A research run ranked a credible source top, but a dubious lone-source "\$965B valuation" survived; the real answer ("\$380B") held only because three independent sources corroborated it. Corroborate numbers; don't trust rank (LAW 5).
- **An all-null email column can mean the play never resolves emails.** `company-to-contact` returns identity only (`email: null` always) — you must chain the email waterfall. Don't read all-null as "no emails found."
- **The trust gate trades recall for precision.** The email identity gate withheld correct fused answers as `verify_next` while letting one wrong answer through. Unshipped ≠ wrong and shipped ≠ all-correct — read the tags, and re-check borderline rows before concluding.
- **Trust the runtime; a transient error is not a data miss.** The runtime auto-retries rate-limit and transient 5xx errors and isolates a single-row failure (it never fails the run), so a blip you see mid-run is not an empty cell. Don't record it as null and don't retry-storm around it: let it settle and keep going. The governor owns concurrency, not you.

## Surface lifecycle

All surfaces hit the same backend. Use the **CLI** to discover, invoke, inspect, promote. Use a **prebuilt play** when the registry already has the business pattern — reference it as `prebuilt/<name>` (a plain name can shadow a stale copy; see the CLI callout above). Use a **custom `*.play.ts`** only when the work has multiple durable boundaries no prebuilt covers: source rows, provider calls, datasets, validation, scoring, branching, export shape, reruns. Direct `tools execute` calls are probes, not pipelines. Use the programmatic client (`Deepline.connect()`) only from external Node apps, never inside a play body.

Custom-play lifecycle (the SLOW path): write `my-play.play.ts` with `definePlay` → run locally (`deepline plays run ./my-play.play.ts --input '{...}' --watch`) → inspect and edit the same file (the play accumulates checkpointed stages, so reruns reuse completed work) → promote when stable (`deepline plays set-live ./my-play.play.ts`), then invoke by name or via `ctx.runPlay`.

## Execution philosophy: everything in the play, iteration is nearly free

**If it touches a provider, it belongs in play code** — probes, parallel fan-outs, waterfalls, research columns, exports. Only the play gets durability, receipts, a runtime sheet, and governed parallelism; a bare `tools execute` is for sniffing one contract, and a shell loop of them is the anti-pattern. Fire independent calls concurrently with ordinary `Promise.all` — the runtime still owns rate limits, retries, and billing, so parallelism costs nothing but the wall-clock it saves.

**The cache makes iteration nearly free, so build like it.** Every tool call writes a content-addressed receipt (tool + input; misses included) and every filled cell is reused across runs, so a rerun after an edit re-pays only what changed. Do not hoard runs or fear re-running: grow the play one stage at a time, rerun constantly, and let the cache carry the known-good prefix. This is also why EXPLORE is cheap: the parallel sweep runs candidate routes concurrently on a small sample, keeps the winner (`shared/correctness.md`), and only the loser's spend is ever wasted, once.

Runtime primitives, composition, authoring traps, and parallelism live in `shared/authoring.md`. Exact SDK signatures: https://deepline.com/docs/sdk-v2/sdk-reference. HTTP invocation: https://deepline.com/docs/sdk-v2/api-reference. The route-fanout skeleton — fan out, fuse (reciprocal-rank), judge, emit a per-route ledger — is `plays/route-fanout.play.ts` (`shared/correctness.md` § Fork the comparison-run harness); the coverage escalation ladder is `jobs/enriching.md` § Start cheap, measure coverage, escalate.

## Choose your job

Read the matching doc before executing. The rules here apply to every task; the docs encode what previous runs learned the expensive way.

| If you're about to…                                                    | Read                          |
| ---------------------------------------------------------------------- | ----------------------------- |
| Find companies and contacts (no rows yet)                              | `jobs/finding.md`             |
| Fill columns on existing rows: emails, phones, signals, AI research    | `jobs/enriching.md`           |
| Write per-row outreach copy off research columns                       | `jobs/writing.md`             |
| Build, copy, customize, or debug a custom `*.play.ts` file             | `shared/authoring.md`         |
| Rank an uncertain route, or QA/verify a dataset before shipping        | `shared/correctness.md`       |
| Rank/judge a research shortlist (which sources best answer the question)| `shared/reranking.md`         |
| Diagnose a run that failed, stalled, or produced wrong output          | `references/debugging.md`     |
| Look up exact SDK signatures or HTTP contracts                         | the two hosted doc URLs above |
| **Exit:** extract / convert a Clay table                               | route to `clay-to-deepline`   |

Multi-phase tasks read the jobs docs in order (finding → enriching → writing) and `shared/correctness.md` before shipping.

## CLI mechanics that back the lifecycle

Before EXPLORE spends, confirm the ground: `deepline health`, `deepline auth status --json` (not registered → `deepline auth register`), and for CSV tasks `deepline csv show --csv rows.csv --summary`. Discover the current name with `deepline tools list <category> --json` / `deepline plays search <category> --json`, confirm its contract with `describe`, then run: a prebuilt as `prebuilt/<name>`, a local file by path (`deepline plays run <file.play.ts>` while iterating; `set-live` when stable). Inspect with `deepline runs get <id> --full --json`, export with `deepline runs export <run-id> --out <path>`.

Run `deepline` commands directly and read the complete output. Piping human-formatted output into `head`/`tail`/`grep`/`jq` or backgrounding truncates the errors and run URLs you need; `--json` output is safe to pipe and parse, so use it whenever a downstream step parses output. `plays run` waits and streams completion by default (`--watch` is a compatibility alias); `--no-wait` starts the run and returns the id. Row totals live in `rowCounts.{persisted, succeeded, failed}` alongside `dataset_execution_stats`. The runtime already counted, so read those instead of hand-tallying.

**Take the customer along. The session is the product.** A run that goes silent until a final CSV is a black box even when correct. Announce the route map before spending, show real pilot rows the moment they exist, checkpoint each stage with a compact scoreboard ("12 emails: 6 valid, 6 verify_next" builds trust; a bare "12 emails" spends it), and deliver increments. **Ask when ambiguity is load-bearing.** A segment label, threshold, ICP boundary, or "which of these two people did you mean" can change the outcome, and one wrong full run costs more than one question; a verified answer becomes golden truth. Don't ask about things the pilot can answer.

## Cross-cutting rules

The "why" matters more than the rule — knowing the failure mode lets you handle edge cases. (Pilot-before-scale, null-over-invention, and coverage/cost are LAWS above; these are the mechanics.)

- **Over-provision, then filter.** For N rows, pull ~1.4×N at the top of funnel. Every phase has natural falloff, and companies providers can't find contacts for are the same ones without email coverage — coverage is a property of the company, not something retries overcome. Deliver the best N complete rows; let incomplete rows fall off.
- **Preserve provider evidence columns.** Responses include proof fields the user did not ask for: source URL, funding metadata, validation status, confidence, hiring counts, provenance. Verification runs on evidence, so trimming to display columns destroys the ability to trust the dataset. Asked for `name, title, company, email` and got `seniority`, `last_changed_at`, `source` too? Keep all seven.
- **All I/O through `ctx.*` (replay-safety).** Inside a `*.play.ts`, every non-deterministic operation goes through the runtime: `ctx.tools.execute`, `ctx.runPlay`, `ctx.csv`, `ctx.dataset`, `ctx.fetch`, `ctx.log`, `ctx.sleep`. The body re-executes during replay; `process.env`, `Date.now()`, `fs`, or raw `fetch` see different values on the second execution and corrupt the workflow.
- **Prebuilts are templates.** Search first, reference as `prebuilt/<name>`. If it fits, run it; if only CSV headers differ, pass `--columns.<field> "<Header>"`. Copy (`deepline plays get <name> --source --out ./my-play.play.ts`) only for semantic changes — the copy preserves the provider order the prebuilt already got right.
- **One run per file while iterating.** Edit one local play file in place; the durable cache makes reruns cheap when names and keys stay stable. No `-v2`/`-fixed`/`-final` variants.
- **Outputs go in a project-local working directory.** Files in `/tmp/` are wiped on reboot and users have lost paid enrichment outputs there; credit-costing outputs belong in a directory the user controls. Set up a task-descriptive slug at step zero: `WORKDIR="deepline/data/<slug>" && mkdir -p "$WORKDIR"`. Keep custom `*.play.ts` files in the current workspace (where `node_modules/deepline` is available). After a run, export to the user-requested path with `deepline runs export <run-id> --out <path>` and report the exact path plus the run URL.
- **CSV inputs are runtime datasets.** `input: { csv: string }` pairs with `--csv leads.csv` and `ctx.csv(input.csv, { columns, required })`. The return value is a `PlayDataset` — pass it to `ctx.dataset`; use `count()`/`peek()` for bounded inspection. Row progress, retries, idempotency, and table output depend on the runtime owning the dataset.
