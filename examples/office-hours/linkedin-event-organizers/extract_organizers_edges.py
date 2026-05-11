#!/usr/bin/env python3
"""
Two-phase LinkedIn event organizer extraction using Edges managed identity API.

Phase 1: Search across multiple keywords → save raw search results CSV (playground)
Phase 2: For each event, extract details → organizer name + company URL + individual LinkedIn
"""

import json
import os
import csv
import subprocess
import time
import sys
from pathlib import Path

EDGES_API_KEY = os.environ["EDGES_API_KEY"]
EDGES_API_BASE = "https://api.edges.run/v1/actions"
WORKDIR = Path(__file__).parent

SEARCH_RESULTS_CSV = WORKDIR / "phase1_search_results.csv"
ORGANIZERS_CSV = WORKDIR / "phase2_event_organizers.csv"

TARGET = 100

# Different keywords to diversify results across managed sessions
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


def edges_post(action: str, input_data: dict, timeout: int = 60) -> dict | list:
    url = f"{EDGES_API_BASE}/{action}/run/live"
    body = json.dumps({"identity_mode": "managed", "input": input_data})
    result = subprocess.run(
        [
            "curl", "-s", "--request", "POST",
            "--url", url,
            "--header", f"X-API-Key: {EDGES_API_KEY}",
            "--header", "Content-Type: application/json",
            "--header", "Accept: application/json",
            "--data", body,
        ],
        capture_output=True, text=True, timeout=timeout,
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": result.stdout or result.stderr}


def get_credits_left() -> float:
    result = subprocess.run(
        ["curl", "-s", "--request", "GET",
         "--url", "https://api.edges.run/v1/workspaces",
         "--header", f"X-API-Key: {EDGES_API_KEY}"],
        capture_output=True, text=True, timeout=15,
    )
    try:
        return json.loads(result.stdout).get("credits_left", 0)
    except Exception:
        return 0


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
        result = edges_post("linkedin-search-events", {"url": url})

        if not isinstance(result, list):
            print(f"    ERROR: {result.get('message', result)}")
            time.sleep(2)
            continue

        new = 0
        for event in result:
            eid = event.get("linkedin_event_id")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                location = event.get("location", "")
                event["organizer_company"] = location.split("By ", 1)[1].strip() if "By " in location else ""
                all_events.append(event)
                new += 1

        print(f"    +{new} new unique events (total: {len(all_events)})")
        time.sleep(1.5)

    # Write phase 1 CSV
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
    result = edges_post("linkedin-extract-event", {"linkedin_event_url": event_url})
    if isinstance(result, dict) and "error" not in result and "error_label" not in result:
        return result
    return {}


def find_linkedin_profile(full_name: str, company: str = "") -> str:
    if not full_name.strip():
        return ""
    payload = {"full_name": full_name}
    if company:
        payload["company_name"] = company
    result = edges_post("linkedin-find-profile-url", payload)
    if isinstance(result, dict):
        return (
            result.get("linkedin_profile_url")
            or result.get("url")
            or result.get("profile_url")
            or ""
        )
    return ""


PHASE2_FIELDNAMES = [
    "event_name", "event_url", "event_id", "event_date", "attendees",
    "organizer_company",             # display name parsed from search result location field
    "organizer_company_linkedin",    # company LinkedIn page URL (all events)
    "organizer_company_website",     # company website (all events)
    "organizer_full_name",           # individual name (personal-hosted events only)
    "organizer_first_name",
    "organizer_last_name",
    "organizer_individual_linkedin", # individual LinkedIn URL (personal-hosted only)
    "hosted_by",                     # "person" or "company"
]


def lookup_company_linkedin(company_name: str) -> tuple[str, str]:
    """Return (company_linkedin_url, company_website) by searching LinkedIn companies by name."""
    if not company_name.strip():
        return "", ""
    import urllib.parse
    search_url = (
        "https://www.linkedin.com/search/results/companies/?keywords="
        + urllib.parse.quote(company_name)
    )
    result = edges_post("linkedin-search-companies", {"url": search_url}, timeout=90)
    # Returns a list of company results; take the first match
    if isinstance(result, list) and result:
        first = result[0]
        linkedin = first.get("linkedin_company_url") or first.get("url") or ""
        website = first.get("website") or ""
        return linkedin, website
    return "", ""


def phase2_enrich(events: list[dict]):
    # Write header once
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

        # Company URL from event detail endpoint (present on some events)
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
            # Personal-hosted event — look up individual profile
            individual_linkedin = find_linkedin_profile(full_name, organizer_company)
            named_count += 1
            hosted_by = "person"
            print(f"    Person: {full_name} @ {organizer_company} → {individual_linkedin or 'not found'}")
            # Company URL comes from Apify in the validation pass; skip lookup here
        else:
            # Company-hosted event — look up company LinkedIn page
            company_count += 1
            hosted_by = "company"
            if not company_linkedin and organizer_company:
                company_linkedin, company_website = lookup_company_linkedin(organizer_company)
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
    print(f"  {named_count} personal-hosted events (individual organizer found)")
    print(f"  {company_count} company-hosted events (company page logged)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    skip_phase1 = "--skip-search" in sys.argv

    credits_before = get_credits_left()
    print(f"Credits available: {credits_before:,.0f}\n")

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

    credits_after = get_credits_left()
    spent = credits_before - credits_after
    cost_usd = spent * 19.35 / 1000
    print(f"\nCredits spent: {spent:.1f} (~${cost_usd:.2f} at $19.35/1K)")
    print(f"Credits remaining: {credits_after:,.0f}")


if __name__ == "__main__":
    main()
