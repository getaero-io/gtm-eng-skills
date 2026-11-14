# Getting a skill into the repo

Every route converges here: from an idea, from a play, from what was just run, or arriving with a
`SKILL.md` already written.

## Where it goes

`https://github.com/getaero-io/gtm-eng-skills`, and a new skill goes into **`drafts/<slug>/`**, not
`skills/`.

| Tree | Synced by `deepline skills` | Who it reaches |
|---|---|---|
| `drafts/` | **no** | people who copy the folder by hand |
| `skills/` | yes | every installer on the next skill sync |

That difference is why a new skill starts in `drafts/`: an unreviewed skill in `skills/` is one sync
away from running in strangers' agents. Promotion is a separate, later PR (below).

## The steps

1. `python3 scripts/lint_skill.py <slug> --online` returns `0`. Reports are mentioned, not chased.
2. If the skill ships a play: `deepline plays check <slug>/scripts/<name>.play.ts` passes.
3. Fork the repo (or branch, with write access): `git checkout -b feat/<slug>`.
4. Copy the folder to `drafts/<slug>/`. The answer sheet does **not** go with it.
5. Add one row to the table in `drafts/README.md`: the folder link and one line of purpose.
6. Open the PR with a clear description of what the skill does, the tool IDs it calls, what it writes,
   and what it does not claim.

On the "I open it" path, the agent does 3 to 6 with `git` and `gh pr create`, **after one message
showing the branch, the file list, the diff stat, the PR title and body, and the ask**, and only on a
yes. Nothing is pushed before that yes.

## The repo's own checklist (CONTRIBUTING.md)

- Focused on exactly one GTM workflow.
- Includes a working `deepline tools execute` (or `deepline plays run`) example, with a tool ID that
  `deepline tools describe` resolves.
- Includes a pilot on 1 to 10 rows before any full run.
- Documents required and optional inputs (`## Declared inputs` covers this).
- Links <https://code.deepline.com> for setup.
- Written for an external audience: no internal file paths, org ids, customer names or credentials.

Drafts additionally use fictional placeholders only (`Acme Labs`, `Northwind Analytics`, `Ada
Example`, `.example` domains), and keep `${...}` placeholders in any tracked JSON. See `drafts/README.md`
in the repo.

## Promotion to `skills/`

When a draft is stable, a second PR moves it to `skills/<slug>/`, adds it to the `skills` array in
`.claude-plugin/marketplace.json`, and adds it to the skills table in the root `README.md`. Strip any
TODOs first, and add sample inputs under `examples/` if they help a reviewer. Only then is it part of
the CLI-synced surface.

## Correcting a skill already in a PR

Push a new commit to the same branch. A second PR for the same folder splits the review. Once merged, a
correction is a new PR editing the same folder; the folder name is the skill's identity, so keep `name:`
and the folder unchanged unless the rename is the point of the PR.

## What to expect

A person reviews every PR, so a PR is **submitted for review**, not published. Overlapping an existing
skill is not a rejection: say in the description which adjacent job yours is for, which is what lets a
reader pick between them.
