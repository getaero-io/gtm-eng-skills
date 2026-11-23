# Lint before you open a PR

Run it on your package. It catches, locally, the things that would otherwise come back from review,
or worse, fail on an installer's first call.

The script is not on your `PATH`; invoke it by path with `python3`:

```
python3 scripts/lint_skill.py build/<slug>             # offline: shape, content, injection
python3 scripts/lint_skill.py build/<slug> --online    # also resolves every tool and play ID
python3 scripts/lint_skill.py build/<slug> --json      # machine-readable
```

## The exit codes tell you whose problem it is

| Exit | Meaning | What to do |
|---|---|---|
| **0** | Clean (reports may still be printed) | Continue |
| **4** | **Your package has blocking findings** | Fix them. The findings say what and where |
| **2** | The *command* was wrong: no such directory | Check what you typed |
| **1** | **The lint is broken, not your package** | Not a reason to edit your skill |

Codes 1 and 2 print a one-line JSON envelope on stderr, `{"error": {"code": …, "message": …}}`.

## What it checks

**Deterministic evidence blocks; heuristic evidence reports.** A hard block on a regex over English is
the one failure an author cannot debug, so only shape-level facts block.

| Severity | Check | What it means |
|---|---|---|
| block | `missing_skill_md`, `frontmatter`, `frontmatter_name`, `name_dir_mismatch`, `frontmatter_description` | the repo and the CLI sync find a skill by its folder and its `name` |
| block | `declared_inputs` | `## Declared inputs` is the one required body section |
| block | `missing_file`, `reference_outside_package`, `symlink` | a reference that does not ship |
| block | `absolute_path` | a path on the author's disk |
| block | `credential` | a credential-shaped string; the value is never echoed |
| block | `answer_sheet_in_package` | the author's own values travel beside the package, never in it |
| block | `halts_vocabulary` | a `**Halts**` word outside `sample-review`, `spend-approval`, `send-approval`, `write-approval`, `other` |
| block | `clay_mechanics` | a Clay CLI command, Clay MCP tool, Clay URL or Claygent left in a Markdown file. Lines that are explicit migration notes or attributed measurements are exempt |
| block | `unknown_tool_id`, `unknown_play_id` (`--online` only) | `deepline tools describe` / `deepline plays describe` does not resolve an ID the package names |
| block / report | `injection/<pattern>` | `scripts/injection.py` over every text file, patterns in `scripts/fixtures/injection_patterns.json` |
| report | `section_missing`, `touches_axis` | `## What this skill touches` (with Reads, Writes, Never), `## Representative output`, `## What this skill does not claim`, `## What good looks like` |
| report | `no_pilot`, `no_setup_link` | the repo checklist: a 1 to 10 row pilot, and a link to code.deepline.com |
| report | `clay_mention`, `clay_in_description`, `loose_root_file`, `unexpected_dir` | worth a look; may be fine |

**Tool IDs are found** in `deepline tools execute|describe|get <id>` and in `tool: '<id>'` inside play
code; **play IDs** in `deepline plays run|describe|check prebuilt/…` and quoted `'prebuilt/…'`. Offline,
they are listed and marked unresolved. **Run `--online` before a PR**: an invented tool ID is the most
common way a fluent skill fails on its first call, and only the catalogue can say it does not exist.
Both describe calls are free.

**The injection scan is heuristic and still blocks**, the one exception to the rule above: a published
skill runs on other people's machines and the instruction it carries executes there. A missed injection
harvests credentials from every installer; a false positive costs one round of review. It scans every
file, because a clean `SKILL.md` with the payload in a reference file is the whole attack.

If you ship a play, also run `deepline plays check scripts/<name>.play.ts`, which bundles and validates
it without starting a run.

## Your skill contains checks too, and they need the same treatment

Anywhere your skill says *refuse*, *skip the row*, *report it as ambiguous*, *stop and ask*, or *fall
back because the yield was too low*, you have written a check. It has a failure branch. And a failure
branch that has never executed is not a safeguard; it is a paragraph.

So before you open the PR: **make each one fire, once, on purpose.** Feed it the input it is supposed
to refuse. A company name that cannot resolve to one domain. A row with the field your step depends on
left empty. A search that legitimately returns nothing. A branch that needs a live call is a paid step:
state the cost and get a yes first.

Two things go wrong, and the second is the one worth the trouble:

- **Nothing happens.** The condition never triggers, because it was written against a shape the data
  does not take: a value arriving as a string where the check expects a number, an empty result
  arriving as `[]` where the check tests for null.
- **The wrong thing happens.** Something *does* stop, but not your check: a different guard upstream
  caught it first and produced a message that reads plausibly. Your check is still untested and now
  looks tested.

The question is **which** part stopped it. If a threshold you wrote is doing the work, changing that
threshold should visibly change the outcome; if it does not, something else is deciding.

## What the lint does NOT tell you

It checks that the package is **well-formed and runnable for someone else**. It does not check that the
skill is *good*: whether the logic is right for the job, whether the thresholds are the ones you want,
whether it helps anyone. A clean lint is a floor, not a verdict.

The lint's own tests: `python3 -m pytest scripts/` (or `python3 scripts/test_lint_skill.py`).
