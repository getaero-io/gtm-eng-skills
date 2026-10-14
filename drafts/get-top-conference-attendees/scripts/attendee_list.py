"""Read an attendee list the installer already has, and turn it into campaign seed input.

**No upload endpoint is needed for this.** The campaign create call accepts up to 500 seeded
attendees inline (`name` required, plus optional `title`, `company`, `linkedin_url`, `email`,
`phone`), and Lanyard still finds more on top of them. So a list of 500 or
fewer goes straight in. Only a longer list needs anything new.

Two rules this module enforces, both about not inventing attendance.

1. **A name is the only required field, and a row without one is dropped, not guessed at.**
   A list with a blank name column produces zero seeds and says so, rather than seeding the
   campaign with empty people.

2. **Which list it is gets recorded and reported.** "Last year's attendee list" is real
   evidence that somebody may come again, and it is NOT evidence that they are coming. The
   service assigns its own attendance confidence and `year_context`, so the honest handling is
   to seed the list, label which year it came from, and let those fields carry the difference.
   Nothing here marks anybody as attending.

Everything is pure and dependency-free: `csv` from the standard library, no network, no
credentials. Parsing is exercised by `test_offline.py`.
"""

import csv
import io
import os

# The create call's cap. A list longer than this cannot be seeded inline.
MAX_SEEDS = 500

# Header spellings seen in the wild, mapped to the field the API wants. Matching is
# case-insensitive and ignores spaces, underscores and hyphens, because "Full Name",
# "full_name" and "FULLNAME" are the same column and a person should not have to care.
HEADER_MAP = {
    "name": "name", "fullname": "name", "attendee": "name", "attendeename": "name",
    "contactname": "name", "person": "name",
    "firstname": "_first", "givenname": "_first",
    "lastname": "_last", "surname": "_last", "familyname": "_last",
    "title": "title", "jobtitle": "title", "position": "title", "role": "title",
    "company": "company", "organisation": "company", "organization": "company",
    "employer": "company", "account": "company", "companyname": "company",
    "email": "email", "emailaddress": "email", "workemail": "email", "e-mail": "email",
    "linkedin": "linkedin_url", "linkedinurl": "linkedin_url",
    "linkedinprofile": "linkedin_url", "profile": "linkedin_url", "profileurl": "linkedin_url",
    "phone": "phone", "phonenumber": "phone", "mobile": "phone", "telephone": "phone",
    "tel": "phone",
}

SEED_FIELDS = ("name", "title", "company", "linkedin_url", "email", "phone")


def normalise_header(h):
    return "".join(ch for ch in str(h or "").strip().lower()
                   if ch.isalnum())


def map_headers(headers):
    """Return (mapping of column index -> seed field, list of unmapped header names)."""
    mapping, unmapped = {}, []
    for i, h in enumerate(headers or []):
        key = normalise_header(h)
        field = HEADER_MAP.get(key)
        if field:
            # First column wins for a given field — a sheet with two "email" columns should
            # not have the later one silently overwrite the earlier.
            if field not in mapping.values():
                mapping[i] = field
        elif str(h or "").strip():
            unmapped.append(str(h).strip())
    return mapping, unmapped


def sniff_dialect(sample):
    """Comma or tab, decided from the content rather than the file extension."""
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        return csv.excel


def parse_rows(text):
    """Parse a delimited attendee list into seed dicts.

    Returns (seeds, report). `report` names everything that was NOT straightforward, because
    a silent 40% drop rate is the failure mode here: a list that mostly failed to parse looks
    exactly like a small conference.
    """
    report = {"rows_read": 0, "seeded": 0, "dropped_no_name": 0, "truncated": 0,
              "mapped": {}, "unmapped_columns": [], "built_name_from_parts": 0}
    if not (text or "").strip():
        report["error"] = "the file is empty"
        return [], report

    reader = csv.reader(io.StringIO(text), sniff_dialect(text[:4096]))
    rows = [r for r in reader if any(str(c).strip() for c in r)]
    if not rows:
        report["error"] = "no non-blank rows"
        return [], report

    mapping, unmapped = map_headers(rows[0])
    report["unmapped_columns"] = unmapped
    report["mapped"] = {rows[0][i]: f for i, f in sorted(mapping.items())
                        if not f.startswith("_")}
    has_name = "name" in mapping.values()
    has_parts = "_first" in mapping.values() and "_last" in mapping.values()
    if not (has_name or has_parts):
        report["error"] = (
            "no name column found. Looked for: name, full name, attendee, contact name, or "
            "first name plus last name. Headers seen: %s"
            % (", ".join(str(h) for h in rows[0] if str(h).strip()) or "none"))
        return [], report

    seeds = []
    for raw in rows[1:]:
        report["rows_read"] += 1
        rec = {}
        for i, field in mapping.items():
            if i < len(raw):
                v = str(raw[i] or "").strip()
                if v:
                    rec[field] = v
        name = rec.get("name")
        if not name:
            first, last = rec.pop("_first", ""), rec.pop("_last", "")
            joined = " ".join(p for p in (first, last) if p).strip()
            if joined:
                name = joined
                report["built_name_from_parts"] += 1
        rec.pop("_first", None)
        rec.pop("_last", None)
        if not name:
            report["dropped_no_name"] += 1
            continue
        seed = {"name": name}
        for f in SEED_FIELDS:
            if f != "name" and rec.get(f):
                seed[f] = rec[f][:320]
        seeds.append(seed)

    if len(seeds) > MAX_SEEDS:
        report["truncated"] = len(seeds) - MAX_SEEDS
        seeds = seeds[:MAX_SEEDS]
    report["seeded"] = len(seeds)
    return seeds, report


def load_file(path):
    """Read a .csv / .tsv / .txt attendee list from disk. Returns (seeds, report)."""
    # Format BEFORE existence: "no such file" is the wrong complaint about a path that was
    # never going to work, and it sends somebody hunting for a typo instead of exporting.
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return [], {
            "error": "%s is a spreadsheet, and this reads delimited text only — no "
                     "third-party library ships with this skill. Export the sheet as CSV "
                     "and point at that." % os.path.basename(path),
            "rows_read": 0, "seeded": 0}
    if not os.path.exists(path):
        return [], {"error": "no file at %s" % path, "rows_read": 0, "seeded": 0}
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return parse_rows(fh.read())


def describe(report):
    """The report as lines to print. Says what was dropped, never only what worked."""
    out = []
    if report.get("error"):
        out.append("could not use the list: %s" % report["error"])
        return out
    out.append("read %d row(s), seeded %d attendee(s)"
               % (report.get("rows_read", 0), report.get("seeded", 0)))
    if report.get("mapped"):
        out.append("columns used: " + ", ".join("%s -> %s" % (k, v)
                                                for k, v in report["mapped"].items()))
    if report.get("built_name_from_parts"):
        out.append("built %d name(s) from first + last name columns"
                   % report["built_name_from_parts"])
    if report.get("dropped_no_name"):
        out.append("DROPPED %d row(s) with no name — a row without one cannot be seeded"
                   % report["dropped_no_name"])
    if report.get("truncated"):
        out.append("TRUNCATED %d row(s): the create call accepts %d seeds and the list is "
                   "longer. The rest are not sent; the service still searches for more."
                   % (report["truncated"], MAX_SEEDS))
    if report.get("unmapped_columns"):
        out.append("ignored column(s): " + ", ".join(report["unmapped_columns"]))
    return out
