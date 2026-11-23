---
name: funding-signal-line
description: |
  Produce a copy-ready sentence about a company's funding round, and the list filters that select
  companies which have ever raised or raised recently. Emits a COMPLETE sentence including the
  leading "Saw" and the trailing period, so a row with no evidenced round renders as nothing at all
  rather than as a broken line. Use whenever someone asks: raised a round, recently funded,
  companies that raised, build me a Series A list, VC backed, post-funding outreach, or who just
  raised. Do NOT use it for a "raised in the last 30 days" list — that path is documented and
  explicitly unsolved here. Do NOT use it to quote total funding, a valuation, investor names or a
  date, all of which are wrong often enough to be measured. Runs on Deepline company-data and
  funding-round tools; it writes its own output columns and sends nothing.
ported_from: clay-run/clay-skill-creator/skills/eric-nowoslawski/funding-signal-line
category: signals
personas: [gtm-engineer, sales-development]
mechanism: logic-only
touches: writes-own-output
keywords: [cold-email, lead-scoring]
---

# Funding signal line (a fabricated round is the one failure nobody can fix after it sends)

**The insight that shapes everything here: the model writes wording, never eligibility.** Whether a
company raised, at what stage, and whether it was recent enough are decided in code against a
structured source. The model's only job is to turn a proven fact into one grammatical clause. Every
time that boundary was crossed in testing, the result was a confident sentence about money that
never went into the company — and a founder notices that immediately.

Two code filters do the real work, and both were measured removing real errors:

- The **domain-equality guard** removed **1 wrong company out of 10**. A website filter matches
  *other* listed websites too, so a vendor that lists your target as a customer can win the match —
  observed live, with a total count of 1 and no warning.
- The **equity-stage and 12-month filter** removed **3 misleading "latest rounds" out of 6**. One
  company's latest event was a **$300,000,000 secondary sale**. Existing shareholders selling is not
  money the company raised.

**And the most generally useful thing in this skill has nothing to do with funding.** See Step 4.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The rows** | a CSV (or a Customer DB table) with a bare lowercase `domain` per row — no `www`, no scheme | no default. Domain is the only key that works; a company name alone resolves to the wrong company often enough that the guard exists to catch it |
| **`company_name`** | the company column, if they have one | not required, and used **only** for the abstain log and QA — never for matching |
| **Which recency window** | how many months old a round may be and still be worth naming | the author used **12 months** and the filter is built around it. Loosening it is what puts a stale round in a first line; say so if they ask for more |
| **Whether private-equity rounds count** | whether a PE minority stake should read as a raise | **default excluded**, because buying shares from existing holders is not money into the company. Toggleable for a PE-adjacent offer — note the override |
| **The company-data source** | which Deepline funding tool supplies per-round evidence: `aviato_get_company_funding_rounds` (takes `website`; 0.14 credits per call) or `predictleads_company_financing_events` (takes `company_id_or_domain`; 0.56 credits per call), prices read from `deepline tools describe` on 2026-09-30 | ask, and re-read the price with `describe` before quoting it. Without a per-round source there is no evidence, and this skill does not run |
| **Which model writes the clause** | the exact AI Gateway model ID passed to `ai_inference` | the author graded one model on this exact prompt. **Never ship a model you have not graded on it** — a cheaper model that has not been checked against the abstain rule, the character cap, the lowercase-first rule and the no-date rule is untested, and an $0.11 saving per 1,000 rows does not cover that |
| **How the email body consumes the variable** | whether the whole sentence sits on its own line, or the list is split at upload | **ask, and read Step 4 before answering.** This is where the commonest catastrophic failure lives |
| **What happens to abstaining rows** | keep them with the sentence collapsed, or exclude them | default: keep them. Exclude only when the campaign angle **is** the round |

## What this skill touches

- **Reads** — the domain on each row, and the company and funding records your company-data source
  returns for it.
- **Writes** — four of its own output columns: the wrapped line, the clause, the evidence URL and a
  confidence flag. It does not modify any other field on the row.
- **Never** — names a month, a date, a year or a season; quotes total funding, a valuation or
  investor names; treats a secondary sale, a debt facility or a PE stake as a raise; drafts or sends
  a message; enrols anyone; or writes to a CRM.
- **Halts** — Step 2 sample-review, Step 4 send-approval.
- **Derived from** — the author's graded 10-row adversarial test of the copy lane, plus a measured
  segment scan (76% of a US software 50–500 segment had raised at any stage, 65% at an equity stage).
  The graded path is a script calling a company-data API and a model API; see the claims section.

## Declared outputs

| Field | Type | Example | Null? |
|---|---|---|---|
| `funding_line` | string, max 90. **Written by code, never by the model** | `Saw you raised $52M in the Series B.` | no — `""` |
| `funding_clause` | string, max 80. Written by the model | `you raised $52M in the Series B` | no — `""` |
| `funding_evidence_url` | string, max 300 | the round's source URL | no — `""` |
| `funding_confidence` | `high` / `low` | `high` | no. Always `low` when the line is empty |

**Two fields, two jobs, and keeping them straight is what makes the gate work.** The model writes
the clause: lowercase first letter, no trailing period, under 80 characters, plain language, no em
dashes, and it must read grammatically inside `Saw <clause>.` Then **deterministic code** wraps it:
`"Saw " + clause + "."` — and when the clause is empty, the line is empty too. The model never
writes the wrapped field, so the wrapping cannot be forgotten or hallucinated.

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json`. If the CLI is missing: `npm install -g deepline && deepline auth
register --wait auto`. Run `deepline tools describe <funding tool> --json` and confirm it is callable
and connected, and `deepline csv show --csv <path> --summary` to confirm the input has a `domain`
column. Name them, then say what this run touches: *"this adds four columns to <the file you named>,
reads company and funding records for each domain, and sends nothing."* If a check fails, name it and
stop.

The run is one Deepline play over the CSV (`deepline plays run <file>.play.ts --input
'{"csv":"<path>"}'`, authored per the `deepline-plays` skill): one `.withColumn` for the funding
lookup, one `run_javascript` column for both guards, one `ai_inference` column for the clause, and
one `run_javascript` column that wraps it. Pilot on the 10-row sample before the full file.

## Step 1 — Build the list, or take the list you were given

**If they want a funded-companies list**, build it with `crustdata_v3_company_search` (filter fields
include `funding.last_round_type` and `funding.last_fundraise_date`; read the legal values with
`crustdata_v3_company_search_autocomplete` first), adding an equity-stage filter to their ICP
criteria plus a recency window of 365 or 180 days. The equity stage set below is the author's
source vocabulary; map it onto the round-type values the tool actually returns before filtering:

```
Pre seed · Seed · Series unknown · Series A · Series B through Series E-J
Angel · Corporate round · Convertible note · Equity crowdfunding
```

Measured on a US software 50–500 segment: **76% had raised at any stage, 65% at an equity stage.**

**If a recency filter returns HTTP 400**, check the body — some sources return `400` with a
`NO_RESULTS` payload instead of an empty list. **Treat that as zero matches, not an outage.** A
client that raises on any 400 looks broken when it is working.

## Step 2 — Get the evidence, and run both guards

Per row, look the company up by domain with the chosen funding tool and read its list of rounds.
Round-type labels and the date field name differ between providers — read them off the first
response and map them onto the equity and non-equity sets below before trusting either guard. Then,
**in code, not in the model**:

**Guard 1 — domain equality.** Assert that the returned company's domain equals the domain you
asked for. There is often no strict-domain filter to request, so this has to be checked after the
fact. **Removed 1 wrong company out of 10 on the test set.** Never skip it.

**Guard 2 — equity stage, then recency, in that order.** Drop every non-equity event first:

```
Secondary market · Private equity · Debt financing · Grant
Undisclosed · Non equity assistance · Post IPO (any) · Product crowdfunding
```

**Then** require the newest survivor to be 12 months old or less. Order matters: filter before you
sort for the latest event, or a large recent secondary sale wins and gets called a raise.
**Removed 3 misleading "latest rounds" out of 6.**

**If no company record came back at all, the row abstains.** That is the correct outcome for a
signal you cannot evidence. Do not add a paid enrichment fallback — it is a paid per-company lookup and does not
carry funding fields anyway.

**Halt here (`sample-review`).** Show 10 rows: the domain asked for, the domain returned, the event
that survived both filters, and the clause. Read them.

**Pace lookups at about one request per second.** Zero rate-limit errors were observed at 0.8
requests per second across 37 requests.

## Step 3 — Write the clause, with the wording rules the measurements forced

The model (`ai_inference` with a `jsonSchema` holding one `funding_clause` string) sees the surviving
round and writes one clause. What it must never include, and why —
each of these is a measured error, not a style preference:

- **No month, date, year or season.** The `raised_at` field is systematically early. Measured wrong
  by **15 days, one month, and two months** on three companies.
- **No total funding.** Source totals fold in debt facilities and secondary sales. The **round
  amount** is the number that held up — exact on 4 of 4.
- **No valuation, no investor names.**
- **Blank out database bucket labels.** `Series E-J` and `Series unknown` are index buckets, not
  round names. Fall back to the word "round".
- **If an amount looks absurd, drop the amount and name only the round.** Headline parsing produced
  **$600,000,000,000** from an article about AI budgets, and `0.261` USD tagged as debt.

**An empty model response with a length finish reason is a retry, up to three times. Never record it
as an abstain.** A vendor timeout is an `error`, and an errored row leaves every hit-rate
denominator — **an API error is never a data verdict.**

## Step 4 — Wire the email body correctly. This is the step that ships broken sends.

**Spintax is a RANDOM chooser, not a conditional.** This is the most generally useful thing in this
skill and it applies to every personalization variable in every campaign, not just this one.

`{Saw {{funding_line}}. |}` picks a branch at random on every row with **no knowledge of whether the
variable is populated.** On abstaining rows it renders `Saw .` about half the time. On rows that DO
have a line it **throws the personalization away** about half the time. Both failures at once.

**Spintax can never be used as an if-populated gate for any variable.** Word-level spintax for
wording variety is unrelated and still fine — spintax is for variety, never for conditional content.

Exactly two mechanisms work. Pick one per campaign:

1. **Default — the self-erasing variable.** The entire sentence lives in the variable, which is why
   it carries the leading "Saw" and the trailing period. The body line is `{{funding_line}}` alone
   on its own line. An empty variable renders nothing, so an abstaining row loses that sentence and
   the rest of the email is untouched.
2. **Split at upload.** Partition into populated and empty, and upload two campaigns or variants —
   one with the sentence hard-coded, one without. Use this when the funding angle changes the whole
   email rather than one line, or when the non-empty rate is low enough that a single body would
   read oddly for most recipients.

**Halt here (`send-approval`).** Before anything goes out: **preview one abstaining lead** and
confirm the paragraph collapses cleanly with no double blank line. Then preview one populated lead.

## Step 5 — Deliver, and report both numbers

Report the usable rate **and** the non-empty rate separately, with denominators, plus every row that
abstained and why. Errored rows are reported separately and excluded from both denominators.

## Representative output

Invented examples for shape only; no real company, round or amount appears.

### The funding columns, row by row

| domain | `funding_clause` | `funding_line` | `funding_confidence` | what happened |
|---|---|---|---|---|
| `northstar-example.com` | `you raised $52M in the Series B` | `Saw you raised $52M in the Series B.` | high | equity round, 4 months old |
| `vantageloop.example` | `you raised a Series A` | `Saw you raised a Series A.` | high | amount looked implausible, so the round is named without it |
| `meridian-example.com` | `you closed a round` | `Saw you closed a round.` | high | source said `Series unknown`, a bucket label — fell back to "round" |
| `harborline.example` | `` | `` | low | latest event was a secondary sale — guard 2 dropped it |
| `pinegrove.example` | `` | `` | low | latest equity round is 3 years old — outside the window |
| `atlas-example.com` | `` | `` | low | lookup returned a different company — guard 1 dropped it |
| `brightfold.example` | `` | `` | low | no company record at that domain. Correct abstain |

### The run summary

```
10 rows, adversarial test set
   8 usable   (2 lines written, 6 correct abstains)
   2 misses   both COVERAGE misses, not false claims
   0 false claims                      <- the bar that matters

guard 1 (domain equality)      dropped 1 wrong company
guard 2 (equity stage + 12mo)  dropped 3 misleading "latest rounds"
   of which: 1 secondary sale, 1 private equity, 1 outside the window

body wiring: self-erasing variable, {{funding_line}} alone on its line
QA: previewed 1 abstaining lead -- paragraph collapsed cleanly
```

## What this skill does not claim

- **Two bars, and they measure different things: 8/10 usable and 8/8 claims correct.** Claim
  correctness is scored as true claims divided by **rows where a claim was emitted** — a company
  that never raised, correctly abstained on, is a correct outcome and **leaves the denominator
  entirely.** It is not a miss. The bar binds on truthfulness *when the signal exists*, because a
  fabricated round is the one failure nobody can fix after it sends. Both misses were coverage
  misses: no record for one domain, and a two-month date error pushing one round outside the window.
- **Only 2 of 10 rows produced a non-empty line, and that number does not transfer.** The test set
  was deliberately adversarial — three bootstrapped companies and three whose last round is years
  old. On a list already filtered to a 365-day funding window, every row has a funding event by
  construction, so the non-empty rate is governed by the stage filter and the window, not by source
  coverage. **That rate was not measured. Measure it on your first real campaign before letting copy
  depend on the variable being populated.**
- **The list-building path was not graded end to end.** The segment percentages are real; the
  quality of a list built that way was not scored.
- **A "raised in the last 30 days" list is not solved here and must not be described as working.**
  The freshest feed tested had real dates but only 9 of 25 rows carried a clean company name and
  **none carried a domain**. The cleanup-and-resolve step for it is untested, and so is the
  expensive web-research alternative. Deepline's `prebuilt/funding-updates` play pages a
  funding-rounds radar by discovery time (`since`, `limit` up to 100); whether its rows carry a
  domain, and how its rows survive both guards, was not tested, so it does not change this verdict.
- **The verdict covers a script path** calling a company-data API and a model API, at about three
  seconds and $0.22 per 1,000 rows, measured before this skill was ported to Deepline. **The
  Deepline play build has never been run**, and the funding tools named above are not the
  author's source; the guard counts above are the author's, not measurements of those tools.
- **A company that clearly raised may get an empty line**, because the index lags 3 to 4 months. That
  is expected and correct. **Do not "fix" it by loosening the guards.**
- **Round amounts held up exactly on 4 of 4; dates did not.** That asymmetry is why the line names
  an amount and never a date.
- **No reply, meeting or conversion rate is claimed**, and no benchmark for one exists here.

## What good looks like

- The abstain count is non-zero on any real list, and nobody has tried to loosen a guard to raise it.
- Both guards report having dropped something on a list of any size. A guard that never fires is a
  guard that is not running.
- No sentence anywhere names a month, a date, a total raised, a valuation or an investor.
- No email body uses spintax around the variable. Someone previewed an **abstaining** lead and
  watched the paragraph collapse cleanly.
- Every emitted line has an evidence URL beside it that a human can open.
- Errored rows are reported as errors, not folded into the abstain count.
- Rows where the returned domain differed from the requested one are visible, not silently dropped.

## Rules

1. **The model writes wording. Code decides eligibility.** Never the other way round.
2. **Both guards are mandatory**: domain equality, then equity-stage filtering *before* recency
   sorting.
3. **Abstain is the empty string, and an abstain is a correct outcome**, not a coverage failure.
4. **Never name a month, date, year or season.** The source date is systematically early.
5. **Never quote total funding, a valuation or investors.** Quote the round amount only.
6. **A secondary sale, a debt facility, a grant and a PE stake are not raises.** PE is excluded by
   default; overriding it gets logged.
7. **Blank database bucket labels** and fall back to the word "round".
8. **Spintax is a random chooser and must never gate a personalization variable** — in this skill or
   any other.
9. **Preview an abstaining lead before sending.**
10. **A length finish reason is a retry, up to three. An API error is never a data verdict** and
    leaves every denominator.
11. **Treat a 400 carrying a no-results payload as zero matches, not an outage.**
12. **Pace lookups at about one per second.**
13. **Never ship a model you have not graded on this prompt.**
14. **This skill writes its own columns and sends nothing.**
