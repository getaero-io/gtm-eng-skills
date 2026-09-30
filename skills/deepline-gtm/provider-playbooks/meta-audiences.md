# Meta Audiences

Use these tools for Meta customer-list custom audiences.

- Create one custom audience per segment and then keep syncing member files into the same audience ID.
- Use `mode: "replace"` for full snapshots and `mode: "append"` for incremental adds.
- Deepline hashes supported identifiers locally before upload.
- Watch `operation_status`, `delivery_status`, the `approximate_count_*_bound` pair, and invalid-entry counts when evaluating match health.
- Meta reports audience size as a range. Read `approximate_count_lower_bound` and `approximate_count_upper_bound`; `approximate_count` is a midpoint Deepline derives for backward compatibility, not a figure Meta returns.
- Sizes stay null until Meta finishes processing an upload, and Meta withholds them entirely for audiences below its minimum size threshold. A null count shortly after a sync is normal, not a failed upload.
- `delivery_status` code 411 means a low rate of matched people, which is the signal that a list matched poorly.
- Meta locks an audience while a users upload ingests: `operation_status` code 414 means a replace is still processing, and further writes fail with `META_AUDIENCE_UPDATE_IN_PROGRESS` until it settles. Poll `meta_audiences_get_audience_status` until `operation_status` code returns 200, then retry the full sync in one call. Do not resume a partial upload with `mode: "append"`; re-send the complete list.
- Send the whole member list in one `sync_audience_members` call. Chunking into separate calls collides with the ingest lock and strands a partial audience.
- `audience_id` must be the numeric id Meta returns. Read it from `meta_audiences_create_audience` at `data.audience.id`; a literal "undefined" id means the caller read the wrong response field, and the tool now rejects it before compiling the payload.
- Connect with a system user token: Dashboard → Integrations → Meta Audiences → Connect opens the setup page, which saves the token through `POST /api/v2/integrations/meta_audiences/token`. The dashboard no longer offers Meta Login for Business, because until Meta approves Deepline's App Review it only works for accounts that hold a role on the Deepline app. Existing Login for Business connections keep working. The token comes from the customer's own Business Manager: create a Meta app with the Marketing API product, add a system user (Employee role is enough), assign the ad account with Manage campaigns (ads) and the app with Develop app, and generate a token with `ads_management` and `ads_read` and no expiry (`business_management` is not needed). A human in that business must accept the Custom Audience terms once per ad account, or audience creation fails with "Custom audience terms not accepted" and a terms link; send that link to the customer. The accounts API reports `customAudienceTermsAccepted` per account after setup.
