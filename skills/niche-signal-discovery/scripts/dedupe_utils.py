#!/usr/bin/env python3
"""
Deduplication utilities for niche-signal-discovery prospect lists.

Primary match: apex-domain (public-suffix-aware, handles multi-label TLDs).
Fallback match: fuzzy company name (after stripping corporate suffixes).

The standard library only — no pip dependencies. `difflib.SequenceMatcher`
is used for the fuzzy name ratio so this runs anywhere Python 3 does.

Usage from another script:

    from dedupe_utils import extract_apex, norm_name, match_against_existing

    existing = load_existing_csv("customers.csv")   # rows with 'domain' or 'name'
    candidates = load_candidates("prospects.csv")   # rows with 'domain' and 'name'
    actionable, matched = match_against_existing(candidates, existing, name_threshold=0.85)

Usage from the command line:

    python3 dedupe_utils.py \\
        --existing customers.csv \\
        --candidates prospects.csv \\
        --out-actionable net_new.csv \\
        --out-matched already_known.csv

Why this exists:
  - Raw string match misses parent-company relationships. amsynergy.nikon.com
    and nikon.com refer to the same buyer-side organization, but a naive set
    lookup treats them as unrelated.
  - Name matching alone is noisy: a candidate named "Rocket Propulsion Systems"
    can collide with an unrelated CRM row named "Rocket Propulsion" as a
    substring. Apex domain is a stronger primary key when it's available.
  - The fix is a layered check: match on apex domain first (strong signal),
    then fall back to normalized fuzzy name match with a high threshold only
    when no domain match exists.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from difflib import SequenceMatcher
from typing import Iterable, Sequence
from urllib.parse import urlparse


# ----------------------------------------------------------------------
# Apex domain extraction
# ----------------------------------------------------------------------

# A curated list of multi-label public suffixes that show up often in B2B
# datasets. This is NOT a complete public-suffix-list dump — a production
# system should use `tldextract` — but it covers the countries that have
# appeared in real runs (US, UK, JP, KR, AU, DE, BR, CN, etc).
MULTI_LABEL_SUFFIXES: set[str] = {
    # United Kingdom
    "co.uk", "org.uk", "ac.uk", "gov.uk", "ltd.uk", "plc.uk", "net.uk",
    # Japan
    "co.jp", "ac.jp", "or.jp", "go.jp", "ne.jp",
    # Korea
    "co.kr", "ac.kr", "go.kr", "or.kr", "re.kr",
    # Australia / New Zealand
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.nz", "ac.nz",
    # Brazil / China / India / Israel / South Africa
    "com.br", "com.cn", "net.cn", "co.il", "co.in", "ac.in", "edu.in",
    "co.za", "ac.za",
    # Europe — country-specific commercial
    "co.it", "co.es", "com.es",
    # APAC / LATAM misc
    "com.mx", "edu.mx", "org.mx",
    "com.hk", "com.sg", "com.tr", "com.tw", "com.ar", "com.co", "com.pe",
    "com.ph", "com.my", "com.pk", "com.eg", "com.sa", "com.ua", "com.vn",
    "co.th",
}


def extract_apex(url_or_host: str) -> str:
    """Normalize a URL or bare hostname to its registrable apex domain.

    Returns an empty string when the input can't be parsed into something
    that looks like a domain (empty input, IP literal, obvious garbage).
    This is intentional — downstream code should treat "" as "skip this
    row" rather than as a valid apex.

    Examples:
        extract_apex("amsynergy.nikon.com") -> "nikon.com"
        extract_apex("industry.nikon.com") -> "nikon.com"
        extract_apex("nikon.co.jp") -> "nikon.co.jp"
        extract_apex("www.bbc.co.uk") -> "bbc.co.uk"
        extract_apex("https://corporate.arcelormittal.com/careers") -> "arcelormittal.com"
        extract_apex("") -> ""
    """
    if not url_or_host:
        return ""
    s = url_or_host.strip().lower()
    if not s:
        return ""

    # Prepend a scheme if missing so urlparse populates .netloc.
    if not re.match(r"^https?://", s):
        s = "http://" + s

    try:
        host = urlparse(s).netloc
    except Exception:
        return ""

    # Strip port + leading www. variants.
    host = host.split(":")[0].strip("/").split("/")[0]
    while host.startswith("www."):
        host = host[4:]

    # Reject obvious non-domains.
    if "." not in host or " " in host:
        return ""

    parts = host.split(".")
    if len(parts) < 2:
        return host

    # If the last two labels form a multi-label suffix (e.g., co.uk), the
    # registrable root is the last THREE labels.
    if len(parts) >= 3:
        last_two = ".".join(parts[-2:])
        if last_two in MULTI_LABEL_SUFFIXES:
            return ".".join(parts[-3:])

    return ".".join(parts[-2:])


# ----------------------------------------------------------------------
# Company-name normalization + fuzzy matching
# ----------------------------------------------------------------------

# Corporate suffix tokens to strip before comparing two company names.
# Order matters only for readability — the regex compiles to a single pass.
_CORP_SUFFIX_TOKENS: Sequence[str] = (
    "inc", "llc", "ltd", "gmbh", "sa", "ag", "co", "corp", "corporation",
    "company", "group", "holdings", "limited", "plc", "bv", "srl", "spa",
    "oy", "ab", "pte", "pty", "kg", "mbh", "cie", "sarl",
    "tech", "technologies", "systems", "solutions", "industries",
    "international", "global",
)

_CORP_SUFFIX_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _CORP_SUFFIX_TOKENS) + r")\b\.?",
    flags=re.IGNORECASE,
)


def norm_name(company_name: str) -> str:
    """Normalize a company name for fuzzy comparison.

    - Lowercase
    - Strip corporate suffix tokens (Inc, LLC, Ltd, GmbH, Holdings, ...)
    - Keep only [a-z0-9 ]
    - Collapse whitespace

    Returns "" when normalization leaves less than 3 characters — names that
    short are too noisy to match reliably.

    Examples:
        norm_name("Astura Medical, Inc.") -> "astura medical"
        norm_name("MBDA Systems Holdings Ltd") -> "mbda"
        norm_name("3DMorphic") -> "3dmorphic"
        norm_name("SA") -> ""
    """
    if not company_name:
        return ""
    n = company_name.strip().lower()
    n = _CORP_SUFFIX_RE.sub("", n)
    n = re.sub(r"[^a-z0-9 ]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    if len(n) < 3:
        return ""
    return n


def name_similarity(a: str, b: str) -> float:
    """Return a 0..1 similarity ratio between two company names after
    normalization. Uses difflib.SequenceMatcher which is stdlib and close
    enough to Levenshtein ratio for typical corporate-name matching."""
    na = norm_name(a)
    nb = norm_name(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


# ----------------------------------------------------------------------
# Combined match-against-existing helper
# ----------------------------------------------------------------------

def build_existing_index(
    existing_rows: Iterable[dict],
    domain_field: str = "domain",
    name_field: str = "name",
    website_field: str | None = "website",
) -> tuple[set[str], dict[str, str]]:
    """Build an apex-domain set + normalized-name index from existing rows.

    Returns:
        (apex_set, name_to_apex):
          apex_set is the set of apex domains present in the existing list.
          name_to_apex maps every normalized company name to the apex it
            came from, so a name-match can report which row it collided with.

    existing_rows can be anything iterable of dicts. Pass rows from your
    CRM export, a previous prospect-list CSV, a customer-list download,
    or whatever the user provides as "do not re-contact".
    """
    apex_set: set[str] = set()
    name_to_apex: dict[str, str] = {}

    for r in existing_rows:
        apex = ""
        # Prefer an explicit domain field, fall back to website.
        for fld in (domain_field, website_field):
            if fld and r.get(fld):
                apex = extract_apex(r[fld])
                if apex:
                    break

        if apex:
            apex_set.add(apex)

        nm = norm_name(r.get(name_field, "")) if name_field else ""
        if nm:
            # Don't overwrite a shorter existing key with a longer one; the
            # first occurrence wins so downstream messages are stable.
            name_to_apex.setdefault(nm, apex or "")

    return apex_set, name_to_apex


def check_duplicate(
    candidate: dict,
    apex_set: set[str],
    name_to_apex: dict[str, str],
    domain_field: str = "domain",
    name_field: str = "name",
    website_field: str | None = "website",
    name_threshold: float = 0.85,
) -> tuple[bool, str]:
    """Check a single candidate row against the existing index.

    Returns (is_duplicate, reason). reason is a short string explaining the
    match (e.g. "apex:nikon.com" or "name:astura medical (0.91)") or "" when
    the candidate is net-new.

    The match is layered:
      1. Apex domain match against apex_set (strong, preferred).
      2. If no domain match, walk name_to_apex looking for a fuzzy match
         above name_threshold. Only used as a fallback because name-only
         matches are noisy (e.g. "rocket propulsion" as a substring).
    """
    # Step A: apex domain
    apex = ""
    for fld in (domain_field, website_field):
        if fld and candidate.get(fld):
            apex = extract_apex(candidate[fld])
            if apex:
                break
    if apex and apex in apex_set:
        return True, f"apex:{apex}"

    # Step B: fuzzy company name
    cand_name = candidate.get(name_field, "") if name_field else ""
    nc = norm_name(cand_name)
    if nc:
        best_key = ""
        best_ratio = 0.0
        for existing_name in name_to_apex:
            ratio = SequenceMatcher(None, nc, existing_name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_key = existing_name
                if ratio >= 0.99:  # perfect match, stop early
                    break
        if best_ratio >= name_threshold:
            return True, f"name:{best_key} ({best_ratio:.2f})"

    return False, ""


def match_against_existing(
    candidates: Iterable[dict],
    existing: Iterable[dict],
    domain_field: str = "domain",
    name_field: str = "name",
    website_field: str | None = "website",
    name_threshold: float = 0.85,
) -> tuple[list[dict], list[dict]]:
    """Split candidates into (actionable, matched) against an existing list.

    Each row in the output carries a `dedupe_match` field describing why
    it was classified that way — empty for actionable rows, populated with
    the match reason for matched rows. This makes it trivial to surface in
    reports and explain to the user why a row was excluded.
    """
    apex_set, name_to_apex = build_existing_index(
        existing,
        domain_field=domain_field,
        name_field=name_field,
        website_field=website_field,
    )

    actionable: list[dict] = []
    matched: list[dict] = []
    for c in candidates:
        is_dup, reason = check_duplicate(
            c, apex_set, name_to_apex,
            domain_field=domain_field,
            name_field=name_field,
            website_field=website_field,
            name_threshold=name_threshold,
        )
        out = dict(c)
        out["dedupe_match"] = reason
        if is_dup:
            matched.append(out)
        else:
            actionable.append(out)
    return actionable, matched


# ----------------------------------------------------------------------
# Command-line entry point
# ----------------------------------------------------------------------

def _read_csv(path: str) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with open(path) as f:
        return list(csv.DictReader(f))


def _write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        with open(path, "w", newline="") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _selftest() -> int:
    """Sanity-check the apex and name helpers. Exits non-zero on failure."""
    apex_cases = [
        ("amsynergy.nikon.com", "nikon.com"),
        ("industry.nikon.com", "nikon.com"),
        ("nikon.co.jp", "nikon.co.jp"),
        ("www.bbc.co.uk", "bbc.co.uk"),
        ("corporate.arcelormittal.com", "arcelormittal.com"),
        ("blog.company.com", "company.com"),
        ("firehawkaerospace.com", "firehawkaerospace.com"),
        ("https://www.example.com/foo/bar", "example.com"),
        ("", ""),
        ("localhost", ""),
    ]
    name_cases = [
        ("Astura Medical, Inc.", "astura medical"),
        ("MBDA Systems Holdings Ltd", "mbda"),
        ("3DMorphic", "3dmorphic"),
        ("Firehawk Aerospace", "firehawk aerospace"),
    ]

    failures = 0
    for inp, expected in apex_cases:
        got = extract_apex(inp)
        ok = got == expected
        print(f"apex  {'OK ' if ok else 'FAIL'}  {inp!r:<45} -> {got!r}  (expected {expected!r})")
        if not ok:
            failures += 1
    for inp, expected in name_cases:
        got = norm_name(inp)
        ok = got == expected
        print(f"name  {'OK ' if ok else 'FAIL'}  {inp!r:<45} -> {got!r}  (expected {expected!r})")
        if not ok:
            failures += 1

    # Layered-match sanity check
    existing = [{"domain": "nikon.com", "name": "Nikon Corporation"}]
    candidates = [
        {"domain": "amsynergy.nikon.com", "name": "Nikon AM Synergy"},
        {"domain": "ad-astra.com", "name": "Ad Astra Rocket Company"},
        {"domain": "", "name": "Nikon Corp"},  # name-only fallback
    ]
    actionable, matched = match_against_existing(candidates, existing)
    print()
    print("actionable:", actionable)
    print("matched:   ", matched)
    if len(actionable) != 1 or actionable[0]["domain"] != "ad-astra.com":
        print("FAIL: expected only ad-astra.com to be actionable")
        failures += 1

    return 0 if failures == 0 else 1


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Dedupe a candidate prospect list against an existing list."
    )
    parser.add_argument("--existing", help="CSV with the do-not-contact list")
    parser.add_argument("--candidates", help="CSV with the candidate prospect list")
    parser.add_argument("--out-actionable", help="Write actionable rows here")
    parser.add_argument("--out-matched", help="Write matched-against-existing rows here")
    parser.add_argument("--domain-field", default="domain")
    parser.add_argument("--name-field", default="name")
    parser.add_argument("--website-field", default="website")
    parser.add_argument("--name-threshold", type=float, default=0.85)
    parser.add_argument("--selftest", action="store_true",
                        help="Run built-in sanity tests and exit")
    args = parser.parse_args()

    if args.selftest:
        return _selftest()

    if not (args.existing and args.candidates):
        parser.print_help()
        return 2

    existing = _read_csv(args.existing)
    candidates = _read_csv(args.candidates)
    actionable, matched = match_against_existing(
        candidates, existing,
        domain_field=args.domain_field,
        name_field=args.name_field,
        website_field=args.website_field,
        name_threshold=args.name_threshold,
    )
    if args.out_actionable:
        _write_csv(args.out_actionable, actionable)
    if args.out_matched:
        _write_csv(args.out_matched, matched)
    print(f"existing:   {len(existing)}")
    print(f"candidates: {len(candidates)}")
    print(f"actionable: {len(actionable)}")
    print(f"matched:    {len(matched)}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
