---
name: deepline-plays
description: 'Use this skill for GTM work whose data route must be discovered or composed: finding companies or people, niche web research, provider comparison, SERP-to-source workflows, evidence-backed claims, or authoring a custom Deepline Play. It conditions search programs on the current task, current dataset, and live tool catalog; compares them quickly; closes only unresolved evidence gaps; and compiles the observed winner into deterministic execution. Skip when one named existing Play already satisfies the full contract or when the task is only copywriting.'
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

Turn an uncertain data job into one bounded experiment and one deterministic
Play. Hardcode truth conditions, not task-specific routes.

## Choose the smallest shape

| Situation                                            | Shape                                                                                                 |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| One listed Play satisfies the contract               | Describe, pilot, run it.                                                                              |
| One route is obvious but unverified                  | Compare it with one independent alternative.                                                          |
| Route depends on the current rows or source coverage | Run the dataset-conditioned search experiment below.                                                  |
| No rows exist yet                                    | Treat query partitions or source scopes as input units; discovered entities become result identities. |

Read `jobs/finding.md` only for live open-world company/people discovery and
`jobs/enriching.md` only for live known-row completion. Read
`references/provider-navigation.md` only when choosing or composing live tools.
Do not load these references for an offline design or a route already proven by
the current rows.

## The loop

Use one bounded loop for every unfamiliar shape:

```text
contract → sketch → probe → confirm → batch → challenge gaps → update waterfall
```

### 1. Freeze the contract inline

Define the requested row, required claims, evidence acceptance, target count,
and cohort checks before searching. A cohort check includes its denominator and
the verified claim that satisfies it. `90% of emitted rows` and `90% of all
otherwise-qualified people` are different products.

Keep user intelligence here. The helper must not invent whether a farm owner
needs LinkedIn coverage of 10% or a software engineer needs 90%.

### 2. Sketch the current dataset

Inspect the real columns, missingness, value shapes, and a small sample. Do not
choose easy rows by hand. `runSearchExperiment(...)` deterministically selects
diverse sentinel rows from missingness, types, low-cardinality values, and URL
hosts, then reserves untouched holdout rows.

For open-world work, make each input row a bounded source scope or meaningful
query partition. Geography, entity type, company size, role family, and time can
change the population. Cosmetic query paraphrases do not.

### 3. Propose executable information mechanisms

A `SearchProgram` is the smallest independently testable way to add useful
information. It may discover candidates, verify one evidence family, or close a
specific long-tail gap. It does not need to repeat the whole pipeline. The
shared ledger composes partial results by canonical entity and claim.

Start with two mechanisms:

1. `seed`: the highest-probability way to discover candidates or resolve known rows.
2. `evidence-closer`: an independent way to verify unresolved claims on those candidates.

Add up to three more only for an observed dataset stratum, an unmet consensus
class, or a materially cheaper scale path. These programs form a bounded pool,
not a hand-ordered waterfall. Never add a provider-name variant: Exa and Serper
may be transports to the same terminal pages and therefore one information
mechanism.

Subagents are optional. The parent freezes the contract, sketches the rows, and
starts the seed immediately. Use one parallel challenger wave only when the
source family, long-tail coverage, or scale path is genuinely uncertain. Give
one or two workers the contract and sample rows; ask each for one executable
mechanism. Do not form worker trees or ask agents to critique agents. The
runtime comparison, not prose voting, judges the mechanisms.

### 4. Bind only selected programs to live tools

Search by retrieval role, then inspect exact contracts:

```bash
deepline tools list
deepline tools list <category> --json
deepline tools search "<retrieval role and controls>" --json
deepline tools grep "<provider or literal capability>" --json
deepline tools describe <tool-id> --json
```

Ranked search returning nothing does not prove absence. Browse the exhaustive
category or literal grep before declaring a gap. Describe only the programs you
will execute, checking schema, result shape, limits, async behavior, and
Deepline credit ceiling.

Search can seed candidate URLs. Final facts must be refetched and bound inside
the Play. Once probes expose a stable directory, URL prefix, sitemap section,
query partition, entity key, or provider filter, compile that pattern to
`ctx.fetch`, batch search, map → select → batch scrape, capped crawl, or
provider pagination.

### 5. Author one experiment Play

Scaffold first. This is the fast path, not optional ceremony. It copies the one
editable Play plus portable helpers in one command:

```bash
for dir in "$PWD/.skills/deepline-plays" "$HOME/.claude/skills/deepline-plays" "$HOME/.agents/skills/deepline-plays"; do
  [ -f "$dir/scripts/scaffold-search-experiment.py" ] && SKILL_ROOT="$dir" && break
done
[ -n "${SKILL_ROOT:-}" ] || { echo "Could not find deepline-plays" >&2; exit 1; }
python3 "$SKILL_ROOT/scripts/scaffold-search-experiment.py" ./deepline/data/<task-slug> --name <task-slug>
```

Replace the scope rows, claim contract, and two literal program bodies in the
generated template. Copied helpers are mechanical dependencies, not authored
artifacts. Do not inspect or rewrite them unless `plays check` reports a helper
defect. The scaffold demonstrates both the input shape and output access:
`verifiedSearchClaimValue(result, claimId)` returns an accepted value or null,
while `result.row` retains the original input. Do not read helper types to map
outputs. Its commented `ctx.tools.execute` + `bindLiteralClaim` body is the
complete tool-to-bound-claim pattern; replace the described IDs and fields
instead of searching copied fixtures for syntax. Edit once, run one check, and
reread only the failing boundary. The authoring surface is deliberately small:

```ts
const experiment = await runSearchExperiment({
  ctx,
  rows,
  definition: {
    contract: {
      rowKey: 'domain',
      targetRows: 20,
      claims: [
        {
          id: 'current_owner',
          question: 'Who currently owns this company?',
          minimumIndependentEvidenceClasses: 2,
        },
        {
          id: 'linkedin_url',
          question: 'What is the operator LinkedIn URL?',
          required: false,
        },
      ],
      cohortChecks: [
        {
          id: 'linkedin_coverage',
          minimumRatio: 0.1,
          denominator: 'complete_results',
          verifiedClaimId: 'linkedin_url',
        },
      ],
    },
    programs: [seedProgram, evidenceCloser],
  },
});
```

Each `SearchProgram` contains only `id`, `hypothesis`, a per-attempt call cap,
an optional catalog/quote credit ceiling, and
`run({ ctx, row, gaps, candidates, phase })`. A discovery mechanism may
return only identity evidence. A verifier may consume `candidates` and return
only the claims named by `gaps`. Keep tool IDs and calls literal in these bodies
so `plays check` and reviewers can see the graph. The helper composes partial
results, constructs receipts, and owns all accounting.

```ts
return {
  totalCalls: 1,
  // Set attempt.deeplineCredits only from its receipt. If unavailable, put the
  // described/quoted ceiling on program.maximumDeeplineCreditsPerAttempt.
  results: [
    {
      resultKey: candidate.id,
      canonicalEntityKey: candidate.canonicalUrl,
      claims: {
        current_owner: { value: candidate.name, evidence: [boundEvidence] },
      },
    },
  ],
};
```

### 6. Let the experiment allocate work

The helper performs this sequence in one run:

1. Run every program concurrently on one or two shared diverse rows. This is the only broad parallel wave.
2. Retry an incomplete attempt once, in any phase, only when another program materially changed that unit's candidate/evidence ledger and gaps remain.
3. Rank by complete rows, verified required claims, and cohort coverage. Among equally valid portfolios, prefer lower observed Deepline credits, then fewer calls. Extra providers do not win merely by adding evidence after the frozen consensus requirement is already satisfied. Retain any candidate producer causally required by a winner.
4. Run producers before their consumers over the remaining pilot rows.
5. Invoke alternatives only for rows and claims still unresolved, including failed cohort claims.
6. Freeze the selected order and test untouched holdout rows.
7. Skip exploitation when holdout fails; otherwise run bounded batches in selected order and stop at the target.
8. When a batch still has gaps, compare unused programs together on one shared unresolved row. A challenger joins later batches, or replaces a noncausal fallback when the waterfall is full, only when its bound evidence improves verified coverage. Preserve the primary and observed producer/consumer chains. A program that has never completed a result retires after two live challenge rows; a displaced route already proven on this dataset remains eligible for later gaps.

There is no agent reflection loop. The Play learns a waterfall from observed
rows while it runs. A program/unit pair runs at most once normally and once more
after new evidence unlocks it. Parallelism buys route information on tiny shared
waves; best-first gap closure prevents paying that cost across the full dataset.

Every invocation becomes exactly one of `verified`, `rejected`, `source_miss`,
or `adapter_failure`. Empty results are source misses. Thrown adapters are
failures. No author-maintained observation arrays or scorecards exist.

## Evidence and consensus

Bind final facts to literal source text with
`bindResearchEvidenceToSource(...)`. The experiment groups contributions by
canonical entity and claim value, combines evidence across programs, and asks
the claim contract to verify the result. Conflicting supported values reject
the row.

Consensus counts independent terminal evidence, not transports. Two search
vendors returning one LinkedIn page contribute one lineage. An official page
and a public registry can contribute two. Set `allowAuthoritativeSingle` only
when one authoritative source genuinely settles the claim.

Fallback diversity is judged from observed result identities and terminal
lineages. Provider labels and hypotheses cannot manufacture diversity. When
the common comparison returns no evidence at all, alternatives still receive a
bounded pilot chance so one unlucky sentinel cannot end discovery.

Use `extractGroundedPersonCandidates(...)` only to nominate names from a bound
excerpt. Deterministic identity, role, employer, and freshness checks still
decide the claim. An LLM may reject already-bound candidates through
`applyRejectOnlyDecision(...)`; it cannot add facts or evidence.

## Run and deliver

```bash
deepline billing balance --json
deepline plays check ./deepline/data/<task-slug>/<task-slug>.play.ts
deepline plays run ./deepline/data/<task-slug>/<task-slug>.play.ts --input @input.json --watch
deepline runs get <run-id> --full --json
deepline runs export <run-id> --dataset <final-dataset-path> --out <output>.csv
deepline billing balance --json
```

If run admission fails before a run ID or tool call with
`WORKSPACE_STORAGE_NOT_READY`, `needs_storage_owner_repair`, or another control
plane/storage contract error, retry the identical command once only when the
CLI says completed work is reusable. If it repeats, stop and report the
infrastructure blocker. Do not rewrite the Play, remove datasets, or swap
providers: none of those can change a pre-execution admission failure.

Deliver complete rows, source URLs/excerpts, unresolved rows, initial and final
waterfalls, live adaptations, attempt ledger, holdout result, run ID, and
opening-minus-closing Deepline credits. Also report `experiment.leverage`:
verified complete rows, calls, exhaustive call baseline, calls avoided, and rows
per attributed Deepline credit. Show `experiment.costCoverageFrontier` so the
user can see the non-dominated provider portfolios observed on the same
comparison rows: more verified coverage may cost more, while redundant spend
falls off the frontier. The opening-minus-closing billing delta is the
authoritative whole-run cost. Unknown per-attempt credits remain unknown; they
stay visible on the frontier and never become a fabricated zero or invalidate
a true claim.

## Gates

- Before probing: contract, denominators, row key, and call caps are frozen.
- Before promotion: every required fact has a validated bound receipt and every cohort check passes.
- Before exploitation: untouched holdout confirms the selected order.
- Before declaring absence: the relevant catalog category and an independent source mechanism were tried, not merely a paraphrased query.
