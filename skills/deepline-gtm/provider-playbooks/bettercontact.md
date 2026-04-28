# BetterContact Agent Guidance

## Key patterns
- **Enrichment waits by default.** `bettercontact_enrich` and `bettercontact_bulk_enrich` poll BetterContact and return the terminal enrichment payload on success. Use `wait_for_completion: false` only when you want the launcher response immediately.
- **Email status hierarchy:** deliverable > catch_all_safe > catch_all_not_safe > undeliverable. Only trust deliverable and catch_all_safe for outreach.
- **Batch up to 100 contacts** per enrichment request using `bettercontact_bulk_enrich`.
- When `wait_for_completion: false`, the launcher response returns `{ success, id, message }` — use the `id` field as the `request_id` for `bettercontact_get_result`.
- **Rate limit:** 60 requests per minute per API key, shared across all endpoints.

## Pricing
- 1 email = 1 credit ($0.07 to user), 1 mobile phone = 10 credits ($0.69 to user)
- Credits only consumed on success (triple email verification included)
- **Phone enrichment is expensive** — only enable `enrich_phone_number: true` when explicitly needed

## When to use
- Use BetterContact when you need waterfall email enrichment with multi-provider verification.
- Good fallback when single-provider finders (LeadMagic, Prospeo) miss.
- Includes triple email verification, phone verification, contact & company enrichment.

## When NOT to use
- Don't use for email validation only — use a dedicated validator.
- Don't use for company/org enrichment — BetterContact is contact-focused.
