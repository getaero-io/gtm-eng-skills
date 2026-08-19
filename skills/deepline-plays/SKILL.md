---
name: deepline-plays
description: 'Use this skill for Deepline GTM jobs that search, enrich, score, collect signals, or automate a workflow: “find companies or people,” “enrich this CSV,” “find emails or LinkedIn,” “compare providers,” “build a waterfall,” “create a webhook or cron,” or “write a Play.” Start with the live Play catalog. When no listed Play satisfies the full evidence, coverage, and cost contract, run a bounded explore/exploit experiment that learns a deterministic route from the current data. Skip pure copywriting and non-GTM research.'
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

The **JTBD** defines truth. The dataset exposes uncertainty. The catalog supplies
components. The experiment learns a route. The Play is the durable artifact.

```text
contract → probe → waterfall → frontier
```

## Vocabulary

| Term                | Meaning                                                                  |
| ------------------- | ------------------------------------------------------------------------ |
| **JTBD**            | The population, outcome, and reason the user needs it.                   |
| **Contract**        | A mechanical test for a complete row and a complete cohort.              |
| **Program**         | One executable information move: provider, Play, fetch, or local code.   |
| **Mechanism**       | An end-to-end information path from input uncertainty to bound evidence. |
| **Candidate**       | A plausible value that has not passed the final acceptance contract.     |
| **Seam**            | An inspectable handoff between stages: entity key, URL, record, excerpt. |
| **Lineage**         | Ownership of the terminal source, independent of the transport used.     |
| **Waterfall**       | The observed, dependency-closed order used to exploit the dataset.       |
| **Frontier**        | Valid observed portfolios where coverage cannot improve without cost.    |
| **Absence receipt** | Distinct bounded attempts exhausted before returning a null.             |

A provider implements a stage; it is not itself a mechanism. Provider siblings
are still useful coverage, latency, and Deepline-credit competitors. They count
as separate routes, but only distinct terminal lineages create claim consensus.
Local code, direct fetches, and deterministic tests are programs too.

One untested path is not an experiment. For uncertain work, compare at least
two executable programs on shared units, then apply an observed winner beyond
the comparison surface. Exploration buys route information. Exploitation buys
completed rows.

## Start from the JTBD

Write the JTBD as **unit + decision + acceptance + scale**. It selects the
contract; providers come later.

| JTBD                | What is unknown?                | Contract shape                                                        |
| ------------------- | ------------------------------- | --------------------------------------------------------------------- |
| **Search**          | Which entities belong?          | Bounded population scopes; unique identity plus qualifying evidence   |
| **Enrich**          | What is true of each known row? | Frozen input identity; required claims completed for that exact row   |
| **Signals**         | What changed, for whom, when?   | Subject, predicate, time window, dated source; bounded absence policy |
| **Score / qualify** | What decision follows?          | Required facts preserved beside a reproducible verdict                |
| **Automate**        | When should stages run?         | Trigger, stage graph, review boundary, and replay policy              |
| **Activate / sync** | Was the action applied?         | Dry-run plan or idempotent side effect with an execution receipt      |

Search discovers rows. Enrichment completes rows. Signals attach time-bounded
claims. Scoring derives a decision from claims. Activation consumes accepted
rows. One job may compose these stages, but each keeps its own completion test.

A composite JTBD is a **stage graph**. Reuse proven Plays for known edges and
explore only edges whose coverage, evidence, or economics remain uncertain.

## Choose the execution shape

1. **Exact proven Play:** search and describe the live catalog. Pilot and run a
   Play whose full acceptance contract and fallback behavior are already known.
2. **Known route:** use the ordinary finding, enriching, or automating recipe
   when only the live name, input mapping, or composition is uncertain.
3. **Offline/local route:** inspect local data and author with catalog
   placeholders. Local transforms and design-only work require no live browse.
4. **Uncertain live route:** use the experiment below when coverage, evidence,
   provider composition, or the cheapest valid waterfall must be learned.

- An exact Play may be the seed. If its coverage, acceptance, or economics are
  uncertain on these rows, compare it with another program before scaling.
- Every shape needs a Deepline credit envelope and stop rule. Use a Play quote
  or catalog ceiling; if absent, say `unknown`, never zero.
- `--from provider:<id>` is a live binding. Describe that ID first. Offline,
  use `CATALOG_REQUIRED` seams instead of a remembered provider.
- Read `--help` and schemas; do not probe required arguments by failing calls.

## 1. Freeze the contract

Write the row identity, required claims, accepted evidence, freshness and
reference date, independence rule, cohort denominators, target count, and
probe/exploitation caps before searching. Cost chooses among valid results; it
never makes an unsupported result valid.
Set one optional `maximumDeeplineCredits` on the experiment when the user gives
a spend limit. Every program then needs a described per-attempt ceiling. The
helper admits only waves that fit the remaining conservative exposure.
Optional claims stay in the same `claims` array with `required: false`; there is
no separate `optionalClaims` contract surface.
Existing evidence is a free mechanism: preserve accepted fields and buy only
unresolved claims.

Use only `pilot_units` (every frozen input), `eligible_results` (every
otherwise-qualified emitted candidate), or `complete_results` (complete rows,
for optional-field coverage).

`targetRows` is a stopping count, not a denominator. A check such as “LinkedIn
on 90% of supplied engineers” uses `pilot_units`; “hiring signal on 10% of
complete farm owners” uses `complete_results`.

Set `targetRows` to the user’s explicit delivery target when they give one.
Otherwise set it to every supplied or bounded-scope unit and keep recovering
gaps. A pass floor such as “three of five is fine” is an acceptable outcome,
not permission to silently stop at three when the user asked for maximum
coverage.

For open-world search, make each input unit a bounded population partition or
source scope. For known-row enrichment, preserve the exact supplied rows. Let
the helper select diverse sentinels and untouched holdout units.

Bind facts first. A model may classify or reject bound facts. It cannot add
facts, sources, or consensus. Use `applyRejectOnlyDecision(...)` when a model
filters grounded candidates.

A miss is information, not absence. Return a null only after materially
different eligible programs have been tried within the frozen budget. Preserve
their typed source misses, rejections, adapter failures, and remaining dormant
programs as the absence receipt. Do not praise calls avoided while the target
is unmet and cheap eligible programs remain.

## 2. Browse the capability map when the route is live

Browse before searching by name:

```bash
deepline tools list
deepline tools list <category> --json
deepline tools search "<information role and controls>" --json
deepline tools describe <tool-id> --json
```

Bare `tools list` is the capability map. It shows the live categories; listing
one category shows every provider tool beneath it. Useful families include:

| Information need      | Capability families to inspect                                |
| --------------------- | ------------------------------------------------------------- |
| Candidate populations | Company, people, jobs, local business, registry search        |
| Identity and contact  | Resolution, reverse lookup, email, phone, profile             |
| Known-entity facts    | Person, company, firmographic, employment enrichment          |
| Public evidence       | Web/SERP research, page fetch, scrape, map, crawl, extraction |
| Time-varying signals  | Jobs, news, funding, hiring, technology, ads, social activity |
| Private evidence      | CRM, warehouse, product, intent, first-party events           |
| Activation            | Sequencing, CRM writes, audiences, workflow automation        |

Treat the category listing as the candidate pool. Preserve every relevant
action as a possible program before narrowing. Describe the small initial wave
and any program whose input/output mapping must be compiled; keep the rest as a
dormant catalog shortlist. Ranked search returning nothing is not a catalog
census; inspect the relevant category before recording a catalog gap.

Record whether the action charges Deepline credits on every attempt, only on a
returned result, or on an unknown basis. Confirmed uncharged misses support
broader challenge waves. Unknown cost remains unknown and uses the described
ceiling; it never becomes zero. Copy the described unit into each program as
`billingUnit: 'call' | 'result' | 'unknown'`. The helper counts a confirmed
result-priced miss as zero in its catalog cost estimate while keeping receipt
spend unknown and successful unattributed calls at their catalog ceiling.

Search discovers where to look. Retrieval establishes what the source says.
Use the recurring transformation **probe → pattern → scale**: discover a useful
source or query shape, identify its durable seam, then compile repeated work to
the cheapest bounded retrieval path.

The authoring agent may use its browser, terminal, or search tools to seed sites
and query shapes quickly. Accepted facts must be retrieved and bound inside the
Play so rows retain receipts and replay paths.

Read `references/provider-navigation.md` only when the source geometry remains
unclear after the category browse or a probe must be compiled into a scale path.

## 3. Propose mechanisms

Inventory broadly, execute narrowly. Start the active wave with:

1. **Seed:** the highest-probability candidate or claim-producing mechanism.
2. **Closer:** an independent mechanism for the seed's unresolved evidence.

Register every viable challenger the agent can bind correctly, including
provider siblings with different coverage or economics. The helper probes only
a small maximally heterogeneous subset; the rest remain dormant until a gap
appears. A larger catalog should expand this dormant action space, not expand
every-row spend. State each program as:

```text
hypothesis → diversity features → seams → terminal lineage → call/credit cap → expected miss
```

For an uncertain job, do a short source-first pass before writing code. It
produces 5–10 compact strategy cards from actual registries, pages, private
joins, and source artifacts; the catalog maps those cards to executable
programs. Read `references/strategy-pre-research.md`. This is an authoring
step, not a runtime agent or a new configuration language.

Use `diversityFeatures` for durable information shape, such as
`structured-index`, `pivot:name+domain`, `first-party-web`, or
`role:acceptance-test`. Do not put the provider name there. Two APIs reaching
the same terminal pages may still compete on coverage and economics, but they
form one evidence lineage. One provider can support several mechanisms when its
actions reach genuinely different corpora.

### Subagents: strategy authors

The parent owns the contract, sample, catalog snapshot, and final pool. Author
the seed first. Use one or two subagents only when multiple source geometries
remain plausible and a wrong choice costs more than one short ideation wave.
Give each the same contract and an assigned source lane. They return one card
and one ordinary TypeScript strategy block. They do not execute providers. The
parent rejects false diversity, then binds the admitted blocks into one
deterministic experiment; subagents propose routes, not verdicts.

## 4. Author one experiment Play

Run the bundled scaffold from the installed skill root:

```bash
python3 <skill-root>/scripts/scaffold-search-experiment.py \
  ./deepline/data/<task-slug> --name <task-slug>
```

Edit four seams: scope rows, contract, literal strategy blocks, and final output
mapping. A strategy block is ordinary async TypeScript: it can call tools,
fetch a source, or compose local code. The generated template owns pilot/rank/
holdout/exploit/retry; `boundClaim`, `found`, and `attempt` only make the
evidence/output boundary mechanical. Copied helpers are runtime dependencies.

Default to inline strategy blocks in the one generated Play: this is the
fastest way to author and run 3–5 candidates locally. Promote a stable block
to a reusable **scalar child Play** only when reuse or delegated ownership is
worth a publish step. The parent must call each child with a literal
`ctx.runPlay(...)`; a child receives one row and returns a scalar attempt, so it
cannot own `ctx.csv`, `ctx.dataset`, waits, or a batch run. The parent remains
the single durable experiment and final dataset.

Leave `pilotUnitCount`, `comparisonUnitCount`, and `holdoutUnitCount` unset
unless the user supplied a split. The automatic topology selects diverse
sentinels, adds holdout when the dataset is large enough, and reserves at least
one later row for exploitation. Even a two-row task compares on one row and
applies what it learned to the other; comparing every row is not exploitation.

The helper accepts a broad registered pool, chooses a small heterogeneous shared
wave, composes partial evidence by canonical entity, and retains causal
producers. It confirms the selected waterfall on holdout, exploits valid gaps,
and challenges failures from any phase in bounded heterogeneous waves. A
rejected acceptance test reopens the row; untried programs remain dormant.

Keep the two identities separate. `rowKey` identifies the supplied input unit.
Each emitted `canonicalEntityKey` identifies the discovered candidate itself:
normalized email, domain, profile URL, source URL, or stable record ID. Never
key two different candidates by the input row. That collapses disagreement into
one poisoned ledger entry and leaves acceptance programs nothing testable.
Acceptance programs should inspect each candidate identity within their cap;
one rejected candidate does not reject its siblings or close the row.
Do not hard-code `candidates[0]`. Deterministically prioritize, then test the
bounded slice until one passes or the cap is consumed. Emit each tested
candidate under the same canonical identity: an accepted claim on success, or
typed `hardCheckFailures` such as `rejected:catch_all` on failure. Returning an
empty array loses the rejection receipt and can repeat the wrong work.
Different finders emitting different candidate identities is not itself a hard
failure. Keep both alternatives testable or seek another finder. Use a hard
failure only when an acceptance mechanism rejects that exact candidate, returns
a different value, or proves a contract mismatch. Then disagreement on the
same candidate remains unresolved without poisoning its siblings.

Each attempt reports calls and exactly one outcome per unit: `verified`,
`rejected`, `source_miss`, or `adapter_failure`. Use receipt-attributed credits
when available and catalog ceilings otherwise; unknown cost stays unknown.
When `maximumDeeplineCredits` is set, a blocked next wave stops with
`budget_exhausted`; a described result-priced miss releases its reserved
ceiling after returning empty.
Leave `maxFallbacks` unset. It bounds the active dependency-closed waterfall;
it does not bound total spend or challenge count. Setting it to zero disables
dormant challengers and is invalid while any registered program is dormant.

## 5. Run and deliver the frontier

```bash
deepline billing balance --json
deepline plays check ./deepline/data/<task-slug>/<task-slug>.play.ts
deepline plays run ./deepline/data/<task-slug>/<task-slug>.play.ts --input @input.json --watch
deepline runs get <run-id> --full --json
deepline runs export <run-id> --dataset <final-dataset-path> --out <output>.csv
deepline billing balance --json
```

Deliver complete rows with bound sources, typed unresolved rows, initial and
final waterfalls, explored and remaining programs, live adaptations, holdout
result, attempt ledger, run ID, calls avoided, and `costCoverageFrontier`.
Quality gates precede economics;
among valid portfolios prefer lower observed Deepline credits, then fewer
calls. Opening balance minus closing balance is the authoritative whole-run
cost. Never expose provider spend.

## Conditional references

| Condition                                          | Read                                  |
| -------------------------------------------------- | ------------------------------------- |
| Open-world company or people discovery             | `jobs/finding.md`                     |
| Known-row enrichment or scoring                    | `jobs/enriching.md`                   |
| Webhook, cron, review gate, dry-run, activation    | `jobs/automating.md`                  |
| Tool choice, source geometry, or scale pattern     | `references/provider-navigation.md`   |
| Source-first strategy generation or subagent lanes | `references/strategy-pre-research.md` |
| Failed, stalled, empty, or misshapen run           | `references/debugging.md`             |
| General Play syntax outside the scaffold           | `shared/authoring.md`                 |
| Replay, receipts, resume, and cost accounting      | `shared/durability.md`                |
