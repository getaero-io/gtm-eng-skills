# MillionVerifier

Verify one email per call. Use Play rows for multiple emails; bulk operations are disabled pending file, tenant ownership, and billing contracts.

Keep `ok`, `invalid`, `disposable`, `catch_all`, and `unknown` distinct. `catch_all` and `unknown` do not prove deliverability. A provider error or inconsistent verdict is a failed verification. Repeat verification can consume provider credits again.

The free BYOK connection probe validates the connected customer's key internally and returns status only. Account balances do not establish per-call usage and are not included in the public response.
