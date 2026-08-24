# Clay

Use Clay only with the workspace's own API key. Start with `clay_get_public_api_me` to confirm the user and workspace. For structured search, call `clay_fields` before `clay_create_filters`, then page with `clay_run`. For advanced query mode, read `clay_query_mode_reference`, create the search with `clay_create_query_mode`, then page with `clay_run_query_mode`.

Routine runs are asynchronous. Call `clay_run_routine`, then poll `clay_get_run_results` with the returned `routine_run_id`. For large JSONL inputs, first request an upload URL, upload the file directly to that URL, start the batch with `clay_start_routine_run_batch`, and poll `clay_get_routine_run_batch_results`.

`clay_query` reads existing Clay table data and is available only on eligible enterprise Clay plans. Deepline does not bill for Clay usage; Clay account limits and charges still apply.
