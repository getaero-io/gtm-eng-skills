# Retrieval fusion and reranking

The shared helper borrows the general Last30Days loop:

1. plan materially different ranked retrieval streams;
2. run streams concurrently with isolated outcomes;
3. normalize retrieved items onto stable keys;
4. accumulate raw weighted reciprocal rank globally;
5. bound the fused pool;
6. ask one batched judge for task relevance;
7. retain routes by marginal useful contribution;
8. enrich canonical survivors once;
9. apply delivery fact gates.

People, companies, sources, products, signals, and opaque entities use the same
kernel. Their route callbacks and final fact gates differ.

## RRF

For retrieved item `c`:

```text
rawRrf(c) = Σ routeWeight / (60 + nativeRank)
```

The sum runs over every route stream containing `c`. Do not normalize each
route before fusion. That would make every route's first result equally strong
and erase corroboration. `rrf` in the item output is normalized against
the plan's theoretical maximum only for display and score blending. `rawRrf`
preserves contribution semantics.

## Judge

The judge receives only the bounded fused shortlist in one prompt. It scores
task fit, not truth. Retrieved-item content is fenced and escaped as untrusted
data.
Unknown IDs are ignored. Missing IDs use deterministic fallback.

The default entity blend is:

```text
55% judge relevance
25% normalized RRF
10% adapter-local relevance
 5% freshness
 5% corroboration
```

Research sources use the source-ranking policy from `rerank.ts`. A task may
override the policy after calibration. Hard fact gates remain separate.

## Route selection

The route scorecard measures relevant yield, unique contribution, reliability,
novelty, and marginal Deepline credits. Greedy selection adds the route with
the best new item utility under the portfolio and credit caps.

The result is a route portfolio, not a winning pilot item or a serialized
program. `deepline.route_selection` names route IDs. The authored Play supplies
their executable code.

## Cost and speed

- Parallelize independent routes.
- Bound items per route.
- Bound the global pool before the judge.
- Use one judge call per nonempty row.
- Use `mapBounded` inside item fanout.
- Run expensive enrichment only on canonical survivors after promotion.
- Treat one source failure as a local outcome.

## Verification

Discovery eligibility and factual verification are different questions.
Cross-source agreement raises confidence but is not a universal gate. One
authoritative source may verify a declared fact; otherwise use the task's
explicit weak-source policy. Conflicts remain unresolved. A model cannot clear
a deterministic reject.

## Evaluation

Test unrelated task shapes and report item relevance, unique route
contribution, cost, provider-only positives, judge instability, and delivery
precision/recall when truth exists. A generic helper that needs a noun-specific
branch has failed.
