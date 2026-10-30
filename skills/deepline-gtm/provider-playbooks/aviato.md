# Aviato

Use `deepline billing balance` to check the Deepline balance before billable work.

Use preview enrichment (`preview: true`) when you only need free identity resolution fields. Non-preview person/company enrichment and bulk enrichment can consume Deepline credits.

For `aviato_company_search` and `aviato_person_search`, use Aviato DSL shape:
`{ "dsl": { "offset": 0, "limit": 5, "filters": [{ "name": { "operation": "textcontains", "value": "Polychain" } }] } }`.
Do not use `{ "field": "name", "operation": "contains", "value": "Polychain" }`; Aviato rejects that filter object.

Do not use disabled Aviato operations while their catalog entries report them unavailable. Disabled operations are present only to keep OpenAPI coverage explicit.
