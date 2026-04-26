# Small Business Prospecting

Use this for local SMB discovery like dentists, plumbers, med spas, agencies, or nearby storefronts.

1. Start with `serper_google_maps_search` when you need fast recall, loose discovery, or broad geo coverage.
2. Use `openwebninja_localbusiness_search` when you want structured Google Maps business rows with phone, address, rating, website, and optional `extract_emails_and_contacts=true`.
3. If the target area is map-bounded, prefer `openwebninja_localbusiness_search_in_area` or `openwebninja_localbusiness_search_nearby`.
4. If you need broader non-maps company sourcing, `forager_organization_search` can be a useful complement, but it is not the primary local-business tool.

Default pattern:

- Serper Maps for discovery and query tuning.
- OpenWebNinja Local Business for the structured list you will enrich or export.

Pilot first on one query and a small limit before scaling.
