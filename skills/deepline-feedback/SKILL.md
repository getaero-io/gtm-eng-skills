---
name: deepline-feedback
description: 'Send feedback or bug reports to the Deepline team, including session transcript and environment info. Use when the user asks to report a bug, send product feedback, or share the current Claude/Cowork session with Deepline support.'
disable-model-invocation: false
---

# Deepline Feedback

Send feedback or a bug report to the Deepline team.

## Steps

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

3. **If confirmed**, send the feedback text first:

   ```bash
   deepline feedback send "{feedback text}" --json
   ```

4. **Send the session transcript.** Try the normal Claude transcript location first:

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

5. Tell the user it was sent. If cancelled, do nothing.
