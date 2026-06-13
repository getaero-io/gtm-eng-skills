Use `salesforce_fetch_fields` before writing custom objects or unknown standard objects so you can confirm exact field API names and validation rules.

Use `salesforce_list_contacts`, `salesforce_list_leads`, and `salesforce_list_accounts` for incremental CRM reads. They accept `modified_after` for recent changes and `next_records_url` for pagination handoff.

Use the object-specific create, update, and delete tools for Accounts, Contacts, Leads, and Opportunities instead of building raw Salesforce payloads yourself. The integration already maps Deepline-friendly field names to Salesforce API names.

For custom field write-back on Accounts, Contacts, Leads, and Opportunities, pass `fields` with official Salesforce API names, for example `{ "id": "001...", "fields": { "Deepline_Score__c": 87, "Deepline_Email_Gate__c": true } }`. Values may be strings, numbers, booleans, or `null` to clear a field. If a friendly field and `fields` both target the same Salesforce API name, the explicit `fields` value wins.

After a write, use `salesforce_get_record` with the object API name, record ID, and exact scalar field API names to verify custom field values, for example `{ "object": "Account", "id": "001...", "fields": ["Name", "Deepline_Score__c"] }`.
