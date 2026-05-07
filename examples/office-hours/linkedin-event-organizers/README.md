# LinkedIn event organizer extraction

Office-hours example from May 7, 2026.

Search LinkedIn events by keyword, extract the organizer for each event, look up their LinkedIn profile, validate it with Apify, and export to Google Sheets. Total cost for 105 events: $8.88.

## What we built

12 keyword searches (webinar, masterclass, virtual summit, etc.) via Edges managed identity API — no cookies, no LinkedIn account needed. Each search returns 10 events from a fresh session. Deduplicated to 105 unique events, then extracted organizer names and company pages for all of them.

Results:
- 105 unique events
- 36 named individual organizers (34%)
- 28 validated via Apify name match (80% accuracy)
- 63 company LinkedIn URLs (all 105 events attempted)
- $8.88 total

## How it works

**Phase 1 — Search:** call `linkedin-search-events` with a search URL for each keyword. Deduplicate by event ID. Write to CSV.

**Phase 2 — Extract:** call `linkedin-extract-event` for each URL. Individual-hosted events return `first_name` / `last_name`. Company-hosted events return blank — the API has no individual to surface. For company-hosted events, call `linkedin-search-companies` with the company name to get the company LinkedIn page URL.

**Phase 3 — Profile lookup:** for named organizers, call `linkedin-find-profile-url` with full name + company. Fast but fuzzy — returns wrong profile ~20% of the time.

**Phase 4 — Apify validation:** run every returned URL through Apify's LinkedIn Profile Scraper (dev_fusion actor). Scrapes full name, headline, company name, company LinkedIn URL, company website. Validates on first name only (not current company — the profile may show a past role that still makes it correct).

**Phase 5 — Export:** write to Google Sheets via Sheets API. Named organizers tab has green/red conditional formatting on validation status.

## Key finding

66% of events are company-hosted. The organizer API returns blank for those. To find the individual behind a company event, you'd need to scrape the company's LinkedIn page for the events or marketing lead separately. This script captures company LinkedIn page URLs for all 105 events so that enrichment pass is possible later.

## Files

- `extract_organizers.py` — main two-phase pipeline script. Reads from phase 1 CSV, calls Edges for each event, writes phase 2 CSV incrementally.
- `export_to_sheets.py` — Google Sheets export via OAuth2. Creates spreadsheet, formats headers, adds conditional formatting on name_validated column, registers hyperlinks.
- `phase1_search_results.csv` — raw search results (105 events).
- `phase2_event_organizers.csv` — enriched output with organizer names, LinkedIn URLs, company pages, validation status.

## Cost breakdown

| Step | Action | Credits | Cost |
|---|---|---|---|
| Event search | 12 queries × 15 credits | 150 | $2.90 |
| Event extraction | 105 × 1.5 credits | 157.5 | $3.05 |
| Company lookup | 69 company-hosted × 4.5 credits | 310.5 | $2.58 |
| Profile lookup | 36 organizers × ~2.9 credits | 105 | $2.03 |
| Apify validation | 35 profiles × $0.01 | 35 profiles | $0.35 |
| **Total** | | | **$8.88** |

Edges Silver plan pricing: $19.35/1K credits.
Apify dev_fusion LinkedIn Profile Scraper: $0.01/profile, 99.9% 30-day success rate.

## Usage

```bash
# Set credentials
export EDGES_API_KEY=your_key
export APIFY_API_TOKEN=your_token

# Run the pipeline (both phases)
python deepline/data/linkedin-event-organizers/extract_organizers.py

# Skip phase 1 if you already have search results
python deepline/data/linkedin-event-organizers/extract_organizers.py --skip-search

# Export to Google Sheets (requires OAuth setup)
python deepline/data/linkedin-event-organizers/export_to_sheets.py
```

## Pagination

LinkedIn's event search doesn't support true pagination via the `page=` URL param when called through a managed identity — each call gets a fresh session with no scroll state. To get more than 10 events per keyword, use different keyword variations. "Virtual summit" and "masterclass" return almost no overlap with "webinar."

## What's next

- Email lookup for validated organizers via Fullenrich or BetterContact waterfall
- Sequence activation via Lemlist — event context is a natural outreach hook
- For company-hosted events: scrape company LinkedIn page to find events/marketing lead
