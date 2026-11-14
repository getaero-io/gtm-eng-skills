"""Lay the file beside the tables, then create the two tables and their columns.

    python3 build_loader.py match --prefix tam --companies <file[#tab]> --contacts <file[#tab]>
    python3 build_loader.py build --prefix tam --map <mapping.json> [--dry-run] --out build-state.json

`match` prints the columns the two tables already hold (with how many rows carry each and one
value) beside the columns in the file. `build` creates `storage.<prefix>_companies` and
`storage.<prefix>_contacts` in the Deepline customer DB if they are missing, and adds a column per
confirmed field that is missing. Every statement is `IF NOT EXISTS`, so a second build over the
same prefix creates only the gap and a lost `build-state.json` strands nothing.

It refuses to reuse a column whose stored type disagrees with the mapping, before running anything.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loader_lib as L                                               # noqa: E402

ENTITIES = ("companies", "contacts")


def existing_columns(prefix, entity):
    """The columns this table already holds, as [{id, name, dataType}]. Empty when it does not exist."""
    name = "%s_%s" % (prefix, entity)
    L.qident(name)
    rows = L.db("select column_name, data_type from information_schema.columns "
                "where table_schema = 'storage' and table_name = %s order by ordinal_position"
                % L.sql_literal(name)).get("rows") or []
    return [{"id": r["column_name"], "name": r["column_name"],
             "dataType": L.storage_type(r["data_type"])} for r in rows]


def planned_columns(mapping, entity):
    """{column: loader type} for every confirmed field."""
    return {L.column_for(col, spec): (spec["type"] if isinstance(spec, dict) else spec)
            for col, spec in mapping.get("fields", {}).get(entity, {}).items()}


def conflicts(mapping, entity, live):
    """Every confirmed field whose column exists, or is a base column, with a different type."""
    stored = {c["id"]: c["dataType"] for c in live}
    stored.update({c: "text" for c in L.BASE_COLUMNS[entity]})
    return [(c, stored[c], t) for c, t in planned_columns(mapping, entity).items()
            if c in stored and L.type_conflict(stored[c], t)]


def field_usage(prefix, entity, column):
    """How many rows already carry this column, and one value it holds.

    A column that exists and a column that is IN USE are different facts, and only the second tells
    you whether reusing it would sit beside real data or overwrite it.
    """
    try:
        r = L.db("select count(%s) as n, min(%s::text) as v from %s"
                 % (L.qident(column), L.qident(column), L.table_name(prefix, entity)))
    except RuntimeError:
        return None, ""
    row = (r.get("rows") or [{}])[0]
    return row.get("n"), row.get("v") or ""


def match_command(a):
    """Lay the two lists side by side. The MATCHING is the agent's, not this script's.

    Everything here is fact: the columns in the file with what they read as and two real values,
    and the columns the table already holds with their stored types. The only matches it asserts
    are same-label ones, which need no judgment. A lookup table of known spellings was tried and
    could not see `staff_count`, `# of employees` or a header in another language, and a miss
    printed "no field yet" -- which reads as an answer rather than as nobody having looked.
    """
    shown = False
    for entity, spec in (("companies", a.companies), ("contacts", a.contacts)):
        if not spec:
            continue
        shown = True
        rows = L.read_table(spec)
        existing = existing_columns(a.prefix, entity)

        # SHOW WHAT EACH COLUMN ALREADY HOLDS, not just that it exists. Measured on a cold run
        # (against Clay Audiences fields, 2026): the agent passed over two populated fields because
        # their names read like test artifacts and created duplicates beside them.
        print("\n=== %s: columns %s already has ===" % (entity, L.table_name(a.prefix, entity)))
        if not existing:
            print("  (table does not exist yet — `build` creates it)")
        print("  %-26s %-9s %-9s %s" % ("column", "stores", "populated", "a value it holds"))
        for f in existing:
            n, sample = field_usage(a.prefix, entity, f["id"])
            print("  %-26s %-9s %-9s %s" % (f["id"], f["dataType"], "-" if n is None else n,
                                            (sample or "")[:30]))

        print("\n=== %s: columns in the file ===" % entity)
        print("  %-26s %-9s %-34s %s" % ("column", "reads as", "two values", "same-label match"))
        for col in (rows[0].keys() if rows else []):
            vals = [r.get(col) for r in rows]
            t = L.infer_type(vals)
            sample = " | ".join(str(v).strip() for v in vals if not L.blank(v))[:34]
            hit = L.certain_field_match(col, existing)
            if hit and L.type_conflict(hit["stored_type"], t):
                note = "%s -- TYPE CONFLICT, stores %s" % (hit["field_id"], hit["stored_type"])
            else:
                note = hit["field_id"] if hit else ""
            print("  %-26s %-9s %-34s %s" % (col[:26], t, sample, note))

    if not shown:
        raise SystemExit("match needs --companies and/or --contacts")
    print("""
Now do the matching yourself, against the two lists above. For each column decide one of:
  - it belongs in a column that already exists -> put that column name in `field_id`
  - it is genuinely new                        -> give it a `field_name` and a type
  - it does not belong in the table            -> leave it out

Say WHY for every match that is not a same-label one, and show the whole thing for correction
before anything is created. Where a column would reuse one that stores a different type, that is
not a match -- retype it or give it its own column. The build refuses that reuse anyway.""")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("match", "build"))
    ap.add_argument("--prefix", default="tam",
                    help="tables are storage.<prefix>_companies and storage.<prefix>_contacts")
    ap.add_argument("--map")
    ap.add_argument("--companies", metavar="FILE[#TAB]")
    ap.add_argument("--contacts", metavar="FILE[#TAB]")
    ap.add_argument("--out", default="build-state.json")
    ap.add_argument("--dry-run", action="store_true", help="print the SQL, run nothing")
    a = ap.parse_args(argv)
    L.qident(a.prefix)

    if a.command == "match":
        return match_command(a)
    if not a.map:
        ap.error("build needs --map")
    mapping = json.load(open(a.map, encoding="utf-8"))

    # Both tables, always: contacts carry a foreign key into companies, and a people-only run
    # still needs somewhere for the companies it finds or creates.
    refused, statements = [], []
    for entity in ENTITIES:
        live = [] if a.dry_run else existing_columns(a.prefix, entity)
        refused += [(entity,) + c for c in conflicts(mapping, entity, live)]
        have = {c["id"] for c in live}
        plan = planned_columns(mapping, entity)
        new = sorted(c for c in plan if c not in have and c not in L.BASE_COLUMNS[entity])
        print("%s: %d column(s) %s, %d already there"
              % (L.table_name(a.prefix, entity), len(new),
                 "would be added" if a.dry_run else "to add", len(plan) - len(new)))
        statements += L.ddl(a.prefix, entity, plan)
    if refused:
        raise SystemExit("REFUSING to build: these reuse a column whose stored type disagrees —\n%s\n"
                         "Retype the column in the mapping or give it a column of its own."
                         % "\n".join("  %s.%s stores %s, mapping says %s" % r for r in refused))
    for sql in statements:
        if a.dry_run:
            print("  " + sql)
        else:
            L.db(sql)
    if a.dry_run:
        return 0
    state = {"prefix": a.prefix, "map": os.path.abspath(a.map),
             "tables": {e: L.table_name(a.prefix, e) for e in ENTITIES}}
    json.dump(state, open(a.out, "w", encoding="utf-8"), indent=2, sort_keys=True)
    print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
