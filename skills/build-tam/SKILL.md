---
name: build-tam
description: "Build a Total Addressable Market list: size the audience, source companies from ICP filters, then find contacts at those companies at scale."
---

# Build a TAM List

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

This is a recipe shortcut. It pre-selects the build-tam recipe but the **deepline-gtm governs the entire session**.

## Execution order

1. **Invoke `deepline-gtm`** using the Skill tool.
2. **Follow the meta-skill's full routing instructions** - analyze the user's complete prompt and load every sub-doc the meta-skill tells you to. Do not skip docs just because a recipe is pre-selected.
3. **Follow the meta-skill's routing gate for this recipe.** Read the build-tam recipe at `../deepline-gtm/recipes/build-tam.md` (relative to this file) only when that gate routes you to it. Conditional access and safety checks still apply.

The recipe only covers one part of the task. The meta-skill handles everything else the user asked for.
