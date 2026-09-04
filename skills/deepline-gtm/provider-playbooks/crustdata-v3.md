# CrustData V3 guidance

Use autocomplete before search when filter values are uncertain. Autocomplete is free and reduces expensive zero-result searches.

Use indexed search for discovery:

- `crustdata_v3_person_search`
- `crustdata_v3_company_search`
- `crustdata_v3_job_search`

Keep `limit` strict. Search is billed per returned result, not by matched `total_count`.

Filter to people with verified work emails before paying for enrichment. Person
search accepts `experience.employment_details.current.business_email_verified`
as a filter field (`type: "="`, `value: true`) — it selects only people whose
current employment carries a verified business email, so every returned result
is enrichable to a valid work email. The flag is a boolean, not the address:
the emails themselves come back from person enrich under
`contact.business_emails[*].email`, each with a `status` field (`verified` /
`unverified`). Never read the profile-level email field or
`contact.personal_emails` when the goal is work emails.

## Filter syntax and operators

Person/company/job search all take a `filters` condition group:
`{"op": "and", "conditions": [{"field": "...", "type": "=", "value": ...}]}` -
groups nest, and `op` accepts `and` / `or`. Condition `type` supports `=`,
`!=`, `in`, `not_in`, `contains`, `has_all`, `all_of`, `>`, `<`, `=>`, `=<`.
Sorting is `sorts: [{"field": "...", "order": "asc" | "desc"}]`. Company and
job search have their own filter/sort field vocabularies - read the field
lists in each tool's input schema (`deepline tools describe`) rather than
reusing person fields.

## Company-search response projections

For `crustdata_v3_company_search`, `filters` and `fields` are different
vocabularies. A field path that can filter companies is not necessarily a
response selector. Request response groups such as `basic_info`, `headcount`,
`funding`, `locations`, and `taxonomy`, then read nested values from the
returned group. Do not request `basic_info.industries` or period leaves such
as `headcount.growth_percent.6m`; use `basic_info` and
`headcount.growth_percent` respectively. `roles`, `skills`, `seo`, and
`competitors` are filter-only for this endpoint.

## Size and qualify for free before paying

- `limit: 1` returns `total_count` and `total_count_relation` - TAM sizing for
  the price of one result.
- `preview: true` (person search and person enrich) returns basic fields at
  preview billing - confirm identity/shape before buying full records.
- Person search results include `contact.has_business_email`,
  `has_personal_email`, and `has_phone_number` booleans - you can see contact
  availability per person before spending on enrichment.
- `fields: [...]` on search and enrich limits the returned field paths;
  on enrich, requested field groups drive the price - request only what the
  workflow uses.

## High-leverage person filters most workflows miss

- **Job changes**: `recently_changed_jobs` filters to people who recently
  switched roles; pair with `metadata.updated_at` (range operators) to bound
  data freshness.
- **Alumni prospecting**: the `experience.employment_details.past.*` family
  (`past.company_name`, `past.company_id`, `past.company_linkedin_profile_url`,
  `past.company_headcount_range`, `past.company_industries`) finds everyone
  who USED to work somewhere - "ex-Stripe, now at a 11-200 person company" is
  two conditions.
- **Open to work**: `professional_network.open_to_cards` (values like
  `CAREER_INTEREST`, `HIRING_MANAGER`) surfaces people signalling openness.
- **Normalized titles**: prefer `basic_profile.normalized_title.matched_title`,
  `.department`, and `.sub_department` over raw title string matching - it is
  CrustData's normalized taxonomy and beats regex title lists.
- **Employer size without a company join**:
  `experience.employment_details.current.company_headcount_range` /
  `company_headcount_latest` filter people by their employer's size directly.
- **Seniority and function**: `experience.employment_details.current.seniority_level`
  and `.function_category` are the org-chart building blocks.
- **Influence and tenure**: `professional_network.connections`, `.followers`,
  and `years_of_experience` support scoring and champion selection.

Use enrich after narrowing candidates:

- `crustdata_v3_person_enrich` for full cached person profiles.
- `crustdata_v3_person_contact_enrich` for contact-only lookups.
- `crustdata_v3_company_enrich` for full company records.

Use `crustdata_v3_company_identify` before company enrich when the inbound identifier is fuzzy. It is free. Prefer a domain or LinkedIn company URL. Name-only matching can return unrelated companies even at `confidence_score: 1.0`; treat those results as candidates and verify an independent identifier before changing stored names or domains.

Some `crustdata_v3_person_enrich` field groups (for example `certifications`, per CrustData's own docs) may 403 with a permission error depending on the account's CrustData entitlement — this is not restricted in the schema because a different account may have different access. If a caller hits `PROVIDER_AUTHORIZATION_FAILED` requesting a specific field group, drop it and retry without that group rather than assuming every documented group is universally available to every account.

Do not use old PersonDB field paths with V3 unless a reviewed compatibility mapper converts them to the documented `2025-11-01` field vocabulary.
