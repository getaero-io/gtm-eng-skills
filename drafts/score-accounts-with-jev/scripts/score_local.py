#!/usr/bin/env python3
"""
Score a small batch of real records on THIS machine, running the exact scoring code the Deepline
play will run (under node), with Jev called through Deepline's ai_evaluate. This is the preview the
installer corrects the rubric against before anything is built.

    python3 score_local.py --file records.csv|records.json|records.jsonl [--limit 10] [--map key=Column] [--show-map]

--show-map prints how the file's columns map onto the rubric's inputs and stops, without calling
Jev: show it, take corrections as --map, then run. Reads at most --limit records (max 50). Each
record is one ai_evaluate call (a fraction of a cent, billed by Deepline from usage); a record a
rule disqualifies, or with nothing to ask, costs nothing. The confirmed mapping is saved, so the
build bakes the same mapping into the play. Results are written to the state folder as JSON lines
and summarised here.
"""
import argparse
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_lib as L  # noqa: E402


def label_of(rec_in, ref):
    order = ("full_name", "name", "email", "company_name") if L.ENTITY == "contact" else ("company_name", "name", "domain")
    for k in order:
        if rec_in.get(k):
            return str(rec_in[k])[:28]
    return str(ref)[:28]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rubric")
    ap.add_argument("--file", required=True, help="a CSV, a JSON array, or JSON lines (export a CRM list or table to CSV first)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--map", action="append", default=[])
    ap.add_argument("--show-map", action="store_true")
    a = ap.parse_args()
    limit = max(1, min(a.limit, 50))

    ws = L.workspace()
    r = L.load_rubric(a.rubric, ws["id"])
    columns, recs = L.read_records(a.file, limit)

    mapping = L.apply_overrides(L.propose_map(r["inputs"], columns), columns, a.map)
    L.say(L.mapping_card(r["inputs"], mapping, columns))
    missing = [k for k, s in r["inputs"].items() if s["required"] and not mapping.get(k)]
    if a.show_map:
        print(json.dumps({"mapping": mapping, "unmapped": [k for k in mapping if not mapping[k]]}))
        return
    if missing:
        L.fail("Required input(s) not mapped: %s. Map them with --map key=Column." % ", ".join(missing), code=2)
    if not recs:
        L.fail("The file has no records to score.", code=2)

    sd = L.state_dir(ws["id"])
    L.save(os.path.join(sd, "mapping-%s.json" % L.slug(r["name"])), {"mapping": mapping, "file": os.path.abspath(a.file)})
    out_dir = os.path.join(sd, "previews")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "%s-v%d-%d.jsonl" % (L.slug(r["name"]), r["version"], int(time.time())))
    L.say("")
    L.say("%-28s %5s  %-18s %s" % (L.NOUN, "score", "tier", "why (top reasons) / needs review"))
    tiers, tokens, review = {}, 0, 0
    with open(out_path, "a") as f:
        for i, rec in enumerate(recs):
            rec = dict(rec)
            rec.setdefault("source_ref", "row %d" % (i + 1))
            inp = dict((k, rec.get(c) if c else None) for k, c in mapping.items())
            inp["source_ref"] = rec["source_ref"]
            res = L.score_record(r, inp)
            f.write(json.dumps({"input": inp, "row": rec, "result": res}) + "\n")
            f.flush()
            tiers[res["lead_tier"]] = tiers.get(res["lead_tier"], 0) + 1
            tokens += int(res["jev_input_tokens"] or 0)
            review += res["needs_review"] != "none"
            L.say("%-28s %5s  %-18s %s" % (label_of(inp, inp["source_ref"]), res["lead_score"], res["lead_tier"],
                                           res["score_reasons"][:150]))
            if res["needs_review"] != "none":
                L.say("%-28s %5s  %-18s review: %s" % ("", "", "", res["needs_review"][:150]))
            if res["error"]:
                L.say("%-28s %5s  %-18s error: %s" % ("", "", "", res["error"][:150]))
    L.say("")
    L.say("%d %s scored with %s v%d: %s. %d with an answer worth reviewing. Jev read %d input tokens "
          "(about $%.5f at list price; `deepline billing` shows the real charge)." % (
              len(recs), L.NOUNS, r["name"], r["version"],
              ", ".join("%s %d" % kv for kv in sorted(tiers.items())), review, tokens,
              tokens * L.JEV["list_price_per_mtok"] / 1e6))
    L.say("Every result, with each criterion's answer and points: %s" % out_path)


if __name__ == "__main__":
    main()
