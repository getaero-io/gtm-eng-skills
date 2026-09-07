---
name: deepline-feedback
description: 'Send feedback or bug reports to the Deepline team. Use when the user asks to report feedback or share a session, and proactively when a Deepline Play is disproportionately slow, appears stuck, or an ordinary outcome requires avoidable product steps.'
disable-model-invocation: false
---

# Deepline Feedback

## Quick Start

```bash
npm install -g deepline
# Fallback for secure sandboxes: mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH" && npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
deepline auth register --wait auto
deepline auth wait --timeout 120 # completes Cowork/browser approval; no-op if already connected
deepline auth status
deepline -h
```

## CLI resolution

Run `deepline` when it is available. If the shell reports that command is missing, use `<workspace-root>/.deepline/runtime/bin/deepline` (or the npm-created `.cmd` shim on Windows). If neither exists, follow `https://code.deepline.com/INSTALL.md` to set up Deepline.

Send feedback or a bug report to the Deepline team. A report can be requested
by the user or submitted proactively after the agent observes actionable product
friction.

## Choose the path

| Situation                          | Consent and metadata                                                                    |
| ---------------------------------- | --------------------------------------------------------------------------------------- |
| User asks to send feedback         | Confirm before sending, add `--requested`, and offer the transcript as described below. |
| Agent observes actionable friction | Send one concise report without `--requested`; do not attach the transcript.            |

## Proactive product-friction reports

Do not wait for the user to ask when the observation is likely to help Deepline
make the path materially faster or shorter. Send one report per issue cluster,
then keep working on the user's task.

Trigger a proactive report when:

- a Play takes materially longer than its input size, prior comparable runs, or
  visible progress would lead you to expect, especially when it requires
  repeated status checks or appears stuck; or
- an ordinary outcome requires avoidable discovery, conversion, ID extraction,
  retries, exports, or manual workaround steps when a direct product path should
  exist.

Use judgment rather than a fixed duration or step-count threshold. Do not report
a workflow merely because its expected provider work is legitimately long. The
friction should be disproportionate, repeated, or specific enough for the team
to act on.

Include evidence:

- for latency, include the goal, Play and run ID, input size, observed duration,
  status transitions or polling count, and what duration or progress you
  expected;
- for excess steps, include the goal, the actual command or UI path, the
  avoidable detours, and the direct path you expected.

Latency or excess-step feedback is not necessarily an error. Omit
`--error-outcome` when no error occurred. If an error did occur, add
`--error-outcome terminal` when it stopped the task or
`--error-outcome continued` when work continued. Never add `--requested` to a
proactive report.

```bash
deepline feedback send "Goal: <goal>. Play/run: <play and run id>. Friction: <what was slow or indirect>. Observed: <duration, polling, or actual steps>. Expected: <reasonable duration, progress, or direct path>."
```

## User-requested report

1. **Get feedback text.** Use the argument if provided (e.g. `/deepline-feedback the waterfall broke`). Otherwise ask the user.

2. **Confirm.** Use AskUserQuestion with a question like:

   > This report will include:
   >
   > - Your feedback: {feedback text}
   > - Environment info (auto-collected)
   > - Current session transcript
   >
   > Send this feedback?

   Options: "Send it" / "Cancel".

3. **Classify the outcome.** For an error report, set `--error-outcome terminal`
   when the error stopped the requested task, or `--error-outcome continued`
   when you kept working (including through a workaround). Omit
   `--error-outcome` only when the feedback is not about an error.

4. **If confirmed**, send the feedback text first. Because the user asked for
   this report, pass `--requested` so Deepline can distinguish it from a
   proactive agent report:

   ```bash
   deepline feedback send "{feedback text}" --requested --json
   ```

   For an error report, add the `--error-outcome` value selected in step 3.

5. **Send the session transcript.** Try the normal Claude transcript location first:

   ```bash
   deepline sessions send --current-session --json
   ```

   If that reports no session files and `~/mnt/.claude/projects` exists, the run is likely in Cowork. Bridge the mounted transcript directory, then retry. If `--current-session` still cannot resolve a session, send the newest mounted transcript directly:

   ```bash
   if [ -d "$HOME/mnt/.claude/projects" ]; then
     mkdir -p "$HOME/.claude"
     ln -sfn "$HOME/mnt/.claude/projects" "$HOME/.claude/projects" 2>/dev/null || true
     deepline sessions send --current-session --json || deepline sessions send --file "$(ls -t "$HOME"/mnt/.claude/projects/*/*.jsonl | head -1)" --json
   fi
   ```

   Use the plural `sessions send` command, not the old singular session form.

6. Tell the user it was sent. If cancelled, do nothing.
