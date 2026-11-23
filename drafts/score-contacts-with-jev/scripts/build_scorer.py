#!/usr/bin/env python3
"""
Build (or update) the Deepline play that scores records with a saved rubric, and publish it.

    python3 build_scorer.py --plan        # render the play and run `deepline plays check`; publishes nothing
    python3 build_scorer.py               # render, check, publish; records the webhook URL

The play, "jev-lead-score-<accounts|contacts>-<rubric>":

  input: {"csv": "file.csv"} | {"rows": [...]} | one record (a webhook POST body)
    → records (dataset, one row per record)
        → jev       intake (rules in code, which questions have their data) → one ai_evaluate call,
                    skipped when a rule disqualified the record, a required input is missing, or
                    nothing can be asked; a failed call is kept as data, never a low score
        → verdict   the score: every output key, always present
        → one column per output key, so `deepline runs export` gives a flat CSV
  returns {records}

The scoring code is rendered from the same source the preview ran (jev_lib.CORE), with the rubric
and the column mapping the preview confirmed baked in. The play file is written to the state
folder (and to --out, if given) so it can be read, diffed and re-published.

Idempotent: publishing the same file again makes a new revision of the same play name. A changed
rubric (new version) renders a new file under the same name; the old revision stays in the
play's history (`deepline plays versions`).
"""
import argparse
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_lib as L  # noqa: E402


def find_key(obj, key):
    """First value under `key` anywhere in a JSON document (field placement was not observed live)."""
    if isinstance(obj, dict):
        if obj.get(key):
            return obj[key]
        for v in obj.values():
            got = find_key(v, key)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = find_key(v, key)
            if got:
                return got
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rubric")
    ap.add_argument("--map", action="append", default=[], help="key=Column, overriding the mapping the preview saved")
    ap.add_argument("--out", help="also write the .play.ts here (e.g. into the project folder)")
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()

    ws = L.workspace()
    rubric = L.load_rubric(a.rubric, ws["id"])
    sd = L.state_dir(ws["id"])
    saved = L.load(os.path.join(sd, "mapping-%s.json" % L.slug(rubric["name"])), {}).get("mapping") or {}
    mapping = {k: saved.get(k) for k in rubric["inputs"]}
    for o in a.map:
        k, _, v = o.partition("=")
        if k.strip() not in mapping:
            L.fail("--map: %r is not one of the rubric's inputs (%s)" % (k, ", ".join(mapping)))
        mapping[k.strip()] = v.strip() or None

    name = L.play_name(rubric)
    plays_dir = os.path.join(sd, "plays")
    os.makedirs(plays_dir, exist_ok=True)
    path = os.path.join(plays_dir, name + ".play.ts")
    with open(path, "w") as f:
        f.write(L.render_play(rubric, mapping))
    if a.out:
        with open(a.out, "w") as f:
            f.write(L.render_play(rubric, mapping))

    chk = L.deepline("plays", "check", path, allow_fail=True, timeout=300)
    data = chk.get("data") if "exit" in chk else chk
    if not isinstance(data, dict) or not data.get("valid"):
        errs = (data or {}).get("errors") if isinstance(data, dict) else None
        L.fail("`deepline plays check` rejected the generated play %s: %s" % (path, json.dumps(errs or chk)[:1500]), code=4)
    artifact = data.get("artifactHash")

    mapped = ", ".join("%s<-%s" % (k, v) for k, v in mapping.items() if v and v != k) or "none (inputs by their own names)"
    if a.plan:
        L.say("Would publish in Deepline workspace %s:" % (ws["name"] or ws["id"]))
        L.say("  play %s   (webhook trigger; also runs on a CSV or a list of rows)" % name)
        L.say("  Rubric %s v%d: %d rules, %d Jev questions; Jev through ai_evaluate (%s)."
              % (rubric["name"], rubric["version"], len(rubric["rules"]), len(rubric["questions"]), L.JEV["model"]))
        L.say("  Column mapping baked in: %s" % mapped)
        L.say("  `deepline plays check`: valid (%s). File: %s" % (data.get("summary") or "ok", path))
        print(json.dumps({"play": name, "file": path, "valid": True, "artifactHash": artifact}))
        return

    L.say("Publishing %s in Deepline workspace %s" % (name, ws["name"] or ws["id"]))
    args = ["plays", "publish", path]
    if artifact:
        args += ["--expected-artifact", artifact]
    pub = L.deepline(*args, timeout=300)
    url = find_key(pub, "endpointUrl")
    st_path = os.path.join(sd, "build-state.json")
    st = L.load(st_path, {"plays": {}})
    st.setdefault("plays", {})[L.slug(rubric["name"])] = {
        "play": name, "file": path, "rubric_version": rubric["version"], "mapping": mapping,
        "webhook_url": url, "artifactHash": artifact, "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    L.save(st_path, st)
    print(json.dumps({"play": name, "published": True, "webhook_url": url, "file": path}))
    if not url:
        L.say("Published, but no webhook URL came back in the publish output. Find it with: "
              "deepline plays get %s --json (triggerBindings[].endpointUrl)." % name)


if __name__ == "__main__":
    main()
