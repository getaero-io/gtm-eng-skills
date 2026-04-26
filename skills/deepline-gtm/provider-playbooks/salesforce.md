Use `salesforce_fetch_fields` before writing custom objects or unknown standard objects so you can confirm exact field API names and validation rules.

Use `salesforce_list_contacts`, `salesforce_list_leads`, and `salesforce_list_accounts` for incremental CRM reads. They accept `modified_after` for recent changes and `next_records_url` for pagination handoff.

Use the object-specific create, update, and delete tools for Accounts, Contacts, Leads, and Opportunities instead of building raw Salesforce payloads yourself. The integration already maps Deepline-friendly field names to Salesforce API names.
