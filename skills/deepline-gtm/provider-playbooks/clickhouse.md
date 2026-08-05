# ClickHouse Cloud

Use this provider only with the workspace's own ClickHouse Cloud API Key ID and key secret. Start with list or get operations to discover organization and service IDs.

To access warehouse data, first create a saved Query Endpoint in ClickHouse, then call `clickhouse_query_endpoint_run_get` for simple scalar variables or `clickhouse_query_endpoint_run_post` for complex variables. These actions execute saved SQL, not arbitrary SQL. The selected database role controls the endpoint's data access.

Treat writes with care. Service, backup, API-key, member, ClickPipe, ClickStack, and Postgres operations can change or delete customer resources. A saved Query Endpoint can also write data when its configured SQL and database role allow it. Use a least-privilege API key: ClickHouse developer keys are read-only for assigned services, while admin keys can make changes.
