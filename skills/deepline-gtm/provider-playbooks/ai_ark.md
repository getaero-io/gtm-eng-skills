# AI Ark Integration Guide

## Overview

AI Ark provides company search, people search, reverse lookup, mobile phone finding, personality analysis, async export, and async email finding across enriched profiles.

**Base URL:** `https://api.ai-ark.com/api/developer-portal`
**Auth:** `X-TOKEN` header with API key.
**Rate limits:** 5 req/s, 300 req/min, 18,000 req/hr (all endpoints).

## Credit Costs

| Operation                      | Cost | Unit            |
| ------------------------------ | ---- | --------------- |
| Company Search                 | 0.1  | per result      |
| People Search                  | 0.5  | per result      |
| Reverse People Lookup          | 0.5  | per request     |
| Mobile Phone Finder            | 5.0  | per request     |
| Export People (with Email)     | ~0.5 | per email found |
| Personality Analysis           | TBD  | coming soon     |
| Email Finder                   | ~0.5 | per email found |
| Polling / Statistics / Results | 0    | free            |

## Filter Structure (CRITICAL)

AI Ark uses a strict nested filter structure. **Do NOT flatten or simplify these structures.** Deepline still accepts legacy aliases for existing scripts, but new code should use the AI Ark-native fields below.

### Text filters

Text filters require `{ mode, content }` inside `include`/`exclude`:

```json
{
  "contact": {
    "fullName": {
      "any": {
        "include": {
          "mode": "SMART",
          "content": ["Ada Lovelace"]
        }
      }
    },
    "experience": {
      "current": {
        "title": {
          "any": {
            "include": {
              "mode": "SMART",
              "content": ["VP", "Director", "Head of"]
            }
          }
        }
      }
    }
  }
}
```

### String filters

String filters use arrays directly in `include`/`exclude`:

```json
{
  "contact": {
    "seniority": {
      "any": {
        "include": ["vp", "director", "c_suite"]
      }
    },
    "departmentAndFunction": {
      "any": {
        "include": ["sales", "marketing"]
      }
    }
  }
}
```

### Company filters

Contact company filters use AI Ark company IDs, not company names. Get IDs from `ai_ark_company_search`, then use `latest`, `current`, or `previous`.

```json
{
  "contact": {
    "company": {
      "previous": {
        "any": {
          "include": ["8b1c2fa5-3ceb-437e-5ef5-495bc6d34ace"]
        }
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
    "experience": {
      "current": {
        "title": {
          "any": {
            "include": {
              "mode": "SMART",
              "content": ["VP of Sales", "Head of Sales"]
            }
          }
        }
      }
    },
    "seniority": {
      "any": {
        "include": ["vp", "director"]
      }
    },
    "location": {
      "any": {
        "include": ["San Francisco"]
      }
    }
  }
}
```

### Field type reference

**Contact text filters** (use `{ mode: "SMART", content: [...] }`):
`fullName`, `skill`, `certification`, `education.degree`, `education.fieldOfStudy`, `experience.latest.title`, `experience.current.title`, `experience.previous.title`

**Contact keyword filter**:
`keyword` uses `{ include: { content: [...] } }` with optional `sources`, not a normal text operand.

**Contact string filters** (use `["value1", "value2"]`):
`socialMediaLink`, `seniority`, `location`, `linkedin`, `departmentAndFunction`, `company.latest`, `company.current`, `company.previous`, `education.school`

**Legacy aliases**:
`name` maps to `fullName`; `title` maps to `experience.current.title`; `pastCompany` maps to `company.previous`; `currentCompany` maps to `company.current`; `contactLocation` maps to `location`; `socialProfile` maps to `socialMediaLink`. Do not send an alias and its native equivalent in the same request.

**Account text filters**: `url`, `name`, `productAndServices`, `technologies`

**Account string filters**: `domain`, `linkedin`, `socialMediaLink`, `phoneNumber`, `location`, `technology`, `naics`

### Common mistakes to avoid

- Prefer `contact.experience.current.title` over legacy `contact.title`
- Prefer `contact.company.previous` with AI Ark company IDs over legacy `contact.pastCompany`
- ❌ `{ include: ["value"] }` for text filters → ✅ `{ include: { mode: "SMART", content: ["value"] } }`
- ❌ `{ include: { mode: "SMART", content: ["value"] } }` for string filters → ✅ `{ include: ["value"] }`

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
2. `ai_ark_find_emails` with that `trackId` and a `webhook` URL (single-use, expires in 6 hours).
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
