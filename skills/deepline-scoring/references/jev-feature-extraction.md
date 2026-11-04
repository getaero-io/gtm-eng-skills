# Typed feature extraction with Jev

Read this when an account or lead feature needs judgment over text: business model, customer type, workflow fit, "does this site say X". Jev (`typesafe-ai/jev`, the default model of Deepline's `ai_evaluate` tool) answers a fixed set of typed questions about one record in one call and returns calibrated probabilities instead of prose. It replaces free-form `deeplineagent`/LLM prompts and keyword-only matching for these features. It does not replace the evaluation, freeze and leakage rules in the rest of this skill: its outputs are features, not weights.

The tool name and model id are starting hints. Confirm the live contract with `deepline tools describe ai_evaluate` before a run.

## When to use it

| Feature                                                                                           | Use                               | Why                                                                                                |
| ------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------- |
| Business-model or website judgment (B2B vs B2C, billing model, regulated workflow, sells vs uses) | Jev                               | Keyword hits cannot tell a vendor selling "usage-based billing" from a company that bills that way |
| Exact phrase presence for the lexical layer                                                       | `analyze_signals_v2.py` concepts  | Deterministic and auditable; keep it as the raw observation                                        |
| Role counts from a title roster (`company_titles` is free)                                        | Deterministic regexes over titles | Counting does not need a model; regexes are reproducible and free                                  |
| Open-ended research or multi-step browsing                                                        | `deeplineagent`                   | Jev judges the state it is given; it does not fetch anything                                       |

Do not ask Jev a question a roster regex already answers, and do not feed a regex count back in as a Jev question. Two features measuring the same thing double-count it in the scorer.

## Why it is the default for typed judgments

- **Accuracy.** An internal benchmark ran Jev and Claude Haiku 4.5 on the same 24 webpage excerpts and 28 yes/no flags. Against agent-adjudicated reference labels (not human gold labels), agreement was 98.3% for Jev and 96.4% for Haiku, with 3 false positives for Jev and 13 for Haiku.
- **Cost.** Billing is computed from usage. One call answers about 25 questions together. In a 475-account run, total spend was about 11.5 Deepline credits including a 0.02-credit homepage scrape per row, so Jev was well under a hundredth of a credit per account. Check the current price with `deepline tools describe ai_evaluate`; quote Deepline credits only.
- **Speed.** About 2.5 s per call; the rate limit is 30 requests per second.

## Design the questions

One concept per question, phrased about the account itself. Pick the narrowest type:

| Type      | Use for                       | `criteria`                                                         | Output in `extracted_json[id]`                                                        |
| --------- | ----------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `boolean` | Present or absent trait       | none                                                               | `{type, probability}` (0 to 1)                                                        |
| `choice`  | Mutually exclusive categories | map of choice to meaning; include an `unknown`/`not_stated` option | `{type, choice, probabilities: {choice: p}}`                                          |
| `score`   | Ordered levels                | array of at least two levels, low to high                          | `{type, score, probabilities: {level_index: p}}`; `score` is the expected level index |

Write instructions the way the scorer will read the answer. "Does the company charge its own customers per seat?" separates billing model from "Does the site mention per-seat pricing?", which a billing-software vendor would also pass. Name the entity (the account, not its customers or vendors) and say what counts as evidence. Ask both directions for traits that are easy to conflate (B2B and B2C, rather than one forced binary). Keep the question ids stable; they become column names.

## Build the state

`state` is any JSON. Send what the question needs and nothing that encodes the outcome:

- company name, domain, and website text (homepage plus the relevant pages from the collection recipe), trimmed to about 14k characters;
- firmographics and a filtered roster of titles when a question depends on them;
- never won/lost labels, opportunity notes, AE fields or score explanations. Those are leakage here exactly as in the lexical layer.

An account with no collected text has no answer. Record it as unknown, not as probability 0.

## Read and threshold the output

Answers are at `toolResponse.rawV2.extracted_json`. Keep the raw boolean probability as the feature value and the `score` as a numeric; threshold only for display, rules or counts (0.5 by default, tuned on discovery data if a rule needs it). Read `choice` as a categorical. A missing answer is an error, not a zero.

## Validate before using a flag

Check each flag's prevalence by cohort (won, lost, open, random alternatives) on the discovery split. A flag that is true for about 90% of accounts in every cohort carries no information; drop it rather than let it add noise. Spot-check a few positives and negatives per flag against the source text, especially near the threshold. Then treat the surviving columns like any other candidate feature: the [scoring delivery](scoring-delivery.md) and [scorecard training](scorecard-training.md) rules decide whether they earn points.

## Freeze the question set

The question set is part of the extraction version. Hash the questions JSON (plus model id) when discovery ends and refuse to score with a different hash, alongside the analyzer manifest. Editing a question after looking at validation results consumes the holdout, as editing a keyword alias would.

## Run it

Batch from the CLI with the helper. It reads the `website` cell that `collect_sources.py` writes, keeps per-domain receipts keyed by the questions hash, writes `<out>.manifest.json`, and adds `jev__<id>` plus `coverage__jev` columns:

```bash
python3 scripts/jev_features.py --input accounts_sources.csv --questions questions.json \
  --state-cols company,industry --output accounts_jev.csv --limit 2          # pilot two rows first
python3 scripts/jev_features.py --input accounts_sources.csv --questions questions.json \
  --state-cols company,industry --output accounts_jev.csv --questions-sha256 <frozen hash>
python3 scripts/build_feature_matrix.py --input accounts_jev.csv --keywords keywords.json \
  --carry coverage__jev,jev__sells_b2b,jev__billing_model --output features.csv
```

In a Play, declare the questions `as const` (without it `type` widens to `string` and fails the typecheck against the `boolean | choice | score` union) and pass `staleAfterSeconds: 0` (`null` is rejected):

```ts
const questions = {
  sells_b2b: {
    type: 'boolean',
    instructions: 'Does the company sell mainly to businesses?',
  },
  billing_model: {
    type: 'choice',
    instructions: 'How does the company charge its own customers?',
    criteria: {
      subscription: 'Recurring plan',
      usage: 'Metered or per use',
      one_time: 'One-time purchase',
      not_stated: 'No evidence',
    },
  },
} as const;

const result = await rowCtx.tools.execute({
  id: 'ai_evaluate',
  tool: 'ai_evaluate',
  staleAfterSeconds: 0,
  input: {
    model: 'typesafe-ai/jev',
    questions,
    state: { company: row.company, domain: row.domain, website_text },
  },
});
const answers = result.toolResponse.rawV2.extracted_json;
```

Feed the answers to the shared pure scorer as features; never let a per-row model call produce the weights.
