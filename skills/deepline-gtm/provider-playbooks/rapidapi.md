Use RapidAPI when a registered marketplace listing covers the data you need. RapidAPI is a marketplace like Apify: one Deepline-managed key reaches every listing Deepline is subscribed to, but each listing bills against its own plan, so only listings registered in Deepline can be called.

- Prefer the typed listing tools first: `rapidapi_google_web_search` for Google organic results and `rapidapi_google_image_search` for Google Images. They validate inputs, unwrap the listing's response envelope, and publish an exact per-page price.
- Use `rapidapi_list_listings` (free) when you do not know which listings or endpoints exist. It returns each listing's host, documented endpoints, required inputs, and the typed tool for each endpoint.
- Use `rapidapi_request` only for an endpoint on a registered listing that has no typed tool yet. Pass the listing `host` (or slug), the `path`, and `query` or `body`. Hosts that are not registered are rejected before any call because Deepline cannot price them; ask the Deepline team to register a listing you need.
- Every call is billed per RapidAPI request. Paginated endpoints bill one request per page: start with `pages: 1` and raise it only when you need more than about 20 results, because a larger `pages` value re-bills the earlier pages.
- An empty result set from a search listing is a completed search, not an error, and it is still billed. Do not retry it automatically.
- `billed_requests` in every result is the count the listing reported in its `X-RapidAPI-Billing` header. Deepline settles the call from that count; when the header is absent it charges the requested count.
- Upstream 401 means the RapidAPI key is not subscribed to that listing. 404 and 410 come back as `ok: false` with the upstream body so you can inspect them; 429 and 5xx stay loud so the shared retry policy applies.
- Deepline paces calls to the smallest paid plan's per-second limit across the provider (5 requests per second today); bursts wait briefly for a slot instead of receiving a synthetic 429.

## Examples

```bash
# See which listings and endpoints are registered
deepline tools execute rapidapi_list_listings --payload '{}'
```

```bash
# Typed Google web search, one page (about 20 results)
deepline tools execute rapidapi_google_web_search --payload '{"query":"best laptop 2026","pages":1,"country":"us"}'
```

```bash
# Generic call to a registered listing endpoint
deepline tools execute rapidapi_request --payload '{"host":"real-time-google-search-api","path":"/api/v1/google-search/image","query":{"q":"best laptop 2026"}}'
```
