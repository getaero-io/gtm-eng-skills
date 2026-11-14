#!/usr/bin/env python3
"""
Prove the PUBLISHED play gives the same verdict as the local check, person by person.

    python3 smoke_test.py --from-preview        # the first person of the last preview
    python3 smoke_test.py --fixtures            # every invented case in fixtures.json
    python3 smoke_test.py --fixtures --only stale_current_role
    python3 smoke_test.py --record person.json  # one record you supply (JSON object)

The records go to the live revision of the play in one run (`deepline plays run --name`), the
run's dataset is exported, and each row is checked locally with the exact code the play runs. A
record sent with only a LinkedIn URL makes the play buy the profile (crustdata_v3_person_enrich);
the local check then reuses the profile the play bought (its `found` column), so both sides judge
the same work history.

Match means the wiring and the published code work. Jev's probabilities move slightly between
calls, so a confidence can differ by a few points; the verdict and the relationship must not.
"""
import argparse
import csv
import json
import os
import sys
import tempfile
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import active_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fixtures", action="store_true")
    g.add_argument("--from-preview", action="store_true")
    g.add_argument("--record", help="a JSON file holding one record")
    ap.add_argument("--only", action="append", default=[], help="with --fixtures: just these case ids")
    a = ap.parse_args()

    ws = L.workspace()
    st = L.load(os.path.join(L.state_dir(ws["id"]), "build-state.json"), {})
    if not st.get("published"):
        L.fail("The play is not published yet: run build_workflow.py first.")

    if a.fixtures:
        cases = [(c["id"], c["record"], c.get("expect") or {})
                 for c in json.load(open(os.path.join(HERE, "fixtures.json")))["cases"]
                 if not a.only or c["id"] in a.only]
    elif a.record:
        cases = [("record", json.load(open(a.record)), {})]
    else:
        prev = L.load(os.path.join(L.state_dir(ws["id"]), "last-preview.json"), {})
        if not prev.get("records"):
            L.fail("No preview has run yet: run check_local.py first, or use --fixtures.")
        cases = [("preview-1", prev["records"][0], {})]

    stamp = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    rows, refs = [], {}
    for i, (cid, rec, exp) in enumerate(cases):
        body = dict(rec, source_ref="smoke-%s-%d" % (stamp, i))
        # A profile object travels as JSON text, the way a CSV column would carry it.
        if isinstance(body.get("profile"), (dict, list)):
            body["profile"] = json.dumps(body["profile"])
        rows.append(body)
        refs[body["source_ref"]] = (cid, body, exp)

    with tempfile.TemporaryDirectory() as t:
        inp, idf, out = os.path.join(t, "in.json"), os.path.join(t, "run.json"), os.path.join(t, "out.csv")
        json.dump({"rows": rows}, open(inp, "w"))
        L.say("Sending %d record(s) through the published play %s." % (len(rows), L.PLAY_NAME))
        res = L.deepline("plays", "run", "--name", L.PLAY_NAME, "--input", "@" + inp, "--run-id-file", idf,
                         allow_fail=True, timeout=1800)
        run_id = L.find_run_id(L.load(idf, {})) or L.find_run_id(res)
        if not run_id:
            L.fail("The run did not start: %s" % (res.get("error") or res))
        if "exit" in res:
            L.fail("Run %s failed: %s (inspect: deepline runs get %s --json)" % (run_id, res.get("error"), run_id))
        L.deepline("runs", "export", run_id, "--dataset", "result.records", "--out", out)
        with open(out, newline="") as f:
            got = dict((r.get("source_ref"), r) for r in csv.DictReader(f))

    bad, lines = 0, []
    for ref, (cid, body, exp) in refs.items():
        live = got.get(ref)
        if not live:
            bad += 1
            lines.append((cid, "no row in the run's export", "", ""))
            continue
        found = live.get("found")
        try:
            found = json.loads(found) if found else None
        except json.JSONDecodeError:
            found = None
        local = L.check_record(body, enrich=(lambda _u: found) if found else None)
        same = all(str(live.get(k)) == str(local.get(k)) for k in ("active_at_company", "relationship", "check_status"))
        meets = all(live.get(k) == v for k, v in exp.items())
        if not (same and meets):
            bad += 1
        lines.append((cid, "%s / %s (%s%%)" % (live.get("active_at_company"), live.get("relationship"),
                                              live.get("verdict_confidence")),
                      "match" if same else "DIFFERS: local %s / %s" % (local["active_at_company"], local["relationship"]),
                      "" if not exp else ("as expected" if meets else "EXPECTED %s" % exp)))
    for r in lines:
        L.say("  %-28s play: %-34s %s  %s" % r)
    print(json.dumps({"checked": len(lines), "problems": bad, "run_id": run_id}))
    raise SystemExit(0 if not bad else 5)


if __name__ == "__main__":
    main()
