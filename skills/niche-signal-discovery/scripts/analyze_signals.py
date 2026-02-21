#!/usr/bin/env python3
"""
Differential signal analysis for ICP niche signal discovery.

Reads a Deepline-enriched CSV, parses exa_search website content and crustdata
job listings, computes Laplace-smoothed lift scores for keyword categories,
extracts tech stack tools, and outputs JSON results.

Usage:
    python3 analyze_signals.py \\
      --input enriched.csv \\
      --keywords keywords.json \\
      --tools tools.json \\
      --job-roles job_roles.json \\
      --output analysis.json

Options:
    --input         Path to enriched CSV (required)
    --keywords      Path to JSON file with keyword categories (required)
    --tools         Path to JSON file with tech stack tools (required)
    --job-roles     Path to JSON file with job role categories (required)
    --output        Path for JSON output (default: stdout)
    --website-col   Column index for website data (auto-detected if omitted)
    --jobs-col      Column index for job listings (auto-detected if omitted)
    --status-col    Column name for won/lost status (default: "status")

See references/keyword-catalog.md for JSON format examples and guidance on
building target-specific keyword, tool, and job role lists.
"""

import csv
import json
import sys
import re
import argparse
from collections import defaultdict

csv.field_size_limit(sys.maxsize)


def auto_detect_columns(headers):
    """Find website and jobs columns by looking for __dl_full_result__ pattern."""
    website_col = None
    jobs_col = None
    for i, h in enumerate(headers):
        if "__dl_full_result__" in h:
            # Try to determine if it's website or jobs by checking position
            if website_col is None:
                website_col = i
            elif jobs_col is None:
                jobs_col = i
    return website_col, jobs_col


def parse_website_content(cell_value):
    """Extract text content from exa_search results.
    Returns:
        combined_text: all page text concatenated (lowercased)
        pages: list of {url, title, text} per page (text is lowercased)
    """
    if not cell_value or cell_value.strip() == "":
        return "", []
    try:
        data = json.loads(cell_value)
    except (json.JSONDecodeError, TypeError):
        return str(cell_value), []

    texts = []
    pages = []

    # Handle various response shapes
    results = []
    if isinstance(data, dict):
        results = data.get("data", {}).get("results", []) if isinstance(data.get("data"), dict) else []
        if not results:
            results = data.get("results", [])
    elif isinstance(data, list):
        results = data

    for r in results:
        if isinstance(r, dict):
            text = r.get("text", "")
            url = r.get("url", "")
            title = r.get("title", "")
            if text:
                texts.append(text)
            if url:
                pages.append({"url": url, "title": title, "text": text.lower()})

    return " ".join(texts).lower(), pages


def parse_job_listings(cell_value):
    """Extract job titles and descriptions from crustdata job listings.
    Returns:
        listings: list of {title, description, url, text} per listing (text is lowercased)
        combined_text: all listing text concatenated (lowercased)
    """
    if not cell_value or cell_value.strip() == "":
        return [], ""
    try:
        data = json.loads(cell_value)
    except (json.JSONDecodeError, TypeError):
        return [], str(cell_value)

    listings = []
    all_text = []

    # Handle various response shapes
    raw_listings = []
    if isinstance(data, dict):
        raw_listings = data.get("data", {}).get("listings", []) if isinstance(data.get("data"), dict) else []
        if not raw_listings:
            raw_listings = data.get("listings", [])
    elif isinstance(data, list):
        raw_listings = data

    for entry in raw_listings:
        if isinstance(entry, dict):
            # Crustdata uses "title" and "description" (not "job_title"/"job_description")
            title = entry.get("title", entry.get("job_title", ""))
            desc = entry.get("description", entry.get("job_description", ""))
            url = entry.get("url", "")
            combined = f"{title} {desc}"
            listings.append({"title": title, "description": desc, "url": url, "text": combined.lower()})
            all_text.append(combined)

    return listings, " ".join(all_text).lower()


def substring_match(text, keyword):
    """Check if keyword appears as substring in text (case-insensitive)."""
    if not text:
        return False
    return keyword.lower().rstrip("*") in text.lower()


def laplace_lift(won_count, won_total, lost_count, lost_total):
    """Compute Laplace-smoothed lift (Bayesian posterior mean ratio with Jeffreys prior)."""
    won_rate = (won_count + 0.5) / (won_total + 1)
    lost_rate = (lost_count + 0.5) / (lost_total + 1)
    return won_rate / lost_rate


def extract_snippet(text, keyword, context_chars=40):
    """Extract a snippet around the first occurrence of keyword in text."""
    idx = text.find(keyword)
    if idx == -1:
        return None
    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(keyword) + context_chars)
    snippet = text[start:end].strip()
    # Clean up: trim to word boundaries
    if start > 0:
        space = snippet.find(" ")
        if space > 0 and space < context_chars // 2:
            snippet = snippet[space + 1:]
        snippet = "..." + snippet
    if end < len(text):
        space = snippet.rfind(" ")
        if space > len(snippet) - context_chars // 2:
            snippet = snippet[:space]
        snippet = snippet + "..."
    return snippet


def find_source_evidence(keyword, companies, max_evidence=5):
    """Find exact quotes with source URLs for a keyword match.
    Returns list of evidence objects with company, source_type, quote, url, and page_title.
    """
    evidence = []
    kw = keyword.lower().rstrip("*")

    for company in companies:
        if len(evidence) >= max_evidence:
            break

        # Check website pages (per-page text has URLs)
        for page in company.get("pages", []):
            page_text = page.get("text", "")
            if kw in page_text:
                snippet = extract_snippet(page_text, kw)
                if snippet:
                    evidence.append({
                        "company": company["domain"],
                        "source_type": "website",
                        "quote": snippet,
                        "url": page.get("url", ""),
                        "page_title": page.get("title", ""),
                    })
                    break  # One match per company per source type

        # Check job listings (per-listing text has URLs)
        for listing in company.get("job_listings", []):
            listing_text = listing.get("text", "")
            if kw in listing_text:
                snippet = extract_snippet(listing_text, kw)
                job_title = listing.get("title", "")
                if snippet:
                    evidence.append({
                        "company": company["domain"],
                        "source_type": "job_listing",
                        "quote": snippet,
                        "url": listing.get("url", ""),
                        "job_title": job_title,
                    })
                    break  # One match per company per source type

    return evidence


def analyze(input_path, keywords, tools, job_roles,
            website_col=None, jobs_col=None, status_col="status"):
    """Run the full differential analysis.

    Args:
        input_path: Path to enriched CSV
        keywords: Dict of category -> list of keyword strings
        tools: Dict of category -> list of tool name strings
        job_roles: Dict of role_name -> list of role keyword strings
        website_col: Column index for website data (auto-detected if None)
        jobs_col: Column index for job listings (auto-detected if None)
        status_col: Column name for won/lost status
    """

    # Read CSV
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    # Auto-detect columns if not specified
    if website_col is None or jobs_col is None:
        auto_web, auto_jobs = auto_detect_columns(headers)
        if website_col is None:
            website_col = auto_web
        if jobs_col is None:
            jobs_col = auto_jobs

    # Find status column
    status_idx = None
    for i, h in enumerate(headers):
        if h.lower().strip() == status_col.lower():
            status_idx = i
            break

    if status_idx is None:
        raise ValueError(f"Status column '{status_col}' not found in headers: {headers}")

    # Parse companies
    companies = []
    for row in rows:
        if len(row) <= max(status_idx, website_col or 0, jobs_col or 0):
            continue

        status = row[status_idx].strip().lower()
        if status not in ("won", "lost"):
            continue

        domain = row[0].strip() if row[0] else "unknown"

        website_text = ""
        pages = []
        if website_col is not None and website_col < len(row):
            website_text, pages = parse_website_content(row[website_col])

        job_listings = []
        jobs_text = ""
        if jobs_col is not None and jobs_col < len(row):
            job_listings, jobs_text = parse_job_listings(row[jobs_col])

        # Combined text for general keyword matching
        combined_text = f"{website_text} {jobs_text}"

        companies.append({
            "domain": domain,
            "status": status,
            "website_text": website_text,
            "jobs_text": jobs_text,
            "combined_text": combined_text,
            "pages": pages,
            "job_listings": job_listings,
            "has_website": len(website_text) > 100,
            "has_jobs": len(job_listings) > 0,
        })

    won = [c for c in companies if c["status"] == "won"]
    lost = [c for c in companies if c["status"] == "lost"]
    won_total = len(won)
    lost_total = len(lost)

    # ── Keyword analysis ──
    keyword_results = {}
    for category, kws in keywords.items():
        category_results = []
        for kw in kws:
            kw_lower = kw.lower().rstrip("*")
            won_count = sum(1 for c in won if kw_lower in c["combined_text"])
            lost_count = sum(1 for c in lost if kw_lower in c["combined_text"])
            lift = laplace_lift(won_count, won_total, lost_count, lost_total)

            # Source breakdown (website vs jobs vs both)
            won_web = sum(1 for c in won if kw_lower in c["website_text"] and kw_lower not in c["jobs_text"])
            won_jobs = sum(1 for c in won if kw_lower not in c["website_text"] and kw_lower in c["jobs_text"])
            won_both = sum(1 for c in won if kw_lower in c["website_text"] and kw_lower in c["jobs_text"])

            evidence = find_source_evidence(kw, won + lost)

            category_results.append({
                "keyword": kw,
                "won_count": won_count,
                "won_pct": round(won_count / won_total * 100, 1) if won_total else 0,
                "lost_count": lost_count,
                "lost_pct": round(lost_count / lost_total * 100, 1) if lost_total else 0,
                "lift": round(lift, 2),
                "source_breakdown": {
                    "website_only": won_web,
                    "jobs_only": won_jobs,
                    "both": won_both
                },
                "evidence": evidence
            })

        category_results.sort(key=lambda x: x["lift"], reverse=True)
        keyword_results[category] = category_results

    # ── Tech stack tool analysis ──
    tool_results = {}
    for category, tool_list in tools.items():
        category_results = []
        for tool in tool_list:
            tool_lower = tool.lower()
            won_count = sum(1 for c in won if tool_lower in c["combined_text"])
            lost_count = sum(1 for c in lost if tool_lower in c["combined_text"])

            if won_count < 2 and lost_count < 1:
                continue

            lift = laplace_lift(won_count, won_total, lost_count, lost_total)
            evidence = find_source_evidence(tool, won + lost)

            category_results.append({
                "tool": tool,
                "won_count": won_count,
                "won_pct": round(won_count / won_total * 100, 1) if won_total else 0,
                "lost_count": lost_count,
                "lost_pct": round(lost_count / lost_total * 100, 1) if lost_total else 0,
                "lift": round(lift, 2),
                "evidence": evidence
            })

        category_results.sort(key=lambda x: x["lift"], reverse=True)
        tool_results[category] = category_results

    # ── Job role analysis ──
    job_role_results = {}
    won_with_jobs = [c for c in won if c["has_jobs"]]
    lost_with_jobs = [c for c in lost if c["has_jobs"]]

    for role_name, role_keywords in job_roles.items():
        won_match = sum(1 for c in won_with_jobs
                        if any(rk in c["jobs_text"] for rk in role_keywords))
        lost_match = sum(1 for c in lost_with_jobs
                         if any(rk in c["jobs_text"] for rk in role_keywords))

        job_role_results[role_name] = {
            "won_count": won_match,
            "won_with_jobs": len(won_with_jobs),
            "won_pct": round(won_match / len(won_with_jobs) * 100, 1) if won_with_jobs else 0,
            "lost_count": lost_match,
            "lost_with_jobs": len(lost_with_jobs),
            "lost_pct": round(lost_match / len(lost_with_jobs) * 100, 1) if lost_with_jobs else 0,
        }

    # ── Stats ──
    won_with_content = sum(1 for c in won if c["has_website"])
    lost_with_content = sum(1 for c in lost if c["has_website"])
    avg_won_chars = (sum(len(c["website_text"]) for c in won) / won_total) if won_total else 0
    avg_lost_chars = (sum(len(c["website_text"]) for c in lost) / lost_total) if lost_total else 0

    stats = {
        "won_total": won_total,
        "lost_total": lost_total,
        "won_with_content": won_with_content,
        "lost_with_content": lost_with_content,
        "won_with_jobs": len(won_with_jobs),
        "lost_with_jobs": len(lost_with_jobs),
        "won_coverage_pct": round(won_with_content / won_total * 100, 1) if won_total else 0,
        "lost_coverage_pct": round(lost_with_content / lost_total * 100, 1) if lost_total else 0,
        "avg_won_chars": round(avg_won_chars),
        "avg_lost_chars": round(avg_lost_chars),
    }

    # ── Anti-fit signals (lift < 0.5) ──
    anti_fit = []
    for category, results in keyword_results.items():
        for r in results:
            if r["lift"] < 0.5 and (r["won_count"] > 0 or r["lost_count"] > 1):
                anti_fit.append({**r, "category": category})
    anti_fit.sort(key=lambda x: x["lift"])

    return {
        "keyword_results": keyword_results,
        "tool_results": tool_results,
        "job_results": job_role_results,
        "stats": stats,
        "anti_fit": anti_fit,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Differential signal analysis for ICP",
        epilog="See references/keyword-catalog.md for JSON format examples."
    )
    parser.add_argument("--input", required=True, help="Path to enriched CSV")
    parser.add_argument("--keywords", required=True, help="Path to JSON file with keyword categories")
    parser.add_argument("--tools", required=True, help="Path to JSON file with tech stack tools")
    parser.add_argument("--job-roles", required=True, help="Path to JSON file with job role categories")
    parser.add_argument("--output", help="Path for JSON output (default: stdout)")
    parser.add_argument("--website-col", type=int, help="Column index for website data")
    parser.add_argument("--jobs-col", type=int, help="Column index for job listings")
    parser.add_argument("--status-col", default="status", help="Column name for won/lost status")

    args = parser.parse_args()

    with open(args.keywords) as f:
        keywords = json.load(f)

    with open(args.tools) as f:
        tools = json.load(f)

    with open(args.job_roles) as f:
        job_roles = json.load(f)

    results = analyze(
        input_path=args.input,
        keywords=keywords,
        tools=tools,
        job_roles=job_roles,
        website_col=args.website_col,
        jobs_col=args.jobs_col,
        status_col=args.status_col,
    )

    output = json.dumps(results, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Analysis written to {args.output}", file=sys.stderr)
        print(f"Stats: {json.dumps(results['stats'], indent=2)}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
