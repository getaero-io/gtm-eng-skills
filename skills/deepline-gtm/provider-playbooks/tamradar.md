# TAMRadar Agent Guidance

Use Deepline monitor tools for customer-facing TAMRadar workflows. TAMRadar provider actions in the integration catalog are internal adapter operations used by monitor deployment, status checks, update polling, webhook diagnostics, and cleanup.

Do not call the generated TAMRadar lifecycle operations directly from public play or agent flows. Start from monitor capabilities such as `tamradar.company_radar`, `tamradar.contact_radar`, or `tamradar.industry_radar`, then let Deepline manage upstream radar ids, polling, billing presentation, and event emission.
