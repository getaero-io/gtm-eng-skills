---
name: specificity-rewrite
description: |
  Write the one sentence that makes a generic offer feel written for this company rather than for
  five thousand people. Produces the tail of "I think we can help you ___" as a short lowercase
  clause anchored to something the company actually sells, and leaves it blank when the company does
  not fit. Use whenever someone asks: make it feel specific to them, write the specificity line, why
  would they think this is for them, or personalize the offer and not just the intro. Do NOT use it
  to write a whole email, to find a signal about the company — funding, hiring, tech and pricing are
  separate skills — or to promise anything the sender does not actually do. It writes its own output
  columns and sends nothing.
category: personalize-outbound
personas: [gtm-engineer, sales-development]
mechanism: logic-only
touches: writes-records
keywords: [cold-email]
ported_from: clay-run/clay-skill-creator/skills/eric-nowoslawski/specificity-rewrite
---

# Specificity rewrite (judge a batch, never a row)

**The insight: the intro is not what makes an email feel generic — the offer is.** Everyone
personalizes the first line and then pitches the same thing in the same words to everyone. This
writes the half nobody personalizes: the tail of *"I think we can help you ___"*, anchored to a
real thing this company sells, phrased in this company's own nouns.

**And the rule that comes out of measuring it is the one to internalise.** The same script run twice
on the same ten domains scored 8/10 both times — but **the failing rows were different**. One run had
a grammar break the guard could not see; on the re-run that row was fine and a different row went
awkward. That is real non-determinism, and it means **you judge a batch, never a row.** A single bad
line is not a broken prompt, and a single good one is not a working one.

**One boundary makes this safe:** the model may only ever promise something on the client's own
capability list. Without that list it borrows adjacent promises — growth, demand, customers — that
the sender cannot deliver.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The rows** | a CSV (or a Deepline Customer DB table) with `domain` and `company_name` | no default |
| **A description of what each company sells** | one honest paragraph per company, from their company data or their site | **this is the whole input.** With no description the row blanks — correctly. See Step 2 for why "just fetch the homepage" fails on exactly the lists this works best on |
| **The sender's capability list** | a fixed block of short lines naming what they actually do, **plus a "we do NOT do" line** | **ask, and lock it once per client, not per row.** This is the part people forget and it is the whole safety mechanism: the model may only promise something on this list. The "do NOT" line is what stops it borrowing adjacent promises |
| **Their offerings or revenue streams** | extra columns if they have them | not required; they sharpen the anchor |
| **The frame in the email copy** | the exact sentence the clause slots into | default `I think we can help you {{line}}.` **If they change the frame, it changes in the copy AND in the prompt's context sentence together, and the batch gets re-graded** — the verdict was measured against one specific frame |
| **What happens to blank rows** | route them to a campaign whose copy does not need the line, or exclude them | **default: route them out of this campaign.** See Step 5 — this is also what lets them measure whether the line earns its keep |
| **Which model writes the clause** | the `model` passed to `deeplineagent` | use a **mini-class** model with `providerOptions` reasoning effort set explicitly. Measured: a reasoning model with its effort level left unset cost **19× the estimate** for no quality gain |
| **A rendering fallback, and its cap** | whether they will pay for rendered page text when a plain fetch returns nothing, and the row cap | ask. Without it, thin-website rows simply blank, which is an acceptable outcome |

## What this skill touches

- **Reads** — the company name, domain and description on each row, plus the sender's capability
  block. Optionally fetches a company's public homepage when no description exists.
- **Writes** — one sendable clause, plus three QA-only columns (the anchor, the offer item it mapped
  to, and a reading-level score) on the rows you point it at.
- **Never** — promises anything absent from the capability list, names the company inside the
  clause, drafts a whole email, sends anything, enrols anyone, or writes to a CRM.
- **Halts** — Step 1 other, Step 4 sample-review.
- **Derived from** — the author's 10-domain graded run, repeated twice on the same domains, plus a
  measured four-brand fetch probe and a reading-level measurement across eight filled tails. The
  graded path is a script calling a model API; see the claims section.

## Declared outputs

| Field | Type | Example | Sent? |
|---|---|---|---|
| `specificity_line` | 6–14 words, ≤90 chars, lowercase, no trailing period | `know the landed cost of every pool float before you price it` | **yes** — blank is a real answer |
| `specificity_anchor` | the concrete thing it anchored to | `pool float` | **no — QA only** |
| `specificity_offer_item` | the capability it mapped to | `inventory and cost-of-goods tracking per product` | **no — QA only** |
| `grade_line` | reading level of the tail | `4.9` | **no — QA only** |

The last three exist so the guard can check the line mechanically and an operator can see *why* a
line came out as it did. **They are never sent to anyone.**

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json` (missing CLI: `npm install -g deepline && deepline auth register
--wait auto`) and confirm the input CSV exists (`deepline csv show --csv <path> --summary`). Name it,
then say what this run touches: *"this adds one sendable column and three QA columns to <the file you
named>, and sends nothing."* If the check fails, name it and stop.

The per-row work runs as a Deepline play: evidence columns (Step 2), one `deeplineagent` column with
a `jsonSchema` for the four output fields and `maxToolCalls: 0`, then a `run_javascript` column for
the mechanical gates in Step 3. Pilot on 10 rows with `--debug` before the full file.

## Step 1 — Lock the capability block before writing a single line

Collect the sender's capability list as short lines, and **make them add the "we do NOT do" line.**
Without it the model reaches for adjacent promises, because "we help with inventory costing" sits
next to "we help you grow" in latent space and only the sender knows which one is a lie.

**Halt here (`other`).** Read the block back and confirm it. This is locked once per client and then
reused on every row, so an error here is an error on every row.

## Step 2 — Get one honest paragraph per company

In order, stopping as soon as you have enough text:

1. **The company description already in their data.** Measured: present on **9 of 10** domains, and
   rich enough to write from on **8 of those 9**. Free.
2. **A plain homepage fetch** — meta description plus the first 1,500 characters
   (`contextdev_get_web_scrape_markdown`, free; the figures below were measured on a raw HTTP fetch,
   not this tool, so read its output length on the pilot rows before trusting either number). **Measured 1 out of
   4 on ecommerce domains: one returned 0 bytes, one 16 bytes, one 1 byte, and one refused the
   connection.**
3. **A rendering fallback, capped**, only when step 2 returned under about 400 characters and the
   run's explicit row cap has budget (`firecrawl_scrape`, `formats: ["markdown"]`,
   `onlyMainContent: true`; 0.02 Deepline credits per page per `deepline tools describe`). Verified once at 7,805 characters of clean text in 8.3
   seconds, after a plain fetch returned nothing.

**Internalise step 2's numbers.** Modern ecommerce sites frequently return nothing to a plain fetch.
If your evidence source is "just fetch the homepage", you will silently write from nothing on exactly
the list types this skill is best at. **Writing from nothing is worse than blanking.**

## Step 3 — Write the clause, then gate it mechanically

The model picks one concrete anchor from the description, maps it to one item on the capability list,
and writes the tail in **this company's nouns**.

Rules the prompt enforces:

1. **Start with a plain verb** — track, see, know, build, cut. Lowercase, no trailing period.
2. 6 to 14 words. One idea. No em dashes.
3. **Never contain the company name, the words "help you", or the word "specifically".** All three
   are already in the frame, and repeating them is the tell.
4. **Never promise sales, growth, demand or customers** unless the capability list says the sender
   does that.
5. **The anchor must be a concrete thing the company sells**, not a business abstraction. "Improve
   efficiency" and "your products" mean the model failed to find an anchor — send it back rather than
   shipping them.
6. **Say the capability in the company's words, not the capability list's words.** Copying the list's
   phrasing is how every row ends up sounding the same.
7. If there is no honest anchor, return blank.

### The reading-level gate goes on the tail, not the rendered sentence

Enforce grade 7 on the **generated tail**. Above it, one simplify rewrite; still above, the row
blanks. Measured: eight filled tails scored 2.5 to 5.9 and none needed the rewrite.

**This is measured, not assumed.** The frame `Specifically, I think we can help you.` **scores 5.7
entirely on its own** — "Specifically" is five syllables inside a seven-word stem. Add any 6-to-14
word tail and the full sentence lands at **7.0 to 9.8 no matter how plain the tail is.** A tail of
grade 2.5 still renders at 7.0.

**So gating the render would blank every row for a property of the house copy, not of the data.**

The clean fix is a copy change, not a data change: **dropping the word "Specifically" takes the worst
sampled render from grade 9.1 to 6.3**, under the bar, with no change to the generated tail. Do that,
and keep gating the tail anyway — it is the half you generate.

## Step 4 — Read a batch, not a row

**Halt here (`sample-review`).** Show 10 rendered sentences — frame plus tail — beside the anchor and
the capability each mapped to. Read them as a set.

**Judge the batch.** Two runs give different lines for the same row; that is measured. A single
awkward line in ten is inside the grade. A batch where the anchors are business abstractions, or
where every line reuses the capability list's phrasing, is a prompt problem.

## Step 5 — Handle the blanks, and never with spintax

**A row missing this campaign's personalization signal should generally not be in this campaign.**
Build the list so the line lands, and route the blanks to a campaign whose copy does not need one.
That is also the only way to measure whether the line earns its keep.

Where a genuinely optional clause blanks on a small share of rows, **pre-render the whole sentence** —
frame, clause, trailing period and space — into **one** field, so the body carries a single merge
field that renders as nothing when empty.

**Spintax is banned as the blank-handling mechanism.** It picks a variant at random and cannot branch
on whether a variable is empty, so it will render `I think we can help you .` on blank rows and throw
the personalization away on populated ones.

**And a blank rate is a targeting signal.** Expect **10 to 20% blanks** on a normal ecommerce or SMB
list, higher on lists full of tiny companies with thin sites. **Over 30% in a segment means the list
is wrong for this campaign, not that the prompt is wrong.** Re-target or route those rows elsewhere.

## Step 6 — Deliver

Report the filled rate with its denominator, the blank rate by reason (no description, no honest
anchor, failed the reading gate), and the rows where the anchor is an abstraction rather than a
thing. Name the field the copy should reference.

## Representative output

Invented examples for shape only; no real company appears. Capability list used:
*inventory and cost-of-goods tracking per product · landed-cost calculation · supplier lead-time
reporting · we do NOT do demand generation, ads, or sales hiring.*

### The clause, row by row

| company | `specificity_anchor` | `specificity_line` | `grade_line` | rendered |
|---|---|---|---|---|
| Northstar Pool Supply | `pool float` | `know the landed cost of every pool float before you price it` | 4.9 | *I think we can help you know the landed cost of every pool float before you price it.* |
| Vantage Coffee Roasters | `single-origin bag` | `see which single-origin bags actually make money after freight` | 5.4 | *…see which single-origin bags actually make money after freight.* |
| Meridian Hardware | `supplier lead time` | `track supplier lead times without chasing three inboxes` | 3.8 | *…track supplier lead times without chasing three inboxes.* |
| Harborline Textiles | `` | `` | — | blank — description was one line of boilerplate, no honest anchor |
| Pinegrove Studio | `` | `` | — | blank — homepage returned 1 byte, no description in their data |

### The run summary

```
10 rows
   8 filled     <- 8/10, and 8/10 again on a re-run of the same domains
   2 blank      1 no description anywhere, 1 no honest anchor

  blank rate 20%  (expected band is 10-20% on ecommerce/SMB)

reading level, generated tails: 2.5 to 5.9   0 needed a simplify rewrite
  note: the RENDERED sentences score 7.0-9.8 because the frame alone is 5.7.
        gated the tail, as designed. not one row blanked on the gate.

anchors that were business abstractions: 0
lines reusing the capability list's own wording: 0

blank rows routed to: <the campaign the installer named>
copy should reference: the pre-rendered single field
```

## What this skill does not claim

- **8 of 10 usable, twice, on the same ten domains — and the failing rows moved between runs.** One
  run had a grammar break the guard could not see; on the re-run that row was clean and a different
  row went awkward. That is real non-determinism, measured. **Judge a batch, never a row**, and do
  not conclude anything from a single line in either direction.
- **The verdict was measured against one specific frame.** If you change the frame, change it in the
  copy and in the prompt's context sentence together, and re-grade on the same domains. The
  reading-level arithmetic in particular depends on the frame's own score.
- **The reading-level numbers are the tail's, not the sentence's.** Eight filled tails scored 2.5 to
  5.9. The rendered sentences score 7.0 to 9.8 regardless, because the frame contributes 5.7 on its
  own. Anyone quoting a grade for this skill has to say which of the two they mean.
- **The two failures had different causes and only one is fixable.** A company with no description in
  any source cannot be written about; that is a correct blank, not a miss to engineer away.
- **The blank rate is a property of the list, not of the prompt.** 10 to 20% is normal. Over 30%
  means the segment is wrong for this campaign.
- **The verdict covers a script path** calling a model API. **The Deepline play build has never been
  run** — and one cost note is measured, on Clay's AI column rather than Deepline: a reasoning model
  with its effort level unset cost **19× the estimate**. Use a mini-class model and set the effort.
- **The source chain's fetch numbers are small and brutal: 1 of 4 on ecommerce domains**, with
  responses of 0 bytes, 16 bytes, 1 byte and a refused connection. Four brands is not a survey, but
  it is enough to stop anyone building on a plain homepage fetch alone.
- **It cannot tell whether the sentence is true of the sender's business** beyond checking it against
  the capability list they supplied. A wrong capability list produces confident wrong promises on
  every row.
- **No reply, meeting or conversion rate is claimed**, and no benchmark for one exists here. This
  writes one clause.

## What good looks like

- The capability list has a "we do NOT do" line in it, and someone read the list back before the run.
- The blank rate sits in the 10–20% band, and nobody tried to engineer it to zero.
- Every anchor is a thing the company sells — a pool float, a single-origin bag — not "efficiency"
  or "your products".
- No two lines in a batch reuse the capability list's own phrasing.
- No clause contains the company name, "help you", or "specifically".
- Nobody gated the rendered sentence, so nobody blanked a whole list over a property of the frame.
- No email body uses spintax to handle the blanks; either the row was routed out or the whole
  sentence is pre-rendered into one field.
- A batch was judged as a set, and nobody re-ran the prompt because of one awkward line.

## Rules

1. **The model may only promise something on the sender's capability list**, and that list needs a
   "we do NOT do" line.
2. **The frame lives in the copy, never inside the variable.**
3. **Gate the tail's reading level, not the rendered sentence's.** The frame alone scores 5.7.
4. **Judge a batch, never a row.** Two runs give different lines for the same row.
5. **Spintax is never the blank-handling mechanism.** Route the row out, or pre-render the whole
   sentence into one field.
6. **A blank is a real answer**, and over 30% blanks in a segment means the list is wrong.
7. **The anchor must be a concrete thing the company sells.** Business abstractions are a failure to
   find an anchor, not a line.
8. **Say the capability in the company's nouns, not the list's.**
9. **Never write from nothing.** If the description is empty and the fetch returned nothing, blank the
   row — a plain homepage fetch fails on most ecommerce sites.
10. **Never send the QA fields.** The anchor, the mapped capability and the grade are for operators.
11. **Use a mini-class model.** A reasoning model with the effort unset cost 19× for no gain.
12. **If you change the frame, change it in both places and re-grade.**
13. **This skill writes its own columns and sends nothing.**
