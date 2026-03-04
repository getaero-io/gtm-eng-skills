---
name: get-leads-at-company
disable-model-invocation: true
description: |
  Given a company name or list of companies, find GTM-relevant contacts, pick the
  best ICP fit, research their recent activity, and draft personalized outreach.

  Read gtm-meta-skill to guide how to use this skill.
---

> Start here first: read `gtm-meta-skill` before running this skill.
> On completion, follow `gtm-meta-skill` Section 7 for proactive issue feedback and the session-sharing Yes/No consent step.

# Get Leads at Company

From a company name (or list), this skill resolves the company identity, finds GTM employees, picks the best ICP match, researches their LinkedIn activity, and drafts personalized outreach — all in one enrichment chain.

## Quickstart: simple contact lookup - dropleads is great to start with because its free. 

if that has bad results / empty results, broaden filters or switch to a second dropleads query.

```bash
deepline tools execute dropleads_search_people \
  --payload '{
    "filters": {
      "companyNames": ["Acme Corp"],
      "jobTitles": ["VP Sales", "Head of Revenue", "GTM", "Revenue Operations"]
    },
    "pagination": {"page": 1, "limit": 10}
  }'
```

## Full chain: company list → personalized outreach

This pipeline:

1. Resolves company identity via dropleads (name + company-level targeting)
2. Finds LinkedIn employees via Apify
3. Picks best ICP contact via AI
4. Researches their recent posts
5. Drafts a personalized outbound message

```bash
deepline enrich --input companies.csv --in-place --rows 0:0 \
  --with 'apollo_company=apollo_company_search:{"q_organization_name":"{{Company}}","per_page":3,"page":1}' \
  --with 'company_profile=run_javascript:@$WORKDIR/company_profile.js' \
  --with 'employees=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-company-employees-scraper-no-cookies","input":{"identifier":"{{company_profile.data.company_linkedin}}","max_employees":60,"job_title":"gtm"},"timeoutMs":180000}' \
  --with 'pick_contact=call_ai_claude_code:{"model":"sonnet","json_mode":{"type":"object","properties":{"full_name":{"type":"string"},"headline":{"type":"string"},"linkedin_url":{"type":"string"},"why_fit":{"type":"string"}},"required":["full_name","headline","linkedin_url","why_fit"]},"system":"Pick the single best outreach persona for GTM at this company. Prefer revenue ops, growth, GTM engineering, or sales leadership.","prompt":"Company: {{Company}}\nCandidates: {{employees.data}}\nReturn strict JSON only."}' \
  --with 'recent_posts=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-profile-posts","input":{"username":"{{pick_contact.extracted_json.linkedin_url}}","total_posts":5,"limit":5},"timeoutMs":180000}' \
  --with 'post_signals=call_ai_claude_code:{"model":"haiku","json_mode":{"type":"object","properties":{"themes":{"type":"array","items":{"type":"string"}},"signals":{"type":"array","items":{"type":"string"}},"hook":{"type":"string"}},"required":["themes","signals","hook"]},"prompt":"Analyze for outbound personalization.\nPerson: {{pick_contact.output}}\nPosts: {{recent_posts.extracted_json}}\nReturn strict JSON."}' \
  --with 'message=call_ai_claude_code:{"model":"sonnet","json_mode":{"type":"object","properties":{"subject":{"type":"string"},"body":{"type":"string"}},"required":["subject","body"]},"prompt":"Write a concise outbound message (≤90 words) to {{pick_contact.extracted_json.full_name}} at {{company_profile.data.company_name}}. Use these signals: {{post_signals.extracted_json}}. Be casual, specific, no fluff."}'
```

After validating one row, scale:

```bash
deepline enrich --input companies.csv --in-place --rows 1: \
  # ... same flags
```

Use `run_javascript:@$WORKDIR/<script>.js` for all JS transform columns; do not inline JSON `{"code":"..."}` payloads.

## Simpler version: just find contacts (no messaging)

```bash
deepline enrich --input companies.csv --in-place --rows 0:1 \
  --with 'contacts=dropleads_search_people:{"filters":{"companyNames":["{{Company}}"],"jobTitles":["VP Sales","Head of Revenue","Revenue Operations","GTM"],"personalCountries":{"include":["United States"]}},"pagination":{"page":1,"limit":5}}'
```

## Column reference after full chain

- `company_profile.data.company_name` — resolved company name
- `company_profile.data.company_domain` — primary domain
- `pick_contact.extracted_json.full_name` — selected contact name
- `pick_contact.extracted_json.linkedin_url` — their LinkedIn
- `pick_contact.extracted_json.why_fit` — AI rationale for selection
- `post_signals.extracted_json.hook` — personalization hook from posts
- `message.extracted_json.subject` + `message.extracted_json.body` — outbound message

## When company_linkedin is null

If `company_profile.data.company_linkedin` is null, the Apify employee scraper will fail. Fall back to broader contact search:

```bash
deepline enrich --input companies.csv --in-place --rows 0:0 \
  --with 'contacts=dropleads_search_people:{"filters":{"companyNames":["{{Company}}"],"jobTitles":["VP Sales","Head of Revenue","Revenue Operations","GTM","CRO"],"seniority":["C-Level","VP","Director","Owner"]},"pagination":{"page":1,"limit":10}}'
```

## Seniority filtering

When searching for decision-makers, add seniority filters to avoid getting individual contributors:

```bash
"person_seniorities": ["c_suite", "vp", "director", "owner"]
```

Valid seniority values: `c_suite`, `vp`, `director`, `manager`, `senior`, `entry`, `owner`, `partner`

## Tips

- Prefer `max_employees: 60` for smaller companies; increase for enterprises
- Filter by `job_title: "gtm"` for a broad GTM net; use `"sales"` or `"revenue"` for narrower searches
- Always add `person_seniorities` to avoid noisy results from IC roles
- Run `deepline playground start --csv companies.csv --open` after enrichment to review rows

## Cost estimation

The full chain is expensive per company — pilot first:

| Step | Credits | Notes |
|------|---------|-------|
| `dropleads_search_people` | ~1 | Company resolution |
| `apify_run_actor_sync` (employees) | ~5-10 | LinkedIn scraping, varies by company size. Highest quality |
| `call_ai_claude_code` (pick + signals + message) | 0 | 3 AI calls total |
| **Full chain total** | **~7-12** | **Per company** |

For large lists, use the simpler Dropleads-only version first, then run the full chain only on high-priority accounts.

## Related skills

- **Need emails after finding contacts?** → Use `contact-to-email` skill
- **Need LinkedIn URLs?** → Use `linkedin-url-lookup` skill
- **Building the account list from scratch?** → Use `build-tam` skill first
- **Want to score accounts before outreach?** → Use `niche-signal-discovery` skill

## Get started

Sign up and get your API key at [code.deepline.com](https://code.deepline.com).

```bash
curl -s "https://code.deepline.com/api/v2/cli/install" | bash
deepline auth register
```
