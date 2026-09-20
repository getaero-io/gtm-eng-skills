---
name: deepline-pre-research
description: 'Deprecated alias. This skill was renamed to `deepline-research`. Use when a user or script still invokes `/deepline-pre-research`: immediately load and follow the `deepline-research` skill instead. Triggers: pre-research, source discovery, provider strategy, research data sources, ScrapeCreators, X/Twitter data, Reddit comments, public and private datasets, CRM data, workflow data, custom language, messaging language, pain language.'
---

# deepline-pre-research (renamed to deepline-research)

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

This skill was renamed. `deepline-pre-research` is a temporary alias kept so existing prompts, scripts, and saved commands keep working. It will be removed.

## What to do

Load the `deepline-research` skill and follow it for this request. Do not answer from this file; it contains no instructions of its own.

If the skill loader supports names, invoke `deepline-research`. Otherwise read the entrypoint directly, trying these roots in order and using the first that exists:

```bash
for candidate in \
  "$PWD/.skills/deepline-research" \
  "$HOME/.claude/skills/deepline-research" \
  "$HOME/.agents/skills/deepline-research"; do
  [ -d "$candidate" ] && { echo "$candidate/SKILL.md"; break; }
done
```

Then tell the user once, in a single line, that `/deepline-pre-research` is now `/deepline-research`, and continue with the actual request.
