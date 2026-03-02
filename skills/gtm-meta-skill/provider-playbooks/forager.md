# Forager Workflow Guidance

Forager has 850M+ B2B person records and is especially strong for verified mobile phone numbers (200M+ database). Prefer Forager over other providers when the goal is phone number discovery.

## Search & Discovery

- Always start with totals operations (`forager_person_role_search_totals`, `forager_organization_search_totals`, `forager_job_search_totals`) to estimate result volume at zero credit cost before running paid searches.
- Use `forager_person_role_search` for prospecting by role, skills, and company criteria. Each page costs 1 credit.
- Use `forager_organization_search` for company prospecting by industry, size, technology stack, and revenue filters.
- Use `forager_job_search` for intent-signal analysis: companies hiring for specific roles indicate growth and budget in those areas.

## Boolean Text Search

- Fields like `role_title`, `role_description`, `person_name`, `organization_description` use boolean text search.
- **Multi-word phrases MUST be quoted**: `'"VP Sales"'` not `'VP Sales'`. Unquoted phrases cause a parse error.
- Supports AND, OR, NOT, and parentheses: `("VP Sales" OR "Director of Sales") NOT intern`

## Filter Fields Use Integer IDs

- `person_locations`, `person_skills`, `person_industries`, `organization_locations`, etc. all require **integer IDs**, not name strings.
- Retrieve IDs from the lookup operations first (e.g. `forager_industries`, `forager_locations`, `forager_person_skills`).

## Enrichment & Reveals

- Use `forager_person_detail_lookup` to enrich a known person by `person_id` or `linkedin_public_identifier`. Only set `reveal_work_emails`, `reveal_personal_emails`, and `reveal_phone_numbers` when you actually need that contact data -- reveals add significant credit cost (5 credits per email type, 15 credits for phone).
- Use `forager_person_reverse_lookup` for reverse identity resolution from a known email or phone number.
- Use `forager_website_detail_lookup` for technographic enrichment on a specific domain.

## Cross-Provider Workflow Tips

- Apollo `apollo_search_people` returns obfuscated last names. When building name-dependent workflows (e.g. email pattern generation), bridge through `apollo_people_match` first to get the real last name, then use Forager for phone/email reveals.
- Forager person search results include `person_id` -- save this for subsequent `forager_person_detail_lookup` calls to avoid re-searching.
- Use `forager_account` to check remaining credit balance before large batch operations.
