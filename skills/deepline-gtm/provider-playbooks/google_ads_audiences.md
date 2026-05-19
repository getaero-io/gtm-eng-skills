# Google Ads Audiences

Use these tools for Google Customer Match lifecycle and member uploads.

- Prefer `google_ads_audiences_create_audience` once per list, then keep reusing the returned audience ID.
- Use `google_ads_audiences_sync_audience_members` with `mode: "replace"` for full refreshes and `mode: "append"` for incremental adds.
- Include `login_account_id` when the OAuth user accesses the advertiser through a manager account.
- Keep Google consent and terms-of-service state explicit. Deepline defaults `terms_of_service_accepted` to true for uploads.
- Treat returned `request_ids` as async upload receipts and poll `google_ads_audiences_get_audience_status` for downstream list health.

