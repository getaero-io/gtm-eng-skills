#!/usr/bin/env python3
"""Build the analyzer's accounts CSV from a HubSpot portal.

Labels: a company is `won` if any associated deal is closed-won, else `lost` if any associated
deal is closed (lost or disqualified), else `unlabeled` (open deal). Companies without deals are
`unlabeled` and only included through `--universe-sample N` (a seeded random sample used as the
coverage control and percentile reference population).

`known_at` for closed accounts is the earliest matching close date minus `--lead-days` (default 90),
so collection can drop evidence that appeared after the decision window. Needs HUBSPOT_API_KEY.

    cli-sh python3 hubspot_accounts.py --output accounts.csv --universe-sample 300
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

DEAL_PROPS = ["dealname", "dealstage", "pipeline", "closedate", "createdate", "amount", "hs_is_closed_won", "hs_is_closed"]
COMPANY_PROPS = ["domain", "name", "industry", "numberofemployees", "country", "annualrevenue", "lifecyclestage",
                 "createdate", "hs_employee_range", "type", "web_technologies", "description"]


def api(path: str, data: dict | None = None) -> dict:
    tok = os.environ.get("HUBSPOT_API_KEY")
    if not tok:
        sys.exit("HUBSPOT_API_KEY not set (run through cli-sh)")
    req = urllib.request.Request("https://api.hubapi.com" + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(req))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                time.sleep(2 * (attempt + 1)); continue
            sys.exit(f"HubSpot {exc.code} on {path}: {exc.read()[:500]!r}")


def all_deals() -> list[dict]:
    deals, after = [], None
    while True:
        q = "&".join("properties=" + p for p in DEAL_PROPS) + "&associations=companies&limit=100" + (f"&after={after}" if after else "")
        r = api("/crm/v3/objects/deals?" + q)
        deals += r["results"]
        after = (r.get("paging") or {}).get("next", {}).get("after")
        if not after:
            return deals


def companies_by_id(ids: list[str]) -> dict:
    out = {}
    for i in range(0, len(ids), 100):
        r = api("/crm/v3/objects/companies/batch/read", {"properties": COMPANY_PROPS, "inputs": [{"id": c} for c in ids[i:i + 100]]})
        for c in r["results"]:
            out[c["id"]] = c["properties"]
    return out


def universe_sample(n: int, exclude: set[str], seed: int) -> dict:
    """Seeded sample of companies with a domain and no deals (list endpoint; no 10k search cap)."""
    pool, after = [], None
    while True:
        q = "properties=domain&limit=100" + (f"&after={after}" if after else "")
        r = api("/crm/v3/objects/companies?" + q)
        pool += [(c["id"], (c["properties"].get("domain") or "").lower()) for c in r["results"] if c["id"] not in exclude]
        after = (r.get("paging") or {}).get("next", {}).get("after")
        if not after:
            break
    random.Random(seed).shuffle(pool)
    chosen = [cid for cid, dom in pool if dom][:n]
    return companies_by_id(chosen)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output", required=True)
    p.add_argument("--universe-sample", type=int, default=0)
    p.add_argument("--seed", type=int, default=20261028)
    p.add_argument("--lead-days", type=int, default=90)
    args = p.parse_args()

    deals = all_deals()
    cids = sorted({a["id"] for d in deals for a in (d.get("associations") or {}).get("companies", {}).get("results", [])})
    comp = companies_by_id(cids)
    scored_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = {}
    for d in deals:
        pr = d["properties"]
        lab = "won" if pr.get("hs_is_closed_won") == "true" else ("lost" if pr.get("hs_is_closed") == "true" else "unlabeled")
        for a in (d.get("associations") or {}).get("companies", {}).get("results", []):
            c = comp.get(a["id"], {})
            r = rows.setdefault(a["id"], {"account_id": a["id"], "labels": [], "close_dates": [], "deal_names": [], "props": c})
            r["labels"].append(lab); r["close_dates"].append(pr.get("closedate")); r["deal_names"].append(pr.get("dealname") or "")

    def row_for(cid: str, props: dict, status: str, known_at: str, deal_names: str, deal_labels: str) -> dict:
        return {"account_id": cid, "domain": (props.get("domain") or "").lower().strip(), "name": props.get("name"),
                "status": status, "known_at": known_at, "scored_at": scored_at, "deal_labels": deal_labels, "deal_names": deal_names,
                "industry": props.get("industry"), "numberofemployees": props.get("numberofemployees"), "country": props.get("country"),
                "annualrevenue": props.get("annualrevenue"), "lifecyclestage": props.get("lifecyclestage"),
                "hs_employee_range": props.get("hs_employee_range"), "type": props.get("type"),
                "web_technologies": props.get("web_technologies"), "company_createdate": props.get("createdate")}

    out = []
    for cid, r in rows.items():
        labs = set(r["labels"])
        status = "won" if "won" in labs else ("lost" if "lost" in labs else "unlabeled")
        known_at = ""
        cds = [c for c, l in zip(r["close_dates"], r["labels"]) if l == status and c]
        if status in ("won", "lost") and cds:
            dt = min(datetime.fromisoformat(c.replace("Z", "+00:00")) for c in cds) - timedelta(days=args.lead_days)
            known_at = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(row_for(cid, r["props"], status, known_at, "|".join(r["deal_names"]), "|".join(r["labels"])))
    n_deal = len(out)
    if args.universe_sample:
        for cid, props in universe_sample(args.universe_sample, set(rows), args.seed).items():
            out.append(row_for(cid, props, "unlabeled", "", "", "universe_sample"))
    fields = list(row_for("", {}, "unlabeled", "", "", "").keys())
    excluded = [dict(o, miss_reason="missing_domain") for o in out if not o["domain"]]
    out = [o for o in out if o["domain"]]
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    with open(args.output + ".excluded.csv", "w", newline="") as f:  # population reconciliation, written even when empty
        w = csv.DictWriter(f, fieldnames=fields + ["miss_reason"]); w.writeheader(); w.writerows(excluded)
    from collections import Counter
    print(json.dumps({"deals": len(deals), "deal_companies": n_deal, "rows_written": len(out), "rows_excluded_missing_domain": len(excluded),
                      "status_counts": dict(Counter(o["status"] for o in out)),
                      "universe_sample": args.universe_sample, "seed": args.seed}, indent=2))


if __name__ == "__main__":
    main()
