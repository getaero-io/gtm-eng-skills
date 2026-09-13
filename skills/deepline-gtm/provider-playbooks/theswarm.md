# The Swarm

Use the workspace's own The Swarm API key. Deepline does not bill for The Swarm usage; the connected account's The Swarm plan and API permissions still apply.

Search returns profile or company IDs; fetch retrieves records for IDs, LinkedIn names, or numeric/entity identifiers supported by that action. V3 fetch uses `linkedin_names`, not the similarly named aliases found in some prose documentation. Fetch batches allow at most 1,000 identifiers. Search uses Elasticsearch Query DSL; when `stable_pagination` is true, the provider documentation requires `limit: 1000`.

Use `linkedinName` for beta profile/company posts and refreshed profile requests. Pass the returned post's `urn` into comments, reactions, or reshares. Request and response pagination names differ by endpoint; use its exact contract. Company posts use `page`, profile posts use `paginationToken`, and V3 search/relationships use `pagination_token`.

Relationships return connection information scoped to the API-key team. Live responses confirm an object containing `items`, `count`, `total_count`, and an optional `pagination_token`. Provider responses are preserved without flattening or renaming their fields.

Partner mapping, child-team switching/creation, and connector addition are unavailable in this connector. Connector addition is asynchronous but has no documented completion-status API; it is not safe to claim completed mapping from HTTP 202 acceptance.
