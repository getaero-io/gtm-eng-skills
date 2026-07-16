# Browserbase Agent Guidance

Use Browserbase Search when you need web results without opening a browser.
Use Browserbase Fetch when you need page content and do not need interaction.
Use sessions when the caller will connect Playwright, Puppeteer, or another CDP
client to a managed browser. Public session creation disables Browserbase logs
and recordings and does not accept contexts, extensions, certificate IDs,
external proxy credentials, project IDs, or arbitrary metadata.

Do not plan workflows around `browserbase_update_context`; live Browserbase API
validation returned a deprecation 404 for API context uploads, so Deepline keeps
that operation covered but disabled.

Do not use Browserbase Agents for customer workflows. Agent runs accept
shared-project resources and sensitive free-form data without a tenant-scoped
provider boundary or a zero-retention control, so Deepline disables this tool.

This connector uses Deepline-managed Browserbase credentials. Customers are
charged Deepline credits. Never expose Browserbase provider spend.
