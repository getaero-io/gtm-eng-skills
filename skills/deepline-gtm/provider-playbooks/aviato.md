# Aviato

Use `aviato_get_balance` first when validating credentials or checking account state.

Use preview enrichment (`preview: true`) when you only need free identity resolution fields. Non-preview person/company enrichment and bulk enrichment can consume Aviato credits.

For `aviato_company_search` and `aviato_person_search`, use Aviato DSL shape:
`{ "dsl": { "offset": 0, "limit": 5, "filters": [{ "name": { "operation": "textcontains", "value": "Polychain" } }] } }`.
Do not use `{ "field": "name", "operation": "contains", "value": "Polychain" }`; Aviato rejects that filter object.

Do not use disabled Aviato operations until Aviato supplies the complete endpoint credit ladder and the purchased-credit USD rate. Disabled operations are present only to keep OpenAPI coverage explicit.
