# Writing outreach

Per-row copy generation, sequence design, qualification language, and scoring. The deliverable is text columns on rows that already have research and identity context.

This doc does **not** cover finding people or filling emails — those live in `jobs/finding-companies-and-contacts.md` and `jobs/enriching-and-researching.md` and must complete before this doc is useful. Outreach generation without research columns produces mail-merge.

## When you are in this doc

You have rows with name, title, company, identity, and **at least one research or context column** ("what they sell," "recent funding," "pain points," "tier"). The user phrasing is something like:

- "write a cold email for each of these leads"
- "draft a 4-step sequence for the Tier 1 contacts"
- "write qualification copy for each row explaining why they are a good fit"
- "personalize a first line per contact based on the research column"

If the rows do not have research columns yet, route to `jobs/enriching-and-researching.md` (research section) first. Trying to write personalized outreach off `name + title + company` alone produces template output regardless of how good the prompt is.

## Choose your approach

| You need                                                           | Pattern category                                                                  | Discovery                                       |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------- | ----------------------------------------------- |
| One personalized snippet per row (subject, first line, value prop) | single-prompt `deeplineagent` with output `jsonSchema`                            | `deepline tools describe deeplineagent --json`  |
| A multi-step sequence per row (4 emails, each with subject + body) | `deeplineagent` with array `jsonSchema`                                           | (same)                                          |
| ICP fit / tier classification with reasoning                       | `deeplineagent` with enum `jsonSchema`                                            | (same)                                          |
| Score rows on multiple criteria                                    | `deeplineagent` with object `jsonSchema` returning `{score, fit_band, rationale}` | (same)                                          |
| Deterministic template merge (no AI)                               | `run_javascript` with the template inline                                         | `deepline tools describe run_javascript --json` |

`deeplineagent` is the right tool for almost all generative outreach work. `run_javascript` is for the rare case where the user wants strict template merge (e.g. a field substitution with no rewriting) — and at that point, the question is whether the user wants AI-assisted personalization at all.

## Durable rules

### Personalization requires a row-specific signal

Every email must reference something specific to the row: a product the company makes, a pain point, recent news, a use case, the persona's actual responsibility — not just `{{first_name}}` and `{{company_name}}` in a template. If the only row-specific data feeding the prompt is name + title + company, the output is mail-merge regardless of how the prompt is phrased. The fix is upstream: enrich the row with a research column first, then write copy that conditions on it.

### Research happens in enriching-and-researching, not here

A common failure mode is writing the research and the copy in the same `deeplineagent` prompt: "Look up Acme and write me a personalized email." That conflates two responsibilities, makes the output non-cacheable, and produces shallow research because the prompt is optimized for copy quality, not factual depth. Research belongs in a prior `ctx.map` stage (or a prior CLI run) that produces a `company_research` or `pain_points` column. The copy stage then _reads_ that column.

### Structured output for anything downstream will read

When the output is one or more emails, sequences, or qualification objects, use `jsonSchema`. _Failure mode:_ free-text output for sequences makes the user (or the next stage) parse N emails out of a blob, and any malformed run silently breaks the parse. A schema enforces shape at write time and gives downstream stages a clean contract.

```typescript
// 4-step sequence schema
jsonSchema: {
  type: 'object',
  properties: {
    steps: {
      type: 'array',
      minItems: 4,
      maxItems: 4,
      items: {
        type: 'object',
        properties: {
          step: { type: 'integer' },
          subject: { type: 'string' },
          coreValueProp: { type: 'string' },
          email: { type: 'string' },
        },
        required: ['step', 'subject', 'coreValueProp', 'email'],
      },
    },
  },
  required: ['steps'],
  additionalProperties: false,
}
```

### Qualification is evidence-based and uses high recall

When classifying rows against an ICP (Tier 1 / 2 / 3, fit / no-fit, score 0-100), build the prompt around _only_ the provided context — do not let the model hallucinate evidence. Mark `Unknown` when evidence is missing, not a low score. _Failure mode:_ a model asked "is this lead a fit?" without explicit instruction to ground on context will fabricate plausible-sounding reasons, and the resulting tiers correlate poorly with reality.

Default to high recall: when evidence is borderline, lean toward the higher tier. Outreach is cheaper than missing a real prospect; the noise is filtered downstream by reply rate.

### Carry lineage end-to-end

Preserve provider provenance, research source columns, and identity columns alongside the generated copy. _Failure mode:_ a CSV of generated emails with no link back to which research informed each one is impossible to QA, debug, or A/B test. Every row should carry the inputs that produced its copy, not just the copy itself.

### Structured outputs are wrapped — flatten before re-prompting

`deeplineagent` columns with `jsonSchema` are stored wrapped in an AI result envelope. Direct interpolation `{{column}}` into another `deeplineagent` prompt usually works, but field-level access `{{column.subject}}` does not. If a downstream step needs `column.subject`, add a `run_javascript` flatten pass first that emits a scalar column. (Same rule as in `jobs/enriching-and-researching.md`.)

## Patterns

### One-shot per-row personalization

The simplest pattern: one prompt produces one output object per row. Use when the deliverable is a single email or a single first-line snippet.

```typescript
const personalized = await ctx.tools.execute({
  id: 'personalized_email',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Write a cold email to ${row.first_name} ${row.last_name} (${row.title}) at ${row.company_name}.
Pain point context: ${row.pain_points}.
Open with a one-sentence reference to the pain point. Keep the email under 90 words.
Return JSON with subject, first_line, body.`,
    jsonSchema: {
      type: 'object',
      properties: {
        subject: { type: 'string' },
        first_line: { type: 'string' },
        body: { type: 'string' },
      },
      required: ['subject', 'first_line', 'body'],
      additionalProperties: false,
    },
  },
  description: 'Write one personalized cold email for this row.',
});
```

The prompt explicitly references `row.pain_points` as the personalization signal — that column was produced upstream in `jobs/enriching-and-researching.md`.

### Multi-step sequence

When the user wants a 3-5 email sequence, generate it as one structured output rather than calling the model N times. The model can plan the arc better when it sees all steps at once, and the schema enforces a fixed number of steps.

```typescript
const sequence = await ctx.tools.execute({
  id: 'outbound_sequence',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Design a 4-step outbound sequence for ${row.first_name} at ${row.company_name}.
Persona: ${row.title}. Pain: ${row.pain_points}.
Step 1: hook + value prop. Step 2: proof / case study. Step 3: low-friction CTA. Step 4: breakup.
Each step under 90 words.`,
    jsonSchema: {
      /* see schema in Durable rules section */
    },
  },
  description: 'Generate a multi-step outbound sequence.',
});
```

### Tier classification with reasoning

Qualification is just a structured output with an enum tier and a free-text rationale.

```typescript
const tier = await ctx.tools.execute({
  id: 'lead_tier',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Using only the provided context, classify ${row.company_name} as a fit for our ICP.
ICP: ${input.icp_description}.
Context: ${row.company_research}.
If the context does not contain enough evidence to decide, return tier "unknown".`,
    jsonSchema: {
      type: 'object',
      properties: {
        tier: {
          type: 'string',
          enum: ['high_fit', 'medium_fit', 'low_fit', 'unknown'],
        },
        rationale: { type: 'string' },
        evidence_used: { type: 'array', items: { type: 'string' } },
      },
      required: ['tier', 'rationale', 'evidence_used'],
      additionalProperties: false,
    },
  },
  description: 'Classify lead fit for outbound prioritization.',
});
```

`evidence_used` is a soft accountability column — it makes the model surface which context fields it actually used, which catches the failure mode of hallucinated reasoning.

### Scoring with multiple criteria

When the user wants a 0-100 score against multiple criteria, return both the composite score and the per-criterion breakdown.

```typescript
const score = await ctx.tools.execute({
  id: 'lead_score',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Score this lead against the ICP on a 0-100 scale.
ICP criteria: ${input.icp_description}.
Lead context: ${row.company_research}, role: ${row.title}.
Return the composite score, fit_band (high|medium|low|unknown), and a per-criterion breakdown.`,
    jsonSchema: {
      type: 'object',
      properties: {
        score: { type: 'integer', minimum: 0, maximum: 100 },
        fit_band: {
          type: 'string',
          enum: ['high', 'medium', 'low', 'unknown'],
        },
        criteria: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              criterion: { type: 'string' },
              met: { type: 'boolean' },
              note: { type: 'string' },
            },
          },
        },
      },
      required: ['score', 'fit_band', 'criteria'],
      additionalProperties: false,
    },
  },
  description: 'Score lead fit across ICP criteria.',
});
```

## Validation

### Novelty check

After generating copy across a list, sample a few rows and check: does each email reference something specific to that row, or do the emails read like a template with name swaps? If the latter, the upstream research column is too thin — go back to `jobs/enriching-and-researching.md` and produce richer research before regenerating.

A simple programmatic check: count the rows where the email body is detectable across two or more rows with substring overlap > 80%. High overlap rate means the model is template-completing, which means the research signal is not strong enough to differentiate rows.

### Spot-check before bulk send

Generated copy should be sampled and read by a human before going to a sender. Models occasionally produce confidently wrong claims (a wrong company description, a fabricated case study, a misattributed quote) that are caught immediately by reading but invisible to a downstream programmatic check.

## Exit

- Copy and qualification columns are ready → hand off to the user's outreach tool. Deepline does not send mail; the deliverable is a CSV the user uploads to Apollo, Instantly, Smartlead, or wherever they run sequences.
- The output reads as mail-merge → back to `jobs/enriching-and-researching.md` to enrich the row with a stronger research signal, then regenerate.
- A custom play is failing — usually because the research column is malformed or the schema is rejecting wrapped output → `references/debugging.md`.
