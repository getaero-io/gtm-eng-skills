# Google Ads Audiences

Use these tools for Data Manager v1 audience lifecycle (Customer Match and other ingested user lists) and member uploads.

## Audience kinds and `upload_key_types`

Pick the right `upload_key_types` for the data you'll ingest:

- `CONTACT_ID` (default) — Customer Match by SHA-256 hashed email, phone, and/or address.
- `MOBILE_ID` — IDFA / AAID mobile advertising IDs. Requires `ingested_user_list_info.mobile_id_info.app_id` + `key_space` (`IOS` or `ANDROID`).
- `USER_ID` — first-party CRM user IDs.
- `PAIR_ID` — publisher/advertiser identity reconciliation IDs.
- `PSEUDONYMOUS_ID` — DMP-style pseudonymous IDs.

Lists can hold a single key type or a mix. For Customer Match (the common B2B path), use `CONTACT_ID`.

## Account types

`account_type` (and `login_account_type`) accepts the Data Manager v1 `accountTypes` enum:

- `GOOGLE_ADS` (default — used for Google Ads customer + manager accounts)
- `DISPLAY_VIDEO_PARTNER`
- `DISPLAY_VIDEO_ADVERTISER`
- `DATA_PARTNER`
- `GOOGLE_ANALYTICS_PROPERTY`
- `GOOGLE_AD_MANAGER_AUDIENCE_LINK`

Note: Data Manager v1 does not separate "customer" vs "manager" account-type values like the legacy Google Ads API. Both use `GOOGLE_ADS`.

## Lifecycle

- Prefer `google_ads_audiences_create_audience` once per list, then reuse the returned audience ID.
- Use `google_ads_audiences_sync_audience_members` with `mode: "replace"` for full refreshes and `mode: "append"` for incremental adds.
- Include `login_account_id` when the OAuth user accesses the advertiser through a manager (MCC) account.
- Keep Google consent and terms-of-service state explicit. Deepline defaults `terms_of_service_accepted` to true for uploads.
- Treat returned `request_ids` as async upload receipts and poll `google_ads_audiences_get_audience_status` for downstream list health.
- `membership_life_span_days` is capped at 540 (Google's Customer Match maximum) and is sent as a Data Manager `membershipDuration` Duration string under the hood.
