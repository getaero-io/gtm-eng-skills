# Polymarket guidance

Use Polymarket for read-only prediction-market data: what a market asks, what it is priced at, how that price moved, and how it resolved. There is no trading.

Identifiers differ by tool, and all of them come from a market record:

- `id` (numeric market id): `polymarket_get_market`.
- `clobTokenIds` (one token per outcome, in the same order as `outcomes`): `polymarket_get_price`, `polymarket_get_midpoint`, `polymarket_get_spread`, `polymarket_get_order_book`, `polymarket_get_price_history`, `polymarket_get_batch_price_history`.
- `conditionId` (0x hash): the `market` input of `polymarket_list_trades`, `polymarket_get_holders`, `polymarket_get_open_interest`.
- event `id`: `polymarket_get_live_volume`.

1. Find markets with `polymarket_search` (keyword) or `polymarket_list_markets` (filters). Search returns events with nested `markets`.
2. A market record already carries current prices in `outcomePrices`, so pricing many markets needs no per-token call. Use `polymarket_get_midpoint` or `polymarket_get_price` for a fresh single quote, and `polymarket_get_spread` or `polymarket_get_order_book` to judge whether a thinly traded price is meaningful.
3. For past prices, call `polymarket_get_price_history` with the outcome token as `market`. Use `interval` (`1h`, `6h`, `1d`, `1w`, `1m`, `max`) with a `fidelity` in minutes; an explicit `startTs`/`endTs` window longer than a few weeks is rejected as too long, so prefer `interval: "max"` with a coarse `fidelity` such as `1440` for long ranges. History remains available after a market resolves.
4. For past results, call `polymarket_list_markets` with `closed: true`. A resolved market has `umaResolutionStatus: "resolved"` and `outcomePrices` of `1` for the winning outcome and `0` for the others.

Polymarket sends `outcomes`, `outcomePrices`, and `clobTokenIds` as JSON-encoded strings; Deepline results return them as arrays, index-aligned with each other. Prices are probabilities between 0 and 1, usually decimal strings. Timestamps in price history (`t`) are unix seconds.

In `polymarket_get_holders` the top-level `token` of each group is masked as `[REDACTED]` by Deepline's generic secret filter. Read the outcome token id from `holders[].asset` instead, and the outcome from `holders[].outcomeIndex`.
