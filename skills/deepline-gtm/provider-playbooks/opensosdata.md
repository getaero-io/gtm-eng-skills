# OpenSOSData Integration Guide

US Secretary of State business entity lookup across currently active OpenSOSData jurisdictions.

## When to use

Use `opensosdata_business_lookup` to find the registered officer name for a business entity.
This is the bridge between "I have a restaurant name" and "I have an owner name to skip-trace."

Typical flow:

1. `opensosdata_business_lookup` → get officer name from SOS
2. `enformion_contact_enrich` → get mobile phone from officer name + city/state

## State-by-state officer data coverage

| Coverage                          | States                                                 | Notes                                         |
| --------------------------------- | ------------------------------------------------------ | --------------------------------------------- |
| **Full** (name + address + title) | FL, TX (franchise tax), CO, PA, MN, NY, WI, KY, SC, RI | FL is best — full officer list with addresses |
| **Name only**                     | IL, IN, TN, CT, MA, GA, NV, ND, AL, AR, IA, MO         |                                               |
| **Entity found, no officers**     | OH, CA, MI, WA, NJ                                     | SOS shields member names — use other methods  |

## Critical gotchas

### 1. FL officer name format — ALWAYS reverse

FL SOS returns `"LASTNAME, FIRSTNAME MIDDLE"`. Use `reverseOfficerName()` from `opensosdata-shared.ts`:

- `"SMITH, JOHN EDWARD"` → `"John Smith"`
- `"DE LA CRUZ, MARIA"` → `"Maria De La Cruz"`

Other states that use this format: LA, SC, sometimes GA.

### 2. Async states (CA, MA, NV, OR, WA)

These states return HTTP 202 with a `jobId`. The action **automatically polls** every 3 seconds
until complete (up to 90s). No special handling needed by the caller.

### 3. Skip registered agent services

Filter officer names containing: "Corporation Service", "CT Corporation", "Incorp",
"Northwest Registered", "Statutory Agent". These are professional RA services, not people.
Use `isRegisteredAgentService()` from `opensosdata-shared.ts`.

### 4. Balance monitoring

Each lookup costs Deepline credits. Check remaining balance before large batch runs.
Check balance: `GET /v1/account/balance` → `lookupsRemaining`.
Topup URL: https://app.opensosdata.com#billing

## Response structure

Synchronous (most states):

```json
{
  "success": true,
  "data": {
    "entityName": "NOBLE BEAST BREWING LLC",
    "entityType": "LLC",
    "entityId": "2441200",
    "status": "Active",
    "formationDate": "10/28/2015",
    "registeredAgentName": "",
    "officers": [],
    "sosUrl": "https://businesssearch.ohiosos.gov/...",
    "scrapedAt": "2026-05-31T..."
  }
}
```

FL with full officers:

```json
{
  "success": true,
  "data": {
    "entityName": "CASTAWAYS RIVER TIKI BAR LLC",
    "officers": [
      { "name": "SWANSON, KIRK ALAN", "title": "MGR", "address": "..." }
    ]
  }
}
```

→ Reverse: `reverseOfficerName("SWANSON, KIRK ALAN")` = `"Kirk Swanson"`

Async (CA/MA/NV/OR/WA) — handled automatically, caller receives final result.

Not found (no charge):

```json
{ "success": false, "error": "Entity not found", "cost": 0 }
```

## Credentials

Single API key passed as `x-api-key` header.
Set via Deepline dashboard → Integrations → OpenSOSData, or `OPENSOSDATA_API_KEY` env var.

API endpoint: `https://api.opensosdata.com/v1/lookup`
