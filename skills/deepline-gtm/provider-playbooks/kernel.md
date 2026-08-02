# Kernel.ai guidance

Kernel is asynchronous company-data infrastructure. Start one job, save its
`id`, and call only the matching getter until the status is `completed` or
`failed`. Do not loop aggressively. Firmographics can take tens of minutes.

Use entity resolution when you need a stable Kernel company id. Parentage and
firmographics launchers require that id. Use combined when you want identity
resolution plus one or both add-ons in one job.

Do not send personal data unless Kernel has explicitly approved that data and
use case. Do not provide a webhook URL. Deepline has not yet enabled signed
Kernel callback ingestion.

The paid launchers are currently unavailable. Their nominal Kernel-credit
ladder is documented, but the purchased USD exchange rate and Deepline async
refund reconciliation are not configured. Existing job status getters remain
available.
