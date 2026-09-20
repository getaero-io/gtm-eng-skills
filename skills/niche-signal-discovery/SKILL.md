---
name: niche-signal-discovery
disable-model-invocation: false
description: 'Deprecated alias. This skill was renamed to `deepline-scoring`. Use when a user or script still invokes `/niche-signal-discovery`: immediately load and follow the `deepline-scoring` skill instead. Triggers: ICP analysis, niche signals, won vs lost analysis, differential signals, signal discovery, ICP signal report, account scoring signals, lead scoring, first-party signals, buyer signals.'
---

# niche-signal-discovery (renamed to deepline-scoring)

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

This skill was renamed. `niche-signal-discovery` is a temporary alias kept so existing prompts, scripts, and saved commands keep working. It will be removed.

## What to do

Load the `deepline-scoring` skill and follow it for this request. Do not answer from this file; it contains no instructions of its own.

If the skill loader supports names, invoke `deepline-scoring`. Otherwise read the entrypoint directly, trying these roots in order and using the first that exists:

```bash
for candidate in \
  "$PWD/.skills/deepline-scoring" \
  "$HOME/.claude/skills/deepline-scoring" \
  "$HOME/.agents/skills/deepline-scoring"; do
  [ -d "$candidate" ] && { echo "$candidate/SKILL.md"; break; }
done
```

Then tell the user once, in a single line, that `/niche-signal-discovery` is now `/deepline-scoring`, and continue with the actual request.
