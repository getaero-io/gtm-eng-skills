# Time Machine: make the change the opening

Select `comparison_mode=before_after` to require a verified comparison. The opening must
state **both what was true earlier and what is true in the current observation**. For example,
with fictional evidence: “You used to lead with standalone reporting; now you are emphasizing
reporting inside the CRM.” The next line explains why that might matter for the actual offer.
A current-state-only line fails review. This is evidence comparison, not a claim that the sender
has been watching the prospect.

## Setup once, compare per company

- Choose Offer or ICP, CTA, greeting and signature as usual.
- Choose **Before vs. now** (`comparison_mode=before_after`) or **Best supported signal** (`auto`).
- Optionally set `comparison_focus`, such as buyer emphasis, product positioning or pricing.
- Optionally set `comparison_as_of` to a past `YYYY-MM-DD` cutoff. Every selected historical
  receipt must match it. Leave blank when companies have different available history.
- Map **Past observation** to `past_observation_json` and **Current observation** to
  `current_observation_json`, or supply receipts through `evidence_json`.
- If the current receipt is blank, deeplineagent researches current evidence live. If the past
  receipt is missing, required comparison mode returns a research hold; it never invents history.

In the default run the date input selects/checks imported evidence. For automatic
retrieval, use the optional `--exa` run in `exa-connection.md`. Users export their own
key as `EXA_API_KEY`; the runner adds two Deepline `generic_http_request` nodes that call Exa
/contents. It requests history as of the selected cutoff and fresh current contents.
The base run has no automatic fetch.
Exa documents historical retrieval at https://exa.ai/blog/exa-snapshot.

## Minimal receipt examples (fictional)

Past column:

```json
{"id":"example-before","provider":"exa_snapshot","url":"https://example.com/","observed_at":"2026-09-18T12:00:00Z","requested_as_of":"2026-06-01T00:00:00Z","text":"Standalone reporting for independent finance teams.","role":"past"}
```

Current column:

```json
{"id":"example-now","provider":"source_capture","url":"https://example.com/","observed_at":"2026-09-18T12:00:00Z","text":"Reporting inside your CRM with connected account data.","role":"current"}
```

Examples illustrate shape, not reusable real observations. Keep source text intact. Never
make a model invent receipts. An actual provider capture time may be supplied as `captured_at`;
omit it when unavailable. Exa current contents without a historical cutoff uses source_capture,
with provider provenance recorded separately. Labels do not authenticate an imported receipt.

## What the checks establish

Python checks exact receipt IDs, company domains, verbatim excerpts, real dates, past-before-current
ordering, matching selected cutoff and current freshness (seven days by default; configurable
1–30 via `max_current_age_days`). It rejects identical text and title-only history.
The separate deeplineagent audit checks equivalent page purpose, source meaning, meaningful difference,
identity and offer relevance. Both sides must contain supported claims. A new date alone is not a signal. For historical comparisons, timing strength assesses the asserted temporal contrast: valid past bound plus fresh current observation can support earlier/now; exact capture dates or a corroborated transition provide stronger timing evidence. A comparison score never establishes an exact change date.

The final copy critic requires both observations explicitly in the opening and faithful date
precision. A requested cutoff means a snapshot at or before that cutoff. It is **not** the
actual capture date or the date the company changed. Without a real capture date, use
“earlier/now” or “from/toward,” not an invented month or “last week.”

A change in positioning can justify “you are emphasizing X more.” It cannot by itself justify
“you launched X,” “you stopped offering Y,” or “your operations now require Z.” Implications stay
hypothetical. Missing/unchanged evidence returns a hold even if the numerical score is high.

An imported current receipt may support a comparison when the same page cannot be reopened,
provided identity, date, contents and audit support it and no accessed evidence contradicts it.
The evidence card labels this as operator-provided provenance and retains its observation date.
It is not independent authentication or fresh retrieval by the workflow.

## Outputs for review

`comparison_json` retains before/after claims, historical/current URLs, receipt IDs,
requested cutoff, actual capture date if known, current observation date and change kind.
Subject/body keep research mechanics out of the email. The evidence card remains available
for a reviewer to inspect. No supported difference means no comparison copy.
