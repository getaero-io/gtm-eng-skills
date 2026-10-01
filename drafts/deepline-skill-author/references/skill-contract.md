# SKILL.md — the contract

## Frontmatter

```yaml
---
name: your-skill-slug          # lowercase, hyphens, matches the directory name
description: |
  What it does, in one dense paragraph. Then: "Use whenever someone asks: the actual
  phrases people use." Then: "Do NOT use it to <adjacent job>, or to <another one>."

  Requires: Deepline CLI, https://code.deepline.com
---
```

**Two fields, and both are yours.** `name` and `description` are what the repo, the CLI's skill sync
and an installed agent read. Anything else in the block is read by nothing; put it in the body, where a
reader can see it. (A port from another platform may carry a `ported_from:` line; that is provenance
for reviewers, not a field anything acts on.)

**The description is the trigger**, so write the phrases people actually type and the jobs yours
should *not* be confused with. Those two earn their length; a vague description is the most common
reason a good skill never gets used. The repo's own template puts the triggers on separate lines
(`Triggers:` followed by quoted requests) and ends with the `Requires:` line; either shape works, as
long as real phrases are in it.

**There is no length limit we can point you at.** Trim only because the writing is loose: cut
restatements and mechanism detail, which belong in the body. Chasing a character count is a waste of
the creator's approvals.

**Avoid angle brackets in the description.** `<placeholder>` reads as an unfinished template, and prose
beats slots for the one field a router reads. Write "for a given intent", not "for `<intent>`".

**Say what the skill does not claim, in the body.** A `## What this skill does not claim` section, one
plain sentence per gap, is how a reader decides whether to trust it. There is no frontmatter field for
this: a machine field with no machine is worse than prose, because it looks authoritative.

Write each sentence so it stands alone. *"Never run end to end, so no measured cost or latency"* survives
being read cold; *"stage_e — the machine-comparable claims are markup artifacts"* does not, because a
label was carrying the meaning.

**And check your supporting files against it.** A real submission declared that no conversion rate was
claimed anywhere, while one of its own reference files stated that a variant converts better. The main
file is where the discipline gets applied; the references are where it leaks.

## Body

No section list is required. What follows is the shape the strongest skills in the library
converge on — read off them rather than designed in advance, and the three in
`references/examples/` all follow it. Take it as a checklist of things worth having, not a form
to fill in.

```
# Title (a parenthetical stating the move: "declare the measurement, then count")

The insight: <one bold claim>, then the evidence for it, then what follows from it.

## Declared inputs          <- REQUIRED. See below.
## What this skill touches  <- Reads / Writes / Never. Checked.
## Step 0 — Check the platform works, and say where the work runs
## Step 1 — Collect the definition (interview; do not guess)
## Step 2 — <the decision this skill exists to make>
## Step 3 — Free checks before anything paid
## Step 4 — Small batch, then ONE gate: the batch, the cost, the writes, the ask
## Step 5 — Do the work
## Step 6 — Grade / verdict, single-valued
## Step 7 — Deliver
## Representative output    <- REQUIRED. The literal artifact. See below.
## What this skill does not claim   <- the gaps, in plain sentences
## What good looks like
## Rules
## Worked example
```

**The insight, with its evidence.** One claim, stated in bold, followed by *why you believe it*.
This is the single biggest quality difference in the library. "Job counts can be unreliable" is
not an insight — nothing can be built on it. "There is no such thing as the number of jobs open at
a company, and here are four providers returning 8,945 / 737 / 384 / 332 for one company on one
day" is, because every later step is forced by it. If you cannot state a claim and say what made
you believe it, the skill is probably one enrichment call and does not need to be a skill.

**Put the insight in the title too.** A parenthetical — *(declare the measurement, then count)*,
*(claims vs independently re-derived evidence)*, *(enumerate, then prove coverage)* — so a reader
scanning headings gets the move before the prose.

**Step 0: check the platform, and state where the work runs.** Every good skill confirms the tooling
is alive (`deepline preflight --json`) and names the organization. The best ones also state *where computation happens*, because that
is what it costs: arithmetic in the agent is free, the same arithmetic in a per-row column bills per
row. Cost is a design property, not a footnote.

**Say what the skill touches — twice, because the file and the session are read by different people.**
One fact, two surfaces: a `## What this skill touches` section a reader, the validator and a safety
review can all check, and a sentence at Step 0 the installer hears as the run starts. Reads, Writes,
Never — all three named even where the answer is one word:

```
## What this skill touches

- **Reads** — the account and contact objects in your CRM, and the CSV you supply.
- **Writes** — nothing. Output is drafts for you to review.
- **Never** — deletes a record, clears a populated field, or sends your data anywhere but here.
- **Halts** — Step 3 `sample-review`, Step 4 `spend-approval`.
- **Vendor-specific** — Acme Signals. No account, no reduced mode: the skill does not run.
- **Derived from** — J. Okafor's closed-lost workflow, read as configuration. Not author-confirmed.
```

**`Derived from` is required when somebody else built the source.** It names whose work it was and
whether they confirmed the insight — provenance nobody can reconstruct from the file.

**`Vendor-specific` is for when one named outside service is genuinely load-bearing.** It names the
service and what a non-customer gets. Declaring it puts the requirement where a reader sees it
*before* installing rather than discovering it mid-run — a disclosure, not a waiver. Omit it while
requiring a third-party API key whose `If it is missing` cell says there is no fallback, and a
reviewer sends it back.

**`Halts` is the step numbers that stop and wait, each with one word for what it waits on:**
`sample-review`, `spend-approval`, `send-approval`, `write-approval`, `other`. **A gate covering two
things repeats the step number:** `Step 4 spend-approval, Step 4 write-approval` — never a compound
like `cost-and-send`, and never dropped for being prose. Watched on a real submission: a draft
explained its two-purpose gate in a sentence, obeyed *no sentence*, and shipped one word — the second
claim gone, not restated. A prohibition alone only removes. **A boundary is not a halt** — a step
that drafts instead of sending is a `Never`: it declines to act.

Say `Writes: nothing` explicitly where that is true; it is the most reassuring line a read-only skill
has and leaving it implied wastes it. A partial declaration reads like a complete one, and the axis
left out is the axis nobody checked — which is why the check reports a missing `Never` rather than
accepting two of three. **The end of the file is too late.** A skill whose only no-write statements
live in its last step relies on the installer's agent having read the whole thing and volunteered a
summary; that happens, and it is not a guarantee.

**And this is what makes a safety review possible rather than decorative.** *"Is this skill
dangerous?"* is an open-ended judgement. *"It declares `Writes: nothing` — does any step write?"* is
one claim checked against the body, which is a question with an answer. **A skill that declares
nothing cannot be contradicted**, and that is the whole reason the section is required.

**If the work is all judgment, Deepline belongs in the INPUT — not in a wrapper around it.**
An all-logic skill is a real shape, not a failing grade, and bolting a trigger onto a
copywriting skill so it counts as a workflow adds maintenance and changes nothing about the output.
Ask instead what the judgment operates on, and whether a better version of that input is one call
away: a first line decides better when the input carries a funding round, a tier decides better on a
hiring trend than a self-reported band. That is a real dependency, and it survives the question *"why
not just ask an agent?"* **So name the call that fetches the better input, and price it** — or say
plainly that none exists, because a good logic-only skill beats a padded one.

**Interview steps that say "do not guess."** Where a step needs the user's definition — their ICP,
their thresholds, which fields they rely on — say so, and say that the skill stops rather than
inventing one. Skills that quietly supply a default for a decision the user was supposed to make
are the ones that produce confident wrong answers.

**Free before paid.** Order the work so everything free runs first and can eliminate rows before
anything bills — and name what that saves.

**Then run a small batch, and make the first full run something the installer has already seen.**
Nobody can approve a thousand rows they have not looked at, and *"do you approve?"* on an estimate
alone is a question with no evidence behind it. So the batch comes first, and which kind depends on
one property — **whether the step can be taken back**:

| The step is | Do this first | What it catches |
|---|---|---|
| **read-only, or reversible** | **a real 10-row batch.** Ten rows actually run; show the output | the result is *wrong* — a field mapped to the wrong column, an enrichment returning noise, copy that reads badly |
| **irreversible** — an enrollment, a sent message, a CRM write | **a dry run**, then a small live batch | the *scope* is wrong — four thousand rows where you expected four hundred |

The difference matters and the words are not interchangeable. A ten-row test of an enrichment is ten
rows of output to inspect. A ten-row "test" of an enrollment is **ten real people really enrolled**,
and there is no version of that you get to take back. So an irreversible step simulates before it
touches anything.

**Then one gate before anything bills or mutates — one, carrying everything.** Not a gate for the
cost and another for the write. Everything free happens first, then one message holds all of it: what
the batch produced, what the full run costs, exactly what will be written and where, and the ask.
Then stop and wait.

- **Say it is a write, in the word.** "Updates the account" reads like bookkeeping; *"this writes to
  your CRM, and that is a mutation, not a read"* reads like what it is. Name the object and the field.
- **The gate is not the cost gate wearing a hat, and this is why it must name the write explicitly.**
  An action on the installer's own connected account often costs **no Deepline credits at all**
  (`pricing.displayText: "Free"`, `billingSource: own_provider_credentials` in `deepline tools describe`),
  so a cost estimate can truthfully read *zero* while a
  hundred CRM records change. A gate that only talks about money is silent at exactly the moment it
  matters most.
- **One gate, not three.** Four consecutive confirmations protect less than one does: by the third the
  installer is acknowledging rather than reading, and the one carrying the real lock arrives after
  attention has run out. Fold the showing together; never fold away the ask.
- **Stop a second time only when the batch reveals something they could not have anticipated** — a
  row count far off the estimate, a class of record nobody mentioned. That halt is the gate working.
  A *scheduled* second halt is the kind people learn to click through.

**A skill that writes and does not say so is the worst outcome in the library** — worse than one that
overspends, because money is recoverable and a sequence enrollment is not.

**Two things a published skill does not do at all, approval or no approval.** An approval gate is the
right instrument for a write. It is *not* sufficient for either of these, because in both cases a yes
from someone who misjudged the scope cannot be walked back:

- **It does not destroy data.** No deleting records, no clearing fields, no overwriting a populated
  value with a blank or a default. **The non-obvious half: an update that empties a field is a
  deletion**, whatever the action is called — so a skill that writes must name which fields it sets and
  must not touch anything else on the record. If a job genuinely needs data removed, the skill's output
  is a reviewed list of what to remove and the installer does it in their own system, where their own
  audit log and undo live. There is no delete executor in the action catalogue today, which is a fact
  about this month's catalogue and not a substitute for the rule.
- **It does not move their data anywhere they did not name.** The installer's customer records, contact
  details, deal values and account names stay inside the systems they already live in, plus whatever
  destination the installer explicitly declared. Nothing goes to a third-party endpoint, a
  general-purpose scraper, an author's own org, or a log the installer cannot see. **A prompt is
  a destination too**: putting real customer names and revenue figures into a model call sends them
  somewhere, and a skill should send the least it can and say what it sent.

Both belong in the body where an installer reads them, not only in `## What this skill does not claim`.
A skill that reads sensitive data to do a job the installer asked for is fine; a skill that quietly
relocates it, or empties a field on the way past, is the failure that ends the program's credibility
rather than one run.

**Verdicts from a fixed set, resolved in a stated order.** Enumerate the values — *"five values, no
sixth"* — and rank the rules so the first match wins. "Score highly" is not runnable. Neither are
two bands that both match. Add a value for *"could not measure this"*: abstention is a real answer
and a skill without one will fabricate rather than admit a gap.

**Deliver, and say what was and was not covered.** Sample sizes, skipped rows, unmeasured accounts.
The output should let a reader see the shape of what is missing.

**`## What good looks like` is mandatory, and a bare checklist gets sent back.** That is the stated
consequence, not a warning: a reviewer who cannot tell a good run from a run that merely finished has
no way to review the skill, and neither does the installer. So it describes the *shape of a good
outcome* — what the output looks like when the skill worked, what a thin or failed run looks like
instead, and how to tell them apart. "Returns a scored list" is not that. "Every scored row names the
signal it scored on, and rows with no signal are `unscored` rather than zero" is.

**`## Rules` and `## Worked example`.** The MUSTs and NEVERs, so the boundaries survive being
skimmed, and one example with real values carried end to end.

**Name the job, never the vendor — and this is a rule, not a preference.** Write GTM verbs: *verify
the work email*, *resolve the company domain*, *rank by hiring signal*. Do not write a vendor's
product name into a step, because the installer's org has different providers connected, at
different prices, and a skill naming yours either fails on their account or silently spends on
something they did not choose. The one place a specific name belongs is where you recorded what *you*
measured, labelled as that.

**One of those two is checked and the other is not, and the difference is worth knowing.** The
validator reports a **missing** `## What good looks like` section, because presence is unambiguous.
It does *not* judge whether the section is any good — "a bare checklist gets sent back" is a
reviewer's call, stated here so you know the bar, not a regex verdict.

The vendor rule is **not** mechanically checked either, and could not be without a vendor list that
would rot the way a function catalogue does. A person reading your steps enforces it.

**Reference a supporting file by its relative path, in a code span — never as a URL.** `` `references/<name>.md` ``, not
`https://github.com/…/references/<name>.md`. Three reasons, and the third is the one that bites:

- **The file is yours, not ours.** It ships inside your package and sits beside your `SKILL.md` on the
  installer's disk, so the relative path is the one that resolves there. A URL points at somebody's
  repository, on a branch, at a path — the same portability failure as hardcoding a list id.
- **An installed skill has no network.** The whole distribution promise is no clone and nothing fetched
  at runtime. A relative path reads from disk; a URL needs egress the installer may not have.
- **An absolute URL is not checkable, and the validator goes quiet.** Measured: a relative reference to
  a missing file is a **blocking** finding; the same reference written as a `https://` URL produces
  `verdict: ok` and no finding at all. So a URL does not just risk breaking — it removes the guard that
  would have told you, and a supporting file that ships nowhere validates clean.

A code span rather than a markdown link, because the two render differently outside a checkout. Pasted
into a document or a chat, a link whose target is a bare relative path gets resolved against *that*
tool's own domain — one landed in Notion as `app.notion.com/references/node-…`, a dead link offering to
be clicked. A code span is plain text everywhere and the validator still sees it.

An illustration of a broken reference is a broken reference: written as a live link, the paragraph
above fails the build.

**Push mechanics out to `references/`.** Field paths, provider rosters, per-arm quirks, schemas.
Keep the body about *decisions*; a body that is mostly field names is a reference file with the
wrong name. If nothing warrants a reference file, do not create one — `account-tier-scoring` is one
file and is one of the best skills we have.

## Declared inputs — the one section that is required

**A skill that only works in the author's org is not a skill, it is a note to yourself.** This
section is what makes the difference, and it is the only body section the lint blocks on.

**The lint checks that it exists; a person checks that it is any good.** No tool can tell a considered
threshold from a hardcoded one, so a thin one is not rejected by a machine, it is sent back by a human. Writing it well is the cheapest
way to make that review fast.

Every value the installer supplies gets a row. Three columns, because each answers a different
question:

```
## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and if an answer does not exist say which step becomes
unavailable rather than guessing. Where a default IS defensible it is named below, and using it
means saying so in the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The book** | CSV or CRM list of accounts, minimum one domain column | no default — there is nothing to score |
| **Size thresholds** | the headcount cut between segments | the author used 1,000 and 50; ask, and if they have no view use them and SAY they are borrowed |
| **Window** | N days | 30 days is defensible and must be stated; never leave it unset, which silently means all time |
```

**Two kinds of thing belong here, and the second is the one people miss.**

| | Example | Why it is the installer's |
|---|---|---|
| **Technical handles** | saved-play names, secret names, list and campaign ids, CRM object and field names, API tokens | they exist only in your org and resolve to nothing in anyone else's |
| **Business context** | the CRM, the ICP, weights, tier cut-offs, verticals, what "senior" means | they are the installer's judgment about their own market, and an author's numbers are borrowed at best |

The technical half a reviewer can catch, because an id has a shape. **The business half
it cannot** — a hardcoded `1000` is indistinguishable from a considered `1000`. So this is the part
that depends on you, and it is the difference between a skill someone can run and a description of
how *you* run yours.

**The vendor rule above has a second half: write the asking into the skill.** Naming the job instead
of the vendor makes the tool a declared input — but a declared input with nothing eliciting it is a
form nobody fills in, so the skill also carries the instruction to ask at install time.

| Instead of | Write |
|---|---|
| read the HubSpot company record | ask which CRM they run, then **read its schema and show the mapping you found** |
| push to the Outreach sequence | ask where sequences live for them, and what identifies the right one |
| query the Snowflake table | ask where the data lives and how to read one row from it |

**Ask for a decision; never ask for a recital.** The row above says *ask*, and it has been read as
*ask the installer to list their own field names from memory* — which produces an intake nobody wants
to start. A skill authenticated to a system can usually **read** that system's shape, so:

| When the input names | Do this | Because |
|---|---|---|
| a field, object or id in a system you can reach | read it, **show the mapping, ask them to correct it** | it is a fact you can look up, and a wrong guess is visible beside the right one |
| a judgment about their market, money or people | **gate it** — no default, stop and ask | nobody can look up who the invite comes from |

Confirming a mapping is cheaper than recalling one and more reliable: a schema read off the live system
beats one typed from memory at the end of a day. **The introspection that makes a skill deterministic
is the same thing that removes the interrogation** — those are not a trade. Gate the judgment calls
absolutely; a substituted sender or an unset suppression list is not a recoverable error.

**Show the shape you need, then ask only about the gaps.** Four steps, and the third is the one that
gets skipped:

1. **Name the shape** — the fields this skill needs, as a small table, with what each is for.
2. **Read their system** and match it against that shape.
3. **Show the mapping you found**, including what you could not match, and invite corrections.
4. **Ask only about the unmatched rows.**

A conventional setup then answers two questions instead of seven, and an unusual one gets the shape as
an explanation of *why* it is asking rather than a bare demand for field names. **And where the system
cannot be introspected, the shape is still the right thing to show** — ask them to paste a field list,
a header row or one sample record and map from that. That is the honest fallback, and it is still far
better than a recital. What it must never become is a vaguer input: a loosely-worded field request does
not reduce guessing, it moves the guess somewhere nobody can see it.

**Then ask lazily.** Front-load only what changes scope or cost, because those decide what gets priced.
Ask the rest at the step that needs it. Fifteen questions up front and fifteen spread across a run are
the same rigour and a completely different experience.

**And a default they waved through is borrowed, not theirs.** The declared-inputs example above says
*"if they have no view use them and SAY they are borrowed"* — this is that rule generalised. Wherever
you offer a recommended value, record whether it was chosen or merely accepted, and say which at
delivery. That is what makes a soft default safe rather than a guess wearing a number, and it is the
precondition for softening any gate at all.

**The test, applied per sentence rather than per word: if the installer does not have this vendor, does
the sentence stop being true?**

- A **boundary** — "do NOT use for Salesforce hygiene" — stops being true and wrongly excludes them.
  Generalise it.
- An **illustrative value** — "`uses Salesforce` is a technographic enrichment, not an ICP filter" —
  stays true and still teaches. Keep it.
- A **trigger phrase** — "do they run Shopify or HubSpot" — stays true, and it is how anyone finds your
  skill. Keep it; removing it is a defect, not a cleanup.
- A **genuine vendor dependency** — a quirk of one API — is *about* that vendor. Keep it, and declare
  `**Vendor-specific**`. Rare, and real. **A data feed is not a quirk:** name the capability, offer
  the vendor as one way to get it, say what a reduced run looks like. Read as *I may name myself
  throughout so long as I admit it*, this bullet becomes a licence, which is not its job.

Do not try to classify the tool into a category first. The skill does not need to know what kind of
thing it is; it needs to ask.

**The third column is not decoration.** "If it is missing" forces you to state what degrades rather
than marking everything mandatory, and it is the same discipline as saying what a skill does not
claim: a reader can then decide whether they have enough to start.

## The answer sheet — this table, filled in

**Your real values are allowed to exist — just not in the `SKILL.md`.** Every input above is a question
the installed skill asks, and with nowhere else to put the answers a creator's only option is leaving
field names in the body, which is the thing we reject. So they go in a small file beside the package,
keyed to the names in this table:

```
skill: webinar-follow-up
answers:
  crm: salesforce
  score_field: Custom_Fit_Score__c
  hot_threshold: 80
```

**Key it to this table and nothing else**, so a gap is visible by reading the two together.
**Identifiers only — never a token or a password.**

**Four rules for the skill you write.** Where it collects the definition: *if a sheet is present, load
it and ask only for what it does not cover* — a partial sheet is normal, and a new input gets asked for
on its own rather than restarting the interview. **Name the values it supplied and invite corrections**,
because a sheet applied silently is a wrong field nobody can catch. **No sheet, no mention of one** — an
announced absence introduces a concept only to report it missing. At delivery: *offer to save the
answers, private, never published*, worded to explain itself.

**It skips questions. It never skips a gate.** The batch, the cost and the write approval are runtime,
and they still run. A sheet means the person is answering fewer questions, which is exactly the person
who needs the gate most.

## Hard requirements

- Exactly one `SKILL.md` at the package root.
- Every relative reference resolves to a file inside the package.
- No org identifiers: saved-play names, list or campaign ids, secret values, CRM record ids.
- Every Deepline tool and play ID resolves with `deepline tools describe` / `deepline plays describe`.
- No credentials, no private hostnames.
- Everything the installer must supply is a **declared input**, named in the body.

## The numbering is a contract, so say so in the body

**A numbered step does not begin until every step before it has its inputs.** That looks self-evident
on the page and turns out not to be. Watched on a real run of a shipped skill: the agent wrote a
204-line implementation of Step 2 before asking Step 1 for the file it was meant to process — and one
of the uncollected inputs decided that code's central policy. It looked finished and was built against
a guess.

So write the rule down rather than trusting the numerals:

> Do not start a step before the steps above it have their answers. If a declared input is missing,
> ask for it — never assume a default and continue.

One line, and it is the difference between a skill that stops and one that produces confident output
from inputs nobody supplied.

## Step 0 is a gate, not a repair shop

**When the platform check fails, report it and stop.** Watched on a real run: told the installed CLI
was below the server's minimum, a skill spent ninety seconds fetching a *different*
repository hunting for a newer release. The diagnosis was correct; the installer read it as a hang.

> If the platform check fails, say which component is wrong, which version is required, and the one
> command that fixes it. Do not install, upgrade or fetch anything to repair it.

An environment the installer has to fix is not a step your skill owns.

See `references/package-layout.md` for layout, `references/determinism.md` for what
any step that spends money has to name, and `references/validation.md` to check all of the above
locally.

**Route on the inputs the installer has, not on what the data turns out to say.** A skill that opens
by asking *which identifier do you hold* — a domain, a name, a profile URL, an email — and branches
there is deterministic before it has read anything, because the branch is decided by the request
rather than by a result. Branching later, on what a lookup returned, means two installers with the
same inputs can take different paths and neither can tell why. Where the arms differ in accuracy or
price, say which input leads to which arm, so the choice is the installer's and not a silent default.

## One audience: the agent

**Everything in this file is written for an agent, end to end.** Do not add a `## Listing`,
`## Marketing` or "for the reader" section; a file with two audiences serves neither. What it owes a
human reader is already here: `description` as a router string, `## What this skill touches` as a
disclosure, `## What good looks like` as your own standard for a correct run, and the row you add to
the repo's README table when the skill is promoted.

## `## Representative output` — the one thing a reader cannot derive

**The artifact itself, written out.** A reader can work out your steps from the body. What they
cannot work out is what a plausible score, evidence sentence or exclusion reason looks like *in your
domain*, so if you do not write those, the installer's agent invents them.

**Give the literal table.** Headers, then two or three rows of transparently invented data — not a
description of one, and not a bracketed frame:

```
## Representative output

### Weekly at-risk digest

| Rank | Account | Renewal in | Signals fired | Evidence |
|---|---|---|---|---|
| 1 | Northwind | 21 days | champion moved · headcount fell | champion now VP at a competitor; 512 → 470 |
| 2 | Contoso | 44 days | usage fell 40% | weekly active seats 88 → 52 since March |

### Coverage line

142 accounts renewing in 90 days · 138 scored · 4 skipped, no renewal date on file.
```

**Each `###` names one thing the installer receives, and the columns beneath it are that thing's
fields.** Deliver two artifacts, write two blocks. **Columns are not deliverables** — five columns
under one heading is one artifact with five fields, not five outputs, and this is the distinction the
a reader gets wrong when the blocks are missing. Every block needs a heading nothing else in the section
repeats, and filled content under it.

**`Northwind` and `Contoso` are the contract, not real customers.** The header carries the meaning,
so the cells can be obvious inventions — and they should be, because real rows ship whatever your
data happened to be.

**If the output is prose — a brief, a memo — write ONE FILLED INSTANCE under its heading instead.**
Invent plausible-shaped numbers, keep the subject fake. A bracketed skeleton reliably fails here:
`**Title tag (~N chars):** \`[title]\`` has been copied into real output verbatim, brackets and all.
The frame was empty and the agent had nothing else to show.

**And it is only representative** — not a promise of yield and not a benchmark.
`## What this skill does not claim` still owes the reader the gaps.

### Five things that separate a good one from a present one

Presence is all a validator can check. The first of these outranks the other four.

1. **Write it for someone who has not read your skill.** This is the one section a *person* reads
   while deciding, not an agent reads while running — so no term you have not already explained in
   plain words, and no shorthand from your own head. A cell reading `QUALIFIED_FOR_REVIEW`, a
   "two-source floor", an "unmatched identity": each sends the reader to a step they never opened.
   Say what happened in words. *"Rests on one source — take that walkthrough away and she drops to
   49, under the cut-off"* costs nothing and needs no glossary.
2. **The verdict enum, stated once — not in every cell.** It has to be identifiable, because
   installers filter on it: one line beside the table, *"the first table is `QUALIFIED_FOR_REVIEW`,
   the second `RESEARCH_REQUIRED`, and those are the only two verdicts"*. Lowercase values an
   installer configured (`mid_market`) read fine in a cell; machine constants do not, and a
   reviewer will flag them.
3. **Show a row that did not succeed, and why in a sentence anybody can read.** Four wins teaches
   the reader that your skill always wins. "Three case studies, none saying who did the work" tells a
   reader more about your method than any passing row does.
4. **Give a number its scale and its bar.** `72` is unreadable; `72 / 100, cut-off 55` is a
   verdict. Claim no precision the method has not got: if the weights are proposed or
   installer-supplied, `72` is honest and `72.4` asserts calibration you disclaimed elsewhere. And
   **where a score leans on one source, show it without that source** — a candidate dropping 43 → 26
   when one citation goes is *why* it reads "research required" instead of merely asserting it.
5. **One brief, one kind of candidate.** A table mixing a person and an agency is confusing before
   jargon even arrives. If your skill handles both, show one — or add a column saying which.



