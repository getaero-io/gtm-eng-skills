# Wiza — Agent Guidance

## Prospect search

`wiza_search_prospects` discovers prospects by title, level, company, industry, and location. It returns names, titles, companies, and LinkedIn URLs without contact information. `size` sets how many profiles come back (default 0, which returns only the match count; maximum 30), and each returned profile is billed.

```json
{
  "filters": {
    "job_title": [{ "v": "VP of Sales", "s": "i" }],
    "job_title_level": ["VP"],
    "company_industry": [{ "v": "SaaS", "s": "i" }],
    "location": [{ "v": "United States", "b": "country", "s": "i" }]
  }
}
```

Search matches the employer by name only, through `job_company` (for example `[{ "v": "Acme", "s": "i" }]`). It has no company domain filter. `filters.company_domain` without a company name is rejected; sent with one, it is ignored and the result carries a warning. When you start from a domain, resolve the company name first. Unknown filter keys are rejected.

The response is `{ prospects: [...], total: N }`. Do not expect more than 30 results per call. Use structured locations (`v`, `b`, `s`) for new payloads; older aliases remain accepted and normalized.

`wiza_get_individual_reveal` reads an existing reveal. `wiza_get_credits` reads account credits. Use these operations only for data the user is authorized to access. Do not recommend Sales Navigator saved-search scraping or browser-session credential reuse.

## SDK/API reveal contract

The existing SDK/CLI/API reveal operation remains available. Its OpenAPI-native payload accepts `individual_reveal` plus `enrichment_level`; older aliases still normalize before dispatch. Reveals are queued and polled to a terminal state. The levels are `none` (profile), `partial` (email), `phone`, and `full` (email and phone).

A reveal returns a flat object with `email`, `phone_number1`, `mobile_phone1`, and `status` (`finished` or `failed`). The terminal result's `credits.api_credits.total`, when present, determines settlement. Without that credits object, settlement uses returned contact fields rather than the requested level. Budget email and phone work separately; no intermediary agreement establishes authorization from the source platform.
