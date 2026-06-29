# Wiza — Agent Guidance

## When to use

Wiza for LinkedIn → email/phone enrichment. Key advantage over ContactOut: **accepts Sales Navigator and LinkedIn Recruiter URLs** in addition to standard LinkedIn profile URLs. Strong for outbound teams with Sales Nav lists.

Wiza is backed by the upstream OpenAPI contract. Prefer OpenAPI-native payloads
for new work; Deepline still accepts older aliases and normalizes them before
the provider request.

## Provider characteristics

- **Input required**: LinkedIn URL (including Sales Nav), email, or name+company
- **Geographic coverage**: Global
- **Credit cost**: 1 credit for profile-only, 2 credits for email, 5 credits for phone
- **Enrichment levels**: partial (email, 2 credits), phone (5 credits), full (email+phone, 7 credits), none (profile only, 1 credit)
- **Async**: reveals are queued and processed — the handler polls until finished

## Key operations

### wiza_reveal_person

Starts an async enrichment job and polls until finished. Accepts any LinkedIn URL type.

```json
{
  "individual_reveal": {
    "profile_url": "https://www.linkedin.com/in/johndoe"
  },
  "enrichment_level": "partial"
}
```

For personal emails only:

```json
{
  "individual_reveal": {
    "profile_url": "https://www.linkedin.com/in/johndoe"
  },
  "enrichment_level": "partial",
  "email_options": {
    "accept_personal": true
  }
}
```

Wiza does not document an exact spend response header for reveals. The terminal GET result includes `credits.api_credits.total`; Deepline uses that exact result-body value when present. If a terminal result lacks Wiza's credits object, settlement falls back to returned contact fields, not just the requested enrichment level.

For phones + emails:

```json
{
  "individual_reveal": {
    "profile_url": "https://www.linkedin.com/in/johndoe"
  },
  "enrichment_level": "full"
}
```

Name + company fallback:

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "company_domain": "acme.com",
  "enrichment_level": "partial"
}
```

### wiza_search_prospects

Discover prospects by job title, level, company, industry, location. **Free** — returns masked profiles without contact info. Returns up to 30 results per search.

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

Typical flow: search → get LinkedIn URLs → feed into `wiza_reveal_person` to enrich.

## Output shape

`wiza_reveal_person` returns a flat object. Email at `email`, phones at `phone_number1`, `mobile_phone1`. Status at `status` ("finished" | "failed").

`wiza_search_prospects` returns `{ prospects: [...], total: N }`.

## Enrichment levels

| Level     | Returns                        |
| --------- | ------------------------------ |
| `none`    | Profile data only (1 credit)   |
| `partial` | Emails only (2 credits)        |
| `phone`   | Phone numbers only (5 credits) |
| `full`    | Emails + phones (7 credits)    |

## Anti-patterns

- Don't use `enrichment_level: "full"` on large lists without budgeting phone credits separately
- Don't use Wiza defaults for a personal-email-only workflow; pass `email_options: "personal"` to avoid work/generic email lookup.
- Don't skip polling — reveals are async, status starts as "queued"
- Don't expect more than 30 results from search per call
- Don't send a bare location string in new code; use `{ "v": "...", "b": "city|state|country", "s": "i" }`. Legacy `person_location: "New York"` remains accepted and becomes `{ "v": "New York, New York, United States", "b": "city", "s": "i" }`.
