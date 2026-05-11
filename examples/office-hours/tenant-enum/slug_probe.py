#!/usr/bin/env python3
"""
slug_probe.py — Generate tenant slug candidates from a company domain/name
and HTTP-probe each platform fingerprint to confirm a live tenant.

Usage:
    # Single company
    python3 slug_probe.py --domain shopify.com --company "Shopify" \
        --platforms zendesk salesforce atlassian

    # CSV of companies (needs 'domain' column, optional 'company_name')
    python3 slug_probe.py --csv companies.csv \
        --platforms probeable \
        --output confirmed_tenants.csv

    # List all supported platforms
    python3 slug_probe.py --list
"""

import argparse
import csv
import re
import socket
import sys
import time
import urllib.request
from dataclasses import dataclass, fields
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

# Strips common legal suffixes from the end of a domain prefix.
# "sonomainc" handles the specific case of williams-sonomainc.com → williams-sonoma
_LEGAL = re.compile(
    r"[-.]?(inc|corp|llc|ltd|co|group|holdings|international|intl|"
    r"technologies?|solutions|services|systems|global|enterprises?|"
    r"partners|consulting|advisors|plc|sa|srl|sonomainc|brandco|inc)$",
    re.I,
)


def domain_to_slugs(domain: str, company_name: str = "") -> list[str]:
    """Return up to 5 slug candidates, most likely first.

    Priority: domain prefix > company name hyphenated > no-separator > acronym.
    Domain prefix wins because it's what the company typed at provisioning time.
    """
    candidates: list[str] = []

    base = domain.lower().split(".")[0]
    base = base.encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9-]", "", base)
    cleaned = _LEGAL.sub("", base).strip("-")
    for s in (cleaned, base):
        if s and len(s) >= 2 and s not in candidates:
            candidates.append(s)

    if company_name:
        name = company_name.encode("ascii", "ignore").decode().lower()
        name = re.sub(
            r"\b(inc\.?|corp\.?|llc\.?|ltd\.?|co\.?|plc\.?|s\.a\.?|"
            r"group|holdings|international|technologies?|solutions|"
            r"services|systems|global|enterprises?|partners)\b",
            " ", name,
        ).strip()
        slug_h = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
        slug_n = re.sub(r"[^a-z0-9]+", "", name)
        words = [w for w in re.split(r"[^a-z0-9]+", name) if len(w) > 1]
        acronym = "".join(w[0] for w in words) if len(words) >= 3 else ""
        for s in (slug_h, slug_n, acronym):
            if s and len(s) >= 2 and s not in candidates:
                candidates.append(s)

    return candidates[:5]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_UA = "Mozilla/5.0"
_TIMEOUT = 8


def _head(url: str) -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return r.status, r.url, ""
    except HTTPError as e:
        return e.code, "", e.headers.get("Location", "")
    except (URLError, OSError):
        return 0, "", ""


def _dns(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return True
    except (socket.gaierror, OSError):
        return False


# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------

@dataclass
class Platform:
    label: str
    url_template: str
    probe_method: str   # "http_200" | "http_302" | "http_fragment" | "http_405" | "dns" | "crt_only"
    fragment: str = ""
    filter_slug_re: str = ""
    notes: str = ""

    def probe(self, slug: str) -> bool:
        url = self.url_template.format(slug=slug)
        if self.probe_method == "crt_only":
            return False

        if self.probe_method in ("http_200", "http_302"):
            code, _, _ = _head(url)
            return code == 200 if self.probe_method == "http_200" else code in (301, 302)

        if self.probe_method == "http_405":
            code, _, _ = _head(url)
            return code in (200, 401, 403, 405)

        if self.probe_method == "http_fragment":
            _, final_url, loc = _head(url)
            return self.fragment in final_url or self.fragment in loc

        if self.probe_method == "dns":
            host = url.replace("https://", "").split("/")[0]
            return _dns(host)

        return False

    def login_url(self, slug: str) -> str:
        return self.url_template.format(slug=slug)


# Fingerprints verified by live testing (2026-05-07).
# See platforms.md for full truth table and test pairs.
PLATFORMS: dict[str, Platform] = {
    "salesforce": Platform(
        label="Salesforce", url_template="https://{slug}.my.salesforce.com",
        probe_method="http_200",
        notes="200=live, 404=ghost. Verified: uber, amazon, walmart.",
    ),
    "zendesk": Platform(
        label="Zendesk", url_template="https://{slug}.zendesk.com",
        probe_method="http_200",
        notes="200=live, 403=ghost. Verified: shopify, slack, box.",
    ),
    "freshdesk": Platform(
        label="Freshdesk", url_template="https://{slug}.freshdesk.com",
        probe_method="http_302",
        notes="302=live, 404=ghost. Verified: shopify, panasonic.",
    ),
    "jamf": Platform(
        label="Jamf Cloud", url_template="https://{slug}.jamfcloud.com",
        probe_method="http_fragment", fragment="/view/sso/login",
        filter_slug_re=r"(\.internal\.|\.alb\.|\.sbox\.|jenkins|jnks)",
        notes="Wildcard DNS — all slugs 200. Real tenants: final URL has /view/sso/login. "
              "Verified: ibm, pointclickcare, stanford, github, spotify.",
    ),
    "atlassian": Platform(
        label="Atlassian", url_template="https://{slug}.atlassian.net",
        probe_method="http_200",
        notes="200=live, 404=ghost. Verified: netflix, nasa, spotify, visa.",
    ),
    "servicenow": Platform(
        label="ServiceNow", url_template="https://{slug}.service-now.com",
        probe_method="http_200",
        filter_slug_re=r"^(dev\d+|demo|training|sandbox|test|uat|stage|preprod|pd)",
        notes="200=live. Filter dev\\d+ slugs (free instances). Verified: nasdaq, cisco.",
    ),
    "salesloft": Platform(
        label="Salesloft", url_template="https://{slug}.salesloft.com",
        probe_method="http_200",
        notes="200=live, DNS NXDOMAIN=ghost. Verified: zoom.",
    ),
    "pagerduty": Platform(
        label="PagerDuty", url_template="https://{slug}.pagerduty.com",
        probe_method="http_405",
        notes="405=live (real subdomains reject HEAD). Verified: netflix, airbnb, stripe.",
    ),
    "greenhouse": Platform(
        label="Greenhouse", url_template="https://job-boards.greenhouse.io/{slug}",
        probe_method="http_200",
        notes="Path-based. 200=live, 404=ghost. Verified: stripe, hubspot.",
    ),
    # --- crt.sh-only (wildcard DNS, HTTP probe unreliable) ---
    "workday": Platform(
        label="Workday", url_template="https://{slug}.myworkday.com",
        probe_method="crt_only",
        notes="Use ct_harvest.py --platform workday",
    ),
    "bamboohr": Platform(
        label="BambooHR", url_template="https://{slug}.bamboohr.com",
        probe_method="crt_only",
        notes="Use ct_harvest.py --platform bamboohr",
    ),
    "outreach": Platform(
        label="Outreach", url_template="https://{slug}.outreach.io",
        probe_method="crt_only",
        notes="Use ct_harvest.py --platform outreach",
    ),
}


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

@dataclass
class Result:
    domain: str
    company_name: str
    platform: str
    slug_tried: str
    login_url: str
    confirmed: str
    probe_method: str
    all_slugs_tried: str


def find_tenant(domain: str, company_name: str, platform_key: str, rate_limit: float = 0.3) -> Result:
    p = PLATFORMS[platform_key]
    filter_re = re.compile(p.filter_slug_re, re.I) if p.filter_slug_re else None
    slugs = domain_to_slugs(domain, company_name)

    result = Result(
        domain=domain, company_name=company_name, platform=p.label,
        slug_tried="", login_url="", confirmed="no",
        probe_method=p.probe_method, all_slugs_tried=",".join(slugs),
    )

    if p.probe_method == "crt_only":
        result.confirmed = "crt_only"
        return result

    for slug in slugs:
        if filter_re and filter_re.search(slug):
            continue
        time.sleep(rate_limit)
        if p.probe(slug):
            result.slug_tried = slug
            result.login_url = p.login_url(slug)
            result.confirmed = "yes"
            return result

    result.slug_tried = slugs[0] if slugs else ""
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Probe SaaS tenant subdomains.")
    parser.add_argument("--domain", help="Single company domain.")
    parser.add_argument("--company", default="", help="Company name (improves slug generation).")
    parser.add_argument(
        "--platforms", nargs="+",
        choices=[*PLATFORMS.keys(), "all", "probeable"],
        default=["zendesk"],
    )
    parser.add_argument("--csv", help="Input CSV with 'domain' column.")
    parser.add_argument("--output", default="confirmed_tenants.csv")
    parser.add_argument("--rate-limit", type=float, default=0.3)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'Key':<14} {'Label':<30} {'Method':<16} Notes")
        print("-" * 80)
        for k, p in PLATFORMS.items():
            print(f"{k:<14} {p.label:<30} {p.probe_method:<16} {p.notes[:40]}")
        return

    if "all" in args.platforms:
        platforms = list(PLATFORMS.keys())
    elif "probeable" in args.platforms:
        platforms = [k for k, p in PLATFORMS.items() if p.probe_method != "crt_only"]
    else:
        platforms = args.platforms

    if args.domain:
        rows = [{"domain": args.domain, "company_name": args.company}]
    elif args.csv:
        with open(args.csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        parser.error("Provide --domain or --csv")
        return

    col_names = [f.name for f in fields(Result)]
    total = 0
    with open(args.output, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=col_names)
        writer.writeheader()
        for row in rows:
            domain = row.get("domain", "").strip()
            company = row.get("company_name", "").strip()
            if not domain:
                continue
            for pkey in platforms:
                result = find_tenant(domain, company, pkey, args.rate_limit)
                writer.writerow({f: getattr(result, f) for f in col_names})
                icon = "✓" if result.confirmed == "yes" else ("~" if result.confirmed == "crt_only" else "✗")
                print(f"  {icon} {domain:<30} {pkey:<14} {result.login_url or result.slug_tried}", file=sys.stderr)
                if result.confirmed == "yes":
                    total += 1

    print(f"\nDone. {total} confirmed tenants → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
