# Fundable API Guidance

Use Fundable for startup discovery, venture funding rounds, investor portfolios, founders, and saved funding alerts.

## Choose the endpoint

- Use `fundable_discover_companies` to find companies by company attributes, latest-round details, or investor participation.
- Use `fundable_search_deals` when the target is funding rounds across company histories. Use the `latest_deal` filters on company discovery when only the newest round matters.
- Use `fundable_search_companies`, `fundable_search_investors_by_name`, or `fundable_search_people_by_name` when resolving a name or uncertain identifier. Supply exactly one search input.
- Use `fundable_get_company`, `fundable_get_investor`, or `fundable_get_person` for a known entity. Prefer a domain or profile URL when available.
- Use the corresponding `*_deals` action for full funding history or investor activity.
- Use `fundable_unlock_person_email` or `fundable_unlock_person_phone` only when a verified contact is explicitly needed. New unlocks consume Fundable credits; a repeated unlock on the same account is free.
- Resolve readable location or industry names with `fundable_search_locations` or `fundable_search_industries` before using permalink filters.
- `fundable_get_alerts` requires alert IDs and a start/end date. `fundable_get_alert_configurations` lists the authenticated account's saved alerts.
- Email and phone unlocks are available on non-trial Pro, Enterprise, and API plans. Alert reads are available on Pro+ and Enterprise plans; alert reads are free.

## Authentication and pricing

Every operation uses a Fundable API key in a Bearer token. Fundable's API docs describe 200 free starting credits and pay-as-you-go credits from $0.05 per credit. Deepline settles paid calls from the exact `meta.credits_used` value returned by Fundable; that provider billing metadata is removed from the customer-visible response.

API documentation: https://docs.tryfundable.ai/
Pricing and credits: https://docs.tryfundable.ai/usage
