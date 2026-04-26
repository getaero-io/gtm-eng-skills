# Wiza — Agent Guidance

## When to use

Wiza for LinkedIn → email/phone enrichment. Key advantage over ContactOut: **accepts Sales Navigator and LinkedIn Recruiter URLs** in addition to standard LinkedIn profile URLs. Strong for outbound teams with Sales Nav lists.

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
  "linkedin_url": "https://www.linkedin.com/in/johndoe",
  "enrichment_level": "partial"
}
```

For phones + emails:
```json
{
  "linkedin_url": "https://www.linkedin.com/in/johndoe",
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
    "job_title": "VP of Sales",
    "job_level": "vp",
    "company_industry": "SaaS",
    "person_location": "United States"
  }
}
```

Typical flow: search → get LinkedIn URLs → feed into `wiza_reveal_person` to enrich.

## Output shape

`wiza_reveal_person` returns a flat object. Email at `email`, phones at `phone_number1`, `mobile_phone1`. Status at `status` ("finished" | "failed").

`wiza_search_prospects` returns `{ prospects: [...], total: N }`.

## Enrichment levels

| Level | Returns |
|---|---|
| `none` | Profile data only (1 credit) |
| `partial` | Emails only (2 credits) |
| `phone` | Phone numbers only (5 credits) |
| `full` | Emails + phones (7 credits) |

## Anti-patterns

- Don't use `enrichment_level: "full"` on large lists without budgeting phone credits separately
- Don't skip polling — reveals are async, status starts as "queued"
- Don't expect more than 30 results from search per call
