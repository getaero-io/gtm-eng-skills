# Prerequisites

Only the play routes need any of this. **I just have an idea**, **From what we just ran**, and an
existing `SKILL.md` need no setup; the lint runs offline with `python3` alone, and only its `--online`
mode calls the CLI.

## Install and sign in

Deepline's own setup is authoritative: <https://code.deepline.com>. The short form:

```
npm install -g deepline
deepline auth register --wait auto
deepline auth wait --timeout 120     # completes browser approval; no-op if already connected
deepline preflight --json
```

In a sandbox where a global npm install is blocked:

```
mkdir -p "$HOME/.local" && npm config set prefix "$HOME/.local" && export PATH="$HOME/.local/bin:$PATH"
npm install -g deepline --registry https://code.deepline.com/api/v2/npm/
```

If `deepline` is still not on `PATH`, try `<workspace-root>/.deepline/runtime/bin/deepline`, then follow
<https://code.deepline.com/INSTALL.md>. If the install itself cannot reach the network, **the play route
is unavailable here**: say so and take the interview route.

## Confirm you are where you think you are

`deepline preflight --json` reports health, auth and balance in one process. Run it as one standalone
command and wait for it; it may self-update the CLI, so never run it beside another `deepline` command.
Then:

```
deepline auth status --json     # which organization this CLI is acting as
deepline org --help             # switching organizations, if the play lives in another one
```

**Say the organization out loud before reading a play.** A creator with several organizations names a
play that exists in one of them, and a not-found from the wrong one reads exactly like a typo.

## What this reads, and what it never touches

```
deepline plays list --json                    names of saved and prebuilt plays (org-wide)
deepline plays describe <name> --json         a play's contract
deepline plays get <name> --source --out …    a play's source
deepline plays check <file.play.ts>           bundle + validate locally, no run
deepline tools search "<intent>" --json       find tool candidates
deepline tools describe <tool_id> --json      a tool's inputs, outputs and pricing
```

All reads, all free. It never runs a play, executes a tool, exports a run, queries the customer DB,
reads a secret, or saves, publishes or deploys a play.

## Keeping this skill current

This skill lives in the repo's `drafts/` tree, which `deepline skills` does not sync. Update it by
pulling the repo (`git -C <your checkout> pull`). Keep the CLI current with `deepline update`; an old
CLI can lack a subcommand this file names, so if one is missing, check `deepline <group> --help` on the
installed version before assuming the command was renamed.
