# Dun & Bradstreet

- D&B Direct+ requires a customer consumer key and consumer secret. A Hoovers subscription alone does not prove Direct+ API access.
- Company discovery: criteria search accepts domain, D-U-N-S numbers, registration numbers, SIC industries, employee ranges and location filters. Name lookup uses typeahead with a search term and country.
- Company matching accepts D-U-N-S, or country plus a name, website, registration number, telephone, email or address. Matching returns candidates; match-quality information helps select the intended company. Extended match combines identity resolution and licensed Data Blocks in one request.
- Data Blocks and versions must be licensed to the connected D&B account. Available content depends on that contract.
- Deepline does not bill for D&B API usage. D&B can charge the customer account under its own contract.
- Family tree returns corporate subsidiaries/branches with pagination. Beneficial ownership returns the licensed ownership list or structure, subject to country coverage.
- Entitlements reports what the connected key can access; it does not grant or purchase access. Reference categories and codes decode D&B identifiers used in filters and results.
- Batch, monitoring, the sketch Multi-Process endpoint, contact search, and historical audit are not exposed. Principal/contact information can be requested through licensed Data Blocks.
