# ContactOut — Agent Guidance

## When to use

ContactOut for LinkedIn → email/phone enrichment when you have a LinkedIn URL. High accuracy for active LinkedIn users. Strong for US + global. Falls after dropleads in cost-ordered waterfalls.

**Key differentiator**: Free pre-check APIs (`contactout_check_email_status`) tell you if a profile has work or personal email on file before spending credits. Always use these first when enriching at scale.

## Provider characteristics

- **Input required**: LinkedIn URL (best), email, or name+company
- **Geographic coverage**: Global, strongest in US + Europe
- **Credit cost**: ~$0.10 per email credit; separate phone + search credits
- **LinkedIn URL requirement**: Must contain "linkedin.com/in/" or "linkedin.com/pub/". Sales Navigator URLs not supported.

## Key operations

### contactout_check_email_status (FREE — use first at scale)

Check if a LinkedIn profile has work email on file. Zero credits consumed. Use this to filter out profiles with no coverage before running enrichment.

```json
{
  "profile": "https://www.linkedin.com/in/johndoe"
}
```

Returns: `{ "has_work_email": true, "has_personal_email": false }`

### contactout_enrich_person

Enriches a person by LinkedIn URL (preferred), email, or name+company. Returns email array at `email`, `work_email`, `personal_email`.

```json
{
  "linkedin_url": "https://www.linkedin.com/in/johndoe",
  "include": ["work_email"]
}
```

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "company_domain": "acme.com"
}
```

### contactout_search_people

Search people by title, company, location, seniority. Use `reveal_info: false` (default) for count/discovery. Set `reveal_info: true` to retrieve emails (costs search + email credits).

```json
{
  "job_title": "(VP OR Head) Sales",
  "company_size": "201-500",
  "location": "United States",
  "reveal_info": false
}
```

Boolean logic supported: `"(Sales AND CRM) NOT Manager"`

### contactout_enrich_domain

Enriches company data (size, industry, funding, HQ) from a domain name.

```json
{
  "domain": "salesforce.com"
}
```

## Output shape

`contactout_enrich_person` returns a flat profile object. Email at `email[0]`, `work_email[0]`, or `personal_email[0]`. No nested envelope.

`contactout_search_people` returns `{ profiles: [...], metadata: { total_results: N } }`.

## Anti-patterns

- Don't use Sales Navigator or Recruiter URLs — they'll return 400
- Don't skip `check_email_status` when enriching a large list — it's free and filters out empty profiles
- Don't include "http://" or "www." in domain values for `enrich_domain`
- Don't set `reveal_info: true` on search without knowing the count first — use `reveal_info: false` to size the audience
