---
name: competitive-social-listening
description: "Build a competitive intelligence dataset from LinkedIn engagement: find who's liking, commenting on, and sharing your competitors' posts. Scrapes company + senior employee posts (last N months), captures all reactions/comments with full engager profiles, filters by seniority (VP/CXO/Director/Sales/Marketing), and outputs a ranked engagement CSV + HTML dashboard. Triggers: competitive analysis, who engages with competitor posts, competitor LinkedIn followers, social listening, LinkedIn engagement analysis, who likes competitor posts."
---

> On completion, follow `gtm-meta-skill` Section 7 for proactive issue feedback and the session-sharing Yes/No consent step.

# Competitive Social Listening

Given a list of LinkedIn company URLs + time window, produces:
- `all_engagements.csv` — every reaction/comment, full engager profile
- `senior_engagements.csv` — filtered to VP / CXO / Director / Sales / Marketing
- `dashboard.html` — self-contained HTML dashboard (open in browser, shareable)
- `competitive_analysis.zip` — all three packaged for sharing

**Use the e2e script for full runs:**
```bash
python ~/.claude/skills/competitive-social-listening/scripts/competitive_social_listening.py \
  --companies "Acme:https://www.linkedin.com/company/acme/:acme.com" \
              "Rival:https://www.linkedin.com/company/rival/:rival.com" \
  --output /tmp/comp_run --months 3 --employees 10

# Test mode (1 company, 2 employees, 5 posts):
python competitive_social_listening.py --test --output /tmp/comp_test
```

Or follow the manual steps below if you need to debug or resume a partial run.

---

## Pipeline Architecture

```
Input: [company LinkedIn URLs + time window]
         │
         ├─── ⚡ PARALLEL ──────────────────────────────────────┐
         │    Phase A: Employee discovery (dropleads)           │
         │    → employee LinkedIn URLs per company              │
         │                                                       │
         │    Phase B: Company page posts (harvestapi)          │
         │    → starts immediately, no need to wait for A       │
         └──────────────────────────────────────────────────────┘
         │
         ▼
    all_urls.csv (company pages + employee profiles)
         │
         ▼
    Full post scrape → posts_data.csv
    [harvestapi/linkedin-company-posts, no reactions, fast]
         │
         ▼
    Filter high-engagement posts (≥5 reactions or ≥2 comments)
         │
         ├─── ⚡ PARALLEL (max 12 concurrent) ────────────────┐
         │    10-post batches → async apify_run_actor         │
         │    viral posts (>300 reactions) → separate batch   │
         │    → datasetIds collected as_completed()           │
         └────────────────────────────────────────────────────┘
         │
         ▼
    Download all datasets → parse + deduplicate
         │
         ▼
    all_engagements.csv + senior_engagements.csv + dashboard.html
```

---

## Prerequisites

```bash
deepline backend start   # always required before any deepline tool execute
deepline billing balance  # check credits before starting
```

Set your working directory:
```bash
export WORKDIR=/tmp/comp_$(date +%Y%m%d)
mkdir -p $WORKDIR
```

---

## Step 1: Collect Inputs → `companies.csv`

Accept from user:
- List of company LinkedIn URLs
- Time window (default: 3 months)
- Max employees per company (default: 10)
- Seniority filter (default: VP, CXO, Director, Sales, Marketing)

Create seed file:
```csv
company_name,company_linkedin,domain
Acme,https://www.linkedin.com/company/acme/,acme.com
Rival,https://www.linkedin.com/company/rival/,rival.com
```

**If domain is unknown**, resolve via Apollo (optional — dropleads works without domain if you have LinkedIn URL):
```bash
deepline tools execute apollo_organization_search --payload \
  '{"q_organization_name": "Acme Corp", "per_page": 1}'
# Look for .data.organizations[0].primary_domain
# Apollo returns "organizations" NOT "accounts" — critical
```

---

## Step 2: Employee Discovery → `all_urls.csv`

**Provider: dropleads** (not `harvestapi/linkedin-company-employees` — that actor returns empty)

Run for each company (fire all companies in parallel — don't wait for one before starting the next):

```bash
deepline tools execute dropleads_search_people --payload '{
  "filters.companyDomains": ["acme.com"],
  "filters.seniority": ["C-Level", "VP", "Director"],
  "filters.departments": ["Sales", "Marketing"],
  "pagination.limit": 10
}'
```

> ⚠️ **Field names use dot notation**: `filters.companyDomains`, NOT `companyDomains`. `filters.seniority`, NOT `seniorities`. `pagination.limit`, NOT `limit`.
>
> ⚠️ **Response is raw text with a CSV path**, not JSON:
> ```
> /tmp/output_1772593757336.csv (8 rows)
> columns: ["id", "fullName", "title", "linkedinUrl", ...]
> ```
> Extract the CSV path with `re.search(r'(/tmp/\S+\.csv)', output)` and read it with Python's `csv.DictReader`.

Build `$WORKDIR/all_urls.csv`:
```csv
company,linkedin_url,description
Acme,https://www.linkedin.com/company/acme/,Company Page
Acme,https://www.linkedin.com/in/jane-smith,Jane Smith - VP Sales
Rival,https://www.linkedin.com/company/rival/,Company Page
...
```

This file is the **source of truth** for company → handle mapping used in Step 5.

---

## Step 3: Scrape Posts (No Reactions) → `posts_data.csv`

One actor run for all URLs. **Do not request reactions here** — scraping reactions inline causes CLI timeout (actor runtime >90s).

```bash
deepline tools execute apify_run_actor --payload '{
  "actorId": "harvestapi/linkedin-company-posts",
  "input": {
    "targetUrls": [
      "https://www.linkedin.com/company/acme/",
      "https://www.linkedin.com/in/jane-smith"
    ],
    "postedLimit": "3months",
    "maxPosts": 50,
    "scrapeReactions": false,
    "scrapeComments": false
  }
}'
```

> ⚠️ **`postedLimit` valid values**: `"month"`, `"3months"`, `"6months"`, `"year"`. NOT `"1month"` or integers.

Wait for `status: SUCCEEDED`, capture `defaultDatasetId`. Download:
```bash
deepline tools execute apify_get_dataset_items \
  --payload '{"datasetId": "DATASET_ID", "params": {"limit": 5000}}' \
  > $WORKDIR/posts_raw.json
```

Parse the response (deepline CLI prepends a status header — skip to first `{` or `[`):
```python
import re, json
with open(f"{WORKDIR}/posts_raw.json") as f:
    content = f.read()
m = re.search(r'(\{|\[)', content)
items = json.loads(content[m.start():])
```

**Actual field names** in Apify response items:
| Field | Actual key | Common mistake |
|---|---|---|
| Post URL | `linkedinUrl` | `postUrl` ✗ |
| Post text | `content` | `text` ✗ |
| Author name | `author["name"]` (dict) | `authorName` ✗ |
| Reactions | `engagement["likes"]` (dict) | `totalReactions` ✗ |
| Comments | `engagement["comments"]` (dict) | `totalComments` ✗ |
| Post date | `postedAt` | `posted_at` ✗ |

> ⚠️ **`source_url` is always empty** in post results — never use it for company mapping. Instead: extract the LinkedIn handle from `linkedinUrl` and look it up in `all_urls.csv`.

```python
def extract_handle(url):
    url = url.rstrip("/")
    m = re.search(r"/(?:in|company|pub)/([^/?#]+)", url)
    if m: return m.group(1).lower()
    m = re.search(r"/posts/([^_]+)_", url)   # handle from post URLs
    if m: return m.group(1).lower()
    return None
```

Save as `posts_data.csv`. Filter high-engagement posts (≥5 reactions **or** ≥2 comments) → `high_engagement_posts.csv`.

---

## Step 4: Batch Reaction Scraping

### 4.1 Build Batches

**Key insight**: `harvestapi/linkedin-company-posts` accepts individual **post URLs** as `targetUrls`. 10 post URLs ≈ 15s run — well within CLI timeout.

```python
# Separate viral posts before batching
normal = [p for p in posts if p["total_reactions"] <= 300]
viral  = [p for p in posts if p["total_reactions"] > 300]

# Normal posts: 10 per batch, 100 max reactions
batches = [normal[i:i+10] for i in range(0, len(normal), 10)]

# Viral posts: 5 per batch, 50 max reactions (prevents timeout)
viral_batches = [viral[i:i+5] for i in range(0, len(viral), 5)]
```

Each batch config:
```json
{
  "actorId": "harvestapi/linkedin-company-posts",
  "input": {
    "targetUrls": ["https://www.linkedin.com/posts/acme_..."],
    "scrapeReactions": true,
    "maxReactions": 100,
    "scrapeComments": true,
    "maxComments": 50
  }
}
```

### 4.2 Run Batches — Async, Max 12 Parallel

**Always use `apify_run_actor` (async), never `apify_run_actor_sync`** — reaction scraping exceeds the ~90s CLI timeout.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_batch(batch_config, idx):
    raw = subprocess.run(
        ["deepline", "tools", "execute", "apify_run_actor",
         "--payload", json.dumps(batch_config)],
        capture_output=True, text=True, timeout=180
    )
    output = raw.stdout + raw.stderr
    # Extract datasetId from output
    m = re.search(r'"defaultDatasetId"\s*:\s*"([A-Za-z0-9]+)"', output)
    return m.group(1) if m else None

# Run in groups of 12 — >15 concurrent causes 2-3 timeouts
with ThreadPoolExecutor(max_workers=12) as ex:
    futures = {ex.submit(run_batch, b, i): i for i, b in enumerate(batches)}
    dataset_ids = []
    for future in as_completed(futures):   # process as each finishes, don't wait for all
        ds_id = future.result()
        if ds_id:
            dataset_ids.append(ds_id)
```

> ⚠️ **If a batch times out**: the Apify run likely completed on the server — only the CLI wait timed out. Re-run that batch alone (not in parallel with others). It will finish in ~15s on retry.

### 4.3 Download All Datasets

Fire dataset downloads in parallel (all independent):
```python
def download_dataset(ds_id):
    result = subprocess.run(
        ["deepline", "tools", "execute", "apify_get_dataset_items",
         "--payload", json.dumps({"datasetId": ds_id, "params": {"limit": 2000}})],
        capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr
    m = re.search(r'(\{|\[)', output)
    if not m: return []
    data = json.loads(output[m.start():])
    if isinstance(data, dict): return data.get("data", data.get("items", []))
    return data if isinstance(data, list) else []

# Download all in parallel
with ThreadPoolExecutor(max_workers=10) as ex:
    all_items = []
    for items in ex.map(download_dataset, dataset_ids):
        all_items.extend(items)
```

---

## Step 5: Parse Engagements → CSVs

Deduplicate on `(post_url, actor_id, engagement_type)`. Classify seniority from position title:

```python
SENIOR_PATTERNS = {
    "C-Suite/Exec": [r"\bceo\b", r"\bcto\b", r"\bcfo\b", r"\bcoo\b", r"\bcmo\b", r"\bcro\b",
                     r"\bcpo\b", r"\bciso\b", r"\bchief\b", r"\bfounder\b", r"\bco-founder\b",
                     r"\bpresident\b", r"\bowner\b", r"\bpartner\b", r"\bprincipal\b"],
    "VP":           [r"\bvp\b", r"\bvice president\b", r"\bsvp\b", r"\bevp\b", r"\brvp\b"],
    "Director":     [r"\bdirector\b"],
    "Sales":        [r"\bsales\b", r"\baccount executive\b", r"\bbdr\b", r"\bsdr\b", r"\brevenue\b"],
    "Marketing":    [r"\bmarketing\b", r"\bgrowth\b", r"\bdemand gen\b", r"\bcontent\b", r"\bbrand\b"],
}
```

Output columns (both CSVs):
`company, post_url, post_author, post_date, post_total_reactions, post_total_comments, post_content_preview, engagement_type, reaction_type, comment_text, engagement_date, engager_name, engager_linkedin_url, engager_position, engager_title_category, is_senior, engager_picture_url`

---

## Step 6: Dashboard + Package

Run `build_dashboard.py` → `dashboard.html` (Chart.js via CDN, self-contained, no server needed):
- Stat cards: senior engagements, all engagements, unique engagers, reactions, comments
- Bar: by company | Donut: title category mix | Bar: reaction types | Line: monthly trend
- Top posts table (ranked by senior engagement count)
- Top 20 engager table — ⚡ highlights multi-company engagers (highest-signal prospects)

> ⚠️ **f-string + JS braces conflict**: if building HTML template in Python, use a string placeholder (`__DATA_JSON__`) and `.replace()` instead of an f-string. Minified JS `{{` inside an f-string causes `SyntaxError: single '}' is not allowed`.

```bash
cd $WORKDIR && zip -j competitive_analysis.zip dashboard.html all_engagements.csv senior_engagements.csv
```

---

## Speed Architecture

These are the proven parallelism wins for this workflow. Each reduces wall-clock time without adding complexity.

### 1. Fan-out employee discovery
Fire dropleads for all companies simultaneously (ThreadPoolExecutor), not one-by-one. 3 companies = same time as 1.

### 2. Overlap employee discovery with company page post scraping
Company-page post scraping doesn't need employee URLs. Start the first actor run for company pages the moment you have them — don't wait for dropleads to finish.

### 3. `as_completed()` for reaction batches
Don't wait for an entire group to finish before starting dataset downloads. Start downloading the first completed batch immediately while others are still running.

### 4. Parallel dataset downloads
All `apify_get_dataset_items` calls are independent. Run them all concurrently (max 10 parallel — Apify rate limit).

### 5. Progressive CSV writing
Append engagement rows to CSVs as each dataset is parsed rather than holding all data in memory. Reduces peak memory for large runs (>50k rows).

### 6. Speculative file reads (Claude Code pattern)
When running in an agent loop: fire all tool calls that are independent in a single message. Don't wait for file A before reading file B if they're not dependent.

### Why best-in-class agents are faster

| Technique | Description | Applied here |
|---|---|---|
| **Parallel tool dispatch** | Fire all independent API calls in one message/thread | Fan-out dropleads + Apify simultaneously |
| **PTC (Programmatic Tool Calling)** | Write code to loop over tool calls, avoiding model round-trips | E2E script replaces 50+ agent turns |
| **Speculative prefetch** | Read files you'll likely need before confirmed you need them | `all_urls.csv` written early, reused later |
| **Sub-agent isolation** | Spawn agents for independent work streams with no shared context | ThreadPoolExecutor batches = sub-agent equivalent |
| **Minimal context passing** | Pass IDs and file paths between steps, not data blobs | Only `datasetId` strings passed between phases |
| **Fail fast with known errors** | Encode all known failure modes as input validation | `postedLimit` map, viral batch detection, header-skip parser |

---

## Pitfalls Reference

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | 0 employees returned | Wrong dropleads field names | Use `filters.companyDomains`, `filters.seniority`, `pagination.limit` (dot notation) |
| 2 | dropleads JSON parse fails | Response is raw text + CSV path, not JSON | Use `deepline_raw()` + `re.search(r'(/tmp/\S+\.csv)', output)` |
| 3 | 0 unique posts parsed | `postUrl` field doesn't exist | Use `linkedinUrl`; author is `author["name"]` (dict); engagement is `engagement["likes"]` |
| 4 | Posts actor `422` error | Invalid `postedLimit` value | Use `"month"`, `"3months"`, `"6months"`, `"year"` only |
| 5 | Employee actor returns empty | Wrong actor | `harvestapi/linkedin-company-employees` is broken; use `dropleads_search_people` |
| 6 | Reaction batch `exit code 4` | `apify_run_actor_sync` timeout | Use async `apify_run_actor`, capture `defaultDatasetId`, download separately |
| 7 | 2-3 batches timeout when >15 parallel | Apify server-side throttle | Max 12 parallel; retry timed-out batches solo |
| 8 | Viral post batch always times out | >300-reaction posts + `maxReactions:100` | Separate batch: `maxReactions: 50`, batch_size 5 |
| 9 | `JSONDecodeError: Expecting value` on ds files | deepline CLI prepends status header | `re.search(r'(\{|\[)', content)` to find first JSON char |
| 10 | Can't map posts to companies | `source_url` always empty in Apify output | Extract handle from `linkedinUrl`, match against `all_urls.csv` |
| 11 | `SyntaxError: single '}' not allowed` | JS braces in Python f-string | Use `__DATA_JSON__` placeholder + `.replace()` |
| 12 | `_csv.Error: field larger than field limit` | Large JSON in deepline enrich CSV cells | Don't route Apify data through deepline enrich; use `apify_get_dataset_items` directly |

---

## Cost Estimation

Run before starting:

```python
def estimate_cost(n_companies, employees_per_company=10, months=3):
    urls = n_companies * (1 + employees_per_company)
    posts = urls * 15                           # ~15 posts/URL avg
    high_eng = int(posts * 0.78)                # 78% pass engagement filter (validated)
    batches = (high_eng // 10) + 1

    # Apify: ~$0.002 per dataset item
    post_items = posts
    reaction_items = high_eng * 150             # reactions + comments per post
    apify_usd = (post_items + reaction_items) * 0.002

    # Dropleads: ~5 Deepline credits per employee
    dl_credits = n_companies * employees_per_company * 5

    print(f"URLs: {urls} | Posts: ~{posts} | High-eng: ~{high_eng} | Batches: {batches}")
    print(f"Apify: ~${apify_usd:.0f} | Deepline credits: ~{dl_credits}")
    return apify_usd, dl_credits

estimate_cost(3)   # 3 companies, 10 employees each
# → Apify: ~$23 | Deepline credits: ~150
```

**Validated actuals (3-company run, Vooma/GoAugment/TryPallet):**
- 25 URLs → 268 posts → 209 high-engagement → 21 batches
- 8,855 total engagements, 4,131 senior (49%)
- Apify: ~$20-30 | Deepline credits: ~75-150

Always run `deepline billing balance` first. Pilot one batch before committing to full run.
