# GovFiles

Use company search or officer search to discover US entities across supported
jurisdictions. Use company lookup when the jurisdiction code and registry
number are already known. For physical locations, submit a local-business
batch with 1–500 rows and poll the returned batch id until it is `succeeded`
or `failed`; successful results include the complete result document inline.

GovFiles uses an `X-API-Key` credential. GovFiles provider charges remain on
the connected account, while Deepline separately charges Deepline credits for
billable search, direct lookup, and matched local-business operations.

## OpenSOSData migration

For an OpenSOSData-style legal-entity lookup with `entity_name` and `state`,
use `govfiles_search_companies_v2` with `q` set to the entity name and the
state's GovFiles jurisdiction code (for example, `us_de`), then use
`govfiles_get_company_v2` with the returned jurisdiction and registry number.
Use `govfiles_search_officers_v2` when the workflow needs person-to-company
relationships.

For OpenSOSData bulk local-business ownership enrichment, use
`govfiles_create_local_business_batch` and then
`govfiles_get_local_business_batch`. GovFiles accepts 1–500 rows per batch,
so a 1,000-row OpenSOSData request must be split into at least two batches.
Each row needs a business name and address; address-free name/state input is
not a semantic drop-in for local-business matching. Batch results can include
operator legal names, restaurants, and people, and provider billing applies
to rows that return at least one person. The contracted provider price is $0.15
per matched location; Deepline applies its standard customer markup on top of
that provider amount. Search rows are $0.01 each and direct entity lookup is
one $0.01 provider credit; no-result searches and documented not-found lookups
are not charged.
