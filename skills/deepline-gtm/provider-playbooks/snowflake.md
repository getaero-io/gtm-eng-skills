Use Snowflake when the task requires querying an organization's warehouse data.

Prefer `snowflake_run_semantic_query` when a saved semantic layer exists or the user asks for business metrics, dimensions, filters, funnels, or model-defined entities. The semantic query tool renders the stored Snowflake semantic layer into SQL and returns both rows and the rendered SQL for inspection.

Use `snowflake_run_query` only when the user provides raw SQL, asks for direct SQL, or the semantic layer does not cover the requested analysis. Never expose Snowflake warehouse spend as Deepline spend.
