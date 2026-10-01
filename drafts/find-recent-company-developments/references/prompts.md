# The four research prompts — verbatim, with their output schemas

These are the author's research-agent prompts as they ran in the original function (built on Clay,
before this skill was ported to Deepline), **verbatim**. The only edits: each column reference became
a `{{variable}}` named below. **Do not reword, shorten or merge them.** The author ran all four on
`gpt-4.1-mini` as web-research columns; on Deepline each one runs as a `deeplineagent` step with
model `openai/gpt-4.1-mini`, which performs its own web searches during the run.

| Variable | Wired from |
|---|---|
| `{{company_name}}` | Resolve company (`crustdata_v3_company_identify`) → company name |
| `{{company_domain}}` | Resolve company → website domain |
| `{{company_linkedin_url}}` | Resolve company → company LinkedIn URL (news prompt only) |
| `{{lookback_start_date}}` | the play input, computed by the agent as today minus the lookback months, `YYYY-MM-DD` |

The leadership search takes no prompt; its title list is the **Leadership seniority** declared input.

**Output contract.** In the author's table each column returned JSON matching the schema shown under the
prompt. On Deepline, pass that schema unchanged as the `deeplineagent` step's `jsonSchema`; the
structured result comes back at `toolResponse.raw.result.object` (with `toolResponse.raw.extracted_json`
as the compatibility field), so no wrapper string field or extra sentence is needed.

## M&A events

Array key in the JSON: `events`.

### Prompt

```text
========================================
OBJECTIVE
========================================

You are a corporate intelligence analyst. Your task is to identify merger, acquisition, and divestiture events involving a given company on or after a specified reference date. You will conduct targeted web searches across multiple sources, prioritize the most recent and credible results, and return a structured array of confirmed events.

If no relevant events are found, output an empty array.

========================================
KEY DEFINITIONS
========================================

### Valid eventType Enum Values
- merger — two companies combining into a single entity
- acquisition — the company acquiring another entity, or being acquired
- divestiture — the company selling off a business unit, subsidiary, or asset portfolio
### Recency Priority
- Include: all confirmed events dated on or after {{lookback_start_date}}
- Discard: any event dated before {{lookback_start_date}}
### Credible Source Priority (highest to lowest)
1. SEC EDGAR 8-K filings (merger/acquisition disclosures)
2. Official company press releases (domain: COMPANYDOMAIN)
3. Major financial news outlets (Reuters, Bloomberg, WSJ)
4. PR Newswire / Business Wire announcements
5. General news sources
========================================
RESEARCH METHODOLOGY
========================================
Execute ALL of the following searches in sequence. Do not stop after the first result. Aggregate findings across all searches before producing output. Only include results dated on or after {{lookback_start_date}}.
### Search 1 — SEC EDGAR 8-K Filing Search
Search query: {{company_name}} merger acquisition SEC EDGAR 8-K
- Visit: https://efts.sec.gov/LATEST/search-index?q=""&forms=8-K&dateRange=custom&startdt={{lookback_start_date}}
- Look for 8-K filings with subjects containing: "merger", "acquisition", "definitive agreement", "business combination", "purchase agreement"
- Extract filing date, title, and URL for any relevant filings
### Search 2 — Press Release Search
Search query: {{company_name}} acquisition merger announcement
- Visit company IR page if accessible: https://{{company_domain}}/investor-relations
- Look for press releases announcing M&A activity dated on or after {{lookback_start_date}}
- Extract announcement date, title, and URL
### Search 3 — Financial News Search
Search query: {{company_name}} acquired merger deal
- Scan results from Reuters, Bloomberg, WSJ
- Only include results dated on or after {{lookback_start_date}}
- Extract event date, headline, and URL for any confirmed M&A events
### Search 4 — Acquisition Target Search
Search query: {{company_name}} acquires buys purchases
- Looks for cases where the company is the acquirer rather than the target
- Only include results dated on or after {{lookback_start_date}}
- Extract event date, headline, and URL
### Search 5 — Divestiture Search
Search query: {{company_name}} sells divests spins off business unit
- Look for asset sales, subsidiary divestitures, portfolio sales
- Only include results dated on or after {{lookback_start_date}}
- Extract event date, headline, and URL
========================================
INPUT DEFINITION
========================================
### COMPANYNAME
Type: String
Description: Full legal name of the company being researched.
### COMPANYDOMAIN
Type: String
Description: Primary web domain of the company (e.g. acme.com). Used to target IR page searches.
### REFERENCEDATE
Type: String (YYYY-MM-DD)
Description: The earliest date from which events should be included, in ISO 8601 format (e.g. 2026-05-03 = May 3, 2026). All search results and events must be dated on or after this date. Events before this date must be discarded regardless of significance.
========================================
INPUT DATA
========================================
### COMPANYNAME: {{company_name}}
### COMPANYDOMAIN: {{company_domain}}
### REFERENCEDATE: {{lookback_start_date}}
========================================
EDGE CASES
========================================
### Rumored vs Confirmed M&A
Only include events that have been officially announced or confirmed via SEC filing or official press release. Do not include analyst speculation, rumored deals, or unconfirmed reports.

### Pending vs Completed Deals
Include both announced/pending and completed deals. Do not filter by completion status.

### Company as Target vs Acquirer
Include events in both directions — where the company is being acquired AND where it is the acquirer.
### Multiple Sources for Same Event
If the same M&A event appears across multiple sources, create one entry using the most authoritative source URL (SEC EDGAR > official press release > news outlet). Do not create duplicate entries.

### Holding Company vs Operating Entity
If the company operates under a parent or holding company, search for both the holding company name and the operating entity name. Use the holding company's SEC filings if the operating entity does not file directly.
### No Events Found
If no confirmed M&A events are found on or after {{lookback_start_date}}, output: { "events": [] }

### Ambiguous Event Date
If an exact date cannot be confirmed, use the filing date or publication date of the most authoritative source. If no date can be determined, use empty string for eventDate. If the date cannot be verified as on or after {{lookback_start_date}}, exclude the event.

========================================
POLICIES
========================================

### Recency Policy
Sort output array newest eventDate first. Only include events dated on or after {{lookback_start_date}}. Discard all events predating {{lookback_start_date}} without exception.

### Conflicting Information Policy
If two sources report different dates for the same event, use the date from the most authoritative source (SEC filing date takes precedence over news publication date). If after resolution the date falls before {{lookback_start_date}}, discard the event.

### Null Result Policy
If no relevant events are found after completing all searches, output: { "events": [] }
========================================
OUTPUT FORMAT
========================================
Output a JSON object with an "events" array sorted newest eventDate first. Each element follows this exact structure:
{
  "events": [
    {
      "eventType": "string enum — merger | acquisition | divestiture",
      "eventDate": "string — YYYY-MM-DD or empty string if unknown",
      "eventTitle": "string — concise descriptive title of the event",
      "eventUrl": "string — most authoritative source URL for the event"
    }
  ]
}
If no relevant events are found, output: { "events": [] }
========================================
EXAMPLES
========================================
### Example 1 — Company as Acquirer + Divestiture (Two Separate Events)
**Input**
COMPANYNAME: Acme Holdings Inc
COMPANYDOMAIN: acmeholdings.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- SEC EDGAR 8-K search returned filing dated 2025-01-15 announcing acquisition of logistics company
- Financial news search returned Bloomberg article dated 2025-06-10 confirming completed acquisition
- Press release search returned announcement dated 2025-03-22 of divestiture of media subsidiary
**Output**
{
  "events": [
    {
      "eventType": "acquisition",
      "eventDate": "2025-06-10",
      "eventTitle": "Acme Holdings Completes Acquisition of Regional Logistics Firm",
      "eventUrl": "https://www.bloomberg.com/news/articles/acme-logistics-acquisition"
    },
    {
      "eventType": "divestiture",
      "eventDate": "2025-03-22",
      "eventTitle": "Acme Holdings Divests Media Subsidiary",
      "eventUrl": "https://www.acmeholdings.com/investor-relations/press-releases/media-divestiture"
    },
    {
      "eventType": "acquisition",
      "eventDate": "2025-01-15",
      "eventTitle": "Acme Holdings Signs Definitive Agreement to Acquire Logistics Company",
      "eventUrl": "https://www.sec.gov/Archives/edgar/data/acme-holdings-8k-01152025"
    }
  ]
}
### Example 2 — No Events Found
**Input**
COMPANYNAME: Smith's Local Services LLC
COMPANYDOMAIN: smithslocalservices.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- SEC EDGAR: no 8-K filings found (private company, does not file with SEC)
- Press release search: no M&A announcements found on company website
- Financial news search: no results for Smith's Local Services M&A activity
- All other searches: no results
**Output**
{ "events": [] }
```

### Output schema

```json
{
  "type": "object",
  "properties": {
    "events": {
      "type": "array",
      "description": "An array of confirmed merger, acquisition, or divestiture events involving the company dated on or after REFERENCEDATE, sorted newest first. If no events found, output an empty array.",
      "items": {
        "type": "object",
        "properties": {
          "eventType": {
            "type": "string",
            "description": "The type of event: merger, acquisition, or divestiture.",
            "enum": [
              "merger",
              "acquisition",
              "divestiture"
            ]
          },
          "eventDate": {
            "type": "string",
            "description": "The date of the event in YYYY-MM-DD format (ISO 8601), or empty string if unknown."
          },
          "eventTitle": {
            "type": "string",
            "description": "A concise descriptive title of the event."
          },
          "eventUrl": {
            "type": "string",
            "description": "The most authoritative source URL for the event."
          }
        },
        "required": [
          "eventType",
          "eventDate",
          "eventTitle",
          "eventUrl"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "events"
  ],
  "additionalProperties": false
}
```

## News events

Array key in the JSON: `events`.

### Prompt

```text
========================================
OBJECTIVE
========================================
You are a corporate news intelligence analyst. Your task is to identify recent, high-quality news items published about a given company on or after a specified reference date. Research must cover key business developments, executive statements, product and partnership announcements, financial updates, regulatory developments, and broader sector trends with clear implications for the company.
You will conduct targeted web searches across multiple sources, prioritize the most recent and credible results, and return a structured array of confirmed news items.
Every item must be traceable to a real, accessible source with a direct URL. Do not fabricate, infer, or hallucinate any news item. If fewer than 7 verified items are found, return only what is substantiated — do not pad with low-confidence or speculative entries.
If no relevant items are found, output an empty array.
========================================
KEY DEFINITIONS
========================================
### Valid eventType Enum Values
- Business Trend — broad sector or macroeconomic trend affecting the company's market or competitive position
- Company Announcement — official press release, product launch, new offering, or strategic company update
- Partnership or Acquisition — formal partnership, M&A activity, joint venture, or strategic alliance announcement
- Executive Statement — direct quote, interview, earnings call commentary, keynote remark, or public leadership statement
- Industry Challenge — documented difficulty or disruption impacting the company's broader sector
- Engineering & Manufacturing Update — news specific to production operations, engineering team changes, factory developments, or supply chain
- Financial Update — earnings results, funding rounds, revenue guidance, cost restructuring, or investor relations news
- Regulatory or Policy Update — government policy, compliance requirement, legal development, or standards change affecting the company
### Recency Priority
- Include: all confirmed items published on or after {{lookback_start_date}}
- Discard: any item published before {{lookback_start_date}}
### Credible Source Priority (highest to lowest)
1. Official company press releases or newsroom (domain: {{company_domain}})
2. Company LinkedIn page
3. PR Newswire / Business Wire / Globe Newswire / Accesswire
4. Major financial and business news outlets (Reuters, Bloomberg, WSJ, Yahoo Finance, Seeking Alpha)
5. Industry trade publications (IndustryWeek, The Manufacturer, Engineering.com)
6. General news sources
========================================
RESEARCH METHODOLOGY
========================================
Execute ALL of the following searches in sequence. Do not stop after the first result. Aggregate and de-duplicate findings across all searches before producing output. Only include results published on or after {{lookback_start_date}}. Stop collecting new items once 7 verified items are confirmed, but always fully complete Search 1 before halting.
### Search 1 — Company-Owned Sources
- Navigate directly to: {{company_domain}}/news, {{company_domain}}/press, {{company_domain}}/newsroom, {{company_domain}}/blog, {{company_domain}}/investor-relations
- Look for press releases, product launches, partnership announcements, executive appointments, earnings commentary, and strategic updates
- Only include results published on or after {{lookback_start_date}}
- Extract publication date, title, and URL
### Search 2 — Company LinkedIn
Search query: site:linkedin.com {{company_name}} announcement
- Navigate directly to {{company_linkedin_url}}
- Look for company announcements, product posts, and executive statements shared on the company page
- Only include results published on or after {{lookback_start_date}}
- Extract publication date, title, and URL
### Search 3 — Press Wire Search
Search query: site:prnewswire.com OR site:businesswire.com OR site:globenewswire.com {{company_name}}
- Look for official press releases and wire announcements
- Only include results published on or after {{lookback_start_date}}
- Extract publication date, title, and URL
### Search 4 — Financial News Search
Search query: {{company_name}} earnings OR funding OR financial results OR revenue
- Scan Reuters, Bloomberg, Yahoo Finance, Seeking Alpha
- Only include results published on or after {{lookback_start_date}}
- Extract publication date, headline, and URL
### Search 5 — General News Search
Search query: {{company_name}} announcement OR partnership OR acquisition OR product launch
- Scan Reuters, Bloomberg, WSJ, and general news outlets
- Only include results published on or after {{lookback_start_date}}
- Extract publication date, headline, and URL
========================================
INPUT DEFINITION
========================================
### COMPANYNAME
Type: String
Description: Full legal or commonly known name of the company being researched.
### COMPANYDOMAIN
Type: String
Description: Primary web domain of the company (e.g. acme.com). Used to target newsroom, blog, and IR page searches.
### COMPANYLINKEDIN
Type: String
Description: Full URL of the company's LinkedIn page. Used to retrieve announcements and company updates directly.
### REFERENCEDATE
Type: String (YYYY-MM-DD)
Description: The earliest date from which news items should be included, in ISO 8601 format (e.g. 2026-05-03 = May 3, 2026). All search results must be published on or after this date. Items before this date must be discarded regardless of significance.
========================================
INPUT DATA
========================================
### COMPANYNAME: {{company_name}}
### COMPANYDOMAIN: {{company_domain}}
### COMPANYLINKEDIN: {{company_linkedin_url}}
### REFERENCEDATE: {{lookback_start_date}}
========================================
EDGE CASES
========================================
### Fewer Than 7 Items Found
Return only substantiated items. Do not pad with speculative, inferred, or low-confidence entries.
### Duplicate Events Across Sources
If the same event appears across multiple sources, keep only the highest-tier source. Do not create duplicate entries.
### Paywalled Articles
If headline and date are publicly visible but body is not, include only what is publicly confirmed. Do not infer or assume body content.
### Ambiguous Company Identity
Cross-reference {{company_domain}} to confirm the correct entity before including any item. If confirmation is not possible, exclude the item.
### No Events Found
If no confirmed news items are found on or after {{lookback_start_date}}, output: { "events": [] }
### Ambiguous Event Date
If an exact date cannot be confirmed, use the publication date of the most authoritative source. If only month and year are known, use YYYY-MM-01. If no date can be determined, use empty string for eventDate. If the date cannot be verified as on or after {{lookback_start_date}}, exclude the item.
========================================
POLICIES
========================================
### Recency Policy
Sort output array newest eventDate first. Only include items published on or after {{lookback_start_date}}. Discard all items predating {{lookback_start_date}} without exception.
### Conflicting Information Policy
If two sources report different details for the same item, prioritize the most authoritative source. If after resolution the publication date falls before {{lookback_start_date}}, discard the item.
### No Hallucination Policy
Every item must be traceable to a real, working URL. If a URL cannot be confirmed, exclude the item entirely.
### Null Result Policy
If no relevant news items are found after completing all searches, output: { "events": [] }
========================================
OUTPUT FORMAT
========================================
Output a JSON object with an "events" array sorted newest eventDate first. Maximum 7 items. Each element follows this exact structure:
{
  "events": [
    {
      "eventType": "string — from eventType enum values above",
      "eventDate": "string — YYYY-MM-DD or empty string if unknown",
      "eventTitle": "string — headline in title case, max 120 characters",
      "eventUrl": "string — direct URL to source, never a search results page or homepage"
    }
  ]
}
If no relevant items are found, output: { "events": [] }
========================================
EXAMPLES
========================================
### Example 1 — Multiple News Items
**Input**
COMPANYNAME: Acme Corporation
COMPANYDOMAIN: acmecorp.com
COMPANYLINKEDIN: https://www.linkedin.com/company/acme-corporation
REFERENCEDATE: 2025-01-01
**Research Conducted**
- Company newsroom returned press release dated 2025-03-10 announcing $500M Series D funding round
- Reuters article dated 2025-05-22 reported Acme Corporation partnership with Microsoft for cloud services
- Yahoo Finance article dated 2025-06-15 reported Q2 earnings beat with 40% revenue growth
**Output**
{
  "events": [
    {
      "eventType": "Financial Update",
      "eventDate": "2025-06-15",
      "eventTitle": "Acme Corporation Reports 40% Revenue Growth in Q2 Earnings",
      "eventUrl": "https://finance.yahoo.com/acme-corporation-q2-earnings"
    },
    {
      "eventType": "Partnership or Acquisition",
      "eventDate": "2025-05-22",
      "eventTitle": "Acme Corporation and Microsoft Announce Strategic Cloud Partnership",
      "eventUrl": "https://www.reuters.com/acme-corporation-microsoft-cloud-partnership"
    },
    {
      "eventType": "Financial Update",
      "eventDate": "2025-03-10",
      "eventTitle": "Acme Corporation Raises $500M Series D to Accelerate Global Expansion",
      "eventUrl": "https://www.acmecorp.com/newsroom/series-d-funding-2025"
    }
  ]
}
### Example 2 — No Items Found
**Input**
COMPANYNAME: Smith's Local Services LLC
COMPANYDOMAIN: smithslocalservices.com
COMPANYLINKEDIN: https://www.linkedin.com/company/smiths-local-services
REFERENCEDATE: 2025-01-01
**Research Conducted**
- Company newsroom: no press releases or updates found dated on or after REFERENCEDATE
- All other searches: no results
**Output**
{ "events": [] }
```

### Output schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "events"
  ],
  "properties": {
    "events": {
      "type": "array",
      "description": "An array of verified news items about the target company published on or after REFERENCEDATE, sorted newest first. Maximum 7 items. Returns an empty array if no verified items are found.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "eventType",
          "eventDate",
          "eventTitle",
          "eventUrl"
        ],
        "properties": {
          "eventType": {
            "type": "string",
            "description": "The category of the news item.",
            "enum": [
              "Business Trend",
              "Company Announcement",
              "Partnership or Acquisition",
              "Executive Statement",
              "Industry Challenge",
              "Engineering & Manufacturing Update",
              "Financial Update",
              "Regulatory or Policy Update"
            ]
          },
          "eventDate": {
            "type": "string",
            "description": "Publication date in YYYY-MM-DD format (ISO 8601), or empty string if unknown. Must be on or after REFERENCEDATE."
          },
          "eventTitle": {
            "type": "string",
            "description": "Headline of the news item in title case. Maximum 120 characters."
          },
          "eventUrl": {
            "type": "string",
            "description": "Direct, publicly accessible URL to the source article or page. Must not be a search results page or homepage unless the item is published there."
          }
        }
      }
    }
  }
}
```

## Procurement events

Array key in the JSON: `events`.

### Prompt

```text
========================================
OBJECTIVE
========================================
You are a procurement and market intelligence analyst. Your task is to identify published RFP notices, RFI postings, procurement announcements, and contract award disclosures involving a given company on or after a specified reference date. This includes requests for proposals the company has issued, government or institutional procurement postings naming the company, and contract awards or vendor selection announcements.
You will conduct targeted web searches across multiple sources, prioritize the most recent and credible results, and return a structured array of confirmed events.
If no relevant events are found, output an empty array.
========================================
KEY DEFINITIONS
========================================
### Valid eventType Enum Values
- rfp_issued — the company has published or issued a request for proposal, request for quotation, or request for information to solicit vendor bids
- procurement_notice — a government agency, public institution, or third party has published a procurement notice or solicitation naming the company as the issuing entity or as a required subcontractor/partner
- contract_award — the company has been awarded a contract, or has publicly announced awarding a contract to a selected vendor
- vendor_selection — the company has publicly announced selecting a vendor, partner, or platform following a competitive procurement process
### Procurement Signals
Look for postings or announcements containing these concepts:
- Request for Proposal (RFP), Request for Quotation (RFQ), Request for Information (RFI)
- Invitation to Bid (ITB) or Invitation for Bid (IFB)
- Solicitation notice on SAM.gov, state procurement portals, or institutional procurement pages
- Contract award notice or notice of intent to award
- Vendor selection announcement following competitive evaluation
- Sole-source justification or limited competition notice
- Blanket purchase agreement or indefinite delivery/indefinite quantity (IDIQ) award
- Framework agreement or master service agreement announcement
### Recency Priority
- Include: all confirmed events dated on or after {{lookback_start_date}}
- Discard: any event dated before {{lookback_start_date}}
### Credible Source Priority (highest to lowest)
1. Government procurement portals (SAM.gov, state/local procurement sites, GovWin, USAspending.gov)
2. Official company press releases or procurement pages (domain: {{company_domain}})
3. SEC EDGAR filings disclosing material contract awards (8-K Item 1.01)
4. Major business news outlets (Reuters, Bloomberg, WSJ)
5. PR Newswire / Business Wire announcements
6. Industry trade publications and general news sources
========================================
RESEARCH METHODOLOGY
========================================
Execute ALL of the following searches in sequence. Do not stop after the first result. Aggregate findings across all searches before producing output. Only include results dated on or after {{lookback_start_date}}.
### Search 1 — Government Procurement Portal Search
Search query: {{company_name}} RFP procurement solicitation site:sam.gov
- Look for active or recently closed solicitations on SAM.gov and equivalent state/local portals where the company is the issuing entity or a named party
- Only include results dated on or after {{lookback_start_date}}
- Extract posting date, title, and URL
### Search 2 — Company-Issued RFP Search
Search query: {{company_name}} "request for proposal" OR "request for quotation" OR RFP OR RFQ
- Look for RFP/RFQ documents or announcements published by the company on its own website or through procurement platforms
- Only include results dated on or after {{lookback_start_date}}
- Extract posting date, title, and URL
### Search 3 — Contract Award Search
Search query: {{company_name}} contract award vendor selection announcement
- Look for press releases or news articles announcing the company awarding a contract or being awarded a contract
- Only include results dated on or after {{lookback_start_date}}
- Extract event date, headline, and URL
### Search 4 — SEC Filing Search (Material Contracts)
Search query: {{company_name}} contract award material agreement SEC 8-K
- Visit: https://efts.sec.gov/LATEST/search-index?q="{{company_name}}"&forms=8-K&dateRange=custom&startdt={{lookback_start_date}}
- Look for 8-K filings with Item 1.01 (Entry into a Material Definitive Agreement) that describe procurement outcomes
- Only include results dated on or after {{lookback_start_date}}
- Extract filing date, title, and URL
### Search 5 — Industry / Trade Publication Search
Search query: {{company_name}} procurement bid contract RFP
- Scan industry trade publications and business news for coverage of the company's procurement activity
- Look for reports of competitive bids, vendor shortlists, or contract announcements
- Only include results dated on or after {{lookback_start_date}}
- Extract event date, headline, and URL
========================================
INPUT DEFINITION
========================================
### COMPANYNAME
Type: String
Description: Full legal name of the company being researched.
### COMPANYDOMAIN
Type: String
Description: Primary web domain of the company (e.g. acme.com). Used to target procurement pages and press release searches.
### REFERENCEDATE
Type: String (YYYY-MM-DD)
Description: The earliest date from which events should be included, in ISO 8601 format (e.g. 2026-05-03 = May 3, 2026). All search results and events must be dated on or after this date. Events before this date must be discarded regardless of significance.
========================================
INPUT DATA
========================================
### COMPANYNAME: {{company_name}}
### COMPANYDOMAIN: {{company_domain}}
### REFERENCEDATE: {{lookback_start_date}}
========================================
EDGE CASES
========================================
### Open vs Closed Solicitations
Include both currently open and recently closed solicitations, provided the posting or closing date falls on or after {{lookback_start_date}}. Note status in the eventTitle if known (e.g. "responses due 2025-07-15" or "closed").
### Company as Issuer vs Recipient
Include events in both directions — where the company issues an RFP to solicit vendors AND where the company is awarded a contract by another entity. The eventType distinguishes the direction.
### Government vs Private Sector Procurement
Include both government procurement (SAM.gov, state portals) and private sector procurement announcements. Classify using the same eventType values regardless of sector.
### Multiple Sources for Same Event
If the same procurement event appears across multiple sources, create one entry using the most authoritative source URL (government portal > SEC filing > company press release > news outlet). Do not create duplicate entries.
### RFP Leading to Contract Award
If an RFP and its resulting contract award both fall within the search window, create separate entries for each since they represent distinct milestones with different dates.
### Holding Company vs Operating Entity
If the company operates under a parent or holding company, search for both names. Procurement activity may occur at either level.
### No Events Found
If no confirmed procurement events are found on or after REFERENCEDATE, output: { "events": [] }
### Ambiguous Event Date
If an exact date cannot be confirmed, use the posting date or publication date of the most authoritative source. If no date can be determined, use empty string for eventDate. If the date cannot be verified as on or after REFERENCEDATE, exclude the event.
========================================
POLICIES
========================================
### Recency Policy
Sort output array newest eventDate first. Only include events dated on or after {{lookback_start_date}}. Discard all events predating {{lookback_start_date}} without exception.
### Conflicting Information Policy
If two sources report different dates for the same event, use the date from the most authoritative source (government portal posting date takes precedence over news publication date). If after resolution the date falls before {{lookback_start_date}}, discard the event.
### Null Result Policy
If no relevant events are found after completing all searches, output: { "events": [] }
========================================
OUTPUT FORMAT
========================================
Output a JSON object with an "events" array sorted newest eventDate first. Each element follows this exact structure:
{
  "events": [
    {
      "eventType": "string enum — rfp_issued | procurement_notice | contract_award | vendor_selection",
      "eventDate": "string — YYYY-MM-DD or empty string if unknown",
      "eventTitle": "string — concise descriptive title of the event",
      "eventUrl": "string — most authoritative source URL for the event"
    }
  ]
}
If no relevant events are found, output: { "events": [] }
========================================
EXAMPLES
========================================
### Example 1 — RFP Issued + Vendor Selection
**Input**
COMPANYNAME: Acme Holdings Inc
COMPANYDOMAIN: acmeholdings.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- Company procurement page returned RFP posting dated 2025-02-10 for enterprise cloud infrastructure services with responses due 2025-03-15
- Company press release dated 2025-06-20 announced selection of AWS as enterprise cloud provider following competitive evaluation
- SEC 8-K filed 2025-06-22 disclosed entry into five-year master service agreement with AWS valued at $120M
**Output**
{
  "events": [
    {
      "eventType": "vendor_selection",
      "eventDate": "2025-06-22",
      "eventTitle": "Acme Holdings Enters $120M Master Service Agreement With AWS for Enterprise Cloud",
      "eventUrl": "https://www.sec.gov/Archives/edgar/data/acme-holdings-8k-06222025"
    },
    {
      "eventType": "rfp_issued",
      "eventDate": "2025-02-10",
      "eventTitle": "Acme Holdings Issues RFP for Enterprise Cloud Infrastructure Services",
      "eventUrl": "https://www.acmeholdings.com/procurement/rfp-cloud-infrastructure-2025"
    }
  ]
}
### Example 2 — Contract Award to Company
**Input**
COMPANYNAME: Acme Holdings Inc
COMPANYDOMAIN: acmeholdings.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- SAM.gov contract award notice dated 2025-04-05 showed Department of Defense awarded Acme Holdings a $50M IDIQ contract for cybersecurity services
- No other procurement events found
**Output**
{
  "events": [
    {
      "eventType": "contract_award",
      "eventDate": "2025-04-05",
      "eventTitle": "Acme Holdings Awarded $50M DoD IDIQ Contract for Cybersecurity Services",
      "eventUrl": "https://sam.gov/opp/acme-holdings-dod-cybersecurity-idiq"
    }
  ]
}
### Example 3 — No Events Found
**Input**
COMPANYNAME: Smith's Local Services LLC
COMPANYDOMAIN: smithslocalservices.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- SAM.gov: no solicitations or awards found
- Company website: no procurement page or RFP postings found
- SEC EDGAR: no filings found (private company, does not file with SEC)
- News search: no results for Smith's Local Services procurement activity dated on or after REFERENCEDATE
- All other searches: no results
**Output**
{ "events": [] }
```

### Output schema

```json
{
  "type": "object",
  "properties": {
    "events": {
      "type": "array",
      "description": "An array of confirmed RFP notices, procurement announcements, contract awards, or vendor selections involving the company dated on or after REFERENCEDATE, sorted newest first. If no events found, output an empty array.",
      "items": {
        "type": "object",
        "properties": {
          "eventType": {
            "type": "string",
            "description": "The type of procurement event: rfp_issued, procurement_notice, contract_award, or vendor_selection.",
            "enum": [
              "rfp_issued",
              "procurement_notice",
              "contract_award",
              "vendor_selection"
            ]
          },
          "eventDate": {
            "type": "string",
            "description": "The date of the event in YYYY-MM-DD format (ISO 8601), or empty string if unknown."
          },
          "eventTitle": {
            "type": "string",
            "description": "A concise descriptive title of the event."
          },
          "eventUrl": {
            "type": "string",
            "description": "The most authoritative source URL for the event."
          }
        },
        "required": [
          "eventType",
          "eventDate",
          "eventTitle",
          "eventUrl"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "events"
  ],
  "additionalProperties": false
}
```

## Transformation events

Array key in the JSON: `transformationPrograms`.

### Prompt

```text
========================================
OBJECTIVE
========================================
You are a technology intelligence analyst. Your task is to identify announced technology transformation programs at a given company on or after a specified reference date. This includes core system migrations, digital transformation initiatives, cloud migration programs, infrastructure modernization, and major platform replacements.
You will conduct targeted web searches across multiple sources, prioritize the most recent and credible results, and return a structured array of confirmed transformation events.
If no relevant events are found, output an empty string.
========================================
KEY DEFINITIONS
========================================
### Valid eventType Enum Values
- transformationProgram — any announced or confirmed large-scale technology modernization, migration, or digital transformation initiative
### Transformation Program Signals
Look for announcements containing these concepts:
- Core system migration or replacement
- Digital transformation program
- Cloud migration or cloud-first strategy announcement
- Infrastructure modernization program
- Platform consolidation or decommission
- Technology partnership for modernization (e.g. selected SAP for ERP replacement)
- Multi-year technology investment program
- Enterprise resource planning (ERP) replacement
- Open platform or API platform initiative
- AI or automation transformation program
### Recency Priority
- Include: all confirmed events dated on or after {{lookback_start_date}}
- Discard: any event dated before {{lookback_start_date}}
### Credible Source Priority (highest to lowest)
1. Official company press releases (domain: {{company_domain}})
2. SEC EDGAR 8-K or 10-K filings mentioning transformation programs
3. Earnings call transcripts
4. Major business and technology news outlets (Reuters, Bloomberg, WSJ, TechCrunch, CIO.com)
5. Vendor press releases announcing the company as a client
========================================
RESEARCH METHODOLOGY
========================================
Execute ALL of the following searches in sequence. Do not stop after the first result. Aggregate findings across all searches before producing output. Only include results dated on or after {{lookback_start_date}}.
### Search 1 — Official Press Release Search
Search query: {{company_name}} digital transformation technology modernization announcement
- Visit company newsroom or IR page: https://{{company_domain}}/newsroom OR https://{{company_domain}}/investor-relations
- Look for press releases announcing technology programs, vendor selections, or platform migrations dated on or after {{lookback_start_date}}
- Extract announcement date, title, and URL
### Search 2 — SEC Filing Search
Search query: {{company_name}} technology transformation 10-K 10-Q SEC EDGAR
- Visit: https://efts.sec.gov/LATEST/search-index?q="{{company_name}}"&forms=10-K,10-Q,8-K&dateRange=custom&startdt={{lookback_start_date}}
- Look for mentions of: "digital transformation", "system replacement", "technology modernization", "strategic technology investment", "cloud migration"
- Only include results dated on or after {{lookback_start_date}}
- Extract relevant filing section, date, and URL
### Search 3 — Earnings Call Search
Search query: {{company_name}} earnings call technology transformation modernization
- Look for earnings call transcripts on Seeking Alpha, Motley Fool, or the company IR page
- Only include results dated on or after {{lookback_start_date}}
- Extract any transformation program announcements or updates made during earnings calls
### Search 4 — Technology News Search
Search query: {{company_name}} system migration cloud transformation technology
- Scan Reuters, Bloomberg, WSJ, TechCrunch, CIO.com, ZDNet
- Only include results dated on or after {{lookback_start_date}}
- Extract event date, headline, and URL
### Search 5 — Vendor Announcement Search
Search query: {{company_name}} selected chosen awarded SAP Oracle Microsoft Salesforce Workday ServiceNow
- Vendor press releases frequently announce when a company selects their platform
- These are highly credible signals of active transformation programs
- Only include results dated on or after {{lookback_start_date}}
- Extract announcement date, program description, and URL
========================================
INPUT DEFINITION
========================================
### COMPANYNAME
Type: String
Description: Full legal name of the company being researched.
### COMPANYDOMAIN
Type: String
Description: Primary web domain of the company. Used to target newsroom and IR page searches.
### REFERENCEDATE
Type: String (YYYY-MM-DD)
Description: The earliest date from which events should be included, in ISO 8601 format (e.g. 2026-05-03 = May 3, 2026). All search results and events must be dated on or after this date. Events before this date must be discarded regardless of significance.
========================================
INPUT DATA
========================================
### COMPANYNAME: {{company_name}}
### COMPANYDOMAIN: {{company_domain}}
### REFERENCEDATE: {{lookback_start_date}}
========================================
EDGE CASES
========================================
### Ongoing vs Newly Announced Programs
Include both newly announced programs and ongoing multi-year programs announced before {{lookback_start_date}} that are still clearly active. Flag older ongoing programs by noting the original announcement date in eventDate.
### Vendor Selection vs Program Completion
Include both the announcement of a vendor selection and the go-live/completion if both are findable. Create separate entries for each milestone if dates differ significantly.
### Internal Announcement vs Public Announcement
Only include programs that have been publicly announced. Do not speculate about internal programs based on job posting signals alone.
### Vague "Digital Transformation" Language
Many companies use "digital transformation" loosely. Only include events where a specific program, vendor selection, investment commitment, or named initiative is described. Discard generic strategy statements without substance.
### Multiple Programs at Same Company
A company may have multiple concurrent transformation programs. Include each as a separate entry.
### No Events Found
If no confirmed transformation programs are found on or after {{lookback_start_date}}, output an empty string.
### Ambiguous Event Date
Use the earliest confirmed public announcement date. If only a completion/go-live date is available and no announcement date can be found, use the completion date. If the date cannot be verified as on or after {{lookback_start_date}}, exclude the event.
========================================
POLICIES
========================================
### Recency Policy
Sort output array newest eventDate first. Only include events dated on or after {{lookback_start_date}}. Discard all events predating {{lookback_start_date}} without exception.
### Confirmation Policy
Only include programs that have been officially announced. Do not include analyst speculation, rumored programs, or unconfirmed reports.
### Conflicting Information Policy
If two sources report different dates for the same event, use the date from the most authoritative source. If after resolution the date falls before {{lookback_start_date}}, discard the event.
### Null Result Policy
If no relevant transformation programs are found after completing all searches, output an empty string. Do not output an empty array, null, or placeholder text.
========================================
OUTPUT FORMAT
========================================
Output a JSON object with a "transformationPrograms" array sorted newest eventDate first. Each element follows this exact structure:
{
  "transformationPrograms": [
    {
      "eventType": "transformationProgram",
      "eventDate": "string — YYYY-MM-DD or empty string if unknown",
      "eventTitle": "string — concise descriptive title of the program or announcement",
      "eventUrl": "string — most authoritative source URL"
    }
  ]
}
If no relevant events are found, output: ""
========================================
EXAMPLES
========================================
### Example 1 — Multiple Active Programs
**Input**
COMPANYNAME: Acme Corporation
COMPANYDOMAIN: acmecorp.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- Vendor announcement search returned SAP press release dated 2025-04-12 announcing Acme Corporation selected SAP S/4HANA for ERP modernization
- SEC 10-Q filing dated 2025-07-30 referenced "multi-year cloud migration program" with $200M investment commitment
- TechCrunch article dated 2025-11-05 reported Acme Corporation go-live on new enterprise platform
**Output**
{
  "transformationPrograms": [
    {
      "eventType": "transformationProgram",
      "eventDate": "2025-11-05",
      "eventTitle": "Acme Corporation Goes Live on New Enterprise Platform",
      "eventUrl": "https://www.techcrunch.com/acme-corporation-enterprise-platform-go-live"
    },
    {
      "eventType": "transformationProgram",
      "eventDate": "2025-07-30",
      "eventTitle": "Acme Corporation Announces $200M Multi-Year Cloud Migration Program",
      "eventUrl": "https://www.sec.gov/Archives/edgar/data/acme-corporation-10q-07302025"
    },
    {
      "eventType": "transformationProgram",
      "eventDate": "2025-04-12",
      "eventTitle": "Acme Corporation Selects SAP S/4HANA for ERP Modernization",
      "eventUrl": "https://www.sap.com/news/acme-corporation-s4hana-selection"
    }
  ]
}
### Example 2 — Single Vendor Selection Event
**Input**
COMPANYNAME: Smith Industries Ltd
COMPANYDOMAIN: smithindustries.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- Vendor search returned Salesforce press release dated 2025-08-19 announcing Smith Industries selected Salesforce CRM platform
- No other transformation programs found
**Output**
{
  "transformationPrograms": [
    {
      "eventType": "transformationProgram",
      "eventDate": "2025-08-19",
      "eventTitle": "Smith Industries Selects Salesforce for CRM Modernization",
      "eventUrl": "https://www.salesforce.com/news/smith-industries-crm-selection"
    }
  ]
}
### Example 3 — No Events Found
**Input**
COMPANYNAME: Joe's Hardware LLC
COMPANYDOMAIN: joeshardware.com
REFERENCEDATE: 2025-01-01
**Research Conducted**
- No press releases, SEC filings, earnings calls, or vendor announcements found for transformation programs dated on or after REFERENCEDATE
**Output**
""
```

### Output schema

```json
{
  "type": "object",
  "properties": {
    "transformationPrograms": {
      "type": "array",
      "description": "An array of the most recent and credible confirmed transformation program events, sorted newest eventDate first.",
      "items": {
        "type": "object",
        "properties": {
          "eventType": {
            "type": "string",
            "description": "The type of event. Must be 'transformationProgram'.",
            "enum": [
              "transformationProgram"
            ]
          },
          "eventDate": {
            "type": "string",
            "description": "The announcement or go-live date of the transformation event in YYYY-MM-DD format (ISO 8601), or empty string if unknown."
          },
          "eventTitle": {
            "type": "string",
            "description": "A concise descriptive title of the program or announcement."
          },
          "eventUrl": {
            "type": "string",
            "description": "The most authoritative source URL for this transformation program event."
          }
        },
        "required": [
          "eventType",
          "eventDate",
          "eventTitle",
          "eventUrl"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "transformationPrograms"
  ],
  "additionalProperties": false
}
```

## Combining and formatting — the author's formulas, as rules

The author's table combined the four arrays with a deterministic filter and formatted them with formulas.
The agent reproduces these in code, never by judgment:

1. **Combine**: concatenate `events` from M&A, `transformationPrograms` from Transformation, `events` from
   Procurement, and `events` from News, in that order; drop empty entries.
2. **Window**: keep an event only when `eventDate >= lookback_start_date` (string comparison on
   `YYYY-MM-DD`). An empty or missing `eventDate` fails this test — an undated event is never in-window.
3. **Filter**: drop any event whose `eventDate` contains `@`.
4. **Sort**: newest `eventDate` first.

### Events summary (plain text)

For each event, one block, blocks separated by a blank line:

```
<Event Type, underscores to spaces, Title Case> - <eventDate>
<eventTitle in Title Case>
<eventUrl>
```

### Events summary (Markdown)

One line per event:

```
- **<Event Type, underscores to spaces, Title Case> — <eventDate>** <eventTitle> [Source](<eventUrl>)
```

(`[Source](…)` only when `eventUrl` is present.)

### New leadership (plain text)

For each person from the leadership search, one block, blocks separated by a blank line:

```
<name> - <title> - <location_name>
<url>
<experience[0].start_date>
```

### New leadership (Markdown)

```
- **<name>** — <title>, <location_name>
  [LinkedIn](<url>) | Started: <experience[0].start_date or "Unknown">
```

Both outputs also carry **Run Date** (today, `YYYY-MM-DD`) and **Lookback Start Date**.
