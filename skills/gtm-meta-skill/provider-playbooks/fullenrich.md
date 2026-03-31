# Fullenrich Agent Guidance

## Key patterns
- **Enrichment is async** (45-60s average, up to 90s). Submit via `fullenrich_enrich`, poll via `fullenrich_get_result`. Typical completion: 30-90 seconds per contact.
- **Use `enrich_fields`** to control what's enriched: `contact.emails` (1 credit), `contact.phones` (10 credits), `contact.personal_emails` (3 credits).
- **LinkedIn URL** improves accuracy significantly (5-20% for emails, 10-60% for phones).
- **Email status hierarchy:** DELIVERABLE > HIGH_PROBABILITY > CATCH_ALL > INVALID. Use `most_probable_work_email` field for the best result.
- **Phone costs 10x email** -- use judiciously and only when explicitly needed.
- **Search is synchronous** -- use `fullenrich_people_search` or `fullenrich_company_search` for prospecting.
- **Reverse email** is async -- same submit/poll pattern as enrichment.
- **`forceResults=true`** query param on get-result returns partial results if enrichment is still running.

## When to use
- Best for high-quality email/phone waterfall enrichment with extensive provider coverage (20+ sources).
- Search API is good for prospecting by job title, company, location, industry.
- Reverse email lookup useful for identifying contacts from email addresses.

## When NOT to use
- Don't use for email validation only -- use a dedicated validator (ZeroBounce, LeadMagic validation).
- Don't use phone enrichment unless explicitly needed -- expensive (10 credits).
- For quick single-provider email lookups, LeadMagic or Prospeo are faster/cheaper.
