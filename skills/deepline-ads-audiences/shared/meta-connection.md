# Meta connection

Meta Audiences connects with a system user token from the customer's own
Business Manager. The dashboard does not offer Meta Login for Business for new
connections: until Meta approves Deepline's App Review, that login only grants
the ads permissions to people with a role on Deepline's own Meta app. Existing
Login for Business connections keep working.

The customer does the Meta steps; nothing on Meta's side can be done for them.
Send them the [setup guide](https://deepline.com/docs/providers/meta-audiences/guide)
and walk them through it:

1. [Create a Business app](https://developers.facebook.com/apps/creation/) with
   the use case "Create & manage ads with Marketing API", connected to the
   Business portfolio that owns the ad account.
2. In [System users](https://business.facebook.com/latest/settings/system_users),
   add a system user (the default Employee role is enough). Meta enables Add only after an app
   belongs to the portfolio.
3. Assign the ad account with Manage campaigns (ads) and the app with Develop
   app. Full control is not needed.
4. Generate a token for that app with only `ads_management` and `ads_read`,
   expiration Never. Meta preselects 60 days; a 60-day token stops working
   without warning.
5. Accept the Custom Audience terms once per ad account at
   `https://business.facebook.com/ads/manage/customaudiences/tos/?act=<ad account ID>`.
6. Paste the token in Dashboard -> Integrations -> Meta Audiences -> Connect.

`business_management` is not needed.

## Custom Audience terms

Audience creation fails until a person in the business accepts Meta's Custom
Audience terms for that ad account. Deepline records the state per account at
setup: `GET /api/v2/integrations/meta_audiences/accounts` (org admin session
or admin-owned API key) returns `customAudienceTermsAccepted` on each account
(`false` means not accepted, `null` means unknown). It reflects the last
discovery; `POST` to the same endpoint (the page's Refresh) discovers again,
so refresh after the customer accepts. Check it before the first `meta_audiences_create_audience`
on an account. When it is `false`, or create fails with "Custom audience terms
not accepted", send the customer
`https://business.facebook.com/ads/manage/customaudiences/tos/?act=<ad account ID>`
and wait for them to accept; do not retry the create in a loop. Never ask the customer to paste a token
into chat; the dashboard field is the only place it goes.

## Errors

| Error | Cause | Fix |
| --- | --- | --- |
| `(#100) Unsupported get request`, `Requires business_management permission` | A Login for Business token without the ads permissions. | Reconnect with a system user token. |
| "This token can reach no ad accounts" | No ad account assigned to the system user. | Assign it, then select Connect with token again with the same token. |
| `(#190)` / "Error validating access token" | Revoked or truncated token. | Generate and paste a new token. |
| "Custom audience terms not accepted" on create | Custom Audience terms not accepted for that account. | Send the terms link from the error; the customer accepts once. |
