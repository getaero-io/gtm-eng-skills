"""Exercise the generated cascade handlers and the runner without touching Deepline.

cascade.py generates Python handlers from templates. If that Python has a syntax error, or a
substitution leaves a marker behind, every record dies at speed. So generate it here, parse
it, run the handlers against a fake context, then run whole records through the runner with
a fake Deepline — no credentials, no network, no cost.

    python3 test_codegen.py [path/to/cascade-config.json]

Exit 0 means the code the runner would execute is sound. The behavioural block below is keyed
to the shipped example config; with your own config the parse checks still apply, and
assertions naming legs you do not have will be skipped.
"""
import ast, json, os, sys, types

# Importing cascade.py would otherwise leave scripts/__pycache__ inside the package.
sys.dont_write_bytecode = True

SK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SK)
import cascade as B

# Defaults to the shipped example config; pass your own to test the cascade you will run.
cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SK, "cascade-config.example.json")
cfg = json.load(open(cfg_path))
cfg.setdefault("sentinels", ["n/a", "none", "null"])
cfg.setdefault("verified_statuses", ["deliverable", "valid"])
cfg.setdefault("capture_prefix", "person_")
print("config: %s" % cfg_path)
legs = [l for l in cfg["legs"] if l["provider"]["type"] != "none"]
for l in legs:
    l["need"] = "need_" + l["key"]

NEEDS = B.needs_code(legs)
sentinels = [s.lower() for s in cfg["sentinels"]]

def code(tpl, **kv):
    s = tpl.replace("__NEEDS__", NEEDS)
    s = (s.replace("__FIELDS__", json.dumps(B.FIELDS))
          .replace("__FLAGS__", json.dumps(B.FLAGS))
          .replace("__SENTINELS__", json.dumps(sentinels))
          .replace("__VERIFIED_STATUSES__", repr(tuple(cfg["verified_statuses"])))
          .replace("__CAPTURE_PREFIX__", cfg["capture_prefix"])
          .replace("__ENRICHED__", json.dumps(sorted({l["field"] for l in legs})))
          .replace("__GUARANTEED__", json.dumps(B.GUARANTEED_OUT)))
    for k, v in kv.items():
        s = s.replace("__%s__" % k, v)
    return s

def resolve_code(l):
    return code(B.RESOLVE, FIELD=l["field"], SOURCE=l["source"],
                PATHS=json.dumps(l["out_paths"]),
                SKIPKEY=repr(l.get("skip") or ""),
                WANTKEY=repr(l.get("want") or ""),
                REQUIRES=json.dumps(l.get("requires") or []),
                NEED=l["need"], CAPTURE=json.dumps(l.get("capture") or {}))

INTAKE_FULL = code(B.INTAKE)

bodies = {"intake": NEEDS + INTAKE_FULL, "emit": code(B.EMIT)}
for l in legs:
    bodies["resolve:" + l["key"]] = resolve_code(l)

fails = 0
for name, src in bodies.items():
    try:
        ast.parse(src)
    except SyntaxError as e:
        print("SYNTAX ERROR in %s: %s" % (name, e)); fails += 1; continue
    if "__" in src:
        left = sorted({w for w in src.split() if w.startswith("__") and w.endswith("__")
                       and w not in ("__name__",)})
        if left:
            print("UNSUBSTITUTED MARKER in %s: %s" % (name, left)); fails += 1
print("parsed %d generated handler bodies, %d failures" % (len(bodies), fails))

# ---- behavioural run ----------------------------------------------------------
EXAMPLE_LEGS = {"contact_linkedin_flat", "contact_linkedin_paid", "email_flat",
                "email_flat_b", "email_fallback", "phone_flat", "email_verify"}
if not EXAMPLE_LEGS <= {l["key"] for l in legs}:
    print("\nnot the shipped example config: parse checks done, behavioural block skipped")
    sys.exit(1 if fails else 0)

class Ctx:
    def __init__(self, d): self.d = d
    def get_input(self, k): return self.d.get(k)

def load(src, name):
    m = types.ModuleType(name)
    m.__dict__["__name__"] = name
    exec(compile(src, name, "exec"), m.__dict__)
    return m

intake = load(bodies["intake"], "intake")
rec = intake.handler(Ctx({"contact_name": "Ada Lovelace", "company_name": "Analytical Engines",
                          "company_domain": "https://engines.test/about", "skip_phone": "true",
                          "callback_url": "https://hooks.test/inbound"}))

checks = []
checks.append(("domain normalized", rec["company_domain"] == "engines.test"))
checks.append(("name split", (rec["first_name"], rec["last_name"]) == ("Ada", "Lovelace")))
checks.append(("supplied provenance", rec["company_domain_source"] == "supplied"))
checks.append(("skip_phone honoured", rec["skip_phone"] is True))
checks.append(("absent skip defaults to false", rec["skip_email"] is False))
checks.append(("company fields are requestable via opt-IN flags",
               {"want_company_domain", "want_company_linkedin"} <= set(B.WANTS)))
checks.append(("opt-in flags default to false (not requested)",
               rec["want_company_domain"] is False))
checks.append(("phone leg not needed", rec["need_phone_flat"] is False))
checks.append(("domain leg not needed (supplied)", rec["need_company_domain"] is False))
checks.append(("pivot leg needed", rec["need_contact_linkedin_flat"] is True))
checks.append(("email flat BLOCKED on pivot", rec["need_email_flat"] is False))
checks.append(("has_callback", rec["has_callback"] is True))
body = json.loads(rec["_body_contact_linkedin_flat"])
checks.append(("pivot body shape", body == {"name": "Ada Lovelace",
                                            "company": "Analytical Engines"}))
checks.append(("email body empty w/o pivot", rec["_body_email_flat"] == ""))
# The query is keyed by the PROVIDER's parameter names, not ours — `full_name` here is
# their spelling of our `contact_name`. Getting that direction wrong sends a body the
# provider ignores while answering 200.
checks.append(("GET query keyed by the provider's own param names",
               rec["_query_email_flat_b"] ==
               {"full_name": "Ada Lovelace", "domain": "engines.test"}))
checks.append(("no credential-shaped key on the record",
               not [k for k in rec if B.CREDENTIAL_SHAPED.search(k)]))

# --- ENABLING LOOKUPS: the whole point of item 4 ---------------------------------
# Nobody asks for a company domain. It must still be fetched when a leg that needs it is
# wanted, and must NOT be fetched when every such leg is switched off.
nod = intake.handler(Ctx({"contact_name": "Ada Lovelace", "company_name": "Analytical Engines"}))
checks.append(("enabler fires when a consumer needs it", nod["need_company_domain"] is True))
allskip = intake.handler(Ctx({"contact_name": "Ada Lovelace", "company_name": "Analytical Engines",
                              "skip_email": "true", "skip_phone": "true",
                              "skip_linkedin": "true"}))
checks.append(("enabler does NOT fire when all consumers skipped",
               allskip["need_company_domain"] is False))
checks.append(("no credit-billed leg runs under full skip",
               all(allskip.get(k) is False for k in allskip if k.startswith("need_"))))
# A company-domain skip suppresses it only where nothing downstream needs it. The email
# fallback requires a domain, so skipping it while wanting email must still fetch one.
dom_req = intake.handler(Ctx({"contact_name": "Ada Lovelace", "company_name": "Analytical Engines",
                              "skip_email": "true", "skip_phone": "true", "skip_linkedin": "true",
                              "want_company_domain": "true"}))
checks.append(("an opt-in field fires when explicitly requested, with nothing else wanted",
               dom_req["need_company_domain"] is True))

# Skipping LinkedIn as an OUTPUT must still fetch it when email is wanted, or email is dead.
lonly = intake.handler(Ctx({"contact_name": "Ada Lovelace", "company_name": "Analytical Engines",
                            "company_domain": "engines.test", "skip_linkedin": "true"}))
checks.append(("pivot still fetched as an enabler for email",
               lonly["need_contact_linkedin_flat"] is True))
noemail = intake.handler(Ctx({"contact_name": "Ada Lovelace", "company_name": "Analytical Engines",
                              "company_domain": "engines.test", "skip_linkedin": "true",
                              "skip_email": "true", "skip_phone": "true"}))
checks.append(("pivot NOT fetched when nothing needs it",
               noemail["need_contact_linkedin_flat"] is False))

# --- the cascade proper ----------------------------------------------------------
r_pivot = load(bodies["resolve:contact_linkedin_flat"], "r1")
rec2 = r_pivot.handler(Ctx({"prev": rec, "found": {"data": {"result": {
    "linkedin_url": "https://www.linkedin.com/in/ada"}}}}))
checks.append(("pivot filled", rec2["contact_linkedin"] == "https://www.linkedin.com/in/ada"))
checks.append(("pivot attributed", rec2["contact_linkedin_source"] == "flat_provider_a"))
checks.append(("email flat now needed", rec2["need_email_flat"] is True))
checks.append(("email body now built",
               json.loads(rec2["_body_email_flat"]) ==
               {"person_linkedin_url": "https://www.linkedin.com/in/ada"}))

r_native = load(bodies["resolve:contact_linkedin_paid"], "r2")
rec3 = r_native.handler(Ctx({"prev": rec2, "found": {}}))
checks.append(("attribution preserved", rec3["contact_linkedin_source"] == "flat_provider_a"))

r_ef = load(bodies["resolve:email_flat"], "r3")
rec4 = r_ef.handler(Ctx({"prev": rec3, "found": {"data": {"email": None}}}))
checks.append(("flat email miss", rec4["contact_email_source"] == "not_found"))
r_fb = load(bodies["resolve:email_fallback"], "r5")
rec5 = r_fb.handler(Ctx({"prev": rec4, "found": {"email": "ada@engines.test", "email_source": "hunter"}}))
checks.append(("fallback hit", rec5["contact_email"] == "ada@engines.test"))
checks.append(("fallback attributed", rec5["contact_email_source"] == "deepline_waterfall"))

# --- the four non-hit outcomes must stay distinguishable -------------------------
r_ph = load(bodies["resolve:phone_flat"], "r4")
rec_s = r_ph.handler(Ctx({"prev": dict(rec5, skip_phone=False, need_phone_flat=True),
                          "found": {"data": {"phone": "n/a"}}}))
checks.append(("sentinel rejected", rec_s["contact_phone_source"] == "not_found"))
rec_sk = r_ph.handler(Ctx({"prev": rec5, "found": {}}))
checks.append(("opt-out reads skipped", rec_sk["contact_phone_source"] == "skipped"))
rec_bl = r_ph.handler(Ctx({"prev": dict(rec5, skip_phone=False, contact_linkedin="",
                                        need_phone_flat=False), "found": {}}))
checks.append(("missing input reads blocked_missing_input",
               rec_bl["contact_phone_source"] == "blocked_missing_input"))
r_dom = load(bodies["resolve:company_domain"], "r7")
rec_nn = r_dom.handler(Ctx({"prev": dict(allskip, company_domain=""), "found": {}}))
checks.append(("enabler nobody needed reads not_needed",
               rec_nn["company_domain_source"] == "not_needed"))

# --- verification + emit ---------------------------------------------------------
r_v = load(bodies["resolve:email_verify"], "r6")
rec6 = r_v.handler(Ctx({"prev": rec5, "found": {"status": "valid", "sub_status": "alias_address", "free_email": False}}))
emit = load(bodies["emit"], "emit")
out = emit.handler(Ctx({"prev": rec6}))
checks.append(("verified true", out["contact_email_verified"] == "true"))
checks.append(("verified_only populated", out["contact_email_verified_only"] == "ada@engines.test"))
checks.append(("domain match true", out["contact_email_domain_match"] == "true"))
checks.append(("capture kept sub_status", rec6.get("contact_email_verify_sub_status") == "alias_address"))
checks.append(("record_json is parseable", isinstance(json.loads(out["record_json"]), dict)))
checks.append(("filled_count counts non-supplied", out["filled_count"] >= 2))

# --- the OUTPUT CONTRACT: record_json is the deliverable, not the wire record ------
cj = json.loads(out["record_json"])
enriched = {l["field"] for l in legs}
checks.append(("no plumbing in record_json",
               not [k for k in cj if k.startswith("_") or k.startswith("need_")]))
checks.append(("no _source for a field nothing enriches",
               not [k for k in cj if k.endswith("_source") and k[:-7] not in enriched]))
for f in ("contact_name", "company_name", "contact_email", "contact_phone", "contact_linkedin",
          "contact_email_verify_status"):
    checks.append(("contract carries " + f, f in cj))
for f in ("contact_email_verified", "contact_email_verified_only",
          "contact_email_domain_match", "filled_fields", "filled_count",
          "captured_fields", "source_ref"):
    checks.append(("contract carries " + f, f in cj))
checks.append(("contract carries a source per enriched field",
               all(f + "_source" in cj for f in enriched)))
checks.append(("skips echoed so the sources are explainable",
               all(k in cj for k in ("skip_email", "skip_phone", "skip_linkedin"))))
# The email leg MISSED on this path, so its own capture never fires — only the verify
# leg's does. Asserting both would be asserting against data this run does not produce.
checks.append(("the guaranteed six are present even when blank",
               all(g in cj for g in B.GUARANTEED_OUT)))
blankrec = emit.handler(Ctx({"prev": intake.handler(Ctx(
    {"contact_name": "Ada Lovelace", "company_name": "Engines",
     "skip_email": "true", "skip_phone": "true", "skip_linkedin": "true"}))}))
bj = json.loads(blankrec["record_json"])
checks.append(("guaranteed six survive a fully skipped record",
               all(g in bj for g in B.GUARANTEED_OUT)))
checks.append(("a skipped field is blank, not missing",
               bj["contact_email"] == "" and bj["contact_phone"] == ""))
checks.append(("declared captures survive to the contract",
               cj.get("contact_email_verify_sub_status") == "alias_address"))
checks.append(("a capture whose source path was empty is absent, not blank",
               "person_all_emails_json" not in cj))

rec7 = dict(rec6, contact_email="ryan@elsewhere.test")
out2 = emit.handler(Ctx({"prev": rec7}))
checks.append(("verified+mismatch flagged", (out2["contact_email_verified"],
                                             out2["contact_email_domain_match"]) == ("true", "false")))

# --- the runner end to end, against a fake Deepline -------------------------------
class FakeDeepline:
    def __init__(self, answers): self.answers, self.calls = answers, []
    def tool(self, tool, payload):
        self.calls.append((tool, payload))
        if tool == "generic_http_request" and payload["url"].startswith("https://hooks."):
            return {"status_code": 200, "ok": True, "data": {}}
        if tool == "generic_http_request":
            hit = self.answers.get(payload["url"].rsplit("/", 1)[-1])
            if isinstance(hit, Exception): raise hit
            return {"status_code": 200, "ok": True, "data": hit or {}}
        return self.answers.get(tool, {})
    def play(self, play, payload):
        self.calls.append((play, payload))
        return self.answers.get(play, {})

os.environ["FLAT_PROVIDER_A_KEY"] = "k-test"
os.environ["FLAT_PROVIDER_B_KEY"] = "k-test-b"
h = B.handlers(cfg, legs)
dl = FakeDeepline({
    "crustdata_v3_company_enrich": [{"matches": [{"company_data": {"basic_info": {"primary_domain": "engines.test"}}}]}],
    "person-linkedin-url": RuntimeError("generic_http_request: 401 unauthorized"),
    "prebuilt/person-to-linkedin-harvestapi": {"linkedin_url": "https://www.linkedin.com/in/ada"},
    "person-email": {"email": "ada@engines.test"},
    "person-phone": {"phone": "+15550100"},
    "zerobounce_validate": {"status": "valid", "sub_status": "", "free_email": False}})
o = B.run_record(dl, cfg, legs, h, {"contact_name": "Ada Lovelace", "company_name": "Analytical Engines",
                                    "callback_url": "https://hooks.test/in", "source_ref": "row-1"})
rj = json.loads(o["record_json"])
called = [c[0] for c in dl.calls]
checks.append(("runner: enabler filled the domain", rj["company_domain"] == "engines.test"
               and rj["company_domain_source"] == "crustdata"))
checks.append(("runner: a 401 is a leg error, not a silent miss",
               any("contact_linkedin_flat" in e and "401" in e for e in o["leg_errors"])))
checks.append(("runner: the paid pivot finder ran after the flat one failed",
               rj["contact_linkedin_source"] == "deepline_waterfall"))
checks.append(("runner: flat email used the bought pivot", rj["contact_email_source"] == "flat_provider_a"))
checks.append(("runner: billed email waterfall never ran",
               "prebuilt/name-and-domain-to-email-waterfall" not in called))
checks.append(("runner: verified", rj["contact_email_verified"] == "true"))
http = [p for t, p in dl.calls if t == "generic_http_request" and "person-email" in p["url"]][0]
checks.append(("runner: key read from env into the declared header", http["headers"]["x-api-key"] == "k-test"))
checks.append(("runner: key never reaches the output", "k-test" not in json.dumps(o, default=str)))
checks.append(("runner: callback POSTed the contract",
               o.get("callback_status") == "sent" and dl.calls[-1][1]["body_json"]["source_ref"] == "row-1"))
dl2 = FakeDeepline({})
o2 = B.run_record(dl2, cfg, legs, h, {"contact_name": "Ada Lovelace", "company_name": "Analytical Engines",
                                      "contact_email": "ada@x.test", "contact_linkedin": "https://www.linkedin.com/in/ada",
                                      "skip_phone": "true", "company_domain": "x.test"})
rj2 = json.loads(o2["record_json"])
checks.append(("runner: supplied values are never looked up again",
               rj2["contact_linkedin_source"] == "supplied" and rj2["contact_email_source"] == "supplied"
               and [c[0] for c in dl2.calls] == ["zerobounce_validate"]))
checks.append(("runner: skip_phone means no phone call", rj2["contact_phone_source"] == "skipped"))
try:
    B.validate(cfg, legs + [{"key": "bad", "field": "contact_email", "source": "x", "out_paths": ["e"],
                             "provider": {"type": "http", "url": "https://a.test", "api_key": "x",
                                          "key_env": "A", "key_header": "x-api-key"}}])
    checks.append(("validate refuses a credential-shaped field", False))
except SystemExit:
    checks.append(("validate refuses a credential-shaped field", True))

bad = [n for n, ok in checks if not ok]
for n, ok in checks:
    print("  %s %s" % ("ok  " if ok else "FAIL", n))
print("\n%d/%d behavioural checks passed" % (len(checks) - len(bad), len(checks)))
sys.exit(1 if (bad or fails) else 0)
