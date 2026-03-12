---
name: apify-actor-contracts
description: "Auto-generated actor input/output contract reference from src/lib/integrations/apify/typed-actors.ts"
---

# Apify Actor Contracts

This document is generated from `src/lib/integrations/apify/typed-actors.ts`.
Contracts, field descriptions, schemas, and sample payloads come from typed actor contracts.
Do not edit by hand. Regenerate with:

```bash
tsx scripts/generate-apify-actor-contracts.ts
```

## Included Actors

- `dev_fusion/linkedin-profile-scraper` (`linkedin_profile_scraping`)
- `apimaestro/linkedin-profile-detail` (`linkedin_profile_scraping`)
- `harvestapi/linkedin-company-employees` (`linkedin_company_employees_scraping`)
- `s-r/free-linkedin-company-finder---linkedin-address-from-any-site` (`linkedin_company_url_from_domain`)
- `radeance/similarweb-scraper` (`website_traffic_intelligence`)

## dev_fusion/linkedin-profile-scraper

- Use case: `linkedin_profile_scraping`
- Pricing model: `PRICE_PER_DATASET_ITEM`
- Last validated: `2026-02-12`
- Recommended mode: `sync`
- Input schema source: `typed_actor_contract`
- Sync timeout ms: `300000`

### Expected Input Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `profileUrls` | `string[]` | yes | One or more LinkedIn profile URLs to scrape. |
| `maxItems` | `number` | no | Limit number of output rows. |
| `includeContact` | `boolean` | no | Try email/phone enrichment when supported. |

### Minimal Payload

```json
{
  "profileUrls": [
    "https://www.linkedin.com/in/example-person/"
  ]
}
```

### Typical Payload

```json
{
  "profileUrls": [
    "https://www.linkedin.com/in/example-person-1/",
    "https://www.linkedin.com/in/example-person-2/"
  ],
  "maxItems": 100,
  "includeContact": true
}
```

### Input JSON Schema

```json
{
  "type": "object",
  "properties": {
    "profileUrls": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "LinkedIn profile URL."
      },
      "minItems": 1
    },
    "maxItems": {
      "type": "integer",
      "minimum": 1,
      "description": "Maximum number of profiles to return."
    },
    "includeContact": {
      "type": "boolean",
      "description": "Include email/phone enrichment where available."
    }
  },
  "required": [
    "profileUrls"
  ],
  "additionalProperties": true
}
```

### Output Notes

- Each row is a person profile record.
- Expect fields like profile URL, name, headline, experiences, education.
- Contact fields are optional and may be empty.

## apimaestro/linkedin-profile-detail

- Use case: `linkedin_profile_scraping`
- Pricing model: `PAY_PER_EVENT`
- Last validated: `2026-02-12`
- Recommended mode: `sync`
- Input schema source: `typed_actor_contract`
- Sync timeout ms: `300000`

### Expected Input Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `profileUsername` | `string` | no | LinkedIn username (use this or profileUrl). |
| `profileUrl` | `string` | no | LinkedIn profile URL (use this or profileUsername). |
| `enrichEmail` | `boolean` | no | Enable email enrichment if supported by actor build. |

### Minimal Payload

```json
{
  "profileUrl": "https://www.linkedin.com/in/example-person/"
}
```

### Typical Payload

```json
{
  "profileUrl": "https://www.linkedin.com/in/example-person/",
  "enrichEmail": true
}
```

### Input JSON Schema

```json
{
  "type": "object",
  "properties": {
    "profileUsername": {
      "type": "string",
      "description": "LinkedIn username or profile identifier."
    },
    "profileUrl": {
      "type": "string",
      "description": "LinkedIn profile URL."
    },
    "enrichEmail": {
      "type": "boolean",
      "description": "Try to discover email with profile scrape."
    }
  },
  "anyOf": [
    {
      "required": [
        "profileUsername"
      ]
    },
    {
      "required": [
        "profileUrl"
      ]
    }
  ],
  "additionalProperties": true
}
```

### Output Notes

- Typically one record per profile input.
- Profile details include work/education/language/location sections.
- Some builds may include email when available.

## harvestapi/linkedin-company-employees

- Use case: `linkedin_company_employees_scraping`
- Pricing model: `PAY_PER_EVENT`
- Last validated: `2026-02-12`
- Recommended mode: `sync`
- Input schema source: `typed_actor_contract`
- Sync timeout ms: `300000`

### Expected Input Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `companyLinkedinUrls` | `string[]` | yes | Target company LinkedIn page URLs. |
| `maxItems` | `number` | no | Upper bound on employee rows. |
| `profileDepth` | `short|full|full_with_email` | no | Controls cost/field depth by actor event mode. |

### Minimal Payload

```json
{
  "companyLinkedinUrls": [
    "https://www.linkedin.com/company/openai/"
  ]
}
```

### Typical Payload

```json
{
  "companyLinkedinUrls": [
    "https://www.linkedin.com/company/openai/",
    "https://www.linkedin.com/company/anthropic/"
  ],
  "maxItems": 250,
  "profileDepth": "full"
}
```

### Input JSON Schema

```json
{
  "type": "object",
  "properties": {
    "companyLinkedinUrls": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "LinkedIn company page URL."
      },
      "minItems": 1
    },
    "maxItems": {
      "type": "integer",
      "minimum": 1,
      "description": "Maximum employee profiles returned."
    },
    "profileDepth": {
      "type": "string",
      "enum": [
        "short",
        "full",
        "full_with_email"
      ],
      "description": "Extraction depth/cost mode."
    }
  },
  "required": [
    "companyLinkedinUrls"
  ],
  "additionalProperties": true
}
```

### Output Notes

- Each row is a company employee profile.
- Typical fields include name, title, profile URL, company and location.
- Full mode adds expanded profile details; email mode may include contact candidates.

## s-r/free-linkedin-company-finder---linkedin-address-from-any-site

- Use case: `linkedin_company_url_from_domain`
- Pricing model: `PRICE_PER_DATASET_ITEM`
- Last validated: `2026-02-13`
- Recommended mode: `sync`
- Input schema source: `typed_actor_contract`
- Sync timeout ms: `300000`

### Expected Input Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `domains` | `string[]` | yes | List of company domains to resolve into LinkedIn company URLs. |

### Minimal Payload

```json
{
  "domains": [
    "openai.com"
  ]
}
```

### Typical Payload

```json
{
  "domains": [
    "openai.com",
    "anthropic.com",
    "perplexity.ai",
    "stripe.com",
    "notion.so"
  ]
}
```

### Input JSON Schema

```json
{
  "type": "object",
  "properties": {
    "domains": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "Company domain (for example, openai.com)."
      },
      "minItems": 1
    }
  },
  "required": [
    "domains"
  ],
  "additionalProperties": true
}
```

### Output Notes

- Each row maps an input domain to a discovered LinkedIn company page URL.
- Expect fields like domain and linkedin_url in the output dataset.
- Some runs may include additional social URLs when available.

## radeance/similarweb-scraper

- Use case: `website_traffic_intelligence`
- Pricing model: `PAY_PER_EVENT`
- Last validated: `2026-02-26`
- Recommended mode: `sync`
- Input schema source: `typed_actor_contract`
- Sync timeout ms: `300000`

### Expected Input Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `urls` | `string[]` | yes | One or more website URLs to scrape traffic intelligence for. |
| `include_indepth_data` | `boolean` | no | Enable deeper company/demographic/competitor/rank trend output. |
| `proxySettings` | `record` | yes | Apify proxy configuration for Similarweb requests (for example, {"useApifyProxy": true}). |

### Minimal Payload

```json
{
  "urls": [
    "https://www.indeed.com/"
  ],
  "proxySettings": {
    "useApifyProxy": true
  }
}
```

### Typical Payload

```json
{
  "urls": [
    "https://www.indeed.com/",
    "https://www.linkedin.com/",
    "https://www.glassdoor.com/"
  ],
  "include_indepth_data": true,
  "proxySettings": {
    "useApifyProxy": true
  }
}
```

### Input JSON Schema

```json
{
  "type": "object",
  "properties": {
    "urls": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "Website URL to analyze."
      },
      "minItems": 1
    },
    "include_indepth_data": {
      "type": "boolean",
      "description": "Include additional company, audience, competitor, and rank-history insights when available."
    },
    "proxySettings": {
      "type": "object",
      "description": "Apify proxy configuration forwarded to the actor run; required by this actor.",
      "properties": {
        "useApifyProxy": {
          "type": "boolean",
          "description": "Use Apify Proxy pool."
        },
        "apifyProxyGroups": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Optional Apify Proxy groups (for example, RESIDENTIAL)."
        },
        "countryCode": {
          "type": "string",
          "description": "Optional country targeting code (for example, US)."
        },
        "proxyUrls": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Optional custom proxy URLs."
        }
      }
    }
  },
  "required": [
    "urls",
    "proxySettings"
  ],
  "additionalProperties": true
}
```

### Output Notes

- Each row is a Similarweb website analytics snapshot for one input URL.
- Core fields include global/country/category ranks, visits, traffic sources, and engagement metrics.
- In-depth mode may include company demographics, competitor sets, keyword/referral/social breakdowns, and historical rank series.
