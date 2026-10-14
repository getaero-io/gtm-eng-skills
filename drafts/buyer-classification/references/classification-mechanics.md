# Classification mechanics — the two-gate logic, keyword construction, headcount rules, escalation

KB-derived judgment (buyer-classification playbook), re-derived for the
CLI/agent surface 2026-08-12 and ported to Deepline 2026-09-30. The
classification engine is deterministic code + agent judgment, not a per-row LLM
column — cheaper (0 credits), auditable, and reproducible. The judgment (two
requirements, keyword lists, exclusions, headcount) is provider-neutral.

## The two-requirement logic (both must hold)

```
is_buyer = FUNCTION(title, exclusions) AND SENIORITY(title, headcount)
```

- **FUNCTION** — the department/function that owns or directs the purchase of
  THIS product. Brief-specific, always. A DevTools build targets engineering;
  an HR-tech build targets People/HR; never default to finance.
- **SENIORITY** — senior enough to evaluate, champion, or approve budget for
  THIS purchase size. Also brief-specific: a $99/mo tool is bought by
  managers; a platform re-architecture is bought by VPs.

## Constructing the keyword lists (the interview's output)

Worked example — spend-management fintech (substitute values per vertical;
the STRUCTURE is what generalizes):

```
function_include:  finance, financial, accounting, accountant, controller,
                   comptroller, treasury, treasurer, fp&a, bookkeeping,
                   accounts payable, accounts receivable, ap, ar, spend, cfo
                   (abbreviations like ap/ar are safe ONLY under word-boundary
                   matching — as substrings they'd match everywhere)
function_exclude:  sales, marketing, engineering, product, security, hr,
                   legal, customer success
exclusion_traps:   "account executive", "account manager", "accounts director"
                   → SALES (the #1 finance-product misclassification)
seniority_include: chief, cfo, founder, owner, president, evp, svp, vp,
                   vice president, head of, director, managing director
sub_decider:       manager, senior manager, lead, analyst, associate,
                   specialist, bookkeeper, clerk, intern, coordinator
```

Construction rules:
- **Word-boundary matching, never bare substring** — `cfo` as a substring
  matches inside longer words and inside relation phrases; match tokens.
- **Exclusion traps run FIRST** — a title hitting an exclusion trap never
  reaches the include lists.
- **Support-relation phrases beat contained keywords**: "chief of staff to
  the CFO", "assistant to the VP", "office of the CEO" — the pattern
  `(chief of staff|assistant|advisor|office|deputy)( to| of)? (the )?<title>`
  classifies by the SUPPORT role (influencer at best), not the contained
  title. This is the substring-trap family: a contained "CFO" is not the CFO.
- **Compound titles** ("CFO & Co-Founder", "VP Sales / Interim CFO"): split on
  WHITESPACE-DELIMITED separators only — `/`, `,`, ` & `, ` and ` — classify
  each part, best (most-buyer) verdict wins, rationale quotes the winning
  part. Never split on a bare `&`: intra-word ampersands are real function
  names (FP&A, M&A, R&D) and a bare-`&` split shreds them into noise.
- **Interim/acting/fractional + a buying title still has authority** —
  classify as the title, flag the modifier.
- Vertical-specific ranks need vertical taxonomies built from the real org
  chart (law firms: Managing/Equity Partner = owner tier; Of Counsel =
  senior). Construct from the vertical, don't copy the corporate default.

## Headcount disambiguation (what "Manager" means)

Company headcount is the critical disambiguator for mid-tier titles in the
owning function — without it, classification over-promotes at enterprises and
under-counts at SMBs:

```
title in sub_decider AND function matches:
  headcount ≤ SMALL_CO (default 200)  → de facto decider (persona:
                                        "<Function> Decision-Maker", flagged
                                        headcount-modified)
  headcount > SMALL_CO                → influencer
  headcount unknown                   → influencer + flag "size-unknown" (the
                                        conservative read; never promote on
                                        missing data)
```

State the threshold in the delivery; it's a convention the user can re-cut.
Headcount arrives as a band string in some sources — parse the band's upper
bound; unparseable bands = unknown (never silently 0).

## Confidence + rationale contract

| confidence | meaning |
|---|---|
| `gate-matched` | deterministic keyword gates placed it; reproducible |
| `judgment` | the residual — reasoned against the same two requirements, one at a time, rationale mandatory |
| `unclear` | empty title, gibberish, or undecidable after judgment — with the reason |

Rationale: ≤20 words, quoting the title evidence ("'VP Finance' → seniority:
VP, function: finance"). A verdict without quoted evidence is a vibe.

## Right-sizing and the escalation ladder

- **Lean is_buyer (this skill's default)**: one product, one persona →
  `is_buyer + persona + confidence + rationale`. The KB's canonical rule:
  don't pay for MEDDPICC enums the build won't consume.
- **Full committee classification** (seniority enum × department enum ×
  MEDDPICC role) only when downstream genuinely consumes committee framing
  (multi-product routing, CRM-wide segmentation, opener-variant switching).
  The canonical enums (7 seniority / 12 department / 8 roles) and their
  embedded rules: product/project/program managers default to individual
  contributor (the classic over-promotion error); Director+ = decision-maker
  tier; economic buyer = final budget authority (typically CFO/CEO for spend).
- **Persisting the classifier as a Deepline play** (runs on future rows
  without an agent): a `run_javascript` column carrying the gates (free,
  deterministic), then a `deeplineagent` column only on rows the gates left
  unplaced, with the two-requirement prompt and a `jsonSchema` whose `persona`
  is an enum. The `deeplineagent` step is usage-priced per row where
  agent-side classification is free — do it when the user needs the column to
  run unattended (a webhook- or cron-triggered play), not for one-shot list
  passes. Re-check `deepline tools describe deeplineagent --json` at build
  time.

## Edge-case expectations (the fixture table)

| Title (headcount) | Expected — spend-management example |
|---|---|
| Chief Financial Officer | buyer · CFO · gate-matched |
| Interim CFO | buyer · CFO · gate-matched (interim flagged, authority intact) |
| VP Finance | buyer · VP Finance · gate-matched |
| Director of FP&A | buyer · Finance Decision-Maker · gate-matched |
| Finance Manager (50-person co) | buyer · Finance Decision-Maker · headcount-modified |
| Finance Manager (5,000-person co) | influencer · Finance Influencer |
| Finance Manager (headcount unknown) | influencer + size-unknown flag |
| Procurement Lead | not a buyer for spend-mgmt · flagged gatekeeper |
| AP Specialist | influencer · Finance Influencer |
| Project Manager | non-buyer (the classic over-promotion trap) |
| Founder & CFO (30-person co) | buyer · CFO (compound split, best part wins) |
| Chief of Staff to the CFO | influencer — relation rule beats contained "CFO" |
| Account Executive | non-buyer · SALES (exclusion trap) |
| "" / emoji / gibberish | unclear, with reason |
