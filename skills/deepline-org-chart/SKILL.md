---
name: deepline-org-chart
description: "Build an interactive account org chart, leadership map, buying committee, or manager/report neighborhood around a person. Use for decision makers, reporting-line candidates, stakeholder mapping, and warm intro paths. Skip standalone email lookup and unrelated cross-company prospecting."
---

# Account Org Chart Builder

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

This is a recipe shortcut. It pre-selects the deepline-org-chart recipe but the **deepline-gtm governs the entire session**.

## Execution order

1. **Invoke `deepline-gtm`** using the Skill tool.
2. **Follow the meta-skill's full routing instructions** - analyze the user's complete prompt and load every sub-doc the meta-skill tells you to. Do not skip docs just because a recipe is pre-selected.
3. **Follow the meta-skill's routing gate for this recipe.** Read the deepline-org-chart recipe at `../deepline-gtm/recipes/account-orgchart.md` (relative to this file) only when that gate routes you to it. Conditional access and safety checks still apply.

The recipe only covers one part of the task. The meta-skill handles everything else the user asked for.
