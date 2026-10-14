---
name: clean-first-names-for-greetings
description: |
  Turn the raw first-name field on a lead row into the name a person would actually be greeted by,
  so an email can open with it, using a Deepline play. Strips honorifics, fixes SHOUTING and lowercase, removes possessive
  artifacts from business listings, keeps hyphenated and internally capitalised names intact, and
  withholds a value entirely rather than guessing. Use whenever someone asks: clean these first
  names, the greeting says Hi DR MATTHEW, strip the titles off the names, some rows have the whole
  name in the first-name column, normalize first names for the campaign, or why does my merge field
  look robotic. Do NOT use it to find a missing name — it never looks anything up, and a blank stays
  blank. Do NOT use it to clean company names, to decide whether a company is in your ICP, or to
  detect that a contact has left their job. It writes one column and sends nothing.
category: verify-and-clean
personas: [gtm-engineer, revops]
mechanism: logic-only
touches: writes-records
keywords: [crm-hygiene, cold-email]
ported_from: clay-run/clay-skill-creator/skills/eric-nowoslawski/clean-first-names-for-greetings
---

# Clean first names for greetings (a withheld row beats a wrong greeting)

**The insight, and it is the whole design: the failure you must never ship is a confident wrong
name, not a blank one.** `Hi N/A,` and `Hi Tvk,` are both worse than an excluded row, because the
excluded row costs you one send and the wrong one costs you the account. So every rule here is
built to make the model's errors announce themselves rather than to squeeze the accuracy higher.

That is measurable. Two versions of the extraction prompt scored **identically on accuracy** and
differed only in silent failures — 3 versus 0. The version that ships is the one whose mistakes are
visible, not the one that is cleverer.

**Run this before any other custom variable**, because other variables interpolate the cleaned
name. Run it alongside company-name cleaning, which is its twin and deliberately the same shape —
with one difference worth knowing: **first-name cleaning is a standing column** (a mangled first
name breaks the greeting on every campaign that opens with one), while company-name cleaning is a
toggle you switch on per client.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The rows** | a CSV (or a Deepline Customer DB table / CRM export) with `first_name_raw` per row | no default — there is nothing to clean. This is the only hard requirement |
| **`last_name_raw`** | the raw last-name column, if they have one | not required, but **ask for it** — it is free and it is what catches the duplicated-full-name and company-in-the-person-column cases. Without it those rows ship uncaught |
| **`company_name_raw`** | the raw company column, if they have one | not required, but **ask** — it is the only reliable discriminator for short ALL-CAPS tokens. Without it, guard G2 cannot run and a company name can ship as a person |
| **Where the cleaned value is written** | the column name their copy will reference | default `first_name_clean`, and **say you used it**. Keep the raw value in place beside it so a human can always see the source string |
| **What happens to withheld rows** | the review queue, list or view they route to | ask — this skill excludes rather than substitutes, so a row with nowhere to go is a row that silently disappears |
| **Whether non-Latin-script names are in scope** | whether this campaign sends in English only | ask. Names written only in a non-Latin script are **kept exactly as written and flagged**, not transliterated and not blanked. An English-only campaign excludes them; a native-language campaign is a legitimate use for them, and the preserved name is what makes that possible |
| **Which model does the extraction** | the `model` passed to `ai_inference` (exact AI Gateway id, case-sensitive) | the author measured `gpt-4o-mini`. A different model changes the token cap: **200 for mini-class, 2000 for nano-class**, and a nano model left at 200 returns empty on essentially every row |

**Pass the RAW strings, never the cleaned company name.** The model needs to see the mess to
recognise it.

## What this skill touches

- **Reads** — the raw first-name, last-name and company-name strings on the rows you point it at.
- **Writes** — one cleaned-name column plus its three companion fields (`changed`, `confidence`,
  `needs_review`) on the same rows. Nothing else.
- **Never** — looks a name up anywhere, transliterates a name, substitutes a generic greeting,
  drafts or sends a message, enrols anyone in a sequence, or writes to a CRM.
- **Halts** — Step 2 sample-review.
- **Derived from** — a 100-row adversarially stratified benchmark and a 14,731-row frequency sample
  of real contact rows, both the author's, plus a head-to-head prompt audit on 30 fresh rows. The
  graded path is a script calling a model API; see the claims section for what that does and does
  not cover.

## Declared outputs

| Field | Type | Example | Null? |
|---|---|---|---|
| `first_name_clean` | string, 20 chars target / 40 hard | `Ruba` | no — **`""` instead** |
| `changed` | boolean | `true` | no |
| `confidence` | `high` / `low` | `low` | no |
| `needs_review` | boolean, **computed by the guards, never by the model** | `true` | no |

**The abstain value is the empty string.** Never `N/A`, never the text `null`, never `there`,
`friend`, `team` or `folks`. This is not a style preference: **`N/A` renders into a live email as
`Hi N/A,`.**

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json` (missing CLI: `npm install -g deepline && deepline auth register
--wait auto`) and tell the user which org it reports. Confirm the input exists and carries the
columns: `deepline csv show --csv <file> --summary`. Name it out loud, then say in one sentence what
this run will touch: *"this adds a cleaned-name column and three companion columns to <the CSV>,
reads nothing else, and sends nothing to anyone."*

If the platform check fails, say which command failed and stop. There is nothing to write into.

## Step 1 — Collect the inputs, and ask about the ones that are free

Work through the declared-inputs table. Two questions matter more than they look:

- **Ask for the last-name and company columns even though they are optional.** They cost nothing and
  they are the only way two whole failure classes get caught.
- **Ask where withheld rows go.** This skill excludes rather than guesses, so without a destination
  the withheld rows are simply gone.

Do not ask which model to use unless the installer has a preference; default it and say so. Do not ask for the output column
name — default it, say so, and let it be corrected.

## Step 2 — Clean a 20-row sample, read it, then gate

Run the column on 20 rows **that include the messy ones** — filter for blanks, ALL-CAPS, leading
lowercase, honorific prefixes, parentheses, and values of two characters or fewer. A random 20 rows
will look perfect and tell you nothing.

Then show the installer the sample as a before-and-after table and **halt for sample-review.**

**Halt here (`sample-review`).** This is the only gate, and it is before the spend, not after.
State how many of the 20 shipped a value, how many were withheld, and read out any row where the
cleaned value surprised you.

The reason this gate exists: every failure mode below is **silent**. An empty column, an unbound
variable, and a guard that withheld every row all look identical to "still processing".

## Step 3 — Run the extraction, with the guards attached

The cleaning is one model call per row against a locked prompt, plus six deterministic checks that
run in code, not in the model. In Deepline that is a custom play (author per the deepline-gtm
`recipes/deepline-plays.md`; run `deepline plays run file.play.ts --input '{"csv":"leads.csv"}'`,
then `deepline runs export <run-id> --out <final.csv>`): one `ai_inference` column (`model`,
`system`, `prompt`, `jsonSchema`, `maxOutputTokens`; read `result.object`), then a `run_javascript`
column holding the guards. **Never run the model without the guards.**

Rules the prompt enforces:

1. Return the name a person would be greeted by, and nothing else.
2. Strip honorifics and credentials — `Dr`, `Prof`, `Mr`, `Mrs`, `Ms`, `MD`, `PhD`, `Esq`.
3. Drop anything appended that is not part of the name — emoji, hiring notices, pronouns, job
   titles, company names.
4. **Apply casing after extraction, never during.** Title Case, except deliberate internal capitals
   (`DeAndrea`, `McCurry`) and non-Latin scripts, which stay exactly as written. A lowercase or
   SHOUTING greeting is the most recognisable mail-merge tell in cold email.
5. **Possessive artifacts are stripped only at the END of the field** (`Araceli's` → `Araceli`).
   Broaden this and you destroy `D'Anza`, `T'Kia`, `O'Brien`, `Qurratu'Aini`.
6. **Never take the first half of a hyphenated name.** `Maria-Jose` stays whole.
7. If the string contains no answer, return the empty string.

**Do not shorten the prompt.** This was measured, not argued. A 13-line candidate ran head to head
against the full version on 30 fresh rows, same model, same parameters:

| | full prompt | short candidate |
|---|---|---|
| Ship-ready rows | **29/30** | 27/30 |
| **Broken sends** | **0** | **3 (10%)** |
| Cost per 1,000 rows, warm | **$0.047** | $0.0325 |

Cutting the example block drops the static prefix under the model's 1,024-token cache floor: 82%
fewer prompt tokens buys only 31% less cost, and the model loses the examples that carry the hard
cases. **The guards do not compensate for a weaker prompt** — verified: all six guards returned
false on all five rows where the short prompt diverged. They catch invention and known junk, not
failure to strip.

### The six guards, required on every runtime

| Guard | Catches | Action | Why it is written this way |
|---|---|---|---|
| **G1** placeholder | mailbox roles and junk — `Admin`, `Info`, `Team`, `N/A`, blank | ABSTAIN | matches the **whole** normalised string, never a substring: `Adminson` and `Teamer` are real surnames |
| **G2** company overlap | first + last reading as the company name | **FLAG ONLY** | never an auto-abstain — a real row is `Jana Meerman` at company `Jana Meerman` |
| **G3** caps acronym | 2–4 character ALL-CAPS with **no vowel** (`TVK`, `KSM`) | FLAG | the vowel test is what keeps `PAUL` and `PHAM` out of the flag |
| **G4** run-together shout | one ALL-CAPS token of 9+ characters (`KIRKDELANEY`) | FLAG | splitting it would invent a word boundary |
| **G5** non-Latin script | the cleaned value is not writable in Latin script | FLAG, **never abstain** | keep the name exactly as written; transliterating invents letters, blanking destroys a real name |
| **G6** invented letters | the normalised output is not a substring of the normalised input | QUARANTINE | a trip here means the model made something up |

**One bug worth knowing about, because it hid itself.** The first version of G1 tested emptiness
after normalising to `[0-9a-z]` — which reduces `珊` to the empty string. That version **silently
abstained on every Chinese, Cyrillic, Arabic and Korean name in the benchmark, 4 of 100 rows, and
reported them as ordinary placeholder abstains, so the model's score never moved.** Any edit to the
normaliser must keep a Unicode-aware letters test beside it.

**Truncation is a retry, never an abstain.** A `length` finish reason (`result.finishReason` on the `ai_inference` output) means raise the token cap (`maxOutputTokens`) and
call again. Running a nano-class model at a mini-class cap returns empty content on essentially
every row, which is the single most common way to measure a 0% hit rate on a working prompt.

## Step 4 — Gate the downstream send: exclude, never substitute

| Condition | What happens |
|---|---|
| the cleaned value is empty | **EXCLUDE the row**, route to review |
| any guard fired (`needs_review` true) | **EXCLUDE the row**, route to review |
| the name is written only in a non-Latin script | **EXCLUDE from an English-language campaign**, route to review with the name intact |
| any of the above, and someone proposes a generic greeting | **No.** Not `there`, `friend`, `team`, `folks`, or the company name. Not by substitution, not by spintax |

**Why exclusion rather than a fallback greeting.** An unusable first name usually means the row is
not a person at all — which makes the title and the email address suspect too. A generic greeting
does not rescue that row, it sends a worse email to a worse address.

## Step 5 — Deliver, and say what was withheld

Report, in this order: how many rows shipped a value, how many were withheld and under which guard,
and the rows where the cleaned value differs from the raw in a way a human should glance at. Name the
column the copy should reference. Do not report a percentage without the denominator.

## Representative output

Invented examples for shape only; no real contact appears.

### The cleaned column, row by row

| `first_name_raw` | `first_name_clean` | `changed` | `confidence` | `needs_review` | what happened |
|---|---|---|---|---|---|
| `Dr Ruba` | `Ruba` | true | high | false | honorific stripped |
| `alan` | `Alan` | true | high | false | casing applied after extraction |
| `PAUL` | `Paul` | true | high | false | has a vowel, so G3 does not fire |
| `Maria-Jose (MJ)` | `MJ` | true | high | false | parenthetical is the name they use |
| `Araceli's Flowers` | `Araceli` | true | high | false | possessive stripped at the end only |
| `McCurry` | `McCurry` | false | high | false | internal capital preserved |
| `KIRKDELANEY` | `` | true | low | **true** | G4 — splitting would invent a boundary |
| `TVK` | `` | true | low | **true** | G3 — initials or an acronym, nothing decides it |
| `Info` | `` | true | high | **true** | G1 — mailbox role, whole-string match |
| `Дарья` | `Дарья` | false | high | **true** | G5 — kept exactly, excluded from an English campaign |

### The run summary

```
20 rows sampled (messy-pattern filter, not random)
  14 shipped a copy-ready value
   6 withheld for review:  G1 x2   G3 x1   G4 x1   G5 x2
   0 rows where the output contained letters the input did not (G6 clean)

copy should reference: first_name_clean
withheld rows routed to: <the review view the installer named>
```

## What this skill does not claim

- **The graded figure is 96/100, and the honest figure is 94.5%.** The prompt's example block
  overlaps the benchmark — 27 of the 100 rows appear verbatim as examples, because the examples were
  written after reading the corpus. **On the 73 held-out rows the score is 69/73 (94.5%), and all
  four failures are in the held-out set.** Quote 94.5%.
- **That verdict covers a script path calling a model API**, at roughly one second and $0.21 per
  1,000 rows. **The Deepline `ai_inference` play column has never been run**, and the `run_javascript`
  version of the six guards has never been executed — they were measured in Python. Same prompt, same model,
  different runtime. Build it, run the 20-row sample, and read the output before trusting either.
- **100 rows, adversarially stratified, majority English.** Re-run the benchmark on the installer's
  own corpus before locking this for a list that is mostly CJK or Arabic names.
- **The residual failures have no fix.** The model's errors are all one class: a short or shouted
  token that could be initials or could be a business, with nothing in the string to settle it. A
  bigger model does not solve that. It needs a flag and a human, which is what the guards do.
- **The expected production rate is 97–99% shipping, not 96%.** Those are different numbers measured
  on different things: the benchmark is deliberately adversarial, while a frequency sample of 14,731
  real rows found the genuinely broken share to be 1–3%.
- **No reply, meeting or conversion rate is claimed**, and no benchmark for one exists here. This
  skill changes one merge field.
- **It cannot tell you the row is stale.** A correctly cleaned name on someone who left the company
  is still a correctly cleaned name. That is a list-freshness problem.
- **Roughly 7.8% of rows in shared contact data have a first name and a company that describe
  different people.** That is a defect in the source, measured but not fixed here — it gets flagged
  and has to be resolved upstream.

## What good looks like

- The withheld count is non-zero on a messy list. If every row ships, a guard is not firing.
- The 20-row sample was drawn with a messy-pattern filter, not at random, and someone read it.
- The raw value still sits beside the cleaned one, so a human can always see the source string.
- Copy references the cleaned column, not the sequencer's or CRM's built-in first-name field. This is the
  single commonest way a cleaned list still sends `Hi Dr Matthew,`.
- No row anywhere carries `N/A`, `there`, `friend` or the company name as a greeting.
- A non-Latin-script name is present and intact in the review queue, not blanked and not
  transliterated.
- Running it twice on the same rows produces the same values.

## Rules

1. **Abstain is the empty string.** Never `N/A`, never a generic greeting, never a guess.
2. **The model never runs without the six guards**, and the guards never substitute for the prompt.
3. **G2 is flag-only, always.** Turning it into an abstain drops real people whose company is named
   after them.
4. **G5 never abstains and never transliterates.** Keep the name as written and let the downstream
   gate decide the campaign.
5. **Do not shorten the prompt.** It was audited head to head and the short version shipped three
   broken sends in thirty rows.
6. **Apply casing after extraction, never during it.**
7. **Strip possessives only at the end of the field.**
8. **Never split a hyphenated name.**
9. **A truncated response is a retry, never an abstain.** Check the token cap matches the model class.
10. **Sample 20 messy rows and have a human read them before running the list.** Every failure here
    is silent, and "no rows qualified" looks exactly like "the gate is broken".
11. **Report the denominator with every rate.**
12. **This skill writes one column and sends nothing.** What happens to the excluded rows is the
    installer's decision, not this skill's.
