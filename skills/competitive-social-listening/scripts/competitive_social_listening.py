#!/usr/bin/env python3
"""
competitive_social_listening.py
End-to-end LinkedIn competitive social listening pipeline.

Usage:
    python competitive_social_listening.py \\
        --companies "Vooma:https://www.linkedin.com/company/vooma-inc/:vooma.com" \\
                    "GoAugment:https://www.linkedin.com/company/goaugment/:goaugment.com" \\
        --output /tmp/comp_run \\
        --months 3 \\
        --employees 10

    # Test mode (1 company, 2 employees, 5 posts, 10 reactions):
    python competitive_social_listening.py --test --output /tmp/comp_test
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BATCH_SIZE = 10           # post URLs per Apify reaction-scraping run
MAX_PARALLEL_BATCHES = 12 # max concurrent Apify runs (stay under throttle)
REACTION_SCRAPE_TIMEOUT = 180  # seconds per batch subprocess call
POST_SCRAPE_TIMEOUT = 300      # seconds for initial post scrape

SENIOR_PATTERNS = {
    "C-Suite/Exec": [
        r"\bceo\b", r"\bcto\b", r"\bcfo\b", r"\bcoo\b", r"\bcmo\b",
        r"\bcro\b", r"\bcpo\b", r"\bciso\b", r"\bchief\b", r"\bfounder\b",
        r"\bco-founder\b", r"\bcofounder\b", r"\bpresident\b",
        r"\bowner\b", r"\bpartner\b", r"\bprincipal\b",
    ],
    "VP":       [r"\bvp\b", r"\bvice president\b", r"\bsvp\b", r"\bevp\b", r"\brvp\b", r"\bgvp\b"],
    "Director": [r"\bdirector\b"],
    "Sales":    [r"\bsales\b", r"\baccount executive\b", r"\baccount manager\b",
                 r"\bbusiness development\b", r"\bbdr\b", r"\bsdr\b", r"\brevenue\b"],
    "Marketing":[r"\bmarketing\b", r"\bgrowth\b", r"\bdemand gen\b", r"\bcontent\b", r"\bbrand\b"],
}


# ---------------------------------------------------------------------------
# Deepline CLI wrapper
# ---------------------------------------------------------------------------

def deepline(tool_id: str, payload: dict, timeout: int = 120) -> dict | None:
    """
    Run: deepline tools execute <tool_id> --payload '<json>'
    Returns parsed JSON result dict, or None on failure.

    deepline CLI prepends a status header before JSON — we skip to the first { or [.
    """
    cmd = ["deepline", "tools", "execute", tool_id, "--payload", json.dumps(payload)]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout + result.stderr
        m = re.search(r"(\{|\[)", output)
        if not m:
            print(f"  [WARN] {tool_id}: no JSON in output. Snippet: {output[:300]}")
            return None
        return json.loads(output[m.start():])
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {tool_id} timed out after {timeout}s")
        return None
    except json.JSONDecodeError as e:
        print(f"  [JSON ERROR] {tool_id}: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] {tool_id}: {e}")
        return None


def deepline_raw(tool_id: str, payload: dict, timeout: int = 120) -> str:
    """Like deepline() but returns raw stdout+stderr text (for async run_id extraction)."""
    cmd = ["deepline", "tools", "execute", tool_id, "--payload", json.dumps(payload)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return str(e)


def extract_dataset_id(text: str) -> str | None:
    """Extract defaultDatasetId from deepline apify_run_actor output."""
    # From JSON body
    m = re.search(r'"defaultDatasetId"\s*:\s*"([A-Za-z0-9]+)"', text)
    if m:
        return m.group(1)
    # From suggested next command
    m = re.search(r'datasetId.*?"([A-Za-z0-9]{15,})"', text)
    if m:
        return m.group(1)
    return None


def extract_run_id(text: str) -> str | None:
    """Extract runId from deepline apify_run_actor output."""
    m = re.search(r'"runId"\s*:\s*"([A-Za-z0-9]+)"', text)
    if m:
        return m.group(1)
    m = re.search(r'runId.*?"([A-Za-z0-9]{15,})"', text)
    if m:
        return m.group(1)
    return None


def parse_deepline_file(path: str) -> list:
    """Parse a JSON file written by deepline CLI (has status header before JSON)."""
    with open(path) as f:
        content = f.read()
    m = re.search(r"(\{|\[)", content)
    if not m:
        return []
    try:
        data = json.loads(content[m.start():])
        if isinstance(data, dict):
            return data.get("data", data.get("items", []))
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  [PARSE ERROR] {path}: {e}")
        return []


# ---------------------------------------------------------------------------
# Step 1: Employee discovery (dropleads)
# ---------------------------------------------------------------------------

def discover_employees(company: str, domain: str, limit: int = 10) -> list[dict]:
    """
    Find senior employees at a company domain via dropleads.
    Returns list of {name, linkedin_url, position, company}.

    IMPORTANT: dropleads returns raw text with a CSV file path — not JSON.
    Output format: "/tmp/output_XXXXXXX.csv (N rows)\ncolumns: [...]\npreview: ..."
    """
    print(f"\n  [employees] Searching dropleads for {company} ({domain})...")
    payload = {
        "filters.companyDomains": [domain],
        "filters.seniority": ["C-Level", "VP", "Director"],
        "filters.departments": ["Sales", "Marketing"],
        "pagination.limit": limit,
    }
    raw = deepline_raw("dropleads_search_people", payload, timeout=60)

    # dropleads returns text like "/tmp/output_1772593757336.csv (1 rows)\ncolumns: [...]"
    csv_match = re.search(r'(/tmp/\S+\.csv)', raw)
    if not csv_match:
        print(f"  [employees] No CSV path in dropleads response for {company}. Snippet: {raw[:300]}")
        return []

    csv_path = csv_match.group(1)
    try:
        with open(csv_path) as f:
            people = list(csv.DictReader(f))
    except Exception as e:
        print(f"  [employees] Could not read {csv_path}: {e}")
        return []

    rows = []
    for p in people[:limit]:
        li = (p.get("linkedinUrl") or p.get("linkedin_url") or "").strip()
        if li:
            rows.append({
                "company": company,
                "linkedin_url": li,
                "description": f"{p.get('fullName', p.get('full_name', p.get('name', '')))} - {p.get('title', p.get('job_title', ''))}",
            })

    print(f"  [employees] Found {len(rows)} employees for {company}")
    return rows


# ---------------------------------------------------------------------------
# Step 2: Scrape posts (no reactions — fast pass)
# ---------------------------------------------------------------------------

def scrape_posts(all_urls: list[str], months: int = 3) -> tuple[str | None, list]:
    """
    Scrape posts from all URLs (company pages + employee profiles).
    No reactions — just post metadata.
    Returns (dataset_id, raw_items).
    """
    period_map = {1: "month", 2: "3months", 3: "3months", 6: "6months", 12: "year"}
    period = period_map.get(months, "3months")

    print(f"\n[posts] Scraping posts from {len(all_urls)} URLs (period={period})...")
    payload = {
        "actorId": "harvestapi/linkedin-company-posts",
        "input": {
            "targetUrls": all_urls,
            "postedLimit": period,
            "maxPosts": 50,
            "scrapeReactions": False,
            "scrapeComments": False,
        },
    }
    raw = deepline_raw("apify_run_actor", payload, timeout=POST_SCRAPE_TIMEOUT)
    if "TIMEOUT" in raw:
        print("[posts] Actor timed out in CLI. Trying to extract dataset_id from partial output...")

    dataset_id = extract_dataset_id(raw)
    run_id = extract_run_id(raw)
    if not dataset_id and run_id:
        print(f"[posts] Got run_id={run_id}, polling for completion...")
        dataset_id = poll_for_dataset(run_id)

    if not dataset_id:
        print("[posts] Could not get dataset_id. Aborting post scrape.")
        return None, []

    print(f"[posts] Dataset: {dataset_id}. Downloading items...")
    items = download_dataset(dataset_id, limit=5000)
    print(f"[posts] Downloaded {len(items)} posts")
    return dataset_id, items


def poll_for_dataset(run_id: str, max_wait: int = 300) -> str | None:
    """Poll apify_get_actor_run until SUCCEEDED and return defaultDatasetId."""
    start = time.time()
    while time.time() - start < max_wait:
        result = deepline("apify_get_actor_run", {"runId": run_id}, timeout=30)
        if result:
            run_data = result.get("data", {})
            if isinstance(run_data, dict):
                run_info = run_data.get("run", run_data)
            else:
                run_info = {}
            status = run_info.get("status", "")
            if status == "SUCCEEDED":
                return run_info.get("defaultDatasetId")
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                print(f"[poll] Run {run_id} ended with status: {status}")
                return None
            print(f"[poll] Run {run_id} status={status}, waiting...")
        time.sleep(10)
    print(f"[poll] Timeout waiting for run {run_id}")
    return None


def download_dataset(dataset_id: str, limit: int = 2000) -> list:
    """Download all items from an Apify dataset."""
    result = deepline(
        "apify_get_dataset_items",
        {"datasetId": dataset_id, "params": {"limit": limit}},
        timeout=120,
    )
    if not result:
        return []
    if isinstance(result, dict):
        return result.get("data", result.get("items", []))
    return result if isinstance(result, list) else []


# ---------------------------------------------------------------------------
# Step 3: Parse posts → metadata dict
# ---------------------------------------------------------------------------

def parse_posts(raw_items: list) -> tuple[dict, list]:
    """
    Parse raw Apify post items into posts_by_url dict and sorted list.
    Returns (posts_by_url, all_posts_sorted_by_reactions).

    Actual Apify field names (from harvestapi/linkedin-company-posts):
      - "linkedinUrl"  (not "postUrl")
      - "content"      (not "text")
      - "author"       (dict with "name", "url" keys)
      - "postedAt"     (ISO string or dict)
      - "engagement"   (dict with "likes", "comments" keys)
    """
    posts_by_url = {}
    for item in raw_items:
        # Actual field is "linkedinUrl"; fall back to legacy names
        url = (item.get("linkedinUrl") or item.get("postUrl") or
               item.get("url") or item.get("post_url") or "").strip().rstrip("/")
        if not url:
            continue

        # Author: returned as dict {"name": ..., "url": ...}
        author = item.get("authorName") or item.get("author_name") or ""
        author_linkedin = item.get("authorProfileUrl") or item.get("author_linkedin") or ""
        if isinstance(item.get("author"), dict):
            author = author or item["author"].get("name", "")
            author_linkedin = author_linkedin or item["author"].get("url", "") or item["author"].get("linkedinUrl", "")

        # Engagement: returned as dict {"likes": N, "comments": N}
        eng = item.get("engagement") or {}
        if not isinstance(eng, dict):
            eng = {}
        reactions = int(
            eng.get("likes") or eng.get("reactions") or
            item.get("totalReactions") or item.get("total_reactions") or item.get("likesCount") or 0
        )
        comments = int(
            eng.get("comments") or
            item.get("totalComments") or item.get("total_comments") or item.get("commentsCount") or 0
        )

        posts_by_url[url] = {
            "post_url": url,
            "author_name": author,
            "author_linkedin": author_linkedin,
            "author_type": "company" if "company" in author_linkedin.lower() else "person",
            "posted_at": str(item.get("postedAt") or item.get("posted_at") or ""),
            "content_preview": (item.get("content") or item.get("text") or item.get("commentary") or "")[:200],
            "total_reactions": reactions,
            "total_comments": comments,
            "num_shares": int(item.get("sharesCount") or item.get("num_shares") or 0),
        }

    all_posts = sorted(posts_by_url.values(), key=lambda x: x["total_reactions"], reverse=True)
    print(f"[parse_posts] {len(all_posts)} unique posts")
    return posts_by_url, all_posts


def filter_high_engagement(posts: list, min_reactions: int = 5, min_comments: int = 2) -> list:
    """Filter posts with enough engagement to be worth scraping reactions on."""
    return [p for p in posts if p["total_reactions"] >= min_reactions or p["total_comments"] >= min_comments]


# ---------------------------------------------------------------------------
# Step 4: Build reaction-scraping batches
# ---------------------------------------------------------------------------

def build_batches(posts: list, batch_size: int = BATCH_SIZE) -> list[dict]:
    """
    Split post URLs into batches for Apify reaction scraping.
    Viral posts (>300 reactions) get separate batches with reduced limits.
    """
    normal = [p for p in posts if p["total_reactions"] <= 300]
    viral  = [p for p in posts if p["total_reactions"] > 300]

    batches = []
    for i in range(0, len(normal), batch_size):
        chunk = [p["post_url"] for p in normal[i:i+batch_size] if p.get("post_url")]
        if chunk:
            batches.append({"urls": chunk, "maxReactions": 100, "maxComments": 50})

    # Viral: smaller chunks, lower limits
    viral_chunk = 5
    for i in range(0, len(viral), viral_chunk):
        chunk = [p["post_url"] for p in viral[i:i+viral_chunk] if p.get("post_url")]
        if chunk:
            batches.append({"urls": chunk, "maxReactions": 50, "maxComments": 30})

    print(f"[batches] {len(batches)} batches ({len(normal)} normal posts, {len(viral)} viral posts)")
    return batches


# ---------------------------------------------------------------------------
# Step 5: Scrape reactions/comments for each batch
# ---------------------------------------------------------------------------

def run_batch(batch: dict, idx: int) -> str | None:
    """Run one reaction-scraping batch. Returns datasetId or None."""
    payload = {
        "actorId": "harvestapi/linkedin-company-posts",
        "input": {
            "targetUrls": batch["urls"],
            "scrapeReactions": True,
            "maxReactions": batch["maxReactions"],
            "scrapeComments": True,
            "maxComments": batch["maxComments"],
        },
    }
    raw = deepline_raw("apify_run_actor", payload, timeout=REACTION_SCRAPE_TIMEOUT)
    if "TIMEOUT" in raw:
        print(f"  [batch {idx:02d}] CLI timeout — trying to extract partial datasetId")

    dataset_id = extract_dataset_id(raw)
    if dataset_id:
        print(f"  [batch {idx:02d}] OK → datasetId={dataset_id}")
    else:
        run_id = extract_run_id(raw)
        if run_id:
            print(f"  [batch {idx:02d}] Got runId={run_id}, polling...")
            dataset_id = poll_for_dataset(run_id, max_wait=180)
        if not dataset_id:
            print(f"  [batch {idx:02d}] FAILED — no datasetId")
    return dataset_id


def scrape_all_reactions(batches: list, max_parallel: int = MAX_PARALLEL_BATCHES) -> list[str]:
    """
    Run all batches in parallel groups. Returns list of successful datasetIds.
    Retries each failed batch once before giving up.
    """
    dataset_ids = []
    failed_batches = []

    print(f"\n[reactions] Running {len(batches)} batches (max {max_parallel} parallel)...")
    for group_start in range(0, len(batches), max_parallel):
        group = batches[group_start:group_start + max_parallel]
        print(f"[reactions] Group {group_start//max_parallel + 1}: batches {group_start}–{group_start+len(group)-1}")
        with ThreadPoolExecutor(max_workers=max_parallel) as ex:
            futures = {
                ex.submit(run_batch, batch, group_start + i): (group_start + i, batch)
                for i, batch in enumerate(group)
            }
            for future in as_completed(futures):
                idx, batch = futures[future]
                try:
                    ds_id = future.result()
                    if ds_id:
                        dataset_ids.append(ds_id)
                    else:
                        failed_batches.append((idx, batch))
                except Exception as e:
                    print(f"  [batch {idx:02d}] exception: {e}")
                    failed_batches.append((idx, batch))

    # Retry failed batches once, sequentially
    if failed_batches:
        print(f"\n[reactions] Retrying {len(failed_batches)} failed batches (sequential)...")
        for idx, batch in failed_batches:
            ds_id = run_batch(batch, idx)
            if ds_id:
                dataset_ids.append(ds_id)
            else:
                print(f"  [batch {idx:02d}] still failed after retry — skipping")

    print(f"[reactions] {len(dataset_ids)}/{len(batches)} batches succeeded")
    return dataset_ids


# ---------------------------------------------------------------------------
# Step 6: Download + parse engagement data
# ---------------------------------------------------------------------------

def download_all_engagements(dataset_ids: list, workdir: str) -> list:
    """Download all datasets and return combined list of raw engagement items."""
    all_items = []
    print(f"\n[download] Fetching {len(dataset_ids)} datasets...")
    for i, ds_id in enumerate(dataset_ids):
        print(f"  [download] {i+1}/{len(dataset_ids)}: {ds_id}")
        items = download_dataset(ds_id, limit=2000)
        print(f"    → {len(items)} items")
        all_items.extend(items)
    print(f"[download] Total raw items: {len(all_items)}")
    return all_items


def extract_handle(url: str) -> str | None:
    """Extract LinkedIn handle from any LinkedIn URL."""
    url = url.rstrip("/")
    m = re.search(r"/(?:in|company|pub)/([^/?#]+)", url)
    if m:
        return m.group(1).lower()
    m = re.search(r"/posts/([^_]+)_", url)
    if m:
        return m.group(1).lower()
    return None


def classify_title(position: str) -> str | None:
    """Return senior title category or None."""
    if not position:
        return None
    p = position.lower()
    for category, patterns in SENIOR_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, p):
                return category
    return None


def build_engagement_rows(
    raw_items: list,
    posts_by_url: dict,
    handle_to_company: dict,
) -> list[dict]:
    """
    Convert raw Apify engagement items into flat rows.
    Deduplicates on (post_url, actor_id, type).
    """
    rows = []
    seen = set()

    for item in raw_items:
        actor = item.get("actor", {})
        position = actor.get("position", "") or ""
        post_url = (item.get("query", {}).get("post") or item.get("postUrl") or "").strip().rstrip("/")
        actor_id = actor.get("id", "")
        eng_type = item.get("type", "")

        dedup_key = (post_url, actor_id, eng_type)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        category = classify_title(position)
        post_meta = posts_by_url.get(post_url, {})
        handle = extract_handle(post_url)
        company = handle_to_company.get(handle, "") if handle else ""

        # Parse posted_at
        posted_at_raw = post_meta.get("posted_at", "")
        posted_at = ""
        if posted_at_raw:
            d = re.search(r"'date':\s*'([^']+)'", posted_at_raw)
            if d:
                posted_at = d.group(1)[:10]
            elif re.match(r"\d{4}-\d{2}-\d{2}", posted_at_raw):
                posted_at = posted_at_raw[:10]

        rows.append({
            "company": company,
            "post_url": post_url,
            "post_author": post_meta.get("author_name", ""),
            "post_author_linkedin": post_meta.get("author_linkedin", ""),
            "post_date": posted_at,
            "post_total_reactions": post_meta.get("total_reactions", ""),
            "post_total_comments": post_meta.get("total_comments", ""),
            "post_content_preview": post_meta.get("content_preview", ""),
            "engagement_type": eng_type,
            "reaction_type": item.get("reactionType", "") if eng_type == "reaction" else "",
            "comment_text": (item.get("commentary", "") or "") if eng_type == "comment" else "",
            "comment_url": item.get("linkedinUrl", "") if eng_type == "comment" else "",
            "engagement_date": (item.get("createdAt", "") or "")[:10],
            "engager_name": actor.get("name", ""),
            "engager_linkedin_url": actor.get("linkedinUrl", ""),
            "engager_position": position,
            "engager_title_category": category or "",
            "is_senior": "yes" if category else "no",
            "engager_picture_url": actor.get("pictureUrl", ""),
        })

    return rows


# ---------------------------------------------------------------------------
# Step 7: Write CSVs
# ---------------------------------------------------------------------------

def write_csvs(rows: list, workdir: str) -> tuple[str, str]:
    """Write all_engagements.csv and senior_engagements.csv. Returns (all_path, senior_path)."""
    if not rows:
        print("[csv] No rows to write")
        return "", ""

    fieldnames = list(rows[0].keys())
    senior = [r for r in rows if r["is_senior"] == "yes"]

    all_path = os.path.join(workdir, "all_engagements.csv")
    senior_path = os.path.join(workdir, "senior_engagements.csv")

    with open(all_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    with open(senior_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(senior)

    print(f"\n[csv] all_engagements.csv: {len(rows)} rows → {all_path}")
    print(f"[csv] senior_engagements.csv: {len(senior)} rows → {senior_path}")
    by_cat = Counter(r["engager_title_category"] for r in senior)
    by_co = Counter(r["company"] for r in senior if r["company"])
    print(f"[csv] Senior by category: {dict(by_cat)}")
    print(f"[csv] Senior by company: {dict(by_co)}")
    return all_path, senior_path


# ---------------------------------------------------------------------------
# Step 8: Dashboard HTML
# ---------------------------------------------------------------------------

def build_dashboard(rows: list, workdir: str) -> str:
    """Generate self-contained dashboard.html. Returns path."""
    senior = [r for r in rows if r["is_senior"] == "yes"]
    if not senior:
        print("[dashboard] No senior rows — skipping dashboard")
        return ""

    # Aggregate data
    by_company = dict(Counter(r["company"] or "External" for r in senior))
    by_cat = dict(Counter(r["engager_title_category"] for r in senior))
    reaction_types = dict(Counter(r["reaction_type"] for r in senior if r["reaction_type"]))

    post_counts = Counter(r["post_url"] for r in senior)
    post_meta = {}
    for r in senior:
        url = r["post_url"]
        if url not in post_meta:
            post_meta[url] = {
                "url": url,
                "author": r["post_author"] or "Unknown",
                "company": r["company"] or "External",
                "date": r["post_date"],
                "preview": r["post_content_preview"][:100] if r["post_content_preview"] else "",
                "senior_engagements": post_counts[url],
            }
    top_posts = sorted(post_meta.values(), key=lambda x: x["senior_engagements"], reverse=True)[:15]

    engager_meta = {}
    for r in senior:
        key = r["engager_linkedin_url"]
        if key not in engager_meta:
            engager_meta[key] = {
                "name": r["engager_name"],
                "url": r["engager_linkedin_url"],
                "position": r["engager_position"],
                "category": r["engager_title_category"],
                "picture": r["engager_picture_url"],
                "count": 0,
                "companies": set(),
            }
        engager_meta[key]["count"] += 1
        if r["company"]:
            engager_meta[key]["companies"].add(r["company"])
    top_engagers = sorted(engager_meta.values(), key=lambda x: x["count"], reverse=True)[:20]
    for e in top_engagers:
        e["companies"] = ", ".join(sorted(e["companies"])) or "External"

    month_counts = {}
    for r in senior:
        d = r["post_date"]
        if d and len(d) >= 7:
            month_counts[d[:7]] = month_counts.get(d[:7], 0) + 1

    total_reactions = sum(1 for r in senior if r["engagement_type"] == "reaction")
    total_comments = sum(1 for r in senior if r["engagement_type"] == "comment")
    unique_engagers = len(set(r["engager_linkedin_url"] for r in senior))

    data_json = json.dumps({
        "summary": {
            "total_senior": len(senior),
            "total_all": len(rows),
            "unique_engagers": unique_engagers,
            "reactions": total_reactions,
            "comments": total_comments,
        },
        "by_company": by_company,
        "by_cat": by_cat,
        "reaction_types": reaction_types,
        "top_posts": top_posts,
        "top_engagers": top_engagers,
        "timeline": dict(sorted(month_counts.items())),
    }, default=str)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Competitive Engagement Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{--bg:#0f1117;--s1:#1a1d27;--s2:#222635;--b:#2e3347;--tx:#e8eaf0;--mu:#7c82a0;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--tx);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;}}
header{{background:var(--s1);border-bottom:1px solid var(--b);padding:18px 28px;}}
header h1{{font-size:17px;font-weight:600;}}
header p{{color:var(--mu);font-size:12px;margin-top:3px;}}
main{{padding:22px 28px;max-width:1400px;margin:0 auto;}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px;}}
.stat{{background:var(--s1);border:1px solid var(--b);border-radius:10px;padding:16px;}}
.stat .l{{color:var(--mu);font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;}}
.stat .v{{font-size:26px;font-weight:700;letter-spacing:-1px;}}
.charts{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:20px;}}
.chart-card{{background:var(--s1);border:1px solid var(--b);border-radius:10px;padding:18px;}}
.chart-card h3{{font-size:13px;font-weight:600;margin-bottom:12px;}}
.wide{{grid-column:span 2;}}
table{{width:100%;border-collapse:collapse;}}
th{{text-align:left;font-size:11px;text-transform:uppercase;color:var(--mu);padding:8px 10px;border-bottom:1px solid var(--b);}}
td{{padding:9px 10px;border-bottom:1px solid var(--b);font-size:13px;}}
tr:last-child td{{border-bottom:none;}}
tr:hover td{{background:var(--s2);}}
.co{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;}}
a{{color:inherit;text-decoration:none;}}
a:hover{{text-decoration:underline;}}
</style>
</head>
<body>
<header>
  <h1>Competitive Engagement Dashboard</h1>
  <p>Senior LinkedIn engagements (VP / C-Suite / Director / Sales / Marketing) · Last 3 months</p>
</header>
<main>
<div class="stats">
  <div class="stat"><div class="l">Senior Engagements</div><div class="v" id="sTot"></div></div>
  <div class="stat"><div class="l">All Engagements</div><div class="v" id="sAll"></div></div>
  <div class="stat"><div class="l">Unique Engagers</div><div class="v" id="sUniq"></div></div>
  <div class="stat"><div class="l">Reactions</div><div class="v" id="sReact"></div></div>
  <div class="stat"><div class="l">Comments</div><div class="v" id="sComment"></div></div>
</div>
<div class="charts">
  <div class="chart-card"><h3>By Company</h3><canvas id="coCh" height="220"></canvas></div>
  <div class="chart-card"><h3>Title Category</h3><canvas id="catCh" height="220"></canvas></div>
  <div class="chart-card"><h3>Reaction Types</h3><canvas id="rxCh" height="220"></canvas></div>
  <div class="chart-card wide"><h3>Monthly Trend</h3><canvas id="tlCh" height="160"></canvas></div>
  <div class="chart-card"><h3>Title Mix per Company</h3><canvas id="stCh" height="160"></canvas></div>
</div>
<div class="chart-card" style="margin-bottom:20px">
  <h3>Top Posts by Senior Engagement</h3>
  <table><thead><tr><th>#</th><th>Author</th><th>Company</th><th>Date</th><th>Preview</th><th>Senior Eng.</th><th></th></tr></thead>
  <tbody id="postTbl"></tbody></table>
</div>
<div class="chart-card">
  <h3>Top 20 Engagers</h3>
  <table><thead><tr><th>Name</th><th>Position</th><th>Category</th><th>Companies Engaged</th><th>Count</th><th>Profile</th></tr></thead>
  <tbody id="engTbl"></tbody></table>
</div>
</main>
<script>
const D=__DATA_JSON__;
const C={{GoAugment:'#22d3ee',TryPallet:'#f472b6',Vooma:'#6366f1',External:'#64748b'}};
const CC={{'C-Suite/Exec':'#a78bfa',VP:'#60a5fa',Director:'#34d399',Sales:'#f59e0b',Marketing:'#fb7185'}};
function coColor(co){{return C[co]||'#64748b';}}
document.getElementById('sTot').textContent=D.summary.total_senior.toLocaleString();
document.getElementById('sAll').textContent=D.summary.total_all.toLocaleString();
document.getElementById('sUniq').textContent=D.summary.unique_engagers.toLocaleString();
document.getElementById('sReact').textContent=D.summary.reactions.toLocaleString();
document.getElementById('sComment').textContent=D.summary.comments.toLocaleString();
const opts={{responsive:true,plugins:{{legend:{{labels:{{color:'#7c82a0',font:{{size:11}}}}}}}},scales:{{}}}};
new Chart('coCh',{{type:'bar',data:{{labels:Object.keys(D.by_company),datasets:[{{data:Object.values(D.by_company),backgroundColor:Object.keys(D.by_company).map(coColor).map(c=>c+'cc'),borderWidth:0,borderRadius:4}}]}},options:{{...opts,plugins:{{legend:{{display:false}}}},scales:{{y:{{ticks:{{color:'#7c82a0',font:{{size:11}}}},grid:{{color:'#2e3347'}}}},x:{{ticks:{{color:'#e8eaf0',font:{{size:11}}}},grid:{{display:false}}}}}}}}}}});
new Chart('catCh',{{type:'doughnut',data:{{labels:Object.keys(D.by_cat),datasets:[{{data:Object.values(D.by_cat),backgroundColor:Object.keys(D.by_cat).map(k=>CC[k]||'#888')}}]}},options:{{responsive:true,cutout:'62%',plugins:{{legend:{{position:'right',labels:{{color:'#7c82a0',font:{{size:11}},boxWidth:12}}}}}}}}}});
new Chart('rxCh',{{type:'bar',data:{{labels:Object.keys(D.reaction_types),datasets:[{{data:Object.values(D.reaction_types),backgroundColor:'rgba(99,102,241,0.8)',borderWidth:0,borderRadius:4}}]}},options:{{...opts,indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#7c82a0',font:{{size:11}}}},grid:{{color:'#2e3347'}}}},y:{{ticks:{{color:'#e8eaf0',font:{{size:11}}}},grid:{{display:false}}}}}}}}}}});
new Chart('tlCh',{{type:'line',data:{{labels:Object.keys(D.timeline),datasets:[{{label:'Senior Eng',data:Object.values(D.timeline),borderColor:'#22d3ee',backgroundColor:'rgba(34,211,238,0.1)',fill:true,tension:0.4,pointRadius:4}}]}},options:{{...opts,plugins:{{legend:{{display:false}}}},scales:{{y:{{ticks:{{color:'#7c82a0',font:{{size:11}}}},grid:{{color:'#2e3347'}}}},x:{{ticks:{{color:'#e8eaf0',font:{{size:11}}}},grid:{{display:false}}}}}}}}}}});
const cos=['GoAugment','TryPallet','Vooma'];
const cats=['C-Suite/Exec','VP','Director','Sales','Marketing'];
new Chart('stCh',{{type:'bar',data:{{labels:cos,datasets:cats.map((c,i)=>({label:c,data:cos.map(co=>(D.by_company_cat?.[co]?.[c])||0),backgroundColor:Object.values(CC)[i]+'cc',borderWidth:0}})}},options:{{...opts,scales:{{x:{{stacked:true,ticks:{{color:'#e8eaf0',font:{{size:11}}}},grid:{{display:false}}}},y:{{stacked:true,ticks:{{color:'#7c82a0',font:{{size:11}}}},grid:{{color:'#2e3347'}}}}}},plugins:{{legend:{{position:'right',labels:{{color:'#7c82a0',font:{{size:11}},boxWidth:10}}}}}}}}}}});
const maxSE=Math.max(...D.top_posts.map(p=>p.senior_engagements));
D.top_posts.forEach((p,i)=>{{document.getElementById('postTbl').innerHTML+=`<tr><td style="color:#7c82a0">${{i+1}}</td><td>${{p.author}}</td><td><span class="co" style="background:${{coColor(p.company)}}22;color:${{coColor(p.company)}}">${{p.company}}</span></td><td style="color:#7c82a0;font-size:12px">${{p.date||'—'}}</td><td style="color:#7c82a0;font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{p.preview||'—'}}</td><td><b>${{p.senior_engagements}}</b></td><td><a href="${{p.url}}" target="_blank" style="color:#7c82a0;font-size:11px">↗</a></td></tr>`;}});
D.top_engagers.forEach((e,i)=>{{const multi=e.companies.includes(',');document.getElementById('engTbl').innerHTML+=`<tr><td><b>${{i+1}}. ${{e.name}}</b></td><td style="color:#7c82a0;font-size:12px;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{e.position.slice(0,80)}}</td><td><span style="font-size:11px;color:${{CC[e.category]||'#888'}}">${{e.category}}</span></td><td style="font-size:12px">${{e.companies}}${{multi?' <b style=\\"color:#a78bfa\\">⚡</b>':''}} </td><td><b>${{e.count}}</b></td><td><a href="${{e.url}}" target="_blank" style="color:#7c82a0;font-size:11px">↗</a></td></tr>`;}});
</script>
</body>
</html>"""
    # Replace placeholder (avoids f-string vs JS brace conflicts)
    html = html.replace("__DATA_JSON__", data_json)

    out_path = os.path.join(workdir, "dashboard.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"[dashboard] Saved → {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Step 9: Package output
# ---------------------------------------------------------------------------

def package_zip(workdir: str) -> str:
    """Zip dashboard + both CSVs for sharing."""
    import zipfile
    zip_path = os.path.join(workdir, "competitive_analysis.zip")
    files = ["dashboard.html", "all_engagements.csv", "senior_engagements.csv"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in files:
            fpath = os.path.join(workdir, fname)
            if os.path.exists(fpath):
                zf.write(fpath, fname)
    size_mb = os.path.getsize(zip_path) / 1024 / 1024
    print(f"[zip] {zip_path} ({size_mb:.1f} MB)")
    return zip_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_company_arg(s: str) -> dict:
    """
    Parse company arg: "Name:linkedin_url:domain" or "Name:linkedin_url"
    """
    parts = s.split(":", 2)
    if len(parts) < 2:
        raise ValueError(f"Invalid company format (need Name:linkedin_url[:domain]): {s}")
    return {
        "name": parts[0].strip(),
        "linkedin_url": parts[1].strip(),
        "domain": parts[2].strip() if len(parts) > 2 else "",
    }


def main():
    parser = argparse.ArgumentParser(description="Competitive social listening pipeline")
    parser.add_argument("--companies", nargs="+",
                        help="Companies as 'Name:linkedin_url:domain' (repeat for multiple)")
    parser.add_argument("--output", default="/tmp/comp_social",
                        help="Output directory (default: /tmp/comp_social)")
    parser.add_argument("--months", type=int, default=3,
                        help="Lookback months (default: 3)")
    parser.add_argument("--employees", type=int, default=10,
                        help="Max employees per company (default: 10)")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: 1 company, 2 employees, 5 posts, 10 reactions")
    args = parser.parse_args()

    # Test mode defaults
    if args.test:
        print("=== TEST MODE: GoAugment only, 2 employees, 5 posts, 10 reactions ===\n")
        companies = [{"name": "GoAugment", "linkedin_url": "https://www.linkedin.com/company/goaugment/", "domain": "goaugment.com"}]
        args.employees = 2
        args.months = 1
        global BATCH_SIZE
        BATCH_SIZE = 5
    elif args.companies:
        companies = [parse_company_arg(c) for c in args.companies]
    else:
        parser.print_help()
        sys.exit(1)

    workdir = args.output
    Path(workdir).mkdir(parents=True, exist_ok=True)
    print(f"Output: {workdir}")
    print(f"Companies: {[c['name'] for c in companies]}")
    print(f"Months: {args.months}, Max employees: {args.employees}\n")

    # ---- Build all_urls: company pages + employees ----
    all_url_rows = []
    for co in companies:
        all_url_rows.append({
            "company": co["name"],
            "linkedin_url": co["linkedin_url"],
            "description": "Company Page",
        })
        if co["domain"]:
            employees = discover_employees(co["name"], co["domain"], limit=args.employees)
            all_url_rows.extend(employees)

    # Write all_urls.csv
    all_urls_path = os.path.join(workdir, "all_urls.csv")
    with open(all_urls_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["company", "linkedin_url", "description"])
        w.writeheader()
        w.writerows(all_url_rows)

    # Build handle → company map
    handle_to_company = {}
    for row in all_url_rows:
        h = extract_handle(row["linkedin_url"])
        if h:
            handle_to_company[h] = row["company"]

    all_linkedin_urls = [r["linkedin_url"] for r in all_url_rows]
    print(f"\n[setup] Total URLs: {len(all_linkedin_urls)}")

    # ---- Step 2: Scrape posts ----
    _, raw_post_items = scrape_posts(all_linkedin_urls, months=args.months)
    if not raw_post_items:
        print("[ERROR] No posts scraped. Check Apify credentials and URLs.")
        sys.exit(1)

    posts_by_url, all_posts = parse_posts(raw_post_items)

    # Write posts_data.csv
    posts_csv_path = os.path.join(workdir, "posts_data.csv")
    if all_posts:
        with open(posts_csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_posts[0].keys()))
            w.writeheader()
            w.writerows(all_posts)
        print(f"[posts] Saved {len(all_posts)} posts → {posts_csv_path}")

    # Filter high-engagement
    high_eng = filter_high_engagement(all_posts)
    print(f"[posts] High-engagement posts: {len(high_eng)}/{len(all_posts)}")

    # In test mode, cap to 5 posts
    if args.test:
        high_eng = high_eng[:5]
        print(f"[test] Capped to {len(high_eng)} posts")

    if not high_eng:
        print("[WARN] No high-engagement posts found. Writing empty outputs.")
        write_csvs([], workdir)
        sys.exit(0)

    # ---- Step 3-5: Batch reaction scraping ----
    # In test mode, use low reaction limits
    if args.test:
        batches = [{"urls": [p["post_url"] for p in high_eng[:5] if p.get("post_url")],
                    "maxReactions": 10, "maxComments": 5}]
    else:
        batches = build_batches(high_eng)

    dataset_ids = scrape_all_reactions(batches)
    if not dataset_ids:
        print("[ERROR] No reaction datasets collected.")
        sys.exit(1)

    # ---- Step 6: Download + parse engagements ----
    raw_engagement_items = download_all_engagements(dataset_ids, workdir)
    engagement_rows = build_engagement_rows(raw_engagement_items, posts_by_url, handle_to_company)
    print(f"[engagements] {len(engagement_rows)} deduplicated rows")

    # ---- Step 7: Write CSVs ----
    write_csvs(engagement_rows, workdir)

    # ---- Step 8: Dashboard ----
    build_dashboard(engagement_rows, workdir)

    # ---- Step 9: Zip ----
    package_zip(workdir)

    # ---- Summary ----
    senior = [r for r in engagement_rows if r["is_senior"] == "yes"]
    print(f"""
=== DONE ===
Output: {workdir}
  all_engagements.csv      {len(engagement_rows):>6} rows
  senior_engagements.csv   {len(senior):>6} rows (VP/CXO/Director/Sales/Mkt)
  dashboard.html           → open in browser
  competitive_analysis.zip → share this

Senior by company: {dict(Counter(r['company'] for r in senior if r['company']))}
""")


if __name__ == "__main__":
    main()
