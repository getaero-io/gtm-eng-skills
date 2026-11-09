# Reo.dev Write API

Connect your own Reo.dev **Write** API key before calling these tools (Reo:
Settings → Configurations → API Keys → Product Usage API). It is a different
key from the Read key the `reo_*` read tools use; neither works in place of
the other. Deepline charges 0 credits. Every tool writes to the connected Reo
workspace, so confirm the target and contents before calling one.

## Lists

1. `reo_write_create_list` with a unique `name`, `type` (ACCOUNT or
   DEVELOPER), `primaryKey` and `mapping`. It returns the `id` to use as
   `list_id`. A repeated name fails.
2. `reo_write_add_to_list` with that `list_id`, the same `type`, and up to
   1,000 `entities` per call. ACCOUNT lists take domains; DEVELOPER lists take
   emails, LinkedIn or GitHub IDs. `enrich: true` spends Reo credits.

Both need `user`: the email of a user in the Reo workspace. Read lists back
with `reo_list_lists` and `reo_get_list_accounts` / `reo_get_list_developers`.

## Product usage

- Telemetry or call-home events: `reo_write_add_telemetry_event` (one event)
  or `reo_write_add_telemetry_aggregate` (a pre-counted total). Send
  `ip_addr` or `domain`. A single event with no `user_id` (anonymous
  call-home) also needs `user_agent`.
- Product usage: `reo_write_add_product_usage_event` (one user event) or
  `reo_write_add_product_usage_aggregate` (`mode` DOMAIN with `domain`, or
  USER with `user_id` and `user_id_type`).

`activity_type` must be a metric key configured in Reo's Product Usage
Settings, or Reo ignores the data. `event_at` is Unix seconds.

There is no idempotency key: repeating a call records the event again.
