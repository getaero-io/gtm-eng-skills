# LinkedIn URL Validation Rules

**Without validation, ~54% of LinkedIn lookups are false positives.** Every resolved URL must pass name + company validation before acceptance.

## Table of Contents

1. [Validation Decision Tree](#validation-decision-tree)
2. [Name Validation](#name-validation)
3. [Company Validation](#company-validation)
4. [Apify Profile Verification](#apify-profile-verification)
5. [Confidence Scoring](#confidence-scoring)
6. [Nickname Mappings](#nickname-mappings)
7. [Company Alias Mappings](#company-alias-mappings)
8. [Edge Cases](#edge-cases)

---

## Validation Decision Tree

```
LinkedIn URL found (from Apollo/CSE/Exa)
  ├── Slug pre-filter: first name at start, last name present?
  │   ├── NO → MISMATCH → Reject, try next provider
  │   └── YES → Continue validation
  │       ├── Name matches profile? (first + last)
  │       │   ├── YES → Company matches? (current or past employer)
  │       │   │   ├── YES → CONFIRMED (score ≥25) → Accept
  │       │   │   ├── FUZZY → LIKELY (score 15-24) → Accept with review
  │       │   │   └── NO → NAME_ONLY → Apify verify or try next provider
  │       │   └── NO → Try nickname expansion
  │       │       ├── Nickname matches → Re-validate with expanded name
  │       │       └── Still no → MISMATCH → Reject, try next provider
  │       └── No name data available → Apify verify to get full profile
  └── No URL found → Try next provider in waterfall

Post-waterfall: Apify verify all CONFIRMED/LIKELY URLs
  ├── Profile scrape returns currentPositions + experience
  ├── Confirm name + company against full work history
  └── Flag CHANGED_JOBS if company only appears in past positions
```

## Name Validation

### Slug-based pre-filter (no API call needed)

Fast pre-filter before spending API calls on validation:

```python
def validate_slug(slug, first_name, last_name):
    """Fast pre-filter: check if name matches LinkedIn slug."""
    slug_clean = slug.replace('-', '').replace('/', '').rstrip('0123456789')
    first_clean = first_name.lower().replace("'", "").replace(" ", "")
    last_clean = last_name.lower().replace("'", "").replace(" ", "")

    first_at_start = slug_clean.startswith(first_clean)
    last_appears = last_clean in slug_clean or last_clean[:5] in slug_clean

    return first_at_start and last_appears
```

### Full name validation

```python
def validate_name_match(first_name, last_name, profile_name):
    """Check if first and last name appear in the LinkedIn profile name."""
    if not profile_name:
        return False
    profile_lower = profile_name.lower()
    first_lower = first_name.lower().strip()
    # Handle multi-part last names - check the final surname token
    last_parts = last_name.strip().split()
    last_lower = last_parts[-1].lower() if last_parts else ''
    return first_lower in profile_lower and last_lower in profile_lower
```

**Rules:**
- First name must match profile first name (case-insensitive, starts-with OK)
- Last name must appear in profile last name
- Middle names/initials are ignored
- Handle reversed slug order: some slugs are `lastname-firstname`
- If initial match fails, try nickname expansion before rejecting

## Company Validation

### Company normalization

```python
COMPANY_SUFFIXES = [
    ', Inc.', ', Inc', ' Inc.', ' Inc', ', LLC', ' LLC',
    ', Corp.', ' Corp.', ' Corp', ', Ltd.', ' Ltd.', ' Ltd',
    ', LP', ' LP', ', L.P.', ' L.P.', ' LLP', ', LLP',
    ' Group', ' Holdings', ' International',
]

def normalize_company(name):
    """Normalize company name for fuzzy matching."""
    result = name.strip()
    for suffix in COMPANY_SUFFIXES:
        if result.endswith(suffix):
            result = result[:-len(suffix)].strip()
    return result.lower()
```

### Fuzzy company matching

```python
def company_matches(source_company, profile_company):
    """Check if two company names refer to the same organization."""
    a = normalize_company(source_company)
    b = normalize_company(profile_company)
    # Substring match (handles "Synchrony Financial" vs "Synchrony")
    if a in b or b in a:
        return True
    # Check aliases
    for key, aliases in COMPANY_ALIASES.items():
        if key in a or a in key:
            for alias in aliases:
                if alias in b:
                    return True
    # First significant word match (for multi-word companies)
    words = a.split()
    generic = {'the', 'of', 'and', 'for', 'in', 'at', 'global', 'group', 'inc', 'international'}
    significant = [w for w in words if w not in generic and len(w) > 3]
    if significant and significant[0] in b:
        return True
    return False
```

### What counts as a match

- Current employer matches source company (**strongest** — +15 points)
- Past employer matches source company (valid — person may have changed jobs, +10 points)
- Company subsidiary/parent matches (e.g., "Instagram" matches "Meta")

### What does NOT count

- Advisor/board member roles — these are not real employment
- Volunteer positions
- Education entries

## Apify Profile Verification

After the waterfall resolves candidate URLs, verify with Apify profile scraping:

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with 'profile=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-profile-scraper-no-cookies","input":{"username":"{{linkedin}}"},"timeoutMs":60000}'
```

### What to check in Apify response

| Field | Validation | Points |
|-------|-----------|--------|
| `data.firstName` + `data.lastName` | Must match expected name (fuzzy) | +10 |
| `data.currentPositions[].companyName` | Must match expected company | +15 |
| `data.experience[].companyName` | Company in past positions | +10 (flag CHANGED_JOBS) |
| `data.headline` | Contains expected title/company | +5 |

### When to Apify-verify

- **Always verify:** High-value contacts (enterprise decision-makers, named accounts)
- **Spot-check:** 10% sample to measure false positive rate for bulk lists
- **Skip:** If false positive rate < 10% on spot-check, save credits

### Apify rate limiting

- Concurrent task limits — queue requests sequentially
- Verify returned HTML contains expected content (check for key fields)
- If Apify returns empty/blocked response, retry once then skip

## Confidence Scoring

| Score | Status | Meaning | Action |
|-------|--------|---------|--------|
| 25+ | CONFIRMED | Name + company match | Accept immediately |
| 15-24 | LIKELY | Name match, company fuzzy | Accept with review |
| 5-14 | NAME_ONLY | Partial match, no company | Manual review or Apify verify |
| <5 | MISMATCH | Low/no confidence | Reject, try next provider |

**Scoring breakdown:**

| Signal | Points | Notes |
|--------|--------|-------|
| Exact name match (first + last) | +10 | Both names in profile |
| First name + partial last | +7 | First exact, last contains target |
| Partial name match | +3 | One name matches loosely |
| Current company match | +15 | Company in currentPositions |
| Past company match | +10 | Company in work history |
| Name in URL slug | +5 | `/in/firstlast` pattern |
| Apify-verified identity | +10 | Full profile confirms match |
| Name mismatch | -10 | Neither name matches |
| No company data available | 0 | Can't validate, but not negative |

## Nickname Mappings

Common nickname → formal name mappings. **Try both directions** — if "Phil" fails, try "Philip", and vice versa:

| Nickname | Formal Name(s) |
|----------|----------------|
| Phil | Philip |
| Bob, Rob | Robert |
| Mike | Michael |
| Bill, Will | William |
| Jim, Jimmy | James |
| Joe | Joseph |
| Dan, Danny | Daniel |
| Tom, Tommy | Thomas |
| Dick, Rick | Richard, Frederick |
| Ted | Theodore, Edward |
| Liz, Beth | Elizabeth |
| Kate, Katie | Katherine, Catherine |
| Jen, Jenny | Jennifer |
| Chris | Christopher, Christine |
| Alex | Alexander, Alexandra |
| Sam, Sammy | Samuel, Samantha |
| Matt | Matthew |
| Dave | David |
| Steve | Steven, Stephen |
| Tony | Anthony |
| Nick | Nicholas |
| Ben | Benjamin |
| Greg | Gregory |
| Pat | Patrick, Patricia |
| Doug | Douglas |
| Jeff | Jeffrey |
| Andy, Drew | Andrew |
| Charlie, Chuck | Charles |
| Ed, Eddie | Edward, Edmund |
| Jack | John |
| Wes | Wesley |
| Meg, Maggie | Margaret |
| Sue | Susan |

### Nickname expansion in waterfall

When the primary lookup returns null, retry with expanded nicknames:

1. Check if first name is a known nickname → try formal name(s)
2. Check if first name is a known formal name → try nickname(s)
3. If multiple alternates exist, try the most common one first

## Company Alias Mappings

Major companies with common abbreviations or alternate names:

```python
COMPANY_ALIASES = {
    'ernst & young': ['ey', 'ernst & young', 'ernst and young'],
    'blue cross': ['bcbs', 'blue cross', 'blue cross blue shield'],
    'jpmorgan': ['jp morgan', 'jpmorgan', 'chase', 'jpmorgan chase'],
    'pwc': ['pricewaterhousecoopers', 'pwc'],
    'deloitte': ['deloitte', 'deloitte touche', 'dtt'],
    'kpmg': ['kpmg'],
    'bank of america': ['bofa', 'bank of america', 'merrill lynch', 'merrill'],
    'at&t': ['att', 'at&t'],
    'ibm': ['ibm', 'international business machines'],
    'ge': ['general electric', 'ge'],
    'meta': ['facebook', 'meta', 'instagram', 'whatsapp'],
    'alphabet': ['google', 'alphabet', 'youtube', 'deepmind'],
    'microsoft': ['microsoft', 'linkedin', 'github', 'azure'],
}
```

## Edge Cases

### 1. O'Rourke, St. James, Van der Berg

Special characters in names cause mismatches. Normalize before matching:

- O'Rourke → ORourke, Rourke
- St. James → St James, StJames
- Van der Berg → Vanderberg, Van der Berg
- McDonald → Mcdonald, MacDonald

### 2. Very common names

"John Smith" returns hundreds of results. Company validation is critical — without it, you'll match the wrong John Smith.

### 3. Job changers

Person left the company in your CRM. Their LinkedIn now shows a different employer. Options:
- Use Apify profile scraper to get full `experience[]` array
- Accept the match if name + former company appear anywhere in work history
- Flag as CHANGED_JOBS for manual review

### 4. Hyphenated/maiden names

"Sarah Johnson-Smith" in CRM might be "Sarah Johnson" or "Sarah Smith" on LinkedIn. Try:
1. Full hyphenated name
2. First part only (maiden name)
3. Second part only (married name)
