# BetterContact Agent Guidance

## Key patterns

- **Enrichment is upstream-async.** By default, `bettercontact_enrich` and `bettercontact_bulk_enrich` wait briefly for terminal results. If the job is still running, they return a pollable request id; set `wait_for_completion: false` for launch-only behavior. Use `bettercontact_get_result` to fetch terminal results.
- **Email status hierarchy:** deliverable > catch_all_safe > catch_all_not_safe > undeliverable. Only trust deliverable and catch_all_safe for outreach.
- **Batch up to 100 contacts** per enrichment request using `bettercontact_bulk_enrich`.
- Use the launcher response `id` as the `request_id` for `bettercontact_get_result`.
- **Rate limit:** 600 requests per minute per API key, shared across all endpoints. This is BetterContact's confirmed going-forward limit; its public rate-limit page still shows the previous 60 RPM value.

## Pricing

- Deepline bills from the terminal enrichment result, and charges only for successful lookups.
- **Phone enrichment costs significantly more than email** — only enable `enrich_phone_number: true` when explicitly needed

## When to use

- Use BetterContact when you need waterfall email enrichment with multi-provider verification.
- Good fallback when single-provider finders (LeadMagic, Prospeo) miss.
- Includes triple email verification, phone verification, contact & company enrichment.

## When NOT to use

- Don't use for email validation only — use a dedicated validator.
- Don't use for company/org enrichment — BetterContact is contact-focused.
