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

Optimize in one order: **maximize trust first, then correctness, then price — in that order.** Trust is the session itself (route map up front, real rows early, a scoreboard at each checkpoint); correctness is whether the cells survive verification; price is a refactor-phase concern the golden loop handles last. Never trade the first two for the third. That ordering is also the standing question — asked on every route and again after every delivery: **can this be more trustworthy, more accurate, cheaper?** A route that shipped yesterday is a candidate for today's comparison run; single-provider defaults calcify, measured options compound. The journey is: **define the ICP → find → enrich → verify → write → deliver.** New or uncertain routes are built test-first against a golden set of known-truth rows (`shared/correctness.md`) before they earn a full run.

> **Names of plays and tools are starting hints. The CLI is the live source of truth.**
>
> Tool IDs and play names get renamed, deprecated, and added constantly. Confirm any name before spending:
>
> - `deepline tools list --json` — enumerate the tool categories; `deepline tools list <category> --json` lists EVERY tool in one category. **Browse first**: enumerate categories → exhaustive category listing → `describe`. This is complete recall — use it before concluding a provider class doesn't exist.
> - `deepline tools search <query> --json` — ranked search, for a cross-cutting filter, not an inventory.
> - `deepline plays search <category> --json` — find the current canonical play for a pattern.
> - `deepline plays describe <name> --json` / `deepline tools describe <id> --json` — confirm the input contract before invoking.
>
> When unsure about command shape, run `deepline <command> --help` before guessing flags.

## Choose the right surface

All surfaces hit the same backend. Use the **CLI** to discover, invoke, inspect, promote. Use a **prebuilt play** when the registry already has the business pattern and the contract fits — column aliases are an invocation concern, not a reason to copy code. Use a **custom `*.play.ts`** when the work has multiple durable boundaries: source rows, provider calls, datasets, validation, scoring, branching, export shape, reruns. Direct `tools execute` calls are probes, not pipelines. Use the programmatic client (`Deepline.connect()`) only from external Node apps, never inside a play body.

Custom-play lifecycle: write `my-play.play.ts` with `definePlay` → run locally (`deepline plays run ./my-play.play.ts --input '{...}' --watch`) → inspect and edit the same file (the play accumulates checkpointed stages, so reruns reuse completed work) → promote when stable (`deepline plays set-live ./my-play.play.ts`), then invoke by name or via `ctx.runPlay`.

## Execution philosophy: everything in the play, iteration is nearly free

**If it touches a provider, it belongs in play code** — probes, parallel fan-outs, waterfalls, research columns, exports. Only the play gets durability, receipts, a runtime sheet, and governed parallelism; a bare `tools execute` is for sniffing one contract, and a shell loop of them is the anti-pattern. Fire independent calls concurrently with ordinary `Promise.all` — the runtime still owns rate limits, retries, and billing, so parallelism costs nothing but the wall-clock it saves.

**The cache makes iteration nearly free — build like it.** Every tool call writes a content-addressed receipt (tool + input; misses included) and every filled cell is reused across runs, so a rerun after an edit re-pays only what changed. Do not hoard runs or fear re-running: grow the play one stage at a time, rerun constantly, and let the cache carry the known-good prefix. This is also why exploring is cheap — run candidate routes in parallel on a small sample, measure, keep the winner (`shared/correctness.md`), and only the loser's spend is ever wasted, once.

Runtime primitives, composition, authoring traps, and parallelism live in `shared/authoring.md`. Exact SDK signatures: https://deepline.com/docs/sdk-v2/sdk-reference. HTTP invocation: https://deepline.com/docs/sdk-v2/api-reference.

## Choose your job

Read the matching doc before executing. The rules here apply to every task; the docs encode what previous runs learned the expensive way.

| If you're about to…                                                    | Read                          |
| ---------------------------------------------------------------------- | ----------------------------- |
| Find companies and contacts (no rows yet)                              | `jobs/finding.md`             |
| Fill columns on existing rows: emails, phones, signals, AI research    | `jobs/enriching.md`           |
| Write per-row outreach copy off research columns                       | `jobs/writing.md`             |
| Build, copy, customize, or debug a custom `*.play.ts` file             | `shared/authoring.md`         |
| Rank an uncertain route, or QA/verify a dataset before shipping        | `shared/correctness.md`       |
| Diagnose a run that failed, stalled, or produced wrong output          | `references/debugging.md`     |
| Look up exact SDK signatures or HTTP contracts                         | the two hosted doc URLs above |
| **Exit:** extract / convert a Clay table                               | route to `clay-to-deepline`   |

Multi-phase tasks read the jobs docs in order (finding → enriching → writing) and `shared/correctness.md` before shipping.

## Execution loop

Once the job doc names the pattern category, this loop finds the current canonical tool/play and confirms its contract. Skipping it means guessing at names, input shapes, or auth state the CLI would answer for free.

```
1. Confirm runtime is healthy:        deepline health
2. Confirm auth is registered:        deepline auth status --json   (not registered -> deepline auth register)
3. For CSV tasks, inspect row shape:  deepline csv show --csv rows.csv --summary
4. Discover the right tool or play:   deepline tools list <category> --json
                                      deepline plays search <category> --json
5. Confirm the input contract:        deepline tools describe <id> --json
                                      deepline plays describe <reference> --json
6. Either:
   a) run a prebuilt directly:        deepline plays run <name> --input '{...}' --watch
                                      deepline plays run <name> --csv rows.csv --columns.domain Website --watch
   b) write a *.play.ts file and run: deepline plays run <file.play.ts> --csv rows.csv --watch
7. Inspect and export:                deepline runs get <id> --full --json
                                      deepline runs export <run-id> --out <path>
8. Verify before delivering:          shared/correctness.md
```

Run `deepline` commands directly and read their complete output — piping human-formatted output into `head`/`tail`/`grep`/`jq` or backgrounding truncates the errors and run URLs you need; `--json` output is safe to pipe and parse. Use `--json` whenever a downstream step parses output. `plays run` waits for the run and streams completion by default (`--watch` is a compatibility alias); pass `--no-wait` to start and return the run ID, then follow with `deepline runs get <id> --json`. `plays run <name>` runs the live registered version; `plays run <file.play.ts>` runs the local file directly — run by file path while iterating, `set-live` when stable.

## Take the customer along: explore, then exploit

The session is the product. A run that goes silent until a final CSV feels like a black box even when correct; the same run narrated builds the trust the dataset needs. Treat every job as explore-then-exploit:

- **Announce the route map before spending.** After discovery, one short message: the routes you'll try in order, expected cost and coverage for each, and what "good" looks like. Expectations set early turn partial coverage into a finding instead of a disappointment.
- **Show real rows within minutes.** The first pilot rows belong in chat the moment they exist — early rows are the trust down-payment; a polished CSV an hour later is not a substitute.
- **Explore cheap, exploit the winner — and use your range.** Probe candidate routes on small samples, in parallel inside one play (`shared/authoring.md` § Parallelism). Candidates mean the category, not a famous-name shortlist: `deepline tools list <category>` is complete recall, and sweeping every viable tool over a ~10-row batch costs a few credits while mapping the whole market — one default provider is an opinion. Report each route's marginal fill and cost as it lands, present the ranked options and let the customer pick the accuracy/cost operating point, then adjust the play to carry the winners as legs.
- **Checkpoint between phases** with a compact scoreboard: coverage, validation verdicts, credits spent, what's next. "12 emails: 6 valid, 6 verify_next" builds trust; a bare "12 emails" spends it.
- **Deliver increments.** Refresh the working CSV as stages complete; the final message reports deltas since the last checkpoint plus the final scorecard.
- **Ask when ambiguity is load-bearing.** When a segment label, threshold, ICP boundary, or "which of these two people did you mean" can change the run's outcome, ask the short question instead of guessing — one question is cheaper than a wrong full run, and a verified answer becomes golden truth. Don't ask about things the pilot can answer.

## Cross-cutting rules

The "why" matters more than the rule — knowing the failure mode lets you handle edge cases.

- **Pilot before scale.** Slice a pilot CSV (`head -2 rows.csv > pilot.csv`) or a 1-2 row `--input` subset first. A misshaped payload at scale burns credits across hundreds of rows before the issue is visible; a pilot exposes the same defect on row 1 for cents. Show real pilot rows and get explicit approval before the full paid run.
- **Over-provision, then filter.** For N rows, pull ~1.4×N at the top of funnel. Every phase has natural falloff, and companies providers can't find contacts for are the same ones without email coverage — coverage is a property of the company, not something retries overcome. Deliver the best N complete rows; let incomplete rows fall off.
- **When tools come up empty, return null.** Do not pattern-complete companies or contacts from training data. The output then looks like success but contains unverifiable rows that fail at outreach time. Null (or fewer rows) keeps the line between _found by tools_ and _inferred from memory_ visible.
- **Preserve provider evidence columns.** Responses include proof fields the user did not ask for: source URL, funding metadata, validation status, confidence, hiring counts, provenance. Verification runs on evidence, so trimming to display columns destroys the ability to trust the dataset. Asked for `name, title, company, email` and got `seniority`, `last_changed_at`, `source` too? Keep all seven.
- **All I/O through `ctx.*` (replay-safety).** Inside a `*.play.ts`, every non-deterministic operation goes through the runtime: `ctx.tools.execute`, `ctx.runPlay`, `ctx.csv`, `ctx.dataset`, `ctx.fetch`, `ctx.log`, `ctx.sleep`. The body re-executes during replay; `process.env`, `Date.now()`, `fs`, or raw `fetch` see different values on the second execution and corrupt the workflow.
- **Prebuilts are templates.** Search first. If it fits, run it; if only CSV headers differ, pass `--columns.<field> "<Header>"`. Copy (`deepline plays get <name> --source --out ./my-play.play.ts`) only for semantic changes — the copy preserves the provider order the prebuilt already got right.
- **One run per file while iterating.** Edit one local play file in place; the durable cache makes reruns cheap when names and keys stay stable. No `-v2`/`-fixed`/`-final` variants.
- **Outputs go in a project-local working directory.** Files in `/tmp/` are wiped on reboot and users have lost paid enrichment outputs there; credit-costing outputs belong in a directory the user controls. Set up a task-descriptive slug at step zero: `WORKDIR="deepline/data/<slug>" && mkdir -p "$WORKDIR"`. Keep custom `*.play.ts` files in the current workspace (where `node_modules/deepline` is available). After a run, export to the user-requested path with `deepline runs export <run-id> --out <path>` and report the exact path plus the run URL.
- **CSV inputs are runtime datasets.** `input: { csv: string }` pairs with `--csv leads.csv` and `ctx.csv(input.csv, { columns, required })`. The return value is a `PlayDataset` — pass it to `ctx.dataset`; use `count()`/`peek()` for bounded inspection. Row progress, retries, idempotency, and table output depend on the runtime owning the dataset.
