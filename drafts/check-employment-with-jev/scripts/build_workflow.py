#!/usr/bin/env python3
"""
Build (or update) and publish the Deepline play "person-active-at-company-jev"
("Person Active At Company (Jev)").

    python3 build_workflow.py --plan        # render and check the play; changes nothing in the workspace
    python3 build_workflow.py               # render, check, publish; prints the webhook URL

The play, per person (a CSV, a list of rows, or one webhook record):

  records (dataset)
    → found     crustdata_v3_person_enrich, only for a person sent with a LinkedIn URL and no usable
                profile (and not skip_enrichment); a failed purchase comes back no_profile
    → jev       ai_evaluate (typesafe-ai/jev): the small questions about each role, one request;
                skipped when there is nothing to ask; a failed call comes back failed, never a verdict
    → verdict   the code in active_lib.CORE combines the answers
    → one column per output key, so an export is a flat CSV

The play file is written to this skill's state folder and checked with `deepline plays check`
(free) before any publish. Publishing makes it live for the workspace and opens its webhook.
Re-running after a code change publishes a new revision under the same name.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import active_lib as L  # noqa: E402


def endpoint(obj):
    """The webhook URL in `plays publish --json` output (triggerBindings[].endpointUrl)."""
    if isinstance(obj, dict):
        if isinstance(obj.get("endpointUrl"), str):
            return obj["endpointUrl"]
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            got = endpoint(v)
            if got:
                return got
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()

    ws = L.workspace()
    d = L.state_dir(ws["id"])
    path = os.path.join(d, L.PLAY_NAME + ".play.ts")
    with open(path, "w") as f:
        f.write(L.render_play())
    chk = L.deepline("plays", "check", path, allow_fail=True)
    chk = chk.get("data", chk) if "exit" in chk else chk
    if not chk.get("valid"):
        L.fail("`deepline plays check` refused the play (%s): %s" % (path, chk.get("errors") or chk.get("error")), code=6)
    L.say("Play %s checked: %s" % (L.PLAY_NAME, chk.get("summary") or "valid"))
    L.say("  per person: %s only when a profile must be bought (priced per matched record); "
          "%s (%s) when there is something to ask." % (L.ENRICH_TOOL, L.JEV["tool"], L.JEV["model"]))
    L.say("  file: %s" % path)
    if a.plan:
        L.say("Would publish it to Deepline workspace %s, with a webhook." % (ws["name"] or ws["id"]))
        return

    pub = L.deepline("plays", "publish", path)
    url = endpoint(pub)
    st_path = os.path.join(d, "build-state.json")
    L.save(st_path, {"play": L.PLAY_NAME, "file": path, "webhook_url": url, "published": True})
    L.say("Published %s in %s." % (L.PLAY_NAME, ws["name"] or ws["id"]))
    if not url:
        L.say("  The publish output named no webhook URL; read it with `deepline plays get %s --json`." % L.PLAY_NAME)
    print(json.dumps({"play": L.PLAY_NAME, "webhook_url": url, "published": True}))


if __name__ == "__main__":
    main()
