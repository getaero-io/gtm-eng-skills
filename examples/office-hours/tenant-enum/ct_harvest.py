#!/usr/bin/env python3
"""
ct_harvest.py — Harvest confirmed SaaS tenants via subdomain enumeration.

Primary:  subfinder (50+ passive DNS/CT sources) → httpx (concurrent HTTP probe)
Fallback: crt.sh JSON API → crt.sh postgres

Requirements (primary path):
    brew install subfinder httpx

Usage:
    python3 ct_harvest.py --list
    python3 ct_harvest.py --platform zendesk --output zendesk_tenants.csv
    python3 ct_harvest.py --platform jamf atlassian --output results.csv
    python3 ct_harvest.py --platform all --output all_tenants.csv
    python3 ct_harvest.py --crtsh --platform zendesk   # force crt.sh fallback
"""

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, fields
from typing import Iterator
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------

@dataclass
class Platform:
    label: str
    root_domain: str
    slug_suffix: str
    login_url_template: str
    httpx_match_codes: str          # comma-separated HTTP codes that mean "live"
    final_url_fragment: str = ""    # secondary check for wildcard platforms
    filter_slug_re: str = ""
    notes: str = ""


PLATFORMS: dict[str, Platform] = {
    "zendesk": Platform(
        label="Zendesk", root_domain="zendesk.com", slug_suffix=".zendesk.com",
        login_url_template="https://{slug}.zendesk.com",
        httpx_match_codes="200",
        notes="200=live, 403=ghost.",
    ),
    "freshdesk": Platform(
        label="Freshdesk", root_domain="freshdesk.com", slug_suffix=".freshdesk.com",
        login_url_template="https://{slug}.freshdesk.com",
        httpx_match_codes="301,302",
        notes="302=live, 404=ghost.",
    ),
    "salesforce": Platform(
        label="Salesforce", root_domain="my.salesforce.com", slug_suffix=".my.salesforce.com",
        login_url_template="https://{slug}.my.salesforce.com",
        httpx_match_codes="200",
        notes="200=live.",
    ),
    "atlassian": Platform(
        label="Atlassian", root_domain="atlassian.net", slug_suffix=".atlassian.net",
        login_url_template="https://{slug}.atlassian.net",
        httpx_match_codes="200",
        notes="200=live, 404=ghost.",
    ),
    "servicenow": Platform(
        label="ServiceNow", root_domain="service-now.com", slug_suffix=".service-now.com",
        login_url_template="https://{slug}.service-now.com",
        httpx_match_codes="200",
        filter_slug_re=r"^(dev\d+|demo|training|sandbox|test|uat|stage|preprod|pd)",
        notes="Filter dev\\d+ slugs (free instances).",
    ),
    "salesloft": Platform(
        label="Salesloft", root_domain="salesloft.com", slug_suffix=".salesloft.com",
        login_url_template="https://{slug}.salesloft.com",
        httpx_match_codes="200",
        notes="200=live.",
    ),
    "pagerduty": Platform(
        label="PagerDuty", root_domain="pagerduty.com", slug_suffix=".pagerduty.com",
        login_url_template="https://{slug}.pagerduty.com",
        httpx_match_codes="200,401,403,405",
        notes="405=live (real subdomains reject HEAD).",
    ),
    "bamboohr": Platform(
        label="BambooHR", root_domain="bamboohr.com", slug_suffix=".bamboohr.com",
        login_url_template="https://{slug}.bamboohr.com",
        httpx_match_codes="200",
        notes="Wildcard DNS. subfinder enumeration gives the tenant list.",
    ),
    "workday": Platform(
        label="Workday", root_domain="myworkday.com", slug_suffix=".myworkday.com",
        login_url_template="https://{slug}.myworkday.com",
        httpx_match_codes="200,301,302",
        notes="External DNS often blocks probes; subfinder passive enumeration is reliable.",
    ),
    "outreach": Platform(
        label="Outreach", root_domain="outreach.io", slug_suffix=".outreach.io",
        login_url_template="https://{slug}.outreach.io",
        httpx_match_codes="200,301,302",
        notes="DNS blocks external probes; subfinder finds slugs passively.",
    ),
    "gong": Platform(
        label="Gong", root_domain="app.gong.io", slug_suffix=".app.gong.io",
        login_url_template="https://{slug}.app.gong.io",
        httpx_match_codes="200",
        notes="Wildcard DNS.",
    ),
    "monday": Platform(
        label="Monday.com", root_domain="monday.com", slug_suffix=".monday.com",
        login_url_template="https://{slug}.monday.com",
        httpx_match_codes="200,301,302",
        notes="Wildcard DNS.",
    ),
    "hubspot": Platform(
        label="HubSpot (pages)", root_domain="hs-sites.com", slug_suffix=".hs-sites.com",
        login_url_template="https://{slug}.hs-sites.com",
        httpx_match_codes="200",
        notes="Tenant landing pages on hs-sites.com.",
    ),
    "netsuite": Platform(
        label="Oracle NetSuite", root_domain="netsuite.com", slug_suffix=".app.netsuite.com",
        login_url_template="https://{slug}.app.netsuite.com",
        httpx_match_codes="200,301,302",
        notes="Numeric account IDs. Company name is in cert CN.",
    ),
    "greenhouse": Platform(
        label="Greenhouse", root_domain="greenhouse.io", slug_suffix=".greenhouse.io",
        login_url_template="https://job-boards.greenhouse.io/{slug}",
        httpx_match_codes="200,301,302",
        notes="Path-based ATS. subfinder finds greenhouse.io subdomains; check job-boards path.",
    ),
    "datadog": Platform(
        label="Datadog", root_domain="datadoghq.com", slug_suffix=".datadoghq.com",
        login_url_template="https://{slug}.datadoghq.com",
        httpx_match_codes="200,301,302",
        notes="Subfinder enumerates.",
    ),
    # Wildcard platforms — secondary URL check required
    "jamf": Platform(
        label="Jamf Cloud", root_domain="jamfcloud.com", slug_suffix=".jamfcloud.com",
        login_url_template="https://{slug}.jamfcloud.com",
        httpx_match_codes="200",
        final_url_fragment="/view/sso/login",
        filter_slug_re=r"(\.internal\.|\.alb\.|\.sbox\.|jenkins|jnks)",
        notes="Wildcard DNS. Real tenants: final URL has /view/sso/login. "
              "Ran 2026-05-07: 11,913 subs → 436 confirmed tenants.",
    ),
}


@dataclass
class Tenant:
    platform: str
    slug: str
    subdomain: str
    login_url: str
    confirmed: str   # "yes" | "crtsh_unprobed"
    source: str      # "subfinder" | "crtsh_json" | "crtsh_postgres"


# ---------------------------------------------------------------------------
# subfinder + httpx (primary)
# ---------------------------------------------------------------------------

def _has(name: str) -> bool:
    return shutil.which(name) is not None


def _subfinder(root_domain: str, threads: int = 10, timeout: int = 300) -> list[str]:
    cmd = ["subfinder", "-d", root_domain, "-silent", "-t", str(threads), "-timeout", str(timeout)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * 2)
        return [l.strip().lower() for l in result.stdout.splitlines() if l.strip()]
    except Exception as e:
        print(f"  [subfinder error] {e}", file=sys.stderr)
        return []


def _httpx(urls: list[str], match_codes: str, threads: int = 100, timeout: int = 8) -> set[str]:
    if not urls:
        return set()
    # -fr = follow redirects (critical: without this, platforms that 302 before
    # 200 are missed entirely — Jamf, Salesforce, Freshdesk all do this)
    cmd = ["httpx", "-mc", match_codes, "-fr", "-silent", "-threads", str(threads), "-timeout", str(timeout)]
    try:
        proc = subprocess.run(cmd, input="\n".join(urls), capture_output=True, text=True, timeout=max(timeout * 3, 120))
        return {l.strip() for l in proc.stdout.splitlines() if l.strip()}
    except Exception as e:
        print(f"  [httpx error] {e}", file=sys.stderr)
        return set()


def _final_url_check(url: str, fragment: str, timeout: int = 8) -> bool:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="HEAD")
    try:
        with urlopen(req, timeout=timeout) as r:
            return fragment in r.url
    except HTTPError as e:
        return fragment in e.headers.get("Location", "")
    except (URLError, OSError):
        return False


def harvest_subfinder(platform_key: str, sf_threads: int = 10, httpx_threads: int = 100) -> Iterator[Tenant]:
    p = PLATFORMS[platform_key]
    filter_re = re.compile(p.filter_slug_re, re.I) if p.filter_slug_re else None

    print(f"  [subfinder] enumerating {p.root_domain}...", file=sys.stderr)
    all_subs = _subfinder(p.root_domain, threads=sf_threads)
    print(f"  [subfinder] {len(all_subs)} subdomains found", file=sys.stderr)

    clean: list[tuple[str, str]] = []
    for sub in all_subs:
        if not sub.endswith(p.slug_suffix):
            continue
        slug = sub[: -len(p.slug_suffix)]
        if not slug or "." in slug:
            continue
        if filter_re and filter_re.search(slug):
            continue
        clean.append((slug, f"https://{sub}"))

    print(f"  [subfinder] {len(clean)} clean slug candidates", file=sys.stderr)

    live_urls = _httpx([url for _, url in clean], p.httpx_match_codes, threads=httpx_threads)
    print(f"  [httpx -fr] {len(live_urls)} matched HTTP {p.httpx_match_codes}", file=sys.stderr)

    seen: set[str] = set()
    for slug, url in clean:
        if url not in live_urls or slug in seen:
            continue
        seen.add(slug)
        if p.final_url_fragment and not _final_url_check(url, p.final_url_fragment):
            continue
        yield Tenant(
            platform=p.label, slug=slug, subdomain=f"{slug}{p.slug_suffix}",
            login_url=p.login_url_template.format(slug=slug),
            confirmed="yes", source="subfinder",
        )


# ---------------------------------------------------------------------------
# crt.sh fallback
# ---------------------------------------------------------------------------

def _crtsh_json(domain: str) -> list[dict] | None:
    wildcard = f"%.{domain}"
    url = "https://crt.sh/?" + urlencode({"q": wildcard, "output": "json", "deduplicate": "Y"})
    req = Request(url, headers={"User-Agent": "ct-harvest/2.0"})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else []
        except HTTPError as e:
            if e.code in (429, 503):
                time.sleep(10 * (attempt + 1))
                continue
            if e.code in (500, 502, 504):
                return None
            return []
        except (URLError, json.JSONDecodeError):
            return None
    return None


def harvest_crtsh(platform_key: str) -> Iterator[Tenant]:
    p = PLATFORMS[platform_key]
    filter_re = re.compile(p.filter_slug_re, re.I) if p.filter_slug_re else None

    print(f"  [crt.sh] querying {p.root_domain}...", file=sys.stderr)
    rows = _crtsh_json(p.root_domain)
    source = "crtsh_json"
    if rows is None:
        print("  [crt.sh] JSON API down — install subfinder+httpx for primary path", file=sys.stderr)
        return

    print(f"  [crt.sh] {len(rows)} certs", file=sys.stderr)
    seen: set[str] = set()
    for row in rows:
        for raw_san in (row.get("name_value", "") or "").splitlines():
            raw_san = raw_san.strip().lower()
            if not raw_san or raw_san.startswith("*"):
                continue
            if not raw_san.endswith(p.slug_suffix):
                continue
            slug = raw_san[: -len(p.slug_suffix)]
            if not slug or "." in slug or slug in seen:
                continue
            if filter_re and filter_re.search(slug):
                continue
            seen.add(slug)
            yield Tenant(
                platform=p.label, slug=slug, subdomain=raw_san,
                login_url=p.login_url_template.format(slug=slug),
                confirmed="crtsh_unprobed", source=source,
            )


# ---------------------------------------------------------------------------
# Dispatcher + CLI
# ---------------------------------------------------------------------------

def harvest_platform(platform_key: str, force_crtsh: bool = False, sf_threads: int = 10, httpx_threads: int = 100) -> Iterator[Tenant]:
    if not force_crtsh and _has("subfinder") and _has("httpx"):
        print(f"  [mode] subfinder + httpx -fr", file=sys.stderr)
        yield from harvest_subfinder(platform_key, sf_threads=sf_threads, httpx_threads=httpx_threads)
    else:
        if not force_crtsh:
            missing = [t for t, ok in [("subfinder", _has("subfinder")), ("httpx", _has("httpx"))] if not ok]
            print(f"  [mode] crt.sh fallback (missing: {', '.join(missing)})", file=sys.stderr)
            print(f"  [tip]  brew install subfinder httpx", file=sys.stderr)
        else:
            print(f"  [mode] crt.sh (--crtsh flag)", file=sys.stderr)
        yield from harvest_crtsh(platform_key)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harvest SaaS tenants via subfinder+httpx (primary) or crt.sh (fallback).\n"
                    "Install primary: brew install subfinder httpx",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--platform", nargs="+", choices=[*PLATFORMS.keys(), "all"], default=["zendesk"])
    parser.add_argument("--output", default="tenants.csv")
    parser.add_argument("--crtsh", action="store_true", help="Force crt.sh fallback.")
    parser.add_argument("--sf-threads", type=int, default=10)
    parser.add_argument("--httpx-threads", type=int, default=100)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        sf_ok, hx_ok = _has("subfinder"), _has("httpx")
        print(f"\nMode: {'subfinder+httpx ✓' if (sf_ok and hx_ok) else 'crt.sh fallback'}")
        if not sf_ok: print("  Install: brew install subfinder")
        if not hx_ok: print("  Install: brew install httpx")
        print(f"\n{'Key':<14} {'Label':<25} {'Root domain'}")
        print("-" * 60)
        for k, p in PLATFORMS.items():
            print(f"{k:<14} {p.label:<25} {p.root_domain}")
        return

    platforms = list(PLATFORMS.keys()) if "all" in args.platform else args.platform
    col_names = [f.name for f in fields(Tenant)]
    total = 0

    print(f"Harvesting: {', '.join(platforms)}", file=sys.stderr)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=col_names)
        writer.writeheader()
        for pname in platforms:
            print(f"\n[{pname}]", file=sys.stderr)
            count = 0
            for tenant in harvest_platform(pname, force_crtsh=args.crtsh, sf_threads=args.sf_threads, httpx_threads=args.httpx_threads):
                writer.writerow({field: getattr(tenant, field) for field in col_names})
                count += 1
                if count % 200 == 0:
                    print(f"  … {count} tenants", file=sys.stderr)
            print(f"  total: {count} tenants", file=sys.stderr)
            total += count

    print(f"\nDone. {total} total tenants → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
