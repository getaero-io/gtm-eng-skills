---
name: deepline-plays
description: "Create custom Deepline plays/scripts that combine multiple tools and/or other plays, with durable datasets, fallback logic, joins, projections, and custom run/export behavior."
---

# Deepline Plays Recipe

This is a recipe shortcut. It pre-selects the deepline-plays recipe but the **deepline-gtm governs the entire session**.

## Execution order

1. **Invoke `deepline-gtm`** using the Skill tool.
2. **Follow the meta-skill's full routing instructions** - analyze the user's complete prompt and load every sub-doc the meta-skill tells you to. Do not skip docs just because a recipe is pre-selected.
3. **Additionally read** the deepline-plays recipe at `../deepline-gtm/recipes/deepline-plays.md` (relative to this file) for the specific workflow.

The recipe only covers one part of the task. The meta-skill handles everything else the user asked for.
