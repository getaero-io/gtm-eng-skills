# Jev: what this skill relies on

Jev is reached through Deepline's `ai_evaluate` tool (`deepline tools describe ai_evaluate --json`),
which calls the Vercel AI Gateway evaluation model `typesafe-ai/jev`. What Jev is good and bad at is
from TypeSafe's published documentation (docs.typesafe.ai: the API reference, State, Confidence, the
composite-scoring pattern and the Jev 1.13 "jaggedness" page, last reviewed 2026-09-17). Re-read them
before changing the questions: the model is new.

## What Jev is

A decision model, not a chat model. You send a `state` and a map of typed `questions`; it
returns one typed answer per question with probabilities, and writes no text. This skill uses:

| TypeSafe's name | `ai_evaluate` type | Answer fields read |
|---|---|---|
| **Noul** (yes or no) | `boolean`, with `criteria: {true, false}` | `probability`: P(yes), 0 to 1 |
| **Choice** (one of a set of described options) | `choice`, with `criteria: {option: description}` | `choice`, `probabilities` (sum to 1) |

`ai_evaluate` returns no `confidence` field. This skill uses the margin between the top
probability and the runner-up as its own confidence; for a yes/no it equals `|2p − 1|`.

`instructions` may be an object: the question in one field, the data it refers to in others,
named in backticks. That is how each question carries only its own role. All questions for one
person go in one request.

## The call

| | |
|---|---|
| Tool | `ai_evaluate` (provider `deeplineagent`), billed by Deepline from the returned usage; no key of your own |
| Input | `{model: "typesafe-ai/jev", state, questions}` |
| Output | `result.answers` (one per question id), `result.response.modelId`, `usage.inputTokens`; in a play read from `toolResponse.rawV2`, from the CLI at `toolResponse.raw` |
| Model | `typesafe-ai/jev`, the only Jev id the gateway lists (checked 2026-09-30). It is not version-pinned on this route; every verdict records the `jev_model` that answered. The 0.6 and 0.4 thresholds were checked against jev-1.13.0 |
| Limits | 64,000 tokens a request; 32,000 for the state plus the longest question (the gateway's model card) |

## Price

- **The gateway lists $0.042 per million input tokens; output is free.** Deepline bills
  `ai_evaluate` from usage, so its charge shows in `deepline billing` rather than a fixed rate.
  Measured on jev-1.13.0 through TypeSafe's own API (2026-09, when this skill ran on Clay): about
  800 to 1,100 input tokens for a short invented profile, about 2,200 on average for real ones,
  so four to ten cents per thousand people at list price.
- A failed call (rate limit, upstream outage, billing) comes back as a typed tool error; the play
  catches it and the verdict is `failed` with the reason, so the person can be re-run.

## What Jev is bad at, from its own documentation, and what this skill does about it

| Documented weakness | Here |
|---|---|
| Comparing dates | Every date is compared in code; Jev sees "March 2021" and "no end date", never a comparison to make |
| Counting items in a list | One question per role, combined in code, as TypeSafe's own counting advice says |
| Literal reading | Each question states one condition and describes both answers; the "still held?" wording names the cases (several fractional roles, a founder working elsewhere) |
| Large state full of irrelevant detail | The state is the headline; each question carries only its role |
| Structural invariants not guaranteed | Each decision is asked one way; code enforces the rest (an ended role is never held) |
| Adversarial content | A profile written to argue its own case can move an answer. Say so |
