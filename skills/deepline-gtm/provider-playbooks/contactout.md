# ContactOut — Agent Guidance

## When to use

ContactOut for LinkedIn → email/phone enrichment when you have a LinkedIn URL. High accuracy for active LinkedIn users. Strong for US + global. Falls after dropleads in cost-ordered waterfalls.

**Key differentiator**: Free pre-check APIs (`contactout_check_email_status`, `contactout_check_work_email`, `contactout_check_personal_email`, `contactout_check_phone`) tell you which contact channels are present before you spend credits on enrichment. Use these first when enriching at scale.

## Provider characteristics

- **Input required**: LinkedIn URL (best), email, or name+company
- **Geographic coverage**: Global, strongest in US + Europe
- **Provider credit cost**: ~$0.10 per ContactOut email credit; separate phone + search credits
- **LinkedIn URL requirement**: Must contain "linkedin.com/in/" or "linkedin.com/pub/". Sales Navigator URLs not supported.

## Key operations

### contactout_linkedin_contact_info

Uses ContactOut's Contact Info API (`GET /v1/people/linkedin`) for one LinkedIn profile. For personal-email waterfalls, call this instead of `contactout_enrich_person`:

```json
{
  "profile": "https://www.linkedin.com/in/johndoe",
  "email_type": "personal"
}
```

`email_type` accepts `personal`, `work`, `personal,work`, or `none`. ContactOut only consumes email credits when emails are returned; `email_type: "none"` returns no emails and consumes no email credits. `include_phone: true` can consume phone credits when phone numbers are returned.

ContactOut does not document a per-call charge response header for this endpoint. Deepline billing is therefore locked to the documented response fields: one email credit when any returned email bucket is non-empty, plus one phone credit when a phone bucket is non-empty.

### contactout_check_email_status (FREE convenience helper)

Checks work-email and personal-email availability together for one LinkedIn profile.

```json
{
  "profile": "https://www.linkedin.com/in/johndoe"
}
```

Returns:

- `contactout_check_email_status` → `{ "has_personal_email": false, "has_work_email": true, "status": "verified" }`

### contactout_check_work_email / contactout_check_personal_email / contactout_check_phone (FREE — use first at scale)

Check whether a LinkedIn profile has work email, personal email, or phone coverage. Zero credits consumed. Use these to filter out profiles with no coverage before running enrichment.

```json
{
  "profile": "https://www.linkedin.com/in/johndoe"
}
```

Returns one channel-specific payload per tool:

- `contactout_check_work_email` → `{ "has_work_email": true, "status": "verified" }`
- `contactout_check_personal_email` → `{ "has_personal_email": false }`
- `contactout_check_phone` → `{ "has_phone": true }`

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

`contactout_linkedin_contact_info` returns the same flat profile object, but profile-only responses with no email or phone data are treated as no-result for billing and waterfall control.

`contactout_search_people` returns `{ profiles: [...], metadata: { total_results: N } }`.

## Anti-patterns

- Don't use Sales Navigator or Recruiter URLs — they'll return 400
- Don't skip the free checker tools when enriching a large list — they filter out empty profiles before you spend credits
- Don't include "http://" or "www." in domain values for `enrich_domain`
- Don't set `reveal_info: true` on search without knowing the count first — use `reveal_info: false` to size the audience
