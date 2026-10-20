# IPQS — Agent Routing

## Phone validation: use Trestle instead

**For phone validation, use `trestle_phone_validation` first, not IPQS.**

Trestle returns `activity_score` (0–100) which tells you whether a line is active or disconnected — IPQS phone validation does not. Activity score is the most useful signal for filtering stale numbers before cold outreach.

| Scenario                                               | Use                                  |
| ------------------------------------------------------ | ------------------------------------ |
| Validate a phone after enrichment                      | `trestle_phone_validation`           |
| Verify phone belongs to a specific person (name match) | `trestle_real_contact`               |
| IPQS phone validate                                    | Last resort only — no activity score |

## Email validation: use LeadMagic instead

**Do not use `ipqs_email_verify` or `ipqs_batch_email_verify` for outbound email validation.**

IPQS returns separate `valid` and `catch_all` fields. A `valid: true` result with `catch_all: true` does not confirm that the individual mailbox exists, so Deepline marks it `valid_catch_all` with `verified: false`. Use `leadmagic_email_validation` as the primary outbound validation gate — it returns a structured `email_status` (`valid` / `catch_all` / `invalid`) and is inexpensive per call.

Priority for email validation: `leadmagic_email_validation` → `zerobounce_validate` → IPQS (last resort).

## What IPQS is good for

- Fraud scoring: `fraud_score` on email or phone
- Disposable/honeypot detection: `disposable`, `honeypot` fields
- Spam trap detection on email
- DNC status on phone (use `trestle_phone_validation` for line type + activity though)
