# Test Unhinted Provider

Synthetic no-bill provider for exercising adaptive backpressure when an upstream rate limit is not published as a queue hint.

Use `test_unhinted_low_rps` only in internal regression plays and local tests. It intentionally returns upstream 429 errors when callers exceed the input-configured window.
