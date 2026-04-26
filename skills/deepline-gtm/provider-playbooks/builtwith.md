# BuiltWith Guidance

- Use `builtwith_domain_lookup` when you already know the domain and need live/current technographics. The handler defaults `live_only` to true; set `live_only=false` only when historical detections matter.
- Use `builtwith_vector_search` to discover the exact BuiltWith technology label before `builtwith_lists` or `builtwith_trends`. Free-text tech guesses often miss if the BuiltWith canonical name differs.
- Use `builtwith_bulk_domain_lookup` for row-heavy domain work. It auto-polls queued jobs by default and normalizes both sync and async paths to the same `results[]` shape.
- The batch compiler only coalesces `builtwith_domain_lookup` calls when the request can be losslessly represented by the native bulk API. Requests using `trust`, `no_attr`, or date-range filters stay single-call.
- `builtwith_lists` is best for account sourcing by technology; `builtwith_relationships`, `builtwith_redirects`, and `builtwith_tag_lookup` are better for niche infrastructure signals and related-domain expansion.
