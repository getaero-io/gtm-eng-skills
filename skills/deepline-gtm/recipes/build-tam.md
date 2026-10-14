---
name: build-tam
description: 'Build a Total Addressable Market list: size the audience, source companies from ICP filters, then find contacts at those companies at scale.'
---

# Build a TAM List

Use this for requests like "build a TAM or list from ICP filters, then pull contacts at scale", "we sourced 935K leads and need the last 65K", or "we exhausted most strategies and need new lead-sourcing channels".

Each step says what to get. Find the tool or prebuilt play for it with `deepline search "<input you have -> result you need>"`, then read its filters and price with `deepline describe <tool>` or `deepline describe <play>`.

1. **Write the ICP as filters.** Industry or category, headcount range, geography, funding stage, technology, hiring signal. Note the target count and which filters are hard requirements.
2. **Check for a known source first.** When the companies are listed on a page you can name, such as a portfolio, a directory, a registry, or a conference site, extract that page instead of reconstructing it from searches.
3. **Size the audience before pulling rows.** Use a count tool, or run the search with a limit of 1 and read the total. A total far from the target means the filters are wrong; more pages will not fix it.
4. **Source companies first, then people.** Run a structured company search with the ICP filters. Check enum-like values such as industry names and regions against the tool's autocomplete or described enum before a full search, because a guessed value returns nothing without an error. Read a small sample for fit, then pull more than the target when you expect rows to drop out later.
5. **Fill gaps from a second, independent source.** Dedupe on company domain. When database-style search returns little, as it does for pre-revenue startups, niche verticals, and many non-US markets, switch to web search or a local-business search instead of widening the same filters. Resolve a missing domain from the company's official site, never from the spelling of its name.
6. **Find people at those companies.** `prebuilt/company-to-contact` returns the best role-matched contact for one company, and its `-batch` form takes a CSV. For a broad function, search with one or two function keywords plus seniority instead of guessed exact titles, which miss real ones. For nuanced roles at named companies, follow `find-qualified-titles.md`.
7. **Add contact data only to the rows you keep.** Emails and phones go through the prebuilt batch plays named in the skill's working rules.
8. **Run it as a play, and stop at good enough.** Pilot on a small slice, read its cost, then run the full list. Filter out bad matches and fill gaps instead of restarting discovery, and use the firmographics the search already returned instead of enriching them again.

```bash
deepline search "ICP filters -> count of matching companies or people, before pulling rows"
deepline search "ICP filters (industry, headcount, country, funding stage) -> matching companies with domains"
deepline search "company domains -> people in a function at director level or above"
```
