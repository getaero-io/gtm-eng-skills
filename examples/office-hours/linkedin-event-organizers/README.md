# LinkedIn Event Organizer Extraction

Office-hours example from May 7, 2026.

Extract organizer and attendee context from LinkedIn event pages while handling public-page limits and authenticated scraping constraints.

## Flow

1. Try a public fetch first.
2. If the page is login-gated, route to a browser-backed or authenticated provider.
3. Use Apify actors for structured LinkedIn extraction when the actor supports the target page shape.
4. Keep a fallback CSV input so the workflow can still test enrichment, scoring, and outreach when LinkedIn blocks scraping.
5. Normalize organizers into company, title, LinkedIn URL, event URL, and confidence.

## Files

- `workflow.json` - provider-routing skeleton for event organizer extraction.
