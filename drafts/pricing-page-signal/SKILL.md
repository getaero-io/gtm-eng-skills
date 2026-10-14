---
name: pricing-page-signal
description: |
  Decide whether a company publishes public self-serve pricing, and extract its plan tiers, price
  points and the axis its tiers differ on. Produces a structured filtering record per domain; the
  copy-ready price clause is OFF by default and runs only when a campaign brief asks for it. Use
  whenever someone asks: do they have a pricing page, is their pricing public, filter out
  enterprise quote-only companies, what do they charge, find their plans, or split self-serve from
  sales-led. Do NOT use it to learn what a prospect actually pays after negotiation, to read private
  rate cards, marketplace listings or ecommerce SKU prices, or to decide whether a company is in
  your ICP. Runs on Deepline's HTTP, scrape and inference tools; it writes its own output columns
  and sends nothing.
ported_from: clay-run/clay-skill-creator/skills/eric-nowoslawski/pricing-page-signal
category: research
personas: [gtm-engineer, sales-development]
mechanism: logic-only
touches: writes-records
keywords: [lead-scoring, cold-email]
---

# Pricing page signal (bones by default, because a price in a stranger's inbox is a claim)

**The insight that sets the default: almost everyone who wants this only ever wanted the filter.**
The valuable output is the structured record — is pricing public, is there a free tier, is it
per-seat or usage, is enterprise quote-only. That is internal work, and it is right 8 times in 10
with the existence check alone right 10 times in 10.

The one-line price clause is the **weakest** part of the output and it is **off by default**. It
measured usable on 9 of 10 in a clean regrade and 6 of 10 on an earlier corrected run — a 70-to-90%
field. **A price a prospect cannot find on their own site destroys the message**, so the clause is
opt-in, stripped at the output boundary unless the brief explicitly asks.

**And there is a second distinction that matters more than anything else here.** See the outputs
section: `quote_only` and `unknown` are not the same thing, and collapsing them is how a campaign
silently deletes real prospects because of a network error.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it,
never substitute a plausible default, and where an answer does not exist say which step becomes
unavailable rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The rows** | a CSV (or a Customer DB table) with a bare lowercase `domain` per row — no scheme, no `www` | no default. The domain is the only input that works |
| **`company_name`** | the company column, if they have one | not required; it improves the optional copy line and nothing else |
| **Filter or route** | what a `pricing_public: false` row should do — leave this campaign, or go to a different one | **ask once, up front.** If the brief is silent, **route rather than delete**, and say so in the handoff: reversing a routing choice is cheap, reversing a deletion is not |
| **Whether the copy clause is wanted** | whether any sentence will quote a price to a stranger | **default OFF.** Turning it on raises the accuracy bar this skill is held to — see the claims section. Ask explicitly; never infer it |
| **How the pages get fetched** | `generic_http_request` (free; supports `HEAD` and `GET`) for the path sweep and plain fetch; `contextdev_get_web_scrape_markdown` (free) or `firecrawl_scrape` (0.02 credits per page, from `describe` on 2026-09-30) as the rendered second source | confirm the tools are callable with `deepline tools describe <id> --json`. Without a way to read a page there is no evidence and this skill does not run |
| **Which model extracts the record** | the exact AI Gateway model ID passed to `ai_inference` | the author graded one model on this prompt. A model that has not been graded against the verbatim-price rule is untested |
| **Concurrency per origin** | how politely to fetch | **default 2 per origin, and keep it.** These are the websites of companies they want to sell to |

## What this skill touches

- **Reads** — the public pages at each domain, fetched over plain HTTP, and nothing else.
- **Writes** — its own structured pricing record plus a confidence flag, on the rows you point it at.
  The optional copy clause is written only when the brief asked for it.
- **Never** — logs in, fills a form, reads a private rate card, invents a price or a plan name,
  removes a row on its own authority, drafts or sends a message, or writes to a CRM.
- **Halts** — Step 1 other, Step 4 sample-review.
- **Derived from** — the author's clean 10-domain regrade, on domains that appear nowhere in the
  prompt. An earlier 9/10 on this same chain is **withdrawn as contaminated** — the claims section
  says exactly why, because the reason is more useful than the number.

## Declared outputs

| Field | Type | Example | Null? |
|---|---|---|---|
| `pricing_public` | boolean | `true` | no, defaults false |
| `pricing_url` | string | the pricing page URL | yes — `""` |
| `pricing_model` | `per_seat` / `usage` / `flat` / `credits` / `quote_only` / `unknown` | `per_seat` | no |
| `plans` | array of `{name, price, period}`, max 6 | — | yes — `[]` |
| `lowest_paid_price` | string | `$10` | yes — `""` |
| `has_free_tier` | boolean | `true` | no |
| `enterprise_quote_only` | boolean | `true` | no |
| `feature_diff_axis` | 6 words or fewer | `seats and automation limits` | yes — `""` |
| `confidence` | `high` / `low` | `high` | no |
| `pricing_line` | **OPT-IN, absent on a default run** | `your Basic plan is $10 per user per month` | n/a |

### `quote_only` and `unknown` are not the same thing

- **`quote_only`** — the page exists and every tier says contact sales. **A confident finding you
  can filter on.**
- **`unknown`** — you could not read the page at all. **A failed fetch, not a finding.** The row must
  not be filtered out on your say-so.

**If every tier says "Contact Sales", the correct answer is `pricing_public: false` — a real and
useful signal, not a failure.**

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json` (CLI missing: `npm install -g deepline && deepline auth register
--wait auto`), confirm the fetch tools above describe as callable, and run `deepline csv show --csv
<path> --summary` to confirm a `domain` column. The run is one Deepline play over the CSV, authored
per the `deepline-plays` skill: `generic_http_request` columns for the sweep and fetch, an
`ai_inference` column with a `jsonSchema` for the record, and a `run_javascript` column for the
verbatim assertions. Name them, then say what this run touches: *"this reads public pages at each domain and adds a pricing
record to <the file you named>. It logs into nothing and sends nothing."* If a check fails, name it
and stop.

## Step 1 — Ask the one question that changes the output

Ask whether `pricing_public: false` rows should **filter** out of this campaign or **route** to a
different one, and whether the copy clause is wanted at all.

**Halt here (`other`).** These two answers change what gets produced and what accuracy bar applies,
so they are not defaults to be assumed. If the brief is silent on filter-versus-route, say you are
routing and why.

## Step 2 — Find the page, then read it

Sweep the likely paths with cheap `HEAD` requests (`generic_http_request`, `method: "HEAD"`) before fetching anything — `/pricing`, `/plans`,
`/price`, and the handful of variants — then GET the one that answered and take the price-dense
window of the text.

**Fetch at concurrency 2 per origin.** These are prospects' websites.

**A page that comes back as a short JavaScript shell has told you nothing.** It is not a negative
finding and it is not an empty pricing page. It is `unknown`.

## Step 3 — Extract the record, and assert every claim back against the text

The model reads the captured text and returns the structured record. Then, **in code**:

**Every price and every plan name must appear verbatim in the fetched page text.** Grep each
reported name and price back out of the captured text and drop anything that is not there.

This is not belt-and-braces. **Writing "Base" where the page says "Basic" is the same failure as
inventing a price** — the prospect goes looking, does not find it, and the message is dead. **Never
grade a batch by eye.**

**A true negative needs a second, independently located page with real readable text** — a
rendered fetch (`contextdev_get_web_scrape_markdown` with `waitForMs`, or `firecrawl_scrape`) of a
different URL, such as the page a `serper_google_search` for `<domain> pricing` returns. If the
second source also comes back as a JS shell, that **confirms nothing in either direction** — the row
stays `unknown`.

## Step 4 — Read a sample before the list runs

**Halt here (`sample-review`).** Show 10 rows: the domain, the page found, the record extracted, and
for each reported price the line of captured text it was grepped out of. Read them.

The failure this catches: a chain that returns `unknown` on every row looks identical to a chain
that is still running, and because a filter brief acts on the output, **an unnoticed failed-fetch
run can quietly remove an entire list from a campaign.** That is exactly why `unknown` never
removes a row.

## Step 5 — Deliver, and keep the two accuracy stories separate

Report: how many rows produced a usable filtering record, how many are `quote_only` (a finding), and
how many are `unknown` (a failure to read). **Never add those last two together.** If the copy
clause was turned on, report its usable rate separately, because it is held to a higher bar.

## Representative output

Invented examples for shape only; no real company, plan or price appears.

### The pricing record, row by row

| domain | `pricing_public` | `pricing_model` | `lowest_paid_price` | `has_free_tier` | `enterprise_quote_only` | `confidence` | what happened |
|---|---|---|---|---|---|---|---|
| `northstar-example.com` | true | `per_seat` | `$10` | true | true | high | three tiers plus a quote-only enterprise tier |
| `vantageloop.example` | true | `usage` | `$0.004` | false | false | high | metered, priced per request |
| `meridian-example.com` | true | `flat` | `$99` | false | true | high | one paid plan, then contact sales |
| `harborline.example` | **false** | `quote_only` | `` | false | true | high | page exists, every tier says contact sales. **A finding** |
| `pinegrove.example` | false | **`unknown`** | `` | false | false | **low** | page was a JavaScript shell twice. **Not a finding — this row is not filtered** |
| `brightfold.example` | false | **`unknown`** | `` | false | false | **low** | no pricing page found on ten paths. **Not a finding** |

### The run summary

```
10 domains
   8 usable filtering records
   10/10 on the existence check alone     <- plan on this number

  of the 8:  6 pricing_public=true   2 quote_only (a real finding)
   2 unknown -- failed reads, NOT findings, NOT filtered out

every reported price and plan name grepped back out of captured text: 8/8 verified
  1 model-reported plan name dropped in code: page said "Basic", model wrote "Base"

copy clause: OFF (brief did not ask for it)
disposition for pricing_public=false rows: ROUTE to the sales-led campaign
```

## What this skill does not claim

- **An earlier 9/10 on this chain is withdrawn, and the reason is worth more than the number.** The
  first run was **contaminated**: three of the four examples in the prompt were verbatim the scraped
  text and the exact expected output of three of the ten graded rows — and the prompt had been
  rewritten *after* seeing first-pass failures on those same rows. **30% of the test had its answers
  in the prompt.** The 8/10 above is a clean regrade on ten domains that appear nowhere in the
  prompt. **The clean number is lower, which is what you should expect whenever a contaminated
  number gets re-measured.**
- **The rule that follows from it, and it applies to any prompt anyone edits here:** an example may
  never be text from a domain in the test set, and if you tune a prompt against failures on specific
  rows, you must regrade on different rows.
- **Two bars, and which one binds depends on you.** Used to route or filter, this is internal work
  and the plain 70%-usable bar applies. **The moment a campaign turns the copy clause on, or quotes
  a price to a stranger, the 90%-claim-correctness bar binds.** That is the whole reason the clause
  is off by default.
- **The copy clause is a 70-to-90% field.** Usable on 9 of 10 in the clean regrade, 6 of 10 on an
  earlier corrected run. Treat it as optional, never mandatory.
- **`unknown` is not a finding.** It means the fetch failed. Filtering on it deletes real prospects
  because of a network error, and this skill will not do it.
- **It does not know what anyone actually pays.** Published pricing is a list price. Negotiated
  rates, private rate cards, marketplace listings and ecommerce SKUs are all out of scope.
- **The verdict covers a script path** — a HEAD sweep, a plain GET, and a model extractor at roughly
  $0.50 per 1,000 domains, measured before this skill was ported to Deepline. **The Deepline play
  build has never been run.**
- **A pricing page can change the day after you read it.** There is no freshness guarantee here; the
  record is true as at the fetch.
- **No reply, meeting or conversion rate is claimed**, and no benchmark for one exists here.

## What good looks like

- The default run produced **no** copy clause, because nobody asked for one.
- `quote_only` and `unknown` are separate numbers in the report, and nobody added them together.
- Not one row was removed from a campaign on an `unknown`.
- Every reported price can be grepped back out of the captured page text, and at least one
  model-reported name was dropped in code for not matching the page exactly.
- A row that returned a JavaScript shell twice is `unknown`, not "no pricing page".
- The filter-or-route decision was asked, not assumed, and is written into the handoff.
- Fetching stayed at concurrency 2 per origin.

## Rules

1. **Bones by default.** Do not produce, push or build a column for the copy clause unless the brief
   asks for it.
2. **Every price and plan name must appear verbatim in the fetched text. Assert it in code.** Never
   grade a batch by eye.
3. **`quote_only` is a finding. `unknown` is a failed read.** Never collapse them.
4. **`unknown` never removes a row.** Act only on high-confidence findings.
5. **If the brief is silent, route rather than delete**, and say so.
6. **A true negative needs a second independently located page with real readable text.** A
   JavaScript shell confirms nothing in either direction.
7. **Turning the copy clause on raises the bar from 70% usable to 90% claim-correct.** Say so when
   someone asks for it.
8. **An example in a prompt may never be text from a domain in the test set**, and a prompt tuned
   against specific failing rows must be regraded on different rows.
9. **Fetch at concurrency 2 per origin.**
10. **Read a 10-row sample before running the list** — a run that failed to read every page looks
    exactly like a run still in progress, and the downstream filter acts on it either way.
11. **This skill writes its own columns and sends nothing.** Whether a pricing value removes a row is
    the installer's decision, made per campaign brief.
