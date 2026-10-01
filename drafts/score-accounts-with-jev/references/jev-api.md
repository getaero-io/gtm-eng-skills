# Jev: what this skill relies on

Jev's behaviour is from TypeSafe's published documentation, read on 2026-09-28 (docs.typesafe.ai:
the API reference, Models, Confidence, the composite-scoring pattern and the Jev 1.13
"jaggedness" page). The route is Deepline's `ai_evaluate` tool (`deepline tools describe
ai_evaluate --json`), which calls Jev through the Vercel AI Gateway's evaluation API. Re-read both
before changing anything here: the model and the evaluation API are new.

## What Jev is

A decision model, not a chat model. You send a `state` (the record) and a map of typed `questions`;
it returns one typed answer per question with probabilities. It writes no text and gives no
explanations. Three question types: yes/no Nouls, categories (Choice) and scales (Score):

| Rubric kind | `ai_evaluate` type | Asks | Answer fields this skill reads |
|---|---|---|---|
| **noul** | `boolean` | a yes/no question; optional `criteria` `{true, false}` | `probability`: P(yes), 0 to 1. No confidence field; this skill uses `abs(2p - 1)` |
| **choice** | `choice` | pick one of up to 255 options; `criteria` maps each option to its description | `choice`, `probabilities` (per option, sum to 1, "when available") |
| **score** | `score` | place it on an ordered scale; `criteria` is the list of 2 to 10 described levels | `score` (fractional position, level 0 = first), `probabilities` keyed `"0"`, `"1"`, … |

All questions for one record go in **one request**; Jev reads the state once and answers every
question.

**Confidence.** TypeSafe's own API returns a `confidence` for Choice and Score; the evaluation API
behind `ai_evaluate` does not. This skill computes its own: the top probability minus the
runner-up, which for a yes/no is exactly `abs(2p - 1)`. With no distribution in the answer, the
confidence is blank, nothing is flagged for review, and the chosen option counts as certain.

## The route

| | |
|---|---|
| Tool | `ai_evaluate` (provider `deeplineagent`), billing managed by Deepline: no Jev key, no TypeSafe or OpenRouter account |
| Input | `{"model": "typesafe-ai/jev", "state": {…}, "questions": {…}}` |
| Output (CLI `tools execute --json`) | `toolResponse.raw.result.answers`, `toolResponse.raw.result.response.modelId`, `toolResponse.raw.usage.inputTokens` |
| Output (in a play) | `toolResponse.rawV2` (or `.rawV2.data` when `toolResponse.view === 'data'`): the same `result`, `usage`, `meta` |
| Model | `typesafe-ai/jev`, the only Jev id the gateway lists (checked 2026-09-30). It is **not version-pinned**: it moves when TypeSafe ships. Every result records the model id that answered (`jev_model`); re-check tier cut-offs after a release |
| Context | 64,000 tokens per request; 32,000 for the state plus the longest question (gateway listing) |

## Price and limits

- **Input $0.042 per million tokens, output free** at the gateway's list price. A rubric of three
  to eight questions with a few hundred words of record text is roughly 800 to 1,500 tokens, so a
  few cents per thousand records at that price. `ai_evaluate` is billed by Deepline "from returned
  usage"; Deepline's own rate is not published in `describe`, so read the real charge in
  `deepline billing` after the ten-record preview and quote that.
- Deepline's configured pacing for the provider is about 30 requests a second. A failed call
  reaches the play as a typed tool error with a `category`: `rate_limit`, `network`, `upstream`,
  `billing`, `authentication`, `validation`. The play catches it on that record only, which comes
  back `failed` with the reason and nothing else changes; re-run those records later.

## What Jev is bad at, from its own documentation, and what this skill does about it

| Documented weakness | Here |
|---|---|
| Arithmetic, counting, numeric comparison | Headcount, revenue, any number: a `bands` **rule**, computed in code |
| Comparing dates | "How long ago": a `days_since` rule, computed in code |
| Literal reading | Each question states its exact condition and describes every option |
| Large state full of irrelevant detail | Only the fields some asked question `reads` are sent |
| Indirection | Instructions point at the field by name in backticks, e.g. `` `description` `` |
| Score levels are weak for interpolation | A Score's position is only used for points (as in TypeSafe's composite-scoring example), never to reconstruct a number |
| Adversarial content in state | Record text is data; a record written to argue for its own classification can move the answer. Say so to the installer |

## Confidence floor

TypeSafe's guidance is to set thresholds by the cost of each kind of mistake, not a round number.
This skill uses one floor per rubric (0.6 unless changed): answers under it are listed in
`needs_review`, and still contribute their expected points, so an unsure answer moves the score less
than a sure one.
