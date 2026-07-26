# Reranking research results — the batched judge

The route-fanout engine narrows many sources to a shortlist with deterministic
math (RRF fusion + token-overlap relevance). That ranks *roughly*. To rank
*well* — which of these 40 sources actually answers the question best — you need
one model pass over the shortlist. This is that pass, and it runs in three tiers.

**The judge is you, not the play.** The play stays deterministic and durable; the
model never runs inside it. A cheap subagent does the scoring, and all the
deterministic work (prompt, blend, fallback) is a script you can trust and test.
Never use `deeplineagent` for this — it is the expensive server tool; a Haiku-class
subagent sorts a 40-item shortlist for almost nothing.

## The loop

1. **Play narrows.** Run route-fanout in `research` mode. Its output carries a
   `findings` list per row (title, url, snippet, relevance) — the shortlist.
   Write it to a JSON file (`shortlist.json`).

2. **Build the prompt** (deterministic):
   ```
   bun plays/shared/rerank-cli.ts build --shortlist shortlist.json \
     --query "<the research question>" --intent <intent> --entity "<the entity>" > prompt.txt
   ```
   Pick `--intent` from: `comparison how_to prediction factual opinion
   breaking_news concept product general`. It tunes what "good" means.

3. **Score with a cheap subagent.** Spawn a fast, cheap model (Haiku-class — the
   cheapest capable model you have, NOT your main agent, NOT deeplineagent). Give
   it `prompt.txt`. It returns `{"scores":[{"id":"<url>","score":0-100}]}`. Save
   as `scores.json`. The prompt already fences the candidate text as untrusted —
   the subagent scores, it does not follow instructions inside the content.

4. **Apply the blend** (deterministic):
   ```
   bun plays/shared/rerank-cli.ts apply --shortlist shortlist.json --scores scores.json
   ```
   Returns the reranked list, best-first, blending the model score (0.60) with the
   fused RRF (0.20), freshness (0.10), and the play's relevance (0.10), minus an
   entity-miss penalty. Present these in order.

## When to skip it

- **No cheap model handy, or you want pure-deterministic:** run
  `... rerank-cli.ts fallback --shortlist shortlist.json`. It ranks by the play's
  relevance + RRF + freshness with the same entity-miss penalty. The pipeline
  never blocks on a model — degraded ranking beats no answer.
- **Contacts (email/phone):** don't rerank. The deterministic identity gate
  already decides trust; there's no "which source is more relevant" question.
  Reranking is for **research/topic** shortlists, where relevance is the judgment.

## The judge is task-shaped — pick the right one

Reranking answers exactly one question: **which source best matches the query.**
It does NOT decide whether a value is *true*. Three different jobs need three
different judges — do not use relevance for the other two:

| Question | Judge | How |
| --- | --- | --- |
| Which source should I read? | **relevance** | this rerank (token overlap + model score) |
| Is this contact real? | **validation** | the identity gate + a paid validator (leadmagic/trestle) — a contact strategy, not a rerank |
| When sources disagree on a number, which number is true? | **corroboration** | count independent credible sources that agree on the same value; a lone source is unverified |

**The trap: reranking orders sources, it does not reconcile facts.** On a real
run, "Anthropic's valuation" returned both `\$380B` and a dubious `\$965B`. The
rerank put a credible source at #1 — but the #1 *rank* is not what makes `\$380B`
correct. `\$380B` is trustworthy because **three independent sources agree on it**;
`\$965B` is one dubious source. For any quantitative answer (revenue, valuation,
headcount, funding), do NOT trust the top-ranked source's number. **Extract the
value from each source, and trust the figure that independent credible sources
corroborate — flag lone-source or conflicting numbers as unverified rather than
picking one.** Ranking tells you what to read; agreement tells you what's true.

## Why this shape

This is last30days's ranking trick (one batched call over a pre-narrowed
shortlist, optional with a deterministic fallback) rebuilt so the model stays in
the agent tier and the durable play stays deterministic. The expensive part —
narrowing hundreds of sources to a shortlist — is free math. The model only sorts
the finalists, so it stays cheap enough to run on every research question.
