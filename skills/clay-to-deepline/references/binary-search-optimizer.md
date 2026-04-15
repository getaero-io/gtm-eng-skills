# Binary Search Optimizer (Claygent Web Research Pattern)

Use whenever replicating a `use-ai (claygent + web)` column that does multi-step web research. Matches Clay's adaptive search behavior (search → read snippet → detect gaps → follow-up) while using confidence gates to avoid unnecessary API calls.

## Pass Structure

```python
# Pass A — deterministic, parallel, highlights-only (cheap)
# Always runs. 3 fixed search angles.
# IMPORTANT: Include domain in ALL 3 queries to prevent name-collision failures
# (e.g. "onit.com" → Onity Group; "getflex.com" → Flex Ltd electronics)
queries = [
    f'"{co_name}" {domain} 10-K annual report investor relations strategic initiatives',
    f'"{co_name}" {domain} new product launches features announcements 2024 2025',
    f'"{co_name}" {domain} go-to-market new customer segments market expansion 2024 2025',
]
# highlights_only=True: contents={'highlights': {'numSentences': 3, 'highlightsPerUrl': 2}}
# ~10x fewer tokens than text=True — sufficient for snippet scoring

# Pass B — synthesis with confidence gate
schema = {
    ...output fields...,
    "confidence": {"type": "string"},        # "high" | "medium" | "low"
    "missing_angles": {"type": "array", "items": {"type": "string"}}
}
# confidence == "high": STOP. Done.

# Pass C — conditional follow-up (only if confidence != "high")
# 1-2 targeted exa searches on missing_angles[0:2], text=True

# Pass D — re-synthesize with follow-up research

# Pass E — primary-source deep-read (only if still confidence != "high")
# Find authoritative URL via _extract_primary_source_url(exa_text, company_domain)
# Fetch with text=True, re-synthesize
```

## Tracking Columns

Always emit these alongside output:

| Column | Values | Purpose |
|---|---|---|
| `research_confidence` | `"high"` / `"medium"` / `"low"` | Gates passes C and E |
| `research_passes` | `"1"` / `"2"` / `"3"` | Cost analysis |

## Confidence Calibration (26-row Production Data)

**`low` ≠ bad output.** 26 rows across varied company types:
- `high`: 0/26 (0%) — essentially never reached with Exa
- `medium`: 9/26 (35%) — large public companies, funded startups with active blogs
- `low`: 17/26 — but 13/17 had specific, actionable content

Clay uses Google (better 10-K discovery); Deepline uses Exa (better recent blog/PR). These confidence scales are not equivalent — don't map Deepline `low` to Clay `low`.

**Real quality signal — content pattern matching:**
```python
FAILURE_MARKERS = ['UNCHANGED', 'UNRESOLVED', 'NO UPDATE', 'SOURCE INVALID',
                   'CRITICAL SOURCE MISMATCH', 'Unable to determine']
def is_failed_research(row):
    strat_raw = row.get('strategic_initiatives_summary', '')
    try:
        top5 = json.loads(strat_raw).get('top_5_initiatives', '')
    except:
        top5 = strat_raw
    return any(m in top5 for m in FAILURE_MARKERS)
```
Expected failure rate: ~15% (name collisions + no indexed primary source).

## Known Failure Modes

| Failure type | Example | Fix |
|---|---|---|
| **Name collision** | `onit.com` → ONIT mortgage servicer; `getflex.com` → Flex Ltd electronics | Quote `co_name`; add industry disambiguator |
| **No indexed primary source** | `ziphq.com`, `edmentum.com` | Fall back to Crunchbase + LinkedIn |
| **Cross-company URL contamination** | `bloomreach.com` deep-read → W.R. Berkley report | Use `_extract_primary_source_url(company_domain=domain)` with domain validation |
| **Confidence drops Pass B→E** | Most rows | Expected — don't re-run. Use content quality check. |

## Adapting the 3 Search Angles

| Use case | Angle A | Angle B | Angle C |
|---|---|---|---|
| GTM strategy | 10-K / investor relations | New product launches | New customer segments |
| Signal detection (e.g. ClickHouse) | Tech stack / job postings | Engineering blog / GitHub | Conference talks / customer stories |
| Competitor research | Pricing / comparison pages | Customer reviews (G2, Capterra) | Exec interviews |
| Funding / private company | Crunchbase / funding rounds | Official newsroom | Founder blog / podcasts |

## `_extract_primary_source_url()` — Domain-Validated URL Scoring

**Two-pass approach: domain-match first, fallback to score-all.** Without domain validation, Exa results often contain aggregator URLs (BusinessWire, TechCrunch) belonging to a *different* company.

```python
def _extract_primary_source_url(exa_text, company_domain=''):
    root = re.sub(r'\.[a-z]{2,}$', '', company_domain.lower().split('.')[-2]
                  if company_domain.count('.') >= 1 else company_domain.lower())

    def _score(u):
        ul = u.lower()
        s = 0
        if 'ir.' in ul or '/investor' in ul:            s += 4
        if 'sec.gov' in ul or '10-k' in ul:             s += 3
        if 'annual' in ul or 'earnings' in ul:          s += 2
        if 'newsroom.' in ul or '/newsroom' in ul:      s += 3
        if 'press-release' in ul or '/press/' in ul:    s += 2
        if 'businesswire.com' in ul or 'prnewswire.com' in ul: s += 2
        if 'blog.' in ul or '/blog/' in ul:             s += 2
        if '/about' in ul or '/company' in ul:          s += 1
        if 'crunchbase.com' in ul or 'techcrunch.com' in ul: s += 1
        return s

    all_urls = _URL_RE.findall(exa_text)

    # Pass 1: only URLs on the target company's domain
    if root:
        matched = [((_score(u), u)) for u in all_urls
                   if root in re.sub(r'https?://', '', u).split('/')[0].lower()
                   and _score(u) > 0]
        if matched:
            return sorted(matched, reverse=True)[0][1]

    # Pass 2: score all URLs (no on-domain authoritative link found)
    scored = [(_score(u), u) for u in all_urls if _score(u) > 0]
    return sorted(scored, reverse=True)[0][1] if scored else None
```

Score all authoritative types (IR, newsroom, blog) — degrade gracefully for startups and private companies that have no IR site.
