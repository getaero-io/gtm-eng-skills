#!/usr/bin/env python3
"""Collect website text and job listings for each domain in an accounts CSV through the Deepline CLI.

Writes a copy of the CSV with `website` and `jobs` JSON cells in the shapes the analyzer accepts,
plus `website_status` / `jobs_status` and per-domain receipts under `<out>.receipts/`. Reruns are
resumable: domains with an existing receipt are not re-purchased.

Tools (price at time of writing): firecrawl_crawl, 0.02 credits per page (async; polled with
firecrawl_get_crawl_status); predictleads_company_job_openings, 0.56 credits per call.

Point-in-time rule: when a row has `known_at`, the provider is asked for openings first seen before it
and the result is filtered again with a strict timezone-aware comparison; undated openings are dropped.
Receipts are keyed by domain AND known_at, so a later-cutoff receipt is never reused for an earlier
decision; duplicate rows share one paid collection. Up to 3 pages (300 openings) are fetched; a company
with more is marked `partial` and its job flags stay unknown downstream. Website text has no history
here; current copy is labeled `retrieved_at` = now so downstream validation can treat it as such.

    python3 collect_sources.py --input accounts.csv --output accounts_sources.csv --pages 8
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import urlsplit
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


NON_PAGE_URL = re.compile(r"\.(xml|pdf)$|sitemap|/(feed|rss)(/|$)", re.I)  # applied to the URL path only
MAX_PAGE_CHARS = 200_000  # per page; truncation beyond this marks the website envelope partial
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def deepline(tool: str, payload: dict, timeout: int = 180) -> dict:
    cmd = ["deepline", "tools", "execute", tool, "--input", json.dumps(payload)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"{tool} exit {res.returncode}: {res.stderr[-500:]}")
    text = res.stdout.strip()
    start = text.find("{")
    return json.loads(text[start:]) if start >= 0 else {}


def crawl_site(domain: str, pages: int, poll_seconds: int, max_wait: int, max_chars: int = MAX_PAGE_CHARS,
               resume_job: str | None = None, checkpoint=None) -> tuple[dict, dict]:
    if resume_job:
        job = resume_job
        receipt = {"tool": "firecrawl_crawl", "provider_job_id": job, "resumed": True}
    else:
        started = deepline("firecrawl_crawl", {
            "url": f"https://{domain}", "limit": pages, "maxDiscoveryDepth": 1, "sitemap": "include",
            "excludePaths": [r"(?i)\.(xml|pdf)($|\?)", r"(?i)sitemap", r"(?i)/(feed|rss)(/|$|\?)"],  # Firecrawl regexes; index files are not page copy
            "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
        })
        raw = (started.get("toolResponse") or {}).get("rawV2") or {}
        job = ((raw.get("data") or {}).get("id")) if isinstance(raw.get("data"), dict) else None
        receipt = {"tool": "firecrawl_crawl", "started": started.get("job_id"), "provider_job_id": job,
                   "billing_start": started.get("billing")}
        if not job:
            return {"ok": False, "error": "crawl_not_started", "raw": raw}, receipt
        if checkpoint:
            checkpoint(receipt)  # persist the paid crawl id before polling so a restart resumes instead of re-buying
    waited = 0
    while waited < max_wait:
        time.sleep(poll_seconds); waited += poll_seconds
        st = deepline("firecrawl_get_crawl_status", {"id": job})
        body = ((st.get("toolResponse") or {}).get("rawV2") or {})
        status = str(body.get("status", "")).lower()
        if status in ("completed", "failed", "cancelled"):
            receipt["billing_status"] = st.get("billing"); receipt["status"] = status
            pages_out = []
            for item in body.get("data") or []:
                md = item.get("markdown") or ""
                meta = item.get("metadata") or {}
                url = meta.get("sourceURL") or meta.get("url") or meta.get("og:url") or ""
                if md.strip() and not NON_PAGE_URL.search(urlsplit(url).path or ""):
                    pages_out.append({"url": url, "title": meta.get("title") or meta.get("og:title") or "",
                                      "markdown": md[:max_chars], "truncated": len(md) > max_chars})
            if status != "completed":
                return {"ok": False, "error": status, "pages": pages_out}, receipt
            result = {"pages": pages_out, "retrieved_at": now(), "completed": body.get("completed"), "total": body.get("total")}
            if any(p.get("truncated") for p in pages_out):
                result["status"] = "partial"  # cut text cannot prove a concept is absent
            return result, receipt
    receipt["status"] = "pending"
    return {"ok": False, "error": "pending", "pending": True}, receipt


def _instant(value: str):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo is not None else None


MAX_JOB_PAGES = 3  # 100 openings per page; more than this is marked partial, not treated as complete


def job_openings(domain: str, known_at: str | None, checkpoint=None, resume: dict | None = None) -> tuple[dict, dict]:
    cutoff = _instant(known_at) if known_at else None
    if known_at and cutoff is None:
        raise ValueError(f"known_at must be an ISO-8601 instant with timezone: {known_at!r}")
    resume = resume or {}
    jobs = list(resume.get("jobs_so_far") or []); dropped = int(resume.get("dropped") or 0); undated = int(resume.get("undated") or 0)
    receipts = list(resume.get("pages") or []); pages = int(resume.get("pages_fetched") or 0)
    meta = resume.get("meta")
    first_page = pages + 1
    if resume.get("complete"):
        first_page = MAX_JOB_PAGES + 1
    for page in range(first_page, MAX_JOB_PAGES + 1):
        payload = {"company_id_or_domain": domain, "limit": 100, "page": page}
        if known_at:
            payload["first_seen_at_until"] = known_at  # provider-side window; filtered again below
        interrupted = None
        try:
            res = deepline("predictleads_company_job_openings", payload)
        except Exception as exc:  # noqa: BLE001
            interrupted = str(exc)[:300]; res = {}
        raw = (res.get("toolResponse") or {}).get("rawV2") or {}
        receipts.append({"page": page, "job_id": res.get("job_id"), "billing": res.get("billing"), "error": interrupted})
        meta = raw.get("meta") or meta
        data = raw.get("data")
        if interrupted or not isinstance(data, list):
            if page == 1:
                return {"ok": False, "error": interrupted or "no_data", "raw_status": res.get("status")}, {"tool": "predictleads_company_job_openings", "pages": receipts, "meta": meta}
            # a failed later page means the listing is incomplete: partial, never "success"
            return ({"jobs": jobs, "retrieved_at": now(), "dropped_after_known_at": dropped, "dropped_undated": undated,
                     "pages_fetched": pages, "status": "partial", "error": interrupted or "no_data_on_page"},
                    {"tool": "predictleads_company_job_openings", "pages": receipts, "meta": meta})
        pages += 1
        for item in data:
            a = item.get("attributes") or {}
            first_seen = a.get("first_seen_at") or a.get("posted_at") or ""
            seen_at = _instant(first_seen) if first_seen else None
            if cutoff is not None:
                if seen_at is None:
                    undated += 1; continue          # cannot prove it existed before the decision date
                if not (seen_at < cutoff):
                    dropped += 1; continue           # strict earlier-than
            jobs.append({"title": a.get("title") or "", "description": a.get("description") or "",
                         "url": a.get("url") or "", "first_seen_at": first_seen, "last_seen_at": a.get("last_seen_at") or "",
                         "location": a.get("location") or ""})
        if checkpoint:  # persist the purchased page and the resume position before the next paid call
            checkpoint({"tool": "predictleads_company_job_openings", "pages": receipts, "meta": meta, "jobs_so_far": jobs,
                        "dropped": dropped, "undated": undated, "pages_fetched": pages, "complete": len(data) < 100})
        if len(data) < 100:
            break
    partial = pages == MAX_JOB_PAGES and (resume.get("last_page_full") if first_page > MAX_JOB_PAGES else len(data) == 100)
    out = {"jobs": jobs, "retrieved_at": now(), "dropped_after_known_at": dropped, "dropped_undated": undated,
           "pages_fetched": pages, "no_active_openings_confirmed": (meta or {}).get("no_active_openings_confirmed")}
    if partial:
        out["status"] = "partial"  # the analyzer reads this envelope status; partial collection cannot prove absence
    return out, {"tool": "predictleads_company_job_openings", "pages": receipts, "meta": meta}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--pages", type=int, default=8)
    p.add_argument("--max-page-chars", type=int, default=MAX_PAGE_CHARS)
    p.add_argument("--poll-seconds", type=int, default=5)
    p.add_argument("--max-wait", type=int, default=240)
    p.add_argument("--limit", type=int, default=None, help="Only collect the first N rows without receipts (budget guard)")
    p.add_argument("--skip-jobs", action="store_true")
    p.add_argument("--skip-website", action="store_true")
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()

    rows = list(csv.DictReader(open(args.input, encoding="utf-8-sig", newline="")))
    receipts_dir = Path(args.output + ".receipts"); receipts_dir.mkdir(parents=True, exist_ok=True)

    def key_of(row: dict) -> tuple[str, str]:
        domain = (row.get("domain") or "").strip().lower().removeprefix("www.")
        return domain, (row.get("known_at") or "").strip()

    def receipt_path(domain: str, known_at: str) -> Path:
        return receipts_dir / (f"{domain}__{known_at.replace(':', '')}.json" if known_at else f"{domain}.json")

    def load_receipt(domain: str, known_at: str) -> dict | None:
        p = receipt_path(domain, known_at)
        if p.exists():
            return json.loads(p.read_text())
        legacy = receipts_dir / f"{domain}.json"  # earlier runs keyed receipts by domain only
        if known_at and legacy.exists():
            rec = json.loads(legacy.read_text())
            if (rec.get("known_at") or "") == known_at:
                return rec
        return None

    def collect_one(domain: str, known_at: str, rec: dict | None) -> dict:
        rec = rec or {"domain": domain, "collected_at": now(), "known_at": known_at or None, "receipts": {}}
        path = receipt_path(domain, known_at)
        def checkpoint(kind):
            def _cp(receipt):
                rec["receipts"][kind] = receipt
                path.write_text(json.dumps(rec))
            return _cp
        if not args.skip_website and "website" not in rec:
            try:
                resume = (rec["receipts"].get("website") or {}).get("provider_job_id")
                site, r = crawl_site(domain, args.pages, args.poll_seconds, args.max_wait, args.max_page_chars,
                                     resume_job=resume, checkpoint=checkpoint("website"))
                if site.get("pending"):
                    rec["website_status"] = "pending"  # crawl id kept in receipts; a rerun polls it instead of buying again
                else:
                    rec["website"] = site
                    rec["website_status"] = ("partial" if site.get("status") == "partial" else "success") if site.get("pages") and site.get("ok", True) else (site.get("error") or "empty")
                rec["receipts"]["website"] = {**(rec["receipts"].get("website") or {}), **r}
            except Exception as exc:  # noqa: BLE001
                rec["website_status"] = "pending" if (rec["receipts"].get("website") or {}).get("provider_job_id") else "error"
                if rec["website_status"] == "error":
                    rec["website"] = {"ok": False, "error": str(exc)[:300]}
                rec["receipts"]["website"] = {**(rec["receipts"].get("website") or {}), "error": str(exc)[:300]}
            path.write_text(json.dumps(rec))  # persist the paid part before starting the next
        if not args.skip_jobs and "jobs" not in rec:
            try:
                jobs, r = job_openings(domain, known_at or None, checkpoint=checkpoint("jobs"), resume=rec["receipts"].get("jobs"))
                rec["jobs"] = jobs; rec["jobs_status"] = ("partial" if jobs.get("status") == "partial" else "success") if jobs.get("ok", True) else (jobs.get("error") or "error")
            except Exception as exc:  # noqa: BLE001
                rec["jobs"] = {"ok": False, "error": str(exc)[:300]}; rec["jobs_status"] = "error"; r = {"error": str(exc)[:300]}
            rec["receipts"]["jobs"] = r
            path.write_text(json.dumps(rec))
        return rec

    def apply(row: dict, rec: dict | None, status: str | None = None) -> None:
        if rec is None:
            row["website"], row["jobs"] = "", ""; row["website_status"] = row["jobs_status"] = status or ""
            return
        row["website"] = json.dumps(rec["website"]) if rec.get("website") is not None else ""
        row["jobs"] = json.dumps(rec["jobs"]) if rec.get("jobs") is not None else ""
        row["website_status"], row["jobs_status"] = rec.get("website_status", ""), rec.get("jobs_status", "")

    complete = lambda rec: rec is not None and (args.skip_website or "website" in rec) and (args.skip_jobs or "jobs" in rec)  # noqa: E731
    tasks: dict[tuple[str, str], dict | None] = {}
    members: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        domain, known_at = key_of(row)
        if not domain:
            apply(row, None, "missing_domain"); continue
        members.setdefault((domain, known_at), []).append(row)
        if (domain, known_at) in tasks:
            continue
        rec = load_receipt(domain, known_at)
        if complete(rec):
            tasks[(domain, known_at)] = rec
        elif args.limit is not None and sum(1 for v in tasks.values() if v is None or not complete(v)) >= args.limit:
            tasks[(domain, known_at)] = {"__skip__": True}
        else:
            tasks[(domain, known_at)] = rec  # None or partial -> collect
    todo = [(k, v) for k, v in tasks.items() if not (v and v.get("__skip__")) and not complete(v)]
    for k, v in tasks.items():
        if v and v.get("__skip__"):
            for row in members[k]: apply(row, None, "not_collected")
        elif complete(v):
            for row in members[k]: apply(row, v)
    done = 0
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(collect_one, k[0], k[1], v): k for k, v in todo}
        for fut in as_completed(futures):
            k = futures[fut]
            try:
                rec = fut.result()
                for row in members[k]: apply(row, rec)
            except Exception as exc:  # noqa: BLE001
                for row in members[k]: apply(row, None, f"error:{str(exc)[:80]}")
            done += 1
            print(f"[{done}/{len(todo)}] {k[0]} website={members[k][0]['website_status']} jobs={members[k][0]['jobs_status']}", flush=True)

    fields = list(rows[0].keys())
    for extra in ("website", "jobs", "website_status", "jobs_status"):
        if extra not in fields:
            fields.append(extra)
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"wrote {args.output} ({done} newly collected, {len(tasks)} unique domain/cutoff keys, receipts in {receipts_dir})")


if __name__ == "__main__":
    main()
