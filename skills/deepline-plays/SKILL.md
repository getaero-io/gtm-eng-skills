---
name: deepline-plays
description: 'Deprecated alias. Play work is now part of `deepline-gtm`, and the CLI documents plays itself. Use when a user or script still invokes `/deepline-plays`: immediately load and follow the `deepline-gtm` skill instead. Triggers: play, plays, workflow, waterfall, webhook, cron.'
---

# deepline-plays (now part of deepline-gtm)

## Quick Start

```bash
npm install -g deepline
deepline auth register --wait auto
deepline -h
```

`deepline-plays` is a temporary alias kept so existing prompts, scripts, and saved commands keep working. It will be removed.

## What to do

Load the `deepline-gtm` skill and follow it for this request. Do not answer from this file; it contains no workflow of its own.

If the skill loader supports names, invoke `deepline-gtm`. Otherwise read the entrypoint directly, trying these roots in order and using the first that exists:

```bash
for candidate in \
  "$PWD/.skills/deepline-gtm" \
  "$HOME/.claude/skills/deepline-gtm" \
  "$HOME/.agents/skills/deepline-gtm"; do
  [ -d "$candidate" ] && { echo "$candidate/SKILL.md"; break; }
done
```

To write, check, run, publish, or audit a play, run `deepline plays --help`.

Then tell the user once, in a single line, that `/deepline-plays` is now `/deepline-gtm`, and continue with the actual request.
