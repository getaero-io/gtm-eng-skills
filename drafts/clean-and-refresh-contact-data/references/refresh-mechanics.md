# Refresh mechanics — gates, verifier rules, arms, loop caps

Arms confirmed with `deepline tools describe` / `deepline plays describe`
2026-09-30; re-check prices before quoting. Behaviour notes marked "measured on
Clay" were observed on Clay's equivalent actions, 2026-08-12.

## The two staleness gates (state comparison, never a timer)

Per field being refreshed, two complementary gates:

```javascript
// RE-ENRICH — should I fetch a new value for this row/field?
// new value empty AND old value exists → prior fetch failed/decayed, try again
// OR the current-state check contradicts the record's claim
!newValue && !!oldValue  ||  claimContradicted

// OVERWRITE — should the new value replace the old?
// non-empty AND materially different; empties never clobber values
!!newValue && normalize(newValue) !== normalize(oldValue)
```

Time-based gates ("older than 90 days") re-buy unchanged data and trust changed
data — use them only as a scheduling hint for WHEN to run this play, never as the
per-row test.

## The employment verifier (the verdict that orders everything)

Over the enriched person payload:
- **Domain-match takes precedence over name-match** — acquisitions and rebrands
  rename companies without moving people; compare the record's account domain to
  the person's current employer domain.
- **Multiple concurrent current roles are real** (board seats, advisors): the
  primary/latest experience decides employment; extra current roles → `multi-role`
  flag, never "departed".
- **Empty enrichment = `unverifiable`**, an honest state — absence of evidence is
  not evidence of departure (and completion status is not data: complete runs wrap
  empty or failed items routinely; gate on values at both levels).
- Title drift with the same employer = `changed` (refresh), not a mover.

## Arms + costs (check `describe` for current prices)

| Arm | Cost | Role |
|---|---|---|
| `prebuilt/job-change-check` | billed only on a confirmed move | the batch employment verdict: compares the record against current employment, returns `job_change.status`, new company/title/date, `validation_status`. Rows without an email, or a company anchor plus a contact identifier, return `missing_input` — that is not a verdict |
| `crustdata_v3_person_enrich` (`professional_network_profile_urls` or `business_emails`) | per matched record + requested field groups | the current-state read; request only `basic_profile` and `experience`. The email arm is lower-yield than the URL arm (measured on Clay's Enrich Person; treat a miss on email input as `unverifiable`, never departed) |
| `crustdata_v3_person_search` (company domain + title/seniority filters) | 0.02 credits per returned result; empty pages free | the replacement arm (same-account re-source) and a recovery identifier arm; records carry URL/title/start date; keep `limit` strict and post-validate role identity |
| `prebuilt/company-to-contact` (`roles`, `domain`) | per `plays describe` | alternative replacement arm that returns a role-matched contact plus `rejected_candidates` |
| `leadmagic_email_validation` | 0.09 credits/result | one validator's vocabulary end to end: `valid` → valid; `valid_catch_all` → valid (engagement-confirmed); `catch_all` → `unverified`, never `valid`; `invalid` → invalid; `unknown` → unverified |
| `generic_http_request` + DNS | free | account-domain sanity when an employer domain looks dead — read `status_code` and `final_url` |

## Replacement loop discipline (the freshness loop, capped)

```
departed → role-scoped search at the SAME account (lost contact's function ×
seniority) → verify the candidate's employment (same verifier) →
  verified → replaced (evidence attached)
  failed → attempt++ ; attempt < CAP(2) → widen title vocabulary once → retry
  cap hit → seat = unfilled (report), never cycle
```

Recover vs replace: a cleaner identifier for the SAME person (better LinkedIn URL,
corrected email) is recovery — do it in place. A DIFFERENT person filling the seat
is replacement — policy-gated, capped, evidenced. The mover themself is a FOLLOW
lead for the job-change play, not this loop's problem.

## Overwrite + conflict rules (the change-log contract)

- Every applied change logs `field · old → new · evidence · date`.
- Empty-over-value is structurally impossible (the overwrite gate).
- Two non-empty values disagreeing without a resolution rule → `conflict` flag with
  both values shipped; recency reorders whole records, never per-field (per-field
  most-recent-wins fabricates states that never existed on any source).
- Validity absence FLAGS (`validity: unverified`), never gates a row out — gate only
  on positive invalidity evidence.
