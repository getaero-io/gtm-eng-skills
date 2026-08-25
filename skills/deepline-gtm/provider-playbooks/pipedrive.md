# Pipedrive

Use Pipedrive only with the workspace's own API token. Start with read operations such as listing users, pipelines, stages, or searching records to discover identifiers before writes.

Create, update, archive, convert, and delete operations modify customer CRM data. Inspect the generated tool description and required identifiers before executing them. List endpoints use cursor pagination; pass the returned cursor to continue. Pipedrive also applies an account token budget whose per-operation cost is documented as `x-token-cost` in the upstream API specification.
