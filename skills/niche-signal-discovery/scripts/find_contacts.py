#!/usr/bin/env python3
"""
Find contacts + emails at a list of prospect companies.

This script implements the contact discovery fallback chain required by
Step 7 of the niche-signal-discovery pipeline. It runs through Deepline in
two phases:

  Phase 1: company_to_contact_by_role_waterfall (FREE tier).
           Dropleads + Deepline native + Apollo + Icypeas + Prospeo + Crustdata.
           Works well for >200-employee US/EU companies with mature B2B data
           coverage. Returns LinkedIn URLs + titles; often no emails.

  Phase 2: For any company that Phase 1 returned ZERO contacts for (which
           is the common case for <200-employee, non-US, or niche industrial
           targets), fall back to exa_search_people with includeDomains=
           ['linkedin.com']. Exa neural search goes over public web text and
           finds LinkedIn profiles that mention the company by name — far
           better coverage for small companies than the B2B provider
           waterfall. Parse the result titles ("Name | Role at Company") to
           pull named contacts.

  Phase 3: For every named contact we have a LinkedIn URL for (from either
           phase), run name_and_domain_to_email_waterfall to resolve a
           corporate email. Validate the result against the company's apex
           domain — providers sometimes return stale emails from a previous
           employer (e.g. nick.romonoski@orbitalatk.com when Nick is now at
           X-Bow Systems), and this domain-match validation filters them.

Why this fallback chain exists:
  On the nTop run that motivated this skill improvement, Phase 1 (the
  waterfall) returned ZERO contacts on all 10 top-scoring prospects —
  Plasma Processes, Ad Astra Rocket, Avimetal, Axial3D, CubeLabs, NextAero,
  Camber Spine, American Additive Mfg, 3D-Side, 3di GmbH. These are mostly
  <200-employee industrial companies, many non-US, where Dropleads / Apollo
  / Crustdata have thin coverage. Exa people search found 15 real named
  contacts at 6 of the 10 in the same pass. The moral: the waterfall is
  cheaper (free tier) but Exa is the actual discovery engine for niche
  industrial / non-US targets. Always run both.

Usage:

  python3 find_contacts.py \\
      --input prospects.csv \\
      --output contacts.csv \\
      --roles "Design Engineer,Mechanical Engineer,Additive Manufacturing Engineer" \\
      --top 10

Input CSV columns: domain, name, [score], [niche]
Output CSV columns: company, domain, full_name, title, linkedin_url, email,
                    email_source, discovery_phase, score, niche

The script calls `deepline enrich` for each phase — it's a thin wrapper.
Nothing here bypasses Deepline.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from typing import Iterable

# Load the apex-domain helper from the sibling dedupe_utils module.
# We add the script's directory to sys.path so imports work from anywhere.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dedupe_utils import extract_apex  # noqa: E402


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------

def _run_deepline_enrich(input_csv: str, output_csv: str, with_specs: list[str]) -> None:
    """Thin wrapper around `deepline enrich`. Raises on non-zero exit."""
    cmd = ["deepline", "enrich", "--input", input_csv, "--output", output_csv]
    for spec in with_specs:
        cmd += ["--with", spec]
    print(f"[find_contacts] running: {' '.join(cmd[:4])} (+{len(with_specs)} --with specs)",
          file=sys.stderr)
    subprocess.run(cmd, check=True)


def _read_csv(path: str) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with open(path) as f:
        return list(csv.DictReader(f))


def _write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _parse_json_field(val: str):
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


def _slug_to_name(linkedin_url: str) -> str:
    """Best-effort first/last name extraction from a LinkedIn profile slug.
    LinkedIn slugs look like `/in/first-last-deadbeef` where the trailing
    hash is an account ID. Strip the hash, split on dashes, title-case.
    This is a fallback for when providers don't return full_name."""
    if not linkedin_url:
        return ""
    m = re.search(r"/in/([^/?]+)", linkedin_url)
    if not m:
        return ""
    slug = m.group(1)
    # Strip trailing hash (6+ hex chars) like `-abbbb4172` or `-342152133`
    slug = re.sub(r"-[a-f0-9]{6,}$", "", slug)
    parts = [p for p in slug.split("-") if p and not p.isdigit()]
    return " ".join(p.capitalize() for p in parts[:3])


# ----------------------------------------------------------------------
# Phase 1: company_to_contact_by_role_waterfall
# ----------------------------------------------------------------------

def phase1_waterfall(
    prospects_csv: str,
    out_csv: str,
    roles: list[str],
    seniority: list[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    """Run the FREE company→contact waterfall on every prospect.

    Returns a list of raw contact dicts: one row per contact discovered,
    with fields (company, domain, full_name, title, linkedin_url, discovery_phase).
    Phase 1 rarely returns emails — email resolution is Phase 3.
    """
    seniority = seniority or ["Senior", "Director", "VP", "Manager"]
    spec = json.dumps({
        "alias": "contact",
        "tool": "company_to_contact_by_role_waterfall",
        "payload": {
            "domain": "{{domain}}",
            "company_name": "{{name}}",
            "roles": roles,
            "seniority": seniority,
            "limit": limit,
        },
    })
    _run_deepline_enrich(prospects_csv, out_csv, [spec])

    rows = _read_csv(out_csv)
    contacts: list[dict] = []
    for r in rows:
        parsed = _parse_json_field(r.get("contact", "") or "")
        items: list = []
        if isinstance(parsed, dict) and isinstance(parsed.get("result"), list):
            items = parsed["result"]
        for item in items[:limit]:
            li = item.get("linkedin", "") or ""
            full = item.get("full_name") or _slug_to_name(li)
            contacts.append({
                "company": r.get("name", ""),
                "domain": r.get("domain", ""),
                "full_name": full,
                "title": item.get("title", "") or "",
                "linkedin_url": li,
                "discovery_phase": "waterfall",
            })
    return contacts


# ----------------------------------------------------------------------
# Phase 2: exa_search_people fallback for empty companies
# ----------------------------------------------------------------------

_TITLE_RE = re.compile(
    r"^\s*([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.\-]+(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.\-]+){1,4})\s*[|\-–]\s*(.+)$"
)

# Generic role tokens used to filter out obvious noise (marketers, recruiters,
# unrelated execs) when the caller hasn't supplied vertical-specific roles. The
# vertical-specific tokens come from the --roles argument at runtime — see
# _derive_role_tokens() — so this set stays neutral.
_GENERIC_ROLE_TOKENS = (
    "engineer", "designer", "principal", "director", "head", "vp",
    "cto", "chief", "manager", "lead", "scientist", "researcher",
)


def _derive_role_tokens(roles: Iterable[str]) -> set[str]:
    """Tokenize the caller's --roles list into a set of single-word filter tokens.

    Splits each role on whitespace, lowercases, and unions with the generic
    role tokens. The point is to let Phase 2's company-match filter accept any
    title that contains a word from the caller's vertical-specific role list,
    without baking those words into a hardcoded constant.
    """
    tokens: set[str] = set(_GENERIC_ROLE_TOKENS)
    for role in roles:
        for word in role.lower().split():
            if len(word) >= 3:  # skip short joiners like "of", "or", "in"
                tokens.add(word)
    return tokens


def phase2_exa_people(
    prospects_csv: str,
    out_csv: str,
    roles: list[str],
    already_covered_domains: set[str],
) -> list[dict]:
    """Run exa_search_people on every prospect that Phase 1 missed.

    The Exa neural search is the workhorse for small / non-US / niche
    industrial companies where the B2B provider waterfall has thin data.
    Include only `linkedin.com` in the domain filter so we get profile
    pages, not marketing copy.

    Only processes companies in prospects_csv that are NOT already in
    `already_covered_domains` (i.e., Phase 1 returned at least one contact
    for them). This keeps credit usage tight.
    """
    # Filter prospects down to the ones that need the fallback.
    all_prospects = _read_csv(prospects_csv)
    needs_fallback = [r for r in all_prospects if r["domain"] not in already_covered_domains]
    if not needs_fallback:
        print("[find_contacts] Phase 1 covered everything, no Phase 2 fallback needed",
              file=sys.stderr)
        return []

    fallback_csv = out_csv.replace(".csv", "_input.csv") if out_csv.endswith(".csv") else out_csv + "_input"
    fieldnames = list(all_prospects[0].keys()) if all_prospects else ["domain", "name"]
    _write_csv(fallback_csv, needs_fallback, fieldnames)

    # Derive the title-filter token set from the caller's --roles list. Tokens
    # are matched against Exa result titles in the per-result loop below — this
    # replaces a hardcoded vertical-specific keyword set so the script stays
    # general across verticals.
    role_tokens = _derive_role_tokens(roles)

    # Build an Exa query phrase from the roles. Keep it short — Exa neural
    # does better with a compact OR'd title list than with a sprawling sentence.
    role_clause = " OR ".join(roles[:6])
    query = f"{role_clause} at {{{{name}}}}"

    spec = json.dumps({
        "alias": "exa_people",
        "tool": "exa_search_people",
        "payload": {
            "query": query,
            "type": "neural",
            "numResults": 10,
            "includeDomains": ["linkedin.com"],
        },
    })
    _run_deepline_enrich(fallback_csv, out_csv, [spec])

    rows = _read_csv(out_csv)
    contacts: list[dict] = []
    for r in rows:
        parsed = _parse_json_field(r.get("exa_people", "") or "")
        results: list = []
        if isinstance(parsed, dict):
            data = parsed.get("result", {}).get("data", {}) if isinstance(parsed.get("result"), dict) else {}
            if isinstance(data, dict):
                results = data.get("results", []) or []

        company_name = (r.get("name", "") or "").lower()
        company_tail = company_name.split(",")[0].split("(")[0].strip()[:8]

        for res in results:
            if not isinstance(res, dict):
                continue
            url = res.get("url", "") or ""
            if "/in/" not in url:
                continue
            title = res.get("title", "") or ""
            text = (res.get("text", "") or "")[:300]
            low_title = title.lower()

            # Require the title to look role-relevant AND to mention the
            # company name somewhere. The company-name requirement is the
            # main false-positive filter — Exa neural sometimes returns
            # profiles at COMPETING companies (e.g. on one real run, a search
            # for "Plasma Processes" engineers returned a Hypertherm plasma
            # process engineer, which is a different employer).
            is_role_relevant = any(tok in low_title for tok in role_tokens)
            is_company_match = (
                company_tail and (company_tail in low_title or company_tail in text.lower())
            )
            if not (is_role_relevant and is_company_match):
                continue

            # Parse "Name | Role at Company" out of the title.
            m = _TITLE_RE.match(title)
            if m:
                name = m.group(1).strip()
                role = m.group(2).strip()
            else:
                name = _slug_to_name(url)
                role = title

            contacts.append({
                "company": r.get("name", ""),
                "domain": r.get("domain", ""),
                "full_name": name,
                "title": role,
                "linkedin_url": url if url.startswith("http") else f"https://www.{url.lstrip('/')}",
                "discovery_phase": "exa_people",
            })
    return contacts


# ----------------------------------------------------------------------
# Phase 3: email waterfall + domain validation
# ----------------------------------------------------------------------

def phase3_emails(contacts: list[dict], out_csv: str) -> list[dict]:
    """Resolve emails for every contact with a LinkedIn URL.

    Uses name_and_domain_to_email_waterfall, which chains pattern validation +
    deepline_native + crustdata + PDL. Then validates the returned email
    against the company's apex domain — providers occasionally return a
    stale email from a previous employer, and domain-mismatch is an
    effective filter for that.

    Returns the same contact list with `email` and `email_source` populated.
    `email` is blank when the resolved address doesn't match the apex
    (still kept in `raw_email` so you can inspect). `email_source` is
    "corporate_validated" for clean matches, "apex_mismatch" when the
    address resolved but looked like a stale/different-employer email,
    or "not_found" when the waterfall returned nothing.
    """
    if not contacts:
        return []

    # Dedupe by LinkedIn URL so we don't pay twice for the same person.
    seen: set[str] = set()
    dedup: list[dict] = []
    for c in contacts:
        li = c.get("linkedin_url", "") or ""
        if not li or li in seen:
            continue
        if not c.get("full_name"):
            continue
        seen.add(li)
        dedup.append(c)

    # Build the Phase 3 input CSV.
    input_csv = out_csv.replace(".csv", "_input.csv") if out_csv.endswith(".csv") else out_csv + "_input"
    email_input_rows = []
    for c in dedup:
        name_parts = c["full_name"].split()
        email_input_rows.append({
            "first_name": name_parts[0] if name_parts else "",
            "last_name": name_parts[-1] if len(name_parts) >= 2 else "",
            "linkedin_url": c["linkedin_url"],
            "company": c.get("company", ""),
            "domain": c.get("domain", ""),
            "title": c.get("title", ""),
        })
    _write_csv(
        input_csv, email_input_rows,
        ["first_name", "last_name", "linkedin_url", "company", "domain", "title"],
    )

    spec = json.dumps({
        "alias": "em",
        "tool": "name_and_domain_to_email_waterfall",
        "payload": {
            "linkedin_url": "{{linkedin_url}}",
            "first_name": "{{first_name}}",
            "last_name": "{{last_name}}",
        },
    })
    _run_deepline_enrich(input_csv, out_csv, [spec])

    rows = _read_csv(out_csv)
    results_by_li: dict[str, tuple[str, str]] = {}
    for r in rows:
        em_col = r.get("em", "") or ""
        parsed = _parse_json_field(em_col)
        email = ""
        if isinstance(parsed, dict) and isinstance(parsed.get("result"), str):
            email = parsed["result"].strip()

        li = r.get("linkedin_url", "")
        domain = (r.get("domain", "") or "").lower()
        status = "not_found"
        out_email = ""
        if email:
            em_domain = email.split("@")[-1].lower() if "@" in email else ""
            em_apex = extract_apex(em_domain) if em_domain else ""
            cand_apex = extract_apex(domain)
            if em_apex and cand_apex and em_apex == cand_apex:
                status = "corporate_validated"
                out_email = email
            else:
                status = "apex_mismatch"
                out_email = ""
        results_by_li[li] = (out_email, status)

    enriched: list[dict] = []
    for c in dedup:
        out_email, status = results_by_li.get(c["linkedin_url"], ("", "not_found"))
        enriched.append({
            **c,
            "email": out_email,
            "email_source": status,
        })
    return enriched


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------

def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Find prospect companies (always) and optionally their contacts + emails. "
                    "Companies-only mode is FREE; contact discovery costs additional Deepline credits.",
    )
    parser.add_argument("--input", required=True,
                        help="CSV of prospects (columns: domain, name, [score], [niche])")
    parser.add_argument("--output", required=True,
                        help="Final CSV. In --no-contacts mode this is the top-N company list. "
                             "In --contacts mode it's one row per discovered contact.")
    parser.add_argument(
        "--roles",
        default="",
        help="Comma-separated role strings to look for (REQUIRED in --contacts mode). "
             "Pass the buyer-persona job titles surfaced in Step 0/0.5 — e.g. for a "
             "creative-ops tool: 'Creative Director,Brand Manager,Content Operations Lead'; "
             "for an AR automation tool: 'AR Manager,Accounts Receivable Specialist,Controller'. "
             "Don't reuse last run's roles for a different vertical.",
    )
    parser.add_argument("--seniority", default="Senior,Director,VP,Manager")
    parser.add_argument("--top", type=int, default=10,
                        help="Only process the top N prospects by score (if present)")
    parser.add_argument("--workdir", default="",
                        help="Directory for intermediate files (default: next to --output)")

    # --contacts / --no-contacts toggle. Default is --no-contacts because contact
    # discovery costs additional Deepline credits and the user should always have
    # to opt in. The SKILL.md flow is: ship companies first, then ask for credit
    # approval before turning on contacts.
    contacts_group = parser.add_mutually_exclusive_group()
    contacts_group.add_argument(
        "--contacts", dest="contacts", action="store_true",
        help="Run the 3-phase contact discovery chain (waterfall + Exa fallback + "
             "email waterfall). Costs extra Deepline credits — get user approval first.",
    )
    contacts_group.add_argument(
        "--no-contacts", dest="contacts", action="store_false",
        help="Companies-only mode (default). Output is just the top-N company list with "
             "score and niche; no contacts, no extra credit spend.",
    )
    parser.set_defaults(contacts=False)
    args = parser.parse_args()

    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    seniority = [s.strip() for s in args.seniority.split(",") if s.strip()]

    if args.contacts and not roles:
        parser.error(
            "--roles is required in --contacts mode. Pass the buyer-persona job "
            "titles for THIS run's vertical (from Step 0/0.5 ecosystem discovery). "
            "Example: --roles 'Design Engineer,Mechanical Engineer,DfAM Engineer'"
        )

    # Slice to top N if the input has a score column.
    raw = _read_csv(args.input)
    has_score = raw and "score" in raw[0]
    if has_score:
        def _score(r):
            try: return int(r.get("score", "0") or 0)
            except Exception: return 0
        raw = sorted(raw, key=_score, reverse=True)[:args.top]
    else:
        raw = raw[:args.top]

    workdir = args.workdir or os.path.dirname(os.path.abspath(args.output))
    os.makedirs(workdir, exist_ok=True)

    # ----------------------------------------------------------------
    # --no-contacts mode: just write the top-N company list and exit.
    # ----------------------------------------------------------------
    if not args.contacts:
        company_fields = ["domain", "name", "score", "niche"]
        company_rows = [
            {f: r.get(f, "") for f in company_fields}
            for r in raw
        ]
        _write_csv(args.output, company_rows, company_fields)
        print(f"[find_contacts] Wrote top {len(company_rows)} companies to {args.output} "
              f"(--no-contacts mode, no extra credits spent)", file=sys.stderr)
        print(f"[find_contacts] Re-run with --contacts to add contact discovery + emails.",
              file=sys.stderr)
        return 0

    # ----------------------------------------------------------------
    # --contacts mode: stage prospects and run the 3-phase chain.
    # ----------------------------------------------------------------
    top_csv = os.path.join(workdir, "_top.csv")
    fieldnames = list(raw[0].keys()) if raw else ["domain", "name"]
    _write_csv(top_csv, raw, fieldnames)

    # ---- Phase 1 ----
    phase1_out = os.path.join(workdir, "_phase1_waterfall.csv")
    phase1_contacts = phase1_waterfall(top_csv, phase1_out, roles=roles, seniority=seniority)
    covered = {c["domain"] for c in phase1_contacts if c.get("full_name") and c.get("linkedin_url")}
    print(f"[find_contacts] Phase 1 found {len(phase1_contacts)} contacts "
          f"covering {len(covered)}/{len(raw)} companies", file=sys.stderr)

    # ---- Phase 2 ----
    phase2_out = os.path.join(workdir, "_phase2_exa_people.csv")
    phase2_contacts = phase2_exa_people(top_csv, phase2_out, roles=roles,
                                        already_covered_domains=covered)
    print(f"[find_contacts] Phase 2 found {len(phase2_contacts)} additional contacts",
          file=sys.stderr)

    # ---- Phase 3 ----
    all_contacts = phase1_contacts + phase2_contacts
    phase3_out = os.path.join(workdir, "_phase3_emails.csv")
    with_emails = phase3_emails(all_contacts, phase3_out)

    # Merge score/niche back onto the final output if the input had them.
    score_by_domain = {r["domain"]: r.get("score", "") for r in raw}
    niche_by_domain = {r["domain"]: r.get("niche", "") for r in raw}
    for c in with_emails:
        c["score"] = score_by_domain.get(c["domain"], "")
        c["niche"] = niche_by_domain.get(c["domain"], "")

    # Final write.
    fields = ["company", "domain", "score", "niche", "full_name", "title",
              "linkedin_url", "email", "email_source", "discovery_phase"]
    _write_csv(args.output, with_emails, fields)

    valid = sum(1 for c in with_emails if c["email_source"] == "corporate_validated")
    print(f"[find_contacts] Wrote {len(with_emails)} contacts to {args.output}",
          file=sys.stderr)
    print(f"[find_contacts] {valid} have corporate-validated emails", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
