# GetLeads API Guidance

Use GetLeads for B2B contact search and enrichment, company colleagues and decision-makers, and funding or acquisition signals.

## Choose the endpoint

- Use `getleads_count_contacts` to estimate a contact search before calling `getleads_search_contacts`. Counts and dataset metadata lookups are free in the provider API.
- Use `getleads_search_contacts` for filtered prospect lists. Request only the columns needed, and keep pages small because Deepline charges 1.625 credits per successfully returned contact at the standard $0.10 per credit rate; GetLeads may separately apply its own account credit rules.
- Use `getleads_lookup_colleagues` or `getleads_lookup_decision_makers` when you already know a company domain or LinkedIn company URL. Deepline charges 1.625 credits for each contact returned.
- Use `getleads_lookup_phone` or `getleads_batch_phone_lookup` when phone numbers are the lookup key. Deepline charges 1.625 credits for each successfully matched contact.
- Use `getleads_enrich_from_linkedin`, `getleads_enrich_from_email`, or `getleads_enrich_from_person` for contact enrichment. Deepline charges 1.625 credits for each successful enrichment result.
- Use `getleads_get_filter_values` and `getleads_get_available_columns` to discover accepted filter values and field names. `getleads_get_contacts_health` checks dataset availability.
- Use `getleads_list_funding_signals` and `getleads_list_acquisition_signals` for company event research. Deepline charges 1.625 credits per returned signal.

## Authentication and provider billing

Every operation uses the customer’s GetLeads API key in the `X-API-Key` header. Count and metadata reads are free through Deepline. Billable result operations cost 1.625 Deepline credits per successful contact or signal, based on GetLeads’ separate public $0.125 per delivered website visitor lead offer plus a 30% Deepline markup. GetLeads does not publish a per-result USD price for these API operations and may separately apply the connected account’s own plan and credit rules. This Deepline benchmark is not a GetLeads API rate or a measure of actual provider spend.

Provider-managed exports and CSV uploads, deprecated batch aliases, follower orders, profile monitoring, and provider balance or usage endpoints are disabled in the catalog with an explanation. Manage those directly in GetLeads. Deepline does not expose provider balances, wallet costs, or usage totals in results.

API reference: https://app.getleads.io/openapi.json
Website: https://www.getleads.io/
