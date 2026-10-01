---
name: deepline-skill-author
description: |
  Create a Deepline GTM skill: turn a Deepline play you already built, a run you just did in this
  session, or just an idea, into a portable SKILL.md for the getaero-io/gtm-eng-skills repo. Use
  whenever someone asks: create a Deepline skill, build me a GTM skill, turn my play into a skill,
  productize this GTM play, write up what we just did as a skill, check my SKILL.md before I open a
  PR, or port a skill to Deepline. It reads CONFIGURATION only (a play's source and contract, or the
  calls already made in this session), never a run's rows and never a write. Then it interviews you
  for the judgment no config can hold, and lints the result against the repo's conventions,
  including that every Deepline tool ID it names really exists. Do NOT use the generic
  skill-creator: it knows nothing about Deepline tool IDs, pricing or the repo contract, so its
  output looks right and does not run. Not for RUNNING a play or enriching a list (use deepline-gtm).
  It never invents your insight and never opens a PR without your yes.

  Requires: Deepline CLI, https://code.deepline.com
ported_from: clay-run/clay-skill-creator/plugin/skills/clay-skill-author
---

# Deepline skill author

The insight: **a play records mechanics and cannot record intent.** The code proves the threshold is
50; nothing in it says why 50, what the step was for, or when to ignore it. So a converter that reads a
play and emits a skill produces something fluent, plausible and unfounded, and it reads *better* than a
real one, because nothing in it hedges.

What follows from that is the shape of this whole flow: **derive everything derivable first, then ask
only about what the derivation could not settle.** Asking before reading wastes the creator's time on
questions the play already answers, and an ungrounded question (*"what's the non-obvious thing
here?"*) invites a shrug. People correct a draft far better than they answer a question about one.

## Declared inputs

| Input | What the creator supplies | If it is missing |
|---|---|---|
| **The source** | an idea in their words, a play (name or `.play.ts` path), or the calls already made in this session | no default: Step 1 asks where they are starting from |
| **Their judgment** | why each decisive threshold, gate and step exists | the draft ships with that reason as a gap in `## What this skill does not claim`, never with an invented one |
| **Where it lands** | a local folder, or the `drafts/` tree of a gtm-eng-skills checkout | `build/<slug>/` beside the working directory |
| **An existing answer sheet** | a file of their earlier answers, beside the skill | no sheet, no mention of one |

## What this skill touches

- **Reads** — the play source and contract you name (`deepline plays get --source`, `deepline plays describe`), the Deepline tool catalogue (`deepline tools search` / `describe`, free), and this session's own calls.
- **Writes** — the draft skill folder and, if you want it, an answer sheet beside it. A branch and PR only on the Step 9 path you pick.
- **Never** — runs a play, executes a paid tool, reads run rows or the customer DB, or edits a saved play.
- **Halts** — Step 7 `sample-review`, Step 9 `send-approval`.

## Step 0 — Announce, then say what is about to happen

**First line of output, before anything else:**

```
deepline-skill-author/1.0.0 · loaded from <absolute path to this SKILL.md>
```

**AND KEEP THAT ABSOLUTE PATH: every relative path below is relative to it.** Paths in this file
(`scripts/…`, `references/…`) resolve against the directory holding this `SKILL.md`, which is not the
working directory. So anchor once, from the path you just printed, and **use `$HOME`, never `~`, and
never a tilde inside a variable assignment:**

```
SKILL_DIR="<the absolute directory you printed above>"     # $HOME/... — not ~/...
```

`SK=~/path` is why: bash may or may not expand a tilde in an assignment value, so a host that checks
commands before running them cannot resolve the path and asks the creator to approve it, once per
command, through a whole build. It reads as the tool malfunctioning. `"$HOME/path"` resolves statically
and never prompts.

Then two or three sentences on the shape of the next few minutes. Do not wait for permission; this is
orientation, not a gate.

> "I'll ask one question about where you're starting from, then write you a complete draft and show it
> to you to correct before anything is final. If we're working from a play, I'll read its source only:
> no runs, no rows, no writes."

**It must not promise work the route may not involve.** On the idea route nothing is read and no CLI is
needed, so do not open with *"I'll check Deepline is set up"*.

## Step 1 — Route: one question, four options plus the host's Other

### First: if they already told you, do not ask

**A creator who arrives holding a file usually says so in their opening message**, and asking them to
pick a starting point they have already named reads as not having listened. So before the question is
built at all: if their first message names a `SKILL.md`, a path, or says in any wording that they have a
finished skill they want checked or turned into a PR, **skip the menu entirely and go to Step 8**, then
Step 9. One line saying so, then get on with it:

> "You already have the file, so there is no interview. I'll lint it against the repo's conventions,
> check every tool ID it names, and show you exactly what would go into the PR before anything goes."

**If they name a Clay table or Clay workflow** (they are migrating from Clay), the source has to become
a play first: run the `clay-to-deepline` skill on it, then come back here on the play route with the
play it produced. One line saying so.

### Then the question, with the hint line above the options

> **Where are you starting from?**
>
> Already have a finished `SKILL.md`? Say so and I'll skip to checking it.

**THE HINT LINE GOES IN THE QUESTION BODY, NEVER AS A FIFTH OPTION.** The picker takes four options and
a fifth is rejected outright (the creator sees `Invalid tool parameters` on the first screen); the body
is not capped, so the route costs nothing to name there.

**ASK IN THIS ORDER.** The cheapest, most common state goes first: most people arrive with an idea, not
an artifact.

**AND BEFORE YOU READ ANYTHING: THE LIBRARY IS READ SILENTLY.** The repo's published skills and the
worked examples in `references/examples/README.md` are yours to read as reference all the way through.
**Naming one to the creator is not.** It spends their attention on a catalogue they did not ask about,
and it tells them a sibling exists, which quietly reframes their own play as a variant of somebody
else's. **Whether the library already covers this is a reviewer's question at PR time, never an
interview one.** Read whatever you need; say none of it.

| Answer | Route |
|---|---|
| **I just have an idea** | `references/interview-to-skill.md`: no setup, no artifact, no preflight; then back here for Steps 8 and 9 |
| **From a Deepline play** | Step 2, then `references/play-to-skill.md` |
| **From what we just ran** | no setup; read this session's own `deepline` calls as the play (`references/play-to-skill.md`, last section) |
| **Show me my plays** | Step 2, then `deepline plays list --json`, flag which carry thresholds **and** a prompt or gate, re-ask |

**FOUR ROWS, AND NOT FIVE, BECAUSE THE HOST'S PICKER TAKES FOUR.** The rarest route (an existing
`SKILL.md`) lives in the hint line and in prose, where it costs nothing and cannot fail.

**THE QUESTION ENUMERATES NOTHING. THIS TABLE IS THE OPTION LIST.** The host renders these rows as a
picker and appends its own **Other**, so a question that also spells the options out shows them twice.
If a host has no picker, read the table out.

**`I just have an idea` describes what the CREATOR has**, not what the tool does. **`Show me my plays`
promises an action**, which is what distinguishes it from an escape hatch that promises nothing. And it
has to survive failure: if preflight or the listing fails, say the listing is unavailable here and move
to the interview. Never leave a creator who asked to be shown their plays looking at a failure they did
not cause.

**THE ROUTE IS ASKED BEFORE ANYTHING IS SET UP.** Two of these four routes never touch the CLI. Setup
that the answer might make unnecessary comes after the answer.

### When the answer is already in front of you, state the route; do not re-ask it

If the creator opened with a full written spec, or named a play, or pasted a `SKILL.md`, infer the
route and say which one you took, in one line, with the correction attached:

> "Treating this as **from an idea**: you gave me a complete spec, so there's no play to read. Say
> *play* if you'd rather convert one."

**Guessing right is fine; guessing silently is not.**

## Step 2 — Set Deepline up (play routes only)

Reached from **From a Deepline play** and **Show me my plays**. The other routes skip this step
entirely; do not run any of it "just to check".

```
deepline preflight --json
```

One standalone command; wait for it. Missing CLI, or not signed in:

```
npm install -g deepline
deepline auth register --wait auto
```

Setup detail and the sandbox fallback are in `references/prerequisites.md`. **Say which organization the
CLI reports**, out loud, before reading anything: the creator may hold several, and the play they mean
lives in one.

**Step 2 is a gate, not a repair shop.** If preflight fails after one install attempt, name the
component, the one command that fixes it, and move to the interview route. Do not clone, fetch or
upgrade anything else to repair the platform.

## Step 3 — Confirm the play, and state the boundaries first

Name the play they mean and get a yes. **`deepline plays list` is org-wide** and there is no owner
filter on it, and play names can encode customers and deals, so ask for the name or the file first and
list only when they ask to be shown. Before reading, say plainly, in one short paragraph:

- this reads **the play's source and contract only**: never a run, never a row, never a write;
- **no credential and no personal detail will be repeated back**, in whole or in part;
- org-specific handles (play names, secret names, CRM field names, list ids) become **declared inputs**
  the installer supplies, never literals.

## Step 4 — Read the configuration

**RULE 0 — these commands and no others.**

```
deepline preflight --json
deepline plays list --json                         # only on "Show me my plays"
deepline plays describe <name> --json              # the contract: inputs, outputs, cost estimate
deepline plays get <name> --source --out build/src/<slug>/   # the code
deepline tools describe <tool_id> --json           # per tool the code calls: inputs, outputs, pricing
```

Never `deepline plays run`, `tools execute`, `runs export`, `db query` or `secrets` here: the first
two spend, the next two read the creator's data, and the last reads credentials. Never `plays save`,
`publish` or `deploy`: those are writes, however they read. Read **prompts first** (intent: the
`deeplineagent` prompts and comments), **code second** (mechanics: comparisons, constants, gates, tool
calls), **names last** (evidence of nothing). Never infer a step, threshold or purpose from a step or
column name. Detail: `references/play-to-skill.md`.

**If a credential is in the source**, reading it was unavoidable; what follows is a choice. Never print
any part of it, truncated or not. One sentence inline, no warning banner. Never instruct rotation; you
cannot see what that key touches, so the decision is theirs. No unsolicited debugging of their play.

## Step 5 — Derive the complete draft, before asking anything

Write a **complete** `SKILL.md` to `build/<slug>/` (not an outline, not a plan). It must carry a
**`## Declared inputs` section**: a three-column table of every value the installer supplies, what they
supply, and what happens if it is missing. That section is what makes the skill portable, and it is the
only body section the lint blocks on. All four worked examples model it.

**A file you name, you write, in this step, before anything else happens.** If the draft says *copy
`references/<name>.md`*, that file exists on disk by the end of Step 5. If you are not going to
write it, inline the content and name no file. **Never emit a reference to something that does not
exist yet.** A creator who asks for "just the SKILL.md" walks away with a promise the next step had to
keep.

**And the draft has to be able to READ an answer sheet, or writing one accomplishes nothing.** The
instruction goes IN THE BODY, in the step that collects the definition, and it says three things:

> **If an answer sheet is present beside this skill, load it and ask only for what it does not
> cover.** A partial sheet is normal; a value it is missing gets asked for on its own rather than
> restarting the interview. **Say which values came from the sheet** before using them: a sheet
> applied silently is a wrong field nobody catches. **If there is no sheet, say nothing about
> sheets.** At delivery, offer to save the answers back, in words that explain the offer rather than
> naming it.

**And SAY WHAT THE FILE IS.** Four beats, in this order: it is not part of the skill · what it holds ·
what it saves them · what it lets a colleague do. Then the line about credentials, which is not
optional. Something close to:

> "Want me to save your answers to a file alongside this?
>
> It isn't part of the skill: it's a short note of what you told me (your CRM, the field names, the
> thresholds you picked). Two reasons to keep it. **You** never answer these questions again when you
> re-run this. And if you **send it to a teammate** next to the skill, the skill reads it and asks them
> only what the file doesn't cover.
>
> It stays with you: never committed, never in the PR, and it holds no passwords or API keys."

**It skips questions. It never skips a gate.** The batch, the cost and the write approval are runtime
and still run: somebody working from a sheet is answering fewer questions, which makes them exactly the
person who most needs the pause.

**Every draft names the SHAPE of its output under a heading spelled exactly
`## Representative output`**: the columns, or the fields per item, and two or three rows of obvious
placeholders. Not the values: a shape.

```
## Representative output

### Weekly at-risk digest

| Rank | Account | Renewal in | Signals fired | Evidence |
|---|---|---|---|---|
| 1 | Northwind | 21 days | champion moved · headcount fell | champion now VP at a competitor; 512 → 470 |
```

**ONE `###` PER THING THE INSTALLER RECEIVES, AND COLUMNS ARE NOT DELIVERABLES.** A five-column table
under one heading is ONE artifact with five fields. Two artifacts, two blocks, each under a heading
nothing else in the section repeats.

**Placeholders, never real values.** `Northwind` and `Contoso` are transparently invented, which is the
point. **BUT A PLACEHOLDER IS A CELL, NEVER A WHOLE DELIVERABLE.** When the output is prose (a brief, a
memo, a recommendation), show ONE FILLED INSTANCE with plausible-shaped numbers and a fake subject. A
bracketed skeleton (`**Title tag (~N chars):** \`[title]\``) demonstrates nothing:

| Output is | Show | Because |
|---|---|---|
| a table or a per-item list | headers plus two or three placeholder rows | the headers are the content; the cells are interchangeable |
| prose, a brief, a narrative | one worked instance, written out | the prose *is* the content and a blank frame demonstrates nothing |

**AND IF THE OUTPUT RANKS ANYTHING: A CAVEAT BESIDE THE NUMBER DOES NOT CHANGE THE NUMBER.** A reader
going down a ranked table acts on the order; the evidence column is what they read *after* deciding. So
a caveat that would change who gets contacted lives where the decision is made:

- **In the sort**: it lowers the score, and the weights say why.
- **Or in its own bucket**: kept out of the ranking rather than ranked with an asterisk.
- **Never only in prose beside the rank.**

The tell: **the draft's own evidence line contradicts its own band.** Any row whose evidence names a
mismatch with a stated criterion is rescored or bucketed. **And check the weights against the words the
creator used**: a brief's own headline phrase weighted fourth out of five is how an off-brief candidate
clears the bar honestly.

**Every draft carries a `## What this skill touches` section: Reads, Writes, Never.** Three labelled
lines, all three named even where the answer is one word. Write `Writes: nothing` explicitly when the
skill only reads. Derive it from the steps you just drafted; you know what it reads and writes, because
you wrote it.

**AND THE STEPS THAT STOP ARE DECLARED, NOT READ OUT OF PROSE.** A fourth line:
`**Halts** — Step 4 spend-approval, Step 6 send-approval`. The vocabulary is closed (`sample-review`,
`spend-approval`, `send-approval`, `write-approval`, `other`) and the lint blocks on any other word.
**A step that waits on two things repeats the step number**, `Step 3 spend-approval, Step 3
write-approval`, never a compound like `cost-and-send`, and prose about a combined gate is REWRITTEN as
a repeat, never deleted. **A boundary is not a halt:** a step that drafts instead of sending declines to
act, and that belongs in `Never`.

**Decide the shape before the steps, and derive it from the job rather than defaulting to it.** Two
shapes exist: **call the tools** (`deepline tools execute`, the agent runs the loop) or **ship a play**
(a `.play.ts` the skill runs with `deepline plays run`). `references/determinism.md` names the forcing
conditions for a play: **something has to run when no agent is present** (a cron or webhook trigger, or
a `deepline monitors` deployment), or the volume exceeds what one conversation can hold (more than about
20 rows of tool calls). Put it to them as one thing:

> **Who starts this — you, or a signal?**
>
> - **You** — *`<what they would do to ask for it>`*  ← *assuming this*
> - **A signal** — *`<the event that would fire it instead>`*
>
> Say *signal* to flip it.

**Both branches are written from the skill in hand**, never from an example table. Then state the shape
you chose and why, in one line, and let them correct it. It is not one of Step 6's three.

**A skill that ships a play must BUILD it, not describe it.** The skill carries the `.play.ts` under
`scripts/`, runs `deepline plays check scripts/<name>.play.ts` before anything else, and runs it with a
pilot input first. A skill that says *"wire five steps in dependency order"* gets the work done once, by
hand, in the conversation, and the play never exists.

### When the work is all judgment, Deepline belongs in the INPUT, not in a wrapper

Some skills are genuinely all logic: write the email, score the row, pick the tier. That is allowed.
**The wrong repair is a wrapper**: turning a copywriting skill into a play with a CSV trigger adds a
thing to maintain and changes nothing about the output. **The right repair is an input.** Ask what the
judgment operates on, and whether a better version of that input is one tool call away:

| A skill that decides… | …decides better when the input carries |
|---|---|
| what to say in a first line | a funding round, a job posting, a stack change: a reason to write *today* |
| which tier a row belongs in | headcount trend and hiring signal, not just the self-reported band |
| whether a signup is worth a rep | the company behind the personal email address |
| which competitor moved | the page as it reads now, not as it read when the list was built |

That is a real dependency: it spends real credits, and it survives the question *"why not just ask
Claude?"*. **So name the tool that fetches the better input, and price it**, or say plainly none exists.

**Every draft states its read/write posture at its own Step 0**, a statement and not a question, and
its Step 0 is a gate: `deepline preflight --json`, and if it fails, name the component and the one
command that fixes it, then stop.

**Every draft runs a small batch first, and the kind depends on whether the step can be taken back.**
A read-only or reversible step gets **a real pilot of 1 to 10 rows** whose output the installer
inspects. An **irreversible** step (an enrollment, a sent message, a CRM write) gets **a dry run**
first, then a small live batch: a ten-row "test" of an enrollment is ten real people really enrolled.

**Then exactly one gate before anything bills or mutates, and it carries everything**: the batch
result, the full cost, exactly what will be written and where, and the ask. **Name the write in the
word**, because a CRM write through the installer's own connected account prices at **zero**: `deepline
tools describe hubspot_update_company --json` reports `pricing.displayText: "Free"` and
`billingSource: own_provider_credentials`. A cost gate reporting a truthful zero would otherwise wave a
hundred CRM records through in silence. **Never fold away the ask; never split it into three.**

**And two things never go in a draft, whatever the creator asks for.** No step that **destroys data**
(no delete, no cleared field, no populated value overwritten with a blank; an update that empties a
field *is* a deletion). And no step that **moves the installer's data somewhere they did not name**:
not to a third-party endpoint via `generic_http_request`, not into an author's org, and no more real
customer detail into a `deeplineagent` prompt than the job needs. If a creator describes either, the
draft emits a reviewed list and they run the destructive part in the system that has their audit log.
See `references/skill-contract.md`.

**Any step that spends money must name what runs.** *"Enrich the author to get an email"* resolves
differently for every reader. Four things per paid step: **what runs** (the tool ID or play ID, confirmed
with `deepline tools describe <id> --json` or `deepline plays describe <id> --json`), **what goes in**
(which fields, from which declared input, matched to `inputSchema`), **what to verify in the response**
(the exact path, verbatim, as you saw it), and **what it costs** (`pricing.displayText` and
`pricing.unit`). Find candidates with `deepline tools search "<intent>" --json`; both commands are free.
**Never write a tool ID you have not described**: an invented ID is the most common way a fluent skill
fails on its first call, and `scripts/lint_skill.py --online` blocks on one. Never carry a catalogue of
tool names into a skill as current fact; the procedure outlives the names. Detail and the traps:
`references/determinism.md`. Per-provider gotchas live in the `deepline-gtm` skill's
`provider-playbooks/`.

**IF THE DRAFT'S FIRST STEP IS A SEARCH RATHER THAN AN ENRICHMENT**, price it where it is designed: a
search row is **thinner than the set of fields you can filter on**, so anything the skill judges or
links to beyond what it filtered is a per-row enrichment. Read the search tool's `outputSchema` before
promising a field, and prefer a search tool whose rows already carry what the skill needs.

**AND SOME STEPS CANNOT BE PRICED BEFORE THEY RUN. Those need a cap, not a multiplication.** For a
step whose row count is its *output* (a search, a list expansion, any tool whose `pricing.unit` is
`result`: `crustdata_v3_person_search` says *"Search cost is based on returned rows, not the matched
total_count"*) and for a usage-priced tool (`deeplineagent` reports *"Calculated after
execution from returned usage"*), the draft must:

- **Say the cost depends on what it finds**, and give the per-unit price rather than a total.
- **Carry a cap the installer sets** (a maximum row count or a maximum spend) and stop at it.
- **Approve in two stages where a cap will not do**: run one call, report actual rows and spend, then
  ask before the rest.
- **Re-read `deepline billing balance` after the step and report the real figure**, not the estimate.

Measured on a Clay action, 2026-08-28: a skill told its installer 6 credits and spent 33, because the
price was per returned row and two identical calls returned 4 rows and 25. The arithmetic was right and
the premise was wrong.

**AND ASK IT IN PLAIN WORDS.** The four bullets are the mechanism; this is what the person paying hears:

| Do not say | Say |
|---|---|
| "This step has unbounded cost." | *"This one charges for each person it finds, and I can't tell you how many it'll find until it runs."* |
| "Set a cap on the fan-out." | *"What's the most you'd want to spend here? I'll stop when I hit it."* |
| "Two-stage approval on the batch." | *"Let me do one and tell you what it actually cost, then you decide about the rest."* |
| "Reconciling estimated against actual spend." | *"That cost 33, not the 6 I told you. Here's what I got wrong."* |

**Ask in the unit the person already thinks in**, never make them do the multiplication, one question,
one decision, the honest number in it. **And never present a step you cannot price as the cheap path.**

**Two kinds of thing belong in the declared inputs, and the second is the one that gets missed.**
Technical handles (play names, secret names, list or campaign ids, CRM object and field names) have a
shape, so the lint catches some of them. **Business context does not**: the CRM, the ICP, the weights,
the tier cut-offs, what counts as senior. A hardcoded `1000` is indistinguishable from a considered
`1000`, so it has to be caught here.

### A named tool becomes an interview instruction, not a dependency and not a classification

When the source names a specific vendor (a CRM, a sequencer, a warehouse), do **not** preserve the
vendor, and do **not** try to work out what category of thing it is. Write the *asking* into the skill:

| The source says | The skill says |
|---|---|
| `read the HubSpot company record` | ask which CRM they run, then read its schema and show the mapping you found |
| `push to the Instantly campaign` | ask where sequences live for them, and what identifies the right one |
| `query the Snowflake table` | ask where the data lives and how to read a row from it |

The tool becomes a **declared input** and the skill carries the **instruction to elicit it**. A
declared input with nothing asking for it is a form nobody fills in.

**The test for whether a vendor name survives, per sentence: if the installer does not have this
vendor, does the sentence stop being true?** In a boundary, generalise it. As an illustrative value or
a trigger phrase, keep it (removing a trigger phrase is a defect). Where the behaviour is genuinely
that vendor's, keep it and declare `**Vendor-specific**` in `## What this skill touches`.

**The boundary is derived here, not asked, and it is carved against JOBS.** The `Do NOT use` lines exist
because an installed agent picks a skill by matching its `description`. Write them as the adjacent jobs
this skill is not for: *"not for scoring a list you already have, not for writing a score back to a
CRM"*. **Never name a sibling skill to the creator, in the draft or in your own narration**; the
exception is a skill the draft actually hands off to (`deepline-gtm`, for example), which is a
dependency, not a comparison. The creator cannot answer *"where should I draw the line?"* and must
never be asked; at most, **one closed question in their world** (*"if someone asked for X instead,
should this handle it, yes or no?"*).

**The traceability rule, which is what keeps this honest.** Every substantive claim is exactly one of:

1. **derived**: traceable to a line of the play source, a prompt, or a tool's `describe` output you
   actually read;
2. **supplied**: the creator said it in Step 6;
3. **a gap**: named in a `## What this skill does not claim` body section, one plain sentence each.

There is no fourth category. Drafting before asking makes invention *easier*, so check it by hand
before Step 7: **list every number in the draft and point at the source line or the answer it came
from.** A threshold the draft states that the code does not contain, or one the code contains that the
draft dropped, is a build failure, not a nuance.

### The insight is a substantive claim, and it is the one that escapes

The insight is prose, so nothing mechanical catches it, and it is the most consequential line in the
skill. **Sharpening what the creator said into a claim they did not make is invention, however good the
claim is.** Caught on a real run: the brief said *"a badge scan gets a generic nurture"*; the draft
shipped **"a badge scan is proximity, not interest; raffles and walk-bys scan too"**, a different and
stronger claim with detail that appeared nowhere in the brief.

**So it gets asked.** One closed question, in their world:

> "You said a badge scan gets generic nurture. I'd sharpen that to *a scan is proximity, not
> interest*: raffles and walk-bys scan too. Is that what you meant, or is it more than you'd claim?"

A yes makes it **supplied**. Anything else and the creator's own phrasing ships, with the sharper
reading recorded as a gap. This question does not count against Step 6's budget.

#### A yes only counts from the person who built the source. Ask that FIRST, on the play route.

The CLI reads any play in the org, including one somebody else built. **So before the insight
question, establish authorship**, one closed question:

> "Did you build this play, or are you working from someone else's? It changes one line: an insight
> only ships as confirmed if it comes from whoever designed the thing."

- **They built it**: proceed; a yes makes it `supplied`.
- **Somebody else built it**: **do not ask them to confirm the insight, and do not treat an unprompted
  confirmation as one.** The derived reading ships, `## What this skill does not claim` says it is not
  author-confirmed, and `**Derived from**` in `## What this skill touches` names whose work it was.

**Enthusiasm is not authority.**

**THE FRONTMATTER IS `name` AND `description`.** That is what the repo and the CLI sync read.

```yaml
---
name: your-skill-slug          # lowercase, hyphens, matches the directory name
description: |                 # what it does; "Use whenever someone asks: …"; "Do NOT use it for …"
  …
  Requires: Deepline CLI, https://code.deepline.com
---
```

Anything else is read by nothing, so do not reach for an extra key as a place to put something; it
belongs in the body, where a reader can see it. Full field guidance: `references/skill-contract.md`.

**And a gap declared in `SKILL.md` must not be contradicted by a supporting file.** The main file is
where the discipline gets applied and the supporting files are where it leaks, so re-read every
reference against the gap list before Step 8.

If the play is too thin (names and nothing else), say so and offer the interview. Do not pad a draft
out of four steps; `references/examples/low-yield-fallback/SKILL.example.md` is what the honest version
of that outcome looks like.

## Step 6 — Ask only what the draft could not settle

**A question is allowed only if the answer changes what gets written.** These four classes qualify and
nothing else does:

| Class | Why the tool cannot answer it |
|---|---|
| A decisive threshold with no derivable justification | the value is in the code; the *why* is nowhere |
| A gate whose condition is visible but whose reason is not | `if (!row.video_id) return skip` is readable; "a page without a video is pointless" is not |
| A hardcoded count that may be an editorial rule or an accident | three fixed steps vs "N steps, discovered" are **different skills** |
| An orphan step | a dependency graph cannot tell an abandoned experiment from an optional input |

Everything else becomes a gap in `## What this skill does not claim`.

- **At most three, and the boundary is not one of them.** Budget by class, not by turn count.
- **One decision is one question, even when it has two moving parts.** Put the tie-break inside each
  option rather than asking it afterwards.
- **Keep option text short enough for a picker to render**; reasoning goes in the question body.
- **Order by insight yield, not impact.** A gate question returns intent; an orphan-step question
  returns bookkeeping.
- **One question per message. Then stop and wait.**
- **ELI5 the context in one sentence.** *"Titles cap at six words. Longer reads better in the CMS but
  wraps on cards: hard rule, or is eight fine?"*
- **"Draft it" ends this step immediately**, and so do one-word answers.
- **Never supply an answer the creator did not give.** If they answer nothing, the draft ships with a
  prominent gap saying the intent behind the thresholds was never confirmed.

**"I don't know, that was arbitrary" is a genuinely useful answer**: it becomes a documented gap
instead of a fake rationale. **Warm framing, identical labels**: `unknown` stays `unknown`.

### The outside-service question: a fifth class, and it costs nothing when it does not apply

**Asked only when the draft YOU JUST WROTE needs a provider the installer may not have**: a tool whose
`describe` shows `billingSource: own_provider_credentials` (their own HubSpot, Salesforce, Instantly),
or a `generic_http_request` to a third-party host with its own key. Ask it as a decision with a real
"no" in it:

> Step 2 reads your HubSpot companies, so right now this does nothing for anyone not on HubSpot. What
> should they get instead?
>
> **A**: a reduced run from a CSV export. Less automatic, still useful.
> **B**: nothing; it is HubSpot-only, and the skill says so up front.
> **C**: something else you would write.

**B is a real answer**: it writes `**Vendor-specific**` into `## What this skill touches`. A and C
become the `If it is missing` cell. Either way the answer goes into the file.

## Step 7 — Show the skeleton, confirm, then build

Show the **skeleton of the actual draft**, never a prose summary. **In plain language, not field
names:**

| Instead of | Say |
|---|---|
| "derived / supplied / gap" | "from your play" / "you told me" / "nobody established this" |
| "the 4 machine-comparable claims" | "the four numbers I could check against your code" |
| any other skill, by name, in the draft OR in your own narration | the boundary as adjacent jobs |
| "two lint reports are false positives" | nothing. Fix it or report the one that matters |
| "the description ran 55 chars long" | "I shortened the description"; the measurement is ours |

**The test before any sentence about how the draft was made: would they act differently if they knew
this?**

**It must fit on one screen:**

- the title, and one line on what it produces;
- **the insight, with its provenance**: *your words* / *my sharpening, confirmed* / *your words as you
  put them, because you didn't confirm the sharper reading*;
- the steps as one-liners, in dependency order, each paid step with its tool and its price;
- **every number and where it came from**: *your play* / *you told me* / *nobody established this*.
  **Three provenances, not three grades.** Never apologise for a creator's own judgment: *"these are
  your thresholds; that's what makes them worth shipping, and the skill says so"*;
- **what this skill does not claim**, one plain sentence each;
- **what the installer has to supply**, naming anything that was a credential or an org handle;
- **the boundary as one line in their language** (*"not for X, not for Y"*).

Then **one** question: *"anything wrong?"* If it does not fit on one screen it is too long.

**Write the file ONCE.** Compose the whole draft in memory, then write it in a single pass; each small
edit is a permission prompt and a diff the creator has to read. **And write it as `<slug>/SKILL.md`,
wherever it lands**: the folder name is how the lint and the repo find the skill.

## Step 8 — Answer sheet, lint, pilot, hand back

**FIRST: emit the answer sheet. Every route reaches this step and only this step.** Every specific the
creator gave you that became a declared input, you hold both halves of right now: the question that
will ship, and their own value for it. Write the pairs to a sheet **beside** the package (never inside
it; the lint blocks on that), keyed to the declared-input names. Identifiers only: if a creator offers a
token or a password, refuse it and say why. **Annotate each value as a decision they made or a default
they accepted**, and **if the skill has little durable configuration, say that out loud** rather than
emitting a thin file silently.

**Until this step runs, what is on disk is a draft**, and say so if they ask for it.

```
python3 "$SKILL_DIR/scripts/lint_skill.py" build/<slug>
python3 "$SKILL_DIR/scripts/lint_skill.py" build/<slug> --online     # resolves every tool and play ID
```

`0` clean · `4` your package has blocking findings · `2` bad invocation · `1` the tool is broken, not
the package. What each check means: `references/validation.md`. **Run `--online` before Step 9**; the
offline run lists the IDs it found and says they are unresolved.

If the skill ships a play, also:

```
deepline plays check build/<slug>/scripts/<name>.play.ts
```

which bundles and validates it without starting a run.

**On a skill somebody else wrote (the existing-`SKILL.md` route)**, lint it before touching anything,
and **rename what they wrote, never author what they did not**: retitling `## Output` to
`## Representative output` is formatting and needs a shown diff and a yes; a missing
`## Declared inputs` is author-only, because its third column is a claim about degrade behaviour only
the author can make. Send it back. **Several finished skills at once: lint the lot, report one table,
worst first**, and say a partial pass out loud.

**BLOCKING findings you fix. REPORT findings you MENTION, once, and leave.** Never edit the draft to
clear a report, and never lint twice to watch a number fall.

**Then make each failure branch fire, once, on purpose.** Anywhere the skill says *refuse*, *skip the
row*, *stop and ask*, feed it the input it is supposed to refuse. This is offline reading for most
branches; a branch that needs a live call needs the creator's yes and a stated cost, like any other
paid step. See `references/validation.md`.

**Hand back BOTH, and say what each is for in one line each:** the folder is what goes into the repo;
the sheet stays with them.

## Step 9 — Name both ways to get it into the repo. This step is not optional.

**A linted package is not a finished job.** Do not stop at *"here is your file, it linted clean."*
Name both paths and ask which:

| Path | What happens |
|---|---|
| **You open the PR** | copy the folder into `drafts/<slug>/` of a fork of `https://github.com/getaero-io/gtm-eng-skills`, add a row to `drafts/README.md`, open the PR |
| **I open it** | I do exactly that from this session with `git` and `gh`, after showing you the diff and the PR text, and only on your yes |

New skills go into **`drafts/`**, not `skills/`: `drafts/` is not synced by `deepline skills`, so an
unreviewed skill cannot reach anyone's agent by accident. Promotion to `skills/` (plus
`.claude-plugin/marketplace.json` and the README table) is a later, reviewed PR. Full detail and the
repo's checklist: `references/submitting.md`.

**Neither is the default and neither is recommended over the other.** If they decline both, say where
the package is, that nothing has been pushed, and that either path is still open; then stop. **And do
not re-offer.**

**On the "I open it" path: one message holding the branch name, the file list, the diff stat, the PR
title and body, and the ask.** Then stop and wait. Never push, never open the PR, and never imply the
skill was merged or published; **a PR is submitted for review**. A correction to a PR already open is a
new commit on the same branch, not a second PR.

## Rules

- **NEVER** run a play, execute a paid tool, read run rows or the customer DB, or save, publish or
  deploy a play while authoring.
- **NEVER** write a Deepline tool or play ID you have not confirmed with `deepline tools describe` or
  `deepline plays describe`.
- **NEVER** print any part of a credential, or instruct the creator to rotate one.
- **NEVER** infer a step, threshold or purpose from a step or column name.
- **NEVER** state a claim that is not derived, supplied, or marked as a gap.
- **NEVER** ask a question outside the classes in Step 6, and never two in one message.
- **NEVER** name a sibling skill to the creator or in the draft's boundary; derive the boundary as
  adjacent JOBS and show it as one line.
- **NEVER** show the creator a field name, a stage label or a script name. Say what it means.
- **NEVER** narrate our bookkeeping: how many lint findings, which were overridden, character counts.
- **NEVER** frame creator-supplied logic as a deficiency. Provenance is stated, never ranked.
- **NEVER** push, open a PR, or commit without an explicit yes, and never imply a skill was merged.
- **NEVER** write a paid step without naming the tool, its inputs, what to verify and its price.
  "Enrich it with Deepline" is intent, not an instruction.
- **NEVER** quote a total for a step whose row count is its output; carry a cap, reconcile with
  `deepline billing balance` afterwards, and **never call such a step free or cheap.**
- **NEVER** ask about money in vocabulary the person paying has to decode.
- **NEVER** carry a named vendor through as a dependency; convert it to a declared input **plus** an
  instruction telling the skill to ask for it.
- **NEVER** leave a Clay command, Clay action key or Clay credit figure in a skill as if it were a
  Deepline fact; the lint blocks the commands. A Clay measurement may stay only when attributed.
- **NEVER** state something as settled in a supporting file that the main file lists as unestablished.
- **ALWAYS** put the gaps in a `## What this skill does not claim` body section.
- **ALWAYS** write a `## Declared inputs` section covering both org handles and business context.
- **ALWAYS** derive the full draft before asking anything.
- **ALWAYS** draft, with gaps if needed. Unanswered items are gaps, not blockers. The only thing that
  must never happen is inventing an answer.

## Representative output

### The package

```
build/renewal-risk-radar/
  SKILL.md                      name, description, Declared inputs, What this skill touches, steps,
                                Representative output, What this skill does not claim, Rules
  scripts/<name>.play.ts        only when the shape is a play
```

### The lint line

```
REPORT section_missing              SKILL.md  no `## What good looks like` section

ok · 0 blocking · 4 tool ids, 1 play ids resolved online
```

### The skeleton shown at Step 7

**Renewal risk radar** ranks accounts renewing in 90 days by signals a CSM would act on.
Insight (your words): *usage falling is late; the champion leaving is early.*
Steps: load the CSV · resolve each champion (`crustdata_v3_person_search`, 0.02 credits per returned result,
capped at your 200) · flag moves · rank · deliver. Thresholds: 90-day window (you told me), 40% usage drop (your
play, line 58), seat floor of 20 (nobody established this).
Not for scoring a list you already have; not for writing a score back to the CRM.
Anything wrong?

## What this skill does not claim

- The lint checks form and that tool IDs exist. It does not check that the logic is right for the job.
- Interview-route skills have no ground truth: their logic is the creator's stated intent, unrun.
- The 6-told, 33-spent figure and other measured traps in `references/determinism.md` were observed on
  Clay actions unless marked otherwise; the Deepline pricing fields they map to are named beside them.

## What good looks like

The creator reads the skeleton and says "yes, except one thing." Three questions or fewer were asked,
each naming a specific step, and the boundary was derived rather than handed back. Every threshold
traces to a line of the play or sits in the does-not-claim section, every tool ID resolved with
`--online`, and the PR (if any) went to `drafts/`. The common failure is a skill that is fluent
everywhere and grounded nowhere, and it lints clean, because the lint checks form.

## Worked example

A play that publishes walkthrough pages: `deepline plays get` returns a 300-line `.play.ts` with eight
`ctx.tools.execute` calls and two `deeplineagent` prompts. Ordered by what each step reads, not by line
order, it is six steps. The code holds a six-word title cap, a 200-character hero limit and two gates;
two `withColumn` steps feed nothing. Every tool ID is described and priced (one is per-result, so the
draft carries a cap). The draft is written complete, then three questions: *is three sections an
editorial rule or what this play happened to hardcode* (a different skill either way), *why does a
missing video block the page*, and *are these two unused steps dead or optional*. The answer to the
second is the insight and it was never asked for directly. Skeleton shown, one correction, linted with
`--online`, `deepline plays check` passes, handed over with the answer sheet beside it, and the creator
picks "you open the PR": three questions total.
