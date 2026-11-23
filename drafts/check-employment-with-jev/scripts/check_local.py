#!/usr/bin/env python3
"""
The preview: check up to 50 of the installer's own people on THIS machine, with the exact code the
play runs, before anything is built or bought.

    python3 check_local.py --file people.csv --show-map               # the column mapping, nothing checked
    python3 check_local.py --file people.csv [--map key=Column …] [--limit 10] [--skip 10]
    python3 check_local.py --file people.json                         # a JSON list of records (or JSON lines)
    python3 check_local.py --fixtures                                 # the invented cases
    ... add --enrich to BUY profiles for people that have only a LinkedIn URL
        (crustdata_v3_person_enrich, priced per matched record; the count is printed first)

The inputs are the play's own: company_name, company_domain, company_linkedin_url (at least one),
profile (an enriched profile with a work history, as an object or JSON text), linkedin_url,
full_name. A file's columns are proposed onto them by name and by content (the column whose cells
hold a work history is the profile) and SHOWN for correction.

Each person checked is one ai_evaluate call (a fraction of a cent). Results go to
last-preview.json in this skill's state folder, which the smoke test reuses.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import active_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAPPABLE = ("company_name", "company_domain", "company_linkedin_url", "profile", "linkedin_url", "full_name")
HINTS = {"company_domain": (("domain",), ("website",), ("company", "url")),
         "company_linkedin_url": (("company", "linkedin"),),
         "company_name": (("company", "name"), ("company",), ("account", "name"), ("organization",)),
         "linkedin_url": (("linkedin", "profile"), ("linkedin", "url"), ("linkedin",), ("profile", "url")),
         "full_name": (("full", "name"), ("name",)),
         "profile": (("enrich", "person"), ("profile",))}


def words(s):
    out, cur = [], ""
    for ch in str(s or "").lower() + " ":
        if ch.isalnum():
            cur += ch
        elif cur:
            out.append(cur)
            cur = ""
    return set(out)


def propose(columns, rows):
    """{input: column or None}. The profile column is found by CONTENT (cells holding a work
    history); the rest by name, most specific hint first, never reusing a column."""
    out, used = {}, set()
    for c in columns:
        vals = [r.get(c) for r in rows if r.get(c)]
        if any(L.node_call("read_profile", L.node_call("_obj", v))[0] for v in vals[:3]):
            out["profile"] = c
            used.add(c)
            break
    for key in ("company_linkedin_url", "company_domain", "linkedin_url", "company_name", "full_name", "profile"):
        if out.get(key):
            continue
        for hint in HINTS[key]:
            hit = next((c for c in columns if c not in used and set(hint) <= words(c)
                        and not words(c) & {"data", "table", "json", "steps"}
                        and not (key == "linkedin_url" and "company" in words(c))
                        and not (key == "full_name" and words(c) & {"company", "account", "first", "last"})), None)
            if hit:
                out[key] = hit
                used.add(hit)
                break
    return dict((k, out.get(k)) for k in MAPPABLE)


def apply_map(mapping, columns, overrides):
    by_name = dict((c.strip().lower(), c) for c in columns)
    for o in overrides:
        if "=" not in o:
            L.fail("--map takes key=Column, got %r" % o, code=2)
        k, v = o.split("=", 1)
        if k not in MAPPABLE:
            L.fail("Unknown input %r. Inputs: %s" % (k, ", ".join(MAPPABLE)), code=2)
        v = v.strip()
        mapping[k] = None if v.lower() in ("", "none", "-") else by_name.get(v.lower())
        if v.lower() not in ("", "none", "-") and not mapping[k]:
            L.fail("No column called %r." % v, code=2)
    return mapping


def show_map(mapping):
    L.say("How your columns map onto the play's inputs (correct any with --map input=Column):")
    for k in MAPPABLE:
        L.say("  %-22s ← %s" % (k, repr(mapping[k]) if mapping.get(k) else "(none)"))
    if not any(mapping.get(k) for k in ("company_name", "company_domain", "company_linkedin_url")):
        L.say("  ! No company column: every row would come back not_checked. Map one.")
    if not mapping.get("profile") and not mapping.get("linkedin_url"):
        L.say("  ! Neither a profile nor a LinkedIn URL: nothing can be checked. Map one.")


def file_records(path, overrides, limit, show, skip):
    rows = L.read_records(path)[skip:skip + limit]
    columns = []
    for r in rows:
        for k in r:
            if k not in columns:
                columns.append(k)
    mapping = apply_map(propose(columns, rows), columns, overrides)
    show_map(mapping)
    if show:
        print(json.dumps({"mapping": mapping}))
        raise SystemExit(0)
    recs = []
    for i, r in enumerate(rows):
        rec = dict((k, r.get(c)) for k, c in mapping.items() if c)
        rec["source_ref"] = str(r.get("source_ref") or "row %d" % (skip + i + 1))
        recs.append(rec)
    return recs, mapping


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file")
    src.add_argument("--fixtures", action="store_true")
    ap.add_argument("--map", action="append", default=[])
    ap.add_argument("--show-map", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--skip", type=int, default=0, help="leave out the first N rows (ten other rows: --skip 10)")
    ap.add_argument("--enrich", action="store_true", help="buy profiles for URL-only people (crustdata_v3_person_enrich)")
    a = ap.parse_args()
    a.limit = max(1, min(50, a.limit))

    mapping = None
    if a.file:
        records, mapping = file_records(a.file, a.map, a.limit, a.show_map, max(0, a.skip))
    else:
        records = [c["record"] for c in json.load(open(os.path.join(HERE, "fixtures.json")))["cases"]][:a.limit]

    need = [r for r in records if L.node_call("intake", r)["need_enrichment"]]
    enrich = None
    if need:
        if a.enrich:
            L.say("Buying %d profile(s) with %s (priced per matched record; read `deepline billing` after)."
                  % (len(need), L.ENRICH_TOOL))
            enrich = L.enrich_profile
        else:
            L.say("%d of these people have only a LinkedIn URL; they come back not_checked unless you add "
                  "--enrich (one %s call each, priced per matched record)." % (len(need), L.ENRICH_TOOL))

    results, tokens = [], 0
    for r in records:
        v = L.check_record(r, enrich=enrich)
        tokens += v["jev_input_tokens"] or 0
        results.append(v)
        who = r.get("full_name") or r.get("linkedin_url") or r.get("source_ref") or "?"
        L.say("  %-26s %-22s %-11s %-16s %3s%%  %s%s" % (
            str(who)[:26], str(v["company_checked"])[:22], v["active_at_company"], v["relationship"],
            v["verdict_confidence"], v["evidence"][:110],
            "" if v["needs_review"] == "none" else "  [review: %s]" % v["needs_review"][:90]))
    tally = {}
    for v in results:
        tally[v["active_at_company"]] = tally.get(v["active_at_company"], 0) + 1
    L.say("%d people: %s · Jev %d input tokens (about $%.5f at the gateway's list price; Deepline's charge is in `deepline billing`)"
          % (len(results), ", ".join("%s %d" % kv for kv in sorted(tally.items())), tokens,
             tokens * L.JEV["list_price_per_mtok"] / 1e6))
    try:
        ws = L.workspace()["id"]
    except SystemExit:
        ws = "local"
    L.save(os.path.join(L.state_dir(ws), "last-preview.json"), {"records": records, "results": results, "mapping": mapping})


if __name__ == "__main__":
    main()
