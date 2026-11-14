#!/usr/bin/env python3
"""Create (or adopt) the two customer-DB tables conference attendees are written into.

    python3 build_conference_writer.py conference-config.json [--dry-run]

    storage.conference_attendees   one row per (campaign_id, person_key)
    storage.conference_companies   one row per domain

Built ONCE PER WORKSPACE, not once per conference: the event, the campaign id and the dossier
all arrive as row values, so the same two tables serve every conference this workspace runs.
Re-running is a no-op over what exists and adds only missing columns.

`--dry-run` reads information_schema and prints which columns would be created and which
already exist and would be adopted. It writes nothing.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json                                    # noqa: E402

import conference_lib as C                     # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv[1:]
    if not args:
        raise SystemExit(__doc__.strip().splitlines()[2].strip())
    cfg = json.load(open(args[0]))

    print("== platform ==")
    ws = C.workspace_id()
    want = str(cfg.get("workspace_id") or "")
    if want and ws != want:
        raise SystemExit(
            "WORKSPACE MISMATCH: the deepline login resolves to workspace %s, the config "
            "expects %s.\nRefusing to build. Switch with `deepline org set <id>` and re-run."
            % (ws, want))
    cfg["workspace_id"] = ws
    print("workspace %s verified" % ws)
    link = bool(cfg.get("link_companies", True))
    tables = [C.ATTENDEES] + ([C.COMPANIES] if link else [])

    existing = C.existing_types(C.db(C.existing_columns_sql()))
    print("\n== columns ==")
    total_new = 0
    for t in tables:
        create, adopt, mismatch = C.column_plan(t, existing)
        total_new += len(create)
        state = "exists" if t in existing else "would be created" if dry else "creating"
        print("%s (%s): %d new, %d adopted" % (t, state, len(create), len(adopt)))
        for c, ty in create:
            print("  + %-26s %s" % (c, ty))
        for c, have, ty in mismatch:
            # Validation runs against the REAL type, so a value that does not fit is dropped
            # and named rather than failing the whole batch.
            print("  ! %-26s exists as %s, wanted %s — values that do not fit %s are DROPPED"
                  % (c, have, ty, have))

    if dry:
        print("\n-- dry run: nothing created. %d column(s) would be added." % total_new)
        return

    for t in tables:
        for stmt in C.ddl(t):
            C.db(stmt)
    # Read it back: the count printed is what the DB holds, not what was asked for.
    after = C.existing_types(C.db(C.existing_columns_sql()))
    for t in tables:
        create, _a, _m = C.column_plan(t, after)
        if create:
            raise SystemExit("%s is still missing %s after the build" % (t, [c for c, _ in create]))
        print("= %s: %d columns" % (t, len(after.get(t, {}))))

    wc = C.save_writer_config(cfg)
    print("\nA top-up from any future session needs only this file:\n  %s" % wc)


if __name__ == "__main__":
    main()
