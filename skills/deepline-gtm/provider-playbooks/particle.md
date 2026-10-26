# Particle

Connect your own Particle API key (a `pp_` key) before calling these tools.
Particle bills the connected Particle account for each call; Deepline charges
0 credits for Particle calls.

## Slugs are Particle handles

Podcast, company, publisher, and sponsor identifiers are Particle-assigned
handles (for example `all-in`, `apple`). Never construct one from a name.
Resolve first:

- Podcast: `particle_search_podcasts` (by show name), then pass the returned
  `slug` to podcast tools.
- Company: `particle_list_companies` (`q` for name, or `domain`, `ticker`), or
  `particle_get_company` with a known slug or domain. `particle_lookup_entities`
  resolves LinkedIn slugs, tickers, and domains to Particle entities.
- Sponsor: a sponsor ID comes from `particle_list_sponsors` or from the
  sponsor rows inside another advertising response.
- Episode: `particle_list_podcast_episodes` returns the episode id that
  `particle_list_episode_ads` needs.

## Podcast advertising

- Which brands advertise alongside a sponsor: `particle_get_sponsor_co_occurrence`
  (filter with `sponsor_id` or `company_id`).
- A show's advertisers and ad stats: `particle_get_podcast_advertising` and
  `particle_list_podcast_advertising_sponsors`. Advertisers a show could pitch:
  `particle_list_podcast_recommended_sponsors`.
- A company's podcast ad presence: `particle_get_company_podcast_advertising`,
  with `..._advertising_podcasts` and `..._advertising_placements` for detail,
  and `particle_list_company_podcast_recommendations` for shows it could buy next.
- Market-wide: `particle_get_advertising_leaderboard` (the `_preview` variant is
  a fixed trailing-7-day top 10), `particle_get_publisher_advertising_leaderboard`,
  `particle_list_sponsor_trends`, `particle_get_advertising_timeseries`.
- Ads inside one episode: `particle_list_episode_ads`.

Lists return `{data, has_more, cursor}`; pass `cursor` back to page. Cursors
belong to the endpoint that issued them. Every operation here reads data.
