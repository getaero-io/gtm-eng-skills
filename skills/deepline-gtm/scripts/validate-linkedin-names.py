#!/usr/bin/env python3
"""
Validate LinkedIn profile names against source names.

Usage:
    # Validate a CSV with source names vs scraped profile names
    python validate-linkedin-names.py enriched.csv \
        --source-first first_name --source-last last_name \
        --profile-name-col profile_data.full_name

    # Run against fixture file for eval
    python validate-linkedin-names.py --fixtures fixtures_name_validation.json
"""

import argparse
import csv
import json
import re
import sys
import unicodedata

_QUOTED_NICK_RE = re.compile(r"['\"](\w+)['\"]")
_CLEAN_NAME_RE = re.compile(r"[^\w\s'-]")
_NORMALIZE_RE = re.compile(r"[^a-z\s-]")

NICKNAMES = {
    "mike": {"michael"}, "michael": {"mike"},
    "bob": {"robert", "rob"}, "robert": {"bob", "rob"}, "rob": {"robert", "bob"},
    "bill": {"william", "will"}, "william": {"bill", "will"}, "will": {"william", "bill"},
    "liz": {"elizabeth", "beth"}, "elizabeth": {"liz", "beth"}, "beth": {"elizabeth", "liz"},
    "jim": {"james", "jimmy"}, "james": {"jim", "jimmy"}, "jimmy": {"james", "jim"},
    "joe": {"joseph"}, "joseph": {"joe"},
    "dan": {"daniel", "danny"}, "daniel": {"dan", "danny"}, "danny": {"daniel", "dan"},
    "dave": {"david"}, "david": {"dave"},
    "chris": {"christopher"}, "christopher": {"chris"},
    "matt": {"matthew"}, "matthew": {"matt"},
    "tom": {"thomas"}, "thomas": {"tom"},
    "tony": {"anthony"}, "anthony": {"tony"},
    "nick": {"nicholas", "nico"}, "nicholas": {"nick", "nico"},
    "rick": {"richard"}, "richard": {"rick", "dick"}, "dick": {"richard"},
    "steve": {"steven", "stephen"}, "steven": {"steve", "stephen"}, "stephen": {"steve", "steven"},
    "andy": {"andrew", "drew"}, "andrew": {"andy", "drew"}, "drew": {"andrew", "andy"},
    "alex": {"alexander", "oleksandr", "aleksandr"},
    "alexander": {"alex", "oleksandr"}, "oleksandr": {"alex", "alexander"},
    "sam": {"samuel", "samantha"}, "samuel": {"sam"}, "samantha": {"sam"},
    "ben": {"benjamin", "benny"}, "benjamin": {"ben", "benny"},
    "jon": {"jonathan", "john"}, "jonathan": {"jon", "john"}, "john": {"jon", "jonathan"},
    "ed": {"edward", "ted"}, "edward": {"ed", "ted"}, "ted": {"edward", "theodore"}, "theodore": {"ted"},
    "pat": {"patrick", "patricia"}, "patrick": {"pat"}, "patricia": {"pat"},
    "kate": {"katherine", "katie", "kathy"}, "katherine": {"kate", "katie", "kathy"},
    "jen": {"jennifer", "jenny"}, "jennifer": {"jen", "jenny"},
    "sara": {"sarah"}, "sarah": {"sara"},
    "meg": {"megan"}, "megan": {"meg"},
    "mandy": {"amanda"}, "amanda": {"mandy"},
    "ron": {"ronald"}, "ronald": {"ron"},
    "charlie": {"charles", "chuck"}, "charles": {"charlie", "chuck"},
    "greg": {"gregory"}, "gregory": {"greg"},
    "jeff": {"jeffrey"}, "jeffrey": {"jeff"},
    "doug": {"douglas"}, "douglas": {"doug"},
    "nate": {"nathan", "nathaniel"}, "nathan": {"nate"}, "nathaniel": {"nate"},
    "zach": {"zachary"}, "zachary": {"zach"},
    "max": {"maxwell", "maximilian"}, "maxwell": {"max"}, "maximilian": {"max"},
    "kat": {"katherine", "kate", "kathy"},
}


def normalize(s):
    """Strip accents, lowercase, remove non-alpha except hyphens."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = _NORMALIZE_RE.sub("", s.lower().strip())
    return s.strip()


def first_names_match(source, profile):
    sf = normalize(source)
    pf = normalize(profile)
    if not sf or not pf:
        return False, "empty"
    if sf == pf:
        return True, "exact"
    if len(sf) >= 3 and (sf.startswith(pf) or pf.startswith(sf)):
        return True, "prefix"
    # Nickname
    sf_variants = {sf} | NICKNAMES.get(sf, set())
    pf_variants = {pf} | NICKNAMES.get(pf, set())
    if sf_variants & pf_variants:
        return True, "nickname"
    # Single initial
    if len(sf) == 1 and pf.startswith(sf):
        return True, "initial"
    if len(pf) == 1 and sf.startswith(pf):
        return True, "initial"
    # Check if source contains profile name (handles "J Ryan" matching "J")
    source_parts = sf.split()
    if len(source_parts) > 1:
        for part in source_parts:
            if part == pf or (len(part) >= 3 and (part.startswith(pf) or pf.startswith(part))):
                return True, "multi_part"
            part_variants = {part} | NICKNAMES.get(part, set())
            if part_variants & pf_variants:
                return True, "multi_part_nickname"
    # Check if profile contains quoted nickname
    nickname_match = _QUOTED_NICK_RE.search(profile.lower())
    if nickname_match:
        nick = nickname_match.group(1)
        if nick == sf or sf in NICKNAMES.get(nick, set()) or nick in NICKNAMES.get(sf, set()):
            return True, "quoted_nickname"
    return False, "mismatch"


def last_names_match(source, profile):
    sl = normalize(source)
    pl = normalize(profile)
    if not sl or not pl:
        return False, "empty"
    if sl == pl:
        return True, "exact"
    # Hyphenated: any part matches
    sl_parts = set(sl.replace("-", " ").split())
    pl_parts = set(pl.replace("-", " ").split())
    if sl_parts & pl_parts:
        return True, "hyphenated"
    # One contains the other (covers single-char initials too: "P" in "pabiot")
    if sl in pl or pl in sl:
        return True, "substring"
    return False, "mismatch"


def validate_name(source_first, source_last, profile_full_name):
    """Returns (match: bool, details: dict)."""
    profile_clean = _CLEAN_NAME_RE.sub("", profile_full_name).strip()
    parts = profile_clean.split()
    if len(parts) < 2:
        return False, {"reason": "profile_name_too_short", "profile_clean": profile_clean}

    profile_first = parts[0]
    profile_last = " ".join(parts[1:])

    first_ok, first_reason = first_names_match(source_first, profile_first)
    # Also check if source first name appears as a quoted nickname anywhere in profile
    if not first_ok:
        nickname_match = _QUOTED_NICK_RE.search(profile_clean.lower())
        if nickname_match:
            nick = normalize(nickname_match.group(1))
            sf = normalize(source_first)
            if nick == sf or sf in NICKNAMES.get(nick, set()) or nick in NICKNAMES.get(sf, set()):
                first_ok, first_reason = True, "quoted_nickname"
    last_ok, last_reason = last_names_match(source_last, profile_last)

    return first_ok and last_ok, {
        "first_match": first_ok,
        "first_reason": first_reason,
        "last_match": last_ok,
        "last_reason": last_reason,
        "profile_first": profile_first,
        "profile_last": profile_last,
    }


def run_fixtures(fixture_path):
    """Run eval against fixture file. Returns exit code."""
    with open(fixture_path) as f:
        fixtures = json.load(f)

    results = []
    failures = []

    for fix in fixtures:
        match, details = validate_name(
            fix["source_first"], fix["source_last"], fix["profile_name"]
        )
        expected = fix["expected_match"]
        results.append((expected, match))

        if match != expected:
            failures.append({
                "source": f"{fix['source_first']} {fix['source_last']}",
                "profile": fix["profile_name"],
                "expected": expected,
                "got": match,
                "details": details,
            })

    passed = sum(1 for e, m in results if e == m)
    total = len(results)
    print(f"Name validation eval: {passed}/{total} passed ({passed/total*100:.0f}%)")

    if failures:
        print(f"\nFailures ({len(failures)}):")
        for fail in failures:
            icon = "FP" if fail["got"] else "FN"
            print(f"  [{icon}] {fail['source']} -> {fail['profile']}")
            print(f"       expected={fail['expected']}, got={fail['got']}, {fail['details']}")

    tp = sum(1 for e, m in results if e and m)
    fp = sum(1 for e, m in results if not e and m)
    fn = sum(1 for e, m in results if e and not m)
    tn = sum(1 for e, m in results if not e and not m)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\nConfusion matrix: TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Precision: {precision:.2f} (of accepted, how many correct)")
    print(f"Recall:    {recall:.2f} (of correct, how many accepted)")
    print(f"F1:        {f1:.2f}")

    # Thresholds
    if precision < 0.95:
        print(f"\nFAIL: Precision {precision:.2f} < 0.95 threshold")
        return 1
    if recall < 0.85:
        print(f"\nFAIL: Recall {recall:.2f} < 0.85 threshold")
        return 1

    print("\nPASS: All thresholds met (precision >= 0.95, recall >= 0.85)")
    return 0


def run_csv(csv_path, source_first_col, source_last_col, profile_name_col):
    """Validate a CSV and print mismatches."""
    csv.field_size_limit(10_000_000)
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))

    matched = 0
    mismatched = 0
    skipped = 0

    for r in rows:
        sf = r.get(source_first_col, "").strip()
        sl = r.get(source_last_col, "").strip()
        pn = r.get(profile_name_col, "").strip()

        if not sf or not sl or not pn:
            skipped += 1
            continue

        ok, details = validate_name(sf, sl, pn)
        if ok:
            matched += 1
        else:
            mismatched += 1
            print(f"  MISMATCH: {sf} {sl} -> {pn} ({details})")

    total = matched + mismatched
    print(f"\nValidated: {matched}/{total} matched, {mismatched} mismatched, {skipped} skipped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate LinkedIn profile names")
    parser.add_argument("csv", nargs="?", help="CSV file to validate")
    parser.add_argument("--fixtures", help="Run eval against fixture JSON file")
    parser.add_argument("--source-first", default="first_name")
    parser.add_argument("--source-last", default="last_name")
    parser.add_argument("--profile-name-col", default="profile_name")
    args = parser.parse_args()

    if args.fixtures:
        sys.exit(run_fixtures(args.fixtures))
    elif args.csv:
        run_csv(args.csv, args.source_first, args.source_last, args.profile_name_col)
    else:
        parser.print_help()
