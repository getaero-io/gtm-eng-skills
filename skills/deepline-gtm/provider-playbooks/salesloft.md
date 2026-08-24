# Salesloft agent guidance

Salesloft tools use the workspace's own Salesloft API key. Deepline does not charge for provider usage. The connected key must include every scope required by the operations an agent calls.

Prefer read operations before mutations. Resolve stable Salesloft IDs with list or fetch operations, then pass those IDs to create, update, delete, cadence-membership, activity, or workflow operations. Read pagination metadata and continue paging when a complete result set is required.

Creation, update, deletion, sending, redaction, import, bulk-job, webhook, and signal operations change customer data or start provider work. Confirm the intended records and payload before calling them. The operation description and generated schema are the source of truth for required identifiers and fields.

Operations documented only as `multipart/form-data` are registered but disabled because the shared V2 executor cannot yet encode multipart requests safely. Do not substitute JSON or work around the disabled status.
