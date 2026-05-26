# Writing outreach

Outbound copy, sequence design, qualification language, and scoring for known contacts/accounts with evidence.

This doc does **not** cover finding people or filling emails — those live in `jobs/finding-companies-and-contacts.md` and `jobs/enriching-and-researching.md` and must complete before this doc is useful. Outreach generation without research columns produces mail-merge.

## When you are in this doc

You have contacts/accounts with name, title, company, identity, and at least one evidence signal ("what they sell," "recent funding," "pain points," "tier"). User phrasing looks like:

- "write a cold email for each of these leads"
- "draft a 4-step sequence for the Tier 1 contacts"
- "write qualification copy explaining why each contact is a good fit"
- "personalize a first line per contact based on the research column"

If the list lacks evidence, route to `jobs/enriching-and-researching.md` first. `name + title + company` alone produces template output.

## Choose your approach

| You need                                                           | Pattern category                                                                  | Discovery                                       |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------- | ----------------------------------------------- |
| One personalized snippet per contact/account (subject, first line, value prop) | single-prompt `deeplineagent` with output `jsonSchema`                            | `deepline tools describe deeplineagent --json`  |
| A multi-step sequence per contact/account | `deeplineagent` with array `jsonSchema`                                           | (same)                                          |
| ICP fit / tier classification with reasoning                       | `deeplineagent` with enum `jsonSchema`                                            | (same)                                          |
| Score accounts/contacts on multiple criteria                       | `deeplineagent` with object `jsonSchema` returning `{score, fit_band, rationale}` | (same)                                          |
| Deterministic template merge (no AI)                               | plain TypeScript in the play step                                                 | no tool needed                                  |

`deeplineagent` is the right tool for almost all generative outreach work. If the user wants strict template merge with no rewriting, write the merge directly in TypeScript inside the play.

Outreach generation is row work, so put it in a play. Probe `deeplineagent` or `run_javascript` only to confirm the live input contract or model menu; the copy that ships to the user should be produced by a `ctx.map` stage with stable keys. This makes regeneration cheap when only the prompt changes, preserves the research columns that fed each message, and keeps the final CSV tied to an inspectable run instead of a one-off script.

## Durable rules

### Personalization requires a contact/account-specific signal

Every email must reference a specific signal: product, pain point, recent news, use case, or persona responsibility. If the prompt only has name + title + company, the output is mail merge. Fix upstream by adding evidence first.

### Research happens in enriching-and-researching, not here

A common failure mode is writing the research and the copy in the same `deeplineagent` prompt: "Look up Acme and write me a personalized email." That conflates two responsibilities, makes the output non-cacheable, and produces shallow research because the prompt is optimized for copy quality, not factual depth. Research belongs in a prior durable boundary that produces `company_research`, `pain_points`, or similar context. For row work that boundary is usually a `ctx.map` stage; for scalar work it may be `ctx.step` or `ctx.tools.execute`. The copy stage then _reads_ that saved context.

### Structured output for anything downstream will read

When the output is one or more emails, sequences, or qualification objects, use `jsonSchema`. _Failure mode:_ free-text output for sequences makes the user (or the next stage) parse N emails out of a blob, and any malformed run silently breaks the parse. A schema enforces shape at write time and gives downstream stages a clean contract.

```typescript fragment
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

When classifying accounts/contacts against an ICP, ground only on provided evidence. Mark `Unknown` when evidence is missing, not a low score.

Default to high recall: when evidence is borderline, lean toward the higher tier. Outreach is cheaper than missing a real prospect; the noise is filtered downstream by reply rate.

### Carry lineage end-to-end

Preserve provider provenance, research sources, and identity fields next to generated copy. Copy without lineage is impossible to QA, debug, or A/B test.

### Structured outputs are wrapped — flatten before re-prompting

`deeplineagent` columns with `jsonSchema` are stored wrapped in an AI result envelope. Direct interpolation `{{column}}` into another `deeplineagent` prompt usually works, but field-level access `{{column.subject}}` does not. If a downstream step needs `column.subject`, flatten it in the next TypeScript step and emit the scalar there. (Same rule as in `jobs/enriching-and-researching.md`.)

## Patterns

### One-shot personalization

The simplest pattern: one prompt produces one output object per contact/account. Use for a single email or first-line snippet.

```typescript fragment
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

```typescript fragment
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

```typescript fragment
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

```typescript fragment
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

After generating copy, sample a few contacts/accounts. If emails read like name-swapped templates, the upstream evidence is too thin; enrich again before regenerating.

A simple programmatic check: flag email bodies with >80% overlap across multiple contacts. High overlap means the evidence is not differentiated enough.

### Spot-check before bulk send

Generated copy should be sampled and read by a human before going to a sender. Models occasionally produce confidently wrong claims (a wrong company description, a fabricated case study, a misattributed quote) that are caught immediately by reading but invisible to a downstream programmatic check.

## Exit

- Copy and qualification columns are ready → hand off to the user's outreach tool. Deepline does not send mail; the deliverable is a CSV the user uploads to Apollo, Instantly, Smartlead, or wherever they run sequences.
- The output reads as mail-merge → back to `jobs/enriching-and-researching.md` to enrich the row with a stronger research signal, then regenerate.
- A play is failing - usually because the research column is malformed or the schema is rejecting wrapped output -> `references/debugging.md`.
