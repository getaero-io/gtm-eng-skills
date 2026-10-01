#!/usr/bin/env python3
"""
Everything checkable with no network and no Deepline credits. The verdict code runs under `node`,
the same text the play embeds.

    python3 test_offline.py            # run the checks (exit 0 = all pass)
    python3 test_offline.py --record   # maintainers: re-record jev_answers.json from live Jev (spends a little)
    python3 test_offline.py --play     # also run `deepline plays check` on the rendered play (free, needs the CLI)

1. The play renders with no unfilled slot, embeds the verdict code verbatim, and uses no
   replay-unsafe clock.
2. The invented cases in fixtures.json, replayed against recorded Jev answers, give the verdict
   each case expects. A changed question set is caught, not silently replayed.
3. Output keys are always all present, and every verdict value is from its fixed set.
4. Jev failures come back `failed`, never as a verdict.
5. Company matching, date reading, and Crustdata's profile shape, case by case.
6. Ties and rivals.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import active_lib as L  # noqa: E402

ANSWERS = os.path.join(HERE, "jev_answers.json")
passed, failed = [0], []


def check(name, cond, detail=""):
    if cond:
        passed[0] += 1
    else:
        failed.append("%s %s" % (name, detail))


def cases():
    return json.load(open(os.path.join(HERE, "fixtures.json")))["cases"]


def replay(record_file):
    store = json.load(open(record_file)) if os.path.exists(record_file) else {}

    def make(cid):
        def call(body):
            rec = store.get(cid)
            if not rec:
                raise AssertionError("no recorded Jev answer for %s: run test_offline.py --record" % cid)
            if sorted(rec["questions"]) != sorted(body["questions"]):
                raise AssertionError("%s asks different questions than were recorded (%s vs %s): re-record"
                                     % (cid, sorted(body["questions"]), sorted(rec["questions"])))
            for q in body["questions"].values():
                if q["type"] not in ("boolean", "choice", "score"):
                    raise AssertionError("question type %r is not one ai_evaluate takes" % q["type"])
            return 200, rec["response"]
        return call
    return make


def record():
    store = {"_about": json.load(open(ANSWERS)).get("_about", "") if os.path.exists(ANSWERS) else ""}
    for c in cases():
        def call(body, cid=c["id"]):
            st, resp = L.ask_jev(body)
            store[cid] = {"questions": sorted(body["questions"]), "response": resp}
            return st, resp
        L.check_record(c["record"], call=call)
    json.dump(store, open(ANSWERS, "w"), indent=1, sort_keys=True)
    print("recorded %d cases into %s" % (len(store) - 1, ANSWERS))


# ---------------------------------------------------------------------------- 1

def test_render():
    src = L.render_play()
    check("no unfilled slot in the play", "__" not in src.replace("__name__", ""), "")
    check("play embeds the verdict code verbatim", L.render_core() in src)
    check("play calls ai_evaluate and crustdata enrich", "tool: 'ai_evaluate'" in src
          and "tool: 'crustdata_v3_person_enrich'" in src)
    core = L.render_core()
    check("verdict code reads no wall clock", "Date.now()" not in core and "new Date()" not in core)
    check("clock is checkpointed in the play", "ctx.step('now'" in src)
    # plays check refuses a dataset table name ("<play>_<dataset key>") over 63 characters
    check("play name + dataset key fit 63 characters", len(L.PLAY_NAME) + len("_records") <= 63, L.PLAY_NAME)
    for k in L.OUTPUT_KEYS:
        check("play has a column for %s" % k, ".withColumn('%s'," % k in src)


def test_play_check():
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, L.PLAY_NAME + ".play.ts")
        open(p, "w").write(L.render_play())
        r = subprocess.run(["deepline", "plays", "check", p, "--json"], capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
        except json.JSONDecodeError:
            d = {"valid": False, "errors": [r.stderr[:300]]}
        check("deepline plays check: valid", d.get("valid") is True, d.get("errors"))


# ---------------------------------------------------------------------------- 2, 3

def test_fixtures():
    make = replay(ANSWERS)
    for c in cases():
        try:
            v = L.check_record(c["record"], call=make(c["id"]))
        except AssertionError as e:
            check("replay " + c["id"], False, str(e))
            continue
        for k, want in c["expect"].items():
            check("%s: %s" % (c["id"], k), v.get(k) == want, "got %r want %r" % (v.get(k), want))
        check("%s: all keys" % c["id"], set(L.OUTPUT_KEYS) <= set(v), sorted(set(L.OUTPUT_KEYS) - set(v)))
        check("%s: active value" % c["id"], v["active_at_company"] in L.ACTIVE_VALUES, v["active_at_company"])
        check("%s: relationship value" % c["id"], v["relationship"] in L.RELATIONSHIPS, v["relationship"])
        check("%s: status value" % c["id"], v["check_status"] in L.CHECK_STATUSES, v["check_status"])
        check("%s: never blank evidence" % c["id"], bool(v["evidence"]) and bool(v["needs_review"]))
        if v["check_status"] == "checked":
            check("%s: tokens read from usage" % c["id"], v["jev_input_tokens"] > 0, v["jev_input_tokens"])


# ---------------------------------------------------------------------------- 4

def test_failures():
    c = cases()[0]["record"]
    for code, body, word in ((401, {"category": "authentication", "message": "x"}, "authentication"),
                             (429, {"category": "rate_limit", "message": "x"}, "rate limit"),
                             (0, {"category": "billing", "message": "x"}, "credits"),
                             (200, {"result": {"answers": {}}}, "no answers"),
                             (200, "not json", "no answers"), (0, None, "failed")):
        v = L.check_record(c, call=lambda b, code=code, body=body: (code, body))
        check("Jev %s is failed" % word, v["check_status"] == "failed" and v["active_at_company"] == "not_checked",
              "%s %s" % (v["check_status"], v["active_at_company"]))
        check("Jev %s says why" % word, word in v["error"], v["error"])


# ---------------------------------------------------------------------------- 5

def test_matching_and_dates():
    core = L.load_core()
    t = core["target_of"]({"company_name": "Northwind Supply Inc.", "company_domain": "https://www.northwind.example/about"})

    def role(**kw):
        base = {"company": "", "domain": "", "linkedin": ""}
        base.update(kw)
        return base
    ident = core["identity"]
    check("subdomain matches", ident(role(company="x", domain="shop.northwind.example"), t)[0] == "confirmed")
    check("legal suffix ignored", ident(role(company="Northwind Supply, LLC"), t)[0] == "name_match")
    check("name overlap asks Jev", ident(role(company="Northwind"), t)[0] == "name_overlap")
    check("other company is none", ident(role(company="Contoso"), t)[0] == "none")
    check("same name, other website: Jev decides",
          ident(role(company="Northwind Supply", domain="northwind-supply.example"), t)[0] == "id_conflict")
    t2 = core["target_of"]({"company_linkedin_url": "https://www.linkedin.com/company/northwind-supply-example/"})
    check("LinkedIn page matches", ident(role(company="NW", linkedin="northwind-supply-example"), t2)[0] == "confirmed")
    t3 = core["target_of"]({"company_domain": "fabrikam-example.co.uk"})
    check("co.uk root", core["_root"]("mail.fabrikam-example.co.uk") == "fabrikam-example.co.uk")
    check("domain label is a name", ident(role(company="Fabrikam Example Ltd"), t3)[0] == "name_match")
    d = core["_date"]
    for raw, want in (("2021-03-01", "2021-03-01"), ("Mar 2021", "2021-03"), ("March 2021", "2021-03"),
                      ("2021", "2021"), ({"year": 2021, "month": 3}, "2021-03"), ("Present", ""), (None, ""),
                      ("2021-03-01T00:00:00Z", "2021-03-01")):
        check("date %r" % (raw,), d(raw) == want, "got %r" % d(raw))
    check("days since 1970", core["_days_since"]("1970-01-01") is not None and core["_days_since"]("1970-01-01") > 20000)
    r = core["_role"]({"company": "X", "title": "Y", "start_date": "2020-01", "end_date": "2021-01", "is_current": None})
    check("ended role is not open", r["open"] is False)
    r = core["_role"]({"company": "X", "title": "Y", "start_date": "2020-01", "end_date": None})
    check("no end date is open", r["open"] is True)
    r = core["_role"]({"company": {}, "company_name": "X", "title": "Y"})
    check("empty company object falls back to company_name", r["company"] == "X", r)
    ix = core["intake"]({"company_name": "X", "linkedin_url": "https://linkedin.com/company/x"})
    check("company URL is not a person URL", not ix["need_enrichment"] and "not a LinkedIn profile" in ix["blocked"])
    ix = core["intake"]({"company_name": "X", "linkedin_url": "https://www.linkedin.com/in/x", "skip_enrichment": "true"})
    check("skip_enrichment is honoured", not ix["need_enrichment"])
    ix = core["intake"]({"company_name": "X", "linkedin_url": "https://www.linkedin.com/in/x", "skip_enrichment": True})
    check("skip_enrichment as a JSON boolean is honoured", not ix["need_enrichment"])
    old = {"last_refresh": "2020-01-01", "experience": [{"company": "X", "title": "Y", "is_current": True}]}
    ix = core["intake"]({"company_name": "X", "profile": old, "linkedin_url": "https://www.linkedin.com/in/x",
                         "max_profile_age_days": "365"})
    check("old supplied profile is re-bought when asked", ix["need_enrichment"] and ix["stale_supplied"])
    ix = core["intake"]({"company_name": "X", "profile": old, "linkedin_url": "https://www.linkedin.com/in/x"})
    check("old supplied profile is used when not asked", not ix["need_enrichment"])


def test_crustdata_shape():
    """crustdata_v3_person_enrich's response, as its schema describes it, reads as a work history."""
    crust = [{"matches": [{"confidence_score": 1, "person_data": {
        "basic_profile": {"name": "Dana Ruiz", "headline": "VP Operations at Northwind Supply", "last_updated": "2026-09-01"},
        "experience": {"employment_details": {
            "current": [{"name": "Northwind Supply", "title": "VP Operations", "start_date": "2021-04-01",
                         "end_date": None, "company_website_domain": "northwind.example",
                         "company_professional_network_profile_url": "https://www.linkedin.com/company/northwind-supply-example"}],
            "past": [{"name": "Fabrikam Freight", "title": "Director of Operations", "start_date": "2016-01-01",
                      "end_date": "2021-03-01", "company_website_domain": "fabrikam.example"}]}}}}]}]
    core = L.load_core()
    roles, facts = core["read_profile"](core["_obj"](crust))
    check("crustdata: both roles read", len(roles) == 2, roles)
    check("crustdata: current role is open, past is not", roles[0]["open"] and not roles[1]["open"])
    check("crustdata: company website read", roles[0]["domain"] == "northwind.example")
    check("crustdata: name and headline read", facts["name"] == "Dana Ruiz" and "VP Operations" in facts["headline"])
    rec = {"company_domain": "northwind.example", "linkedin_url": "https://www.linkedin.com/in/dana", "full_name": "Dana Ruiz"}
    ix = core["intake"](rec)
    check("URL-only person needs a profile", ix["need_enrichment"])
    pr = core["prepare"](ix, crust)
    check("bought profile is used", pr["source"] == "enriched" and pr["ask"], pr.get("blocked"))
    pr = core["prepare"](ix, {"data": crust})
    check("bought profile one level down is used", pr["source"] == "enriched")
    pr = core["prepare"](ix, {"_enrich_error": "boom"})
    check("failed purchase is no_profile, not a verdict", pr["blocked"] == "no_profile" and "no work history" in pr["enrich_note"])
    v = core["verdict"](pr, None, None)
    check("... and comes back not_checked", v["active_at_company"] == "not_checked" and v["check_status"] == "no_profile")
    ix2 = core["intake"](dict(rec, full_name="Pat Quinn"))
    pr2 = core["prepare"](ix2, crust)
    check("a bought profile for someone else is flagged", "not Pat Quinn" in (pr2.get("name_mismatch") or ""))


# ---------------------------------------------------------------------------- 6

def test_tie_and_rival():
    """Two certain current roles at the company: the evidence names the newer one. A side role
    elsewhere is never named as a rival main job."""
    rec = {"company_domain": "northwind.example", "profile": {"experience": [
        {"company": "Northwind Supply", "title": "SVP Stores", "start_date": "2015-01-01", "is_current": True,
         "company_domain": "northwind.example"},
        {"company": "Northwind Supply", "title": "CEO, Stores", "start_date": "2022-07-01", "is_current": True,
         "company_domain": "northwind.example"},
        {"company": "Contoso Robotics", "title": "Board Member", "start_date": "2020-01-01", "is_current": True,
         "company_domain": "contoso.example"}]}}
    core = L.load_core()
    pr = core["prepare"](core["intake"](rec))
    emp = {"type": "choice", "choice": "employee", "probabilities": {"employee": 1.0}}
    emp_99 = {"type": "choice", "choice": "employee", "probabilities": {"employee": 0.99, "contractor": 0.01}}
    board = {"type": "choice", "choice": "advisor_or_board", "probabilities": {"advisor_or_board": 1.0}}
    answers = {}
    for q in pr["jev_body"]["questions"]:
        answers[q] = board if q.startswith("other_") else (emp if q.startswith("kind_") else {"type": "boolean", "probability": 0.9})
    # the newer role scored a hair lower, as Jev did live (0.99 against 1.00): still a tie
    newer = next(i for i, r in enumerate(pr["roles"]) if r["title"] == "CEO, Stores")
    answers["kind_%d" % newer] = emp_99
    v = core["verdict"](pr, 200, {"result": {"answers": answers, "response": {"modelId": "typesafe-ai/jev"}},
                                  "usage": {"inputTokens": 1}})
    check("tie goes to the newer role", v["role_title"] == "CEO, Stores", v["role_title"])
    rows = json.loads(v["roles_json"])
    check("a board seat is never a rival job", all(r["rival_job"] == "" for r in rows), [r["rival_job"] for r in rows])
    check("still primary", v["relationship"] == "primary_job", v["relationship"])
    check("model read from the response", v["jev_model"] == "typesafe-ai/jev", v["jev_model"])


def main():
    if "--record" in sys.argv:
        record()
        return
    tests = [test_render, test_fixtures, test_failures, test_matching_and_dates, test_crustdata_shape, test_tie_and_rival]
    if "--play" in sys.argv:
        tests.append(test_play_check)
    for t in tests:
        try:
            t()
        except (Exception, SystemExit) as e:  # a crash is a failure, named
            failed.append("%s crashed: %r" % (t.__name__, e))
    print("%d checks passed, %d failed" % (passed[0], len(failed)))
    for f in failed:
        print("  FAIL " + f)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
