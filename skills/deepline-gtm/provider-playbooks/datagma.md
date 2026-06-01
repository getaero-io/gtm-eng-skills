# Datagma Workflow Guidance

Datagma is strongest when you need real-time enrichment rather than a static
contact database. It is especially useful for direct mobile numbers, international
coverage, and job-change validation.

## When to use Datagma

- Use `datagma_full_enrichment` when you have a strong identifier such as a
  LinkedIn URL, a professional email, or a domain-backed full name.
- `datagma_enrich_person` and `datagma_enrich_company` remain valid compatibility aliases when older workflows expect the flat legacy Datagma response shape.
- Use `datagma_find_email` when you only need a verified work email and want a
  narrower, cheaper workflow than full enrichment.
- Use `datagma_search_phone_numbers` when you already have an email or social URL
  and want direct mobile numbers.
- Use `datagma_job_change_detection` before outreach refreshes when you need to
  confirm whether a contact is still at the same company.
- Use `datagma_find_people` to source up to 10 people by title inside a target company.

## Input strategy

1. LinkedIn URL or company domain
2. Professional email
3. Full name plus company context
4. Company-name-only lookups only when nothing stronger is available

Datagma’s own docs emphasize that LinkedIn URL and domain-backed inputs are the
most reliable. Prefer those over plain company-name searches.

## Billing behavior to remember

- Public pricing currently states `1 credit = 1 verified email`.
- Public pricing currently states `30 credits = 1 mobile phone number`.
- `datagma_find_people` is explicitly documented as 10 credits on success and
  1 credit on a no-result response.
- `datagma_full_enrichment`, `datagma_job_change_detection`, and
  `datagma_search_phone_numbers` expose `creditBurn` in the response. Deepline
  uses that vendor-reported value rather than guessing.
- Catch-all email results are free on the public pricing page.

## Endpoint guidance

### `datagma_find_email`

Use for:

- verified work-email lookup from name + company context

Best inputs:

- `firstName` + `lastName` + `company`
- or `fullName` + `company`
- optionally `linkedInSlug` when you have the company LinkedIn slug

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
