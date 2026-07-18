# Podscan

Podscan indexes and transcribes the podcast ecosystem and exposes full-text
search across every transcript.

## When to use

- "Find every podcast where {topic / brand / competitor} was discussed."
- "Who talked about {subject} on a podcast?" — episode transcripts carry
  structured host/guest metadata (name, company, occupation, industry).
- Social-listening / brand-monitoring over spoken audio, not just text.
- Sourcing warm outbound targets: podcast guests who discussed your category
  are high-intent, self-identified buyers.

## Operations

- `podscan_episodes_search` — full-text transcript search. Returns matching
  episodes with the matched `_search_highlight` snippet, the parent `podcast`,
  `metadata.hosts[]` / `metadata.guests[]` (name + company + occupation), and
  AI-extracted `topics[]` with sentiment. Use quoted phrases for precision,
  e.g. `"customer interviews"`. Full transcripts are omitted by default (they
  are large); pass `include_transcript: true` only when you need them.
- `podscan_podcasts_search` — discover shows by title/description.

## Tips

- Quote multi-word phrases to avoid loose matches.
- `pagination.total` gives the corpus-wide mention count for a query — useful
  for sizing before pulling pages.
- `language` filters by ISO 639-1 code (e.g. `en`) and is honored by the API.
  Date and category filtering are not currently exposed because Podscan's
  documented search surface does not reliably support them.
- Turn guests into contactable leads by piping `guest_name` + `guest_company`
  into LinkedIn resolution and an email waterfall.

## Auth & billing

Deepline supplies the Podscan credential (`PODSCAN_API_KEY`). Deepline bills one
Podscan credit ($0.01) per successful search — a well-formed response with at
least one result. Zero-match searches are free; a malformed provider response is
rejected rather than billed as an empty result.

## Rate limits

Podscan rate-limits aggressively (roughly 10 req/min on trial plans, higher on
paid). The connector applies a conservative shared limit and surfaces upstream
429s; prefer `deepline enrich`, which paces requests automatically.
