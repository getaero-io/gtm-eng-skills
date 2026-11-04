# Deepline Agent Guidance

Use Deepline monitor tools for customer-facing Deepline workflows. Deepline provider actions in the integration catalog are internal adapter operations used by monitor deployment, status checks, update polling, webhook diagnostics, and cleanup.

Do not call the generated Deepline lifecycle operations directly from public play or agent flows. Start from monitor capabilities such as `deepline_native.company_radar`, `deepline_native.contact_radar`, or `deepline_native.industry_radar`, then let Deepline manage upstream radar ids, polling, billing presentation, and event emission.

<!-- skill-tool-compat: deepline_native_get_funding_updates -- Hidden while it is retired (KAR-120); existing exact-ID calls and Plays remain supported, and this guide does not select it for new workflows. -->

**Retiring: `deepline_native_get_funding_updates`.** This standalone funding-rounds feed is hidden from tool search and is being retired. Existing exact-ID calls and Plays keep working: it returns funding-round updates as JSON from one Deepline-managed feed, at a flat $0.10 per call for up to 100 updates, filtered by `since` and paged with `cursor`/`limit`. Do not choose it for new workflows.

The radar preview action is internal too. Customers reach it only through `deepline monitors preview`, which bills it per returned update at the monitor finding price; never call it directly.
