# Small Business Prospecting

Use this for local SMB discovery like dentists, plumbers, med spas, agencies, or nearby storefronts.

1. Start with `serper_google_maps_search` when you need fast recall, loose discovery, or broad geo coverage.
2. Use `openwebninja_localbusiness_search` when you want structured Google Maps business rows with phone, address, rating, website, and optional `extract_emails_and_contacts=true`.
3. If the target area is map-bounded, prefer `openwebninja_localbusiness_search_in_area` or `openwebninja_localbusiness_search_nearby`.
4. If you need broader non-maps company sourcing, `forager_organization_search` can be a useful complement, but it is not the primary local-business tool.

Default pattern:

- Serper Maps for discovery and query tuning.
- OpenWebNinja Local Business for the structured list you will enrich or export.

Contact-email recovery pattern:

- Start with Maps identity and the business website/contact page when the row has a normal homepage.
- Treat Facebook and Instagram profiles as optional candidate sources, not mandatory steps. Consider them when the row's only website is a social profile, the official site is missing/thin, or a pilot/ground-truth sample suggests contact emails are in Facebook About blocks, Instagram profile contact fields, bios, link-in-bio pages, or recent posts.
- Search ScrapeCreators without over-constraining to a category if profile tools are not showing up in the first pass:

```bash
deepline tools search "facebook profile email scrapecreators" --json
deepline tools search "instagram profile bio email scrapecreators" --json
deepline tools search scrapecreators --json
```

- If available, test `scrapecreators_facebook_profile`, `scrapecreators_facebook_profile_posts`, `scrapecreators_instagram_profile`, and `scrapecreators_instagram_user_posts` on a tiny sample before scaling. Fall back to Serper/Firecrawl/Apify or direct website extraction when no managed profile route fits.
- Add audit columns such as `facebook_url`, `instagram_url`, `social_email`, `social_email_source`, `social_identity_evidence`, and `social_contact_confidence` instead of overwriting the canonical email directly.
- Accept social profile contact data only when the profile identity matches at least two of business name, address, phone, website/menu/booking link, or Maps profile.

Pilot first on one query and a small limit before scaling.
