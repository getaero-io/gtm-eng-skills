"""Offline observation gate. No crawling, signature discovery or use confirmation.

Usage: python3 technology_evidence.py normalized-observations.json
Input is a JSON list conforming to references/technology-evidence.md.
Output deliberately omits raw URLs, snippets and unrecognized fields.
"""
import ipaddress
import json
import re
import sys
from datetime import datetime
from urllib.parse import urlsplit


def host(url):
    if not isinstance(url, str) or re.search(r"[\s\\]", url):
        raise ValueError("Invalid public URL")
    p = urlsplit(url)
    if p.scheme not in ("https", "http") or p.username or p.password:
        raise ValueError("Only public HTTP(S) URLs without userinfo")
    h = (p.hostname or "").rstrip(".").lower()
    # Deliberately conservative. This is not a network/SSRF authorization gate.
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", h) or "." not in h:
        raise ValueError("Invalid hostname")
    if any(not label or label.startswith("-") or label.endswith("-") for label in h.split(".")):
        raise ValueError("Invalid hostname")
    try:
        ipaddress.ip_address(h)
    except ValueError:
        return h
    raise ValueError("IP addresses are not vendor domains")


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
        raise ValueError("Expected an opaque identifier")
    return value


def classify(row):
    if not isinstance(row, dict):
        raise ValueError("Expected observation object")
    account = identifier(row["account_id"])
    component = identifier(row["component_id"])
    stamp = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Timestamp must have timezone")
    page_host = host(row["page_url"])
    kind = row["kind"]
    if kind not in {"mention", "public_link", "embedded", "snippet", "network"}:
        raise ValueError("Unsupported observation kind")
    signature = identifier(row["signature_id"])
    signature_host = host(row["signature_source"])
    level = {"mention": "mention_only", "snippet": "snippet_candidate"}.get(kind)
    resource_host = None
    if level is None:
        resource_host = host(row["resource_url"])
        vendor_domain = row["vendor_domain"]
        if not isinstance(vendor_domain, str) or host("https://" + vendor_domain) != vendor_domain:
            raise ValueError("Expected canonical lowercase vendor domain")
        matches = resource_host == vendor_domain or resource_host.endswith("." + vendor_domain)
        if not matches:
            level = "unmatched_domain"
        elif kind == "network":
            status = row.get("status")
            if status is not None and (type(status) is not int or not 100 <= status <= 599):
                raise ValueError("Invalid HTTP status")
            level = "requested" if status is None else (
                "response_observed" if 200 <= status < 300 else "failed_request"
            )
            # Redirects/cache responses need their own contextual review.
        else:
            level = "public_link" if kind == "public_link" else "embedded_reference"
    return {
        "account_id": account, "component_id": component,
        "observed_at": stamp.isoformat(), "page_host": page_host,
        "signature_id": signature, "signature_source_host": signature_host,
        "resource_host": resource_host, "level": level,
        "scoring_eligible": False, "contract_verified": False,
    }


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        raise ValueError("Input must be a list")
    result = [classify(row) for row in rows]  # Validate everything before printing.
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
