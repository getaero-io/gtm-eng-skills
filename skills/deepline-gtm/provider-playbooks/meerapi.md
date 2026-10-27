# Meer API

- Meer checks a phone number against its country's national do-not-call register. It answers `do_not_call` true or false. It does NOT report whether a number is valid, its line type, or its carrier. Do not use it as a phone validity or line-type validator; use a phone validator for that.
- Good fit as a compliance gate after phone discovery and validation: drop or flag numbers with `do_not_call: true` before dialing or texting.
- Send E.164 with the national leading zero dropped (UK 01000822380 is +441000822380). Deepline rejects numbers that are not E.164 (leading `+`, digits only) before calling Meer, because Meer charges for numbers its register marks invalid. Unsupported countries return a 422 listing supported countries.
- Requires your own Meer API key. Deepline does not bill for Meer; Meer charges credits to your account and the cost varies by country. The response does not include the credit cost; see your Meer dashboard.
- Webhook mode (`webhook_url`) and the reseller `X-Forwarded-Host` header are not exposed. Calls are synchronous.
- `meerapi_get_usage_stats` reads your request counts (total, monthly, by country) and is free. Billing-period credit usage is not exposed.
