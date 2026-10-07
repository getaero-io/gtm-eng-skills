Use `salesforce_fetch_fields` before writing custom objects or unknown standard objects so you can confirm exact field API names and validation rules.

Use `salesforce_list_contacts`, `salesforce_list_leads`, and `salesforce_list_accounts` for incremental CRM reads. They accept `modified_after` for recent changes and `next_records_url` for pagination handoff.

Use the object-specific create, update, and delete tools for Accounts, Contacts, Leads, and Opportunities instead of building raw Salesforce payloads yourself. The integration already maps Deepline-friendly field names to Salesforce API names.

For custom field write-back on Accounts, Contacts, Leads, and Opportunities, pass `fields` with official Salesforce API names, for example `{ "id": "001...", "fields": { "Deepline_Score__c": 87, "Deepline_Email_Gate__c": true } }`. Values may be strings, numbers, booleans, or `null` to clear a field. If a friendly field and `fields` both target the same Salesforce API name, the explicit `fields` value wins.

After a write, use `salesforce_get_record` with the object API name, record ID, and exact scalar field API names to verify custom field values, for example `{ "object": "Account", "id": "001...", "fields": ["Name", "Deepline_Score__c"] }`.

Campaign membership is how Salesforce records that a lead or contact took part in an event, webinar, or program. To mark event attendance or registration, find the campaign with `salesforce_list_campaigns` (filter with `name_contains` and `is_active`), then call `salesforce_add_campaign_member` with `campaign_id`, exactly one of `lead_id` or `contact_id`, and a `status` such as `Attended`. Do not use a custom field on the Lead or Contact for this. The status must be one of the campaign's member statuses; an invalid status fails with the list of valid labels, so retry with one of them rather than guessing. The call is idempotent: re-adding an existing member updates its status and returns `created: false`. Use `salesforce_list_campaign_members` to read who is already in a campaign and their status.

Before creating a lead or contact, call `salesforce_search` with the email (and name or phone if you have them) to find existing Leads, Contacts, and Accounts. Update a match instead of creating a duplicate. Search results can lag a few seconds behind record creation.

To log a call, email, or other activity, use `salesforce_create_task` with `who_id` set to the Lead or Contact. Add `what_id` for the Account, Opportunity, or Campaign only when `who_id` is a Contact; Salesforce rejects `what_id` on Lead tasks.

For reads that no list tool covers (Tasks, Events, Users, OpportunityContactRoles, custom objects, filtered or joined queries), use `salesforce_query` with a SOQL `SELECT`. It returns one page per call; pass `next_records_url` with the same `soql` for the next page, and `include_deleted: true` to include deleted records. Escape single quotes in string literals as `\'`.

Use the typed tools first. `salesforce_api_request` is the escape hatch for everything else: one authenticated `GET`, `POST`, `PUT`, `PATCH`, or `DELETE` to a relative REST path such as `/services/data/v60.0/sobjects/Event` (Events), `/services/data/v60.0/sobjects/OpportunityContactRole` (contact roles), `/services/data/v60.0/composite/sobjects` (batch writes of up to 200 records), or `/services/data/v60.0/analytics/reports/<reportId>` (reports). Lead conversion is not available as a REST resource; do not try to fake it with field updates.
