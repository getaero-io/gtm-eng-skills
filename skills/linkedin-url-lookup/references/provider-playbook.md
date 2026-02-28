# Provider Playbook

Detailed API patterns, quirks, and optimization tips for each LinkedIn lookup provider. Read this when implementing or debugging provider-specific issues.

## Table of Contents

1. [Apollo People Match (Primary)](#apollo-people-match-primary)
2. [Google CSE (Fallback)](#google-cse-fallback)
3. [Exa Semantic Search (Fallback)](#exa-semantic-search-fallback)
4. [PeopleDataLabs](#peopledatalabs)
5. [Apify Profile Verification](#apify-profile-verification)
6. [Provider Comparison Matrix](#provider-comparison-matrix)

---

## Apollo People Match (Primary)

**Deepline tool:** `apollo_people_match`
**Direct API:** `POST https://api.apollo.io/v1/people/match`

### When to Use

Primary provider for LinkedIn URL lookup. Best when you have name + company. Apollo's matching algorithm cross-references multiple fields for high precision.

```bash
# Deepline CLI
deepline tools execute apollo_people_match \
  --payload '{"first_name":"Phil","last_name":"Parvaneh","organization_name":"Acme Corp"}' --json
```

### Response Fields

- `linkedin_url` — direct LinkedIn URL
- `organization.name` — matched company
- `title` — current title
- `email` — business email (bonus data)

### Quirks

- Returns `null` for `linkedin_url` when no match — NOT an empty string
- Nickname mismatches cause nulls: "Phil" won't match "Philip" in Apollo
- Company name must be close to Apollo's record: "Synchrony Financial" won't match if Apollo has "Synchrony"
- **Coverage:** ~65% for name+company lookups

### When Apollo Fails

Apollo misses when:
1. **Nickname mismatch** — CRM has "Phil", LinkedIn has "Philip". Fall back to Google CSE/Exa which use broader matching.
2. **Company name variation** — "Synchrony Financial" vs "Synchrony". Try stripped company name.
3. **New/small company** — Apollo's database may not have the company. Fall back to search.
4. **Recent job change** — Person switched companies since last CRM update.

---

## Google CSE (Fallback)

**API:** `GET https://www.googleapis.com/customsearch/v1`
**Auth:** `key` + `cx` query params
**Deprecation:** January 2027

### Query Construction

Multi-pass retry with decreasing specificity — this is key for handling nicknames:

**Pass 1 (strict):**
```
"FirstName LastName" company site:linkedin.com/in
```

**Pass 2 (no quotes — catches name variations):**
```
FirstName LastName company site:linkedin.com/in
```

**Pass 3 (nickname expanded — no company filter):**
```
NicknameExpanded LastName site:linkedin.com/in
```

### Important: Quoted + Context + Site = Too Restrictive

Combining quoted names + context keywords + `site:` restriction often returns 0 results. Drop the quotes first, then drop context keywords.

### Result Filtering

- Only accept URLs containing `/in/` (skip `/company/`, `/posts/`, `/pulse/`)
- Check that first AND last name appear in the result title
- Fallback to first `/in/` link if no name-matched title

### Cost

100 free queries/day, then $5 per 1,000 queries. Budget ~$1.00 for 200 fallback lookups.

---

## Exa Semantic Search (Fallback)

**API:** `POST https://api.exa.ai/search`
**Auth:** `x-api-key` header

### The Secret Weapon: `category` Parameter

Use `category: 'linkedin profile'` instead of `includeDomains: ['linkedin.com']`:

- **`category`** — Server-side ML classifier that pre-filters to LinkedIn profile pages ONLY. Skips company pages, posts, pulse articles.
- **`includeDomains`** — Simple domain filter that includes ALL LinkedIn pages (company, posts, etc.)

Combine with `type: 'neural'` for semantic name/company matching that handles nicknames and name variations.

```json
{
  "query": "\"John Smith\" Acme LinkedIn profile",
  "numResults": 5,
  "category": "linkedin profile",
  "type": "neural",
  "contents": {
    "text": {"maxCharacters": 500}
  }
}
```

### Result Scoring

Exa returns `results[].{url, title, text}`. Score by:

1. Name appears in title: +5
2. Company appears in title or text: +15
3. Pick highest-scoring `/in/` URL

### When Exa Wins

- Nickname mismatches (semantic search handles "Phil" → "Philip")
- Unusual name spellings
- People with very common names (semantic context helps disambiguate)

### Cost

~$0.01 per search. Budget ~$1.00 for 100 fallback lookups.

---

## PeopleDataLabs

**Deepline tool:** `peopledatalabs_person_identify`
**Direct API:** `GET https://api.peopledatalabs.com/v5/person/identify`

### When to Use

As a secondary waterfall step after Apollo in Deepline CLI waterfalls. Best with name + company, can also use LinkedIn URL for enrichment.

```bash
deepline tools execute peopledatalabs_person_identify \
  --payload '{"first_name":"Phil","last_name":"Parvaneh","company":"Acme Corp"}' --json
```

### Response Fields

- `data.linkedin_url` — LinkedIn URL
- `data.0.linkedin_url` — Some responses nest in array

### Quirks

- Returns a likelihood score (1-10). Filter ≥6 for reliable matches.
- Company matching is fuzzy but sometimes TOO fuzzy — validate results.
- **Coverage:** ~55% for name+company lookups

---

## Apify Profile Verification

**Deepline tool:** `apify_run_actor_sync`
**Actor:** `apimaestro/linkedin-profile-scraper-no-cookies`

### Purpose

Apify is NOT for finding LinkedIn URLs — it's for **verifying** them after the waterfall. It scrapes the actual LinkedIn profile to confirm the person's identity and current company.

### Usage

```bash
# Verify a single profile
deepline tools execute apify_run_actor_sync \
  --payload '{
    "actorId": "apimaestro/linkedin-profile-scraper-no-cookies",
    "input": {"username": "https://www.linkedin.com/in/johnsmith"},
    "timeoutMs": 60000
  }' --json
```

### Batch verification (post-waterfall)

```bash
# Only run on rows that have a linkedin URL resolved
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with 'profile=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-profile-scraper-no-cookies","input":{"username":"{{linkedin}}"},"timeoutMs":60000}'
```

### Response Fields for Validation

Key fields to check:

- `data.firstName`, `data.lastName` — Confirm name match
- `data.headline` — Contains current title + company
- `data.currentPositions[].companyName` — Current employer(s)
- `data.experience[].companyName` — Full work history (for job changers)
- `data.location` — Geographic info

### Validation Logic

```python
def verify_with_apify(profile_data, expected_first, expected_last, expected_company):
    """Verify Apify profile data matches expected contact."""
    # Name check
    profile_name = f"{profile_data.get('firstName', '')} {profile_data.get('lastName', '')}".lower()
    name_ok = expected_first.lower() in profile_name and expected_last.lower() in profile_name

    # Company check — current positions first, then full history
    company_ok = False
    expected_clean = normalize_company(expected_company).lower()

    for pos in profile_data.get('currentPositions', []):
        if expected_clean in (pos.get('companyName', '') or '').lower():
            company_ok = True
            break

    if not company_ok:
        for exp in profile_data.get('experience', []):
            if expected_clean in (exp.get('companyName', '') or '').lower():
                company_ok = True  # Job changer — flag for review
                break

    return name_ok and company_ok
```

### Cost & Rate Limiting

- ~5 credits per profile scrape
- Apify has concurrent task limits — queue requests sequentially if hitting limits
- Verify returned data actually contains expected fields before processing (check for empty/blocked responses)
- **Cost optimization:** Don't verify every URL. Spot-check 10% to measure false positive rate. Only bulk-verify if rate > 10%.

---

## Provider Comparison Matrix

| Provider | Cost/Call | Coverage | Nicknames | Company Validation | Best For |
|----------|----------|----------|-----------|-------------------|----------|
| Apollo People Match | ~1 credit | ~65% | No | Cross-referenced | Primary — highest precision |
| Google CSE | $0.005 | ~50% | Via multi-pass retry | Manual (from results) | Broad fallback, name variations |
| Exa Semantic | ~$0.01 | ~45% | Yes (neural) | From text snippet | Edge cases, nickname mismatches |
| PeopleDataLabs | ~1 credit | ~55% | No | Fuzzy | Secondary in Deepline waterfall |
| Apify Profile | ~5 credits | N/A (verify only) | N/A | Full work history | Post-waterfall identity verification |

### Recommended Waterfall Orders

**Deepline CLI (simple):**
Apollo → PeopleDataLabs → (Apify verify)

**Custom waterfall (max coverage):**
Apollo → Google CSE (multi-pass with nicknames) → Exa → (Apify verify)

**Budget-conscious:**
Apollo → PeopleDataLabs → (spot-check 10% with Apify)
