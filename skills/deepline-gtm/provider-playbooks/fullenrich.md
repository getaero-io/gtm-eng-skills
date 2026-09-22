# FullEnrich Agent Guidance

## Key patterns

- **Async submit + async fetch.** `fullenrich_bulk_enrich` and `fullenrich_reverse_email` start background jobs and return an `enrichment_id`. A Play waits synchronously for terminal data, prints the status command before polling, and reports progress about every 15 seconds. Status checks run every 15 seconds. If a run is canceled or reaches its wait limit, the provider job can continue and may still incur Deepline credits; use the logged status command with `fullenrich_get_result` or `fullenrich_get_reverse_result` to check it.
- Submit at most 50 contacts or emails per batch. Split larger inputs into multiple calls.
- **Use `enrich_fields`** to control what's enriched: `contact.emails` is the cheapest, `contact.personal_emails` costs more, and `contact.phones` is by far the most expensive.
- **LinkedIn URL** improves accuracy significantly (5-20% for emails, 10-60% for phones).
- **Email status hierarchy:** DELIVERABLE > HIGH_PROBABILITY > CATCH_ALL > INVALID. Use `most_probable_work_email` field for the best result.
- **Phone costs 10x email** -- use judiciously and only when explicitly needed.
- **Search is synchronous** -- use `fullenrich_people_search` or `fullenrich_company_search` for prospecting.
- Status and result reads are free Deepline actions. The accepted batch's Deepline charge settles once from its final usage; do not resubmit a batch that is already running.
- **`forceResults=true`** on a direct get-result call returns partial results if enrichment is still running.

## When to use

- Best for high-quality email/phone waterfall enrichment with extensive provider coverage (20+ sources).
- Search API is good for prospecting by job title, company, location, industry.
- Reverse email lookup useful for identifying contacts from email addresses.

## When NOT to use

- Don't use for email validation only -- use a dedicated validator (ZeroBounce, LeadMagic validation).
- Don't use phone enrichment unless explicitly needed -- it is the most expensive field.
- For quick single-provider email lookups, LeadMagic or Prospeo are faster/cheaper.
