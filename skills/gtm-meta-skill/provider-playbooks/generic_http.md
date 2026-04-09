Use a direct HTTP call when no provider-specific Deepline integration exists.

For safe public API calls, validate:

- `url` is an absolute public URL.
- request method and transport headers are supported.
- exactly one body representation (`body_json`, `body_text`, or `body_form_urlencoded`) is set.

Prefer a dedicated provider when one exists.
