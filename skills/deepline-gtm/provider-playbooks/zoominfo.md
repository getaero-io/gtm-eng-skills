# ZoomInfo guidance

Use the five search actions to discover candidate records. Use
`zoominfo_lookup` to resolve documented filter values before building searches.

Send the JSON:API envelope exactly as documented:

```json
{
  "data": {
    "type": "CompanySearch",
    "attributes": {
      "companyName": "ZoomInfo"
    }
  }
}
```

Search results preserve the provider's `data`, `meta`, and `links` under the
Deepline result envelope. Read rows from `result.data.data`, pagination metadata
from `result.data.meta`, and pagination links from `result.data.links`. Do not
unwrap or discard pagination metadata.

Deepline charges no credits for ZoomInfo enrichment actions. Do not use customer
credentials for testing; rely on the provider-owned OpenAPI examples unless an
explicit Deepline internal/test Partner App is available.

ZoomInfo tool results retain the provider response in `toolResponse.raw`, including
array-valued response fields such as `company` and `familyTree`. The `company_name`
convenience getter uses the first provider-reported company name; read the raw
array when you need every associated company or family-tree entry.
