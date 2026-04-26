# Serper Agent Guidance

Use Serper when you need live Google results fast and broad recall matters more than source-specific extraction.

Prefer `serper_google_search` for:
- broad web research
- newsy or changing facts
- finding a company, person, or topic before deeper enrichment
- collecting candidate URLs to hand off to extraction tools

Prefer `serper_google_maps_search` for:
- local business discovery
- location-aware company lookups
- phone, address, rating, website, or CID retrieval

Practical guidance:
- Start with Serper before heavier browser or extraction workflows when you do not yet know the right destination URL.
- Treat Serper as a discovery and recall layer, then pass strong hits into structured tools like Firecrawl, Apify, or provider-specific enrichments.
- Use Maps search when the user cares about storefronts, service areas, offices, or other local entities.
- Expect live-search variability. If a result is important, validate it with the returned URL or a follow-up fetch.
