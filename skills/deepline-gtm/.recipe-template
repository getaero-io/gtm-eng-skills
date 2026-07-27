# Recipe Template

Use this structure for all recipes in `recipes/`.

```markdown
---
name: recipe-name
description: "One-line description of what this recipe does."
---

# Recipe Title

One-line summary of the workflow.

## When to use

- "Example user request that triggers this recipe"
- "Another example"

## What NOT to do

| Anti-pattern | What happens | Why it fails |
|-------------|-------------|-------------|
| Describe the wrong approach | What the agent will observe | Root cause |

## Steps

### Step 1: [verb] — [category: search|enrich|transform|compose|deliver]

Description of what this step does.

**Input:** What data/fields this step needs and where they come from.

```bash
# exact command
```

**Output:** What this step produces — columns, format, expected row count.
**Checkpoint:** Validation gate before proceeding (e.g., "verify row count matches expected").
**Fallback:** Alternative approach if the primary fails.

### Step 2: ...

(repeat for each step)

## Gotchas

| Gotcha | What happens | Fix |
|--------|-------------|-----|
| Known issue | Observable symptom | Workaround or prevention |
```

## Step categories

| Category | Covers |
|----------|--------|
| **search** | Finding/pulling data from providers — scraping, discovery, datasets |
| **enrich** | Adding data to existing rows — qualification, email lookup, profiles |
| **transform** | Reshaping data — filtering, merging, deduping, formatting |
| **compose** | Generating content — emails, personalization, scoring narratives |
| **deliver** | Pushing results to a destination — Sheets, CRM, sequencer, CSV export |

## Principles

- Every step must declare its **input** (what fields/format it needs) and **output** (what it produces).
- Every step should have a **checkpoint** before the next step consumes its output.
- Every step should have a **fallback** — an alternative tool or approach if the primary fails.
- Anti-patterns in "What NOT to do" should come from real session failures, not speculation.
