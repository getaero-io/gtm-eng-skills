Use EmailBison read endpoints to inspect campaigns, sender email accounts, replies, lead state, tags, and warmup state before making writes.

Prefer targeted campaign/lead operations over workspace/admin operations. Mutating workspace, token, sender account, webhook, and delete operations require the user's own credential and should be used only when the requested workflow explicitly needs them.

Do not expose EmailBison team credit balances as customer-facing provider spend. Account details and balance fields stay internal, and there is no shared Deepline balance monitor for EmailBison because API keys are customer-specific.
