# Notion

Connect an internal connection token or personal access token with access to the target workspace. Search for a page or data source, then use its ID for reads and queries. Page creation, page updates, and appending child blocks change workspace content. Paginated lists return a next cursor; pass it to retrieve subsequent results.

The initial page creation tool supports synchronous creation only; template and allow_async options are not exposed. Data source queries use the current `/v1/data_sources/{id}/query` path even though the upstream operation ID says post-database-query. Search page_size must be an integer from 1 through 100. The API version is pinned centrally; do not pass a Notion-Version field.
