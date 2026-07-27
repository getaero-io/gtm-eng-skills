# ClickHouse Cloud

Use this provider only with the workspace's own ClickHouse Cloud API Key ID and secret. Start with list or get operations to discover organization and service IDs. The API manages cloud resources, not SQL queries inside a ClickHouse database.

Treat writes with care. Service, backup, API-key, member, ClickPipe, ClickStack, and Postgres operations can change or delete customer resources. Use a least-privilege API key: ClickHouse developer keys are read-only for assigned services, while admin keys can make changes.
