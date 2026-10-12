Find a verified business email using `trykitt_find_email` with `fullName` and `domain`. Optional `linkedinStandardProfileURL` helps resolve names. Found emails are already verified. A completed miss returns `email: null` and is free.

Use `trykitt_verify_email` for an existing address. Completed verifications are charged, including unknown/catch-all results. Both tools use synchronous results; `realtime: false`, callbacks, and legacy async job lookup are unavailable.

Connect your own API key to use your TryKitt account without a Deepline provider charge, or use Deepline-managed credentials. Never pass API keys in tool payloads.

Use the shared `email_status` getter for verification decisions. `valid-risky` and undocumented verdicts produce unknown/hold; inspect the preserved raw `validity` rather than assuming catch-all or confirmed deliverability.
