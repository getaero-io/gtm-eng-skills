# Sourcing arms — Deepline tools, costs, graduation

Tool IDs and prices confirmed with `deepline tools describe` on 2026-09-30. Prices
and contracts drift — re-run `describe` and read `pricing` before quoting.

## Category discovery — Google Maps search

`serper_google_maps_search` — 0.04 credits per returned place; one call returns a
fixed ~20 places and each page bills separately.

- Input: `query` (`"<category> in <location>"`), `page` (1-indexed), `gl`/`hl`
  (default `us`/`en` — pin them; an unpinned locale leaks localized UI strings into
  names), optional `ll` (`@lat,lng,zoom`) to anchor the map.
- Output `places[]`: `title, address, category, rating, ratingCount, phoneNumber,
  website, cid, latitude, longitude, position`. Structured — no scraping, no
  selectors to rot. `cid` is the place-level dedupe key.
- Paginate only while the previous page came back full; a short page is the end of
  the market for that query, not a reason to loop.
- Many (category, location) pairs at once: `serper_google_maps_search_batch`
  (`queries`, up to 100 per request, same per-result rate).

Alternatives on the same job:
- `openwebninja_localbusiness_search` (0.06/result): `subtypes`, `verified`,
  `business_status` filters (drop closed places at the source), optional
  `extract_emails_and_contacts`. Map-bounded variants:
  `openwebninja_localbusiness_search_in_area` (`lat, lng, zoom`) and
  `openwebninja_localbusiness_search_nearby` (`lat, lng, radius`).
- `openmart_search_businesses` (0.13/result): Openmart store records with
  `location`, `ownership_type`, `min_locations`/`max_locations`,
  `min_overall_rating`, `min_total_reviews`, `has_website`, `exclude_root_domains`.
  The location-count and ownership filters do the franchise screen in the query.
  Field names inside `content` vary; check the first response before keying on them.

## Brand locations — Openmart

`openmart_enrich_company` (0.13 per returned record): input the PARENT's `website`
(top-level domain, e.g. "subway.com") or `social_media_link`, plus `location` and
`limit`. It resolves a KNOWN brand to its store records in a geo — use it for the
brand-grain job and franchise mapping, never expect it to answer "gyms in Brooklyn".
`openmart_search_brands` returns one row per brand/company instead of one per store.
Openmart bills successful results only; no-result calls are not billed. Treat
`null` arrays in brand responses as empty.

Owner/operator at a location: `openmart_find_people` (async, 1.26 per result) or
the `smb-owner-finder` route — hand off to find-decision-makers-at-company
semantics.

## Depth on survivors

- `openwebninja_localbusiness_business_details` (usage-priced; `business_id` from
  an OpenWebNinja search): hours, emails/contacts with `extract_emails_and_contacts`.
- `openwebninja_localbusiness_business_reviews` (0.06 per review): review text.
- Business mailbox: `prebuilt/smb-business-email` / `-batch` (Openmart candidates
  validated with LeadMagic).

Maps rows already carry rating, review count, phone and website, so most asks need
no paid depth at all. Survivors only — the funnel exists so this spend is minimal.

## Dedupe mechanics (free; the linchpin)

- Domain normalization: strip scheme/www/query, registrable label via a
  PUBLIC-SUFFIX-AWARE extraction (a naive split kills co.uk/com.au-family domains),
  collapse subpaths (`brand.example/locations/providence` → `brand.example`).
- Grain: location grain keys on name+address (site-less SMBs are normal); brand
  grain collapses on normalized domain / brand name with `location_count` carried.
- Multi-level dedupe for bulk hauls: place id (`cid`) → lat/lon → name+address (the
  order matters; each level catches what the previous missed). Arms overlap, so
  dedupe across arms too.

## Scale + graduation

- Ad-hoc sweep ceiling: ~3 cities / ~10 pages per location. Beyond that, or for any
  recurring refresh, write a Deepline play over a CSV of (category, location)
  queries: one `serper_google_maps_search` (or `openmart_search_businesses`) step
  per row, a `run_javascript` step for normalize/dedupe, then
  `deepline plays run <file>.play.ts --input '{"csv":"queries.csv"}'` and
  `deepline runs export <run-id> --out businesses.csv`. Pilot 2-3 rows first.
- US legal owner / registration behind a storefront: `enformion_business_search`
  (3.5 credits per lookup with a result) or `govfiles_create_local_business_batch`
  — depth, not discovery.
