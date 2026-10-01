---
name: clean-company-names-for-copy
description: |
  Turn the raw company-name string on a lead row into the short human form a person would say out
  loud, so it can be dropped into email copy, using Deepline plays. "318, Inc dba Hamiltons Bud and Bloom" becomes
  "Hamiltons Bud and Bloom". Starts from the free deterministic normalizer and only escalates to an
  AI column (Deepline `ai_inference`) when a measured read of the installer's own list says the normalizer cannot fix what is
  wrong. Use whenever someone asks: clean these company names, strip the LLC and Inc, the company
  names look robotic, normalize company names for the campaign, or my merge field is printing a
  tagline. Do NOT use it to find a company FACT — funding, hiring, tech, pricing are separate
  skills. Do NOT use it to decide whether a company is real or in your ICP, to clean first names, or
  to fix a stale row. It writes one column and sends nothing.
category: verify-and-clean
personas: [gtm-engineer, revops]
mechanism: logic-only
touches: writes-records
keywords: [crm-hygiene, cold-email]
ported_from: clay-run/clay-skill-creator/skills/eric-nowoslawski/clean-company-names-for-copy
---

# Clean company names for copy (the free normalizer is the default, AI is the toggle)

**The insight most people get backwards: the AI pass is not the answer, it is the escalation.**
There is already a free, deterministic normalizer that handles suffixes and casing, and it scores
**89/100** on its own. An AI pass gets you to 98/100 — worth it for some clients and pure ceremony
for others, and the difference is not a matter of taste. It is a twenty-row read of their own list.

So this skill's first job is to talk you out of the expensive path, and its second job is to run it
properly when the read says you need it.

**Why this is a toggle when first-name cleaning is a standing column:** a mangled first name breaks
the greeting on every campaign that opens with one. A mangled company name only breaks the
campaigns that name the company. Same shape, different default.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The rows** | a CSV (or a Deepline Customer DB table / CRM export) with `company_name_raw` per row | no default — there is nothing to clean. The only hard requirement |
| **`domain`** | the bare lowercase domain, no `www` | not required, but **ask** — it costs nothing and it lifts accuracy on ambiguous strings. Without it, a row where the name and the domain disagree cannot be flagged |
| **Whether the copy names the company** | which sentences reference it — a subject line, a first sentence, a possessive | **ask first, because it decides whether to run at all.** If no copy names the company, stop here and say so |
| **The 20-row read** | their verdict on 20 rows of the free normalizer's output | **this is the decision, not a formality** — see Step 1. No default: the author cannot read the installer's list for them |
| **Where the cleaned value is written** | the column name their copy will reference | default `company_clean`, and **say you used it**. Keep the raw value beside it |
| **What happens to abstained rows** | the review list or view they route to | ask — this skill excludes rather than substitutes, so a row with nowhere to go silently disappears |
| **Whether an operator override applies** | whether they want the volume and will accept dropping the clause instead of the row | ask only if they push back on exclusion. Note the best practice once, do it their way, and **log the override** |
| **Which model does the extraction** | the `model` passed to `ai_inference` (exact AI Gateway id, case-sensitive) | the author measured `gpt-4o-mini`, and **that is the weaker model for the abstain case** — 7/10 against 10/10 for a nano-class model. Token cap **200 for mini-class, 2000 for nano-class** |

## What this skill touches

- **Reads** — the raw company-name string, and the domain where one exists, on the rows you point it
  at.
- **Writes** — one cleaned-name column plus `changed` and `confidence` on those rows. Nothing else.
- **Never** — looks a company up in a database, invents or corrects a spelling, substitutes a
  generic phrase for a missing name, drafts or sends a message, enrols anyone, or writes to a CRM.
- **Halts** — Step 1 sample-review, Step 4 sample-review.
- **Derived from** — a 100-row graded benchmark and a separate 10-row abstain probe, both the
  author's, plus measured variants across five paths. The graded path is a script calling a model
  API; see the claims section for what that does and does not cover.

## Declared outputs

| Field | Type | Example | Null? |
|---|---|---|---|
| `company_clean` | string, 40 chars target / 60 hard | `Ajax Turner` | no — **`""` instead** |
| `changed` | boolean | `true` | no |
| `confidence` | `high` / `low` / `unknown` | `high` | no. The regex-only path reports `unknown` on every row, because it cannot judge itself |

**The abstain value is the empty string.** Never `N/A`, never the text `null`, never a guess.

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json` (missing CLI: `npm install -g deepline && deepline auth register
--wait auto`). Tell the user which org it reports. Confirm the input exists and has the column:
`deepline csv show --csv <file> --summary`. Name it, then say what this run touches:
*"this adds a cleaned-name column and two companion columns to <the CSV you named>, reads nothing
else, and sends nothing."* If the check fails, name the failing command and stop.

## Step 1 — Decide whether the AI pass is needed at all. This is the gate.

Run the **free deterministic normalizer** (a `run_javascript` column in a play: legal-suffix strip
plus title-casing; see Step 2) on 20 rows of their list and put the output in front of
them. Then apply the test. **Escalate to the AI pass only when all three are true:**

1. The copy names the company somewhere a reader will notice — a subject line, a first sentence, a
   possessive.
2. A 20-row read of the normalizer's output finds **more than about 2** values they would edit
   before sending.
3. Those failures are the **model-shaped kind** — taglines after a pipe, `dba` entities,
   parenthetical descriptors, appended city names, second-language duplicates, junk strings that
   need an abstain — and **not** simple suffix or casing problems.

**If the failures are suffix and casing problems, the free normalizer already handles them and the
AI pass buys nothing.** Say so and stop.

**Halt here (`sample-review`).** Show the 20 rows, state which of the two paths the list needs, and
**record the decision** so QA reads the right column and nobody re-litigates it mid-campaign.

Real strings that show the difference. The normalizer handles the first two; only the AI path
handles the rest:

```
Ajax Turner Company, Inc.                          <- suffix. Normalizer.
ABN TECH CORP                                      <- casing. Normalizer.
318, Inc dba Hamiltons Bud and Bloom               <- dba entity. AI.
AlaMark Technologies | FileMaker Consultants | ... <- tagline after a pipe. AI.
Alraqhi Acessories for Building Materials | (…)    <- second-language duplicate. AI.
Self-employed                                      <- needs an abstain. Guard.
```

## Step 2 — Run the free path, and stop here if that is the answer

The deterministic normalizer with title-casing on: a `run_javascript` column in a custom play
(`deepline plays run file.play.ts --input '{"csv":"leads.csv"}'`, author per the deepline-gtm
`recipes/deepline-plays.md`). Pure compute, no provider call. **89/100 on the benchmark** (measured on
Clay's built-in normalize-company-name action; a hand-written JS normalizer is a different
implementation, so re-read the 20-row sample rather than assuming the same score).

If Step 1 said this is enough, this is the whole skill. Report what it produced, tell them which
column the copy references, and move to Step 5.

**One thing the free path cannot do: judge itself.** It reports `confidence: unknown` on every row.
So a regex-only run that shows zero review flags on a list nobody has read is not a clean list, it
is an unexamined one. **Sample 20 rows by hand before any send.**

## Step 3 — the AI pass, with the placeholder guard attached

One `ai_inference` call per row (a `.withColumn(..., 'ai_inference', {model, system, prompt,
jsonSchema, maxOutputTokens})` step in the play) against a locked prompt. Rules it enforces, in the order they matter:

1. Return the short human form of the brand, nothing else.
2. Strip legal suffixes — `Inc`, `LLC`, `Ltd`, `Corp`, `GmbH`, `Pty`, and the rest.
3. Resolve `dba` and `trading as` to the **operating** brand, not the registered entity.
4. Drop taglines, service lists and descriptors after a pipe, dash or comma.
5. Drop an appended city or region that is not part of the brand.
6. **Strip parenthetical descriptors but keep parentheses that ARE the brand** — `(319) Auto Body`
   and `(402) Creamery` are real names. Rule 6 overreaching here is a polish problem, not a
   send-blocker, since both readings are sendable.
7. Drop a second-language duplicate of the same name.
8. Use the brand's real casing, not Title Case applied blindly.
9. **Protect genuine acronyms narrowly.** An over-broad acronym rule is what ships `ABN TECH`
   SHOUTING. If you edit this rule, re-run the benchmark.
10. **Never invent a word, and never fix a misspelling** — fixing a typo means inventing a word. A
    misspelling in the source survives cleaning. Catch it with a spell-check on the review list.
11. Abstain to the empty string on a junk string.

**Do not shorten the prompt**, and specifically do not cut the example block. A 950-token static
prefix cached **zero** tokens; a 1,716-token prefix cached about 1,300. Dropping under the model's
1,024-token cache floor costs three times as much per thousand rows for a shorter prompt.

Set the JSON response format (`jsonSchema`; read `result.object`). Without it the column returns prose and the downstream formula, which
expects an object, silently gets nothing. Pass no temperature setting (leave `providerOptions` without one) — the default is not zero, so
the same input gives different answers on a rerun. Cache the output and do not re-run a locked
campaign's names.

### The placeholder guard is mandatory, not a nicety

Rule 11 tells the model to abstain on junk. A nano-class model obeys, **10/10**. **`gpt-4o-mini`
does not: 7/10**, returning `Self-Employed CPA`, `Confidential Jobs` and `Private Practice` as if
they were brands. Mini is the cheaper and commoner model, so **the abstain cannot be the model's
decision alone.**

Run a deterministic blocklist on the raw input **and on the model's output**, matching the **whole
normalised string** plus a `selfemployed` prefix.

**Never match on substrings.** `Unknown Arts` and `Retired - BTH Bank` are real companies, and a
substring rule deletes them silently. Checking the output as well as the input is also what stops
the regex path turning `Retired - BTH Bank` into `Retired` and sending it.

**A truncated response is a retry, never an abstain.** A `length` finish reason (`result.finishReason` on the `ai_inference`
output) means the cap was too small (`maxOutputTokens`) — raise it and call again. This is not theoretical: the first draft returned empty on **3
of 100 rows** for exactly this reason, and **every one of them looked like a legitimate abstain until
the finish reason was checked.** A nano-class model spends around 640 reasoning tokens, so a nano
model left at the mini cap of 200 returns `length` on essentially every row.

## Step 4 — Read 20 sampled values before the list runs

**Halt here (`sample-review`).** Show 20 cleaned values beside their raw strings. Re-test the prompt
if the read finds **more than one** name an operator would edit.

Every failure mode here is silent. Empty column, unbound variable, and a gate that dropped every row
look identical to "still processing" — and because the Step 5 gate excludes empty rows, **a gate
that cannot evaluate true drops the entire list from the campaign** while reporting nothing.

## Step 5 — Gate the downstream send: exclude, never substitute

If the cleaned value is empty, or the cleaner abstained on a junk string — `Self-employed`, `N/A`,
`Private Practice`, `Confidential Jobs` — **exclude the row from any campaign whose copy references
the company** and route it to review.

**Do not substitute "your team", "your company" or anything generic, and do not spintax around it.**
The sentence was written to name a company. An empty value means you do not know where this person
works, which usually also means the row's title and domain are suspect, and a generic substitute
just sends a worse email to a worse address.

**Operator override:** keeping the row with the whole clause dropped via spintax is available when
the operator wants the volume and accepts the trade. Note the best practice once, proceed their way,
log the override.

## Step 6 — Deliver, and say which path ran

Report: which path ran and why, how many rows shipped a value, how many abstained, and the rows where
the cleaned name does not match the domain. Name the column the copy should reference. Never report a
rate without its denominator.

## Representative output

Invented examples for shape only; no real company appears.

### The cleaned column, row by row

| `company_name_raw` | `company_clean` | `changed` | `confidence` | what happened |
|---|---|---|---|---|
| `Ajax Turner Company, Inc.` | `Ajax Turner` | true | high | legal suffix stripped — the free path does this |
| `ABN TECH CORP` | `ABN Tech` | true | high | casing, with the acronym protected narrowly |
| `318, Inc dba Hamiltons Bud and Bloom` | `Hamiltons Bud and Bloom` | true | high | resolved to the operating brand |
| `AlaMark Technologies \| FileMaker Consultants` | `AlaMark Technologies` | true | high | tagline after the pipe dropped |
| `(319) Auto Body` | `(319) Auto Body` | false | high | the parentheses ARE the brand |
| `Northstar Example (a Vantage company)` | `Northstar Example` | true | high | parenthetical descriptor dropped |
| `accounting business solutions` | `Accounting Business Solutions` | true | low | a generic string that is a real name — flagged, not abstained |
| `Self-employed` | `` | true | high | **guard** — whole-string placeholder match |
| `Private Practice` | `` | true | high | **guard** — mini would have shipped this as a brand |
| `Retired - BTH Bank` | `` | true | high | **guard on the OUTPUT** — the regex path would have sent `Retired` |

### The run summary

```
path: AI column (20-row read found 6 edits, all model-shaped)
  free normalizer alone scored 14/20 acceptable on the same read

1,000 rows processed
  974 shipped a copy-ready value
   26 abstained and routed to review (placeholder guard: 19 on input, 7 on output)
    0 recorded as an abstain that was really a truncation

  11 rows flagged: cleaned name does not match the domain -- review before sending

copy should reference: company_clean
abstained rows routed to: <the review view the installer named>
```

## What this skill does not claim

- **Quote the score as "98/100 on a 100-row, A-heavy, English-majority sample" — never as "98
  percent".** The benchmark corpus is alphabetically skewed toward names starting with a digit or
  the letter A. A hundred rows is enough to lock a prompt. It is not enough to support a general
  accuracy figure.
- **That verdict covers a script path calling a model API**, at roughly one second and $0.15 per
  1,000 rows. **The Deepline `ai_inference` play column has never been run.** Same prompt, same model,
  different runtime. Build it, read the 20-row sample, and fix what you find before running a list.
- **The placeholder guard is a mitigation to re-measure, not an independent result.** With the guard
  `gpt-4o-mini` scores 10/10 on the abstain probe — but the blocklist was written against those same
  ten rows. Re-measure it on the installer's own junk strings.
- **The free path scores 89/100 and cannot judge itself.** It reports `confidence: unknown` on every
  row by design. Zero review flags from a regex-only run means nobody has looked.
- **A misspelling in the source survives cleaning**, deliberately: fixing it would mean inventing a
  word, which rule 10 forbids. Accepted trade-off, caught by a spell-check on the review list.
- **Acronym-versus-word is undecidable from the string alone** for 4-to-6-letter all-caps tokens.
  Residual error class, about 1%. Accept it or check the website.
- **Two legitimate brands in one string** — a parent plus an operating brand — is genuinely
  ambiguous. The model picks one and reports `high` when it should report `low`. Sendable either way;
  review the rows where the chosen name does not match the domain.
- **It cannot tell you the row is stale.** A correctly cleaned name for a company the person has left
  is still a correctly cleaned name. That is a list-freshness problem.
- **Roughly 7.8% of rows in shared contact data have a name and a domain that describe different
  companies.** Measured, not fixed here. Flag it and resolve upstream — and any database lookup you
  add must use an **exact** domain match, never a fuzzy one.
- **No reply, meeting or conversion rate is claimed**, and no benchmark for one exists here.

## What good looks like

- Someone was talked out of the AI pass when their list did not need it, and the decision is
  written down.
- The 20-row read happened on the installer's own list, and a human read it.
- The abstain count is non-zero on a real list. Roughly 1–3% of rows are junk strings that should
  abstain; zero abstains means the guard is not running.
- No row anywhere carries `N/A`, `your team`, `your company` or a tagline as the company name.
- `Unknown Arts` and `Retired - BTH Bank` style names are still present — a substring blocklist
  would have deleted them.
- The raw value sits beside the cleaned one, so a human can see the source string.
- Rows where the name and the domain disagree are flagged, not silently sent.
- Running it twice on the same rows gives the same values.

## Rules

1. **The free normalizer is the default.** the AI pass runs only when all three escalation
   conditions in Step 1 are true, and the decision gets recorded.
2. **Abstain is the empty string.** Never `N/A`, never a generic substitute, never a guess.
3. **The placeholder guard runs on input AND output, on every model and every runtime.** It is what
   makes the cheaper model safe here.
4. **Never match placeholders on substrings.** Whole normalised string only, plus the
   `selfemployed` prefix.
5. **A truncated response is a retry, never an abstain.** Check the finish reason before recording
   an empty value — three of a hundred rows fooled the author's first draft.
6. **Match the token cap to the model class**: 200 for mini, 2000 for nano.
7. **Never invent a word or correct a spelling.**
8. **Keep parentheses that are part of the brand.**
9. **Do not shorten the prompt**, and specifically keep the example block — cutting it triples the
   cost per thousand rows by dropping under the cache floor.
10. **Set the JSON response format and pass no temperature.**
11. **Read 20 sampled values before running the list.** A gate that cannot evaluate true drops the
    whole list and looks exactly like "no rows qualified".
12. **Report the denominator with every rate**, and never state the benchmark as a percentage.
13. **This skill writes one column and sends nothing.** What happens to excluded rows is the
    installer's call.
