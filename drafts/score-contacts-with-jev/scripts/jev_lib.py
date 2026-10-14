"""
Shared helpers for the Jev lead-score skills: the rubric, the scoring code that runs inside the
Deepline play, where state lives, and how the Deepline CLI is driven.

The two sibling packages (accounts and contacts) ship the same scripts. Only the two constants
below differ, and every script reads them from here.

Rules this file keeps:

  * Jev decides, code counts. Jev answers Choice, Noul (boolean) and Score questions; every
    number, date, list lookup, weight and cut-off is computed in code. Jev's own documentation
    says it is weak at arithmetic, dates and counting, so nothing numeric is ever asked of it.
  * The scoring code is ONE source (CORE below, plain JavaScript). The generated play embeds it,
    and the local preview runs the very same rendered text under `node`, so a preview score is the
    score the play returns for the same record and the same Jev answers. test_offline.py runs it.
  * Jev is reached through Deepline's `ai_evaluate` tool (model `typesafe-ai/jev`), billed to the
    Deepline workspace. There is no Jev key to find, save or print.
  * State lives at a path this library COMPUTES from the Deepline workspace, never one an agent
    composes per run.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SKILL = "score-contacts-with-jev"
ENTITY = "contact"          # "account" | "contact"

ENTITY_WORDS = {"account": ("account", "accounts"),
                "contact": ("contact", "contacts")}
NOUN, NOUNS = ENTITY_WORDS[ENTITY]
A_NOUN = ("an " if NOUN[0] in "aeiou" else "a ") + NOUN

# Where Jev is reached. Deepline's ai_evaluate takes a Vercel AI Gateway evaluation model id; the
# gateway lists only the unversioned "typesafe-ai/jev" (checked 2026-09-30), so the version cannot
# be pinned on this route. Every result records the model id that actually answered.
JEV = {"tool": "ai_evaluate", "model": "typesafe-ai/jev",
       "list_price_per_mtok": 0.042}   # the gateway's published input price; output is free

# The output every scoring run returns. Keys are guaranteed present; blank is a value.
OUTPUT_KEYS = ("lead_score", "lead_tier", "score_status", "score_reasons", "needs_review",
               "coverage_pct", "criteria_json", "rubric", "jev_model", "jev_input_tokens", "error",
               "source_ref", "scored_at")
STATUSES = ("scored", "disqualified", "insufficient_data", "not_scored", "failed")

RESERVED_INPUTS = ("source_ref",)


# ---------------------------------------------------------------- output

def say(msg):
    """Progress for the agent to relay. Plain words."""
    print(msg, flush=True)


def fail(msg, code=1):
    print("STOP: " + msg, file=sys.stderr, flush=True)
    raise SystemExit(code)


# ---------------------------------------------------------------- deepline CLI

def deepline(*args, allow_fail=False, timeout=600):
    """Run the deepline CLI with --json, JSON out. A failure stops the script unless allow_fail."""
    cmd = ["deepline", *args]
    if "--json" not in cmd:
        cmd.append("--json")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        fail("The `deepline` CLI is not on PATH. Install it: npm install -g deepline && "
             "deepline auth register --wait auto")
    except subprocess.TimeoutExpired:
        if allow_fail:
            return {"error": "timed out", "exit": -1}
        fail("deepline %s timed out after %ds" % (" ".join(args[:3]), timeout))
    out = r.stdout or ""
    try:
        data = json.loads(out) if out.strip() else {}
    except json.JSONDecodeError:
        data = {"raw": out}
    if r.returncode == 0:
        return data
    if allow_fail:
        return {"error": data.get("error") if isinstance(data, dict) and data.get("error") else (r.stderr or out)[:600],
                "exit": r.returncode, "data": data}
    fail("deepline %s failed (exit %s): %s" % (" ".join(args[:3]), r.returncode, (r.stderr or out)[:600]))


def workspace():
    who = deepline("auth", "status")
    ws = who.get("workspace") or {}
    if not ws.get("id"):
        fail("`deepline auth status` did not return a workspace. Run `deepline auth register --wait auto`, then re-run.")
    return {"id": str(ws["id"]), "name": ws.get("name")}


def find_run_id(obj):
    """The run id in whatever JSON `plays run` or --run-id-file wrote. Field names are read loosely
    because they were not observed live for this skill."""
    if isinstance(obj, dict):
        for k in ("runId", "run_id", "workflowId", "id"):
            v = obj.get(k)
            if isinstance(v, str) and v:
                return v
        for v in obj.values():
            got = find_run_id(v)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = find_run_id(v)
            if got:
                return got
    return None


# ---------------------------------------------------------------- state

def state_dir(workspace_id=None):
    """~/.local/state/<skill>/<deepline-workspace-id>/ — computed, never composed by the caller."""
    wid = str(workspace_id or workspace()["id"])
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    d = os.path.join(base, SKILL, wid)
    os.makedirs(d, mode=0o700, exist_ok=True)
    return d


def load(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def slug(text):
    out, dash = [], False
    for ch in (text or "").lower():
        if ch.isalnum():
            out.append(ch)
            dash = False
        elif not dash and out:
            out.append("-")
            dash = True
    return "".join(out).strip("-")[:60] or "rubric"


def rubric_path(name, workspace_id=None):
    d = os.path.join(state_dir(workspace_id), "rubrics")
    os.makedirs(d, mode=0o700, exist_ok=True)
    return os.path.join(d, slug(name) + ".json")


def list_rubrics(workspace_id=None):
    d = os.path.join(state_dir(workspace_id), "rubrics")
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def load_rubric(name=None, workspace_id=None):
    """The saved rubric by name; with no name, the only one there is."""
    names = list_rubrics(workspace_id)
    if not name:
        if len(names) == 1:
            name = names[0]
        elif not names:
            fail("No rubric saved for this workspace yet. Save one first: rubric_tool.py save <file>")
        else:
            fail("Several rubrics are saved (%s); say which with --rubric." % ", ".join(names))
    p = rubric_path(name, workspace_id)
    if not os.path.exists(p):
        fail("No rubric called %r. Saved: %s" % (name, ", ".join(names) or "none"))
    return validate_rubric(load(p, {}))


# ======================================================================= the rubric

RULE_KINDS = ("bands", "match", "lookup", "present", "days_since")
QUESTION_KINDS = ("noul", "choice", "score")
ABSTAIN = "not_enough_information"


def _num_or_fail(v, where, lo=None, hi=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        fail("%s: %r is not a number" % (where, v))
    if x != x or x in (float("inf"), float("-inf")):
        fail("%s: %r is not a finite number" % (where, v))
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        fail("%s: %g must be between %g and %g" % (where, x, lo, hi))
    return x


def _ident(v, where):
    s = str(v or "")
    if not s or not all(c.islower() or c.isdigit() or c == "_" for c in s) or not s[0].isalpha():
        fail("%s: %r must be lower_snake_case, starting with a letter" % (where, v))
    return s


def _bands(raw, where):
    if not isinstance(raw, list) or not raw:
        fail("%s: bands must be a non-empty list" % where)
    out = []
    for i, b in enumerate(raw):
        if not isinstance(b, dict):
            fail("%s: band %d must be an object" % (where, i + 1))
        nb = {"points": _num_or_fail(b.get("points", 0), "%s band %d points" % (where, i + 1)),
              "says": str(b.get("says") or "").strip()}
        if b.get("below") is not None:
            nb["below"] = _num_or_fail(b["below"], "%s band %d below" % (where, i + 1))
        out.append(nb)
    capped = [b for b in out if "below" in b]
    if capped != sorted(capped, key=lambda b: b["below"]):
        fail("%s: bands must be in increasing order of `below`" % where)
    if len([b for b in out if "below" not in b]) > 1 or ("below" not in out[-1] and len(out) > 1 and
                                                         any("below" not in b for b in out[:-1])):
        fail("%s: only the last band may leave `below` out (it catches everything above)" % where)
    return out


def validate_rubric(doc):
    """Check a rubric and return it normalised. Every script loads rubrics through this, so a
    rubric that reaches the play has passed it. Fails naming the first problem."""
    if not isinstance(doc, dict):
        fail("rubric: expected a JSON object")
    ent = doc.get("entity") or ENTITY
    if ent != ENTITY:
        fail("rubric: this rubric is for %s records, but this skill scores %s" % (ent, NOUNS))
    name = str(doc.get("name") or "").strip()
    if not name:
        fail("rubric: give it a name")
    inputs_raw = doc.get("inputs")
    if not isinstance(inputs_raw, dict) or not inputs_raw:
        fail("rubric: `inputs` must name at least one field")
    inputs = {}
    for k, v in inputs_raw.items():
        k = _ident(k, "input")
        if k in RESERVED_INPUTS:
            fail("input %r is reserved; rename it" % k)
        v = v if isinstance(v, dict) else {"label": str(v)}
        t = v.get("type") or "text"
        if t not in ("text", "number", "date"):
            fail("input %s: type must be text, number or date" % k)
        inputs[k] = {"label": str(v.get("label") or k.replace("_", " ")), "type": t,
                     "required": bool(v.get("required")),
                     "max_chars": int(v.get("max_chars") or 4000)}
    ids = set()

    def new_id(i, where):
        i = _ident(i, where)
        if i in ids:
            fail("%s: id %r is used twice" % (where, i))
        ids.add(i)
        return i

    rules = []
    for n, r in enumerate(doc.get("rules") or [], start=1):
        where = "rule %d" % n
        if not isinstance(r, dict):
            fail("%s: must be an object" % where)
        rid = new_id(r.get("id"), where)
        kind = r.get("kind")
        if kind not in RULE_KINDS:
            fail("rule %s: kind must be one of %s" % (rid, ", ".join(RULE_KINDS)))
        inp = r.get("input")
        if inp not in inputs:
            fail("rule %s: input %r is not one of the rubric's inputs" % (rid, inp))
        nr = {"id": rid, "label": str(r.get("label") or rid.replace("_", " ")), "kind": kind, "input": inp,
              "disqualify": bool(r.get("disqualify")), "origin": str(r.get("origin") or "")}
        if kind in ("bands", "days_since"):
            nr["bands"] = _bands(r.get("bands"), "rule %s" % rid)
            if nr["disqualify"]:
                fail("rule %s: a %s rule cannot disqualify; use a match rule" % (rid, kind))
        elif kind == "match":
            vals = r.get("values")
            if not isinstance(vals, list) or not vals:
                fail("rule %s: `values` must be a non-empty list" % rid)
            nr["values"] = [str(x).strip().lower() for x in vals if str(x).strip()]
            nr["mode"] = r.get("mode") or "equals"
            if nr["mode"] not in ("equals", "contains"):
                fail("rule %s: mode must be equals or contains" % rid)
            nr["points"] = _num_or_fail(r.get("points", 0), "rule %s points" % rid)
            nr["miss_points"] = _num_or_fail(r.get("miss_points", 0), "rule %s miss_points" % rid)
            nr["says"] = str(r.get("says") or "").strip()
            nr["miss_says"] = str(r.get("miss_says") or "").strip()
        elif kind == "lookup":
            tbl = r.get("table")
            if not isinstance(tbl, dict) or not tbl:
                fail("rule %s: `table` must map values to points, e.g. {\"a\": {\"points\": 25, \"says\": \"tier A account\"}}" % rid)
            nr["table"] = {}
            for tk, tv in tbl.items():
                tv = tv if isinstance(tv, dict) else {"points": tv}
                nr["table"][str(tk).strip().lower()] = {
                    "points": _num_or_fail(tv.get("points", 0), "rule %s value %s points" % (rid, tk)),
                    "says": str(tv.get("says") or "%s %s" % (nr["label"].lower(), tk)).strip()}
            nr["miss_points"] = _num_or_fail(r.get("miss_points", 0), "rule %s miss_points" % rid)
            nr["miss_says"] = str(r.get("miss_says") or "").strip()
            if nr["disqualify"]:
                fail("rule %s: a lookup rule cannot disqualify; use a match rule" % rid)
        else:  # present
            nr["points"] = _num_or_fail(r.get("points", 0), "rule %s points" % rid)
            nr["says"] = str(r.get("says") or "").strip()
            nr["miss_says"] = str(r.get("miss_says") or "").strip()
        rules.append(nr)

    questions = []
    for n, q in enumerate(doc.get("questions") or [], start=1):
        where = "question %d" % n
        if not isinstance(q, dict):
            fail("%s: must be an object" % where)
        qid = new_id(q.get("id"), where)
        kind = q.get("kind")
        if kind not in QUESTION_KINDS:
            fail("question %s: kind must be one of %s (Jev's Noul, Choice, Score)" % (qid, ", ".join(QUESTION_KINDS)))
        reads = q.get("reads")
        if isinstance(reads, str):
            reads = [reads]
        if not isinstance(reads, list) or not reads or any(x not in inputs for x in reads):
            fail("question %s: `reads` must list the inputs it needs, from: %s" % (qid, ", ".join(inputs)))
        ins = q.get("instructions")
        if not ins or not isinstance(ins, (str, dict, list)):
            fail("question %s: needs `instructions` (the question Jev answers)" % qid)
        nq = {"id": qid, "label": str(q.get("label") or qid.replace("_", " ")), "kind": kind,
              "reads": list(reads), "instructions": ins, "origin": str(q.get("origin") or "")}
        if kind == "noul":
            crit = q.get("criteria") or {}
            if crit and not isinstance(crit, dict):
                fail("question %s: criteria must be {\"true\": ..., \"false\": ...}" % qid)
            nq["criteria"] = {k: crit[k] for k in ("true", "false") if crit.get(k)}
            pts = q.get("points") or {}
            nq["points"] = {"yes": _num_or_fail(pts.get("yes", 0), "question %s yes points" % qid),
                            "no": _num_or_fail(pts.get("no", 0), "question %s no points" % qid)}
            nq["says_yes"] = str(q.get("says_yes") or "").strip()
            nq["says_no"] = str(q.get("says_no") or "").strip()
            if q.get("disqualify_at") is not None:
                d = _num_or_fail(q["disqualify_at"], "question %s disqualify_at" % qid)
                if not 0.5 <= d <= 1:
                    fail("question %s: disqualify_at must be between 0.5 and 1" % qid)
                nq["disqualify_at"] = d
        elif kind == "choice":
            opts = q.get("options")
            if not isinstance(opts, dict) or len(opts) < 2:
                fail("question %s: a choice needs at least two options" % qid)
            no = {}
            for ok, ov in opts.items():
                ok = _ident(ok, "question %s option" % qid)
                ov = ov if isinstance(ov, dict) else {"means": ov}
                no[ok] = {"means": ov.get("means"), "points": _num_or_fail(ov.get("points", 0),
                                                                           "question %s option %s points" % (qid, ok)),
                          "says": str(ov.get("says") or ok.replace("_", " ")).strip(),
                          "disqualify": bool(ov.get("disqualify"))}
            if ABSTAIN not in no:
                no[ABSTAIN] = {"means": "The information given does not say enough to decide.",
                               "points": 0.0, "says": "not enough information", "disqualify": False}
            if len(no) > 255:
                fail("question %s: Jev takes at most 255 options" % qid)
            nq["options"] = no
            nq["disqualify_at"] = _num_or_fail(q.get("disqualify_at", 0.8), "question %s disqualify_at" % qid, 0.5, 1)
        else:  # score
            lv = q.get("levels")
            if not isinstance(lv, list) or not 2 <= len(lv) <= 10:
                fail("question %s: a score needs 2 to 10 `levels`, lowest first" % qid)
            nq["levels"] = lv
            nq["points"] = _num_or_fail(q.get("points", 0), "question %s points" % qid)
            if nq["points"] < 0:
                fail("question %s: a score's points must be positive (lowest level earns 0)" % qid)
        questions.append(nq)

    if not rules and not questions:
        fail("rubric: add at least one rule or question")
    tiers = doc.get("tiers") or [{"tier": "A", "min": 70}, {"tier": "B", "min": 45},
                                 {"tier": "C", "min": 25}, {"tier": "D", "min": 0}]
    tiers = sorted(({"tier": str(t["tier"]), "min": _num_or_fail(t["min"], "tier min")} for t in tiers),
                   key=lambda t: -t["min"])
    if tiers[-1]["min"] > 0:
        fail("tiers: the lowest tier must start at 0, or some scores get no tier")
    for t in tiers:
        if t["tier"] in STATUSES:
            fail("tiers: %r is reserved for a status; name the tier something else" % t["tier"])
    out = {"entity": ENTITY, "name": name, "version": int(doc.get("version") or 1),
           "about": doc.get("about") or {}, "inputs": inputs, "rules": rules, "questions": questions,
           "tiers": tiers, "tiers_origin": str(doc.get("tiers_origin") or ""),
           "confidence_floor": _num_or_fail(doc.get("confidence_floor", 0.6), "confidence_floor (a share, 0 to 1)", 0, 1),
           "min_coverage": _num_or_fail(doc.get("min_coverage", 0.5), "min_coverage (a share, 0 to 1)", 0, 1)}
    if max_points(out) <= 0:
        fail("rubric: nothing can earn points, so every score would be 0")
    return out


def item_max(it):
    """The most points one rule or question can add."""
    k = it["kind"]
    if k in ("bands", "days_since"):
        return max([b["points"] for b in it["bands"]] + [0])
    if k in ("match",):
        return max(it["points"], it["miss_points"], 0)
    if k == "lookup":
        return max([v["points"] for v in it["table"].values()] + [it["miss_points"], 0])
    if k == "present":
        return max(it["points"], 0)
    if k == "noul":
        return max(it["points"]["yes"], it["points"]["no"], 0)
    if k == "choice":
        return max([o["points"] for o in it["options"].values()] + [0])
    return max(it["points"], 0)


def max_points(r):
    return sum(item_max(i) for i in r["rules"] + r["questions"])


def estimate_tokens(r):
    """Rough input tokens per record (4 chars a token): every question plus a typical state."""
    q = len(json.dumps([jev_question_payload(x) for x in r["questions"]]))
    state = sum(min(v["max_chars"], 600) for k, v in r["inputs"].items()
                if any(k in x["reads"] for x in r["questions"]))
    return int((q + state) / 4) + 60


def jev_question_payload(q):
    """A rubric question as ai_evaluate takes it (the `questions` map entry). A Noul is the
    evaluation API's `boolean`."""
    if q["kind"] == "noul":
        p = {"type": "boolean", "instructions": q["instructions"]}
        if q.get("criteria"):
            p["criteria"] = q["criteria"]
        return p
    if q["kind"] == "choice":
        return {"type": "choice", "instructions": q["instructions"],
                "criteria": {k: v.get("means") for k, v in q["options"].items()}}
    return {"type": "score", "instructions": q["instructions"], "criteria": q["levels"]}


def rubric_card(r, price=True):
    """The rubric as the installer reads it before anything is built. Plain text."""
    mx = max_points(r)
    L = ["Rubric: %s (v%d) — scores %s, 0 to 100" % (r["name"], r["version"], NOUNS), ""]
    L.append("Worked out in code (free, no Jev call):")
    if not r["rules"]:
        L.append("  (none)")
    for it in r["rules"]:
        src = r["inputs"][it["input"]]["label"]
        if it["kind"] in ("bands", "days_since"):
            unit = " days ago" if it["kind"] == "days_since" else ""
            parts = []
            lo = None
            for b in it["bands"]:
                rng = ("under %s" % _fmt(b["below"])) if lo is None and "below" in b else (
                    ("%s–%s" % (_fmt(lo), _fmt(b["below"] - 1))) if "below" in b else "%s+" % _fmt(lo if lo is not None else 0))
                parts.append("%s%s → %+g" % (rng, unit, b["points"]))
                lo = b.get("below", lo)
            L.extend(_wrapped("  %-26s from %s: " % (it["label"], src), parts))
        elif it["kind"] == "match":
            vals = ", ".join(it["values"][:6]) + (" …" if len(it["values"]) > 6 else "")
            verdict = "DISQUALIFIES" if it["disqualify"] else "%+g, otherwise %+g" % (it["points"], it["miss_points"])
            L.extend(_wrapped("  %-26s from %s: " % (it["label"], src),
                              ["%s %s → %s" % ("is one of" if it["mode"] == "equals" else "contains", vals, verdict)]))
        elif it["kind"] == "lookup":
            L.extend(_wrapped("  %-26s from %s: " % (it["label"], src),
                              ["%s → %+g" % (k.upper() if len(k) == 1 else k, v["points"]) for k, v in it["table"].items()]
                              + ["anything else → %+g" % it["miss_points"]]))
        else:
            L.append("  %-26s from %s: present → %+g" % (it["label"], src, it["points"]))
    L += ["", "Asked of Jev (one request per %s, all questions together):" % NOUN]
    if not r["questions"]:
        L.append("  (none)")
    for q in r["questions"]:
        reads = ", ".join(r["inputs"][k]["label"] for k in q["reads"])
        if q["kind"] == "noul":
            pure_dq = q.get("disqualify_at") and not (q["points"]["yes"] or q["points"]["no"])
            tail = [] if pure_dq else ["yes %+g" % q["points"]["yes"], "no %+g" % q["points"]["no"]]
            if q.get("disqualify_at"):
                tail.append("yes at %d%%+ DISQUALIFIES" % round(q["disqualify_at"] * 100))
            L.extend(_wrapped("  %-26s Noul (yes/no) on %s: " % (q["label"], reads), tail))
        elif q["kind"] == "choice":
            L.extend(_wrapped("  %-26s Choice on %s: " % (q["label"], reads),
                              ["%s %+g%s" % (k, o["points"], " (disqualifies)" if o["disqualify"] else "")
                               for k, o in q["options"].items()]))
        else:
            L.append("  %-26s Score (%d levels) on %s: 0 to %+g" % (q["label"], len(q["levels"]), reads, q["points"]))
    L += ["", "Most points possible: %s. Tiers: %s." % (_fmt(mx), ", ".join(
        "%s ≥ %s" % (t["tier"], _fmt(t["min"])) for t in r["tiers"])),
          "Below %d%% coverage (too little data to judge) %s is 'insufficient_data', not a low tier."
          % (round(r["min_coverage"] * 100), A_NOUN),
          "Answers under %d%% confidence are listed in needs_review." % round(r["confidence_floor"] * 100)]
    borrowed = [i["label"] for i in r["rules"] + r["questions"] if i.get("origin") == "default"]
    if r.get("tiers_origin") == "default":
        borrowed.append("tier cut-offs")
    if borrowed:
        L.append("Borrowed defaults you accepted rather than chose: %s." % ", ".join(borrowed))
    if price and r["questions"]:
        tok = estimate_tokens(r)
        cost = tok * JEV["list_price_per_mtok"] / 1e6
        L.append("Jev through Deepline (ai_evaluate): about %d input tokens per %s, roughly $%.3f per 1,000"
                 % (tok, NOUN, cost * 1000))
        L.append("%s at the gateway's list price. Deepline bills it from usage; the preview's real" % NOUNS)
        L.append("charge shows in `deepline billing`.")
    return "\n".join(L)


def _wrapped(head, parts, width=100):
    """head + parts joined by "; ", wrapped at word boundaries under the head's indent."""
    import textwrap
    glue = "\x00"          # keeps "x → +5" and "option +25" on one line
    text = "; ".join(parts).replace(" → ", glue + "→" + glue).replace(" days ago", glue + "days" + glue + "ago")
    text = text.replace(" DISQUALIFIES", glue + "DISQUALIFIES")
    for sign in "+-":
        for d in "0123456789":
            text = text.replace(" " + sign + d, glue + sign + d)
    lines = textwrap.wrap(text, width=width, initial_indent=head, subsequent_indent=" " * 29,
                          break_on_hyphens=False, break_long_words=False) or [head.rstrip()]
    return [l.replace(glue, " ") for l in lines]


def _fmt(x):
    x = float(x)
    return ("{:,.0f}".format(x) if x == int(x) else "{:,.2f}".format(x))


# ======================================================================= the code that runs in the play
# One source, plain JavaScript. Rendered with the rubric and the mapping baked in as JSON. The play
# embeds it; the local preview and the offline tests run the identical text under `node`.

CORE = r'''
const RUBRIC = __RUBRIC__;
const JEV = __JEV__;
const INPUT_MAP = __INPUT_MAP__;
const ABSTAIN = "not_enough_information";
// The clock: set once per run from a checkpointed ctx.step in the play (reading the wall clock
// in play code is not replay-safe), and from the local clock in the preview.
let NOW_MS = 0;

function _s(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v).trim();
}

function _r2(x) { return Math.round(x * 100) / 100; }

function _num(v) {
  // A number from text: '1,200' -> 1200; '51-200' or '1,001-5,000' -> the midpoint;
  // '10k', '2.5M', '$3.4bn', '5 million', '1.2B' -> scaled. null when there is no number.
  const t = _s(v).replace(/,/g, "").replace(/\$/g, "").toLowerCase();
  const units = [["thousand", 1e3], ["million", 1e6], ["billion", 1e9], ["bn", 1e9], ["mn", 1e6],
                 ["k", 1e3], ["m", 1e6], ["b", 1e9]];
  const nums = [];
  let cur = "";
  for (let i = 0; i <= t.length; i++) {
    const ch = i < t.length ? t[i] : " ";
    if (/[0-9]/.test(ch) || (ch === "." && cur && cur.indexOf(".") < 0)) {
      cur += ch;
    } else if (cur) {
      let n = parseFloat(cur);
      const rest = t.slice(i).replace(/^ +/, "");
      for (const [word, mult] of units) {
        if (rest.startsWith(word) && !/\p{L}/u.test(rest.charAt(word.length))) { n *= mult; break; }
      }
      nums.push(n);
      cur = "";
      if (nums.length === 2) break;
    }
  }
  if (!nums.length) return null;
  return nums.length === 2 ? (nums[0] + nums[1]) / 2 : nums[0];
}

function _civil_days(y, m, d) {
  // Days since 1970-01-01 for a calendar date, by arithmetic alone (no Date parsing, which reads
  // "2020-02" and time zones differently across runtimes).
  y -= m <= 2 ? 1 : 0;
  const era = Math.floor((y >= 0 ? y : y - 399) / 400);
  const yoe = y - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
  return era * 146097 + doe - 719468;
}

function _int(s) { return /^\s*-?\d+\s*$/.test(s) ? parseInt(s, 10) : null; }

function _days_since(v) {
  // Whole days (UTC) from a date written YYYY-MM-DD, YYYY-MM or YYYY to now. null if unreadable.
  const parts = _s(v).slice(0, 10).replace(/\//g, "-").split("-");
  const y = _int(parts[0]);
  const m = parts.length > 1 && parts[1] ? _int(parts[1]) : 1;
  const d = parts.length > 2 && parts[2] ? _int(parts[2].slice(0, 2)) : 1;
  if (y === null || m === null || d === null) return null;
  if (!(y >= 1900 && y <= 2200 && m >= 1 && m <= 12 && d >= 1 && d <= 31)) return null;
  return Math.floor(NOW_MS / 86400000) - _civil_days(y, m, d);
}

function _band(bands, x) {
  for (const b of bands) {
    if (!("below" in b) || x < b.below) return b;
  }
  return bands[bands.length - 1];
}

function _norm(v) {
  let s = _s(v).toLowerCase();
  for (const p of ["https://", "http://", "www."]) {
    if (s.startsWith(p)) s = s.slice(p.length);
  }
  return s.replace(/\/+$/, "").trim();
}

function _item(it, status, points, answer, confidence, says, assessable, disq, verdict) {
  // One criterion's result. `points` is what it earned (for a Jev answer, expected points over
  // the probabilities); `verdict` is what the chosen answer is worth on its own, which decides
  // whether the reason reads as counting for the record or against it.
  return {id: it.id, label: it.label, kind: it.kind, status: status, answer: answer,
          confidence: confidence === undefined ? null : confidence, points: _r2(points),
          max: it._max, says: says || "", assessable: assessable !== false, disqualifies: !!disq,
          verdict: _r2(verdict === undefined || verdict === null ? points : verdict)};
}

function apply_rule(r, vals) {
  const raw = vals[r.input] || "";
  if (!raw) return _item(r, "blocked_missing_input", 0, "", null, "", false);
  const k = r.kind;
  if (k === "bands" || k === "days_since") {
    const x = k === "bands" ? _num(raw) : _days_since(raw);
    if (x === null) return _item(r, "unreadable", 0, raw.slice(0, 80), null, "", false);
    const b = _band(r.bands, x);
    return _item(r, "supplied", b.points, raw.slice(0, 80), null, b.says || "");
  }
  if (k === "match") {
    const v = _norm(raw);
    const hit = r.mode === "equals" ? r.values.indexOf(v) >= 0 : r.values.some(x => v.indexOf(x) >= 0);
    if (hit) return _item(r, "supplied", r.disqualify ? 0 : r.points, raw.slice(0, 80), null, r.says || "", true, r.disqualify);
    return _item(r, "supplied", r.disqualify ? 0 : r.miss_points, raw.slice(0, 80), null, r.miss_says || "");
  }
  if (k === "lookup") {
    const hit = r.table[_norm(raw)];
    if (hit) return _item(r, "supplied", hit.points, raw.slice(0, 80), null, hit.says || "");
    return _item(r, "supplied", r.miss_points, raw.slice(0, 80), null, r.miss_says || "");
  }
  return _item(r, "supplied", r.points, "present", null, r.says || "");
}

function question_payload(q) {
  if (q.kind === "noul") {
    const p = {type: "boolean", instructions: q.instructions};
    if (q.criteria && Object.keys(q.criteria).length) p.criteria = q.criteria;
    return p;
  }
  if (q.kind === "choice") {
    const c = {};
    for (const k of Object.keys(q.options)) c[k] = q.options[k].means === undefined ? null : q.options[k].means;
    return {type: "choice", instructions: q.instructions, criteria: c};
  }
  return {type: "score", instructions: q.instructions, criteria: q.levels};
}

function pick(row) {
  // A record's inputs: the rubric's own key first, then the column the build mapped onto it.
  const out = {};
  const r = row || {};
  for (const k of Object.keys(RUBRIC.inputs).concat(["source_ref"])) {
    let v = r[k];
    if ((v === undefined || v === null || v === "") && INPUT_MAP[k]) v = r[INPUT_MAP[k]];
    out[k] = v;
  }
  return out;
}

function intake(inp) {
  // Everything decided before Jev is asked: rules, which questions have the data they read,
  // the one ai_evaluate request. A question whose inputs are all blank is never sent.
  inp = inp || {};
  const vals = {};
  for (const k of Object.keys(RUBRIC.inputs)) vals[k] = _s(inp[k]).slice(0, RUBRIC.inputs[k].max_chars || 4000);
  const missing = Object.keys(RUBRIC.inputs).filter(k => RUBRIC.inputs[k].required && !vals[k]);
  const rules = RUBRIC.rules.map(r => apply_rule(r, vals));
  const dq_by_rule = rules.filter(x => x.disqualifies);
  const askable = RUBRIC.questions.filter(q => q.reads.some(k => vals[k]));
  const blocked = RUBRIC.questions.filter(q => askable.indexOf(q) < 0).map(q => q.id);
  const ask = askable.length > 0 && !missing.length && !dq_by_rule.length;
  const state = {};
  for (const q of askable) for (const k of q.reads) if (vals[k]) state[k] = vals[k];
  const questions = {};
  for (const q of askable) questions[q.id] = question_payload(q);
  return {ask: ask, missing: missing, rules: rules, asked: ask ? askable.map(q => q.id) : [],
          blocked: blocked,
          skipped_reason: missing.length ? "missing required input: " + missing.join(", ") :
            (dq_by_rule.length ? "disqualified by a rule before asking Jev" : (askable.length ? "" : "no question had the data it reads")),
          jev_body: ask ? {model: JEV.model, state: state, questions: questions} : null,
          source_ref: _s(inp.source_ref)};
}

function _margin(probs) {
  // Our confidence for a distribution: the top probability minus the runner-up. For a yes/no it
  // equals |2p - 1|, the confidence used for a Noul. null when no distribution came back.
  const vals = Object.keys(probs || {}).map(k => Number(probs[k]) || 0).sort((a, b) => b - a);
  if (!vals.length) return null;
  return vals[0] - (vals.length > 1 ? vals[1] : 0);
}

function _answer_item(q, a, floor) {
  // [item, review note] for one Jev answer. Points are the EXPECTED points over Jev's
  // probabilities, so an answer Jev is unsure of moves the score less than a sure one.
  const k = q.kind;
  if (!a || typeof a !== "object") return [_item(q, "no_answer", 0, "", null, "", false), ""];
  if (k === "noul") {
    const p = Number(a.probability) || 0;
    const pts = p * q.points.yes + (1 - p) * q.points.no;
    const conf = Math.abs(2 * p - 1);
    const yes = p >= 0.5;
    const disq = !!q.disqualify_at && p >= q.disqualify_at;
    const it = _item(q, "answered", pts, yes ? "yes" : "no", _r2(conf), (yes ? q.says_yes : q.says_no) || "",
                     true, disq, yes ? q.points.yes : q.points.no);
    let note = "";
    if (q.disqualify_at && !(q.points.yes || q.points.no)) {
      // A pure disqualifier: worth a look only when it leans yes but stops short of the bar.
      if (p >= 0.5 && p < q.disqualify_at)
        note = q.label + ": possibly (" + Math.round(p * 100) + "% yes, disqualifies at " + Math.round(q.disqualify_at * 100) + "%)";
    } else if (conf < floor) {
      note = q.label + ": unsure (" + Math.round(p * 100) + "% yes)";
    }
    return [it, note];
  }
  if (k === "choice") {
    let probs = a.probabilities || {};
    if (!Object.keys(probs).length && a.choice) { probs = {}; probs[a.choice] = 1; }
    let pts = 0;
    for (const opt of Object.keys(q.options)) pts += (Number(probs[opt]) || 0) * q.options[opt].points;
    const keys = Object.keys(probs);
    const chosen = a.choice || (keys.length ? keys.reduce((x, y) => (Number(probs[y]) > Number(probs[x]) ? y : x)) : "");
    const conf = _margin(probs);
    const disq = Object.keys(q.options).some(opt => q.options[opt].disqualify && (Number(probs[opt]) || 0) >= q.disqualify_at);
    const abstained = chosen === ABSTAIN;
    if (abstained) pts = 0;     // "not enough information" is not a partial yes: it earns nothing
    const o = q.options[chosen] || {};
    const it = _item(q, abstained ? "abstained" : "answered", pts, chosen, conf === null ? null : _r2(conf),
                     o.says || chosen, !abstained, disq, o.points || 0);
    let note = "";
    if (conf !== null && conf < floor && !abstained) {
      const top = keys.slice().sort((x, y) => (Number(probs[y]) || 0) - (Number(probs[x]) || 0)).slice(0, 2);
      note = q.label + ": unsure (" + top.map(x => x + " " + Math.round((Number(probs[x]) || 0) * 100) + "%").join(", ") + ")";
    }
    return [it, note];
  }
  const s = Number(a.score) || 0;
  const n = q.levels.length;
  const pts = Math.max(0, Math.min(1, s / (n - 1))) * q.points;
  const conf = _margin(a.probabilities);
  const level = Math.max(0, Math.min(n - 1, Math.round(s)));
  const lvl = q.levels[level];
  const it = _item(q, "answered", pts, "level " + level + " of " + (n - 1), conf === null ? null : _r2(conf),
                   typeof lvl === "string" ? lvl : JSON.stringify(lvl), true, false, level / (n - 1) * q.points);
  it.position = _r2(s);
  const note = conf !== null && conf < floor ? q.label + ": unsure (level " + s.toFixed(1) + " of " + (n - 1) + ")" : "";
  return [it, note];
}

const JEV_ERRORS = {
  authentication: "Deepline refused the call (authentication): run `deepline auth status`, then re-run",
  authorization: "Deepline refused the call (authorization): check the workspace's access to ai_evaluate",
  billing: "Deepline credits ran out (billing): top up, then re-run these records",
  rate_limit: "Jev rate limit: re-run these records later",
  network: "Jev could not be reached (network): re-run these records later",
  upstream: "Jev is unavailable or overloaded (upstream): re-run these records later",
  validation: "Jev rejected the request as malformed (validation)"};

function _unwrap(b) {
  // ai_evaluate's output, whether it came as the tool's raw envelope or one level down.
  if (typeof b === "string") { try { b = JSON.parse(b); } catch (e) { b = {raw: b}; } }
  b = b && typeof b === "object" ? b : {};
  if (!b.result && b.data && typeof b.data === "object") b = b.data;
  return b;
}

function score(ix, status_code, body) {
  // The verdict for one record. Keys are always all present. status_code is 200 when the
  // ai_evaluate call returned; otherwise body carries {category, message} from the tool error.
  ix = ix || {};
  const floor = RUBRIC.confidence_floor;
  const items = (ix.rules || []).slice();
  let model = "not called", tokens = 0, err = "";
  let answers = {};
  if (ix.ask) {
    const b = _unwrap(body);
    answers = b.result && b.result.answers && typeof b.result.answers === "object" ? b.result.answers : {};
    const code = Math.trunc(Number(status_code)) || 0;
    if (code !== 200 || !Object.keys(answers).length) {
      err = JEV_ERRORS[b.category] ||
        (code === 200 ? "Jev returned no answers: " : "Jev call failed (" + (b.category || code || "error") + "): ") +
        (b.message ? String(b.message) : JSON.stringify(b)).slice(0, 300);
      return finish(ix, [], "failed", 0, 0, "", "", model, 0, err);
    }
    model = _s((b.result.response || {}).modelId) || _s((b.meta || {}).model) || JEV.model;
    tokens = Number((b.usage || {}).inputTokens) || 0;
  }
  const notes = [];
  for (const q of RUBRIC.questions) {
    if ((ix.blocked || []).indexOf(q.id) >= 0) {
      items.push(_item(q, "blocked_missing_input", 0, "", null, "", false));
    } else if ((ix.asked || []).indexOf(q.id) < 0) {
      items.push(_item(q, "not_needed", 0, "", null, "", false));
    } else {
      const [it, note] = _answer_item(q, answers[q.id], floor);
      items.push(it);
      if (note) notes.push(note);
    }
  }
  const sum = (xs) => xs.reduce((a, b) => a + b, 0);
  const total = sum(items.map(i => i.max)) || 1;
  const earned = sum(items.map(i => i.points));
  const covered = sum(items.filter(i => i.assessable).map(i => i.max));
  const s100 = Math.round(Math.max(0, Math.min(100, 100 * earned / total)));
  const coverage = Math.round(100 * covered / total);
  const dq = items.filter(i => i.disqualifies);
  let status, tier;
  if ((ix.missing || []).length) { status = "not_scored"; tier = "not_scored"; }
  else if (dq.length) { status = "disqualified"; tier = "disqualified"; }
  else if (coverage < RUBRIC.min_coverage * 100) { status = "insufficient_data"; tier = "insufficient_data"; }
  else { status = "scored"; tier = RUBRIC.tiers.find(t => s100 >= t.min).tier; }
  const reasons = [];
  if (dq.length) reasons.push("Disqualified: " + dq.map(i => i.says || i.label).join("; "));
  if ((ix.missing || []).length) reasons.push("Not scored: missing " + ix.missing.join(", "));
  // FOR: the answer itself is worth at least half the criterion's points; shown as "(+25)".
  // AGAINST: the answer itself is worth less than half; shown as "(2 of 25)", so a low score
  // names what pulled it down, and points earned only through Jev's doubt never read as a win.
  const counted = items.filter(i => i.assessable && i.max > 0);
  const pro = counted.filter(i => i.verdict * 2 >= i.max && i.points >= 0.5).sort((a, b) => b.points - a.points);
  const con = counted.filter(i => i.verdict * 2 < i.max).sort((a, b) => (b.max - b.points) - (a.max - a.points));
  for (const i of pro.slice(0, 4)) {
    const p = Math.round(i.points);
    reasons.push(i.label + ": " + (i.says || i.answer) + " (" + (p >= 0 ? "+" : "") + p + ")");
  }
  for (const i of con.slice(0, 3)) reasons.push(i.label + ": " + (i.says || i.answer) + " (" + Math.round(i.points) + " of " + Math.round(i.max) + ")");
  const gaps = items.filter(i => !i.assessable && i.max > 0).map(i => i.label);
  if (gaps.length && (status === "scored" || status === "insufficient_data"))
    reasons.push("No data for: " + gaps.slice(0, 4).join(", ") + (gaps.length > 4 ? " …" : ""));
  return finish(ix, items, status, s100, coverage, reasons.join(" | ") || "no criterion added points",
                notes.join("; ") || "none", model, tokens, err, tier);
}

function finish(ix, items, status, s100, coverage, reasons, review, model, tokens, err, tier) {
  const crit = items.map(i => { const c = Object.assign({}, i); delete c.assessable; delete c.verdict; return c; });
  return {lead_score: s100, lead_tier: tier || status, score_status: status,
          score_reasons: (reasons || (err ? "Not scored: " + err : "none")).slice(0, 500),
          needs_review: (review || "none").slice(0, 500), coverage_pct: coverage,
          criteria_json: JSON.stringify(crit), rubric: RUBRIC.name + " v" + RUBRIC.version,
          jev_model: model, jev_input_tokens: tokens || 0, error: err,
          source_ref: ix.source_ref || "", scored_at: new Date(NOW_MS).toISOString().replace(/\.\d+Z$/, "Z")};
}
'''

NODE_MAIN = r'''
const FNS = {_num, _days_since, apply_rule, intake, score, pick};
let buf = "";
process.stdin.on("data", d => { buf += d; });
process.stdin.on("end", () => {
  NOW_MS = Date.now();
  const q = JSON.parse(buf);
  const out = FNS[q.fn](...q.args);
  process.stdout.write(JSON.stringify(out === undefined ? null : out));
});
'''


def _with_max(r):
    """The rubric as baked into the code: each item carries its own max points."""
    r = json.loads(json.dumps(r))
    for it in r["rules"] + r["questions"]:
        it["_max"] = item_max(it)
    return r


def render_core(rubric, mapping=None):
    return (CORE.replace("__RUBRIC__", json.dumps(_with_max(rubric)))
                .replace("__JEV__", json.dumps({"tool": JEV["tool"], "model": JEV["model"]}))
                .replace("__INPUT_MAP__", json.dumps({k: v for k, v in (mapping or {}).items() if v})))


def node_call(rubric, fn, *args, mapping=None):
    """Run one CORE function under node, exactly the text the play embeds."""
    if not shutil.which("node"):
        fail("`node` is not on PATH. It ships with the Deepline CLI's install (npm); install Node 18+.")
    r = subprocess.run(["node", "-e", render_core(rubric, mapping) + NODE_MAIN],
                       input=json.dumps({"fn": fn, "args": list(args)}), capture_output=True, text=True)
    if r.returncode != 0:
        fail("scoring code failed under node: %s" % (r.stderr or r.stdout)[:800])
    return json.loads(r.stdout)


def load_core(rubric, mapping=None):
    """The scoring code as callables, for the local preview and tests. Every call runs the same
    text the play runs."""
    return {name: (lambda *a, _n=name: node_call(rubric, _n, *a, mapping=mapping))
            for name in ("_num", "_days_since", "apply_rule", "intake", "score", "pick")}


def ask_jev(body):
    """One ai_evaluate call from this machine through the Deepline CLI. Returns (status, body) in
    the shape the play hands to score(): (200, tool output) or (code, {category, message})."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(body, f)
    try:
        res = deepline("tools", "execute", JEV["tool"], "--input", "@" + path, "--timeout", "90s",
                       allow_fail=True, timeout=180)
    finally:
        os.unlink(path)
    if "exit" in res:
        d = res.get("data") if isinstance(res.get("data"), dict) else {}
        e = d.get("error") if isinstance(d.get("error"), dict) else {}
        return (e.get("statusCode") or e.get("status") or 0,
                {"category": e.get("category") or e.get("code") or "", "message": str(res.get("error"))[:300]})
    tr = res.get("toolResponse") or {}
    raw = tr.get("raw") or tr.get("rawV2") or res.get("result") or res
    return 200, raw


def score_record(rubric, record, call=None, mapping=None):
    """Score one record locally exactly as the play would. `call(body)` -> (status, body) is the
    Jev call; by default it is ai_evaluate through the Deepline CLI."""
    core = load_core(rubric, mapping)
    ix = core["intake"](core["pick"](record))
    if not ix["ask"]:
        return core["score"](ix, None, None)
    status, body = (call or ask_jev)(ix["jev_body"])
    return core["score"](ix, status, body)


# ======================================================================= the play

PLAY = r'''/** @mermaid __PLAY_NAME__
 * flowchart TD
 * records[("Records: a CSV, rows, or one webhook record")] --> loop
 * subgraph loop["For each record"]
 *   jev["Ask Jev the rubric questions"] --> verdict["Score: rules, points, tier"]
 * end
 * loop --> out["Return the scored records"]
 */
// @ts-nocheck
import { definePlay } from 'deepline';
// Generated by __SKILL__ (build_scorer.py) from rubric "__RUBRIC_LABEL__". Do not edit by hand:
// change the rubric, preview it, and rebuild.
__CORE__

export default definePlay(
  '__PLAY_NAME__',
  async (ctx, input: any) => {
    NOW_MS = await ctx.step('now', async () => Date.now());
    const items: any = input && input.csv ? await ctx.csv(input.csv)
      : Array.isArray(input && input.rows) ? input.rows : [input || {}];
    // @mermaid-node records type:"dataset" out:"records"
    const records = await ctx
      .dataset('records', items)
      // @mermaid-node jev out:"jev"
      .withColumn('jev', async (row: any, rowCtx) => {
        const ix = intake(pick(row));
        if (!ix.ask) return null;
        try {
          const r: any = await rowCtx.tools.execute({
            id: 'ask_jev',
            tool: 'ai_evaluate',
            input: ix.jev_body as any,
            description: 'Ask Jev every rubric question this record has data for, in one request.',
          });
          const t = r.toolResponse;
          return { status: 200, body: t.view === 'data' ? t.rawV2.data : t.rawV2 };
        } catch (e: any) {
          // A failed Jev call never becomes a low score: the record comes back `failed`.
          return { status: e?.statusCode || 0, body: { category: e?.category || e?.code || '', message: String(e?.message || e) } };
        }
      })
      // @mermaid-node verdict out:"verdict"
      .withColumn('verdict', (row: any) => score(intake(pick(row)), row.jev ? row.jev.status : null, row.jev ? row.jev.body : null))
__FLAT_COLUMNS__
      .run({ description: 'Score each record against the rubric.', undrawnColumns: __UNDRAWN__ });
    // @mermaid-node out out:"$output"
    return { records };
  },
  {
    description: '__DESCRIPTION__',
    webhook: {},
  },
);
'''


def play_name(rubric):
    # Deepline names the play's dataset table "<play>_records" and caps table names at 63
    # characters, so the play name stays within 55.
    return ("jev-lead-score-%s-%s" % (NOUNS, slug(rubric["name"])))[:55].rstrip("-")


def render_play(rubric, mapping=None):
    """The whole .play.ts: the CORE text verbatim, one dataset, one ai_evaluate call per record,
    and every output key as its own column so an export is a flat CSV."""
    flat = "\n".join("      .withColumn('%s', (row: any) => row.verdict.%s)" % (k, k) for k in OUTPUT_KEYS)
    desc = "Scores %s 0 to 100 against the rubric %s v%d: rules in code, judgments by Jev (ai_evaluate)." % (
        NOUNS, rubric["name"], rubric["version"])
    return (PLAY.replace("__CORE__", render_core(rubric, mapping))
                .replace("__PLAY_NAME__", play_name(rubric))
                .replace("__SKILL__", SKILL)
                .replace("__RUBRIC_LABEL__", "%s v%d" % (rubric["name"].replace("*/", ""), rubric["version"]))
                .replace("__FLAT_COLUMNS__", flat)
                .replace("__UNDRAWN__", json.dumps(list(OUTPUT_KEYS)))
                .replace("__DESCRIPTION__", desc.replace("\\", "").replace("'", "")))


# ======================================================================= mapping a source onto the inputs
# A file's columns are mapped onto the rubric's inputs by name, and the proposal is SHOWN for
# correction: confirming a mapping beats reciting one, and a wrong guess is visible beside the
# right one.

def _tokens(s):
    out, cur = [], ""
    for ch in str(s or "").lower():
        if ch.isalnum():
            cur += ch
        elif cur:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


FILLER = {"on", "of", "the", "a", "an", "at", "in", "current", "or", "and", "from", "its", "their"}


def _words(s):
    return set(_tokens(s)) - FILLER


def propose_map(inputs, columns):
    """{input key: column id or None}. columns = [{"id":..., "name":...}]. Exact name or label
    first; then the column sharing the most meaningful words with the key and label (at least
    half of the column's words, and at least one). Never reuses a column. It is a PROPOSAL: the
    caller shows it for correction."""
    out, used = {}, set()
    for key, spec in inputs.items():
        exact = [_tokens(key), _tokens(spec.get("label"))]
        kw, lw = _words(key), _words(spec.get("label"))
        want = kw | lw
        best, best_score = None, 0.0
        for c in columns:
            if c["id"] in used:
                continue
            if _tokens(c.get("name")) in exact:
                best, best_score = c["id"], 9.0
                break
            ct = _words(c.get("name"))
            if not ct:
                continue
            shared = len(ct & want)
            score = shared / float(len(ct)) + shared / float(len(want) or 1)
            # A shared word must come from the input's own name, or two from its label: "Company"
            # is not "What the company does" just because they share "company".
            strong = bool(ct & kw) or len(ct & lw) >= 2
            if strong and shared * 2 >= len(ct) and score > best_score:
                best, best_score = c["id"], score
        out[key] = best
        if best:
            used.add(best)
    return out


def apply_overrides(mapping, columns, overrides):
    """--map key=Column name (or id), repeatable. Unknown columns stop the run rather than map to nothing."""
    by_name = {str(c.get("name") or "").strip().lower(): c["id"] for c in columns}
    ids = {c["id"] for c in columns}
    for o in overrides or []:
        if "=" not in o:
            fail("--map takes key=column, got %r" % o)
        k, v = o.split("=", 1)
        k, v = k.strip(), v.strip()
        if k not in mapping:
            fail("--map: %r is not one of the rubric's inputs (%s)" % (k, ", ".join(mapping)))
        if v in ("", "-", "none"):
            mapping[k] = None
        elif v in ids:
            mapping[k] = v
        elif v.lower() in by_name:
            mapping[k] = by_name[v.lower()]
        else:
            fail("--map: no column or field called %r" % v)
    return mapping


def mapping_card(inputs, mapping, columns):
    names = {c["id"]: c.get("name") for c in columns}
    L = ["%-24s <- %s" % ("input", "your column / field")]
    for k, spec in inputs.items():
        src = mapping.get(k)
        L.append("%-24s <- %s%s" % (k, (names.get(src) or src) if src else "(nothing mapped)",
                                    "   REQUIRED" if spec.get("required") and not src else ""))
    return "\n".join(L)


def read_records(path, limit=None):
    """Columns and records from a CSV, a JSON array (or {"records": [...]}) or JSON lines."""
    import csv
    if path.endswith(".csv"):
        with open(path, newline="") as f:
            recs = list(csv.DictReader(f))
    else:
        with open(path) as f:
            txt = f.read()
        try:
            recs = json.loads(txt)
            recs = recs if isinstance(recs, list) else recs.get("records") or [recs]
        except json.JSONDecodeError:
            recs = [json.loads(l) for l in txt.splitlines() if l.strip()]
    if limit:
        recs = recs[:limit]
    names = []
    for r in recs:
        for k in r:
            if k not in names:
                names.append(k)
    return [{"id": n, "name": n} for n in names], recs
