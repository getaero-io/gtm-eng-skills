# Datagma Workflow Guidance

Datagma is strongest when you need real-time enrichment rather than a static
contact database. It is especially useful for direct mobile numbers, international
coverage, and job-change validation.

## When to use Datagma

- Use `datagma_full_enrichment` when you have a strong identifier such as a
  LinkedIn URL, a professional email, or a domain-backed full name.
- `datagma_enrich_person` remains a compatibility alias for the flat legacy
  response. `datagma_enrich_company` returns the native Datagma response body;
  use its canonical Deepline getters for company name and domain.
- Use `datagma_find_email` when you only need a verified work email and want a
  narrower, cheaper workflow than full enrichment.
- Do not use Datagma for personal-email-only waterfall steps. Public docs expose
  verified work email and full enrichment, not a personal-email-only endpoint.
- Use `datagma_search_phone_numbers` when you already have an email or social URL
  and want direct mobile numbers.
- Use `datagma_job_change_detection` before outreach refreshes when you need to
  confirm whether a contact is still at the same company.
- Use `datagma_find_people` to source up to 10 people by title inside a target company.

## Phone lookup pitfalls

- `datagma_enrich_person` supports optional mobile lookup with `phoneFull=true`.
  Read its flat `mobile_phone` field. Omitting the flag or setting it to false
  preserves basic enrichment; adding email alone does not enable phone lookup.
  Mobile lookup costs more: inspect the payload estimate before a batch. The
  estimate includes one mobile lookup and is not a guaranteed maximum; final
  pricing uses reported usage.
- For an email or social profile URL, use `datagma_search_phone_numbers` and
  read `person.phones`. Send both `email` and `username` when available.
- For name plus company context without an email or social profile, use
  `datagma_full_enrichment` with `phoneFull=true` and read `phoneFull.phones`.
  The compatibility alias's flat `phone` / `mobile_phone` fields are not the
  output paths for these operations.
- Inspect a small sample's actual payload and phone fields before a bulk run.
  An identity result without phones does not prove the provider has no phone
  coverage when the request did not ask for phone lookup.
- Extract candidates only from documented phone fields. Job IDs, timestamps,
  and arbitrary numeric metadata are not phone numbers. When scanning flattened
  output, inspect the field after the tool alias: an alias such as
  `datagma_mobile` does not make its `job_id` field a phone.
- Diagnose completed runs from their original request receipts. Editing a
  configuration afterward does not change what the earlier run sent.

## Input strategy

1. LinkedIn URL or company domain
2. Professional email
3. Full name plus company context
4. Company-name-only lookups only when nothing stronger is available

Datagma’s own docs emphasize that LinkedIn URL and domain-backed inputs are the
most reliable. Prefer those over plain company-name searches.

## Billing behavior to remember

- Mobile phone lookups are substantially more expensive than verified email
  lookups. Prefer `datagma_find_email` when a work email is all you need.
- `datagma_full_enrichment`, `datagma_job_change_detection`, and
  `datagma_search_phone_numbers` report vendor usage in the response. Deepline
  uses that vendor-reported value rather than guessing.
- Where vendor-reported usage is absent, Deepline falls back to endpoint-specific,
  documented success fields rather than treating every non-empty profile as a
  personal-email hit.
- Catch-all email results are free.
- Deepline credit pricing for these actions is generated from the provider
  pricing metadata and rendered on the public provider pages.

## Endpoint guidance

### `datagma_find_email`

Use for:

- verified work-email lookup from name + company context

Best inputs:

- `firstName` + `lastName` + `companyDomain`
- or `fullName` + `companyDomain`
- optionally `linkedInSlug` when you have the company LinkedIn slug

Canonical Deepline snake_case column names map straight through, so CSV columns
named `first_name` / `last_name` / `full_name` / `company_name` /
`company_domain` / `domain` are accepted as input aliases for their camelCase
equivalents (the bare `domain` column is treated as the company web domain).

### `datagma_full_enrichment`

Use for:

- person or company enrichment
- firmographics plus person details in one pass
- real-time phone/email/company expansion

Best inputs:

- `data` set to a LinkedIn URL or professional email
- `fullName` or `firstName` + `lastName` only when paired with `data`

Important:

- `phoneFull=true` should be reserved for cases where you do not already have
  a social profile or email, matching Datagma’s docs guidance.

### `datagma_job_change_detection`

Use for:

- validating whether a contact is still at the same company

Best inputs:

- `fullName` + `companyName`
- add `jobTitle` when the contact name may be ambiguous

### `datagma_find_people`

Use for:

- prospecting inside one company by role title

Best inputs:

- `currentJobTitle`
- plus one of `linkedinId`, `domain`, or `currentCompanies`
- add `countries` when known to improve relevance

The action retains the documented contract while Deepline translates it to
Datagma's current employee-finding endpoint.

### `datagma_search_phone_numbers`

Use for:

- direct mobile-number search from an email or profile URL

Best inputs:

- both `email` and `username` when you have them
- Datagma explicitly recommends passing both together when possible

## Internal-only endpoints

Datagma also exposes reverse-email, reverse-phone, and Twitter lookup endpoints.
They remain internal in this repo because the current public docs do not disclose
standalone pricing for them. Do not move them to the public tool surface until
pricing is verified against live credentials or direct vendor confirmation.
