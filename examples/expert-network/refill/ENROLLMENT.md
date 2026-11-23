# Qualification and paused-campaign enrollment

Qualification checks the same professional identity, expected employer and a practitioner title. The profile dependency must return `company_found=true` and `needs_verification=false`. Geography is inherited from source filtering, not independently rechecked. Email must be validated, have status valid and match the employer domain. Catch-all confirmation is disabled.

These are recruiting checks, not evidence of legal licensing, conflicts clearance, task quality, availability or consent. Missing or conflicting evidence returns held.

## Enrollment gates

Set `CAMPAIGN` in [enrollment-policy.ts](enrollment-policy.ts) to your own dedicated paused campaign. No actual campaign ID is shipped. The Play requires an exact ID match and paused/draft status. It never starts the campaign.

The Play scans variable suppressions for email, domain and profile in pages of 100, up to a 10,000-record bound. Only a short last page proves completion. Invalid or incomplete responses block enrollment. Existing contacts found by exact email are held for manual review rather than silently reused or resubscribed.

Before adding a contact, it claims an outbox keyed by campaign/profile and campaign/email. An acknowledgment is submitted. Exact email/profile campaign membership readback produces confirmed. A lost response is uncertain. An existing claim returns already_claimed; it is not retry permission.

## Records and recovery

| Stage | Input | Output |
|---|---|---|
| Qualification | erm_qualification_input | erm_qualification_output: qualified, held or failed |
| Enrollment | erm_enrollment_input | erm_enrollment_output: confirmed, submitted, held, suppressed, already_claimed or failed |
| External write | erm_enrollment_outbox request | submitting, submitted, confirmed or uncertain, with receipt |

All tables are under `storage`. Qualification results are reused by profile. Replay repairs the input handoff; failed and held results remain for review. A 15-minute lease bounds concurrent batches. Outbox uniqueness protects enrollment separately from the lease.

Confirmed enrollment stays ready because it does not prove delivery. Suppressed results set the suppression flag. Other progression requires reply/application events, which are not connected here.

`reconcile-enrollment.py` reads at most 100 pending outbox rows, checks membership and writes confirmed evidence without adding contacts. Set `ERM_CAMPAIGN_ID` to the same value as the Play constant. `retry-enrollment.py` retries at most two failed records with no outbox entry and retains prior failure evidence. Inspect those records first; never use it for ambiguous external writes.

The qualifier uses `prebuilt/person-linkedin-to-company` and `prebuilt/person-to-email`. Describe their current contracts before deployment. Each scalar adapter has a 2-credit cap, the batch 12 and the cycle 24; source refill is capped at 12. Caps can stop a run; they do not guarantee all requested work completes.
