# Trestle Workflow Guidance

## Key patterns
- **Use `trestle_phone_validate` as the final gate after phone enrichment.** It verifies the phone is a real active line AND confirms the name matches the phone owner — catching the two biggest quality problems in enriched mobile data.
- **Always pass `name` alongside `phone`**. Without `name`, `phone.name_match` will not be scored and contact grades degrade.
- **Interpret `contact_grade` as the headline quality signal:** A = high confidence, B = good, C = acceptable, D/F = drop before outbound.
- **`activity_score >= 70`** indicates an active line. Scores `<=30` suggest the line is stale or disconnected.
- **`linetype = "Mobile"`** is the outbound-friendly type. Landlines and VOIP variants are lower value for cold calling.

## When to use
- Post-waterfall validation after `contact_to_phone_waterfall` so you know which phones are safe to call.
- Identity validation where you have a name + phone and want to confirm they belong together.
- Optionally pass `email` and `address` in the same request to get multi-field identity validation in one call.

## When NOT to use
- Don't use as a phone *discovery* tool — Trestle validates known numbers, it doesn't find new ones.
- Don't use for fraud scoring alone — IPQS is better for fraud/DNC/carrier details.
- Don't call without a `name` parameter unless you only need the line type.

## Pricing
- Consumption is per-request and post-deduct — you only pay when the call succeeds.
- Trestle's own per-call pricing is low single cents; Deepline charges 1 credit per successful validation.
