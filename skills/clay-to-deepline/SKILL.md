---
name: clay-to-deepline
description: "Move Clay tables, workflows and functions to Deepline Plays, and compare what the same run costs in Clay and in Deepline. Use for any Clay migration, Clay export or bookmarklet JSON, Clay CLI workspace, \"convert this Clay table\", Clay credit cost, or \"is Deepline cheaper than Clay\". Reads a Clay CLI export or a bookmarklet / clay-extract.py JSON file. Makes the Plays, proves formula parity on real rows, and prices both sides."
---

# Clay to Deepline

## Quick Start

```bash
npm install -g deepline
deepline -h
```

This is a recipe shortcut. It pre-selects the clay-to-deepline recipe but the **deepline-gtm governs the entire session**.

## Execution order

1. **Invoke `deepline-gtm`** using the Skill tool.
2. **Follow the meta-skill's full routing instructions** - analyze the user's complete prompt and load every sub-doc the meta-skill tells you to. Do not skip docs just because a recipe is pre-selected.
3. **Follow the meta-skill's routing gate for this recipe.** Read the clay-to-deepline recipe at `../deepline-gtm/recipes/clay-to-deepline.md` (relative to this file) only when that gate routes you to it. Conditional access and safety checks still apply.

The recipe only covers one part of the task. The meta-skill handles everything else the user asked for.
