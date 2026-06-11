#!/usr/bin/env python3
"""
Flatten deepline_native_search_contact output into one CSV row per person.

Use after a deepline enrich pass whose contact column contains the persisted
search_contact result. The source CSV is never modified.
"""

import argparse
import csv
import json
import sys


def _load_cell(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _get_path(obj, path):
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _persons_from_cell(value):
    cell = _load_cell(value)
    candidates = [
        ["result", "data", "output", "persons"],
        ["result", "output", "persons"],
        ["data", "output", "persons"],
        ["output", "persons"],
        ["persons"],
    ]
    for path in candidates:
        persons = _get_path(cell, path)
        if isinstance(persons, list):
            return [p for p in persons if isinstance(p, dict)]
    return []


def _first(value, *keys):
    for key in keys:
        if isinstance(value, dict) and value.get(key):
            return value[key]
    return ""


def flatten(rows, contacts_col):
    out = []
    for row in rows:
        persons = _persons_from_cell(row.get(contacts_col))
        for person in persons:
            full_name = _first(person, "name", "full_name")
            first_name = _first(person, "first_name", "firstName")
            last_name = _first(person, "last_name", "lastName")
            if not full_name:
                full_name = " ".join(part for part in [first_name, last_name] if part)
            out.append(
                {
                    "company_name": row.get("company_name", ""),
                    "domain": row.get("domain") or row.get("company_domain", ""),
                    "contact_name": full_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "title": _first(person, "title", "job_title", "jobTitle"),
                    "linkedin_url": _first(person, "linkedin_url", "linkedin", "linkedinUrl"),
                    "seniority": _first(person, "seniority"),
                    "department": _first(person, "department"),
                    "matched_titles": row.get("matched_titles", ""),
                    "source_provider": "deepline_native_search_contact",
                }
            )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--contacts-col", default="contacts")
    args = parser.parse_args()

    with open(args.csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    fieldnames = [
        "company_name",
        "domain",
        "contact_name",
        "first_name",
        "last_name",
        "title",
        "linkedin_url",
        "seniority",
        "department",
        "matched_titles",
        "source_provider",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(flatten(rows, args.contacts_col))


if __name__ == "__main__":
    main()
