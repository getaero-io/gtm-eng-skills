---
name: campaign-angle-finder
description: |
  Build the three-bullet "I had a few ideas for you" email, where the sender names what each bullet
  slot is about up front and the model only fills that slot with a detail true of this company. It
  never picks a subject, never adds a fourth bullet, and never proposes something the sender cannot
  build. Emits three bullets, the evidence quote behind each, and a rendered block. Use whenever
  someone asks: creative ideas campaign, three ideas email, I had a few ideas for you, 3 bullets,
  use cases for their business, or what could they build with us. Do NOT use it when one
  personalized sentence tops an otherwise fixed email, when the hook is an event, or when the sender
  cannot name three slots — that last case means this is the wrong play, not a gap to fill in. It
  writes its own output columns and sends nothing.
category: personalize-outbound
personas: [gtm-engineer, founder]
mechanism: logic-only
touches: writes-records
keywords: [cold-email]
ported_from: clay-run/clay-skill-creator/skills/eric-nowoslawski/campaign-angle-finder
---

# Campaign angle finder (slot discipline is the whole idea)

**One measurement is the entire skill, and everything else is plumbing:**

| Approach | Usable |
|---|---|
| Free-form — *"have three ideas about this company"* | **2/5** |
| Slot-defined — the sender names what each bullet is about | **21/23 (91%)** |

**So the sender names what bullets 1, 2 and 3 are about, in their own words, and those slots stay
fixed for every lead.** The model's only job is to fill a slot with a detail that is true of this
company. It never picks a subject, never adds a fourth, and never writes an idea the sender cannot
deliver on the call that follows.

**If the sender cannot name three slots, this is the wrong play for the campaign.** Do not fill the
gap yourself. An idea the sender did not ask for is an idea they cannot deliver when someone replies
asking about it.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The rows** | a CSV (or a Deepline Customer DB table) with `company_name` and `domain` | no default |
| **What bullet 1, 2 and 3 are each about** | three subjects, **in the sender's own words**, naming things they build, sell or run | **no default, and do not invent one.** If they cannot name three, say this is the wrong play and stop. This is the input the 91% depends on |
| **What specific detail must appear per slot** | for each slot, what about the prospect has to show up in the bullet | ask. Without it the bullets are about the sender, not the prospect |
| **What must never appear** | competitors, dollar figures, headcounts, named customers, anything they do not actually do | ask explicitly. The model borrows adjacent promises without a stated prohibition |
| **Three hand-written bullet sets** | the sender's own complete bullets for three real companies | **ask, and do not accept model-drafted ones** — see the gate in Step 1. This is the input people try hardest to skip |
| **The evidence source** | where the paragraph describing each company comes from | ask. Order and the short-not-empty gate are in Step 2. A row still thin after every rung abstains |
| **The client name for field namespacing** | a short suffix for the pushed field names | **ask.** Near-duplicate custom-field names coexist silently on the same lead record, which is a very quiet way to send the last client's bullets |
| **Where excluded rows go** | the non-ideas campaign rows route to | ask. Any empty bullet excludes the row, so without a destination those rows vanish |
| **Which model fills the slots** | the `model` passed to `deeplineagent` | **use a mini-class model with reasoning effort set to its lowest value** — see Step 3, where a nano model with reasoning unset was measured at **19× the cost** |

## What this skill touches

- **Reads** — the company name, domain and evidence paragraph on each row, plus the sender's slot
  definitions and hand-written examples.
- **Writes** — three bullet columns, three evidence-quote columns and one rendered block, on the rows
  you point it at, under client-namespaced field names.
- **Never** — picks what a bullet is about, adds a fourth bullet, spins a bullet, names a competitor,
  a dollar figure, a headcount or a customer, drafts a whole email, sends anything, enrols anyone, or
  writes to a CRM.
- **Halts** — Step 1 other, Step 4 sample-review.
- **Derived from** — the author's graded script run, plus **27 of 32 real production rows graded
  across seven live campaigns** — out-of-sample, at volume, across different senders. See the claims
  section for what that covers.

## Declared outputs

| Field | Type | Null? |
|---|---|---|
| `creative_idea_1` / `_2` / `_3` | string, 140 chars each | no — **`""`** |
| `evidence_1` / `_2` / `_3` | the quote from the input the bullet was built on | no — `""` |
| `creative_ideas_block` | the three bullets rendered for the email body | no — `""` |

**Abstain is the empty string.** Never a sentinel, never the text `null`.

**Any empty bullet excludes the row** into a separate non-ideas campaign. This is not fussiness: a
sequencer cannot pin a lead to a specific variant, and **a three-bullet email with two bullets is not
a degraded version of this campaign — it is a different email.**

**Namespace the pushed fields per client** (`creative_idea_1_<client>`). The JSON keys stay the same;
the suffix goes on the field that gets pushed.

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json` (missing CLI: `npm install -g deepline && deepline auth register
--wait auto`) and confirm the input CSV exists (`deepline csv show --csv <path> --summary`). Name it,
then say what this run touches: *"this adds seven columns to <the file you named> under
client-namespaced names, and sends nothing."* If the check fails, name it and stop.

The per-row work runs as a Deepline play: one `.withColumn` per evidence rung, then one
`deeplineagent` column for the slot fill, then a `run_javascript` column for the quote verifier and
lint. Pilot on 3 rows with `deepline plays run <file>.play.ts --input '{"csv":"pilot.csv"}' --debug`
before the full file.

## Step 1 — Interview the sender, then make them write three sets by hand

Six questions, in this order:

1. **What is bullet 1 about?** The one thing they build, sell or run that goes in slot 1 — in their
   words, not yours.
2. What is bullet 2 about?
3. What is bullet 3 about?
4. **For each slot, what specific detail about the prospect has to appear?**
5. **What must never appear?**
6. **Now hand-write three complete bullet sets for three real companies.**

### The gate: the sender writes the examples, never the model

**AI never drafts the exemplars it is graded against.** If the model writes the examples, they encode
the model's instincts rather than the sender's offer, and every grading round afterwards measures the
model against itself.

This is not hypothetical — it is the same contamination that forced a verdict to be withdrawn
elsewhere in this family of skills, where a few-shot block turned out to contain the answers to the
rows being graded. **A prompt whose examples contain the answers is not a prompt, it is an answer
key.**

**Halt here (`other`).** Read the three slots and the three hand-written sets back, and confirm them.
Everything downstream is measured against these.

## Step 2 — Get the evidence, and gate on short, not empty

Work the rungs in order, stopping when you have a real paragraph: the company description already in
their data, then a free company-enrichment source, then any client-owned table, then a company search
(`exa_search`), then a rendering fallback (`firecrawl_scrape` on the homepage). **A row still thin
after all of that abstains.**

**Gate each rung on the evidence being SHORT — under about 200 characters — not on it being empty.**
A two-sentence boilerplate description is technically non-empty and produces three generic bullets
that read like a mail merge. **Emptiness is the wrong test**, and it is the commonest reason every
bullet comes back filled on companies nobody could say anything specific about.

## Step 3 — Fill the slots, and verify the quote in the same response

The prompt is assembled in three parts: a system block carrying the sender's offer, the three named
slots, the never-appear list and the output contract; the sender's hand-written sets as prior turns;
and last, per row, the company name, domain and evidence text. In Deepline that is one
`deeplineagent` call with `system`, `messages` (the hand-written sets as user/assistant pairs, then
the row), a `jsonSchema` for the seven output fields, and `maxToolCalls: 0` so the model fills slots
from the evidence it was given rather than browsing for more.

Rules that carry the quality:

- **8 to 22 words per bullet.** No em or en dash. No trailing period. No leading capital.
- **Each bullet must name a detail from the evidence.**
- **An empty bullet is better than a generic one.**
- Never a competitor, a dollar figure, a headcount, or a named customer.
- Lint the **rendered block**, not the raw fields — including an article-agreement check, or you ship
  `a injection molding line`.

### The verifier is free and needs no second call

**Each evidence quote must appear as a real substring of the input evidence, normalised on both
sides.** That is the whole verification: the model is asked to quote what it used, and you assert the
quote is real. **A bullet whose evidence does not appear in the input was invented, and it gets
blanked.**

**A length finish reason is a retry, never an abstain.**

**On model choice, reasoning effort is the variable that matters, not model size.** A nano-class
model at minimal reasoning effort wins on cost by more than double. **A nano-class model with
reasoning left unset is the worst of both worlds:** measured in Clay's AI column (where reasoning
could not be set), it burned thousands of hidden reasoning tokens per row, ran roughly **19× more
expensive than a mini-class model**, and **frequently returned blank content** because the reasoning
ate the token budget. `deeplineagent` exposes the knob: pass
`providerOptions: {"openai": {"reasoningEffort": "minimal"}}` (or the lowest value the chosen model
accepts) and `serviceTier: "flex"` for a bulk run. **Build on mini until a 3-row pilot confirms the
lower effort value is accepted and the content comes back non-blank**, then record the model and
effort in the play file so nobody has to guess what is being paid for. `deeplineagent` is priced
from returned usage; read the pilot's cost from `deepline runs get <run-id> --full --json`.

## Step 4 — Read the thinnest rows, not the best ones

**Halt here (`sample-review`).** Show 10 rendered blocks. Then do the thing nobody does: **sort by
evidence length and read the three thinnest rows by hand.**

**A blank rate under 5% is a warning, not a win.** It means the prompt was loosened and the model is
filling thin rows rather than abstaining. **A blank rate above 30% means the evidence source is wrong
for this client** — change the source, not the prompt.

## Step 5 — Route the exclusions, then deliver

Rows with any empty bullet go to the non-ideas campaign. Report: rows with all three bullets, rows
excluded and at which slot they failed, rows where a bullet was blanked because its quote did not
appear in the evidence, and the blank rate with its denominator. Name the namespaced fields the copy
should reference.

## Representative output

Invented examples for shape only; no real company appears. Slots the sender named: **1 — production
scheduling · 2 — quality and compliance records · 3 — supplier and materials planning.** Never
appear: competitors, dollar figures, headcounts, named customers.

### The three bullets, one company

| | bullet | `evidence_N` (must be a real substring of the input) |
|---|---|---|
| 1 | `a production scheduler that plans injection molding runs against cleanroom capacity` | "injection molding in a class 8 cleanroom" |
| 2 | `batch records that stay audit-ready without anyone rekeying them from the floor` | "ISO 13485 certified" |
| 3 | `resin lead times visible before a run is committed, not after` | "medical-grade resins sourced from three suppliers" |

### The rendered block, and a row that was excluded

```
- a production scheduler that plans injection molding runs against cleanroom capacity
- batch records that stay audit-ready without anyone rekeying them from the floor
- resin lead times visible before a run is committed, not after

EXCLUDED  harborline.example
  bullet 1  ok    "contract manufacturing for orthopedics"
  bullet 2  ok    "FDA registered facility"
  bullet 3  ""    nothing in the evidence about materials or suppliers
  -> routed to the non-ideas campaign. two bullets is a different email, not a worse one.
```

### The run summary

```
32 real production rows, seven live campaigns
  27 usable (84%)                  <- out of sample, at volume, different senders
   5 not usable

blank rate 16%   (healthy band: 5-30%. under 5% means the prompt was loosened)
  read the 3 thinnest rows by hand: all 3 correctly abstained

evidence-quote verification: 96 quotes asserted, 2 blanked for not appearing in the input
rows excluded for an empty bullet: 5 -> routed to <the non-ideas campaign>

fields pushed: creative_idea_1_<client> .. _3_<client>   (namespaced)
model: mini-class, reasoning effort minimal, named in the play file
```

## What this skill does not claim

- **Two numbers, and the second is the better one.** The script path graded 5 of 6. Separately, **27
  of 32 real production rows were graded across seven live campaigns (84%)** — out-of-sample, at real
  volume, across different senders. Quote the second.
- **The 91% figure belongs to slot discipline, not to this implementation.** 21 of 23 slot-defined
  against 2 of 5 free-form is the comparison that justifies the design. It is not a claim about what
  any particular sender's bullets will score.
- **The verdict covers a script path.** **The Deepline play build has never been run** — run its own
  acceptance check before trusting it. And one cost figure is measured, on Clay's AI column rather
  than Deepline: a nano-class model with reasoning unset ran about **19× the cost of mini** and
  frequently returned blank content.
- **The quality ceiling is the sender's slots and examples, not the model.** Free-form ideation
  measured 2 of 5. If the slots are vague, no model recovers it — and if the sender cannot name
  three, this is the wrong play.
- **The verifier proves a quote was real, not that a bullet is a good idea.** It asserts the evidence
  substring appears in the input, which catches invention. Whether the idea is worth the prospect's
  time is a judgment nothing here makes.
- **A blank rate is a diagnostic about the evidence source, not a score.** Under 5% means the prompt
  was loosened; over 30% means the source is wrong for this client. Both are list problems, not
  prompt problems.
- **Re-test when the usable rate drops under 60% on 20 rows, or evidence coverage under 80%.** Those
  are the author's trigger points, not guarantees.
- **No reply, meeting or conversion rate is claimed**, and no benchmark for one exists here.

## What good looks like

- The sender named all three slots in their own words, and someone read them back before any model
  call.
- Three complete bullet sets exist, hand-written by the sender, for three real companies — and no
  model drafted any of them.
- The blank rate sits between 5% and 30%, and somebody read the three thinnest rows by hand.
- Every non-empty bullet has an evidence quote beside it that greps back out of the input verbatim.
- Not one email went out with two bullets. Rows missing one are in the other campaign.
- The pushed fields carry the client suffix, so last client's bullets cannot appear.
- No bullet contains a competitor, a dollar figure, a headcount, a named customer, an em dash or a
  trailing period — checked on the rendered block, not the raw fields.
- The model name and reasoning effort are written in the play file, so nobody has to guess what is being paid for.

## Rules

1. **The sender names what each bullet is about. The model never picks a subject and never adds a
   fourth.**
2. **The sender hand-writes three complete bullet sets before any model call.** AI never drafts the
   exemplars it is graded against.
3. **Any empty bullet excludes the row.** A three-bullet email with two bullets is a different email.
4. **Abstain is the empty string**, and an empty bullet is better than a generic one.
5. **Assert every evidence quote as a real substring of the input.** A quote that is not there means
   the bullet was invented — blank it.
6. **Gate the evidence rungs on SHORT, not empty.** Boilerplate is non-empty and produces mail merge.
7. **Namespace the pushed fields per client.** Near-duplicate field names coexist silently.
8. **Bullets are never spun.**
9. **Never name a competitor, a dollar figure, a headcount or a customer.**
10. **Lint the rendered block**, including article agreement.
11. **Set reasoning effort explicitly** on `deeplineagent`; build on a mini-class model, record it in
    the play file, and switch to nano only after a pilot confirms the lowest effort value is accepted.
12. **A length finish reason is a retry, never an abstain.**
13. **Read the thinnest rows, not the best ones.** A blank rate under 5% is a warning.
14. **If the sender cannot name three slots, stop.** This is the wrong play, not a gap to fill.
15. **This skill writes its own columns and sends nothing.**
