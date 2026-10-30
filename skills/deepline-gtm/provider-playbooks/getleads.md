# GetLeads API Guidance

Use GetLeads for B2B contact search and enrichment, company colleagues and decision-makers, and funding or acquisition signals.

## Choose the endpoint

- Use `getleads_count_contacts` to estimate a contact search before calling `getleads_search_contacts`. Counts and dataset metadata lookups are free in the provider API.
- Use `getleads_search_contacts` for filtered prospect lists. Request only the columns needed, and keep pages small because search charges scale with successfully returned contacts. Inspect the action’s current Deepline pricing.
- Use `getleads_lookup_colleagues` or `getleads_lookup_decision_makers` when you already know a company domain or LinkedIn company URL. Inspect current Deepline pricing per returned contact.
- Use `getleads_lookup_phone` or `getleads_batch_phone_lookup` when phone numbers are the lookup key. Inspect current Deepline pricing per successful match.
- Use `getleads_enrich_from_linkedin`, `getleads_enrich_from_email`, or `getleads_enrich_from_person` for contact enrichment. Inspect current Deepline pricing per successful enrichment.
- Use `getleads_get_filter_values` and `getleads_get_available_columns` to discover accepted filter values and field names. `getleads_get_contacts_health` checks dataset availability.
- Use `getleads_list_funding_signals` and `getleads_list_acquisition_signals` for company event research. Inspect current Deepline pricing per returned signal.

## Authentication and provider billing

Every operation uses the customer’s GetLeads API key in the `X-API-Key` header. Count and metadata reads are free through Deepline. Billable result operations charge per successful contact or signal; inspect the exact action’s current Deepline pricing. The connected GetLeads account may also impose its own limits. Use `deepline billing balance` for the Deepline balance.

Provider-managed exports and CSV uploads, deprecated batch aliases, follower orders, profile monitoring, and provider balance or usage endpoints are disabled in the catalog with an explanation. Manage those directly in GetLeads. Deepline does not expose provider balances, wallet costs, or usage totals in results.

API reference: https://app.getleads.io/openapi.json
Website: https://www.getleads.io/
