# Socrata Open Data

Query any Socrata-hosted government open-data portal. Free, keyless, and the
same query grammar everywhere.

## What this covers

Socrata powers a large share of US city, county, and state open-data portals.
Common dataset families:

- Building permits and construction approvals
- Business licenses and registrations
- Restaurant and food-safety inspections
- Code enforcement and property violations
- 311 service requests

Coverage is per-portal, not national. There is no single "US building permits"
dataset — each city publishes its own. Confirm a metro is on Socrata before
promising coverage for it.

## Order of operations

1. `socrata_discover_datasets` — search the cross-domain catalog by keyword.
   Returns the 4x4 id, the hosting domain, and the column list for each match.
2. `socrata_describe_dataset` — read the exact column names and types before
   writing SoQL. Column names are per-dataset and rarely what you would guess:
   NYC DOB permits uses `bin__`, `job__`, and `permittee_s_business_name`.
3. `socrata_query_dataset` — run the query.

Skipping step 2 is the most common way to waste calls. A wrong column name
returns a 400 (`query.soql.no-such-column`), not an empty result.

## Addressing

Every dataset-scoped call needs **both** `datasetId` and `domain`:

```
datasetId: ipu4-2q9a
domain:    data.cityofnewyork.us
```

The domain is a routing input — it selects the host, and is not forwarded as a
query parameter. Passing a 4x4 without its domain is rejected at validation.

## SoQL notes

- `$select=count(*)` is the cheapest way to size a dataset before pulling it.
- `$where` uses SQL-ish syntax with single-quoted literals:
  `borough='BRONX' AND issuance_date > '2026-01-01'`.
- `$limit` is capped at 50,000 per request. Socrata itself will happily stream a
  270 MB response to an uncapped request; the cap fails loudly instead so you
  paginate deliberately.
- `$order` defaults to `:id` when unset. Do not remove it when paginating —
  Socrata's row order is otherwise unstable across pages, which silently
  duplicates and drops rows.

## Joining to accounts

Most of these datasets key on **address**, not on a company identifier. Address
normalization is the main correctness risk; expect meaningful match loss when
joining raw address strings to a CRM. Where a dataset exposes a parcel or
building identifier (NYC's `bin__`, or `bbl`), prefer it over the address.

Owner and contractor business names are present in permit data and are usable
for fuzzy company matching, with the usual legal-suffix caveats.

## Not every portal is Socrata

Some government portals run CKAN or ArcGIS instead and will not respond to these
endpoints. `data.ca.gov`, for example, is CKAN and returns an entirely different
payload shape. Use `socrata_discover_datasets` to confirm a dataset is on the
Socrata network before building against it.

## API version and credentials

This connector uses keyless SODA 2.1. Upstream now identifies SODA 3.0 as the
latest API; its query endpoint requires authentication or an application
token. Do not substitute SODA 3.0 paths into these tools. There is no managed
credential environment variable for this connector, and optional upstream
`X-App-Token` headers are not currently exposed by it.
