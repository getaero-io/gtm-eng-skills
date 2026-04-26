# Trestle Workflow Guidance

Trestle has two phone APIs:

| Tool | Use when |
|------|----------|
| `trestle_phone_validation` | You need line type, carrier, activity score. No identity matching needed. |
| `trestle_real_contact` | You need to verify the phone belongs to a specific person (name_match, contact_grade). |

## trestle_phone_validation (Phone Intel API)

**Use as the default validation step after phone enrichment.** It's cheap and tells you:
- `is_valid` — is this a real phone number?
- `line_type` — Mobile, Landline, FixedVOIP, NonFixedVOIP, etc.
- `carrier` — service provider name
- `activity_score` — 0-100, where 70+ is active, <=30 is stale/disconnected
- `is_prepaid` — prepaid account status

**When to use:**
- Post-waterfall validation after `contact_to_phone_waterfall`
- Before cold calling to filter out disconnected/landline numbers
- When you don't have or don't care about name matching

**Does NOT require a name.** Just pass the phone number.

## trestle_real_contact (Real Contact API)

**Use when identity verification matters.** Returns everything from Phone Intel plus:
- `phone.name_match` — does the phone belong to this person?
- `phone.contact_grade` — A (high confidence) through F (drop)
- Optional email cross-validation in the same call

**When to use:**
- High-value outbound where you need to confirm identity
- When you have a name + phone and want to verify they belong together
- When you need email validation bundled with phone validation

**Requires both `phone` and `name`.** Optional: `email` for cross-validation.

## Key signals
- **`activity_score >= 70`** indicates an active line
- **`activity_score < 30`** is stale/disconnected — auto-fails waterfall validation
- **`line_type = "Mobile"`** is the outbound-friendly type
- **`contact_grade A/B`** = safe to call, **D/F** = drop

## Waterfall integration
When used after phone enrichment providers, Trestle validation tools automatically fail the waterfall step if:
- `is_valid` is false (invalid number)
- `activity_score` is below 30 (stale/disconnected)

This causes the waterfall to continue to the next phone provider, ensuring you only get validated, active phone numbers.

## Billing
- Both endpoints are post-deduct — you only pay on success.
