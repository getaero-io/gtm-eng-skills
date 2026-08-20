# Affinity API V2

Use these actions only with the workspace's connected Affinity API key.

All actions target Affinity API V2 and pin version `2026-07-15`. Prefer reads
before writes when resolving IDs. List, person, company, opportunity, note, and
field IDs are provider identifiers, not display names.

Actions whose names or descriptions say create, update, merge, send, or delete
change the connected Affinity workspace. Confirm the intended resource and
payload before executing them. Affinity applies the connected user's resource
and endpoint permissions.

Pagination, filters, beta status, and required permissions come from the dated
official Affinity OpenAPI contract. Handle 429 responses with backoff because
Affinity limits each authenticated user and also applies account-level monthly
and concurrency limits.
