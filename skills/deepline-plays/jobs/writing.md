# Writing outreach

The last stage. You have rows with name, title, company, identity, and **at least one research/context column**. Outreach off `name + title + company` alone produces mail-merge regardless of prompt quality — if research columns are missing, go back to the enrichment section first.

Put outreach in a play (a `ctx.dataset` stage with stable keys), so regeneration is cheap when only the prompt changes and the copy stays tied to an inspectable run. `deeplineagent` is the right tool for almost all generative outreach; a plain-TypeScript column is for strict template merge only.

- **Personalization requires a row-specific signal.** Every email must reference something specific to the row — a product, a pain point, recent news, the persona's responsibility — not just `{{first_name}}` and `{{company_name}}`. The fix for mail-merge is always upstream: enrich a research column, then condition on it.
- **Research happens in enrichment, not here.** Writing research and copy in the same prompt ("look up Acme and write me an email") produces shallow research, because the prompt is optimized for copy quality. Research belongs in a prior `ctx.dataset` stage producing `company_research` / `pain_points`; the copy stage _reads_ that column.
- **Structured output for anything downstream reads.** Emails, sequences, and qualification objects use `jsonSchema` — free-text sequences force the next stage to parse N emails out of a blob, and a malformed run breaks the parse silently.
- **Qualification is evidence-based, high recall.** Build the prompt around only the provided context; mark `unknown` when evidence is missing, not a low score. An `evidence_used` array makes the model surface which context it used, catching hallucinated reasoning. When evidence is borderline, lean to the higher tier — outreach is cheaper than missing a real prospect; noise is filtered downstream by reply rate.
- **Carry lineage end-to-end.** Every row carries the research and identity columns that produced its copy, not just the copy — a CSV of emails with no link back to the research is impossible to QA or A/B test.

```typescript
const personalized = await ctx.tools.execute({
  id: 'personalized_email',
  tool: 'deeplineagent',
  input: {
    model: '<model-id-from-describe>',
    prompt: `Write a cold email to ${row.first_name} ${row.last_name} (${row.title}) at ${row.company_name}.
Pain point context: ${row.pain_points}. Open with a one-sentence reference to the pain point. Under 90 words.
Return JSON with subject, first_line, body.`,
    jsonSchema: {
      type: 'object',
      properties: { subject: { type: 'string' }, first_line: { type: 'string' }, body: { type: 'string' } },
      required: ['subject', 'first_line', 'body'],
      additionalProperties: false,
    },
  },
  description: 'Write one personalized cold email for this row.',
});
```

For a multi-step sequence, generate all steps as one structured output (an array `jsonSchema`, `minItems`/`maxItems` fixing the count) — the model plans the arc better seeing all steps at once. **Novelty check** after generating: sample rows and confirm each email references something row-specific; high body overlap across rows means the research signal is too thin — enrich richer, then regenerate. **Spot-check before bulk send:** a human reads a sample — models occasionally produce confidently wrong claims (wrong company description, fabricated case study) that reading catches and no programmatic check does.

Deepline does not send mail. The deliverable is a CSV the user uploads to Instantly, Smartlead, Outreach, or wherever they run sequences.

## Exit

- Output reads as mail-merge → enrich a stronger research signal in `enriching.md`, then regenerate.
- QA the final list before sending → `../shared/correctness.md`.
