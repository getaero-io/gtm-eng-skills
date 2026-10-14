"""Drive the load: one upsert per batch, one ledger line per row the moment its batch returns.

    python3 load_drive.py --entity companies --state build-state.json \
            --csv <path> --map <mapping.json> --ledger ledger/companies.jsonl [--limit 10]

    python3 load_drive.py --entity contacts  --state build-state.json \
            --csv <path> --map <mapping.json> --ledger ledger/contacts.jsonl \
            --company-ledger ledger/companies.jsonl

    python3 load_drive.py verify --state build-state.json --map <mapping.json> \
            --csv <companies file> --ledger ledger/companies.jsonl \
            [--contacts-csv <contacts file> --contacts-ledger ledger/contacts.jsonl]

Nothing is held past its batch: the remaining work is recomputed from the ledger on every start,
so a run that dies resumes and a settled row is never written twice. Shard with `--shard i --of n`
over disjoint strided slices, which is why no lock is needed on the ledger.

`references/ledger-and-resume.md` carries the record shape, the settled-versus-retryable rule and
the resume breadcrumb this writes.
"""
import argparse
import datetime
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loader_lib as L                                               # noqa: E402


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- one row, one batch

def screen_row(item, mapping, entity, company_ids, company_verdicts, hold_unlinked):
    """Screen locally first. Returns (ledger line, None) for a row that settles without a write,
    or (None, built) for a row to write. A row with no match key never reaches the database."""
    key = item["row_key"]

    if item["duplicate"]:
        return L.ledger_line(key, "rejected_duplicate_row_key", at=now(),
                             reason="a row with this key was already seen in this file"), None

    match_key, _ = L.choose_match_key(item["row"], mapping, entity)
    if not match_key:
        return L.ledger_line(key, "rejected_no_match_key", at=now(),
                             reason="carries none of %s" % ", ".join(L.MATCH_KEYS[entity])), None

    company_id, unlinked_reason, link_source = None, None, None
    if entity == "contacts":
        ref = L.contact_join_key(item["row"], mapping)
        company_id = company_ids.get(ref) if ref else None
        if company_id is not None:
            # Where the company came from, read off its own ledger line rather than tracked
            # separately. `created_from` is written by the pre-pass; its absence means the
            # company came from the companies table.
            link_source = {"table": "already_in_table",
                           "contact": "created_from_contact"}.get(
                               (company_verdicts.get(ref) or {}).get("created_from"),
                               "company_table")
        else:
            # Distinguish WHY, so "not every contact got a company" is answerable from the ledger
            # rather than from a debugging session. Three different causes, three different fixes.
            if not ref:
                unlinked_reason = "no_company_reference"
            elif ref in company_verdicts:
                unlinked_reason = "company_%s" % company_verdicts[ref].get("status", "unsettled")
            else:
                unlinked_reason = "company_not_in_company_ledger"
            if hold_unlinked:
                return L.ledger_line(key, "skipped_no_company", at=now(),
                                     reason=unlinked_reason), None

    built = L.build_payload(item, mapping, entity, company_id)
    built.update(row_key=key, link_source=link_source, unlinked_reason=unlinked_reason)
    return None, built


def write_batch(table, batch, entity):
    """One INSERT for the batch; one ledger line per row. Only a match key that came back from
    RETURNING settles. A failed statement fails every row in it — they stay in the work set."""
    try:
        r = L.db(L.upsert_sql(table, [b["payload"] for b in batch]), max_rows=len(batch))
        ids = {row["match_key"]: row["id"] for row in r.get("rows") or []}
        err = ""
    except (RuntimeError, ValueError) as exc:
        ids, err = {}, str(exc)[:200]
    lines = []
    for b in batch:
        eid = ids.get(b["payload"]["match_key"])
        lines.append(L.ledger_line(
            b["row_key"], "completed" if eid else "failed", at=now(), entity_id=eid,
            match_key=b["match_key"], match_value=b["match_value"],
            associated=(b["linked"] if entity == "contacts" else None),
            link_source=b.get("link_source"), unlinked_reason=b.get("unlinked_reason"),
            dropped_fields=b["dropped_fields"],
            reason="" if eid else (err or "its match key did not come back from RETURNING")))
    return lines


# --------------------------------------------------------------------------- the pre-pass

def lookup_companies(table, keys):
    """Find companies already in the table by match key. One read for the whole set, free.

    Returns {(key_type, value): id}. A failed read raises: it is not evidence a company is absent.
    """
    if not keys:
        return {}
    mks = ["%s:%s" % k for k in keys]
    rows = L.db("select id, match_key from %s where match_key in (%s)"
                % (table, ", ".join(L.sql_literal(m) for m in mks)), max_rows=len(mks)).get("rows")
    return {tuple(r["match_key"].split(":", 1)): r["id"] for r in rows or []}


def company_stub(key_type, value, name):
    """The payload for a company created from a contact.

    ALWAYS named, falling back to the key itself. Two reasons: the Step 4 script promises the
    installer "a domain and a name", and a nameless row reads as broken in every list view.
    """
    return {"row_key": value, "match_key": "%s:%s" % (key_type, value), key_type: value,
            "org_name": name or value}


def prepass(a):
    """Resolve the companies the contacts reference but the companies table does not contain.

    Three outcomes per distinct company, and the pre-pass exists so all three are known before a
    single contact is written: already in the table, created here, or unresolvable.

    Anything it resolves is appended to the COMPANY ledger under the key the contacts load will
    look up, so the contacts phase needs no new logic and a re-run never repeats the work.
    """
    mapping = json.load(open(a.map, encoding="utf-8"))
    state = json.load(open(a.state, encoding="utf-8"))
    table = state["tables"]["companies"]
    rows = L.keyed_rows(L.read_table(a.contacts_csv), mapping, "contacts")
    known = L.company_id_map(a.ledger)

    needed, no_key = {}, []
    for item in rows:
        if item["duplicate"] or not L.choose_match_key(item["row"], mapping, "contacts")[0]:
            continue
        join = L.contact_join_key(item["row"], mapping)
        if join and join in known:
            continue                         # the companies table already covered it
        ktype, kval, src = L.company_key_for_contact(item["row"], mapping)
        if not kval:
            no_key.append(item["row_key"])
            continue
        entry = needed.setdefault(join or kval, {"type": ktype, "value": kval, "source": src,
                                                 "name": "", "contacts": 0})
        entry["contacts"] += 1
        entry["name"] = entry["name"] or L.company_name_for_contact(item["row"], mapping)

    distinct = sorted({(e["type"], e["value"]) for e in needed.values()})
    print("contacts referencing a company not in the companies table: %d, across %d distinct "
          "companies" % (sum(e["contacts"] for e in needed.values()), len(distinct)))
    print("contacts with nothing to identify a company by: %d" % len(no_key))
    if not needed:
        return 0

    resolved = lookup_companies(table, distinct)
    found = len(resolved)
    missing = [k for k in distinct if k not in resolved]
    created = set()
    if a.create and missing and not a.dry_run:
        names = {}
        for e in needed.values():
            names.setdefault((e["type"], e["value"]), e["name"])
        stubs = [company_stub(t, v, names.get((t, v), "")) for t, v in missing]
        r = L.db(L.upsert_sql(table, stubs), max_rows=len(stubs))
        for row in r.get("rows") or []:
            k = tuple(row["match_key"].split(":", 1))
            resolved[k] = row["id"]
            created.add(k)
    for k in distinct:
        print("  %-14s %-44s %s" % (k[0], k[1][:44], resolved.get(k)
                                    or ("would create" if a.create else "absent")))

    if not a.dry_run:
        for join, e in needed.items():
            eid = resolved.get((e["type"], e["value"]))
            if eid:
                # Ledgered under the key the CONTACTS load looks up, so that phase is unchanged.
                L.append_settled(a.ledger, L.ledger_line(
                    join, "completed", at=now(), entity_id=eid, match_key=e["type"],
                    match_value=e["value"],
                    created_from=("contact" if (e["type"], e["value"]) in created else "table")))

    if a.dry_run:
        # EVERY key in `distinct` is by definition identified — a contact with nothing to go on
        # never got here, it was counted in `no_key` above.
        print("\nalready in the table: %d   would be created: %d" % (found, len(missing)))
        print("(contacts with nothing to identify a company by are the %d counted above, and no "
              "flag changes that number)" % len(no_key))
        return 0
    print("\nalready in the table: %d   created here: %d   still unresolved: %d"
          % (found, len(created), len(distinct) - len(resolved)))
    if created:
        print("NOTE: the %d created here carry only their match key and a name. They have none of "
              "the attributes a companies table would have given them — say so, and hand back the "
              "list so they can be loaded properly later." % len(created))
    return 0


# --------------------------------------------------------------------------- the pass

def run(a):
    mapping = json.load(open(a.map, encoding="utf-8"))
    state = json.load(open(a.state, encoding="utf-8"))
    table = (state.get("tables") or {}).get(a.entity)
    if not table:
        raise SystemExit("%s was not built. Run build_loader.py build first." % a.entity)

    rows = L.keyed_rows(L.read_table(a.csv), mapping, a.entity)
    todo = L.remaining(rows, a.ledger)
    if a.of > 1:
        todo = todo[a.shard - 1::a.of]
    if a.limit:
        todo = todo[:a.limit]

    company_ids, company_verdicts = {}, {}
    if a.entity == "contacts":
        company_ids = L.company_id_map(a.company_ledger)
        company_verdicts = L.fold_ledger(a.company_ledger)
        print("company ids folded from the ledger: %d of %d settled company rows"
              % (len(company_ids), len(company_verdicts)))

        # A wrong or missing `company_ref_column` unlinks every contact, every row still loads,
        # and the run reports success end to end — so it is caught HERE, before anything is
        # written. Loading the whole file unlinked is not a mistake worth making quietly.
        ref_col = mapping.get("company_ref_column")
        resolvable = sum(1 for i in todo
                         if L.contact_join_key(i["row"], mapping) in company_ids)
        print("contacts in this pass that resolve to a company: %d of %d, via %r"
              % (resolvable, len(todo), ref_col))
        if todo and not resolvable and not a.allow_all_unlinked:
            raise SystemExit(
                "\nSTOPPING: not one contact in this pass resolves to a company, so every row "
                "would load with no company attached.\n"
                "  the company reference column is %r\n"
                "  the company ledger holds %d ids, keyed like: %s\n"
                "  contacts carry values like: %s\n"
                "Those two have to be the SAME key. Fix `company_ref_column` in the mapping, or "
                "the row key on the companies side, then run this again. If the contacts really "
                "have no companies, pass --allow-all-unlinked and say so in the output."
                % (ref_col, len(company_ids),
                   ", ".join(list(company_ids)[:3]) or "(none)",
                   ", ".join(str(i["row"].get(ref_col)) for i in todo[:3]) if ref_col
                   else "(no column configured)"))
    print("shard %d/%d — %d rows to do" % (a.shard, a.of, len(todo)))

    write_resume(a, mapping)
    to_write = []
    for item in todo:
        line, built = screen_row(item, mapping, a.entity, company_ids, company_verdicts,
                                 a.hold_unlinked)
        if line:
            L.append_settled(a.ledger, line)  # settles without a write
        else:
            to_write.append(built)
    done = 0
    for batch in L.batches(to_write, a.batch):
        for line in write_batch(table, batch, a.entity):
            L.append_settled(a.ledger, line)  # the moment the batch returns
        done += len(batch)
        print("  wrote %d/%d" % (done, len(to_write)))
        time.sleep(a.pace)

    tally = L.counts_by_status(a.ledger)
    print("\nledger now: %s" % tally)
    if a.entity == "contacts":
        why, how = {}, {}
        for rec in L.fold_ledger(a.ledger).values():
            if rec.get("status") != "completed":
                continue
            if rec.get("associated"):
                k = rec.get("link_source") or "unknown"
                how[k] = how.get(k, 0) + 1
            else:
                k = rec.get("unlinked_reason") or "unknown"
                why[k] = why.get(k, 0) + 1
        print("company attached, by where it came from: %s" % (how or "none"))
        print("loaded with no company attached: %s" % (why or "none"))
    write_resume(a, mapping, tally)
    return 0


# --------------------------------------------------------------------------- verify

def expected_populated(rows, ledger_path, col, ftype):
    """How many DISTINCT records should carry this field.

    Not "how many CSV rows had a value" — that number is wrong twice over. Rows that never loaded
    do not count. And rows that share a match key landed on ONE record, so counting them
    separately invents a shortfall that is really a collision doing what the report said it would.
    """
    settled = L.fold_ledger(ledger_path)
    ids = set()
    for item in rows:
        rec = settled.get(item["row_key"])
        if not rec or rec.get("status") != "completed" or not rec.get("entity_id"):
            continue
        if col in (rec.get("dropped_fields") or []):
            continue
        v = item["row"].get(col)
        if not L.blank(v) and L.parses_as(v, ftype):
            ids.add(rec["entity_id"])
    return len(ids)


def ids_literal(ids):
    """A bigint array literal of this load's ids. Every id came back from RETURNING; still checked."""
    return "'{%s}'::bigint[]" % ",".join(str(int(i)) for i in sorted(ids))


def populated(table, column, ids):
    """How many of THESE ids carry a value in this column. Scoped to the load, never the table:
    a table-wide count passes a field on rows some earlier load wrote."""
    r = L.db("select count(%s) as n from %s where id = any(%s)"
             % (L.qident(column), table, ids_literal(ids)))
    return (r.get("rows") or [{}])[0].get("n") or 0


def verify(a):
    """Ask the table what it holds, and hold that against what should have landed.

    The ledger says what was SENT. A dropped value, a COALESCE that kept an older value, or a
    batch that settled fewer rows than it carried are all invisible in the ledger's own counts.
    """
    mapping = json.load(open(a.map, encoding="utf-8"))
    sources = {"companies": (a.csv, a.ledger), "contacts": (a.contacts_csv, a.contacts_ledger)}

    # A VERIFICATION THAT CHECKED NOTHING MUST NOT REPORT SUCCESS. Measured on a real run: called
    # with `--ledger` and no `--csv`, this skipped every entity, checked zero fields, and printed
    # "every field matches what should have landed". Refuse before the loop rather than after.
    usable = [e for e, (path, led) in sources.items()
              if path and led and mapping.get("fields", {}).get(e)]
    if not usable:
        raise SystemExit(
            "NOTHING TO VERIFY, so nothing is being claimed.\n"
            "  companies needs --csv AND --ledger; contacts needs --contacts-csv AND "
            "--contacts-ledger.\n"
            "  got: --csv %r --ledger %r --contacts-csv %r --contacts-ledger %r\n"
            "Re-run with the file each ledger belongs to."
            % (a.csv, a.ledger, a.contacts_csv, a.contacts_ledger))
    for entity, (path, led) in sources.items():
        if led and not path:
            print("!! %s: a ledger was given but not its file, so %s IS NOT BEING CHECKED"
                  % (entity, entity))
        elif path and not led:
            print("!! %s: a file was given but not its ledger, so %s IS NOT BEING CHECKED"
                  % (entity, entity))

    tables = json.load(open(a.state, encoding="utf-8"))["tables"]
    mine = {}
    for entity, (_p, led) in sources.items():
        mine[entity] = {r["entity_id"] for r in L.fold_ledger(led or "").values()
                        if r.get("status") == "completed" and r.get("entity_id")} if led else set()
    print("scoped to this load: %d companies, %d contacts"
          % (len(mine["companies"]), len(mine["contacts"])))

    print("%-26s %-9s %-8s %9s %9s  %s"
          % ("field", "entity", "type", "expected", "in your load", ""))
    ok, checked = True, 0
    for entity, (path, ledger) in sources.items():
        if not path or not ledger or not mapping.get("fields", {}).get(entity):
            continue
        rows = L.keyed_rows(L.read_table(path), mapping, entity)
        for col, spec in mapping["fields"][entity].items():
            ftype = spec["type"] if isinstance(spec, dict) else spec
            want = expected_populated(rows, ledger, col, ftype)
            got = populated(tables[entity], L.column_for(col, spec), mine[entity])
            flag = "ok" if got >= want else "SHORT BY %d" % (want - got)
            ok = ok and got >= want
            checked += 1
            print("%-26s %-9s %-8s %9d %9d  %s" % (col[:26], entity, ftype, want, got, flag))

    if a.contacts_ledger:
        # The link the table holds, not the one the loader believes it sent.
        got = populated(tables["contacts"], "company_id", mine["contacts"])
        want = len({r["entity_id"] for r in L.fold_ledger(a.contacts_ledger).values()
                    if r.get("associated") and r.get("entity_id")})
        ok = ok and got >= want
        print("%-26s %-9s %-8s %9d %9d  %s"
              % ("linked to a company", "contacts", "-", want, got,
                 "ok" if got >= want else "SHORT BY %d" % (want - got)))

    if not checked:
        raise SystemExit("\nNo field was actually compared, so there is nothing to report. That "
                         "is a failure, not a pass — check the mapping has fields for the entities "
                         "whose ledgers you passed.")
    print("\n%d fields compared. %s" % (checked,
          "Every one matches what should have landed." if ok else
          "AT LEAST ONE FIELD IS SHORT — name it and both numbers; do not reconcile it away."))
    return 0 if ok else 1


# --------------------------------------------------------------------------- resume breadcrumb

RESUME = """# Resume this load

State on disk (this is the only state that matters):

- ledger:        {ledger}
- mapping:       {map}
- build state:   {state}
- source CSV:    {csv}

Ledger counts at {when}: {tally}

## Next command

```
{cmd}
```

## Do not repeat

- The tables and columns already exist. `build_loader.py build` is safe to re-run; every
  statement is `IF NOT EXISTS`, so it creates only what is missing.
- Settled rows are never re-written. `failed` and `timeout` are not settled and the next pass picks
  them up; do not change anything before retrying one.
"""


def write_resume(a, mapping, tally=None):
    cmd = ("python3 scripts/load_drive.py --entity %s --state %s --csv %s --map %s --ledger %s"
           % (a.entity, a.state, a.csv, a.map, a.ledger))
    if a.entity == "contacts":
        cmd += " --company-ledger %s" % a.company_ledger
    body = RESUME.format(ledger=a.ledger, map=a.map, state=a.state, csv=a.csv, when=now(),
                         tally=tally if tally is not None else L.counts_by_status(a.ledger),
                         cmd=cmd)
    path = os.path.join(os.path.dirname(a.ledger) or ".", "RESUME.md")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(body)


# --------------------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", nargs="?", default="load",
                    choices=("load", "verify", "prepass"))
    ap.add_argument("--entity", choices=("companies", "contacts"))
    ap.add_argument("--state", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--contacts-csv")
    ap.add_argument("--ledger")
    ap.add_argument("--company-ledger")
    ap.add_argument("--contacts-ledger")
    ap.add_argument("--shard", type=int, default=1)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--pace", type=float, default=0.5, help="seconds between batches")
    ap.add_argument("--batch", type=int, default=200, help="rows per INSERT")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--allow-all-unlinked", action="store_true",
                    help="proceed even when NO contact resolves to a company. Only for a TAM "
                         "that genuinely has no company links")
    ap.add_argument("--create", action="store_true",
                    help="prepass only: create the companies that are in neither the companies "
                         "file nor the table. Opt-in — it writes company records nobody listed, "
                         "carrying only a match key and a name")
    ap.add_argument("--dry-run", action="store_true",
                    help="prepass only: resolve and report, create nothing")
    ap.add_argument("--hold-unlinked", action="store_true",
                    help="hold a contact whose company has not loaded instead of loading it "
                         "without a company link")
    a = ap.parse_args(argv)

    if a.command == "verify":
        return verify(a)
    if a.command == "prepass":
        for need in ("contacts_csv", "ledger"):
            if not getattr(a, need):
                ap.error("prepass needs --%s" % need.replace("_", "-"))
        return prepass(a)
    for need in ("entity", "csv", "ledger"):
        if not getattr(a, need):
            ap.error("load needs --%s" % need)
    if a.entity == "contacts" and not a.company_ledger:
        ap.error("contacts need --company-ledger: the company record ids come from it")
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
