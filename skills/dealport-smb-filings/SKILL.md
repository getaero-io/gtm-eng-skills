---
name: dealport-smb-filings
description: |
  Size 28M+ US private company and NYC commercial building markets from primary
  public filings, match account CSVs, and resolve verified human business or
  building owners via Dealport V4 and the Deepline CLI.

  Triggers:
  - "size US private SMBs in Ohio by NAICS from public filings"
  - "match this company CSV to public filing records and find the human owner"
  - "find NYC multifamily building owners with maturing loans"

  Requires: Deepline CLI - https://code.deepline.com (plus a Dealport API key from https://app.dealport.com/connect?tab=keys)
---

# US SMB and Building Public-Filing Prospecting (Dealport + Deepline)

Size off-market US private business and NYC multifamily or mixed-use property markets across 28M+ primary public-filing Records (corporate registries, UCC filings, CMS cost reports, state health and trade licenses, SEC Form ADV, and NYC ACRIS property and mortgage filings), match existing account CSVs, and resolve verified human principals with direct phones, emails, and career profiles.

## Prerequisites

1. **Deepline CLI:** Install and authenticate via [code.deepline.com](https://code.deepline.com):
   ```bash
   npm install -g @deepline/cli
   deepline auth login
   ```
2. **Dealport API key (`DP_API_KEY`):** Create a pay-as-you-go account (starts with a `$5.00` free balance, no subscription) and generate a scoped key at [app.dealport.com/connect?tab=keys](https://app.dealport.com/connect?tab=keys). Reference docs: [app.dealport.com/llms.txt](https://app.dealport.com/llms.txt).

## Input and Output Columns

### CSV Matching and Owner Lookup (`leads.csv`)
- **Required input columns (at least one identifier per row):**
  - `company_name` or `domain` (for private US companies), or `bbl` (10-digit NYC Borough-Block-Lot for NYC buildings)
- **Optional input columns (improve entity resolution):**
  - `city` (string), `state` (2-letter US state code), `external_id` (caller row ID)
- **Output columns written:**
  - `dealport_company_id` (UUID), `matched_name`, `matched_domain`, `filing_sources`, `owner_name`, `owner_title`, `owner_phone`, `owner_email`, `owner_linkedin_url`

## Plain-USD Dealport Rate Card (Verify Before Paid Steps)

- `POST /api/v1/companies/preview` (`preview_companies`) and `POST /api/v1/companies/match` (`match_company_list`): `$0.00`
- `GET /api/v1/balance` (`account_balance`): `$0.00`
- `GET /api/v1/companies`, `GET /api/v1/buildings`, `GET /api/v1/records/{id}`: `$0.01` per Record (`$0.00` on 30-day workspace repeat)
- `POST /api/v1/pages` (`fetch_company_pages`): `$0.00` cached / `$0.01` live fetch
- `POST /api/v1/buildings/owners` (`research_building_owners`): `$0.00` quote without `confirm_max_usd`, `$0.05` per distinct NYC building owner when confirmed
- `POST /api/v1/owners` (`find_owner`) and `POST /api/v1/contacts` (`find_contact`): `$0.09` per verified human owner hit (`$0.00` on miss or 30-day repeat)
- `POST /api/v1/research`: `$0.50` deep cited company research
- `POST /api/v1/avery` (Avery, Dealport's AI outreach specialist, who always discloses she is an AI): `$0.02` per outreach email sent; `$25.00` per accepted double-opt-in Warm Yes introduction (never trigger Avery without explicit human approval)

## Workflow

### Step 1: Check Balance and Size the Market Free (`$0.00`)

Always run a `$0.00` market-sizing preview before unlocking paid Records so the user can verify the total matching universe and inspect 5 sample companies.

```bash
deepline tools execute generic_http_request --payload '{
  "method": "POST",
  "url": "https://app.dealport.com/api/v1/companies/preview",
  "headers": {
    "Authorization": "Bearer '"$DP_API_KEY"'",
    "Content-Type": "application/json"
  },
  "body_json": {
    "state": "OH",
    "naics": ["238220"],
    "independent": true,
    "min_employees": 10,
    "max_employees": 150
  }
}'
```

Share the total match count and 5 sample companies with the user and confirm filters before unlocking Records (`GET /api/v1/companies`) or resolving human owners.

### Step 2: Inspect `--rows 0:1` Pilot Before Batch CSV Matching or Owner Resolution

When starting from an existing `leads.csv`, inspect the first row (`--rows 0:1`) and run a single-row pilot via `deepline tools execute` before processing the full CSV.

```bash
# 1. Inspect the pilot row (0:1) to verify column alignment
deepline csv show leads.csv --rows 0:1 --format table

# 2. Pilot free ($0.00) entity resolution on row 0:1
deepline tools execute generic_http_request --payload '{
  "method": "POST",
  "url": "https://app.dealport.com/api/v1/companies/match",
  "headers": {
    "Authorization": "Bearer '"$DP_API_KEY"'",
    "Content-Type": "application/json"
  },
  "body_json": {
    "items": [
      {
        "external_id": "row-0",
        "name": "Buckeye Mechanical Contracting",
        "domain": "buckeyemechanical.com",
        "city": "Columbus",
        "state": "OH"
      }
    ],
    "watch": false
  }
}'
```

### Step 3: Pilot Verified Human Owner Lookup (`$0.09` per Hit, `$0.00` Miss)

Once row `0:1` resolves to a `company_id` and the user confirms expected spend, test `POST /api/v1/owners` on that single company UUID to verify direct phone, email, and LinkedIn profile output before batching:

```bash
deepline tools execute generic_http_request --payload '{
  "method": "POST",
  "url": "https://app.dealport.com/api/v1/owners",
  "headers": {
    "Authorization": "Bearer '"$DP_API_KEY"'",
    "Content-Type": "application/json"
  },
  "body_json": {
    "company_id": "<dealport_company_uuid_from_step_2>"
  }
}'
```

For NYC multifamily or mixed-use buildings (`GET /api/v1/buildings?borough=BK&min_units=20`), always call `POST /api/v1/buildings/owners` **without `confirm_max_usd` first** (`$0.00` quote), show `total_usd` (`$0.05` per distinct owner) to the user, and pass `confirm_max_usd` only after confirmation.

### Step 4: Full Batch Run and Downstream Deepline Enrichment

After the `--rows 0:1` pilot succeeds and the user approves the batch count:
1. Match up to 250 rows per call via `POST /api/v1/companies/match` (`$0.00`).
2. Resolve verified human principals on qualified `dealport_company_id` rows via `POST /api/v1/owners` (`$0.09` per verified hit; `$0.00` on miss or 30-day workspace repeat) and write enriched columns to `leads-dealport-enriched.csv`.
3. Hand off `leads-dealport-enriched.csv` to `deepline-gtm` (`deepline search` / `deepline run`) when the user wants additional firmographic signals, scorecards, or CRM sync.

## Optional Native MCP and CLI Path

If the agent runtime supports Streamable HTTP MCP or Node 20+, you can also connect Dealport alongside the Deepline CLI:
- **Remote MCP:** `claude mcp add --transport http dealport https://app.dealport.com/api/mcp`
- **Zero-install CLI:** `DP_API_KEY=$DP_API_KEY npx dealport preview --state OH --naics 238220 --independent`
