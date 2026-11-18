# Package layout

## Shape

```
your-skill/
  SKILL.md              exactly one, at the root
  references/           optional
  scripts/              optional (helpers, and the .play.ts when the shape is a play)
```

`package.json` and `skill-metadata.json` at the root are tolerated; some skills in the repo carry them.

Rules, checked by `scripts/lint_skill.py`:

- **Exactly one `SKILL.md`, at the root**, with `name:` equal to the folder name.
- **Supporting files live under `references/` or `scripts/`** (`templates/` and `examples/` are
  tolerated). A loose root file is reported.
- **Every reference must resolve to a file that ships.** A `SKILL.md` naming a reference file that does
  not exist reads as complete and stalls on first use, or worse, the agent invents the missing
  content. The lint blocks on it. If you are not going to write the file, inline what it says and name
  no file.
- **No references outside the package.** A path on your machine (`/Users/…`) or into another skill's
  folder is not something the installer has. The one exception is a skill the draft hands off to by
  name (`deepline-gtm`), which the installer gets from the same sync.
- **No symlinks.**
- **An answer sheet is not a package file.** It lives **beside** the package directory; the lint blocks
  a file named like one inside it.

Reference a supporting file by its relative path in a code span, not as a URL: a URL points at
somebody's repository on a branch, needs network the installer may not have, and the lint cannot
check it.

A single-file skill is a perfectly good skill. Most are.
