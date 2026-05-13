# DiscoLike Integration Guide

Use DiscoLike for website-first company discovery and domain intelligence.

## Best entry points

1. `discolike_count` when you want a fast volume estimate before paying to retrieve a large result set.
2. `discolike_discover` when you have seed domains or a natural-language ICP.
3. `discolike_bizdata` when you already know the domain and need a firmographic profile.
4. `discolike_match` when you start from a company name and need the best matching domain.
5. `discolike_vendors`, `discolike_publiclink`, `discolike_subsidiaries`, and `discolike_redirects` for relationship mapping.

## Segment behavior

`discolike_segment` is public and synchronous from the agent perspective: it submits DiscoLike's async segment job, polls the provider status endpoint, and returns the completed segment rows when available.

If the sync wait times out, call `discolike_get_segment_status` with the returned `task_id` to retrieve the provider result later. This status call is a free read-only recovery step for tasks created by the same organization; final customer billing is reconciled by Deepline's async provider cron against the original `discolike_segment` billing row.

## Pricing caveat

DiscoLike bills directly in USD and the exact query / record rate depends on the account plan. Records cached within the provider account for 90 days are free on repeat retrieval.
