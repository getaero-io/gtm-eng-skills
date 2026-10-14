---
name: job-posting-language-signal
description: |
  Produce a copy-ready clause about a role a company is currently hiring for, selected by language
  the sender cares about — "cold call", "outbound prospecting", "Salesforce" — so the angle is
  "you're hiring for this and that is exactly what we do". Emits a freshness-gated clause that
  blanks when the only posting is stale, plus the evidence URL and posted date. Use whenever someone
  asks: they're hiring, who is hiring SDRs, companies hiring for X, find the hiring signal, what
  roles are they hiring for, or the job description mentions. Do NOT use it as a headcount or
  growth-rate signal, to build a market-wide list of every company hiring (that is a different
  endpoint and a different job), or as proof a role is still open — nothing here can know that. It
  writes its own output columns and sends nothing. Runs on Deepline (theirstack_job_search with a
  server-side description filter, deeplineagent for the clause).
ported_from: clay-run/clay-skill-creator/skills/eric-nowoslawski/job-posting-language-signal
category: signals
personas: [gtm-engineer, sales-development]
mechanism: logic-only
touches: writes-own-output
keywords: [cold-email, lead-scoring]
---

# Job posting language signal (filter server-side, or you will conclude the signal does not exist)

**The single most important thing here is a measurement, and it will save someone a week.** Most
jobs APIs return a title, a date, a URL and a summary per posting — **but never the full job
description.** The description is only reachable *through the filter*. Measured on the same 8
companies with the same 8 keywords (author's script path against a jobs API, 2026-08, before the
Deepline port):

| Approach | Companies matched |
|---|---|
| scanning the **returned fields** locally | **1 of 8** |
| the identical keyword set passed to the **description filter** | **5 of 8** |

**If you scan locally you will conclude the signal does not exist in your market.** It does. You
just cannot see it from the fields you got back.

On Deepline, `theirstack_job_search` does declare a `description` field (markdown) on each returned
job, plus `matching_phrases` / `matching_words`. The rule holds anyway: a local scan only sees the
page you paid for (billed per returned job), while the server-side filter scans every posting in
the window. Filter server-side, and use `matching_phrases` as the evidence of which phrase hit.

**The second thing worth knowing: nothing here can tell you a role is still open.** A posted date is
when the provider *observed* the posting, not proof the job is live. So the clause bound into copy is
suppressed past 30 days — a blunt proxy that kills some genuinely open roles on purpose. Step 4
explains what that costs, with the numbers.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The rows** | a CSV or Customer DB table with a bare lowercase `company_domain` per row | no default |
| **`company_name`** | the company column | **required** — the mandatory name-match gate in Step 3 needs it. Without it, a posting from the wrong company can ship as this company's |
| **The keyword set** | the phrases whose presence in a job description makes the row interesting | **ask, set once per campaign, not per row.** And **enumerate the plural and gerund forms yourself** — see Step 2. There is no sensible default: the phrases are the sender's offer |
| **`role_titles`** | title filters, if they want to narrow further | not required. Description language is the signal; titles are a secondary narrowing |
| **Detection window** | how far back to look for a posting | default **60 days** to detect |
| **Copy window** | how fresh a posting must be to appear in a sentence | default **30 days**, and this is the one bound into copy. Loosening it is what ships a clause about a role that closed |
| **Whether this is a hiring-only segment** | whether rows with no posting should be excluded | default: **keep them and drop the clause.** If they want hiring-only, exclude **at list-build time, never at send time** |
| **The jobs data source** | a Deepline jobs tool with a server-side description filter | default **`theirstack_job_search`** (`job_description_contains_or`, `company_domain_or`, `posted_at_max_age_days`). Alternatives: `bloomberry_search_job_postings` (`keyword` with `OR`, `domain`, `begin_date` — which defaults to 2020-01-01, so always pass it) or `sentrion_company_jobs_search` (`job_keywords`, `published_after`, `company_domain`). Pick one per campaign |
| **Which model writes the clause** | the `deeplineagent` model | a **non-reasoning** model. See Step 3: reasoning budget burn produces empty content on exactly the rows that had postings |

## What this skill touches

- **Reads** — the domain and company name on each row, and the company profile and job postings your
  jobs source returns for them.
- **Writes** — six of its own output columns: the freshness-gated clause, the ungated clause, the
  role named, the evidence URL, the posted date and a confidence flag.
- **Never** — claims a role is still open, quotes a raw requisition title into copy, uses a posting
  from a company whose name did not match, drafts or sends a message, enrols anyone, or writes to a
  CRM.
- **Halts** — Step 2 other, Step 4 sample-review.
- **Derived from** — the author's graded 8-company live test, plus phrase-recall counts measured
  across a whole jobs index over a 30-day window. The graded path is a script calling a jobs API and
  a model API, run before this skill was ported to Deepline; see the claims section.

## Declared outputs

| Field | Type | Example | Bind into copy? |
|---|---|---|---|
| `job_posting_line_safe` | string, ≤90 chars, freshness-gated | `you're hiring an account executive for private equity` | **yes — this is the only one** |
| `job_posting_line` | string, **ungated** | same text, regardless of age | **no — audit and debugging only, never in a send** |
| `job_role_named` | string | `account executive for private equity` | no |
| `job_evidence_url` | string | the posting URL | no |
| `job_posted_date` | date | — | no |
| `job_confidence` | `high` / `low` | `high` | no |

**Bind copy to the gated field. Building the table without the gate rebuilds the one failure in the
live test** — a clause quoting a 53-day-old posting for a role that had already gone from the
company's own board.

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json` (missing CLI: `npm install -g deepline && deepline auth register
--wait auto`). Read the jobs tool's live contract and price, free:
`deepline tools describe theirstack_job_search --json`. Confirm the input CSV with
`deepline csv show --csv <path> --summary`. Name the org and file, then say what this run touches:
*"this adds six columns to <the file you named>, reads job postings per domain, and sends nothing."*
If a check fails, name it and stop.

**If you call a jobs API directly through a `generic_http` tool instead, send a browser user
agent.** Several of these APIs sit behind a CDN that rejects default runtime agents while allowing
an ordinary command-line client.

## Step 1 — Build the keyword set, and enumerate the forms yourself

Description filters typically match **whole phrase tokens**, case-insensitively — no substring, no
stemming. Measured over one 30-day window of a whole jobs index:

| Phrase | Matches |
|---|---|
| `cold call` | 996 |
| `cold calling` | 2,065 |
| `cold outreach` | 2,339 |
| `outbound prospecting` | 2,796 |
| `cold email` | 1,877 |
| `coldcall` | **0** |

**`cold call` matching fewer postings than `cold calling` is the proof.** Under substring matching
the shorter phrase would be the larger set. It is not, so you must write out the plurals and the
gerunds. A 5-phrase set reached **59.8% recall** where an 8-phrase set reached **67.4%**.

**Do not reach for a classifier before you have measured recall.** Run the counts first. **Under 60%
recall means the keywords are wrong, and a model will not save them.**

## Step 2 — Filter server-side, and check that the filter did anything

Request the company's postings **with the keyword set passed to the description filter** and the
detection window inside the date field. On `theirstack_job_search`:

```json
{ "company_domain_or": ["<domain>"],
  "job_description_contains_or": ["cold call", "cold calling", "cold outreach", "outbound prospecting"],
  "posted_at_max_age_days": 60,
  "order_by": [{ "field": "date_posted", "desc": true }],
  "limit": 3 }
```

`job_description_contains_or` matches whole words with word boundaries, case-insensitive unless a
pattern is uppercase — the phrase-token behaviour Step 1 measured. Billing is per returned job
(0.56 Deepline credits/result at the time of porting; zero matches bill zero), so keep `limit`
small: you need the newest matching posting, not all of them.

**Unknown keys are silently stripped, and you get an unfiltered result set that looks successful.**
So before trusting any filter: **compare the result counts with and without it** (on TheirStack,
`include_total_results: true` with `limit: 1` returns `metadata.total_results`). If a filter appears
to do nothing, the key is misspelled.

**Halt here (`other`).** Report the with-and-without counts for the keyword filter, so the installer
can see it is actually filtering rather than returning everything.

**A market-wide jobs search is a different job.** The same tool without `company_domain_or` (or
`deepline_native.industry_job_openings` as a standing monitor) answers "who is hiring for this", not
"does this one domain have a posting". Use it for discovery — pull every posting matching your
filters, paginate, and join back to a TAM on the company identifier. That is list building, not this
skill.

**No cache, by decision.** The path is one small paid search plus a cheap line write, so re-hit the
source every run. If a big list feels expensive, **dedupe the input on bare domain for that run**
instead of caching. In a play, rows already filled in the Customer DB table are reused on rerun; pass
a short `staleAfterSeconds` on the tool call if you want a rerun to refresh them.

## Step 3 — Name-match, then write the clause

**The name-match gate is mandatory and runs on every row.** Compare the company name your jobs source
returned (`company` on each TheirStack job) against the company name on your row, before using any
posting from it. Domain-to-profile
resolution lands on the wrong company often enough that without this gate a clause can quote another
company's job.

Then the model rewrites the title into copy. **That rewrite is the only thing the model step exists
for**, and it is why raw titles cannot be used directly:

```
Partner Development Representative | Advisory and Services
  ->  a partner development representative
```

Rules the clause follows:

- Starts with the word **"you"**, lowercase, no trailing period.
- **12 words or fewer**, plain language, no em dashes.
- No requisition codes, no pipes, no bracketed location suffixes.
- It must read grammatically inside `Saw <clause>.` — **test every generated value in that exact
  frame.**

**There is nothing for the model to fabricate here**: it quotes a title from a payload it was handed
and returns the source URL. The live test confirmed it — **every evidence URL grepped back to the raw
source verbatim, zero inventions.** That is why there is no verifier pass on the claim.

**Empty content with a length finish reason is a retry, never an abstain.** Watch for a specific
trap: reasoning budget burn produces empty content **on exactly the rows that had postings**, while
rows with nothing to say succeed — **so the abstains look perfectly healthy while the signal
silently disappears.** Use a non-reasoning model, or low effort with a generous cap. In a play this is a `deeplineagent`
column with a `jsonSchema` (`{ "role_named": string, "clause": string }`). Transport
errors get their own retry with backoff; they are not verdicts either.

## Step 4 — Apply the freshness gate, and know what it costs

Detect on 60 days. **Suppress the clause in copy when the posting is older than 30 days.** This is a
**formula, not a model call**, and the gated field is the one copy binds to.

**What that costs, measured on the live-test set: 2 of the 5 generating rows blanked.** One was 53
days old and correctly killed — the role was already gone from the company's own board. The other was
**49 days old and verified genuinely open**, and the gate kills it anyway.

**That second row is the price of a blunt proxy: a real open role, killed by its age.** A source that
exposes a true "is this still open" flag would keep it. The age proxy is what you have until one does.

**Halt here (`sample-review`).** Show 10 rows: the posting found, its date, whether the name-match
passed, the ungated clause and the gated one. Read them in the `Saw ___.` frame.

## Step 5 — Handle the blanks, and plan for the real rate

If the clause is empty, **keep the row and drop the clause.** Do not exclude the row unless the
sender asked for a hiring-only segment — and then exclude at list-build time, not at send time.

**This variable can never be mandatory in copy.** Expect roughly **60% of a healthy B2B software TAM
to produce a line before the freshness gate, and 35 to 40% after it.** Any row whose only posting is
31 to 60 days old blanks by design.

## Step 6 — Deliver

Report: rows with a posting, rows that passed the name-match, rows that generated a clause, and rows
the freshness gate suppressed — separately, with denominators. Name the gated field copy should bind
to, and say plainly that the ungated field is for audit only.

## Representative output

Invented examples for shape only; no real company or posting appears. Keyword set:
*cold call · cold calling · cold outreach · outbound prospecting · cold email · sales development ·
prospecting · SDR.*

### The clause, row by row

| domain | posting found | age | name match | `job_posting_line_safe` | what happened |
|---|---|---|---|---|---|
| `northstar-example.com` | Account Executive, Private Equity \| Req 4417 | 6d | pass | `you're hiring an account executive for private equity` | requisition code stripped in the rewrite |
| `vantageloop.example` | Sales Development Representative (Remote - EMEA) | 18d | pass | `you're hiring sales development reps in EMEA` | bracketed suffix rewritten, not quoted |
| `meridian-example.com` | Partner Development Representative \| Advisory | 27d | pass | `you're hiring a partner development representative` | pipe and second clause dropped |
| `harborline.example` | Outbound Account Executive | **49d** | pass | `` | **gate suppressed it — and this role was verified genuinely open** |
| `pinegrove.example` | Enterprise AE | **53d** | pass | `` | gate suppressed it. Correctly — the role is gone from their board |
| `brightfold.example` | Senior SDR | 11d | **FAIL** | `` | profile resolved to a different company. Name-match gate stopped it |
| `atlas-example.com` | — | — | — | `` | no posting matching the keyword set. Correct abstain |
| `cedarworks.example` | — | — | — | `` | no posting at all in the window. Correct abstain |

### The run summary

```
8 companies
   7 usable (87.5%)   5 generated a clause, 3 abstained -- all 3 abstains correct
   1 failure          quoted a 53-day-old posting that was no longer live
                      ^ this is the failure the freshness gate now prevents

keyword filter, server-side vs local scan on these same 8 companies:
   filtered server-side  5 of 8 matched
   scanned locally       1 of 8 matched      <- do not scan locally

freshness gate:  2 of the 5 generating rows suppressed
   53d  correctly killed -- role gone from the company board
   49d  killed anyway -- VERIFIED still open. the cost of an age proxy

name-match gate: stopped 1 row using another company's posting

copy binds to: job_posting_line_safe   (never job_posting_line)
```

## What this skill does not claim

- **7 of 8 usable, and the honest breakdown matters more than the rate:** 5 rows generated a line, 3
  abstained, and **all three abstains were correct.** The single failure quoted a 53-day-old posting
  that was no longer live — which is exactly what the freshness gate was added to prevent. Eight
  companies is enough to find that failure. It is not a market study.
- **Nothing here knows whether a role is still open.** A posted date is an observation date. The
  30-day gate is a proxy, and it is blunt in both directions: it correctly killed one dead role and
  **killed one verified-open role** on the same test set.
- **Plan on 35 to 40% coverage after the gate, not 60%.** Roughly 60% of a healthy B2B software TAM
  produces a line before the gate. Rows whose only posting is 31 to 60 days old blank by design, so
  **this variable cannot be mandatory in copy.**
- **Recall depends entirely on the phrase set the installer wrote.** Measured: 59.8% on five phrases
  against 67.4% on eight, over the same window. A thin phrase set is not a signal that the market is
  quiet.
- **The phrase counts come from one index over one 30-day window.** They prove phrase-token matching
  rather than substring matching, which is the point; they are not a forecast of anyone's market.
- **The verdict covers a script path** calling a jobs API and a model API. **The Deepline play build
  has never been run end to end.**
- **This is not a headcount or growth signal.** One open req is not expansion, and the count of
  postings here is the count that matched a phrase filter, not the company's real hiring volume.
- **No reply, meeting or conversion rate is claimed**, and no benchmark for one exists here.

## What good looks like

- The keyword filter was verified to be filtering — counts compared with and without it — before
  anyone trusted a result.
- The phrase set includes plurals and gerunds, and someone measured recall before proposing a
  classifier.
- Nobody scanned returned fields for description language.
- Copy binds to the gated field, and the ungated field exists only in the audit view.
- The suppressed-by-freshness count is reported separately from the no-posting count. They are
  different things.
- The name-match gate fired at least once on a list of any size.
- Every clause reads correctly inside `Saw ___.` and none contains a requisition code or a pipe.
- The abstain count looks plausible *and* someone checked that rows which had postings produced
  clauses — the reasoning-burn failure makes healthy abstains out of lost signal.

## Rules

1. **Filter server-side. Never scan returned fields for description language.** 1 of 8 against 5 of 8
   on identical keywords.
2. **Bind copy to the freshness-gated field, never the raw one.**
3. **The name-match gate runs on every row** whose posting came from a domain-to-profile resolution.
4. **Never claim a role is still open.** The date is an observation, and the gate is a proxy.
5. **Enumerate plural and gerund forms yourself.** Matching is by whole phrase token, not substring.
6. **Measure recall before reaching for a classifier.** Under 60% means the keywords are wrong.
7. **Compare counts with and without a filter before trusting it.** Unknown keys are stripped
   silently.
8. **Raw job titles are not copy.** No requisition codes, no pipes, no bracketed suffixes.
9. **Test every generated value inside the exact frame it will render in.**
10. **A length finish reason is a retry, never an abstain** — and watch for reasoning burn, which
    empties exactly the rows that had signal while the abstains look healthy.
11. **Send a browser user agent.**
12. **No cache.** Dedupe the input on bare domain instead.
13. **Exclude non-hiring rows at list-build time, never at send time.**
14. **This skill writes its own columns and sends nothing.**
