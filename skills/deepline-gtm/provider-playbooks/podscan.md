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

Deepline supplies the Podscan credential (`PODSCAN_API_KEY`). Billing applies per
successful search — a well-formed response with at least one result. Zero-match
searches are free; a malformed provider response is rejected rather than billed
as an empty result. Deepline credit pricing for these actions is generated from
the provider pricing metadata and rendered on the public provider pages.

## Rate limits

Podscan rate-limits aggressively (roughly 10 req/min on trial plans, higher on
paid). The connector applies a conservative shared limit and surfaces upstream
429s. For multi-query or paginated work, call the tools through
`ctx.tools.execute({ id, tool, input, description })` inside a Play so Deepline
owns provider pacing and retries. Run an authorized local workflow with
`deepline plays run --file podcast-research.play.ts --input '{"query":"customer interviews"}' --watch`
after authoring it with that input contract; a supplied Play needs no extra pilot
run. Use `deepline runs get <run-id> --json` to inspect existing results, not a
fresh search or paid repair. Do not bypass provider limits with an external loop.
