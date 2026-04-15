# RocketReach — Agent Guidance

## When to use

RocketReach for email + phone lookup when dropleads misses. Strong coverage for non-tech companies and US-heavy lists. Falls after dropleads and hunter in cost-ordered waterfalls. Good for person lookup by LinkedIn URL, name+company, or known email.

## Provider characteristics

- **Input required**: LinkedIn URL (preferred), name+company, or email
- **Geographic coverage**: Global, strongest in US
- **Credit cost**: ~$0.12 per person lookup; ~$0.12 per search result
- **Database**: 700M+ professional profiles, 60M+ companies
- **Phone coverage**: Requires `lookup_type: "premium"` to unlock mobile/direct numbers

## Key operations

### rocketreach_lookup_person

Looks up a single person by LinkedIn URL, name+company, or email. Handles async lookups automatically — the handler polls until the status is `"complete"`.

```json
{
  "linkedin_url": "https://www.linkedin.com/in/johndoe"
}
```

With premium phone numbers:
```json
{
  "linkedin_url": "https://www.linkedin.com/in/johndoe",
  "lookup_type": "premium"
}
```

Name + company fallback when no LinkedIn URL:
```json
{
  "name": "John Doe",
  "current_employer": "Acme Corp"
}
```

### rocketreach_search_people

Search with filters. Returns profiles array. Use `contact_method: "email"` to filter to profiles with known emails.

```json
{
  "page_size": 25,
  "query": {
    "current_title": ["VP of Sales", "Head of Sales"],
    "company_size": ["201-500", "501-1000"],
    "country_code": ["US"],
    "contact_method": "email"
  }
}
```

### rocketreach_lookup_company

Look up company metadata by domain or name.

```json
{
  "domain": "salesforce.com"
}
```

## Output shape

`rocketreach_lookup_person` returns a flat profile object. Best email at `recommended_email` or `recommended_professional_email`. All emails at `emails[*].email`. Phones at `phones[*].number`.

`rocketreach_search_people` returns `{ profiles: [...] }`. Same field paths on each profile.

## Email quality

Each email has a `grade` field (A+ = highest deliverability confidence) and `smtp_valid` ("valid" | "invalid" | "unknown"). Prefer `recommended_email` for outbound — it's the highest-grade address.

## Anti-patterns

- Don't call without at least one identifier (linkedin_url, name, or email)
- Don't use name-only without current_employer
- Don't expect phone numbers without `lookup_type: "premium"`
- Don't use for bulk company search — use search_people with company filters instead
