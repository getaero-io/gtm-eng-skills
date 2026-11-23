#!/usr/bin/env python3
"""
Check, save and show a scoring rubric. Every other script loads rubrics through the same check.

    python3 rubric_tool.py check draft.json      # validate + print the card; saves nothing
    python3 rubric_tool.py save  draft.json      # validate, then save for this workspace
    python3 rubric_tool.py show  [--rubric NAME] # the card for a saved rubric
    python3 rubric_tool.py list                  # saved rubrics
    python3 rubric_tool.py export [--rubric NAME] # the saved rubric as JSON, to edit and save again

Saving a rubric whose content changed bumps its version, and every score carries "name vN", so
scores from two versions are never silently compared. Saved under
~/.local/state/<skill>/<deepline-workspace-id>/rubrics/.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_lib as L  # noqa: E402


def _read(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        L.fail("Could not read %s as JSON: %s" % (path, e))


def _content(r):
    return json.dumps({k: v for k, v in r.items() if k != "version"}, sort_keys=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("check", "save"):
        s = sub.add_parser(c)
        s.add_argument("file")
    for c in ("show", "export"):
        s = sub.add_parser(c)
        s.add_argument("--rubric")
    sub.add_parser("list")
    a = ap.parse_args()

    if a.cmd == "check":
        r = L.validate_rubric(_read(a.file))
        L.say(L.rubric_card(r))
        return
    if a.cmd == "list":
        for n in L.list_rubrics():
            L.say(n)
        return
    if a.cmd in ("show", "export"):
        r = L.load_rubric(a.rubric)
        if a.cmd == "export":
            print(json.dumps(r, indent=2))
        else:
            L.say(L.rubric_card(r))
        return

    r = L.validate_rubric(_read(a.file))
    p = L.rubric_path(r["name"])
    if os.path.exists(p):
        old = L.validate_rubric(L.load(p, {}))
        if _content(old) == _content(r):
            L.say("Unchanged: %s v%d is already saved." % (r["name"], old["version"]))
            return
        r["version"] = max(old["version"], r["version"]) + 1
    L.save(p, r)
    L.say(L.rubric_card(r))
    L.say("")
    L.say("Saved as %s v%d." % (r["name"], r["version"]))
    print(json.dumps({"saved": L.slug(r["name"]), "version": r["version"]}))


if __name__ == "__main__":
    main()
