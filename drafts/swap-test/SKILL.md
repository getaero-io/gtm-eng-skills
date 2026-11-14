---
name: swap-test
description: |
  Measure how much of a "personalised" cold email is template, then rewrite the template
  sentences from sourced facts. Every sentence gets one label: slot (would still read the same
  with another prospect's name and industry swapped in), a fact about the prospect, a fact about
  the sender's work, or exempt (greeting, sign-off, opt-out line). More than 30% slot sentences
  fails the email. Each slot sentence is then replaced by one that spends a fact with a source,
  or deleted; a number that appears in no source row never enters the rewrite. Run on a batch
  across several prospects and it also catches any rewritten sentence that came out identical for
  two prospects, which is template by definition. Returns the rewritten email, a before-and-after
  sentence table with the fact behind every change, and the density line ("2 of 9 swappable").
  Use whenever someone asks: is this email actually personalised, how much of this is template,
  make this email specific, why does this read like a sequence, check my first line, review my
  ABM email, does this pass the swap test. Do NOT use it to build a prospect brief (an account
  research skill does that), to pick which case study to use, to check deliverability words, or
  to write a sequence from a blank page (a sequence-writing skill does that; this one takes its
  output).
ported_from: clay-run/clay-skill-creator/skills/matteo-fois/swap-test
---

# Swap test (would this sentence survive a different prospect, unchanged?)

The insight: **personalisation is not a name in the first line. It is the number of sentences
that would be false if you sent them to someone else.** A reader who has seen two emails from
the same sequence recognises the slot the moment the noun changes, and everything after it
reads as automation.

The evidence is the author's own client work. One agency audited the live cold copy of 12
companies, its own included. In one sequence, three rendered emails opened "Your commitment to
enhancing nursing education at [college] caught my attention", "Your work as a [title] at
[company] is impressive", "Your long-time work as a [title] caught my attention": the same line
with different nouns swapped, which the audit called empty personalisation. Nine of the 12
ended on a permission ask ("Open to learning more?", "Worth a quick chat?"). One sequence
shipped with its brackets still in: "[Similar Company], a [industry] org with a similar setup to
[New Company]". Against all of that, the one email in the audit known to have closed a deal
carried nine checkable specifics: a calendar fact ("it's already May"), a named result with a
number (28 contractors placed in under two weeks), a delivery mechanic (a shortlist in 5
business days), and a risk reversal. The template that replaced it carried none, and a list of
four logos in the PS. On a later account-based engagement, the sentence-level swap test was
the gate that made the copy pass the client's review after the first drafts had flattened into
clean, generic emails that could have gone to any account.

What follows from it: the unit of personalisation is the sentence. Each one is labelled, the
slot share is counted against a line fixed before reading, and the rewrite is only allowed to
spend facts that carry a source. Two prospects' rewrites are compared, because a sentence that
came out the same for both was never about either.

**It reads, labels and rewrites; it sends nothing.** It spends no credits, changes nothing in
Deepline or any CRM, and writes into no sequencer. The rewrite is a file the installer takes to their sending
tool.

**It needs facts to spend, and the facts are the lead data you already have.** Anyone running
outbound has scraped the company and the person; those columns are the source. The one question
the rewrite asks of every prospect fact is: can this be confirmed from the lead's row? If it
can, the column is cited. If it cannot, and no note with a URL backs it, the sentence is cut,
never filled. Without lead data or a sender proof list it can still label and score, and it will
say so, but the rewrite stops at deletion.

Do not start a step before the steps above it have their answers. If a declared input is
missing, ask for it. Never assume a default and continue.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's. Ask for it, and where a default
is named below, using it means saying so in the output.

| Input | What it is | If absent |
|---|---|---|
| **The email** | one email as sent or drafted, or a batch: the same touch rendered for several prospects. Subject line included | stop. Nothing to test |
| **Lead data** | the prospect's row in whatever holds the list: a Deepline play run or Customer DB table, a CSV export, a database export, a sheet. Every filled enrichment column on that row is a fact (recent hire, funding, job openings, tech stack, headcount, a line scraped from their site), cited by column name and row. Research notes with a URL count too. A value in no column and no note is not a fact | label and score still run; the rewrite can spend no prospect facts, and in account mode the verdict cannot pass |
| **Sender proof and mechanics** | the sender's checkable claims: results with a number, named clients with permission, delivery mechanics (days, steps), guarantees; each with a source and an id | the rewrite can spend no sender facts; any sender claim in the email is unsourced |
| **Mode** | `account`: the email is meant for this one prospect, so zero prospect facts fails; `segment`: the email is meant for a segment, so prospect facts are optional and sender facts carry it | ask. Never inferred from the email |
| **Slot line** | the share of slot sentences above which the email fails | the author's lines: 30% in account mode (the agency's own account-based copy rule) and 50% in segment mode (calibrated on the audit: the one email known to have closed a deal sat at 40%, the templates at 75% to 100%); say so |
| **Banned asks and openers** | phrasings counted as slot on sight | the author's lists below, borrowed; the installer may add, never remove without saying so |
| **Prospect list for the batch check** | which prospects the batch covers, and each one's name, company and industry, so those words can be masked before comparing | a single email skips the batch check; a batch without the list cannot be masked and the check is reported as not run |

The author's lists, counted as slot on sight and said to be borrowed:

- **Asks:** "Open to learning more?", "Worth a quick look?", "Worth a chat?", "Worth a quick
  chat?", "Mind if I send...", "Would that be helpful?", "Interested in hearing more?",
  "Interested in learning more?", "Would you like to learn more?", "Open to it?", "Open to
  seeing...", "Can I tell you on a call...", "Worth exploring...", "Worth a conversation?",
  "Worth taking a look...", "Want to see how...", "Happy to walk through...", "15 minutes?"
- **Openers:** "Let me get straight to the point", "You seemed like the right person", "Congrats
  on [anything the sender did not verify]", "Dear [company] team", "Hope this finds you well", "I
  wanted to reach out", "Quick question for you", "Quick one", "Thanks for connecting"
- **Hedges that stand where a number should be:** "a lot of", "a number of", "many", "several",
  "some of the", "leading", "trusted by". A hedge in a sentence that also carries a number is
  not counted; the number is what the hedge was standing in for
- **Noun-swap frames:** "Your [work | commitment | role] at/as [x] [caught my attention | is
  impressive | stood out]", "[Industry] is one of the main areas we [work in | focus on]", "We
  help [title] [do outcome]" with nothing checkable after it
- **Decoration:** a list of client names with no outcome attached to any of them

## What this skill touches

- **Reads** - the email or batch, the lead rows, the sender proof list. Files are read only. A
  Deepline play run is read through `deepline runs export <run-id> --out leads.csv`, and a Customer
  DB table through `deepline db query --sql 'select * from "storage"."<table>" limit 20' --json`;
  neither is written to. A database or sheet export is read as a file.
- **Writes** - two files in your working directory: the rewritten email (or batch), and the
  sentence table with labels, fact ids and the density line. Nothing else.
- **Never** - invents a fact, a number, a client name, a date or an event; spends a fact that has
  no source; spends the same fact twice in one email; changes a number, unit or timeframe from
  its source row; keeps a slot sentence in a rewrite without saying which fact would replace it;
  writes into a sequencer or a campaign; runs an enrichment; spends a credit; sends an email.
- **Halts** - Step 3 `sample-review`, Step 5 `sample-review`.

## Step 0 - Check the platform works, and say where the work runs

Confirm the email and any lead data or proof files open. If the lead data or proof list lives in
Deepline (a play run or a Customer DB table), run `deepline preflight --json` and name the org once.
If it reports the CLI out of date, name the one command that fixes it, `deepline update`. An auth
failure means the lead data has to be exported to a file instead. Do not install, upgrade or fetch
anything yourself.

Then tell the installer, in one sentence: this skill reads the email and the facts and does the
labelling and rewriting in the agent; it runs no enrichment, spends no credits, and changes
nothing outside two files in the working directory.

## Step 1 - Collect the inputs before reading a sentence (interview; do not guess)

Collect, in this order: the email or batch; the mode; the lead data (which table, file or export holds
the rows, and which columns are enrichment); the sender proof and mechanics; the slot line; the banned lists, with any additions; the prospect
list for the batch check. Write them into the table header before Step 2 runs. The line and the
lists are fixed here; a line chosen after seeing the score is a justification, not a rule.

## Step 2 - Split into sentences and mark the exempt ones

Split the body on sentence ends. Treat the subject line as a sentence. A bullet or a one-line
paragraph is a sentence. Number them. Mark as **exempt**, and leave out of every count: the
greeting ("Hi Jennifer,"), the sign-off and signature block, and a plain opt-out line ("If this
isn't relevant, let me know"). An opt-out line that carries a pitch or a logo list is not
exempt. Show the numbered split; two installers must get the same count from the same email.

## Step 3 - Label every sentence, then show the table (halt)

Each non-exempt sentence gets exactly one label, decided in this order:

1. **Slot, on sight.** It contains an unresolved placeholder (`{...}`, `[...]`, `<...>`), a
   banned ask, a banned opener, a hedge standing where a number should be, a noun-swap frame,
   or a decoration list. Record which signature fired.
2. **Fact, prospect.** It states something checkable about this prospect that would be false for
   another: their event, hire, filing, product, stack, location, calendar, a line from their own
   site. It must be confirmable from the lead's row (record the column) or from a note with a
   URL (record the id). A prospect-shaped sentence that matches no column and no note is
   **unsourced**.
3. **Fact, sender.** It states something checkable about the sender's work: a result with a
   number, a named client with an outcome, a mechanic with a timeframe, a guarantee. It must
   trace to a proof or mechanics row; record the id. A sender-shaped sentence with no row behind
   it is **unsourced**.
4. **Slot, by the question.** For everything left, ask the one question: *if the prospect's name,
   company and industry were swapped for another prospect's, would this sentence still be true
   and still read the same?* Yes is slot. No is a fact, and it must then trace to a row like any
   other fact; if it cannot, it is unsourced.

**Unsourced counts as slot for the score, and is flagged on its own line**, because a sentence
that looks like a fact and has no source is either template wearing a number or an invention,
and both are worse than a plain slot. Fact-shaped means: it carries a number, a date, a month or
a year, or the agent judged it a fact at rule 4. A vague claim with no number in it ("results
within weeks") is not fact-shaped; it is slot by the question.

Show the table: number, sentence, label, signature or fact id, and the density line: slot
sentences over counted sentences, with the line beside it. Ask the installer to confirm or
correct labels. A correction that turns a slot into a fact needs the fact's row; if the row does
not exist, the label stands. This is the first `sample-review` halt.

## Step 4 - Verdict, single-valued, first match wins

1. **Unsourced claims present** - fail. A number nobody can back is cut before anything else is
   judged. Name them.
2. **Slot share above the line for the mode** - fail. Say the count and the line.
3. **Account mode with zero prospect facts** - fail. The email is segment copy with a
   personalised opener, and the installer said it was meant to be about this prospect.
4. **Pass** - everything else. Report the density anyway; a pass within five points of the
   line is a near miss and is said to be one.

## Step 5 - Rewrite from sourced facts, then show it (halt)

Rewrite only what failed, in this order, and stop when the email passes:

1. **Unsourced claims:** cut, or replace with the sourced row that says the true version. Never
   soften a number to keep it; a number with no row is gone.
2. **The opener, if slot:** replace with one prospect fact in account mode, or one sender fact
   with a number in segment mode. The fact is stated plainly, as a thing that is so, never as
   praise ("caught my attention") and never as a diagnosis of the prospect ("your data is
   scattered"); their situation is framed as a category guess, their facts as facts.
3. **Each remaining slot sentence, in order:** replace with a sentence that spends one unused fact
   (prospect facts first in account mode), or delete it. A fact is spent once per email. When the
   facts run out, the remaining slot sentences are deleted, and the sentence table says
   "deleted: no sourced fact left to spend".
4. **The ask, if banned:** replace with a concrete deliverable the prospect can accept in one word
   ("Want the two-page version? Reply yes") or a time-bounded ask with a specific thing in it.
   The deliverable must be something the installer confirmed they have.
5. **Decoration lists:** replace the list with one client and one outcome from a proof row with
   `named` permission, or cut the list.

Every rewritten sentence carries the id of the fact it spent, and every number in the rewrite
must appear, unchanged, in the row it cites. Re-run Steps 2 to 4 on the rewrite. Show the
before-and-after table and the new density line. Ask the installer to read the rewrite as the
prospect would. If a rewritten sentence reads wrong, the fix is a different fact or a deletion,
never an unsourced improvement. This is the second `sample-review` halt.

## Step 6 - The batch check, when there are several prospects

Mask each prospect's name, company and industry words in every rewritten sentence, then compare
sentences across prospects. Any sentence that is identical for two or more prospects after
masking is **template by construction**: relabel it slot in every email it appears in, re-score
each email, and return the failing ones to Step 5 with the instruction to spend a different
fact. Report how many sentences the check caught and in how many emails.

Also report the share of the batch that shares an opener frame (the first sentence after
masking), since an opener that repeats across the batch is the slot readers see first.

## Step 7 - Deliver

Write two files to the working directory and show the rewrite:

- `swap-test-<YYYY-MM-DD>.md`: the header (mode, line, lists with additions, facts supplied per
  prospect and for the sender), the verdict, the density line before and after, the sentence
  table with labels and fact ids, the batch check result, and the coverage line: sentences
  counted, exempt, slot before, slot after, facts spent, facts unspent, unsourced claims cut.
- `swap-test-<YYYY-MM-DD>-rewrite.md`: the rewritten email, or one per prospect.

Lead with the verdict and the two density lines. The rewrite is a draft for a person to send;
nothing has been sent, scheduled or written into a sequencer.

## Representative output

### Verdict

**Fail, then pass after rewrite.** Before: 6 of 6 counted sentences swappable (100%, line
30%), 1 of them unsourced. After: 0 of 6 swappable; 6 facts spent (2 prospect, 4 sender); 0
unsourced; 2 prospect facts unspent.

### Sentence table

| # | Before | Label | Why | After | Fact |
|---|---|---|---|---|---|
| 1 | Hey Dana - we help EdTech companies hire sales talent with district relationships. | slot | noun-swap frame: "We help [title] [outcome]" | Contoso posted two district-sales openings in March, both asking for K-12 procurement experience. | B-2 (careers page, 2026-03-14) |
| 2 | EdTech is the only space we recruit for. | slot | by the question: true for any prospect | Contoso's 2026 roadmap names Texas and Florida as the two expansion states. | B-4 (investor update, 2026-02) |
| 3 | We've placed a lot of people in this space. | slot | hedge where a number should be | Fabrikam Talent placed 28 contractors at a K-12 vendor in under two weeks. | S-1 (case study, named) |
| 4 | Our clients see results within 3 weeks. | unsourced | no proof row carries "3 weeks" | (cut) | |
| 5 | Open to learning more? | slot | banned ask | Want the two-page version with the district-procurement screen we use? Reply yes. | S-3 (deliverable confirmed) |
| 6 | PS A few companies we've worked with: Alpha, Beta, Gamma, Delta. | slot | decoration list | PS The shortlist arrives in 5 business days. | S-2 (mechanics) |
| 6b | (from the same PS) | | | If a hire is not K-12-fluent in week one, we replace them at no cost. | S-4 (guarantee) |

### Batch check (12 prospects)

2 sentences came out identical for 5 prospects after masking ("Your roadmap names two
expansion states") and were relabelled slot; 5 emails returned to Step 5 and spent a different
lead data column. Opener frame shared across the batch after masking: 0 of 12.

### Coverage line

6 sentences counted · 2 exempt · slot before 6 · slot after 0 · facts spent 6 · facts unspent 2
· unsourced claims cut 1.

## What this skill does not claim

- It checks facts against the lead data, not against the world. A wrong value in a column
  produces a confident wrong sentence; the data's quality is the list's quality.
- The on-sight lists are a floor. A slot sentence that matches no list is caught only by the
  question at label rule 4, which is the agent's judgement, shown in the table for the installer
  to overrule.
- It does not know whether the rewrite reads well. It knows the rewrite is made of sourced facts
  and is not template. Tone is the installer's at the Step 5 halt.
- It has no reply-rate evidence that a lower slot share earns more replies. The evidence is that
  the highest-slot emails in a 12-company audit were the ones the auditor could identify as
  sequences on sight, and the one email in that audit known to have closed a deal was the one
  with the most checkable specifics.
- The lines are one agency's, and the on-sight lists were fitted to that agency's audit. On the
  seven audited emails the lists were built from, the rules reproduce the author's reading of the
  auditor's calls on every counted sentence, which is what fitting means, not proof. There is no
  second labeller and no reply data. A team can set other lines; the skill records the line it
  ran with.

## What good looks like

A good run shows a table anyone can argue with: every slot has the signature or the question
beside it, every fact has an id, and every number in the rewrite can be found in a row. The
rewrite is shorter than the original more often than not, because slot sentences with no fact
to replace them are deleted, not dressed up. On a batch, the check catches something; twelve
rewrites that share no sentence after masking is a claim to be suspicious of.

A thin run looks like a rewrite longer than the original, a number in the rewrite that appears
in no row, a "fact" whose id points to a row that says something slightly different, an opener
that praises the prospect, a pass in account mode with zero prospect facts, or a batch check
reported as clean without the masked comparison having been shown.

## Rules

- The line and the lists are fixed at Step 1. Never adjust them after seeing the score in the
  same run.
- One label per sentence, in the declared order. Unsourced counts as slot and is named.
- Never invent a fact, a number, a client, a date or an event. Never soften a number to keep it.
- A fact is spent once per email. A number in the rewrite is copied from its row, unit and
  timeframe included.
- Slot sentences with no fact to replace them are deleted, never rephrased into better template.
- A prospect fact is stated, never praised, and never turned into a diagnosis of the prospect.
- Every rewritten sentence carries the id it spent.
- A sentence identical across two prospects after masking is slot, whatever it says.
- Nothing is sent, scheduled or written into a sequencer or a CRM.

## Worked example

Fabrikam Talent sends the email in the representative output to Dana at Contoso, an education
software company, in account mode. The lead's row has four filled enrichment columns: two district-sales
job openings dated March, an investor update naming two expansion states, a product launch in
February, and the CEO's line about "procurement cycles" from a podcast. The proof list has a
named K-12 placement result, a delivery mechanic, a replacement guarantee, and a confirmed
two-page deliverable.

Step 2 splits six counted sentences and exempts the signature and the opt-out half of the PS.
Step 3 labels four slot on sight (a noun-swap opener behind an inline greeting, a hedge, a
banned ask, a decoration list), one slot by the question ("the only space we recruit for"),
and one unsourced ("results within 3 weeks": no row carries it). Density 6 of 6. Step 4 fails
on the unsourced claim first, then on the share.

Step 5 cuts the unsourced line, opens on the March job openings, spends the expansion states,
the named placement, the mechanic and the guarantee, and replaces the ask with the confirmed
deliverable. Density after: 0 of 6; nothing was kept without a fact behind it. Run across twelve
prospects, Step 6 finds the
expansion-states sentence identical for five of them, since five rows carried the same
investor-update boilerplate; those five spend the podcast line instead. The installer reads the
Contoso rewrite as Dana would, changes one word of tone, and takes the file to their sending
tool. Nothing was sent.
