# HubSpot API Integration

## Authentication

HubSpot API requires a private app access token:

```bash
# Store in .env.local or export
export HUBSPOT_API_KEY="pat-na2-..."
```

Get token from: HubSpot Settings → Integrations → Private Apps

## Searching Contacts

Use POST `/crm/v3/objects/contacts/search` for filtered queries:

```bash
curl -X POST "https://api.hubapi.com/crm/v3/objects/contacts/search" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filterGroups": [
      {
        "filters": [
          {
            "propertyName": "jobtitle",
            "operator": "CONTAINS_TOKEN",
            "value": "GTM"
          }
        ]
      }
    ],
    "properties": ["email", "firstname", "lastname", "jobtitle", "company", "hs_linkedin_url"],
    "limit": 100
  }'
```

**FilterGroups logic**: Multiple filterGroups = OR logic, filters within a group = AND logic.

Common operators:
- `EQ` - Equals
- `CONTAINS_TOKEN` - Contains word/token
- `IN` - In list
- `GTE` / `LTE` - Greater/less than (dates, numbers)

## Updating Contact Properties

Use PATCH `/crm/v3/objects/contacts/{contactId}`:

```bash
curl -X PATCH "https://api.hubapi.com/crm/v3/objects/contacts/123456" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "jobtitle": "VP of Growth",
      "hs_job_change_detected_date": "2026-03-08"
    }
  }'
```

## Company Associations (CRITICAL)

**HubSpot displays Company associations, not the `company` text field.**

When updating a contact's company:

1. Find or create the Company record
2. Remove old company association
3. Add new company association

### Find or Create Company

```bash
# Search for company
COMPANY_ID=$(curl -s -X POST "https://api.hubapi.com/crm/v3/objects/companies/search" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filterGroups":[{"filters":[{"propertyName":"name","operator":"EQ","value":"Ramp"}]}],"properties":["name","domain"]}' \
  | jq -r '.results[0].id // empty')

# Create if not found
if [ -z "$COMPANY_ID" ]; then
  COMPANY_ID=$(curl -s -X POST "https://api.hubapi.com/crm/v3/objects/companies" \
    -H "Authorization: Bearer $HUBSPOT_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"properties":{"name":"Ramp","domain":"ramp.com"}}' \
    | jq -r '.id')
fi
```

### Check Existing Associations

```bash
curl -s "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  | jq '.results[].toObjectId'
```

### Remove Association

```bash
curl -X DELETE "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies/$OLD_COMPANY_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY"
```

### Add Association

```bash
curl -X PUT "https://api.hubapi.com/crm/v4/objects/contacts/$CONTACT_ID/associations/companies/$NEW_COMPANY_ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "associationCategory": "HUBSPOT_DEFINED",
      "associationTypeId": 1
    }
  ]'
```

**AssociationTypeId 1** = Primary company association.

## Batch Updates

For updating multiple contacts, use batch endpoints:

```bash
curl -X POST "https://api.hubapi.com/crm/v3/objects/contacts/batch/update" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "id": "123",
        "properties": {"jobtitle": "VP Growth", "hs_job_change_detected_date": "2026-03-08"}
      },
      {
        "id": "456",
        "properties": {"jobtitle": "Director GTM", "hs_job_change_detected_date": "2026-03-08"}
      }
    ]
  }'
```

Max 100 records per batch request.

## Common Properties

| Property | Description | Type |
|----------|-------------|------|
| `jobtitle` | Job title | text |
| `company` | Company name (text field, not association) | text |
| `email` | Primary email | text |
| `hs_linkedin_url` | LinkedIn profile URL | text |
| `hs_job_change_detected_date` | Date job change was detected | date (YYYY-MM-DD) |
| `hs_lead_status` | Lead status | enumeration |
| `firstname` / `lastname` | Name fields | text |

## Rate Limits

- 100 requests per 10 seconds (burst)
- 150,000 requests per day

Use batch endpoints when updating multiple records.

## Error Handling

```bash
# Check for errors in response
RESPONSE=$(curl -s -X PATCH "https://api.hubapi.com/crm/v3/objects/contacts/$ID" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"properties":{...}}')

if echo "$RESPONSE" | jq -e '.status == "error"' > /dev/null; then
  echo "Error: $(echo "$RESPONSE" | jq -r '.message')"
fi
```

Common errors:
- `401` - Invalid API key
- `404` - Contact/company not found
- `400` - Invalid property value or missing required field
