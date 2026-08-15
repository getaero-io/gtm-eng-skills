# Affinity

Call `affinity_get_auth_whoami` first to verify the workspace and API key.

Use search and get actions to resolve Affinity IDs before mutating data. Affinity list entries are rows that connect a person, organization, or opportunity to a list. Field values belong to entities or list entries and need the matching field and entity identifiers.

Create, update, delete, file-upload, and webhook actions change customer data. Confirm the target and payload first. Use the rate-limit action when planning a large sync. Affinity recommends an initial REST backfill followed by webhooks for incremental updates.
