#!/usr/bin/env python3
"""
Two-phase LinkedIn event organizer extraction via Deepline.

Phase 1: Search across multiple keywords → save raw search results CSV
Phase 2: For each event, extract details → organizer name + company URL + individual LinkedIn

No API keys needed. Deepline manages LinkedIn identities.
Requires: deepline CLI authenticated (`deepline auth status`)
"""

import json
import csv
import subprocess
import time
import sys
from pathlib import Path

WORKDIR = Path(__file__).parent

SEARCH_RESULTS_CSV = WORKDIR / "phase1_search_results.csv"
ORGANIZERS_CSV = WORKDIR / "phase2_event_organizers.csv"

TARGET = 100

KEYWORDS = [
    "webinar",
    "virtual+event",
    "online+workshop",
    "live+session",
    "masterclass",
    "virtual+summit",
    "online+training",
    "tech+webinar",
    "business+webinar",
    "startup+webinar",
    "product+demo",
    "panel+discussion",
]


def deepline_execute(tool_id: str, payload: dict, timeout: int = 90) -> dict | list:
    result = subprocess.run(
        [
            "deepline", "tools", "execute", tool_id,
            "--payload", json.dumps(payload),
            "--json",
        ],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        return {"error": result.stderr or result.stdout}
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": result.stdout or result.stderr}


# ── Phase 1: collect search results ──────────────────────────────────────────

def phase1_search() -> list[dict]:
    all_events = []
    seen_ids = set()

    for kw in KEYWORDS:
        if len(all_events) >= TARGET:
            break

        url = (
            f"https://www.linkedin.com/search/results/events/"
            f"?keywords={kw}&origin=SWITCH_SEARCH_VERTICAL"
        )
        print(f"  Keyword '{kw}': {url}")

        result = deepline_execute(
            "linkedin_scraper_linkedin_search_events",
            {"input": {"linkedin_event_search_url": url}},
        )

        # Result may be wrapped in Deepline response envelope
        events = result if isinstance(result, list) else result.get("results", result.get("data", []))
        if not isinstance(events, list):
            print(f"    ERROR: {result.get('error', result)}")
            time.sleep(2)
            continue

        new = 0
        for event in events:
            eid = event.get("linkedin_event_id") or event.get("id")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                location = event.get("location", "")
                event["organizer_company"] = location.split("By ", 1)[1].strip() if "By " in location else ""
                all_events.append(event)
                new += 1

        print(f"    +{new} new unique events (total: {len(all_events)})")
        time.sleep(1.5)

    if not all_events:
        print("No events found.")
        return []

    fieldnames = [
        "linkedin_event_id", "event_name", "linkedin_event_url",
        "date", "location", "organizer_company", "attendees", "description",
    ]
    with open(SEARCH_RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_events)

    print(f"\n✓ Phase 1 done — {len(all_events)} unique events → {SEARCH_RESULTS_CSV}")
    return all_events


# ── Phase 2: extract event detail + organizer LinkedIn ───────────────────────

def extract_event_detail(event_url: str) -> dict:
    result = deepline_execute(
        "linkedin_scraper_linkedin_extract_event",
        {"input": {"linkedin_event_url": event_url}},
    )
    if isinstance(result, dict) and "error" not in result:
        return result
    return {}


def find_linkedin_profile(first_name: str, last_name: str, company_name: str = "") -> str:
    if not first_name.strip() and not last_name.strip():
        return ""
    payload: dict = {"first_name": first_name, "last_name": last_name}
    if company_name:
        payload["company_name"] = company_name
    result = deepline_execute("name_to_linkedin_url_waterfall", payload)
    if isinstance(result, dict):
        return (
            result.get("linkedin")
            or result.get("linkedin_url")
            or result.get("linkedin_profile_url")
            or ""
        )
    return ""


def lookup_company_page(company_name: str) -> tuple[str, str]:
    """Search LinkedIn companies by name, return (company_linkedin_url, website)."""
    if not company_name.strip():
        return "", ""
    import urllib.parse
    search_url = (
        "https://www.linkedin.com/search/results/companies/?keywords="
        + urllib.parse.quote(company_name)
    )
    result = deepline_execute(
        "linkedin_scraper_linkedin_extract_company",
        {"input": {"linkedin_company_url": search_url}},
    )
    if isinstance(result, list) and result:
        first = result[0]
        return first.get("linkedin_company_url") or first.get("url") or "", first.get("website") or ""
    if isinstance(result, dict) and "error" not in result:
        return result.get("linkedin_company_url") or result.get("url") or "", result.get("website") or ""
    return "", ""


PHASE2_FIELDNAMES = [
    "event_name", "event_url", "event_id", "event_date", "attendees",
    "organizer_company",
    "organizer_company_linkedin",
    "organizer_company_website",
    "organizer_full_name",
    "organizer_first_name",
    "organizer_last_name",
    "organizer_individual_linkedin",
    "hosted_by",
]


def phase2_enrich(events: list[dict]):
    with open(ORGANIZERS_CSV, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=PHASE2_FIELDNAMES).writeheader()

    named_count = 0
    company_count = 0

    for i, event in enumerate(events, 1):
        event_url = event.get("linkedin_event_url", "")
        event_name = event.get("event_name", "")
        organizer_company = event.get("organizer_company", "")

        print(f"  [{i}/{len(events)}] {event_name[:65]}")

        detail = extract_event_detail(event_url)

        first_name = detail.get("first_name", "")
        last_name = detail.get("last_name", "")
        full_name = detail.get("full_name", "").strip() or f"{first_name} {last_name}".strip()

        company_linkedin = (
            detail.get("organizer_url")
            or detail.get("company_url")
            or detail.get("organizer_linkedin_url")
            or detail.get("company_linkedin_url")
            or ""
        )
        company_website = detail.get("company_website") or detail.get("organizer_website") or ""

        individual_linkedin = ""

        if full_name:
            individual_linkedin = find_linkedin_profile(first_name, last_name, organizer_company)
            named_count += 1
            hosted_by = "person"
            print(f"    Person: {full_name} @ {organizer_company} → {individual_linkedin or 'not found'}")
        else:
            company_count += 1
            hosted_by = "company"
            if not company_linkedin and organizer_company:
                company_linkedin, company_website = lookup_company_page(organizer_company)
            print(f"    Company: {organizer_company} → {company_linkedin or 'not found'}")

        row = {
            "event_name": event_name,
            "event_url": event_url,
            "event_id": event.get("linkedin_event_id", detail.get("linkedin_event_id", "")),
            "event_date": event.get("date", ""),
            "attendees": event.get("attendees", ""),
            "organizer_company": organizer_company,
            "organizer_company_linkedin": company_linkedin,
            "organizer_company_website": company_website,
            "organizer_full_name": full_name,
            "organizer_first_name": first_name,
            "organizer_last_name": last_name,
            "organizer_individual_linkedin": individual_linkedin,
            "hosted_by": hosted_by,
        }

        with open(ORGANIZERS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=PHASE2_FIELDNAMES).writerow(row)

        time.sleep(0.8)

    print(f"\n✓ Phase 2 done — {len(events)} rows → {ORGANIZERS_CSV}")
    print(f"  {named_count} personal-hosted  |  {company_count} company-hosted")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    skip_phase1 = "--skip-search" in sys.argv

    if skip_phase1 and SEARCH_RESULTS_CSV.exists():
        print("Loading existing phase 1 results...")
        with open(SEARCH_RESULTS_CSV, newline="", encoding="utf-8") as f:
            events = list(csv.DictReader(f))
        print(f"  Loaded {len(events)} events")
    else:
        print("=== Phase 1: Searching LinkedIn events ===")
        events = phase1_search()
        if not events:
            return

    print(f"\n=== Phase 2: Extracting organizer details ({len(events)} events) ===")
    phase2_enrich(events)


if __name__ == "__main__":
    main()
