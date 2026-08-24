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

Do not attempt paid enrichment actions. They are not published until ZoomInfo
pricing and runtime usage settlement are approved. Do not use customer
credentials for testing; only an explicit Deepline internal/test Partner App is
allowed.
