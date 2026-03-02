---
name: linkedin-url-lookup
description: |
  Resolve LinkedIn profile URLs from contact name + company name. Uses a multi-pass
  waterfall with validation to handle nicknames (Phil/Philip), name variations
  (O'Rourke/Rourke), and false positives (54% without validation).

  Two approaches: Deepline CLI for quick batch enrichment, or custom waterfall
  with Apollo → Google CSE → Exa providers + Apify profile verification.

  Triggers:
  - "find LinkedIn URL for [name] at [company]"
  - "get LinkedIn profiles for my contact list"
  - "linkedin url lookup"
  - "resolve linkedin urls"
  - "match contacts to linkedin"

  Requires: Deepline CLI — https://code.deepline.com
---

> Start here first: read `gtm-meta-skill` before running this skill.

# LinkedIn URL Lookup

Resolve LinkedIn profile URLs from name + company with strict identity validation. **Without validation, expect ~54% false positive rate** — this skill handles the edge cases that break naive lookups.

## Choose your approach

| Approach | Best for | Coverage | Setup |
|----------|----------|----------|-------|
| [Deepline CLI](#deepline-cli-approach) | Quick batch enrichment, simple pipelines | ~70% (Apollo + PDL) | `deepline auth register` |
| [Custom waterfall](#custom-waterfall-approach) | Full control, max coverage, nickname handling | ~85% (Apollo + CSE + Exa) | API keys for CSE + Exa |

---

## Deepline CLI Approach

### Quick lookup: single contact

```bash
deepline tools execute apollo_people_match \
  --payload '{"first_name":"Phil","last_name":"Parvaneh","organization_name":"Acme Corp"}' --json
```

Check `linkedin_url` in the response. If null, use the batch waterfall.

### Batch lookup: CSV waterfall

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with-waterfall "linkedin" \
  --type linkedin \
  --result-getters '["linkedin_url","data.linkedin_url","data.0.linkedin_url"]' \
  --with 'apollo=apollo_people_match:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}"}' \
  --with 'pdl=peopledatalabs_person_identify:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company":"{{Company}}"}' \
  --end-waterfall
```

Required columns: `First Name`, `Last Name`, `Company`

### Nickname expansion for Deepline

When the waterfall returns null, retry with expanded nicknames. Add a nickname expansion step before the waterfall:

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with 'expanded_name=run_javascript:{"code":"const nicknames={\"phil\":[\"philip\"],\"bob\":[\"robert\"],\"mike\":[\"michael\"],\"bill\":[\"william\"],\"jim\":[\"james\"],\"joe\":[\"joseph\"],\"dan\":[\"daniel\"],\"tom\":[\"thomas\"],\"dick\":[\"richard\"],\"ted\":[\"theodore\",\"edward\"],\"rob\":[\"robert\"],\"liz\":[\"elizabeth\"],\"kate\":[\"katherine\",\"catherine\"],\"jen\":[\"jennifer\"],\"chris\":[\"christopher\",\"christine\"],\"alex\":[\"alexander\",\"alexandra\"],\"sam\":[\"samuel\",\"samantha\"],\"matt\":[\"matthew\"],\"dave\":[\"david\"],\"steve\":[\"steven\",\"stephen\"],\"tony\":[\"anthony\"],\"nick\":[\"nicholas\"],\"ben\":[\"benjamin\"],\"greg\":[\"gregory\"],\"pat\":[\"patrick\",\"patricia\"],\"rick\":[\"richard\",\"frederick\"],\"doug\":[\"douglas\"],\"jeff\":[\"jeffrey\"],\"andy\":[\"andrew\"],\"charlie\":[\"charles\"],\"ed\":[\"edward\",\"edmund\"],\"jack\":[\"john\"],\"wes\":[\"wesley\"]}; const f=(row[\"First Name\"]||\"\").trim(); const fl=f.toLowerCase(); const alts=nicknames[fl]||[]; const formals=Object.entries(nicknames).filter(([k,v])=>v.includes(fl)).map(([k])=>k); return {original:f,alternates:[...alts,...formals]};"}' \
  --with-waterfall "linkedin" \
  --type linkedin \
  --result-getters '["linkedin_url","data.linkedin_url"]' \
  --with 'apollo_orig=apollo_people_match:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}"}' \
  --with 'apollo_alt=apollo_people_match:{"first_name":"{{expanded_name.data.alternates.0}}","last_name":"{{Last Name}}","organization_name":"{{Company}}"}' \
  --with 'pdl=peopledatalabs_person_identify:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company":"{{Company}}"}' \
  --end-waterfall
```

### Apify verification (post-waterfall)

After resolving LinkedIn URLs, verify them with Apify profile scraping to confirm the person actually works at the expected company:

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with 'profile=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-profile-scraper-no-cookies","input":{"username":"{{linkedin}}"},"timeoutMs":60000}'
```

Check `profile.data.currentPositions` or `profile.data.experience` to confirm company match. This catches false positives where the name matched but it's a different person.

---

## Custom Waterfall Approach

For maximum coverage (~85%), use a 3-tier waterfall: Apollo → Google CSE → Exa. Then verify all results with Apify.

### Provider hierarchy

| Tier | Provider | Why | Coverage | Cost |
|------|----------|-----|----------|------|
| 1 | Apollo People Match | Best structured data, cross-references name + company | ~65% | ~1 credit |
| 2 | Google CSE | Broad web index, multi-pass with decreasing specificity | +10% | $5/1000 |
| 3 | Exa Semantic Search | Neural matching handles nicknames and edge cases | +10% | ~$0.01/call |
| Verify | Apify Profile Scraper | Confirms identity — scrapes actual LinkedIn profile | 100% of found | ~5 credits |

### Key implementation patterns

**1. Apollo first, then search-based fallbacks:**

Apollo's matching algorithm cross-references multiple fields (name, company, email). When Apollo returns null (nickname mismatch, company name variation), fall back to Google CSE and Exa which use broader matching.

**2. Google CSE multi-pass for nickname handling:**

When initial search fails, retry with decreasing specificity:

1. `"FirstName LastName" company site:linkedin.com/in` (strict — quoted name + company)
2. `FirstName LastName company site:linkedin.com/in` (no quotes — handles name variations)
3. `NicknameExpanded LastName site:linkedin.com/in` (alternate name — no company filter)

**Important:** Combining quoted names + context keywords + `site:` restriction often returns 0 results. Drop quotes first, then drop context keywords.

**3. Exa `category: 'linkedin profile'` is critical:**

Use `category: 'linkedin profile'` (server-side ML classifier) instead of `includeDomains: ['linkedin.com']`. The category filter pre-filters to personal profile pages only — skipping company pages, posts, and pulse articles.

Combine with `type: 'neural'` for semantic matching that handles nicknames ("Phil" → "Philip").

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

**4. Apify verification after the waterfall (not during):**

Don't verify inline during the waterfall — it's expensive. Run the full waterfall first to get candidate URLs, then batch-verify with Apify:

```bash
# Step 1: Waterfall to find URLs (cheap)
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with-waterfall "linkedin" \
  --type linkedin \
  --result-getters '["linkedin_url","data.linkedin_url","data.0.linkedin_url"]' \
  --with 'apollo=apollo_people_match:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","organization_name":"{{Company}}"}' \
  --with 'pdl=peopledatalabs_person_identify:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company":"{{Company}}"}' \
  --end-waterfall

# Step 2: Verify found URLs with Apify (only rows that have a URL)
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with 'profile=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-profile-scraper-no-cookies","input":{"username":"{{linkedin}}"},"timeoutMs":60000}'
```

Then validate `profile.data` against expected name + company using the validation rules in [references/validation-rules.md](references/validation-rules.md).

**5. Batch checkpointing:**

For large batches (800+), save checkpoint after every contact:

```python
checkpoint['completed'][contact_key] = result
checkpoint['last_index'] = idx
save_checkpoint(checkpoint)
# Resume: --resume flag loads checkpoint and skips completed contacts
```

### Cost estimate (800+ contacts)

| Step | Provider | Est. Calls | Cost |
|------|----------|-----------|------|
| Waterfall | Apollo | ~800 | ~800 credits |
| Waterfall | PDL (Apollo misses) | ~300 | ~300 credits |
| Waterfall | Google CSE (both miss) | ~200 | ~$1.00 |
| Waterfall | Exa (CSE misses) | ~100 | ~$1.00 |
| Verification | Apify (all found URLs) | ~600 | ~3000 credits |
| **Total** | | **~2,000** | **~4,100 credits + $2** |

**Cost optimization:** Only Apify-verify high-value contacts or spot-check a sample (e.g., 10%) to measure false positive rate. If rate < 10%, skip bulk verification.

---

## Validation rules (CRITICAL)

**Every resolved LinkedIn URL must pass validation before acceptance.** See [references/validation-rules.md](references/validation-rules.md) for the full validation framework, nickname mappings, and company aliases.

### Quick reference

| Check | Rule | Why |
|-------|------|-----|
| First name | Must match profile (fuzzy: starts-with OK) | Catch wrong-person matches |
| Last name | Must appear in profile last name or slug | Same |
| Company | Must match current or past employer (fuzzy) | Verify identity, not just name |
| Role type | Must be operational role, not advisor/volunteer | Advisors inflate match counts |
| Slug check | First name at start of slug, last name present | Fast pre-filter, no API needed |

### Company matching uses fuzzy logic

- "Synchrony Financial" matches "Synchrony"
- "Bank of America" matches "BofA" or "Bank of America Merrill Lynch"
- Strip Inc., LLC, Corp., Ltd. before comparing
- Check company alias table (EY/Ernst & Young, Meta/Facebook, etc.)

### Confidence scoring

| Score | Status | Action |
|-------|--------|--------|
| 25+ | CONFIRMED | Accept — name + company match |
| 15-24 | LIKELY | Accept with spot-check |
| 5-14 | NAME_ONLY | Manual review or fallback |
| <5 | MISMATCH | Reject, try next provider |

---

## Edge cases that break naive lookups

### 1. Nickname mismatch (Phil vs Philip)

CRM says "Phil Parvaneh" but LinkedIn says "Philip Parvaneh". Quoted searches `"Phil Parvaneh"` return 0 results.

**Fix:** When the initial lookup returns null, retry with expanded nicknames. See the [nickname mapping table](references/validation-rules.md#nickname-mappings) for all 30+ mappings.

### 2. Name spelling variations (O'Rourke vs Rourke)

Apostrophes, hyphens, and prefixes cause mismatches.

**Fix:** Strip special characters before matching:
- O'Rourke → ORourke, Rourke
- St. James → St James, StJames
- Van der Berg → Vanderberg, Van der Berg

### 3. Quoted name searches too restrictive

Google CSE with `"Phil Parvaneh" + context keywords site:linkedin.com/in` returns 0 results.

**Fix:** Multi-pass retry with decreasing specificity:
1. `"FirstName LastName" company site:linkedin.com/in` (strict)
2. `FirstName LastName site:linkedin.com/in` (no quotes)
3. `NicknameExpanded LastName site:linkedin.com/in` (alternate name)

### 4. Job changers

Person left the company in your CRM. Their LinkedIn shows a different employer.

**Fix:** Use Apify profile scraper to get full work history. Accept the match if name + former company appear anywhere in `experience[]`. Flag as CHANGED_JOBS for manual review.

---

## After lookup

Validate results before using:

```bash
deepline playground start --csv contacts.csv --open
```

Spot-check 5-10 resolved URLs manually. If false positive rate > 10%, tighten validation or run Apify verification on all results.

## Provider details

See [references/provider-playbook.md](references/provider-playbook.md) for API patterns, quirks, and cost details per provider.

## Related skills

- **Need emails after resolving LinkedIn?** → Use `contact-to-email` skill (Workflow B)
- **Finding contacts at companies?** → Use `get-leads-at-company` skill
- **Understanding waterfall patterns?** → See `waterfall-enrichment` skill

## Get started

```bash
curl -s "https://code.deepline.com/api/v2/cli/install" | bash
deepline auth register
```
