#!/usr/bin/env python3
"""
Send ONE record through the published Deepline play and score the same record locally, then
compare. Agreement proves the published play, its baked-in mapping and the published rubric in
one go.

    python3 smoke_test.py --record '{"company_name": "…", "description": "…"}'
    python3 smoke_test.py --from-preview        # the first record of the latest local preview

Jev's probabilities can move slightly between two calls on the same input, so the scores are
compared within 3 points; the status and every confident answer must match, and the tier must
match unless the score sits within 3 points of a cut-off. Costs two ai_evaluate calls (a fraction
of a cent) and one play run.
"""
import argparse
import csv
import glob
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_lib as L  # noqa: E402


def answers(res, floor=0.6):
    """Each criterion's answer, leaving out the ones Jev was unsure of: a 49%/51% yes/no can
    legitimately flip between two calls on the same input."""
    try:
        return dict((c["id"], c["answer"]) for c in json.loads(res.get("criteria_json") or "[]")
                    if c.get("confidence") is None or c["confidence"] >= floor)
    except Exception:
        return {}


def run_published(play, row):
    """One run of the live revision; the scored row read back through `deepline runs export`."""
    t = tempfile.mkdtemp()
    inp, rid, out = os.path.join(t, "input.json"), os.path.join(t, "run-id.json"), os.path.join(t, "out.csv")
    with open(inp, "w") as f:
        json.dump({"rows": [row]}, f)
    res = L.deepline("plays", "run", "--name", play, "--input", "@" + inp, "--run-id-file", rid,
                     allow_fail=True, timeout=600)
    run_id = L.find_run_id(L.load(rid, {})) or L.find_run_id(res)
    if not run_id:
        L.fail("The play run did not start or returned no run id: %s" % json.dumps(res)[:600], code=5)
    if "exit" in res:
        L.fail("The play run %s failed: %s. Inspect: deepline runs get %s --json" % (run_id, str(res.get("error"))[:400], run_id), code=5)
    L.deepline("runs", "export", run_id, "--dataset", "result.records", "--out", out, timeout=300)
    with open(out, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        L.fail("Run %s exported no rows. Inspect: deepline runs get %s --json" % (run_id, run_id), code=5)
    return run_id, rows[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rubric")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--record", help="the record as JSON, keyed by the rubric's input names")
    src.add_argument("--from-preview", action="store_true")
    a = ap.parse_args()

    ws = L.workspace()
    rubric = L.load_rubric(a.rubric, ws["id"])
    st = L.load(os.path.join(L.state_dir(ws["id"]), "build-state.json"), {"plays": {}})
    rec = st.get("plays", {}).get(L.slug(rubric["name"])) or {}
    if not rec.get("play"):
        L.fail("The play for %r is not published yet: build_scorer.py" % rubric["name"])
    if rec.get("rubric_version") != rubric["version"]:
        L.fail("The play was built from v%s of this rubric and the saved rubric is v%d. Re-run "
               "build_scorer.py first." % (rec.get("rubric_version"), rubric["version"]))

    if a.from_preview:
        files = sorted(glob.glob(os.path.join(L.state_dir(ws["id"]), "previews", L.slug(rubric["name"]) + "-*.jsonl")),
                       key=os.path.getmtime)
        if not files:
            L.fail("No local preview yet: score_local.py")
        with open(files[-1]) as f:
            record = json.loads(f.readline())["input"]
    else:
        record = json.loads(a.record)
    record = dict((k, str(v)) for k, v in record.items() if v not in (None, "") and k in list(rubric["inputs"]) + ["source_ref"])
    record.setdefault("source_ref", "smoke-test")

    L.say("Scoring one %s locally and through the published play %s…" % (L.NOUN, rec["play"]))
    local = L.score_record(rubric, record)
    run_id, remote = run_published(rec["play"], record)
    L.say("  local    : %s, %s, %s" % (local["lead_score"], local["lead_tier"], local["score_reasons"][:120]))
    L.say("  deepline : %s, %s, %s" % (remote.get("lead_score"), remote.get("lead_tier"), str(remote.get("score_reasons"))[:120]))
    problems = []
    if remote.get("error"):
        problems.append("the play reports: %s" % remote["error"])
    near_cut = any(abs(float(local["lead_score"]) - t["min"]) <= 3 for t in rubric["tiers"] if t["min"] > 0)
    if remote.get("score_status") != local["score_status"] or (
            remote.get("lead_tier") != local["lead_tier"] and not near_cut):
        problems.append("tier/status differ")
    try:
        if abs(int(float(remote.get("lead_score"))) - int(local["lead_score"])) > 3:
            problems.append("scores differ by more than 3")
    except (TypeError, ValueError):
        problems.append("the play returned no score")
    fl = rubric["confidence_floor"]
    if answers(remote, fl) != answers(local, fl):
        problems.append("criterion answers differ: %s vs %s" % (answers(remote, fl), answers(local, fl)))
    print(json.dumps({"ok": not problems, "run_id": run_id, "local": local["lead_score"],
                      "deepline": remote.get("lead_score"), "problems": problems}))
    if problems:
        L.fail("Local and the published play disagree: " + "; ".join(problems), code=5)
    L.say("Match: the published play returns what the preview showed.")


if __name__ == "__main__":
    main()
