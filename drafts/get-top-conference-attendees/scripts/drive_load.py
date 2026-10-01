#!/usr/bin/env python3
"""Run a conference campaign and load its dossiers into the Deepline customer DB — and top it up later.

    python3 drive_load.py conference-config.json account
    python3 drive_load.py conference-config.json run   --conference "INBOUND" [--city X] [--year 2026]
                                                       [--conference-url https://www.example.com/the-event]
    python3 drive_load.py conference-config.json load   --campaign <campaign id>
    python3 drive_load.py conference-config.json status --campaign <campaign id>

`load` IS the top-up. There is no separate command and no "since" argument, because there is
nothing to be since: unlocking a dossier happens in a browser against the share link, with no
webhook, no unlock endpoint and no changed-since parameter anywhere in the API. Nothing can
tell this script what a person unlocked. So every load re-reads the whole campaign, takes
everything that now carries a dossier, subtracts what the ledger says is already written, and
writes the difference. Run it the day you start and run it again after somebody unlocks forty
more; the command is identical and the second run writes only the forty.

Resumability: every verdict is appended to the ledger THE MOMENT it settles, and the
remaining work is recomputed from the ledger rather than held in memory. Only a written
record settles — a failure stays in the work set so a retry picks it up untouched. And
because every write is an upsert keyed on the attendee's own identifier, a lost ledger costs
redundant writes, never duplicates.

The API key is read from the environment (or a file of KEY=value lines). It is never passed
as an argument: a key on a command line is visible in `ps` to every process on the machine.
"""

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import attendee_list as AL   # noqa: E402
import audience_lib as A      # noqa: E402
import conference_lib as C   # noqa: E402
import lanyard_lib as L       # noqa: E402

BATCH = 100                   # rows per upsert statement

# Ledger verdicts. `write_failed` is deliberately NOT spelled "failed": a dossier state of
# `failed` already means "enrichment ran and produced nothing", and one word naming two
# different facts is exactly what Rule 9 exists to stop.
SETTLED = "written"
WRITE_FAILED = "write_failed"
UNWRITABLE = "unwritable"


# ------------------------------------------------------------------- the ledger


class Ledger:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    def rows(self):
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    # A torn final line from an interrupted write. Everything before it is
                    # still good, which is the whole point of appending one line at a time.
                    continue
        return out

    def settled_ids(self):
        return {r.get("contact_id") for r in self.rows() if r.get("verdict") == SETTLED}

    def _ends_clean(self):
        """Did the last write finish? An interrupted append leaves a partial line with no
        newline, and appending straight onto it would fuse the two into one unparseable
        record — losing not the torn line, which is already gone, but the NEXT one."""
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            return True
        with open(self.path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            return fh.read(1) == b"\n"

    def append(self, **row):
        row.setdefault("at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        prefix = "" if self._ends_clean() else "\n"
        with open(self.path, "a") as fh:
            fh.write(prefix + json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


# --------------------------------------------------------------------- the CLI


def ledger_path(cfg, config_path, campaign_id):
    """Where this campaign's ledger lives — beside the WRITER, keyed by campaign id.

    It used to sit beside the campaign config, which meant a cold session months later could
    not find it and re-wrote every attendee. Harmless, because the writes are upserts, but it
    defeats the one promise the top-up makes: that a second run touches only what is new.

    An older ledger left beside the config is adopted on sight, so a top-up started before
    this change does not lose its history.
    """
    name = "ledger-%s.jsonl" % campaign_id
    new = os.path.join(C.writer_dir(cfg), name)
    if not os.path.exists(new):
        old = os.path.join(os.path.dirname(os.path.abspath(config_path)), name)
        if os.path.exists(old):
            os.makedirs(os.path.dirname(new), exist_ok=True)
            shutil.copyfile(old, new)
            print("  adopted the ledger from %s" % old)
    return new


def load_config(path):
    """Read the config — and when the path is gone, find the workspace's writer config.

    This is what makes a top-up survive a cold session. Somebody comes back weeks later with
    a command from an old note, and the campaign folder it pointed at has been tidied away.
    Everything a top-up actually needs is workspace-level and lives beside the writer, so ask
    Deepline which workspace this is and read it from there.
    """
    if os.path.exists(path):
        return json.load(open(path))

    ws = C.workspace_id()
    candidate = C.writer_config_path({"workspace_id": ws})
    if ws and os.path.exists(candidate):
        print("no config at %s — using this workspace's writer config instead:\n  %s"
              % (path, candidate))
        return json.load(open(candidate))

    raise SystemExit(
        "No config at %s, and no writer config for workspace %s (looked in %s).\n"
        "If the writer was built under another login, point at its config directly.\n"
        "Otherwise build it once with build_conference_writer.py." % (path, ws or "unknown", candidate))


def column_types():
    """{table: {column: plan type}} as the DB really holds them. Empty means not built."""
    return C.existing_types(C.db(C.existing_columns_sql()))


def require_tables(types, link_companies):
    need = [C.ATTENDEES] + ([C.COMPANIES] if link_companies else [])
    missing = [t for t in need if t not in types]
    if missing:
        raise SystemExit(
            "Not built in this workspace yet: %s.\nRun build_conference_writer.py once — it is "
            "built once and reused by every conference afterwards." % ", ".join(missing))


# ------------------------------------------------------- shaping a write row


def person_key(shaped):
    """LinkedIn first, email second — the same order `route_for` matches on."""
    if shaped.get("linkedin_url"):
        return shaped["linkedin_url"].strip()
    if shaped.get("email"):
        return "email:" + shaped["email"].strip().lower()
    return None


def rows_for(shaped, route, types, link_companies=True):
    """(attendee row, company row or None, dropped {display: reason}) for one attendee.

    A blank is None, never "" — the upsert COALESCEs, so None keeps whatever a previous write
    put there and "" would overwrite it with nothing. Every value is validated against its
    column's REAL type; one that does not fit is dropped and named, because Postgres would
    otherwise reject the whole batch statement."""
    ptypes = types.get(C.ATTENDEES, {})
    linked = A.route_is_linked(route)
    dropped = {}

    def val(v, declared, column, label, ttypes=ptypes):
        ok, out, why = A.validate_value(v, ttypes.get(column, declared))
        if not ok and why != "empty":
            dropped[label] = why
        return out if ok else None

    person = {"campaign_id": shaped.get("campaign_id") or None,
              "person_key": person_key(shaped),
              "match_key": A.route_match_key(route)}
    for col in A.PEOPLE_BUILTINS:
        person[col] = val(shaped.get(col), "email" if col == "email" else "text", col, col)
    if not linked:
        person["company_domain"] = None
    for display, declared, src in A.PEOPLE_FIELDS:
        if src != "campaign_id":
            person[src] = val(shaped.get(src), declared, src, display)

    company = None
    if linked and link_companies:
        company = {"domain": person["company_domain"], "org_name": person["company_name"]}
        for display, declared, src in A.COMPANY_FIELDS:
            v = "yes" if src == "attending_flag" else shaped.get(src)
            company[src] = val(v, declared, src, "company:" + display,
                               types.get(C.COMPANIES, {}))
    return person, company, dropped


def write(table, rows, key):
    """Upsert `rows`; return the set of keys the DB RETURNed. Only those settle."""
    got = C.db(C.upsert_sql(table, rows))
    return {key(r) for r in got}


PLACEHOLDER_MARKS = ("REPLACE", "OPTIONAL —", "Optional —", "Optional.")


def placeholders_in(obj, path="body"):
    """Every leaf still holding the example config's own instruction text.

    Walks rather than checking known keys, because the trap is a value nested inside `team`
    or `context` — exactly where a copied example leaves prose behind."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            found += placeholders_in(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += placeholders_in(v, "%s[%d]" % (path, i))
    elif isinstance(obj, str):
        if any(m in obj for m in PLACEHOLDER_MARKS):
            found.append("%s = %r" % (path, obj[:70]))
    return found


# --------------------------------------------------------------------- the load


def offer_unlock(key, contacts, locked, campaign_id):
    """Close with ONE link and ONE next step.

    The ending used to offer three things at once — a CLI unlock command, a payment link and
    a share link — which makes the reader choose between them before they have even read the
    dossiers. There is only one thing worth doing next: open the campaign, read what came
    back, and unlock more there if it is worth it. Everything else is a detour.

    Shown on EVERY path, including a run that wrote nothing, because that is the path
    somebody checking back is on.
    """
    print("\n== read them in Lanyard ==")
    print("  %s" % L.campaign_url(campaign_id))
    print("  Same login you signed in with.")

    tiers = L.locked_by_tier(contacts)
    if not tiers:
        return
    per = locked.get("credits_per_contact") or 5
    total = sum(n for _t, n in tiers)
    print("\n  %d more are ranked and waiting there: %s"
          % (total, ", ".join("%d %s" % (n, t) for t, n in tiers)))
    print("  You can unlock any of them from that page — %s credits each." % per)
    print("\n  **Unlock whenever you like — today, or in a month. Come back and ask me to")
    print("  load them into the customer DB, and I will.** A new session finds this campaign from your")
    print("  Lanyard account on its own; you do not need this id or anything on this machine.")
    print("  Only the newly unlocked ones get written — nothing is duplicated.")


def do_load(cfg, config_path, key, campaign_id, dry=False, limit=None, rewrite=False):
    link = bool(cfg.get("link_companies", True))
    types = column_types()
    require_tables(types, link)

    print("reading campaign %s" % campaign_id)
    campaign = L.get_campaign(key, campaign_id)
    status = campaign.get("status")
    contacts, total = L.list_contacts(key, campaign_id)
    print("  status %s · %d contacts known" % (status, total))
    if status not in L.TERMINAL:
        print("  ! still running — loading what is ready. Run the same command again when "
              "it finishes.")

    ctx = L.campaign_context(campaign, time.strftime("%Y-%m-%d", time.gmtime()))
    ledger = Ledger(ledger_path(cfg, config_path, campaign_id))
    # `--rewrite` ignores what the ledger already settled. It exists for one situation: the
    # columns changed, so records written by an older mapping are missing fields the new one
    # fills. It is safe because every write is an upsert on the attendee's own identifier —
    # rewriting updates, it never duplicates. It is NOT a repair for a failed write; those
    # never settled and are retried anyway.
    settled = set() if rewrite else ledger.settled_ids()
    if rewrite:
        print("  --rewrite: ignoring %d already-written attendees and writing them again"
              % len(ledger.settled_ids()))

    todo, skipped = L.delta(contacts, settled)
    if limit:
        todo = todo[:limit]

    shaped = [L.shape_contact(c, ctx) for c in todo]
    by_route, unwritable = A.plan_writes(shaped, link_company=link)

    print("\n== the plan ==")
    print("  %d with a dossier and not yet written" % len(todo))
    for route in sorted(by_route):
        print("    %-22s %d" % (route, len(by_route[route])))
    if unwritable:
        print("    %-22s %d  (no LinkedIn URL and no email — nothing can match them)"
              % ("unwritable", len(unwritable)))
    for reason, n in sorted(skipped.items()):
        print("    skipped: %-13s %d" % (reason, n))

    allowance = L.free_allowance(campaign)
    locked = L.locked_summary(campaign, contacts)
    print("\n  enrichment allowed: %s of %s requested (source: %s)"
          % (allowance["allowed"], allowance["requested"], allowance["source"]))
    if locked["total"]:
        bits = ", ".join("%s %s" % (v, k) for k, v in sorted(locked["breakdown"].items()))
        print("  %d more are ranked and waiting without a dossier%s"
              % (locked["total"],
                 (" — by %s: %s" % (locked["breakdown_by"], bits)) if bits else ""))
        # No link here. The close gives exactly one, and it is the signed-in campaign page —
        # the campaign's own `unlock_url` is the /claim?t=<token> link, so printing it here
        # both duplicated the ending and put an access token in the middle of a plan.

    if dry:
        print("\n-- dry run: nothing written.")
        return 0

    if not shaped:
        print("\nNothing new to write — everything with a dossier is already in the customer DB.")
        offer_unlock(key, contacts, locked, campaign_id)
        return 0

    already_unwritable = {r.get("contact_id") for r in ledger.rows()
                          if r.get("verdict") == UNWRITABLE}
    items, drops = [], {}
    for s in shaped:
        route, why = A.route_for(s, link_company=link)
        cid = s["lanyard_contact_id"] or (s["email"] or s["linkedin_url"] or s["name"])
        if route == A.ROUTE_UNWRITABLE:
            # Deliberately NOT settled: the same person may acquire a profile or an address
            # later, and a re-read would then write them. But record it only once — a
            # re-appended row every run would grow the ledger without end and say nothing new.
            if cid not in already_unwritable:
                ledger.append(contact_id=cid, verdict=UNWRITABLE, reason=why, name=s["name"])
                already_unwritable.add(cid)
            continue
        person, company, dropped = rows_for(s, route, types, link)
        if dropped:
            drops[cid] = (s["name"], dropped)
        items.append((cid, s, route, person, company))

    if drops:
        print("\n  values dropped rather than written (they do not fit the column's type):")
        for name, d in list(drops.values())[:10]:
            print("    %s: %s" % (name, ", ".join("%s (%s)" % (k, v) for k, v in d.items())))
        if len(drops) > 10:
            print("    … and %d more" % (len(drops) - 10))

    print("\n== writing ==")
    written = failed = linked = 0
    companies_written = set()
    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        print("  batch %d: %d attendees" % (i // BATCH + 1, len(chunk)))
        # Companies first, deduped by domain. A failure here leaves the attendees writable:
        # the link is the company_domain value on the attendee row, not a foreign key.
        comps = {c["domain"]: c for _cid, _s, _r, _p, c in chunk if c}
        if comps:
            try:
                companies_written |= write(C.COMPANIES, list(comps.values()),
                                           lambda r: r.get("domain"))
            except Exception as e:                                # noqa: BLE001
                print("    ! company rows failed: %s" % str(e)[:300])
        try:
            # Deduped by key: two contacts resolving to one person in one statement would make
            # Postgres refuse the whole batch ("cannot affect row a second time").
            rows = {(p["campaign_id"], p["person_key"]): p for _c, _s, _r, p, _co in chunk}
            got = write(C.ATTENDEES, list(rows.values()),
                        lambda r: (r.get("campaign_id"), r.get("person_key")))
        except Exception as e:                                    # noqa: BLE001
            # The whole batch stays unsettled and is retried untouched on the next run.
            print("    ! batch failed to settle: %s" % str(e)[:300])
            failed += len(chunk)
            continue
        for cid, s, route, p, _co in chunk:
            ok = (p["campaign_id"], p["person_key"]) in got
            ledger.append(contact_id=cid, verdict=SETTLED if ok else WRITE_FAILED, route=route,
                          name=s["name"], person_key=p["person_key"], campaign_id=campaign_id,
                          error=None if ok else "not in the RETURNING rows — left unsettled")
            if ok:
                written += 1
                linked += 1 if p.get("company_domain") else 0
            else:
                failed += 1
                print("    ! %s: not confirmed written" % s["name"])

    print("\n== what is now in %s ==" % C.ATTENDEES)
    print("  %d attendee record(s) written%s"
          % (written, " · %d left unsettled (re-run to retry)" % failed if failed else ""))
    if link:
        print("  %d of them linked to their company (%d company row(s) upserted)"
              % (linked, len(companies_written)))
    print("  each carries: tier, score, rank, attendance confidence and evidence, the dossier"
          "\n  headline and summary, their company summary, buying signals, conversation"
          "\n  openers and a value prop — every one a column you can filter on")

    # Which EDITION the attendance evidence is about, broken out. Measured on a live
    # **This is a capability, not a complaint.** Most attendee sources tell you a name and
    # leave you to guess where it came from. This one labels every piece of evidence with the
    # edition it belongs to, which is what makes the list filterable rather than merely
    # plausible — so report the split as information the person now HAS, not as a shortfall.
    years = {}
    for sh in shaped:
        y = sh.get("attendance_year") or "not stated"
        years[y] = years.get(y, 0) + 1
    # The campaign-wide pool first — it is the bigger, fairer number. The split across the
    # written handful says as much about the free allowance as about the event.
    pool = L.attendance_pool(campaign)
    if pool:
        total = (campaign.get("counts") or {}).get("attendees")
        print("  the campaign found %s people in all: %s"
              % (total, ", ".join("%s %s" % (n, y) for y, n in pool)))
    if years:
        print("  of the %d written here: %s"
              % (len(shaped),
                 ", ".join("%d %s" % (n, y) for y, n in sorted(years.items(), key=lambda kv: -kv[1]))))
        if years.get("this_year", 0) < len(shaped):
            print("  every record carries its Attendance year — filter on this_year for the"
                  "\n  ones evidenced against the upcoming edition; the others are regulars,"
                  "\n  on evidence from a previous one.")
    print("  ledger: %s" % ledger.path)

    offer_unlock(key, contacts, locked, campaign_id)
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------- the run


def do_run(cfg, config_path, key, args):
    # Check the things a completed campaign would be USELESS without, BEFORE spending one.
    # A campaign is the only real cost in this skill, and the load that follows it dies
    # immediately on missing tables — so discovering that afterwards means having paid for a
    # run that cannot be written anywhere.
    require_tables(column_types(), bool(cfg.get("link_companies", True)))

    me = L.whoami(key)
    acct = me.get("account") or {}
    print("signed in as %s · %s credits · %s free dossiers per campaign"
          % (acct.get("email"), me.get("credits"), me.get("free_dossiers_per_campaign")))

    found = L.lookup_conference(key, args.conference, args.city, args.year,
                                url=args.conference_url)
    conf = found.get("conference") or {}
    print("\n== the event ==")
    print("  %s · %s to %s · %s" % (conf.get("name"), conf.get("start_date"),
                                    conf.get("end_date"), conf.get("location")))
    print("  %s · confidence: %s" % (conf.get("website"), conf.get("confidence")))
    if not args.yes:
        raise SystemExit(
            "\nStop here and confirm this is the right edition with the person who asked,\n"
            "then re-run with --yes. A campaign is real work against a real event; the wrong\n"
            "edition produces a plausible list of people who will not be there.")

    body = {"domain": cfg["domain"], "conference": L.conference_for_create(conf),
            "goals": cfg["goals"]}

    # An attendee list the installer already has, seeded inline. NO upload endpoint is
    # involved: the create call takes up to 500 attendees directly, and the service still
    # searches for more on top of them.
    if cfg.get("attendee_list_file"):
        seeds, report = AL.load_file(cfg["attendee_list_file"])
        print("\n== the attendee list you supplied ==")
        for ln in AL.describe(report):
            print("  " + ln)
        if report.get("error"):
            raise SystemExit(
                "\nThe attendee list could not be read, and a campaign seeded with nothing is "
                "not the same campaign.\nFix the file or remove `attendee_list_file` from the "
                "config, then re-run.")
        if seeds:
            body["attendees"] = seeds
            year = str(cfg.get("attendee_list_year") or "").strip()
            if year:
                # Which list it is belongs in the campaign's own context, so the scoring
                # knows. Seeding LAST year's list is evidence somebody may come again, not
                # evidence that they are coming — the service's own attendance confidence and
                # year_context are what carry that, and they are written per contact.
                note = ("The supplied attendee list is from %s. Treat it as prior-year "
                        "signal, not confirmation of this year's attendance." % year
                        if year != "this year" else
                        "The supplied attendee list is this year's.")
                ctx = body.get("context") or cfg.get("context") or {}
                if isinstance(ctx, str):
                    ctx = {"conference": ctx}
                ctx = dict(ctx)
                ctx["conference"] = ((ctx.get("conference") or "") + " " + note).strip()
                body["context"] = ctx
                print("  labelled as: %s" % year)
    for opt in ("context", "team", "attendees", "label"):
        if cfg.get(opt):
            body[opt] = cfg[opt]

    # Refuse to send the example file's own instructions as campaign input. An unfilled
    # placeholder is truthy, so without this a teammate literally named "Optional — who is
    # going from your side" is fed into the scoring rubric and the dossiers, and the run looks
    # like it worked.
    left = sorted(placeholders_in(body))
    if left:
        raise SystemExit(
            "These config values still hold the example file's placeholder text, and they are "
            "sent verbatim to the campaign:\n  %s\n"
            "Fill them in or delete the key, then re-run. Refusing to start a campaign "
            "calibrated on placeholder prose." % "\n  ".join(left))
    if cfg.get("enrich_count"):
        body["enrich_count"] = int(cfg["enrich_count"])

    created = L.create_campaign(key, body)
    campaign_id = created.get("campaign_id")
    print("\nstarted campaign %s" % campaign_id)

    # State the allowance on EVERY path. The create response may carry no enrichment block at
    # all — it is not in the published schema — and the account's own figure cannot tell us
    # whether a cap bit. Saying nothing in that case would leave the one disclosure about
    # money resting on the caller having looked it up earlier.
    allowance = L.free_allowance({}, created, me)
    asked = body.get("enrich_count", 10)
    if allowance["capped"]:
        print("  the free allowance caps this at %s dossiers of the %s asked for; the rest "
              "stay ranked and unlockable." % (allowance["allowed"], allowance["requested"]))
    elif allowance["allowed"] is not None and allowance["allowed"] < asked:
        print("  this account covers %s full dossiers per campaign and %s were asked for, so "
              "the rest will come back ranked and locked (source: %s)."
              % (allowance["allowed"], asked, allowance["source"]))
    elif allowance["allowed"] is not None:
        print("  this account covers %s full dossiers per campaign; %s were asked for "
              "(source: %s)." % (allowance["allowed"], asked, allowance["source"]))
    else:
        print("  nothing in this response or in the account reported an enrichment "
              "allowance, so how many dossiers are coming is not knowable until the campaign "
              "reports its own counts. Not assuming a number.")

    # Record the campaign id before polling: a run that is interrupted mid-poll must still
    # be resumable, and the campaign id is the only thing that makes that possible.
    # Beside the WRITER, not beside the config. The config is wherever the session happened
    # to put it — measured, that was inside a git repo on three separate cold runs — and this
    # file is the breadcrumb a later session needs to find a campaign again. Workspace-level
    # also makes it one index across every conference instead of one per folder.
    ids_path = os.path.join(C.writer_dir(cfg), "campaigns.jsonl")
    os.makedirs(os.path.dirname(ids_path), exist_ok=True)
    with open(ids_path, "a") as fh:
        fh.write(json.dumps({"campaign_id": campaign_id, "conference": conf.get("name"),
                             "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    print("  recorded in %s — if this is interrupted, resume with:\n"
          "    python3 drive_load.py %s load --campaign %s"
          % (ids_path, os.path.basename(config_path), campaign_id))

    print("\n== progress ==")
    campaign = L.poll_campaign(key, campaign_id,
                               on_stage=lambda s, m: print("  %-12s %s" % (s, m)))
    if campaign.get("status") == L.FAILED:
        raise SystemExit("\nThe campaign failed: %s\nNothing was written."
                         % (campaign.get("error") or "no reason given"))

    counts = campaign.get("counts") or {}
    print("\n  %s attendees found · %s enriched · %s dossiers"
          % (counts.get("attendees"), counts.get("enriched"), counts.get("dossiers")))
    # The logged-in page, not the `/claim?t=…` share link: same login they signed in with.
    print("  read them here: %s" % L.campaign_url(campaign_id))

    return do_load(cfg, config_path, key, campaign_id, limit=args.limit)


def do_campaigns(key):
    """List the key's campaigns. The recovery path when an id has been lost."""
    rows, total = L.list_campaigns(key)
    if not rows:
        print("No campaigns on this account yet.")
        return 0
    print("%d campaign(s), newest first:\n" % total)
    for r in rows:
        conf = r.get("conference") or {}
        n = r.get("counts") or {}
        print("  %s" % r.get("campaign_id"))
        print("      %-30s %s%s"
              % (" ".join(x for x in (conf.get("name"), conf.get("edition")) if x) or "?",
                 r.get("status") or "", ("  · " + r["label"]) if r.get("label") else ""))
        bits = ["%s attendees" % n.get("attendees")]
        # `this_year` is the number whose attendance evidence is about THIS edition. It is
        # the honest headline: the rest were seen at a previous one.
        if n.get("this_year") is not None:
            bits.append("%s with this year's evidence" % n["this_year"])
        if n.get("dossiers") is not None:
            bits.append("%s dossiers" % n["dossiers"])
        print("      " + " · ".join(bits))
        locked = n.get("locked")
        if locked:
            cost = r.get("unlock_cost_credits")
            print("      %s still locked%s" % (locked, " · %s credits to unlock them all" % cost
                                               if cost is not None else ""))
    print("\nLoad or top one up with:  load --campaign <id>")
    return 0


def resolve_campaign(key, given, match=None):
    """The campaign to act on: the one named, the one matched, or the only one there is.

    Refuses to guess when it cannot tell. Choosing a campaign for somebody is choosing which
    conference's people get written into their customer DB, and the ids are opaque enough that a
    wrong guess would not be obvious afterwards."""
    if given:
        return given
    rows, _ = L.list_campaigns(key)
    if not rows:
        raise SystemExit("No campaigns on this account. Start one with `run --conference ...`.")

    if match:
        hits = L.match_campaigns(rows, match)
        if len(hits) == 1:
            c = hits[0]
            print("matched %r to %s (%s)"
                  % (match, (c.get("conference") or {}).get("name"), c["campaign_id"]))
            return c["campaign_id"]
        if not hits:
            print("Nothing on this account matches %r. What is there:\n" % match)
            for r in rows:
                print("  %s  %s" % (r.get("campaign_id"), (r.get("conference") or {}).get("name")))
            raise SystemExit("\nRefusing to guess. Name one with --campaign <id>.")
        print("%r matches %d campaigns:\n" % (match, len(hits)))
        for r in hits:
            conf = r.get("conference") or {}
            print("  %s  %s %s  (%s dossiers)"
                  % (r.get("campaign_id"), conf.get("name"), conf.get("edition") or "",
                     (r.get("counts") or {}).get("dossiers")))
        raise SystemExit("\nToo close to call. Name one with --campaign <id>.")

    if len(rows) == 1:
        c = rows[0]
        print("one campaign on this account, using it: %s (%s)"
              % ((c.get("conference") or {}).get("name"), c.get("campaign_id")))
        return c["campaign_id"]
    print("Several campaigns on this account — name one with --campaign, or say which\n"
          "with --match \"saastr\":\n")
    for r in rows:
        print("  %s  %-30s %s attendees, %s dossiers"
              % (r.get("campaign_id"), (r.get("conference") or {}).get("name"),
                 (r.get("counts") or {}).get("attendees"),
                 (r.get("counts") or {}).get("dossiers")))
    raise SystemExit("\nRefusing to choose. Re-run with --campaign <id>.")


def report_shortfall(payload, message=None):
    """Not enough credits is not an error to retry — it is a price and a link.

    The only correct response is to put the number and the URL in front of a person and stop.
    Never attempt a payment, and never treat the link as something to follow: money moves in
    a browser where somebody can see what they are buying.
    """
    p = payload or {}
    print("\n== not enough credits ==")
    print("  %s" % (message or "this unlock costs more credits than the account holds"))
    need = p.get("required", p.get("credits_required"))
    have = p.get("available", p.get("credits_available"))
    if need is not None:
        short = p.get("shortfall")
        if short is None and have is not None:
            short = need - have
        print("  needs %s · has %s · short by %s" % (need, have, short))
    url = p.get("payment_url")
    if url:
        print("\n  Top up here, then re-run the same unlock command:")
        print("    %s" % url)
    else:
        print("\n  The response carried no payment_url — top up from the campaign page in "
              "the browser.")
    return 1


def do_unlock(key, campaign_id, args):
    """Price an unlock, then spend only when explicitly told to — and only if it can succeed.

    Two gates, and they are different. `--confirm-spend` is the mechanical one: without it
    this only ever prices. The conversational one lives in the skill, which has to state the
    price, the balance and the count and get a yes before passing the flag.

    Money never moves from here. When the balance cannot cover the quote, the answer is the
    price and a link handed to a person — not a retry, and not an attempt.
    """
    if args.tier:
        selection, what = {"tier": args.tier}, "tier %s" % args.tier
    elif args.top:
        selection, what = {"top": int(args.top)}, "the top %d" % int(args.top)
    else:
        raise SystemExit("unlock needs --tier S (or A/B/C/F) or --top N")

    # Always price first, even when the caller intends to spend: the quote is the thing the
    # person agreed to, and asking for it costs nothing.
    try:
        q = L.unlock(key, campaign_id, selection, dry_run=True)
    except L.LanyardError as e:
        if e.status == 402:
            return report_shortfall(e.payload, e.message)
        raise

    # The dry run answers in its OWN shape — `matched` / `credits_required` /
    # `credits_available` — not the shape a real unlock returns (`unlocked` /
    # `credits_spent` / `credits_remaining`). The published spec documents only the second
    # one, so read both rather than pinning either.
    matched = q.get("matched", q.get("unlocked"))
    need = q.get("credits_required", q.get("credits_spent"))
    have = q.get("credits_available", q.get("credits_remaining"))

    if not matched:
        print("Nothing locked matches %s — nothing to unlock." % what)
        return 0

    print("== the quote ==")
    print("  %s locked contact(s) at %s" % (matched, what))
    print("  costs %s credits · the account holds %s" % (need, have))

    short = (need is not None and have is not None and have < need)
    if short:
        # Do not offer to spend what cannot be spent, and do not make them find out by
        # failing. The quote already carries the link.
        return report_shortfall(q, "This unlock needs %s credits and the account has %s."
                                % (need, have))

    if not args.confirm_spend:
        print("\nPriced only — nothing was spent.")
        print("To go ahead: re-run the same command with --confirm-spend")
        return 0

    try:
        done = L.unlock(key, campaign_id, selection, dry_run=False)
    except L.LanyardError as e:
        if e.status == 402:
            return report_shortfall(e.payload, e.message)
        raise

    print("\n== unlocked ==")
    print("  %s contact(s) · %s credits spent · %s remaining"
          % (done.get("unlocked"), done.get("credits_spent"), done.get("credits_remaining")))
    pending = done.get("dossiers_pending")
    if pending:
        # A contact whose dossier is still being written has no dossier YET, so the load
        # would skip it and the ledger would never settle it. Saying so beats a silent
        # shortfall in the write count.
        print("  %s dossier(s) are still being written. Those contacts have no dossier yet, "
              "so a\n  load right now skips them — run the load again once they finish."
              % pending)
    print("\nNow write them:  load --campaign %s" % campaign_id)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    # `account` rather than `whoami`: this reports the LANYARD account, and `deepline auth
    # status` reports the Deepline workspace. Two different accounts, and naming this one after the other
    # one's verb invited exactly the confusion it got.
    ap.add_argument("mode", choices=["account", "campaigns", "run", "load", "status", "unlock"])
    ap.add_argument("--conference")
    # The event's own page, for when the name alone resolves to the wrong edition. Measured:
    # "SaaStr Annual" and the saastrannual.com URL resolve to two different real events.
    ap.add_argument("--conference-url", dest="conference_url")
    ap.add_argument("--city")
    ap.add_argument("--year")
    ap.add_argument("--campaign")
    ap.add_argument("--match",
                    help="pick the campaign by name instead of by id — e.g. --match saastr. "
                         "Every word must appear in its conference, edition, city or label.")
    ap.add_argument("--yes", action="store_true",
                    help="confirm the matched conference edition is the right one")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tier", choices=["S", "A", "B", "C", "F"],
                    help="unlock: which score band to unlock")
    ap.add_argument("--top", type=int, help="unlock: unlock the top N locked contacts")
    ap.add_argument("--confirm-spend", action="store_true",
                    help="unlock: actually spend credits. Without it, unlock only prices.")
    ap.add_argument("--rewrite", action="store_true",
                    help="re-write attendees the ledger already settled (use after the "
                         "columns changed); upserts, so it updates rather than duplicating")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    cfg = load_config(args.config)

    key = L.read_key(path=cfg.get("key_file"))
    if not key:
        raise SystemExit(
            "No API key. Set LANYARD_API_KEY in the environment, or point `key_file` in the\n"
            "config at a file of KEY=value lines. Never pass a key as an argument — it is\n"
            "visible in `ps` to every process on this machine.")

    if args.mode == "account":
        # WHICH LANYARD ACCOUNT this key belongs to — not the Deepline workspace, which
        # `deepline auth status` answers and which is a different account entirely. This is the only call
        # that answers it without starting anything or needing a campaign to exist.
        me = L.whoami(key)
        acct = me.get("account") or {}
        print("Lanyard account: %s" % acct.get("email"))
        print("  client:          %s" % (acct.get("client") or "none"))
        print("  credits:         %s" % me.get("credits"))
        print("  free dossiers:   %s per campaign" % me.get("free_dossiers_per_campaign"))
        print("  unlimited:       %s" % me.get("unlimited"))
        return 0

    if args.mode == "campaigns":
        return do_campaigns(key)

    if args.mode == "unlock":
        return do_unlock(key, resolve_campaign(key, args.campaign, args.match), args)

    if args.mode == "run":
        if not args.conference:
            raise SystemExit("run needs --conference")
        if args.dry_run:
            # A flag named --dry-run that still starts a campaign would be a trap: the
            # campaign IS the cost, so there is no version of `run` that spends nothing.
            raise SystemExit(
                "--dry-run does not apply to `run`: starting the campaign is the cost, and a "
                "run that skipped it would be testing nothing.\n"
                "To see the event without starting anything, leave off --yes.\n"
                "To see what a load would write without writing it, use `load --dry-run`.")
        return do_run(cfg, args.config, key, args)

    # An id is no longer required: it can be recovered from the account.
    campaign_id = resolve_campaign(key, args.campaign, args.match)

    if args.mode == "status":
        campaign = L.get_campaign(key, campaign_id)
        contacts, total = L.list_contacts(key, campaign_id)
        states = {}
        for c in contacts:
            s = L.dossier_state(c)
            states[s] = states.get(s, 0) + 1
        print("campaign %s · %s" % (campaign_id, campaign.get("status")))
        print("  %d contacts" % total)
        for s, n in sorted(states.items()):
            print("    %-14s %d" % (s, n))
        locked = L.locked_summary(campaign, contacts)
        print("  %d ranked without a dossier (source: %s)" % (locked["total"], locked["source"]))
        return 0

    return do_load(cfg, args.config, key, campaign_id,
                   dry=args.dry_run, limit=args.limit, rewrite=args.rewrite)


if __name__ == "__main__":
    sys.exit(main())
