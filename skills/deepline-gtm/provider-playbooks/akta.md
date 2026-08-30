# Akta agent guidance

Start with `akta_company_search`. It accepts a company name, website, or Akta UUID and avoids guessing which identifier a later company action will resolve.

Use `akta_industry_search` to translate a plain-language topic into Akta industry codes before constructing an industry-filtered news request.

Treat the two search actions as resolvers:

- inspect all returned matches;
- prefer an exact website match over a name-only match;
- keep the Akta UUID for subsequent lookups;
- handle both an empty `data` array and a no-result status.

If company search returns no match, do not work around the disabled Company Addition action. `akta_request_status` accepts only a request ID created through an approved Akta flow.

Do not work around an unavailable action. Paid actions are intentionally gated until an internal account proves the runtime charge and response shape.

For Product Reviews, do not convert the `products` array into a comma-separated string. The wire format repeats the query key.

For Company Data and News filters, preserve comma-separated strings exactly as documented.
