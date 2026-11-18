#!/usr/bin/env python3
"""
Run the contact enrichment cascade through the Deepline CLI, from a declarative config.

Per record:  intake -> for each leg in order: [need_<key>? call provider] -> resolve -> emit
             -> optional callback POST

Every resolve returns the COMPLETE record and recomputes every need_<key> flag, so a later
leg on the same field fires only if the earlier ones came back empty. Several legs naming the
same `field` is how a waterfall is expressed. No extra machinery.

Provider types (see references/cascade-config.md):
  deepline_tool  `deepline tools execute <tool>`   -- one Deepline-billed provider call
  deepline_play  `deepline plays run <play>`       -- a Deepline waterfall play (credit-billed tier)
  http           `deepline tools execute generic_http_request` -- your own flat-rate provider;
                 the key is read from the environment variable named in `key_env` at call
                 time and is never written to the config, a record, or any output
  none           leg omitted

Credentials: this script has no code path that accepts an API key as an argument or a config
value. An http leg names the ENVIRONMENT VARIABLE that holds its key, nothing more.

Usage:
    python3 cascade.py --config cascade-config.json --dry-run
    python3 cascade.py --config cascade-config.json --record '{"contact_name":"..","company_name":".."}'
    python3 cascade.py --config cascade-config.json --csv in.csv --out out.csv [--columns map.json] [--limit N]
    python3 cascade.py --report out.csv
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


# THE INTERFACE. Prescribed and identical for every config, and the whole reason the runner
# needs nothing from the caller up front: a CSV's columns are mapped onto these inputs with
# --columns, whatever they happen to be called. There is nothing to read and nothing to ask.
REQUIRED_IN = ["contact_name", "company_name"]
OPTIONAL_IN = ["contact_email", "contact_linkedin", "contact_phone",
               # Accepted, never required. Each is a lookup not made, and a domain is the
               # cheapest lever there is.
               "company_domain", "job_title"]

# The six the cascade always returns, blank when skipped or not found. A consumer written
# against these works against any cascade this runner produces.
GUARANTEED_OUT = ["contact_name", "company_name", "contact_email", "contact_linkedin",
                  "contact_phone", "contact_email_verified"]

# The record contract: the interface plus what the cascade derives and fills internally.
FIELDS = ["contact_name", "first_name", "last_name", "job_title", "company_name",
          "company_domain", "company_linkedin", "contact_linkedin",
          "contact_email", "contact_phone", "contact_email_verify_status"]
# Caller opt-OUTS, for the three fields the cascade exists to fill. Absent means FALSE — do
# the work — so a caller who has never heard of these gets the full cascade.
SKIPS = ["skip_linkedin", "skip_email", "skip_phone"]

# Caller opt-INS, for the two company fields. These are enabling lookups: they exist because
# the legs after them need a domain or a company profile, and nobody asks for one on its own.
# So they default OFF and fire anyway whenever something downstream requires them — which
# keeps "an enabler costs nothing when nothing needs it" true.
#
# They get a flag at all because without one a field can never be REQUESTED, only inherited
# from whatever happens to need it: a provider that returns a company LinkedIn URL for free
# had no way to be asked for one. Opt-in rather than opt-out because the opposite polarity
# would fire these on every record where the field is missing, adding cost nobody asked for.
WANTS = ["want_company_domain", "want_company_linkedin"]
FLAGS = SKIPS + WANTS

# Config keys that used to carry credentials. Present in an old config, they are a hard
# failure with a migration message rather than a silent downgrade.
RETIRED_KEYS = ("http_secrets", "http_secret_header", "client_env")
CREDENTIAL_SHAPED = re.compile(
    r"(api[_-]?key|secret|token|bearer|authorization|passwo?rd)", re.I)

# ---------------------------------------------------------------- code bodies

INTAKE = r'''
def handler(context):
    # Plain string work only, plus json, so the same handler text is portable to any
    # sandboxed code runtime. Inputs are FLAT rather than one `payload` object so a CSV row
    # maps straight onto them; `payload` is still accepted for a JSON record.
    p = context.get_input("payload") or {}

    def s(v):
        return v.strip() if isinstance(v, str) else ""

    def either(k):
        return s(context.get_input(k)) or s(p.get(k))

    def skip(k):
        # Absent means do the work. Only an explicit true-ish value switches a field off, so
        # a caller that knows nothing about these flags gets the full cascade.
        v = str(context.get_input(k) if context.get_input(k) is not None
                else p.get(k, "")).strip().lower()
        return v in ("true", "1", "yes", "on")

    def domain(v):
        v = s(v).lower().replace("https://", "").replace("http://", "").strip("/")
        return v.split("/")[0]

    contact_name = either("contact_name")
    parts = contact_name.split()
    rec = {
        "contact_name": contact_name,
        # Derived, not part of the interface — a caller supplies one name, not three.
        "first_name": parts[0] if parts else "",
        "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
        "job_title": either("job_title"),
        "company_name": either("company_name"),
        "company_domain": domain(either("company_domain")),
        "company_linkedin": either("company_linkedin"),
        "contact_linkedin": either("contact_linkedin"),
        "contact_email": either("contact_email").lower(),
        "contact_phone": either("contact_phone"),
    }
    if not rec["contact_name"] or not rec["company_name"]:
        raise Exception("contact_name and company_name are required")

    for k in __FLAGS__:
        rec[k] = skip(k)

    # Provenance starts as supplied-or-unknown; each resolve overwrites its own field.
    for f in __FIELDS__:
        rec[f + "_source"] = "supplied" if rec.get(f) else "unknown"

    rec["source_ref"] = either("source_ref") or "n/a"
    rec["callback_url"] = either("callback_url") or ""
    rec["record_json"] = ""
    return _needs(rec)
'''


def needs_code(legs):
    """Generate _needs() from the leg list.

    A leg runs only when: the caller wants it, the field is still missing, AND every field
    it depends on is populated. That last clause is what stops a cascade erroring on an
    input it never got. Provider inputs marked required reject an empty string outright, so
    a leg whose pivot was never found must SKIP rather than fire and die.

    Request bodies are built here rather than in intake because a leg's body can reference a
    field an EARLIER leg resolved. _needs() runs after every resolve, so by the time a leg
    is called its body was rebuilt from the current record.
    """
    lines = ["import json as _cj", "", "",
             "def _needs(rec):",
             "    def val(f):",
             "        return str(rec.get(f) or '').strip()",
             "",
             "    def missing(f):",
             "        return not val(f)",
             ""]
    for l in legs:
        # A leg is eligible when the caller did not switch its field off, OR when some other
        # leg REQUIRES this field and is itself still wanted. That second clause is what makes
        # an enabling lookup happen: a profile URL nobody asked for still gets fetched when
        # the email leg cannot run without one. Without it, every leg keyed off that input
        # reports blocked_missing_input and the cascade quietly does nothing.
        consumers = [c for c in legs
                     if c is not l and l["field"] in (c.get("requires") or [])]
        cons = " or ".join(
            "(%s and missing(%r))" % (
                ("not rec.get(%r)" % c["skip"]) if c.get("skip")
                else ("bool(rec.get(%r))" % c["want"]) if c.get("want") else "True",
                c["field"])
            for c in consumers) or "False"
        if l.get("skip"):
            own = "not rec.get(%r)" % l["skip"]          # opt-out: on unless switched off
        elif l.get("want"):
            own = "bool(rec.get(%r))" % l["want"]        # opt-in: off unless asked for
        else:
            own = "False"                                 # pure enabler: demand only
        conds = ["(%s or (%s))" % (own, cons), "missing(%r)" % l["field"]]
        for r in l.get("requires", []):
            conds.append("not missing(%r)" % r)
        lines.append("    rec[%r] = (%s)" % (l["need"], " and ".join(conds)))
    lines.append("    rec['has_callback'] = bool(val('callback_url'))")
    for l in legs:
        pv = l["provider"]
        if pv["type"] != "http":
            continue
        k = l["key"]
        bmap, bstat = pv.get("body") or {}, pv.get("body_static") or {}
        if bmap or bstat:
            lines.append("    _b = dict(%r)" % (bstat,))
            for param, field in bmap.items():
                lines.append("    if val(%r): _b[%r] = val(%r)" % (field, param, field))
            cond = (" and ".join("val(%r)" % f for f in bmap.values()) if bmap else "True")
            lines.append("    rec['_body_%s'] = _cj.dumps(_b) if (%s) else ''" % (k, cond))
        else:
            lines.append("    rec['_body_%s'] = ''" % k)
        qmap, qstat = pv.get("query") or {}, pv.get("query_static") or {}
        if qmap or qstat:
            lines.append("    _q = dict(%r)" % (qstat,))
            for param, field in qmap.items():
                lines.append("    if val(%r): _q[%r] = val(%r)" % (field, param, field))
            lines.append("    rec['_query_%s'] = _q" % k)
    lines += ["    return rec", ""]
    return "\n".join(lines)


RESOLVE = r'''
import json

__NEEDS__

def handler(context):
    prev = context.get_input("prev") or {}
    found = context.get_input("found")
    rec = dict(prev)

    FIELD = "__FIELD__"
    SOURCE = "__SOURCE__"
    PATHS = __PATHS__
    SENTINELS = __SENTINELS__
    SKIP_KEY = __SKIPKEY__
    WANT_KEY = __WANTKEY__
    REQUIRES = __REQUIRES__
    # Extra data this leg contributes beyond its primary field. Providers often return far
    # more than the one value the leg exists to fill, and throwing it away means paying for
    # it twice when a later stage wants it. A dict or list is JSON-stringified so it can
    # ride through the record and out of emit.
    CAPTURE = __CAPTURE__

    def dig(obj, path):
        cur = obj
        for part in path.split("."):
            if isinstance(cur, list):
                cur = cur[0] if cur else None
            if not isinstance(cur, dict):
                return None
            cur = cur.get(part)
        return cur

    value = ""
    if isinstance(found, (dict, list)):
        # Scan a list of candidate paths rather than trusting one pinned response path. A
        # wrong pin resolves to null and reads as "not found", which is the failure hardest
        # to spot; a scan either finds the value or genuinely did not get one.
        for p in PATHS:
            v = dig(found, p)
            if isinstance(v, list):
                v = v[0] if v else None
            if v and str(v).strip() and str(v).strip().lower() not in SENTINELS:
                value = str(v).strip()
                break

    already = str(rec.get(FIELD) or "").strip()
    if already:
        # Do NOT clobber an attribution an earlier leg already set. When several legs fill
        # the same field (a provider waterfall), every later leg sees the value present and
        # would relabel it "supplied", erasing which provider actually found it - and with
        # it any ability to judge provider hit rates.
        cur = str(rec.get(FIELD + "_source") or "")
        if cur in ("", "unknown"):
            rec[FIELD + "_source"] = "supplied"
    elif value:
        rec[FIELD] = value
        rec[FIELD + "_source"] = SOURCE
    elif not prev.get("__NEED__"):
        # The leg never ran, and there are three different reasons why. Collapsing them
        # would make every provider hit rate downstream meaningless.
        if SKIP_KEY and rec.get(SKIP_KEY):
            rec[FIELD + "_source"] = "skipped"              # the caller switched it off
        elif WANT_KEY and not rec.get(WANT_KEY):
            rec[FIELD + "_source"] = "not_needed"           # opt-in, not asked for
        elif any(not str(rec.get(r) or "").strip() for r in REQUIRES):
            rec[FIELD + "_source"] = "blocked_missing_input"  # an input it needs never arrived
        else:
            rec[FIELD + "_source"] = "not_needed"          # nothing downstream wanted it
    else:
        rec[FIELD + "_source"] = "not_found"

    for out_key, path in CAPTURE.items():
        if str(rec.get(out_key) or "").strip():
            continue
        v = dig(found, path) if isinstance(found, (dict, list)) else None
        if v is None or v == [] or v == {}:
            continue
        rec[out_key] = (json.dumps(v, ensure_ascii=False)
                        if isinstance(v, (dict, list)) else str(v))

    return _needs(rec)
'''

EMIT = r'''
import json


def handler(context):
    rec = dict(context.get_input("prev") or {})
    rec.pop("record_json", None)
    out = dict(rec)

    # The record travelling between legs carries machinery: the per-leg request bodies, the
    # need_* gates, the pinned constants. None of that is the deliverable, and a callback that
    # POSTs it is shipping this runner's internals to somebody else's endpoint. So the OUTPUT
    # CONTRACT is built by exclusion here, and it is what record_json carries.
    ENRICHED = __ENRICHED__
    GUARANTEED = __GUARANTEED__
    noise = set(f + "_source" for f in __FIELDS__ if f not in ENRICHED)
    contract = {k: v for k, v in rec.items()
                if not k.startswith("_") and not k.startswith("need_") and k not in noise}
    # The guaranteed six are present even when empty. A consumer should never have to test
    # whether a key exists before reading it — blank means skipped or not found, and that is
    # a value, not an absence.
    for g in GUARANTEED:
        contract.setdefault(g, "")

    # The callback body is assembled here so the POST stays a dumb transport.
    out["record_json"] = json.dumps(contract, ensure_ascii=False)
    out["callback_url"] = str(rec.get("callback_url") or "")
    out["has_callback"] = bool(out["callback_url"])
    out["_method_post"] = "POST"
    out["_headers_json"] = {"Content-Type": "application/json"}
    # Verification is reported, never destructive. The found address is always emitted so a
    # human can look at it; the VERIFIED slot is what downstream automation should consume,
    # and it is blank unless a verifier actually said so. A wrong address that silently
    # reaches a sending tool is worse than a blank one, and a "risky" or catch-all verdict
    # is not a pass unless the installer declared it one.
    vs = str(rec.get("contact_email_verify_status") or "").strip().lower()
    verified = vs in __VERIFIED_STATUSES__
    out["contact_email_verified"] = "true" if verified else "false"
    out["contact_email_verified_only"] = rec.get("contact_email", "") if verified else ""
    out["contact_email_verify_status"] = vs or "not_checked"

    # Deliverability is not correctness. A mailbox can verify perfectly and belong to a
    # different person at a different company, so the domain comparison is reported
    # separately: verified true with domain_match false is suspect, not clean.
    em = str(rec.get("contact_email") or "").strip().lower()
    dom = str(rec.get("company_domain") or "").strip().lower()
    if em and "@" in em and dom:
        em_dom = em.split("@")[-1]
        root = lambda h: ".".join(h.split(".")[-2:]) if h.count(".") >= 1 else h
        out["contact_email_domain_match"] = "true" if root(em_dom) == root(dom) else "false"
    else:
        out["contact_email_domain_match"] = "unknown"

    # Anything a leg captured beyond its own field, by the agreed prefix.
    pfx = "__CAPTURE_PREFIX__"
    out["captured_fields"] = ",".join(sorted(k for k in rec
                                             if k.startswith(pfx) and rec.get(k))) or "none"
    filled = [f for f in __FIELDS__
              if str(rec.get(f) or "").strip() and rec.get(f + "_source") not in ("supplied",)]
    out["filled_fields"] = ",".join(filled) or "none"
    out["filled_count"] = len(filled)
    # Re-assemble record_json now that the reporting fields exist, so the callback payload and
    # the CSV row describe the same record rather than differing by a few keys.
    for k in ("contact_email_verified", "contact_email_verified_only",
              "contact_email_verify_status", "contact_email_domain_match",
              "captured_fields", "filled_fields", "filled_count"):
        contract[k] = out[k]
    out["record_json"] = json.dumps(contract, ensure_ascii=False)
    return out
'''

PROVIDER_TYPES = ("deepline_tool", "deepline_play", "http")


# ---------------------------------------------------------------- Deepline CLI

def _cli(args, payload=None):
    """Run one deepline command; return parsed JSON. Payload goes through a temp file so a
    record never lands in a process listing."""
    tmp = None
    if payload is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            tmp = f.name
        args = args + ["--input", "@" + tmp]
    try:
        p = subprocess.run(["deepline"] + args + ["--json"], capture_output=True, text=True,
                           env={**os.environ, "DEEPLINE_SKIP_SELF_UPDATE": "1"})
    finally:
        if tmp:
            os.unlink(tmp)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise RuntimeError("deepline %s: %s" % (args[1] if len(args) > 1 else args, (p.stdout + p.stderr)[:400]))
    if p.returncode or (isinstance(out, dict) and out.get("ok") is False):
        err = out.get("error", out) if isinstance(out, dict) else out
        raise RuntimeError(json.dumps(err)[:600])
    return out


def find_output(obj, required):
    """Locate a play's output object inside the CLI's run payload: the first dict carrying
    every key the play's output schema declares required."""
    if isinstance(obj, dict):
        if required and all(k in obj for k in required):
            return obj
        for v in obj.values():
            hit = find_output(v, required)
            if hit is not None:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = find_output(v, required)
            if hit is not None:
                return hit
    return None


class Deepline:
    """The only object that talks to Deepline. Tests swap in a fake with the same methods."""

    def __init__(self):
        self._play_required = {}

    def describe_tool(self, tool):
        return _cli(["tools", "describe", tool])

    def describe_play(self, play):
        return _cli(["plays", "describe", play])

    def tool(self, tool, payload):
        out = _cli(["tools", "execute", tool], payload)
        return (out.get("toolResponse") or {}).get("raw", out)

    def play(self, play, payload):
        if play not in self._play_required:
            sch = self.describe_play(play).get("outputSchema") or {}
            self._play_required[play] = sch.get("required") or []
        out = _cli(["plays", "run", play], payload)
        hit = find_output(out, self._play_required[play])
        if hit is None:
            raise RuntimeError("%s: no output object with %s in the run payload"
                               % (play, self._play_required[play]))
        return hit


# ---------------------------------------------------------------- generated handlers

def handlers(cfg, legs):
    """Compile intake, one resolve per leg, and emit from the templates above. The same
    generated source that test_codegen.py parses and exercises."""
    for l in legs:
        l["need"] = "need_" + l["key"]
    NEEDS = needs_code(legs)
    sentinels = [s.lower() for s in (cfg.get("sentinels") or ["n/a", "none", "null"])]
    verified = tuple(s.lower() for s in (cfg.get("verified_statuses") or ["deliverable", "valid"]))

    def code(tpl, **kv):
        s = tpl.replace("__NEEDS__", NEEDS)
        s = (s.replace("__FIELDS__", json.dumps(FIELDS))
              .replace("__FLAGS__", json.dumps(FLAGS))
              .replace("__SENTINELS__", json.dumps(sentinels))
              .replace("__VERIFIED_STATUSES__", repr(verified))
              .replace("__CAPTURE_PREFIX__", cfg.get("capture_prefix") or "person_")
              .replace("__ENRICHED__", json.dumps(sorted({l["field"] for l in legs})))
              .replace("__GUARANTEED__", json.dumps(GUARANTEED_OUT)))
        for k, v in kv.items():
            s = s.replace("__%s__" % k, v)
        return s

    def load(src, name):
        ns = {"__name__": name}
        exec(compile(src, name, "exec"), ns)
        return ns["handler"]

    out = {"intake": load(NEEDS + code(INTAKE), "intake"), "emit": load(code(EMIT), "emit")}
    for l in legs:
        out[l["key"]] = load(code(RESOLVE, FIELD=l["field"], SOURCE=l["source"],
                                  PATHS=json.dumps(l["out_paths"]),
                                  SKIPKEY=repr(l.get("skip") or ""),
                                  WANTKEY=repr(l.get("want") or ""),
                                  REQUIRES=json.dumps(l.get("requires") or []),
                                  NEED=l["need"], CAPTURE=json.dumps(l.get("capture") or {})),
                             "resolve:" + l["key"])
    return out


class Ctx:
    def __init__(self, d):
        self.d = d

    def get_input(self, k):
        return self.d.get(k)


def _inputs(l, rec):
    """{provider param: record field} -> payload. A list value ["field"] sends [value]."""
    payload = dict(l.get("input_static") or {})
    for param, field in (l.get("tool_inputs") or {}).items():
        if isinstance(field, list):
            v = [str(rec.get(f) or "").strip() for f in field]
            if all(v):
                payload[param] = v
        else:
            v = str(rec.get(field) or "").strip()
            if v:
                payload[param] = v
    return payload


def call(dl, l, rec):
    pv = l["provider"]
    if pv["type"] == "deepline_tool":
        return dl.tool(pv["tool"], _inputs(l, rec))
    if pv["type"] == "deepline_play":
        return dl.play(pv["play"], _inputs(l, rec))
    # http: a flat-rate provider through generic_http_request. Auth comes from the env.
    k = l["key"]
    key = os.environ.get(pv["key_env"], "")
    if not key:
        raise RuntimeError("%s: environment variable %s is not set" % (k, pv["key_env"]))
    headers = {"Content-Type": "application/json"}
    headers.update(pv.get("headers") or {})
    headers[pv["key_header"]] = (pv.get("key_prefix") or "") + key
    req = {"url": pv["url"], "method": pv.get("method", "POST"), "headers": headers}
    if rec.get("_body_" + k):
        req["body_json"] = json.loads(rec["_body_" + k])
    if rec.get("_query_" + k):
        req["query"] = rec["_query_" + k]
    return dl.tool("generic_http_request", req)


def run_record(dl, cfg, legs, h, row):
    """One record through the cascade. Returns the emitted output (record_json is the contract)
    plus leg_errors, which is diagnostics, not contract."""
    rec = h["intake"](Ctx(row))
    errors = []
    for l in legs:
        found = None
        if rec.get(l["need"]):
            try:
                found = call(dl, l, rec)
            except RuntimeError as e:
                # A failed call reads as not_found in the record; the error stays visible here
                # so a 401 from a wrong key is not mistaken for a provider miss.
                errors.append("%s: %s" % (l["key"], e))
        rec = h[l["key"]](Ctx({"prev": rec, "found": found}))
    out = h["emit"](Ctx({"prev": rec}))
    out["leg_errors"] = errors
    cb = cfg.get("callback")
    if out.get("has_callback") and (cb is None or cb.get("enabled", True)):
        try:
            dl.tool("generic_http_request", {"url": out["callback_url"], "method": "POST",
                                             "headers": {"Content-Type": "application/json"},
                                             "body_json": json.loads(out["record_json"])})
            out["callback_status"] = "sent"
        except RuntimeError as e:
            out["callback_status"] = "failed: %s" % e
    return out


# ---------------------------------------------------------------- validation

def validate(cfg, legs, dl=None):
    """Everything checkable before any paid call. With `dl`, also check every declared input
    against the live Deepline tool / play schema (describe is free)."""
    problems = []
    for k in RETIRED_KEYS:
        if k in cfg:
            problems.append("config key %r is retired: it carried an API key. Delete it and "
                            "give each http leg `key_env`, the NAME of an environment "
                            "variable holding the key." % k)
    for l in legs:
        pv = l["provider"]
        for key in list(pv) + list(pv.get("headers") or {}):
            if CREDENTIAL_SHAPED.search(str(key)):
                problems.append("%s: field %r looks like a credential. A key never goes in "
                                "this config; name its environment variable in `key_env`."
                                % (l["key"], key))
        if pv["type"] not in PROVIDER_TYPES:
            problems.append("%s: unknown provider type %r (use %s or none)"
                            % (l["key"], pv["type"], ", ".join(PROVIDER_TYPES)))
        if pv["type"] == "http":
            if not pv.get("url", "").startswith("https://"):
                problems.append("%s: an http leg needs an https:// url (auth headers require "
                                "https)" % l["key"])
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", pv.get("key_env") or ""):
                problems.append("%s: an http leg must name `key_env`, the UPPER_CASE "
                                "environment variable holding the key" % l["key"])
            if not pv.get("key_header"):
                problems.append("%s: an http leg must name `key_header` (e.g. x-api-key or "
                                "Authorization, from the provider's spec)" % l["key"])
        if l["field"] not in FIELDS:
            problems.append("%s: field %r is not part of the record contract %s"
                            % (l["key"], l["field"], FIELDS))
        if l.get("skip") and l["skip"] not in SKIPS:
            problems.append("%s: skip flag %r is not one of %s" % (l["key"], l["skip"], SKIPS))
        if l.get("want") and l["want"] not in WANTS:
            problems.append("%s: want flag %r is not one of %s" % (l["key"], l["want"], WANTS))
        if l.get("skip") and l.get("want"):
            problems.append("%s: a leg carries either `skip` (opt-out) or `want` (opt-in), "
                            "never both" % l["key"])
        for r in l.get("requires", []):
            if r not in FIELDS:
                problems.append("%s: requires %r, which is not a record field" % (l["key"], r))

    # Validate declared inputs against the provider's REAL schema. A guessed parameter name
    # fails at run time as a missing-input error, after money was spent on the legs above it.
    if dl is not None and not problems:
        for l in legs:
            pv = l["provider"]
            try:
                if pv["type"] == "deepline_tool":
                    d = dl.describe_tool(pv["tool"])
                    fields = (d.get("inputSchema") or {}).get("fields") or []
                    known = {f["name"] for f in fields}
                    required = {f["name"] for f in fields if f.get("required")}
                elif pv["type"] == "deepline_play":
                    sch = dl.describe_play(pv["play"]).get("inputSchema") or {}
                    known, required = set(sch.get("properties") or {}), set(sch.get("required") or [])
                else:
                    continue
            except RuntimeError as e:
                problems.append("%s: %s does not resolve: %s"
                                % (l["key"], pv.get("tool") or pv.get("play"), e))
                continue
            declared = set(l.get("tool_inputs") or {}) | set(l.get("input_static") or {})
            if declared - known:
                problems.append("%s: unknown input(s) %s; provider accepts %s"
                                % (l["key"], sorted(declared - known), sorted(known)))
            if required - declared:
                problems.append("%s: required input(s) not mapped %s"
                                % (l["key"], sorted(required - declared)))
            if not (set(l.get("requires") or []) >= {f for p, f in (l.get("tool_inputs") or {}).items()
                                                      if p in required and isinstance(f, str)}):
                problems.append("%s: every field mapped to a REQUIRED provider input must also "
                                "be in `requires`, or the leg fires with it empty" % l["key"])
    if problems:
        raise SystemExit("config will not run:\n  " + "\n  ".join(problems))


# ---------------------------------------------------------------- reach-rate report

def report(rows):
    sources = sorted({k for r in rows for k in r if k.endswith("_source")})
    lines = ["%d records" % len(rows)]
    for s in sources:
        hist = {}
        for r in rows:
            v = r.get(s) or ""
            if v:
                hist[v] = hist.get(v, 0) + 1
        lines.append("%-30s %s" % (s[:-7], " · ".join("%s %d" % kv for kv in
                                                     sorted(hist.items(), key=lambda kv: -kv[1]))))
    errs = sum(1 for r in rows if r.get("leg_errors") not in (None, "", "[]"))
    lines.append("records with a leg error: %d (read leg_errors before trusting not_found)" % errs)
    return "\n".join(lines)




def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate the config against live Deepline schemas; call nothing paid")
    ap.add_argument("--record", help="one JSON record to run")
    ap.add_argument("--csv", help="input CSV; one record per row")
    ap.add_argument("--columns", help="JSON {interface field: csv column} when names differ")
    ap.add_argument("--out", help="output CSV for --csv runs")
    ap.add_argument("--limit", type=int, help="only the first N rows (smoke test)")
    ap.add_argument("--report", metavar="OUT_CSV", help="print the reach-rate report of a finished run")
    a = ap.parse_args()

    if a.report:
        print(report(list(csv.DictReader(open(a.report, newline="")))))
        return
    if not a.config:
        ap.error("--config is required")
    cfg = json.load(open(a.config))
    legs = [l for l in cfg["legs"] if l.get("provider", {}).get("type") != "none"]
    if not legs:
        raise SystemExit("no legs enabled: every leg's provider type is 'none'.")
    dl = Deepline()
    validate(cfg, legs, dl)
    for l in legs:
        pv = l["provider"]
        print("  %-24s -> %s %s" % (l["key"], pv["type"], pv.get("tool") or pv.get("play") or
                                    "%s %s (key from $%s)" % (pv.get("method", "POST"), pv["url"], pv["key_env"])))
    print("config validated against live Deepline schemas")
    if a.dry_run:
        print("dry run: nothing was called.")
        return
    h = handlers(cfg, legs)

    if a.record:
        out = run_record(dl, cfg, legs, h, json.loads(a.record))
        print(json.dumps({**json.loads(out["record_json"]), "leg_errors": out["leg_errors"],
                          "callback_status": out.get("callback_status", "")}, indent=2))
        return
    if not (a.csv and a.out):
        ap.error("give --record, or --csv with --out")
    if os.path.exists(a.out):
        raise SystemExit("%s exists; refusing to overwrite a finished run" % a.out)
    cols = json.load(open(a.columns)) if a.columns else {}
    rows, results = list(csv.DictReader(open(a.csv, newline=""))), []
    for i, src in enumerate(rows[:a.limit] if a.limit else rows):
        row = {f: src.get(c, "") for f, c in cols.items()} if cols else dict(src)
        try:
            out = run_record(dl, cfg, legs, h, row)
            rec = {**json.loads(out["record_json"]), "leg_errors": json.dumps(out["leg_errors"]),
                   "callback_status": out.get("callback_status", "")}
        except Exception as e:  # rejected at intake (missing name/company) or a bad row
            rec = {"source_ref": row.get("source_ref", ""), "rejected": str(e)[:300]}
        results.append(rec)
        print("row %d: %s" % (i + 1, rec.get("rejected") or rec.get("filled_fields")), flush=True)
    keys = []
    for r in results:
        keys += [k for k in r if k not in keys]
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(results)
    print("\n" + report(results))


if __name__ == "__main__":
    main()
