# Gong

Use Gong only with the workspace’s own Access Key and Access Key Secret. Start with read operations for calls, users, and analytics. Write operations can upload recordings, change CRM data, or erase data, so inspect the generated tool description and required identifiers before running them.

Gong limits API access by account. Respect a `429` response and its `Retry-After` header. Cursor-based list responses require passing the returned cursor with the same request inputs.
