#!/usr/bin/env python3
"""
Audit final B2B contact rows before shipping.

The script is deterministic by design: it checks freshness, email risk,
identity confidence, final-cell shape, domain alignment, and duplicate-person
conflicts, then projects those flags into ACTION and flag_reason columns.

Usage:
    python3 contact-accuracy-audit.py final.csv > audited.csv
    python3 contact-accuracy-audit.py --fixtures fixtures_contact_accuracy_audit.json
"""
import argparse
import csv
import json
import re
import sys
from datetime import date, datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def norm_domain(s):
    s = (s or "").strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.split("/")[0]


def norm_linkedin_url(s):
    s = (s or "").strip().lower()
    m = re.search(r"linkedin\.com/in/([^/?#]+)", s)
    return m.group(1).strip("/") if m else ""


def split_domains(s):
    return [norm_domain(p) for p in re.split(r"[,; ]+", s or "") if norm_domain(p)]


def parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(s, fmt)
            return parsed.date()
        except ValueError:
            continue
    return None


def days_old(s, today):
    parsed = parse_date(s)
    if not parsed:
        return None
    return (today - parsed).days


def email_domain(email):
    if "@" not in (email or ""):
        return ""
    return norm_domain(email.rsplit("@", 1)[1])


def person_key(row):
    linkedin = norm_linkedin_url(row.get("linkedin_url") or row.get("linkedin"))
    if linkedin:
        return f"li:{linkedin}"
    email = (row.get("email") or "").strip().lower()
    if EMAIL_RE.match(email):
        return f"email:{email}"
    name = norm(row.get("name") or f"{row.get('first_name', '')} {row.get('last_name', '')}")
    domain = norm_domain(row.get("company_domain") or row.get("domain"))
    title = norm(row.get("current_title") or row.get("title"))
    return f"name:{name}:{domain}:{title}" if name and domain else ""


def flag(row, today):
    flags = []
    email = (row.get("email") or "").strip()
    company = row.get("company") or row.get("company_name") or ""
    current_company = row.get("current_company") or row.get("company") or ""
    title = row.get("current_title") or row.get("title") or ""
    company_domain = norm_domain(row.get("company_domain") or row.get("domain"))
    allowed_domains = set(split_domains(row.get("allowed_email_domains")))
    if company_domain:
        allowed_domains.add(company_domain)

    changed_company = current_company and company and norm(current_company) != norm(company)
    if changed_company:
        flags.append("job_changed")

    if email:
        if not EMAIL_RE.match(email):
            flags.append("invalid_email_format")
        elif changed_company and company_domain and email_domain(email) == company_domain:
            flags.append("email_domain_mismatch")
        elif allowed_domains and email_domain(email) not in allowed_domains:
            flags.append("email_domain_mismatch")
    else:
        flags.append("missing_email")

    linkedin = row.get("linkedin_url") or row.get("linkedin") or ""
    if linkedin and not norm_linkedin_url(linkedin):
        flags.append("invalid_linkedin_url")

    if title and (norm(title) == norm(company) or norm(title) == norm(current_company)):
        flags.append("title_equals_company")

    profile_age = days_old(row.get("profile_scraped_at") or row.get("source_observed_at"), today)
    email_age = days_old(row.get("email_verified_at"), today)
    if profile_age is None:
        flags.append("profile_freshness_missing")
    elif profile_age > 30:
        flags.append("profile_stale")
    if email_age is None:
        flags.append("email_verification_missing")
    elif email_age > 30:
        flags.append("email_verification_stale")

    identity = (row.get("identity_confirmation") or "").strip().upper()
    if not identity or identity == "NONE":
        flags.append("identity_unconfirmed")

    validation = (row.get("email_validation") or row.get("validation_status") or "").strip().lower()
    corroboration = int(row.get("catch_all_corroboration_count") or 0)
    email_risk = "LOW"
    if "catch-all" in validation or "catch_all" in validation:
        if corroboration >= 2:
            email_risk = "MED"
        else:
            email_risk = "HIGH"
            flags.append("catch_all_not_corroborated")
    elif "invalid" in validation or "do_not_mail" in validation:
        email_risk = "HIGH"
        flags.append("email_invalid")
    elif "unknown" in validation or "no-status" in validation or not validation:
        email_risk = "MED"
        flags.append("email_validation_unknown")

    return flags, email_risk, profile_age, email_age


def project_action(flags, confidence, email_risk):
    confidence = (confidence or "").strip().upper()
    if "job_changed" in flags:
        return "REMOVE / RE-TARGET"
    if "duplicate_person_conflict" in flags or "catch_all_not_corroborated" in flags:
        return "REVIEW"
    verify_flags = {
        "invalid_email_format",
        "invalid_linkedin_url",
        "title_equals_company",
        "profile_stale",
        "profile_freshness_missing",
        "email_verification_stale",
        "email_verification_missing",
        "identity_unconfirmed",
        "email_invalid",
        "email_validation_unknown",
        "missing_email",
    }
    if any(f in verify_flags for f in flags):
        return "VERIFY"
    if confidence in ("LOW", "HOLD"):
        return "VERIFY"
    if email_risk == "HIGH":
        return "REVIEW"
    return "SEND"


def audit_rows(rows, today):
    audited = []
    for row in rows:
        flags, email_risk, profile_age, email_age = flag(row, today)
        out = dict(row)
        out["_flags"] = flags
        out["email_risk"] = email_risk
        out["profile_age_days"] = "" if profile_age is None else str(profile_age)
        out["email_verification_age_days"] = "" if email_age is None else str(email_age)
        audited.append(out)

    groups = {}
    for idx, row in enumerate(audited):
        key = person_key(row)
        if key:
            groups.setdefault(key, []).append(idx)
    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        emails = {(audited[i].get("email") or "").strip().lower() for i in indexes}
        titles = {norm(audited[i].get("current_title") or audited[i].get("title")) for i in indexes}
        companies = {norm(audited[i].get("current_company") or audited[i].get("company")) for i in indexes}
        if len(emails) > 1 or len(titles) > 1 or len(companies) > 1:
            for i in indexes:
                audited[i]["_flags"].append("duplicate_person_conflict")

    for row in audited:
        flags = sorted(set(row.pop("_flags")))
        row["flags"] = ",".join(flags)
        row["flag_reason"] = "; ".join(flags)
        row["ACTION"] = project_action(flags, row.get("gold_confidence") or row.get("GOLD_confidence"), row["email_risk"])
    return audited


def run_fixtures(path, today):
    cases = json.load(open(path))
    passed = failed = 0
    for case in cases:
        got = audit_rows(case["rows"], today)
        expected = case["expected"]
        ok = len(got) == len(expected)
        if ok:
            for out, exp in zip(got, expected):
                if exp.get("action") and out["ACTION"] != exp["action"]:
                    ok = False
                if exp.get("email_risk") and out["email_risk"] != exp["email_risk"]:
                    ok = False
                for expected_flag in exp.get("flags", []):
                    if expected_flag not in out["flags"].split(","):
                        ok = False
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL [{case.get('name', '?')}] expected {expected} got {got}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--fixtures")
    ap.add_argument("--today", default="2026-06-07")
    args = ap.parse_args()

    today = parse_date(args.today) or date.today()
    if args.fixtures:
        run_fixtures(args.fixtures, today)
        return

    if not args.csv:
        print("ERROR: provide a CSV path or --fixtures", file=sys.stderr)
        sys.exit(2)

    rows = list(csv.DictReader(open(args.csv)))
    audited = audit_rows(rows, today)
    fields = list(rows[0].keys()) if rows else []
    for col in ("email_risk", "profile_age_days", "email_verification_age_days", "flags", "flag_reason", "ACTION"):
        if col not in fields:
            fields.append(col)
    writer = csv.DictWriter(sys.stdout, fieldnames=fields)
    writer.writeheader()
    writer.writerows(audited)


if __name__ == "__main__":
    main()
