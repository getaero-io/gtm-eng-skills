# AI Ark Integration Guide

## Overview

AI Ark provides company search, people search, reverse lookup, mobile phone finding, personality analysis, async export, and async email finding across enriched profiles.

**Base URL:** `https://api.ai-ark.com/api/developer-portal`
**Auth:** `X-TOKEN` header with API key.
**Rate limits:** 5 req/s, 300 req/min, 18,000 req/hr (all endpoints).

## Credit Costs

| Operation | Cost | Unit |
|-----------|------|------|
| Company Search | 0.1 | per result |
| People Search | 0.5 | per result |
| Reverse People Lookup | 0.5 | per request |
| Mobile Phone Finder | 5.0 | per request |
| Export People (with Email) | ~0.5 | per email found |
| Personality Analysis | TBD | coming soon |
| Email Finder | ~0.5 | per email found |
| Polling / Statistics / Results | 0 | free |

## Filter Structure (CRITICAL)

AI Ark uses a strict nested filter structure. **Do NOT flatten or simplify these structures.**

### Text filters (contactLocation, title, name, education, keyword)

Text filters require `{ mode, content }` inside `include`/`exclude`:

```json
{
  "contact": {
    "contactLocation": {
      "any": {
        "include": {
          "mode": "FUZZY",
          "content": ["San Francisco", "New York"]
        }
      }
    },
    "title": {
      "any": {
        "include": {
          "mode": "FUZZY",
          "content": ["VP", "Director", "Head of"]
        }
      }
    }
  }
}
```

### String filters (seniority, department, function, skills)

String filters use arrays directly in `include`/`exclude`:

```json
{
  "contact": {
    "seniority": {
      "any": {
        "include": ["vp", "director", "c_suite"]
      }
    },
    "department": {
      "any": {
        "include": ["sales", "marketing"]
      }
    }
  }
}
```

### Complete People Search example

```json
{
  "page": 0,
  "size": 25,
  "account": {
    "domain": {
      "any": {
        "include": ["acme.com", "example.com"]
      }
    }
  },
  "contact": {
    "title": {
      "any": {
        "include": {
          "mode": "FUZZY",
          "content": ["VP of Sales", "Head of Sales"]
        }
      }
    },
    "seniority": {
      "any": {
        "include": ["vp", "director"]
      }
    },
    "contactLocation": {
      "any": {
        "include": {
          "mode": "FUZZY",
          "content": ["San Francisco"]
        }
      }
    }
  }
}
```

### Field type reference

**Contact text filters** (use `{ mode: "FUZZY", content: [...] }`):
`name`, `contactLocation`, `currentCompany`, `pastCompany`, `education`, `title`, `keyword`

**Contact string filters** (use `["value1", "value2"]`):
`socialProfile`, `contactLanguage`, `seniority`, `department`, `function`, `skills`, `certifications`

**Account text filters**: `url`, `name`, `productAndServices`, `technologies`

**Account string filters**: `domain`, `linkedin`, `socialMediaLink`, `phoneNumber`, `location`, `technology`, `naics`

### Common mistakes to avoid

- ❌ `contact.location` → ✅ `contact.contactLocation`
- ❌ `{ include: ["value"] }` for text filters → ✅ `{ include: { mode: "FUZZY", content: ["value"] } }`
- ❌ `{ include: { mode: "FUZZY", content: ["value"] } }` for string filters → ✅ `{ include: ["value"] }`

## Recommended Workflow

### Prospecting

1. **Company Search** (`ai_ark_company_search`) to build account lists. Use `account` filters for firmographics, funding, technology, geography, and optional `lookalikeDomains`.
2. **People Search** (`ai_ark_people_search`) to find contacts. Use nested `account` and `contact` filters exactly as shown in the examples above.

### Email Finding (two paths)

**Path A — Export People (recommended for bulk verified email pulls):**
1. `ai_ark_export_people` with filters + optional webhook → returns `trackId`.
2. Poll `ai_ark_export_statistics` until `state: "DONE"`.
3. Fetch results via `ai_ark_export_results` (paginated).

**Path B — Find Emails from Search:**
1. Run `ai_ark_people_search` first → response includes a `trackId`.
2. `ai_ark_find_emails` with that `trackId` (single-use, expires in 6 hours).
3. Poll `ai_ark_email_finder_statistics` until `state: "DONE"`.
4. Fetch results via `ai_ark_email_finder_results` (paginated).

### Identity Resolution

- **Reverse Lookup** (`ai_ark_reverse_lookup`): Look up a person by email or phone number using the `search` field only.

### Phone Numbers

- **Mobile Phone Finder** (`ai_ark_mobile_phone_finder`): Find mobile numbers by LinkedIn URL or name + domain. Use this after you already have a high-confidence person match because it is relatively expensive (5.0/request).

### Personality Analysis

- **Personality Analysis** (`ai_ark_personality_analysis`): Analyze personality traits from a LinkedIn profile URL.

## Pagination

All search/list endpoints use zero-based pagination with `page` and `size` parameters. Search and export creation use JSON body pagination; results browsing uses query params.

## Error Handling

- **409 Conflict**: Export or email-finder result pages were requested while the async job is still processing. Poll statistics first.
- **404 Not Found**: Profile not found (personality analysis).
- **429 Too Many Requests**: Rate limit exceeded. Resets every 60 seconds.

## Key Constraints

- Export People: max 10,000 results per export.
- Find Emails trackId: single-use, expires 6 hours after the People Search that generated it.
- Webhooks: auto-retry up to 30 times. Use HTTPS endpoints and respond `200` immediately.
- Undocumented endpoints in the vendor docs snapshot are intentionally not exposed here.
