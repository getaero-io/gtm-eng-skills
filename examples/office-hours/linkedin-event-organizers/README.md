# LinkedIn event organizer extraction

Office-hours example from May 7, 2026.

Search LinkedIn events by keyword, extract the organizer for each event, look up their LinkedIn profile, and export to Google Sheets. Two versions: one using Deepline (no API keys needed), one using the Edges API directly.

## What we built

12 keyword searches (webinar, masterclass, virtual summit, etc.) via managed LinkedIn identity — no cookies, no LinkedIn account needed. Each search returns 10 events from a fresh session. Deduplicated to 105 unique events, then extracted organizer names and company pages for all of them.

Results:
- 105 unique events
- 36 named individual organizers (34%)
- 63 company LinkedIn URLs (all 105 events attempted)

## How it works

**Phase 1 — Search:** search events by keyword URL. Deduplicate by event ID. Write to CSV.

**Phase 2 — Extract:** extract event detail for each URL. Individual-hosted events return `first_name` / `last_name`. Company-hosted events return blank — the API has no individual to surface. For those, look up the company LinkedIn page by name.

**Phase 3 — Profile lookup:** for named organizers, look up their LinkedIn profile URL by name + company. Fast but fuzzy — returns wrong profile ~20% of the time.

**Phase 4 — Export:** write to Google Sheets via Sheets API. Named organizers tab has green/red conditional formatting on validation status.

## Key finding

66% of events are company-hosted. The organizer API returns blank for those. To find the individual behind a company event, you'd need to scrape the company's LinkedIn page for the events or marketing lead separately. This script captures company LinkedIn page URLs for all 105 events so that enrichment pass is possible later.

## Files

- `extract_organizers_deepline.py` — pipeline using Deepline CLI. No API keys needed, just `deepline auth status`.
- `extract_organizers_edges.py` — pipeline using Edges API directly. Requires `EDGES_API_KEY`.
- `export_to_sheets.py` — Google Sheets export via OAuth2. Creates spreadsheet, formats headers, adds conditional formatting on name_validated column.
- `phase1_search_results.csv` — raw search results (105 events).
- `phase2_event_organizers.csv` — enriched output with organizer names, LinkedIn URLs, and company pages.

## Version comparison

| | Deepline (`extract_organizers_deepline.py`) | Edges (`extract_organizers_edges.py`) |
|---|---|---|
| Auth | `deepline auth status` | `EDGES_API_KEY` env var |
| LinkedIn identities | Managed by Deepline | Managed by Edges |
| Search | `linkedin_scraper_linkedin_search_events` | `linkedin-search-events` |
| Extract | `linkedin_scraper_linkedin_extract_event` | `linkedin-extract-event` |
| Profile lookup | `name_to_linkedin_url_waterfall` | `linkedin-find-profile-url` |
| Company lookup | `linkedin_scraper_linkedin_extract_company` | `linkedin-search-companies` |
| Cost tracking | Deepline dashboard | `GET /v1/workspaces` |

## Usage

**Deepline version (recommended):**
```bash
deepline auth status

python extract_organizers_deepline.py
python extract_organizers_deepline.py --skip-search  # resume from phase 1 CSV
```

**Edges version:**
```bash
export EDGES_API_KEY=your_key

python extract_organizers_edges.py
python extract_organizers_edges.py --skip-search
```

**Export to Google Sheets (both versions write the same CSV format):**
```bash
python export_to_sheets.py
```

## Pagination

LinkedIn's event search doesn't support true pagination via the `page=` URL param when called through a managed identity — each call gets a fresh session with no scroll state. To get more than 10 events per keyword, use different keyword variations. "Virtual summit" and "masterclass" return almost no overlap with "webinar."

## What's next

- Email lookup for validated organizers via Fullenrich or BetterContact waterfall
- Sequence activation via Lemlist — event context is a natural outreach hook
- For company-hosted events: scrape company LinkedIn page to find events/marketing lead
