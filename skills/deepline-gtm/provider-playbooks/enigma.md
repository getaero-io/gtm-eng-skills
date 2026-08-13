# Enigma

Card-spend revenue for US business locations. The only source in the Deepline
catalog that prices a **private** SMB or multi-location group.

## When to use it

- Sizing a private business or multi-location group that files no public financials
- Ranking local-services accounts by revenue per location instead of review count
- Detecting decline (negative growth) as an outbound trigger
- Segmenting by average ticket, which separates business models better than
  location count does

## Contract notes

`enigma_brand_revenue_search` resolves a brand name to its operating locations
and returns per-location card metrics plus group-level aggregates.

**Always pass `state`.** Enigma matches brand names nationwide, so an ungated
lookup mixes unrelated operators that happen to share a name. `state` is applied
as a post-response filter on the resolved address; Enigma's own
`searchInput.address` is a match hint, not a filter, and returns zero results
when supplied alone.

## Reading the numbers

**Use `median_yoy_growth`, never the mean.** Mean growth is corrupted by new
locations entering the panel. A 10-location group in the field test showed +461%
mean growth driven entirely by one ramping new shop at +3915%; its median was a
sober +7%. Growth values are ratios, not percentages: `0.0721` means +7.21%.

**`revenue_per_location_median` beats the average** for groups with a wide spread
between flagship and satellite locations.

## Coverage caveat

Card spend covers card transactions only. It **understates invoiced fleet and
commercial work**, which is a real share of revenue in verticals like auto
repair, HVAC, and plumbing. Treat these figures as directional floors, not
audited revenue, and never present them to a customer as their actual revenue.
