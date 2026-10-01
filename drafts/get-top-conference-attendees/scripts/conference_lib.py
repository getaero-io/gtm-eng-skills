"""The customer-DB side of the conference-attendee writer: paths, SQL, and the one CLI call.

Credential rule, and it is absolute: this module never reads, holds or writes an API key of
any kind. The conference service's key is handled only by the driver, only from the
environment, and is never passed on a command line — a key in an argument is visible in
`ps` to every process on the machine. Everything this module drives is `deepline db query`,
authenticated by the installer's own Deepline login.

The destination is two tables in the Deepline customer DB (Postgres), written only under the
`storage` schema, which is the only schema `deepline db query` lets an agent write:

    storage.conference_attendees   one row per (campaign_id, person_key)
    storage.conference_companies   one row per domain

Every write is `INSERT ... ON CONFLICT DO UPDATE SET col = COALESCE(EXCLUDED.col, col)`, so
the same person written twice is updated, never duplicated, and a value this campaign does
not know never clears one a previous write filled.
"""

import json
import os
import subprocess
import tempfile
import time

import audience_lib as A

ATTENDEES = "storage.conference_attendees"
COMPANIES = "storage.conference_companies"

# Where the writer's config, ledgers and run files live. Keyed on the Deepline WORKSPACE, never
# on the campaign, because the campaign config is per-run and the tables are not.
DEFAULT_WRITER_HOME = "~/.deepline-conference-writer"


def writer_dir(cfg):
    base = cfg.get("writer_dir") or os.path.join(DEFAULT_WRITER_HOME,
                                                 str(cfg.get("workspace_id", "unknown")))
    return os.path.expanduser(base)


def run_dir(cfg, date=None):
    """Where a run's own files belong: config, campaign result, breadcrumbs.

    `~/.deepline-conference-writer/<workspace>/runs/<date>/`. Durable, next to the writer
    config and the ledgers, and — the part that matters — **outside every git repository**.
    Three separate cold runs each invented a folder inside whatever repo the session started
    in, and that output carries real email addresses, the path the key was written to, and
    live share tokens. One `git add -A` publishes all of it.
    """
    date = date or time.strftime("%Y-%m-%d")
    return os.path.join(writer_dir(cfg), "runs", date)


def writer_config_path(cfg):
    """The workspace-level config a LATER session can run a top-up from.

    A top-up needs none of the campaign's own inputs — no domain, no goals, no conference. It
    needs the workspace, whether companies are linked, and where the key is. Those are writer
    facts, so they are written beside the writer and a cold session weeks later can find them
    from `deepline auth status --json` alone."""
    return os.path.join(writer_dir(cfg), "writer-config.json")


WRITER_CONFIG_KEYS = ("workspace_id", "link_companies", "key_file", "writer_dir")


def save_writer_config(cfg):
    out = {k: cfg[k] for k in WRITER_CONFIG_KEYS if k in cfg and cfg[k] is not None}
    out["_what"] = ("Workspace-level config for the conference-attendee writer. A top-up "
                    "needs only this file — point drive_load.py at it and ask for the "
                    "campaign by name.")
    path = writer_config_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)
    return path


# ------------------------------------------------------------------- the CLI


def deepline_json(*args):
    r = subprocess.run(["deepline", *args, "--json"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("deepline %s failed (%s): %s"
                           % (" ".join(args[:2]), r.returncode, (r.stderr or r.stdout)[:600]))
    return json.loads(r.stdout or "{}")


def db(sql):
    """Run one SQL statement. Returns the response's `rows`.

    The SQL goes through a file (`--sql @file`), never an argument: dossier prose is long and
    full of quotes, and an argument is the wrong place for either."""
    fd, path = tempfile.mkstemp(suffix=".sql")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(sql)
        return deepline_json("db", "query", "--sql", "@" + path).get("rows") or []
    finally:
        os.unlink(path)


def workspace_id():
    who = deepline_json("auth", "status")
    return str((who.get("workspace") or {}).get("id") or "")


# ----------------------------------------------------------------- SQL, pure


def sql_literal(v):
    """One value as a Postgres literal. THIS IS THE TRUST BOUNDARY: dossier text is written by
    a third party, so it is quoted here and nowhere else.

    With `standard_conforming_strings = on` (verified on the customer DB) a backslash is an
    ordinary character and doubling `'` is the complete escape. A NUL byte cannot be stored in
    a Postgres text value at all, so it is refused rather than silently truncated."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        raise ValueError("booleans are not in the field plan")
    if isinstance(v, (int, float)):
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("non-finite number")
        return repr(v)
    s = str(v)
    if "\x00" in s:
        raise ValueError("NUL byte in a value")
    return "'" + s.replace("'", "''") + "'"


def _ident(name):
    if not name.replace("_", "").isalnum():
        raise ValueError("bad identifier %r" % name)
    return name


def people_columns():
    """(column, plan type) for the attendee table, identity columns first."""
    cols = [("campaign_id", "text"), ("person_key", "text"), ("match_key", "text")]
    cols += [(c, "text") for c in A.PEOPLE_BUILTINS]
    seen = {c for c, _ in cols}
    cols += [(src, t) for _d, t, src in A.PEOPLE_FIELDS if src not in seen]
    return cols


def company_columns():
    cols = [(c, "text") for c in A.COMPANY_BUILTINS]
    seen = {c for c, _ in cols}
    cols += [(src, t) for _d, t, src in A.COMPANY_FIELDS if src not in seen]
    return cols


TABLES = {
    ATTENDEES: (people_columns, ("campaign_id", "person_key")),
    COMPANIES: (company_columns, ("domain",)),
}


def ddl(table):
    """CREATE TABLE IF NOT EXISTS, then ADD COLUMN IF NOT EXISTS per column.

    The second half is what lets a column added to the field plan later reach a table built
    before it existed: re-running the build adds exactly the gap."""
    cols_fn, key = TABLES[table]
    cols = cols_fn()
    body = ",\n  ".join("%s %s" % (_ident(c), A.SQL_TYPES[t]) for c, t in cols)
    out = ["CREATE TABLE IF NOT EXISTS %s (\n  %s,\n  updated_at timestamptz DEFAULT now(),\n"
           "  PRIMARY KEY (%s)\n)" % (table, body, ", ".join(key))]
    out += ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s %s" % (table, _ident(c), A.SQL_TYPES[t])
            for c, t in cols]
    return out


PG_TO_PLAN = {"numeric": "number", "integer": "number", "bigint": "number",
              "double precision": "number", "real": "number", "smallint": "number",
              "date": "date"}


def existing_columns_sql():
    return ("SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'storage' AND table_name IN "
            "('conference_attendees', 'conference_companies')")


def existing_types(rows):
    """{"storage.<table>": {column: plan type}} from an information_schema read.

    Validation runs against these — the column's REAL type — not the type the plan wanted, so a
    column somebody retyped by hand is respected rather than fought."""
    out = {}
    for r in rows:
        t = "storage." + r["table_name"]
        out.setdefault(t, {})[r["column_name"]] = PG_TO_PLAN.get(r["data_type"], "text")
    return out


def column_plan(table, existing):
    """(to_create, adopted, mismatched) against what the DB already holds for this table."""
    have = existing.get(table, {})
    cols_fn, _ = TABLES[table]
    create, adopt, mismatch = [], [], []
    for c, t in cols_fn():
        if c not in have:
            create.append((c, t))
        elif have[c] != t:
            mismatch.append((c, have[c], t))
        else:
            adopt.append(c)
    return create, adopt, mismatch


def upsert_sql(table, rows):
    """One multi-row upsert. Returns SQL that RETURNs the key of every row it wrote.

    Only a returned key settles in the ledger: the RETURNING list is the positive evidence, so
    a row that silently did not land can never be counted as written."""
    if not rows:
        raise ValueError("no rows")
    cols_fn, key = TABLES[table]
    cols = [c for c, _ in cols_fn()]
    values = ",\n  ".join("(" + ", ".join(sql_literal(r.get(c)) for c in cols) + ")"
                          for r in rows)
    sets = ", ".join("%s = COALESCE(EXCLUDED.%s, t.%s)" % (c, c, c)
                     for c in cols if c not in key)
    return ("INSERT INTO %s AS t (%s) VALUES\n  %s\nON CONFLICT (%s) DO UPDATE SET %s, "
            "updated_at = now()\nRETURNING %s"
            % (table, ", ".join(cols), values, ", ".join(key), sets, ", ".join(key)))
