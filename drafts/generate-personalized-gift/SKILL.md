---
name: generate-personalized-gift
description: |
  Pick one specific, buyable gift and write the note that goes with it, for each person
  on a list of LinkedIn profiles — by writing (once) and running a Deepline play that
  identifies the person, researches their public presence for genuine personal interests
  (not job skills) with a web-browsing agent, chooses a real product in your budget tied to one of
  those interests, finds a live product page, and drafts a short, warm message that names
  the interest. Use whenever someone asks: find a personalized gift for this prospect,
  what should we send these champions, gift ideas for my top accounts, thoughtful gifting
  for a deal, a send-a-gift touch in a sequence, or write a gift note for this person. Do
  NOT use it to write cold emails or openers with no gift, to research an account or
  company, to find someone's email or phone, or to buy, ship or send anything — it ends
  at a gift plan a person reviews. Every gift ships with its rationale, the research
  behind it, and whether its product link was actually confirmed.
category: personalize-outbound
personas: [account-executive, marketing]
mechanism: workflow
touches: writes-own-output
keywords: []
ported_from: clay-run/clay-skill-creator/skills/lorcan-o-rourke/generate-personalized-gift
---

# Generate a personalized gift

The insight: **a gift should be tied directly to a genuine interest — it should feel
personal, not generic swag.** A person's job title tells you what they do, not what they
care about; the interests that make a gift land — a sport, a cause, a hobby, a taste —
live in their public posts, bio, repos and press. So the research comes first, and the
gift is chosen from what the research found.

The judgment lives in four agent prompts, carried **verbatim** in
`references/prompts.md` with the model each one runs on. This skill's job is to stand
those prompts up as a Deepline play, run it per person, and hand back the plan — not to
rewrite them.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and where an answer does not exist say which step becomes unavailable
rather than guessing. Where a default IS defensible it is named below, and using it means saying so in
the output.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The people** | a list or CSV with a LinkedIn profile URL per person; a name column is optional | no default — the LinkedIn URL is the one required input. A name without a URL is not enough to identify anyone |
| **Gift budget** | the price band a gift must fall in, with currency — it fills `{{gift_budget}}` in the gift prompt | the author's own band, **$30-$150**; say so in the output when it is used |
| **Spend cap** | the most Deepline credits they will spend on this list | ask after the one-person test (Step 4), in credits, with the measured per-person cost beside it. No cap, no full run |
| **Where the plan goes** | the conversation, or a CSV path | the conversation. Nothing is sent, bought or written anywhere else |

**If an answer sheet is present beside this skill, load it and ask only for what it does not cover.**
A partial sheet is normal; a value it is missing gets asked for on its own rather than restarting the
interview. **Say which values came from the sheet** before using them — a sheet applied silently is a
wrong field nobody catches. **If there is no sheet, say nothing about sheets** — the check is a file
lookup, not a question, so run the interview as though the feature did not exist rather than reporting
an absence. At delivery, offer to save the answers back (identifiers only — never a token or a
password), private and never published — and phrase the offer so it explains itself: *"want me to save
your answers to a file, so the next person on your team doesn't have to answer these again?"*

## What this skill touches

- **Reads** — the LinkedIn URLs you supply, and each play run's step outputs (the research and product-link steps read public web pages about each person and retailer product pages through `deeplineagent`'s search and scrape tools).
- **Writes** — one play file of its own, `generate-personalized-gift.play.ts`, in your working directory (created once, reused after), its runs and their Customer DB table, and the gift plan, to the conversation or the CSV you name.
- **Never** — edits a play, table or record it did not create, buys, ships or sends a gift, sends the message, or writes to a CRM or sequence.
- **Halts** — Step 2 write-approval, Step 2 spend-approval, Step 4 sample-review, Step 4 spend-approval

## Step 0 — Verify Deepline is working, and say what this does

Say this first, as two sentences: *this writes one Deepline play file (or reuses it if it is
already there) and runs it on each person's public profile; it hands back a gift plan and never
buys, sends or writes anything else.*

Run `deepline preflight --json`. If it fails, name what is wrong — the CLI missing, out of date,
or signed out — give the one fix (`npm install -g deepline && deepline auth register --wait auto`,
or `deepline update`), and **stop**. Tell the user which org you are in.

This skill writes and runs its play **per the `deepline-gtm` skill's `recipes/deepline-plays.md`**
— read it before Step 2 and follow it for the play shape, `deepline plays check`, runs and export.

## Step 1 — Collect the inputs (interview; do not guess)

1. **The people** — LinkedIn profile URLs, one per person. Dedupe on the normalized URL
   (lowercase, strip query string and trailing slash). A name column is corroboration
   only; the enriched name is the one used.
2. **Gift budget** — the band and currency. Offer the author's $30-$150 if they have
   none, and say that is what it is.
3. **Where the plan goes** — the conversation or a CSV path.

The spend cap is asked in Step 4, once there is a measured cost to set it against.

## Step 2 — Find or write the play (one gate first)

**Look before building.** Check the working directory for `generate-personalized-gift.play.ts`,
and `deepline plays grep "personalized gift"` for a saved copy. If one exists, check it has the
steps below with the prompts and models in `references/prompts.md`; if so, reuse it and skip to
Step 3. If it exists but differs, say how, and ask whether to use it as-is or write a fresh one
alongside — never edit it.

**Before creating anything, one message:** the play file name, the step list below, and that the
next step runs it on **one** person — whose cost cannot be stated exactly beforehand, because the
research steps search the open web and bill by what they do (`deeplineagent` is priced from
returned usage, and each search or scrape it calls bills as its own tool). For reference only, one
end-to-end test of the original Clay build (2026-09-25) used **3.3 Clay data credits and 5 action
executions** for one person; that is not a Deepline price. **Wait for an explicit yes.**

The play, in order — one `.withColumn` per step over a CSV with `linkedin_url`, optional
`full_name`, and `gift_budget` (the declared budget, on every row):

| # | Step | Deepline tool | What it does |
|---|---|---|---|
| 1 | **Enrich person** | `crustdata_person_enrichment` | `linkedinProfileUrl` ← `linkedin_url`. 0.4 Deepline credits per returned profile at the database rate, per `deepline tools describe`; do not request email or phone fields, which add charges. Name and title come back at the tool's declared getters (`full_name`, `title`); read the current employer's field from the first response and pin it |
| 2 | **Person found?** | `run_javascript` | returns the name or null; every later step is skipped for a row where it is null, so the run ends there |
| 3 | **Research Interests** | `deeplineagent` | prompt 1 in `references/prompts.md` as `prompt`, its `model`, `jsonSchema` with `interests`, `research_notes`. Tools left on (default `maxToolCalls`), so it can search and scrape the open web |
| 4 | **Ideate Gift** | `deeplineagent` | prompt 2, its model, `jsonSchema` with `gift_idea`, `gift_rationale`, `search_query`; `{{gift_budget}}` from the row; `maxToolCalls: 0` |
| 5 | **Purchasable Product Link** | `deeplineagent` | prompt 3, its model, `jsonSchema` with `product_name`, `product_url`, `price`, `link_verified`. Tools left on, so it can search and open the product page |
| 6 | **Personalized Message** | `deeplineagent` | prompt 4, its model, `jsonSchema` with the fields listed there; `maxToolCalls: 0` |

Interpolate every `{{variable}}` in each prompt from the step named in `references/prompts.md`.
Read structured outputs at `toolResponse.raw.result.object` (per the `deeplineagent` provider
playbook). Every `jsonSchema` property gets a description and is in `required`. Run
`deepline plays check ./generate-personalized-gift.play.ts` before any run.

## Step 3 — Test on one person

Take one person from the list into a one-row CSV and run
`deepline plays run ./generate-personalized-gift.play.ts --input '{"csv":"one.csv"}' --debug`.
Then read `deepline runs get <run-id> --full --json`:

- **cost** — the run's reported billing is its actual spend. Use it, **never the org balance**:
  in a shared org the balance moves with everyone's work (on the original Clay test, a run
  that cost 3.3 credits saw the shared balance fall by about 3,200 in the same minutes).
- **values** — each step's output per row. Check values, not status — a step can complete
  around an empty result.

If any step errored or returned empty fields, fix the build (interpolation, `jsonSchema`,
model id) and re-test — never the prompt wording.

## Step 4 — Show the test, set the cap, then run the rest

**One message:** the test person's full plan in the output shape below, the measured
cost for one person, that cost × the remaining people, and one question: *what is the
most you want to spend on this list?* Say plainly that research depth varies, so later
people can cost more or less than the first. **Wait** — this is the look at gift taste
no estimate reveals, and the spend decision in the same breath.

Then run the remaining people in batches (a CSV slice per run). Keep a running total of each
finished run's reported billing; **stop before the next batch would pass the cap** and
say how many people remain. Export each with `deepline runs export <run-id> --out <file>`.

## Step 5 — Assemble the plan from the step outputs

Build each row **from the step that produced each field** — name, title and company
from *Enrich person*; interests and research notes from *Research Interests*; gift and
rationale from *Ideate Gift*; product name, URL, price and `link_verified` from
*Purchasable Product Link*; only the message from *Personalized Message*. Never take a
URL or price from the message step's copies.

Compare each price to the budget band in code, not by eye; outside it → flag
`over-budget` or `under-budget` in the price cell. A row that ended at **Person found?**
goes under *Could not identify*. A failed row is listed with its error, never dropped.

## Representative output

### Gift plan per person

| Person | Title · Company | Interests | Research notes | Gift | Why it fits | Price | Product link | Link verified | Message |
|---|---|---|---|---|---|---|---|---|---|
| Dana Whitfield | VP Marketing · Northwind | trail running, specialty coffee | Posted about a Big Sur marathon PR (Mar); bio mentions "pour-over snob" | Fellow Stagg EKG kettle | Turns her pour-over habit into a ritual | $165 · over-budget | fellowproducts.com/… | true | "Dana — congrats again on Big Sur…" |
| Sam Ortiz | Head of Data · Contoso | chess, sci-fi | Inferred from title and bio; no public posts found | Chess.com Diamond, 1 year | Fits a strategy-minded data lead | $70 | chess.com/… | false | "Sam — a little something for your next rapid game…" |

### Could not identify

| LinkedIn URL | Reason |
|---|---|
| linkedin.com/in/… | Enrich person returned no person; the row stopped before any research |

Plus a summary: people in, identified, gifts planned, links verified vs not, gifts
outside the budget band, the band used (and whether it was the author's default),
failed rows, and credits spent (the sum of each run's reported billing) against
the cap.

## What this skill does not claim

- How often a gift chosen this way is well received has never been measured.
- A gift based on inferred interests sits in the same list as one based on found interests; the only marker is the research note.
- The original Clay build was run end to end once, on one person (3.3 Clay data credits, 5 action executions). The Deepline play has not been run; cost varies with how much research each person needs, and nothing has measured the spread across a list.
- Prices and stock are as listed when the page was checked; shipping to the recipient's country is not checked.
- It does not check whether the recipient's employer limits the gifts they may accept.
- Public interests can be stale — a post from years ago may not reflect what the person cares about now.
- Why the budget band is $30-$150 was never established — it is the author's default, not a tested figure.

## What good looks like

- The play is written once and reused; the second list costs no build time.
- Every gift traces back to an interest, and every interest to a source — or a research note that says it was inferred.
- A sender can tell at a glance which product links were confirmed and which gifts fall outside the budget.
- People the enrichment could not identify cost one enrichment and nothing more — no research ran on a blank name.
- The common mistake: rewording the prompts "to fit the skill". They are the product; the skill is the wiring.

## Rules

- MUST use the four prompts in `references/prompts.md` verbatim, on the models listed there; NEVER reword, merge or substitute a model silently.
- MUST look for an existing `generate-personalized-gift.play.ts` before writing one, and NEVER edit a play, table or record this skill did not create.
- MUST get explicit approval (Step 2) before creating the play or running it, and a spend cap (Step 4) before running more than one person.
- MUST end the run when Enrich person returns no `name`; NEVER research or gift for an unidentified person.
- MUST assemble each field from the step that produced it and show `Link verified` for every row; NEVER put the link in the message.
- NEVER buy, ship or send a gift or a message, or write to a CRM or sequence — this ends at the plan.

## Worked example

Ask: "Gift ideas for these 25 champions, budget $50-$120." Step 0: `deepline preflight`
passes. Step 1: 25 URLs → 24 unique; budget theirs. Step 2: no existing
play; the six-step play and the one-person test are approved; written, `plays check` passes.
Step 3: test on one person — every step filled; the run reports its cost (this example's
figures are the original Clay run's: 3.3 credits). Step 4: the test plan is shown with "3.3
credits for one person, about 76 for the other 23 — what's the most you want to spend?"; cap
set at 100. Step 5: the other 23 in batches, totalling each run's reported credits between
batches; 21 identified, 2 stopped at *Person found?*, 0 failed. Summary: 24 in · 22 identified
· 22 gifts planned · 19 links verified · 2 outside the budget · budget $50-$120 (theirs) · 74.6
credits spent of a 100 cap.
