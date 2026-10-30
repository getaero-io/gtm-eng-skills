#!/usr/bin/env python3
"""Turn an accounts CSV plus frozen concept configs into a per-account feature matrix.

Reuses the analyzer's loader, concept parser and matcher so the booleans here are exactly the
matches the signal report counted. One column per `<family>__<concept>__<source>` (True when
an affirmative mention exists in that source), plus `coverage__website` / `coverage__jobs`
(success|partial|empty|error|missing) and any `--carry` columns copied from the input
(firmographics such as industry or employee count).

Accounts whose source coverage is not `success` get NaN for that source's concept flags, not
False: missing collection is unknown, not observed absence.

    python3 build_feature_matrix.py --input accounts.csv --keywords keywords.json \
      --tools tools.json --job-roles roles.json --carry industry,numberofemployees \
      --output features.csv
"""
from __future__ import annotations

import argparse
import csv
import sys as _sys
csv.field_size_limit(min(_sys.maxsize, 2**31 - 1))
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import analyze_signals_v2 as az  # noqa: E402


def load_config(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True)
    p.add_argument("--keywords")
    p.add_argument("--tools")
    p.add_argument("--job-roles")
    p.add_argument("--output", required=True)
    p.add_argument("--carry", default="", help="Comma-separated input columns to copy through unchanged")
    p.add_argument("--website-col", type=int)
    p.add_argument("--jobs-col", type=int)
    p.add_argument("--status-col", default="status")
    args = p.parse_args()

    accounts, stats = az.load_accounts(args.input, args.website_col, args.jobs_col, args.status_col, "all")
    carry = [c for c in (x.strip() for x in args.carry.split(",")) if c]
    raw_rows = {}
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row.get("account_id") or "").strip() or az.urlparse(
                row["domain"].strip().lower() if "://" in row["domain"] else "//" + row["domain"].strip().lower()
            ).hostname.removeprefix("www.").rstrip(".")
            raw_rows.setdefault(key, row)

    families = (("keywords", load_config(args.keywords)), ("tools", load_config(args.tools)), ("job_roles", load_config(args.job_roles)))
    columns = []
    specs = []
    for family, config in families:
        if not config:
            continue
        for category, name, aliases in az.concepts(config):
            for kind in (("jobs",) if family == "job_roles" else ("website", "jobs")):
                col = f"{family}__{az.normalize(name).replace(' ', '_')}__{kind}"
                columns.append(col)
                specs.append((col, family, aliases, kind))
    if not specs:
        sys.exit("no concepts configured; pass at least one of --keywords/--tools/--job-roles")

    out_rows = []
    for a in accounts:
        row = {"account_id": a["account_id"], "domain": a["domain"], "status": a["status"], "split": a["split"],
               "coverage__website": a["coverage"]["website"], "coverage__jobs": a["coverage"]["jobs"]}
        src = raw_rows.get(a["account_id"], {})
        for c in carry:
            row[c] = src.get(c, "")
        for col, family, aliases, kind in specs:
            if a["coverage"][kind] != "success":
                row[col] = ""  # unknown, not False
                continue
            positive = False
            for doc in a["documents"][kind]:
                text = doc["title"] if family == "job_roles" else doc["text"]
                if any(hit["polarity"] == "affirmative" for hit in az.occurrences(text, aliases)):
                    positive = True
                    break
            row[col] = positive
        out_rows.append(row)

    fieldnames = ["account_id", "domain", "status", "split", "coverage__website", "coverage__jobs"] + carry + columns
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    summary = {"accounts": len(out_rows), "feature_columns": len(columns), "loader_stats": stats,
               "coverage": {k: {} for k in ("website", "jobs")}}
    for kind in ("website", "jobs"):
        for a in accounts:
            summary["coverage"][kind][a["coverage"][kind]] = summary["coverage"][kind].get(a["coverage"][kind], 0) + 1
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
