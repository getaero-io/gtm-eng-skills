---
name: 10k-value-prop-match
description: |
  Match a seller's own value proposition against what a public target account actually
  says it's prioritizing in its 10-K — instead of matching on fixed keywords or phrases,
  it takes the installer's value-prop statement, reads the account's most recent 10-K
  (Business overview, Risk Factors, MD&A by default), and surfaces the specific stated
  initiatives that line up, each with the literal sentence it matched on. Use whenever
  someone asks: does our positioning line up with what this account says it's investing
  in, find 10-K language that supports outbound personalization, check if a target
  company's stated priorities match our pitch, or build account-specific messaging off
  SEC filing language instead of generic firmographics. Reads the filing through
  Deepline's free sec_edgar tools, sized and checked for truncation, because a 10-K
  routinely runs past the 150,000-character ceiling of a single document read, and does
  the matching as agent judgment rather than a per-row AI column. A theme naming match is not a buying
  signal on its own, so every match also gets read for whether the filing describes the
  need as open or as already solved in-house — a company that names the exact problem
  and states it already built its own fix is not a warmer lead than one that never
  mentioned it. Do NOT use it for private or
  non-SEC-reporting companies (no 10-K exists), for a generic company-news or
  buying-signal scan (use a funding/news signal skill instead), or as a numeric fit
  score — it returns matched initiatives with quotes, not a single number.
category: signals
personas: [revops, sales-leader]
mechanism: logic-only
touches: read-only
keywords: []
ported_from: clay-run/clay-skill-creator/skills/kerry-kean/10k-value-prop-match
---

# 10-K value-proposition match (read the whole filing; match with judgment, not a column)

The insight: **a 10-K's primary document routinely runs to hundreds of KB of body
text, and any reader with a character ceiling will confidently report on the front of
it.** Deepline's `sec_edgar_get_filing_document` returns at most **150,000 characters**
per call (50,000 by default) — a real ceiling, but an honest one: it reports
`truncated`, `returned_chars` and `total_chars`. A skill that reads a 10-K at the
default and ignores those fields reports on the first sixth of the document, and Item
7 (MD&A) is usually past that point. (The predecessor of this skill was built on Clay,
whose `scrape-website` action truncated at 8,192 characters with no flag at all; the
failure mode is the same, only the number moved.) So: **the filing is read with the
truncation fields checked and the rest fetched in full, and the matching is agent
judgment, not a per-row AI column.** Deepline's job in this skill is narrow and free —
resolving a ticker to a CIK, listing filings, and fetching the documents — and
everything downstream of that is the agent's.

## Declared inputs

**Nothing here ships with a value.** Each one is the installer's, not the author's: ask for it, never
substitute a plausible default, and if an answer does not exist say which step becomes unavailable
rather than guessing.

| Input | What the installer supplies | If it is missing |
|---|---|---|
| **The value proposition** | a few sentences, in their own words: what they sell, for whom, and the problem it removes | no default — there is nothing to match against |
| **The target account(s)** | company name, domain, ticker, or SEC CIK; one or many | no default — ask for at least one identifier per account |
| **Fiscal year / filing** | which 10-K to use | most recent filed 10-K is the default, and using the default must be stated in the output |
| **Sections to search** | which 10-K items to read | Item 1 (Business), Item 1A (Risk Factors), Item 7 (MD&A) is the default — the three items initiatives and priorities are usually stated in; ask before expanding to the full document, since a larger fetch is more agent context, not more Deepline credits |
| **Match strictness** | how willing they are to count an adjacent-but-unnamed theme as a match | default is "Strong match" requires a literal quotable sentence; "Possible match" is offered as a separate, lower-confidence bucket — never blended into Strong |

## What this skill touches

- **Reads** — the value-proposition text the installer supplies, the target account list, and each
  account's public 10-K filings from SEC EDGAR (a public, free source).
- **Writes** — nothing. Output is a match report handed back to the installer.
- **Never** — assumes a company has a 10-K on file (private companies and most foreign private
  issuers do not; the skill checks and reports "not applicable" rather than guessing), and never
  reports a "Strong match" without the literal sentence it matched on attached.
- **Halts** — Step 4 `sample-review`, Step 4 `spend-approval`.
- **Derived from** — a fixed-keyword version of this idea built for one client engagement (a
  10-K cost/initiative scan looking for specific named language); generalized here to match against
  whatever value proposition the installer states, rather than a fixed phrase list. Not table-derived
  — this file was written from that pattern and a conversation, not converted from a live table or play,
  so no formula in it has been checked against a running column.

## Step 0 — Check the platform, and say where the work runs

Run `deepline preflight --json`. If the CLI is missing, install it (`npm install -g deepline &&
deepline auth register --wait auto`) and re-run this one. State the org you're in.

**Say this before anything else runs:** the SEC lookups (`sec_edgar_resolve_company`,
`sec_edgar_list_filings`, `sec_edgar_get_filing_index`, `sec_edgar_get_filing_document`) are all
priced **Free** per `deepline tools describe`, and matching the text against the value proposition
happens in this agent — zero Deepline credits for either. A paid call is needed only if a target
account arrives as a bare company name with no ticker or CIK and EDGAR's own company search cannot
resolve it; state that step's declared price before running it across more than a couple of
accounts.

## Step 1 — Collect the definition (interview; do not guess)

1. **The value proposition**, in the installer's own words — what they sell, who it's for, the
   problem it removes. Do not paraphrase it for them; use what they actually said as the thing every
   filing sentence gets compared against.
2. **The target account list** — company names, domains, tickers, or CIKs. Ask which identifier they
   have; do not assume a domain implies a public company.
3. **Fiscal year** — most recent 10-K unless they name one.
4. **Sections** — confirm the Item 1 / 1A / 7 default, or take their preferred scope.

## Step 2 — Resolve each account to a filing (the decision this skill exists to make)

1. If the installer supplied a ticker or CIK, use it directly — `sec_edgar_resolve_company`
   (`ticker`) returns the canonical CIK, free. `sec_edgar_list_filings` accepts either.
2. Otherwise, resolve company name → ticker or CIK. EDGAR's own company search
   (`https://www.sec.gov/cgi-bin/browse-edgar?company=<name>&type=10-K`, fetched with
   `generic_http_request` and a User-Agent header naming the requester, as the SEC requires) is free.
   `crustdata_v3_company_identify` (free) can confirm the domain behind a name, but it returns no
   ticker. The paid fallback is `dataforseo_serp_google_finance_ticker_search_live_advanced`
   (`keyword` = the company name), priced from returned usage.
3. `sec_edgar_list_filings` with `forms: ["10-K", "10-K/A"]` (and `filed_from` / `filed_to` around
   the fiscal year) and confirm a 10-K exists for the requested fiscal year. The response's `company`
   block carries `fiscal_year_end`. **If none exists — private company, files a 20-F instead, hasn't
   filed yet — say so explicitly and skip the account.** Do not substitute a different filing type
   silently.
4. `sec_edgar_get_filing_index` (`cik`, `accession_number`) lists the documents; take the primary
   10-K document's exact name. Then `sec_edgar_get_filing_document` with that `document_name`,
   `format: "text"` and `max_chars: 150000`. **Check `truncated`.** When it is true, `total_chars`
   says how much was left out; fetch the full primary document from its `source_url` with
   `generic_http_request` (free, SEC User-Agent header set) and cut Items 1, 1A and 7 out of it in
   code. If that full fetch also fails, say so and report the account as unreadable rather than
   matching against a partial document without flagging it as partial.

## Step 3 — Free checks before anything paid

Confirm the filing exists and pull the text (Steps 2.3–2.4) for every account before any paid call
runs. Only fall back to the paid ticker search for accounts whose CIK could not be resolved for
free.

## Step 4 — Small batch, then one gate

Run the full flow — resolve, fetch, match — on 2–3 accounts first and show the actual matched
initiatives with their quoted sentences. Then, in one message, state: the batch results, how many
remaining accounts need a paid ticker-resolution call and its declared price, and ask
for approval before running the rest. This step is read-only throughout — the gate is about spend and
about the installer seeing real output before trusting more of it, not about anything being written
anywhere.

## Step 5 — Do the work

For each account: read the fetched sections; extract statements that name a specific initiative,
priority, investment area, or pain point (not generic boilerplate); compare each one against the
value proposition. Read for both directions — a sentence that supports the connection, and a
sentence that actively argues against it (a stated strategy of avoiding what the value proposition
offers is real evidence, not noise). Keep every sentence where a connection, in either direction, is
real enough to quote.

## Step 6 — Grade, two single-valued fields, never blended into one

A theme match and a buying signal are different questions, and this step keeps them as two separate
fields rather than folding "found the theme" and "worth pursuing" into one number. Collapsing them
was a real failure mode caught in testing: a filing can name the exact problem a value proposition
solves while stating, in the same sentence, that the company already solved it itself — that is not
a warmer lead than an account that never mentioned the problem at all, and a single blended score
would report it as one.

**Match verdict** — does the filing name the theme:

- **Strong match** — a literal sentence in the filing names the initiative, and it's a fair reading
  that the value proposition addresses it. The quote is mandatory.
- **Possible match** — a plausible connection, but the filing's language is adjacent rather than
  naming it directly. Still quote the nearest sentence; say why it's Possible and not Strong.
- **No match found** — nothing in the read sections supports a connection. This is a real, reportable
  answer, not a failure — most accounts will have some of these, and that is expected, not a gap in
  the run.

**Need status** — read only on a Strong or Possible match, from the same quoted sentence and its
surrounding paragraph:

- **Open** — the filing describes the theme as an ongoing cost, risk, or priority with no stated fix
  in place yet.
- **Solved in-house** — the filing states the company already built, automated, or contracted its own
  answer to this theme. Report this plainly rather than as a lesser Strong match — it is evidence
  against the account being a live opportunity, not a weaker version of evidence for it.
- **Unclear** — the sentence names the theme but does not say whether it is resolved. Do not guess
  either way.

**Basis** — read for every verdict, including No match found, because "the filing never brought this
up" and "the filing explicitly said this isn't how they operate" are different strengths of evidence
and get reported differently:

- **Explicit** — a specific sentence exists, one way or the other. On a Strong or Possible match, it's
  the confirming quote already required above. On a No match found, it's a sentence that actively
  argues against the connection — a company describing its own model as built specifically to avoid
  what the value proposition offers is a real, reportable disqualifying signal, not an absence of one,
  and it gets quoted the same as a confirming match would.
- **Silent** — the read sections simply never raise the theme, for or against. This is the weaker of
  the two "No match found" cases, and it stays unquoted because there's nothing to quote — reported as
  silence, not padded with a nearby sentence that doesn't actually address it.

## Step 7 — Deliver

Per account: the fiscal year and filing used, every match — Strong, Possible, and any Explicit No
match found — with its quote, section, need status where it applies, and basis, and the coverage
line — sections read, any account skipped and why. Never present a Strong-match, Solved-in-house row
as a lead without the need status visible in the same line — that is the exact pairing this skill
exists to keep together. A Silent no match still gets a row; it just carries no quote.

## Representative output

### Per-account match report

| Account | Filing used | Verdict | Basis | Need status | Matched theme | Quote |
|---|---|---|---|---|---|---|
| Northwind Robotics | FY2025 10-K, Item 7 | Strong match | Explicit | Solved in-house | Warehouse automation cost reduction | "we continued to invest in automating fulfillment center operations to reduce per-unit labor cost, and this automation is now substantially complete" |
| Fenwick Insurance | FY2025 10-K, Item 1A | Strong match | Explicit | Open | Claims-processing cost pressure | "rising claims-handling costs continue to outpace premium growth, and we have not yet identified a scalable remedy" |
| Northwind Robotics | FY2025 10-K, Item 1A | Possible match | Explicit | Unclear | Supply chain resilience | "disruptions to our supplier network could materially affect our results" |
| Beckridge Freight | FY2025 10-K, Item 1 | No match found | Explicit | — | Deliberately avoids the value proposition's category | "our model is built on direct, self-service adoption specifically to avoid the cost of a traditional outsourced fulfillment layer" — a real disqualifying signal, reported and quoted like any other match |
| Halloway Textiles | FY2025 10-K | No match found | Silent | — | — | the read sections never raise warehouse or fulfillment cost at all — no quote exists to attach |
| Contoso Freight | — | Not applicable | — | — | — | Contoso Freight is privately held; no 10-K on file with the SEC |

### Coverage line

6 accounts requested · 5 had a 10-K on file · 5 read in full across Items 1, 1A, 7 · 1 marked not
applicable (private) · 1 ticker resolved via a paid lookup (declared and approved at Step 4) · of
2 Strong matches, 1 is Open and 1 is Solved in-house — reported separately, not averaged together · of
2 No match found accounts, 1 is Explicit (an actual disqualifying quote) and 1 is Silent (the topic
never came up) — also reported separately, since they're different strengths of evidence.

## What this skill does not claim

- This file is interview-derived, not converted from a live table or play — no formula or threshold
  in it has been checked against a run. The `sec_edgar` tools named here were confirmed with
  `deepline tools describe`, not executed.
- A **Silent** No match found means the read sections didn't raise the theme at all — it does not mean
  the company doesn't do the thing. Silence in a 10-K is not disconfirmation; companies don't narrate
  every initiative in their filings. An **Explicit** No match found is different and stronger: the
  filing actively describes a model or strategy that argues against the fit, and that is real
  evidence, not a stronger flavor of silence.
- "Strong" vs. "Possible", "Open" vs. "Solved in-house" vs. "Unclear", and "Explicit" vs. "Silent",
  are all the installer's agent's judgment at read time, not a certified or re-derived score — two
  runs on the same filing could plausibly land a borderline sentence in either bucket on any axis.
- Need status is read from the matched sentence and its immediate paragraph only. A company can state
  a fix is in place in one filing section while a different section (or a later filing) shows it
  didn't fully work — this skill reports what the filing says, not whether the stated fix actually
  held.
- Only covers accounts that file a 10-K with the SEC — US-listed and SEC-reporting companies. Foreign
  private issuers (20-F filers) and private companies are explicitly out of scope, not silently
  skipped without saying so.
- The 150,000-character ceiling is what `deepline tools describe sec_edgar_get_filing_document`
  declared on 2026-09-30; read the live schema before relying on the exact number. The `truncated`
  flag in each response is what the skill actually gates on.
- Does not merge or reconcile a 10-K/A amendment with the original filing automatically; if one
  exists, the skill flags it and asks which version to use.

## What good looks like

Every Strong match carries a literal quoted sentence that a reader can go find in the actual filing,
and carries a need status alongside it — never a bare "Strong match" with the need question left
unanswered. Every account resolves to either a specific filing (with fiscal year stated) or an
explicit "not applicable, no 10-K" — never silently dropped. A run that returns mostly "No match
found" across several accounts is a legitimate result, not a broken run, provided the sections
actually read are stated — and a good run also distinguishes which of those No match accounts had an
actual disqualifying sentence (Explicit) from which ones simply never raised the topic (Silent).
Three failure modes this skill exists to prevent: "Strong match" everywhere with no quotes, every
Strong match reported as a lead with no Solved-in-house accounts flagged, and every No match found
treated as the same flavor of nothing when some of them actually said something.

## Rules

- Never match against a filing read with `truncated: true` without fetching the rest or flagging the
  account as partial.
- Never report a Strong match without the literal source sentence attached.
- Never report a Strong or Possible match without a need status attached — a match with the need
  question unanswered is an incomplete row, not a finished one.
- Never assume a company has a 10-K; check first, and report "not applicable" rather than guessing or
  skipping silently.
- Never blend Possible matches into the Strong count, and never blend Solved-in-house matches into a
  lead list alongside Open ones.
- Never report an Explicit No match found without its quote, and never invent a quote for a Silent
  one — if there's nothing to cite, say so plainly rather than reaching for the nearest sentence.
- Always state the fiscal year of the filing used, per account.

## Worked example

Value proposition supplied: "We help mid-market logistics companies cut warehouse labor cost by
automating pallet-level inventory tracking."

Target: Northwind Robotics, ticker NWRB, FY2025 10-K requested (default: most recent).

1. CIK resolved from the ticker with `sec_edgar_resolve_company` — free.
2. `sec_edgar_list_filings` confirms a FY2025 10-K is on file; `sec_edgar_get_filing_index` names the
   primary document.
3. `sec_edgar_get_filing_document` at `max_chars: 150000` comes back `truncated: true`, so the full
   document is fetched from its `source_url` — Item 1, 1A, and 7 pulled.
4. Item 7 (MD&A) contains: "we continued to invest in automating fulfillment center operations to
   reduce per-unit labor cost, and this automation is now substantially complete." — matched as
   **Strong**: the value proposition's core claim (cut warehouse labor cost via automation) is named
   directly. Need status: **Solved in-house** — the same sentence states the automation is already
   substantially complete, so this is reported as evidence against active need, not muted into a
   weaker Strong match.
5. Item 1A (Risk Factors) contains a supplier-disruption risk sentence — matched as **Possible**: it's
   adjacent (supply chain, not labor cost) rather than a direct hit. Need status: **Unclear** — the
   sentence names a risk, not whether it's being addressed. Basis: **Explicit** — there's a real
   sentence to quote, even though it's an adjacent one.
6. A second target, Beckridge Freight, states in Item 1: "our model is built on direct, self-service
   adoption specifically to avoid the cost of a traditional outsourced fulfillment layer." Matched as
   **No match found**, Basis **Explicit** — the filing didn't just fail to mention the theme, it
   actively described a strategy built to avoid needing it. That gets quoted and reported the same
   as a confirming match, not treated as silence.
7. A third target, Halloway Textiles, never raises warehouse, fulfillment, or labor cost anywhere in
   the read sections. Matched as **No match found**, Basis **Silent** — no quote, because there's
   nothing there to cite.
8. Delivered as the table shown under Representative output, plus the coverage line — the Solved
   in-house row, the Explicit no-match, and the Silent no-match are all reported side by side rather
   than collapsed into one undifferentiated "no matches found" line.
