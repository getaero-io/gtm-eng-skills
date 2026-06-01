# BetterContact Agent Guidance

## Key patterns

- **Enrichment is async.** `bettercontact_enrich` and `bettercontact_bulk_enrich` launch BetterContact jobs and return a request id immediately. Use `bettercontact_get_result` to fetch terminal results.
- **Email status hierarchy:** deliverable > catch_all_safe > catch_all_not_safe > undeliverable. Only trust deliverable and catch_all_safe for outreach.
- **Batch up to 100 contacts** per enrichment request using `bettercontact_bulk_enrich`.
- Use the launcher response `id` as the `request_id` for `bettercontact_get_result`.
- **Rate limit:** 60 requests per minute per API key, shared across all endpoints.

## Pricing

- 1 successful email = 1 provider credit, 1 successful mobile phone = +10 provider credits
- `bettercontact_get_result` returns `credits_consumed`; Deepline bills from that terminal provider usage
- **Phone enrichment is expensive** — only enable `enrich_phone_number: true` when explicitly needed

## When to use

- Use BetterContact when you need waterfall email enrichment with multi-provider verification.
- Good fallback when single-provider finders (LeadMagic, Prospeo) miss.
- Includes triple email verification, phone verification, contact & company enrichment.

## When NOT to use

- Don't use for email validation only — use a dedicated validator.
- Don't use for company/org enrichment — BetterContact is contact-focused.
