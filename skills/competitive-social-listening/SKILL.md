---
name: competitive-social-listening
description: "Build a competitive intelligence dataset from LinkedIn engagement: find who's liking, commenting on, and sharing your competitors' posts. Scrapes company + senior employee posts (last N months), captures all reactions/comments with full engager profiles, filters by seniority (VP/CXO/Director/Sales/Marketing), and outputs a ranked engagement CSV + HTML dashboard. Triggers: competitive analysis, who engages with competitor posts, competitor LinkedIn followers, social listening, LinkedIn engagement analysis, who likes competitor posts."
---

> On completion, follow `gtm-meta-skill` Section 7 for proactive issue feedback and the session-sharing Yes/No consent step.

# Competitive Social Listening

Scrape LinkedIn post reactions/comments for a set of competitor companies and their senior employees. Capture full engager profiles, filter by seniority, and output:
- `all_engagements.csv` — every reaction/comment on every scraped post
- `senior_engagements.csv` — filtered to VP / CXO / Director / Sales / Marketing
- `dashboard.html` — self-contained HTML dashboard (shareable, no server needed)

## Prerequisites

- **Deepline CLI** + running backend (`deepline backend start`)
- **Apify** via Deepline (`harvestapi/linkedin-company-posts` actor)
- **Dropleads** via Deepline (for employee discovery)
- **Python 3** (standard library only — csv, json, re, os)

## Key Architecture Decisions (Validated)

| Decision | Why |
|---|---|
| **Dropleads for employees** (not Apify company-employees actor) | `harvestapi/linkedin-company-employees` returns empty results; dropleads is reliable |
| **Posts first, reactions separate** | Scraping reactions inline with posts causes CLI timeout (>90s); split into two passes |
| **Individual post URLs as `targetUrls`** | `harvestapi/linkedin-company-posts` accepts post URLs directly — 10 posts = ~15s run |
| **10 posts per batch, max 15 parallel** | >15 parallel Apify runs causes CLI timeout on 2-3 batches; run in groups |
| **Reduce `maxReactions` for high-engagement posts** (>300 reactions) | Top viral posts timeout at 100 reactions; use 50 or split separately |
| **Async `apify_run_actor`, not sync** | `apify_run_actor_sync` always times out for reaction scraping; use async + collect datasetId |
| **Parse file header before JSON** | deepline CLI prepends `Status: completed\nJob ID: ...\nResult:\n` — skip to first `{` or `[` |
| **Infer company from post URL handle** | `source_url` in post CSV is always empty; extract handle from post URL and match against all_urls.csv |

---

## Step 0: Collect Company Inputs

Accept from user:
- List of company LinkedIn URLs (e.g. `https://www.linkedin.com/company/vooma-inc/`)
- Time window (default: 3 months)
- Employee title filter (default: VP, CXO, Director, Sales, Marketing)
- Max employees per company (default: 10)

Create seed CSV at `$WORKDIR/companies.csv`:

```csv
company_name,company_linkedin,domain
Vooma,https://www.linkedin.com/company/vooma-inc/,vooma.com
GoAugment,https://www.linkedin.com/company/goaugment/,goaugment.com
TryPallet,https://www.linkedin.com/company/trypallet/,pallet.com
```

If domains are unknown, resolve them via Apollo:

```bash
deepline enrich \
  --input $WORKDIR/companies.csv \
  --output $WORKDIR/companies_enriched.csv \
  --with 'apollo_company=apollo_organization_search:{"q_organization_name":"{{company_name}}","per_page":3}'
```

Extract domain with `scripts/extract_company.js` (use `run_javascript:@$WORKDIR/scripts/extract_company.js`):
- Apollo returns `d.organizations` NOT `d.accounts` — critical
- Always use absolute path for JS files, not relative

```javascript
// scripts/extract_company.js
const q = (row["company_name"] || "").trim().toLowerCase();
let raw = row["apollo_company"];
if (typeof raw === "string") { try { raw = JSON.parse(raw); } catch(e) {} }
const d = raw?.data || {};
const orgs = d.organizations || d.accounts || [];  // organizations first!
const o = orgs.find(x => ((x?.name || "").trim().toLowerCase() === q)) || orgs[0] || null;
if (!o) return null;
return { domain: o.primary_domain || o.domain || null, name: o.name || null, linkedin: o.linkedin_url || null };
```

---

## Step 1: Employee Discovery

Use **dropleads** (not Apify company-employees — that actor returns empty results).

For each company domain, run:

```bash
deepline tools execute dropleads_search_people --payload '{
  "companyDomains": ["vooma.com"],
  "seniorities": ["c_suite", "vp", "director"],
  "departments": ["sales", "marketing"],
  "limit": 10
}'
```

**CRITICAL — dropleads filter format:**
- Use plain array: `"companyDomains": ["vooma.com"]` ✓
- NOT object format: `"companyDomains": {"include": ["vooma.com"]}` ✗

Collect LinkedIn profile URLs from results. Build `$WORKDIR/all_urls.csv`:

```csv
company,linkedin_url,description
Vooma,https://www.linkedin.com/company/vooma-inc/,Company Page
Vooma,http://www.linkedin.com/in/jesse-taylor,Jesse Taylor - VP Sales
GoAugment,https://www.linkedin.com/company/goaugment/,Company Page
...
```

This file is the source of truth for company → handle mapping used later.

---

## Step 2: Scrape Posts (No Reactions — Fast Pass)

Scrape all posts from all company + employee URLs in a single actor run. **Do NOT request reactions here** — too slow, causes timeout.

```bash
deepline tools execute apify_run_actor --payload '{
  "actorId": "harvestapi/linkedin-company-posts",
  "input": {
    "targetUrls": [
      "https://www.linkedin.com/company/vooma-inc/",
      "https://www.linkedin.com/company/goaugment/",
      "http://www.linkedin.com/in/jesse-taylor"
    ],
    "postedLimit": "3months",
    "maxPosts": 50,
    "scrapeReactions": false,
    "scrapeComments": false
  }
}' 2>&1
```

Wait for completion (check `status: SUCCEEDED`), capture `defaultDatasetId`.

Download dataset:
```bash
deepline tools execute apify_get_dataset_items --payload '{"datasetId": "DATASET_ID", "params": {"limit": 5000}}' > $WORKDIR/posts_raw.json
```

Parse with `scripts/parse_posts.py` → `$WORKDIR/posts_data.csv`:
- Fields: `post_url, author_name, author_linkedin, author_type, posted_at, content_preview, total_reactions, total_comments, num_shares`
- **Note**: `source_url` in raw output is always empty — use `all_urls.csv` for company mapping

Filter high-engagement posts (≥5 reactions OR ≥2 comments) → `$WORKDIR/high_engagement_posts.csv`. Sort by reactions desc.

---

## Step 3: Batch Post URL Scraping for Reactions/Comments

**KEY INSIGHT**: `harvestapi/linkedin-company-posts` accepts individual LinkedIn **post URLs** as `targetUrls`. 10 post URLs → ~15s runtime, well within timeout.

### 3.1 Build Batches

```python
# scripts/build_batches.py
import csv, json, os

BATCH_SIZE = 10
MAX_REACTIONS = 100   # reduce to 50 for posts with >300 total reactions
MAX_COMMENTS = 50
WORKDIR = os.environ.get("WORKDIR", "/tmp/comp_analysis")

with open(f"{WORKDIR}/high_engagement_posts.csv") as f:
    posts = list(csv.DictReader(f))

# Separate high-volume viral posts (likely timeout) from normal posts
normal = [p for p in posts if int(p.get("total_reactions") or 0) <= 300]
viral  = [p for p in posts if int(p.get("total_reactions") or 0) > 300]

batches = []
for i in range(0, len(normal), BATCH_SIZE):
    urls = [p["post_url"] for p in normal[i:i+BATCH_SIZE] if p.get("post_url")]
    if urls:
        batches.append({"urls": urls, "maxReactions": MAX_REACTIONS, "maxComments": MAX_COMMENTS})

# Viral posts: smaller batches, reduced limits
for i in range(0, len(viral), 5):
    urls = [p["post_url"] for p in viral[i:i+5] if p.get("post_url")]
    if urls:
        batches.append({"urls": urls, "maxReactions": 50, "maxComments": 30})

for idx, batch in enumerate(batches):
    config = {
        "actorId": "harvestapi/linkedin-company-posts",
        "input": {
            "targetUrls": batch["urls"],
            "scrapeReactions": True,
            "maxReactions": batch["maxReactions"],
            "scrapeComments": True,
            "maxComments": batch["maxComments"]
        }
    }
    with open(f"{WORKDIR}/batch_{idx:02d}.json", "w") as f:
        json.dump(config, f)

print(f"Created {len(batches)} batches ({len(normal)} normal posts, {len(viral)} viral posts)")
```

### 3.2 Run Batches in Background (Max 15 Parallel)

```bash
# Run in groups of 15 to avoid timeout cascade
for i in $(seq -w 0 14); do
  deepline tools execute apify_run_actor --payload "$(cat $WORKDIR/batch_${i}.json)" > $WORKDIR/run_${i}.txt 2>&1 &
done
wait
echo "Group 1 done"

# Collect dataset IDs
for i in $(seq -w 0 14); do
  grep -o 'datasetId.*' $WORKDIR/run_${i}.txt | grep -o '"[A-Za-z0-9]*"' | head -1 | tr -d '"'
done
```

**If a batch times out** (`Failed to reach API: timeout`): re-run that batch solo. The Apify run likely completed on the server — just the CLI wait timed out. Re-running triggers a fresh run safely.

### 3.3 Download All Datasets

```bash
for DATASET_ID in $DATASET_IDS; do
  deepline tools execute apify_get_dataset_items --payload "{\"datasetId\": \"$DATASET_ID\", \"params\": {\"limit\": 2000}}" > $WORKDIR/ds_${DATASET_ID}.json
done
```

---

## Step 4: Parse and Filter Engagements

Use `scripts/parse_engagements.py`:

```python
# scripts/parse_engagements.py
import json, re, csv, os
from collections import Counter

WORKDIR = os.environ.get("WORKDIR", "/tmp/comp_analysis")

def parse_file(path):
    """deepline CLI prepends a status header — skip to first JSON character."""
    with open(path) as f:
        content = f.read()
    m = re.search(r'(\{|\[)', content)
    if not m:
        return []
    try:
        data = json.loads(content[m.start():])
        if isinstance(data, dict):
            return data.get('data', data.get('items', []))
        return data
    except:
        return []

def extract_handle(url):
    """Extract LinkedIn handle from any LinkedIn URL format."""
    url = url.rstrip('/')
    m = re.search(r'/(?:in|company|pub)/([^/?#]+)', url)
    if m:
        return m.group(1).lower()
    # For post URLs: /posts/handlename_...
    m = re.search(r'/posts/([^_]+)_', url)
    if m:
        return m.group(1).lower()
    return None

SENIOR_PATTERNS = {
    'C-Suite/Exec': [r'\bceo\b', r'\bcto\b', r'\bcfo\b', r'\bcoo\b', r'\bcmo\b', r'\bcro\b',
                     r'\bcpo\b', r'\bciso\b', r'\bchief\b', r'\bfounder\b', r'\bco-founder\b',
                     r'\bcofounder\b', r'\bpresident\b', r'\bowner\b', r'\bpartner\b', r'\bprincipal\b'],
    'VP':           [r'\bvp\b', r'\bvice president\b', r'\bsvp\b', r'\bevp\b', r'\brvp\b', r'\bgvp\b'],
    'Director':     [r'\bdirector\b'],
    'Sales':        [r'\bsales\b', r'\baccount executive\b', r'\baccount manager\b',
                     r'\bbusiness development\b', r'\bbdr\b', r'\bsdr\b', r'\brevenue\b'],
    'Marketing':    [r'\bmarketing\b', r'\bgrowth\b', r'\bdemand gen\b', r'\bcontent\b', r'\bbrand\b'],
}

def classify_title(position):
    if not position:
        return None
    p = position.lower()
    for category, patterns in SENIOR_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, p):
                return category
    return None

# Load company → handle mapping
handle_to_company = {}
with open(f"{WORKDIR}/all_urls.csv") as f:
    for row in csv.DictReader(f):
        h = extract_handle(row['linkedin_url'])
        if h:
            handle_to_company[h] = row['company']

# Load post metadata
posts_data = {}
with open(f"{WORKDIR}/posts_data.csv") as f:
    for row in csv.DictReader(f):
        if row.get('post_url'):
            posts_data[row['post_url']] = row

# Load all engagement items from all dataset files
all_items = []
for fname in os.listdir(WORKDIR):
    if fname.startswith('ds_') and fname.endswith('.json'):
        all_items.extend(parse_file(os.path.join(WORKDIR, fname)))

print(f"Raw engagements: {len(all_items)}")

# Build rows with dedup
output_rows = []
seen = set()

for item in all_items:
    actor = item.get('actor', {})
    position = actor.get('position', '') or ''
    post_url = item.get('query', {}).get('post', '')
    actor_id = actor.get('id', '')
    eng_type = item.get('type', '')

    dedup_key = (post_url, actor_id, eng_type)
    if dedup_key in seen:
        continue
    seen.add(dedup_key)

    category = classify_title(position)
    post_meta = posts_data.get(post_url, {})
    handle = extract_handle(post_url)
    company = handle_to_company.get(handle, '') if handle else ''

    posted_at_raw = post_meta.get('posted_at', '')
    posted_at = ''
    if posted_at_raw:
        d = re.search(r"'date': '([^']+)'", posted_at_raw)
        posted_at = d.group(1)[:10] if d else posted_at_raw[:10]

    row = {
        'company': company,
        'post_url': post_url,
        'post_author': post_meta.get('author_name', ''),
        'post_author_linkedin': post_meta.get('author_linkedin', ''),
        'post_date': posted_at,
        'post_total_reactions': post_meta.get('total_reactions', ''),
        'post_total_comments': post_meta.get('total_comments', ''),
        'post_content_preview': (post_meta.get('content_preview', '') or '')[:200],
        'engagement_type': eng_type,
        'reaction_type': item.get('reactionType', '') if eng_type == 'reaction' else '',
        'comment_text': (item.get('commentary', '') or '') if eng_type == 'comment' else '',
        'comment_url': item.get('linkedinUrl', '') if eng_type == 'comment' else '',
        'engagement_date': (item.get('createdAt', '') or '')[:10],
        'engager_name': actor.get('name', ''),
        'engager_linkedin_url': actor.get('linkedinUrl', ''),
        'engager_position': position,
        'engager_title_category': category or '',
        'is_senior': 'yes' if category else 'no',
        'engager_picture_url': actor.get('pictureUrl', ''),
    }
    output_rows.append(row)

fieldnames = list(output_rows[0].keys()) if output_rows else []
senior = [r for r in output_rows if r['is_senior'] == 'yes']

# Save BOTH outputs
with open(f"{WORKDIR}/all_engagements.csv", 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(output_rows)

with open(f"{WORKDIR}/senior_engagements.csv", 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(senior)

print(f"all_engagements.csv: {len(output_rows)} rows")
print(f"senior_engagements.csv: {len(senior)} rows")
print("By category:", dict(Counter(r['engager_title_category'] for r in senior)))
print("By company:", dict(Counter(r['company'] for r in senior if r['company'])))
```

---

## Step 5: Build Dashboard

Run `scripts/build_dashboard.py` — reads `senior_engagements.csv` and outputs `dashboard.html` (self-contained, no server needed, Chart.js via CDN).

Dashboard sections:
- **Stat cards**: total engagements, unique engagers, posts covered, per-company counts
- **Bar chart**: engagements by company
- **Donut chart**: title category mix
- **Bar chart**: reaction type breakdown (LIKE / PRAISE / EMPATHY / INTEREST / APPRECIATION)
- **Line chart**: monthly trend
- **Stacked bar**: title mix per company
- **Top posts table**: ranked by senior engagement count, with company badge + LinkedIn link
- **Top engager cards**: profile photos, position, count, companies engaged
- **Top 20 engager detail table**: highlights ⚡ multi-company engagers (highest-signal prospects)

Package for sharing:
```bash
cd $WORKDIR && zip -j competitive_analysis_dashboard.zip dashboard.html all_engagements.csv senior_engagements.csv
```

---

## Step 6: Outputs

| File | Description |
|---|---|
| `all_engagements.csv` | Every reaction/comment across all posts, all engagers |
| `senior_engagements.csv` | Filtered to VP/CXO/Director/Sales/Marketing only |
| `dashboard.html` | Self-contained HTML dashboard (open in browser, no server) |
| `competitive_analysis_dashboard.zip` | All three files zipped for sharing |

---

## Common Pitfalls (from Production Run)

| Issue | Symptom | Fix |
|---|---|---|
| Apollo returns `organizations` not `accounts` | `company_info` null for all rows | Use `d.organizations \|\| d.accounts` (organizations first) |
| JS file path relative | `Failed to read --with payload file` | Always use absolute path: `run_javascript:@/tmp/.../script.js` |
| Dropleads wrong filter format | 0 employees returned | Use plain array `"companyDomains": ["domain.com"]`, not `{"include": [...]}` |
| `harvestapi/linkedin-company-employees` empty | 0 results for all companies | Switch to `dropleads_search_people` by domain |
| `apify_run_actor_sync` with reactions | `exit code 4` timeout | Use async `apify_run_actor`, capture `defaultDatasetId`, download separately |
| >15 parallel Apify runs | 2-3 batches timeout | Run in groups of 10-15 max |
| Viral posts (>300 reactions) | Consistent timeout | Separate batch with `maxReactions: 50`, or skip |
| deepline CLI output has header | `JSONDecodeError: Expecting value` | Skip to first `{` or `[` with `re.search(r'(\{|\[)', content)` |
| `source_url` empty in posts CSV | Can't map posts to companies | Extract handle from post URL, match against `all_urls.csv` |
| `deepline csv render start` wrong | `Unknown csv command` | Command is `deepline csv render start --csv FILE --open` |
| CSV field size limit (131072) | `_csv.Error: field larger than field limit` | Don't pipe large Apify JSON through deepline enrich; use `apify_get_dataset_items` directly |

---

## Cost Estimation

Run this before starting to estimate total spend:

```python
def estimate_cost(
    n_companies,
    employees_per_company=10,
    posts_per_url=15,           # avg posts per company/employee URL
    pct_high_engagement=0.78,   # % of posts with ≥5 reactions (validated: 209/268 = 78%)
    reactions_per_post=100,     # maxReactions cap
    comments_per_post=50,       # maxComments cap
    deepline_credits_per_employee=5,  # dropleads cost
):
    total_urls = n_companies + (n_companies * employees_per_company)
    total_posts = total_urls * posts_per_url
    high_eng_posts = int(total_posts * pct_high_engagement)

    # Apify pricing: $0.002 per dataset item (PRICE_PER_DATASET_ITEM)
    post_scrape_cost = total_posts * 0.002
    reaction_items = high_eng_posts * (reactions_per_post + comments_per_post)
    reaction_cost = reaction_items * 0.002

    # Deepline credits
    dl_credits = n_companies * employees_per_company * deepline_credits_per_employee

    total_apify = post_scrape_cost + reaction_cost
    print(f"URLs to scrape: {total_urls}")
    print(f"Est. posts: {total_posts} total, {high_eng_posts} high-engagement")
    print(f"Apify post scrape: ${post_scrape_cost:.2f}")
    print(f"Apify reaction scrape: ${reaction_cost:.2f}")
    print(f"Total Apify: ${total_apify:.2f}")
    print(f"Deepline credits (dropleads): ~{dl_credits}")
    print(f"Batches needed: {high_eng_posts // 10 + 1}")

# Example: 3 companies, 10 employees each
estimate_cost(n_companies=3)
# → URLs: 33, Posts: ~495, High-engagement: ~386
# → Apify: ~$0.99 post + ~$30.88 reactions = ~$31.87 total
# → Deepline: ~150 credits
```

**Validated actuals from 3-company run:**
- 25 URLs, 268 posts scraped, 209 high-engagement → 21 batches
- ~8,855 total engagement items downloaded
- Apify spend: ~$2-4 (post scrape) + ~$18-25 (reactions) = **~$20-30 total**
- Deepline credits: ~75 (dropleads for 22 employees)

Always run `deepline billing balance` before starting. Pilot one batch before full run.
