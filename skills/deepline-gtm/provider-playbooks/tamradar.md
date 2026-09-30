# Deepline Agent Guidance

Use Deepline monitor tools for customer-facing Deepline workflows. Deepline provider actions in the integration catalog are internal adapter operations used by monitor deployment, status checks, update polling, webhook diagnostics, and cleanup.

Do not call the generated Deepline lifecycle operations directly from public play or agent flows. Start from monitor capabilities such as `deepline_native.company_radar`, `deepline_native.contact_radar`, or `deepline_native.industry_radar`, then let Deepline manage upstream radar ids, polling, billing presentation, and event emission.

**Exception: `deepline_native_get_funding_updates`.** This one action is a public, standalone tool, not an internal monitor adapter. Call it directly to fetch new funding-round updates as JSON — no monitor deploy step required. It is scoped to a single Deepline-managed funding-rounds feed and costs a flat $0.10 per call regardless of how many updates (up to 100) come back. Use `since` to filter by discovery time and `cursor`/`limit` to page through results.
