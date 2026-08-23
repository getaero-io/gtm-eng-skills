Use BigQuery when the task requires querying an organization's warehouse data.

BigQuery runs over Google's HTTPS API. Prefer OAuth for user-delegated access
and service accounts for workload access. Never ask users to base64-encode a key
or write it to a temporary file. Use `maximumBytesBilled` when the user supplies
a scan budget.

Prefer `bigquery_run_semantic_query` when a saved semantic layer exists or the user asks for business metrics, dimensions, filters, funnels, or model-defined entities. The semantic query tool renders the stored BigQuery semantic layer into SQL and returns both rows and the rendered SQL for inspection.

Use `bigquery_run_query` only when the user provides raw SQL, asks for direct SQL, or the semantic layer does not cover the requested analysis. Leave `write` unset for read-only `SELECT` or `WITH` SQL. Set `write: true` only when the user intentionally wants a single statement that may modify or overwrite customer data. Never expose BigQuery warehouse spend as Deepline spend.
