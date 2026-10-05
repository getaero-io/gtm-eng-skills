# Play → skill

Converts one Deepline play into a portable `SKILL.md`. Reads source and contract only: never a run,
never a row, never a write.

Prerequisite: `references/prerequisites.md`. You need the CLI signed in to the organization holding
the play. A local `.play.ts` file the creator points at needs no CLI to read.

## 1. Find the play

Ask for the name or the file first. `deepline plays list --json` is org-wide and has no owner filter,
and saved-play names can encode customers and deals, so list only when the creator asks to be shown.

### 1b. Several at once: rank silently, offer the strongest three

The door is the `Show me my plays` route. Score each candidate off its contract and source alone:

| Signal | Read from | Why it ranks |
|---|---|---|
| a real decision exists | a comparison in the code, or a `deeplineagent` prompt that classifies | a play that only fetches and copies is a list, and a list productizes into nothing |
| thresholds are written down | numeric constants in comparisons | a skill can carry a number it can find; it cannot carry one that was never written |
| the steps do work | how many `withColumn` / `ctx.tools.execute` steps compute rather than copy | |
| not a scratch copy | untitled, or matching *test*, *scratch*, *copy*, *demo*, *hello* | |

**A play's run count is not a signal**: this route never reads runs. Then say it in two short
paragraphs, no count of what was cut, no criterion, no time estimate:

> All 9 read and drafted. These three look strongest: `renewal-risk`, `icp-scoring`,
> `signup-triage`. Want to start with them?

Then run §2 onward per play, one at a time, best first.

## 2. Read the source

```
deepline plays describe <name> --json                          # contract: input schema, outputs, cost estimate
deepline plays get <name> --source --out build/src/<slug>/     # the code (a directory for multi-file plays)
deepline tools describe <tool_id> --json                       # each tool the code calls
```

`--source` reads the working draft by default; add `--live` to read what actually runs on triggers,
and say which one you read. **Read-only allowlist**: `plays list`, `plays describe`, `plays get`,
`plays check` (bundles and validates locally, starts no run), `tools search`, `tools describe`.
**Never** `plays run`, `runs …` (spends or reads their data), `plays save` / `publish` / `deploy` /
`settings` (writes), `secrets` (credentials), `db query` (their data).

## 3. Evidence precedence

| Order | Read | Evidence of | NOT evidence of |
|---|---|---|---|
| 1 | `deeplineagent` prompts, comments, the play's description | **intent**: why the step exists | the mechanics |
| 2 | comparisons, constants, `ctx.tools.execute` calls, `ctx.runPlay` calls, the input schema | **mechanics**: ground truth for every deterministic claim | intent |
| 3 | step names, column names, variable names | nothing on their own | anything |

**Intent may be wrong and still be faithfully recorded; mechanics may not.** A comment that says the
router handles *"high-value, mid-market and lower-tier leads"* above code that routes only `tier ===
"Tier 1"` describes a play that does one thing. Quote a comment as the author's stated purpose, never
as behaviour.

## 4. Gates live in code, and a gate named in a comment is not a gate

Read every `if`, early `return`, `filter` and ternary that decides whether a later step runs. A step
called `lookupExistingLead // TODO gate create on empty` that flows unconditionally into a create is a
play that creates a record for every row, duplicate or not. **Before stating that anything is gated,
deduped, or skipped, find the line that does it.** `TODO`, `FIXME`, `STUB` and *"placeholder"* are how an
unfinished play announces itself; a skill that narrates it as working describes a system that does not
exist. For a play that writes, that is the most important finding.

**Prompts can grant override authority over deterministic fields.** A classifier prompt that says
*"override the employee count if the website looks bigger"* is the most important behavioural fact in
that play and invisible to a structural read. Read every prompt for permissions, not just for intent.

## 5. Iteration and cost

Fan-out is explicit in a play: `ctx.csv(...)` and `ctx.dataset(...)` rows, `.withColumn` per row,
`ctx.runPlay` per item, a search whose result rows feed the next step. Chain them: *accounts × one
person search (per returned result) × one email waterfall per person found* is a shape, exact, from the
source.

**Cost: derive the bound, then confirm the number.** `deepline plays describe` may carry a per-row or
per-run estimate (`deepline plays list --show-cost` shows it too); each tool's `pricing` from
`deepline tools describe` carries `creditsPerUnit` and `unit`. Where a unit is `result`, the count is
the tool's output and the step needs a cap (see `references/determinism.md`). Never state a run's cost
as derived when one factor is a count nobody has yet; show the bound and say it is a bound.

**A chain is not a waterfall unless a gate sits between its steps.** A waterfall tests the previous
step's output and stops on a hit, so ordering it cheapest first saves money. A plain sequence runs every
step on every row; claiming waterfall savings for it is a false cost claim.

## 6. Thresholds become declared inputs

Extract every number from the mechanics, then check it against any prose that mentions it. A rule
`foundedYear >= 2011` beside a prompt saying *"founded in the last 15 years"* agrees in 2026 and
diverges every year after. So a threshold read out of a play becomes a **declared input with the read
value as its default**, never a constant, and never the relative phrasing.

## 7. Steps come out in dependency order

Order by what each step reads, not by line order: a step may only use what earlier steps produced.
Root inputs (the input schema, the CSV columns read) become the skill's declared inputs and open it.
Steps whose output nothing reads are **played back to the creator** rather than dropped: a dependency
graph cannot tell an abandoned experiment from an optional input.

## 8. The low-yield boundary

A play is too thin to build from when it gives you names and nothing else: one tool call, no
comparisons, no prompt. **A skill assembled from that is invention wearing a citation.** Say which half
is missing (the purpose or the mechanics) and offer the interview. That is a real answer.

## 9. Which thresholds earn a question

**The budget is three CLASSES, not three questions.** A play hands you more numbers than are
decisions:

| Read from the source | In the question? |
|---|---|
| a size cut-off that switches which path a record takes | **yes**: it changes who gets contacted |
| an activity window deciding what counts as flagged | **yes** |
| a country or segment list that switches routing | **yes** |
| tier values on a score **nothing branches on** | **no**: ask why it is computed, not what it should be |
| `limit`, concurrency, retries, timeouts, page sizes | **no**: declare with the read value as default |

## 10. What the interview must still ask

- **The insight and the ICP**: the code rarely carries either.
- **What a run costs at their volume**: the code carries prices per unit, not their list size.
- **What the unused branches are for.**
- **Who the destinations are**: a CRM owner id or a Slack channel in the code says nothing about who.
- **Which steps halt**: declared by the creator, never inferred.

## 11. The skill must ship the play, not describe it

If the shape is a play (a signal starts it, or the volume is beyond a conversation), the skill carries
the `.play.ts` under `scripts/`, with every org-specific literal (secret names, list ids, CRM fields,
thresholds) lifted into the play's input schema and the skill's `## Declared inputs`. Its steps:

1. **Say why it is a play rather than an agent loop.**
2. **`deepline plays check scripts/<name>.play.ts`** before anything else. Do not hardcode CLI forms
   beyond what `deepline plays --help` shows on the installed version.
3. **Pilot on 1 to 10 rows** with `deepline plays run scripts/<name>.play.ts --input '…'`, show the
   output, then the one gate (batch, cost, writes, ask).
4. **Where judgment lives:** comparisons and routing in code, never in a `deeplineagent` prompt; the
   agent prompt is for prose and for classification with a `jsonSchema`.
5. **Triggers last**: a cron or webhook, or a `deepline monitors` deployment, set only after the gate.

**Reproduce the source's shape.** Deviate only when you can name what the deviation needs, and write
the deviation into the skill so an installer debugging it can see it was deliberate.

## From what we just ran (the session route)

The calls already made in this conversation are a play that was run by hand: each `deepline tools
execute` is a step, each comparison you made between calls is a gate, each number you or the creator
chose is a threshold. Read them back in order, and treat them exactly as source: mechanics are the
calls and their inputs; intent is what the creator said while asking for them. **The prices are known**
(you saw the responses), **the yields are one sample** (say so in `## What this skill does not claim`).
Do not re-run anything to fill a gap; mark it.
