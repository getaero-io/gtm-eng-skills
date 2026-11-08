# treg

Connect a team API key from the treg dashboard. Personal sign-in tokens are
not supported. Authentication uses `X-Treg-Token`,
never an upstream Authorization header.

Search with `treg_catalog_search` and inspect an endpoint with
`treg_catalog_endpoint` before calling it. Inspect the required parameters,
HTTP method, cost and asynchronous behavior. Pass the catalog endpoint ID or
registered tool name/path as `rest`, query parameters as `query`, and JSON
request content as `body` to the matching `treg_call_*` tool.

Proxy calls may spend the connected treg account's balance and may create,
change, send or delete upstream data. Deepline adds no provider charge. The
catalog and endpoint details contain treg's current endpoint-specific prices.
Object and array responses retain the upstream shape. The shared execution
runtime represents a top-level JSON null or empty response as an empty object.
A proxy response may be a job
receipt; asynchronous provider workflows require the documented status/result
calls and are not automatically polled. Non-JSON, multipart, streaming, custom
header forwarding and server-side CLI execution are not exposed.
Redirect responses fail instead of being followed, so the treg team key cannot
be forwarded to an upstream redirect destination.

`treg_list_calls`, `treg_get_call` and `treg_get_call_result` inspect existing
team calls. A retained result is not guaranteed: treg returns storage status
and a reason when the archive has no result.
