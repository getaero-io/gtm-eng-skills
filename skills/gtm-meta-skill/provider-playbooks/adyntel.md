Use Adyntel for paid-media intelligence (creative examples, channel presence, and ad strategy signals).

- Deepline injects required Adyntel account identity fields automatically.
- Normalize domains to bare host format (`company.com`, no protocol or `www`).
- Use channel-native tools (`adyntel_facebook`, `adyntel_google`, `adyntel_linkedin`, `adyntel_tiktok_search`) before cross-channel synthesis.
- Prefer `adyntel_google_shopping_sync` to launch and poll Google Shopping in one call.
- Keep `adyntel_google_shopping_status` for manual follow-up polling when you already have an `id`.
- Use `adyntel_tiktok_ad_details` only after collecting IDs from `adyntel_tiktok_search`; pass `id` as a string.
- Billing is request-based for paid endpoints, so pre-filter targets before broad sweeps.

```bash
deepline tools execute adyntel_google --payload '{"company_domain":"hubspot.com"}' --json
```

```bash
deepline tools execute adyntel_google_shopping_sync --payload '{"company_domain":"allbirds.com"}' --json
```
