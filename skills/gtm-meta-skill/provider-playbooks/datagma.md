# Datagma — Agent Guidance

Datagma is a real-time B2B enrichment provider with 75+ data points per person,
strong phone coverage, job-change detection, and international reach.

## When to use Datagma

- You need a phone number and other enrichers have come up empty.
- You need real-time job-change signals (the `job_change_detected` field is native).
- You need international coverage (APAC, EMEA) where US-centric providers fall short.
- You have 1,000 free credits and want real data to test a waterfall.

## Primary identifier priority

1. `linkedin` URL — highest match rate, fastest resolution.
2. `email` — good fallback when LinkedIn is unavailable.
3. `fullName` + `domain` — lower confidence; combine with company context.
4. `fullName` + `companyName` — lowest confidence; only use when domain is unknown.

## datagma_enrich_person

```bash
deepline tools execute datagma_enrich_person \
  --payload '{"linkedin":"https://www.linkedin.com/in/johndoe"}'
```

Output shape (key fields at top level):
- `email` / `professional_email` / `personal_email`
- `phone` / `mobile_phone`
- `full_name`, `title`, `seniority`, `department`
- `location.city`, `location.country`
- `company.name`, `company.domain`, `company.industry`, `company.size`
- `experience[]` — full job history with is_current flag
- `job_change_detected` — true if a recent employer change was detected
- `confidence_score` — 0–1 confidence from Datagma

Target getter paths (for waterfall):
- email:    `email`, `professional_email`, `personal_email`
- phone:    `phone`, `mobile_phone`
- linkedin: `linkedin`
- name:     `full_name`
- company:  `company.name`

## datagma_find_email

Fast email finder — cheaper (in terms of matching complexity) than full enrichment
when you only need an email address.

```bash
deepline tools execute datagma_find_email \
  --payload '{"firstName":"John","lastName":"Doe","companyDomain":"acme.com"}'
```

Always prefer `companyDomain` over `companyName` for accuracy.

## datagma_enrich_company

Enrich firmographics for an account. Feeds into account scoring and ICP qualification.

```bash
deepline tools execute datagma_enrich_company \
  --payload '{"domain":"acme.com"}'
```

Output includes: `industry`, `size`, `headcount`, `revenue`, `funding_stage`,
`technologies`, `hq_country`.

## Cost notes

- Person enrichment: 1 credit (~$0.04) per result.
- Email finder: 1 credit (~$0.04) per email found.
- Company enrichment: 1 credit (~$0.02) per result.
- Credits are billed post-deduct (only charged when data is returned).
- 1,000 free credits at signup — no credit card required.

## Waterfall placement

In a people-enrich waterfall, place Datagma:
- After free enrichers (Apollo preview, LinkedIn scrape) but before expensive fallbacks.
- Specifically useful as a phone-finder fallback after ContactOut or RocketReach.
- Job-change detection makes it valuable as a "refresh trigger" — run for contacts
  not enriched in the last 90 days to detect company changes before outreach.

## Gotchas

- The full enrichment endpoint is `/api/ingress/v2/full` for both person AND company data.
  When only domain/companyName is passed (no person identifiers), it returns company-only data.
- Auth uses a query param (`?apikey=...`) — this is handled automatically by the provider config.
- A 200 response with empty fields means "not found" — check for null email/name before
  treating as enriched.
- `job_change_detected: true` does NOT mean the person left their current company.
  It means Datagma detected a change vs. their last known record. Always check `experience[0]`
  for the current role.
