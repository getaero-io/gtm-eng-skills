---
name: linkedin-url-lookup
disable-model-invocation: true
description: |
  Resolve LinkedIn profile URLs from contact name + company name. Uses a multi-pass
  waterfall with validation to handle nicknames (Phil/Philip), name variations
  (O'Rourke/Rourke), and false positives (54% without validation).

  Before reading this file, first read gtm-meta-skill to understand the Deepline CLI tool and how to use it. Then read this file for guidance on the task.
---

# LinkedIn URL Lookup

Resolve LinkedIn profile URLs from name + company with strict identity validation. **Without validation, expect ~54% false positive rate** — this skill handles the edge cases that break naive lookups.

## Choose your approach

| Approach | Best for | Coverage | Setup |
|----------|----------|----------|-------|
| [Deepline CLI](#deepline-cli-approach) | Quick batch enrichment, simple pipelines | ~70% (Dropleads + PDL) | `deepline auth register` |
| [Custom waterfall](#custom-waterfall-approach) | Full control, max coverage, nickname handling | ~85% (Dropleads + CSE + Exa) | API keys for CSE + Exa |

---

## Deepline CLI Approach

### Quick lookup: single contact

```bash
deepline tools execute dropleads_search_people \
  --payload '{"filters":{"keywords":["Phil Parvaneh"],"companyNames":["Acme Corp"]},"pagination":{"page":1,"limit":1}}'
```

Check `linkedin_url` in the response. If null, use the batch waterfall.

### Batch lookup: CSV waterfall

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with-waterfall "linkedin" \
  --type linkedin \
  --result-getters '["linkedin_url","data.linkedin_url","data.0.linkedin_url"]' \
  --with 'dropleads=dropleads_search_people:{"filters":{"keywords":["{{First Name}} {{Last Name}}"],"companyNames":["{{Company}}"]},"pagination":{"page":1,"limit":1}}' \
  --with 'pdl=peopledatalabs_person_identify:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company":"{{Company}}"}' \
  --end-waterfall
```

Required columns: `First Name`, `Last Name`, `Company`

### Nickname expansion for Deepline

When the waterfall returns null, retry with expanded nicknames. Add a nickname expansion step before the waterfall:

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with 'expanded_name=run_javascript:@$WORKDIR/expand_nicknames.js' \
  --with-waterfall "linkedin" \
  --type linkedin \
  --result-getters '["linkedin_url","data.linkedin_url"]' \
  --with 'dropleads_orig=dropleads_search_people:{"filters":{"keywords":["{{First Name}} {{Last Name}}"],"companyNames":["{{Company}}"]},"pagination":{"page":1,"limit":1}}' \
  --with 'dropleads_alt=dropleads_search_people:{"filters":{"keywords":["{{expanded_name.data.alternates.0}} {{Last Name}}"],"companyNames":["{{Company}}"]},"pagination":{"page":1,"limit":1}}' \
  --with 'pdl=peopledatalabs_person_identify:{"first_name":"{{First Name}}","last_name":"{{Last Name}}","company":"{{Company}}"}' \
  --end-waterfall
```

For `run_javascript`, use file-backed scripts only (`run_javascript:@$WORKDIR/<script>.js`); avoid inline JSON `{"code":"..."}` payloads.

### Apify verification (post-waterfall)

After resolving LinkedIn URLs, verify them with Apify profile scraping to confirm the person actually works at the expected company:

```bash
deepline enrich --input contacts.csv --in-place --rows 0:1 \
  --with 'profile=apify_run_actor_sync:{"actorId":"apimaestro/linkedin-profile-scraper-no-cookies","input":{"username":"{{linkedin}}"},"timeoutMs":60000}'
```

Check `profile.data.currentPositions` or `profile.data.experience` to confirm company match. This catches false positives where the name matched but it's a different person.

---

## Custom Waterfall Approach

For maximum coverage (~85%), use a 3-tier waterfall: Dropleads → Google CSE → Exa. Then verify all results with Apify.

### Provider hierarchy

| Tier | Provider | Why | Coverage | Cost |
|------|----------|-----|----------|------|
| 1 | Dropleads People Search | Best structured data, name + company signals | ~65% | ~1 credit |
| 2 | Google CSE | Broad web index, multi-pass with decreasing specificity | +10% | $5/1000 |
| 3 | Exa Semantic Search | Neural matching handles nicknames and edge cases | +10% | ~$0.01/call |
| Verify | Apify Profile Scraper | Confirms identity — scrapes actual LinkedIn profile | 100% of found | ~5 credits |

### Key implementation patterns

**1. Dropleads first, then search-based fallbacks:**

Dropleads can miss nuanced names and small companies. When it returns null (nickname mismatch, company name variation), fall back to Google CSE and Exa which use broader matching.

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
  --with 'dropleads=dropleads_search_people:{"filters":{"keywords":["{{First Name}} {{Last Name}}"],"companyNames":["{{Company}}"]},"pagination":{"page":1,"limit":1}}' \
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
| Waterfall | Dropleads | ~800 | ~800 credits |
| Waterfall | PDL (Dropleads misses) | ~300 | ~300 credits |
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
