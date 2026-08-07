# Amplemarket

Use `amplemarket_get_account_details` to verify a connection.

Use capability-specific actions directly. Prefer people or company search for
prospecting, contacts and accounts for CRM reads and writes, sequences and lead
lists for outbound activation, and tasks or calls for workflow activity. Do not
route REST work through Amplemarket's separate OAuth MCP server.

Read and write actions use the caller's own Amplemarket workspace credential.
Only call mutation actions when the user explicitly asks for the corresponding
workspace change.

Credit-sensitive enrichment, validation, and lead-enrollment workflows are
disabled until Deepline has exact provider-credit exchange rates and runtime
settlement evidence.
