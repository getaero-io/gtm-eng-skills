# LinkedIn event organizer extraction

Office-hours example from May 7, 2026.

Search LinkedIn events by keyword, extract the organizer for each event, look up their LinkedIn profile, and export to Google Sheets. No API keys — runs entirely through Deepline.

## What we built

12 keyword searches (webinar, masterclass, virtual summit, etc.) via Deepline's managed LinkedIn identity layer — no cookies, no LinkedIn account needed. Each search returns 10 events from a fresh session. Deduplicated to 105 unique events, then extracted organizer names and company pages for all of them.

Results:
- 105 unique events
- 36 named individual organizers (34%)
- 63 company LinkedIn URLs (all 105 events attempted)

## How it works

**Phase 1 — Search:** call `linkedin_scraper_linkedin_search_events` with a search URL for each keyword. Deduplicate by event ID. Write to CSV.

**Phase 2 — Extract:** call `linkedin_scraper_linkedin_extract_event` for each URL. Individual-hosted events return `first_name` / `last_name`. Company-hosted events return blank — the API has no individual to surface. For company-hosted events, call `linkedin_scraper_linkedin_extract_company` with the company name to get the company LinkedIn page URL.

**Phase 3 — Profile lookup:** for named organizers, call `name_to_linkedin_url_waterfall` with first name, last name, and company. Fast but fuzzy — returns wrong profile ~20% of the time.

**Phase 4 — Export:** write to Google Sheets via Sheets API. Named organizers tab has green/red conditional formatting on validation status.

## Key finding

66% of events are company-hosted. The organizer API returns blank for those. To find the individual behind a company event, you'd need to scrape the company's LinkedIn page for the events or marketing lead separately. This script captures company LinkedIn page URLs for all 105 events so that enrichment pass is possible later.

## Files

- `extract_organizers.py` — main two-phase pipeline. Calls Deepline tools for each event, writes phase 2 CSV incrementally.
- `export_to_sheets.py` — Google Sheets export via OAuth2. Creates spreadsheet, formats headers, adds conditional formatting on name_validated column.
- `phase1_search_results.csv` — raw search results (105 events).
- `phase2_event_organizers.csv` — enriched output with organizer names, LinkedIn URLs, and company pages.

## Deepline tools used

| Tool | Purpose | Cost |
|---|---|---|
| `linkedin_scraper_linkedin_search_events` | Search events by keyword | $0.07/result |
| `linkedin_scraper_linkedin_extract_event` | Extract event detail + organizer info | $0.07/result |
| `linkedin_scraper_linkedin_extract_company` | Company LinkedIn page lookup | $0.07/result |
| `name_to_linkedin_url_waterfall` | Individual profile URL lookup | ~$0.06–$0.12/call |

## Usage

```bash
# Authenticate once
deepline auth status

# Run the pipeline (both phases)
python examples/office-hours/linkedin-event-organizers/extract_organizers.py

# Skip phase 1 if you already have search results
python examples/office-hours/linkedin-event-organizers/extract_organizers.py --skip-search

# Export to Google Sheets (requires OAuth setup)
python examples/office-hours/linkedin-event-organizers/export_to_sheets.py
```

## Pagination

LinkedIn's event search doesn't support true pagination via the `page=` URL param when called through a managed identity — each call gets a fresh session with no scroll state. To get more than 10 events per keyword, use different keyword variations. "Virtual summit" and "masterclass" return almost no overlap with "webinar."

## What's next

- Email lookup for validated organizers via Fullenrich or BetterContact waterfall
- Sequence activation via Lemlist — event context is a natural outreach hook
- For company-hosted events: scrape company LinkedIn page to find events/marketing lead
