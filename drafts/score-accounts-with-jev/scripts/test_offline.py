#!/usr/bin/env python3
"""
Offline checks: no Deepline call, no network. Runs the scoring code (the exact JavaScript the play
embeds, under `node`) on fixtures, the scoring arithmetic, the rubric checks, the mapping, and the
play renderer.

    python3 -B test_offline.py        # exit 0 when every check passes

`deepline plays check` on the rendered play is not run here (it needs the CLI and a login); the
build runs it before publishing.
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jev_lib as L  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        print("FAIL " + name + ("  " + str(detail) if detail else ""))
        FAILS.append(name)


def raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


EXAMPLE = json.load(open(os.path.join(HERE, "rubric.example.json")))
R = L.validate_rubric(EXAMPLE)
check("example rubric validates for this skill's entity (%s)" % L.ENTITY, R["entity"] == L.ENTITY)


# ------------------------------------------------------------------ the play

MAPPED = list(R["inputs"])[-1]
play = L.render_play(R, {MAPPED: "Mapped column"})
check("play: embeds the scoring code verbatim", L.render_core(R, {MAPPED: "Mapped column"}) in play)
check("play: one ai_evaluate call per record", play.count("tool: 'ai_evaluate'") == 1)
check("play: clock comes from a checkpointed step, not Date.now() in the code",
      play.count("Date.now()") == 1 and "ctx.step('now'" in play)
check("play: every output key is its own column", all(".withColumn('%s'" % k in play for k in L.OUTPUT_KEYS))
check("play: webhook binding declared", "webhook: {}" in play)
check("play: name is stable, readable, and short enough for its dataset table",
      ("jev-lead-score-%s-%s" % (L.NOUNS, L.slug(R["name"]))).startswith(L.play_name(R)) and len(L.play_name(R)) <= 55)
check("play: carries no key-shaped text", "Bearer" not in play and "Authorization" not in play)

core = L.load_core(R)
num = core["_num"]
check("number: '1,200' -> 1200", num("1,200") == 1200)
check("number: '51-200' -> midpoint", num("51-200") == 125.5)
check("number: '1,001-5,000' -> midpoint", num("1,001-5,000") == 3000.5)
check("number: '10k' -> 10000", num("10k") == 10000)
check("number: '2.5M' -> 2500000", num("2.5M") == 2500000)
check("number: 'unknown' -> None", num("unknown") is None)
check("number: '$3.4bn' -> 3.4e9", num("$3.4bn") == 3.4e9)
check("number: '5 million' -> 5e6", num("5 million") == 5e6)
check("number: '1.2B' -> 1.2e9", num("1.2B") == 1.2e9)
check("days since: garbage -> None", core["_days_since"]("soon") is None)

import time as _t  # noqa: E402

ago400 = _t.strftime("%Y-%m-%d", _t.gmtime(_t.time() - 400 * 86400))
d400 = core["_days_since"](ago400)
check("days since: 400 days ago", d400 in (399, 400, 401), d400)
check("days since: 1970-01-01 is today's day count", core["_days_since"]("1970-01-01") == int(_t.time() // 86400))
check("days since: YYYY-MM and YYYY read", core["_days_since"]("2020-02") is not None and core["_days_since"]("2020") is not None)
check("days since: impossible date -> None", core["_days_since"]("2020-13-45") is None)

# a record every rubric input is filled for
inputs = {}
for k, spec in R["inputs"].items():
    inputs[k] = "250" if spec["type"] == "number" else ("2026-01-01" if spec["type"] == "date" else "Example value for " + k)


def fake_answers(rubric, probs_first=0.9):
    """ai_evaluate's output shape (Vercel AI SDK evaluation answers, Deepline envelope)."""
    ans = {}
    for q in rubric["questions"]:
        if q["kind"] == "noul":
            ans[q["id"]] = {"type": "boolean", "probability": probs_first}
        elif q["kind"] == "choice":
            keys = list(q["options"])
            p = dict((k, 0.0) for k in keys)
            p[keys[0]] = probs_first
            p[keys[1]] = round(1 - probs_first, 4)
            ans[q["id"]] = {"type": "choice", "choice": keys[0], "probabilities": p}
        else:
            n = len(q["levels"])
            p = dict((str(i), 0.0) for i in range(n))
            p[str(n - 1)] = 1.0
            ans[q["id"]] = {"type": "score", "score": n - 1, "probabilities": p}
    return {"status": "completed", "result": {"answers": ans, "response": {"modelId": "typesafe-ai/jev", "timestamp": "2026-09-30T00:00:00Z"}},
            "usage": {"inputTokens": 800, "outputTokens": 0, "totalTokens": 800}, "meta": {"model": "typesafe-ai/jev"}}


ix = core["intake"](core["pick"](inputs))
check("intake: asks Jev when data is present", ix["ask"] is True)
body = ix["jev_body"]
check("intake: one request carries every question", set(body["questions"]) == {q["id"] for q in R["questions"]})
check("intake: question types are ai_evaluate's (boolean/choice/score)",
      all(v["type"] in ("boolean", "choice", "score") for v in body["questions"].values()))
check("intake: every choice offers not_enough_information",
      all("not_enough_information" in v["criteria"] for v in body["questions"].values() if v["type"] == "choice"))
check("intake: state holds only fields a question reads",
      set(body["state"]) <= {k for q in R["questions"] for k in q["reads"]})
check("intake: Jev model sent", body["model"] == L.JEV["model"])

out = core["score"](ix, 200, fake_answers(R))
check("score: every output key present", all(k in out for k in L.OUTPUT_KEYS), [k for k in L.OUTPUT_KEYS if k not in out])
check("score: 0-100 integer", isinstance(out["lead_score"], int) and 0 <= out["lead_score"] <= 100)
check("score: status is one of the fixed set", out["score_status"] in L.STATUSES)
check("score: reasons name points", "(+" in out["score_reasons"])
check("score: input tokens read from usage", out["jev_input_tokens"] == 800)
check("score: model read from the response", out["jev_model"] == "typesafe-ai/jev")
check("score: answers one level down (rawV2.data) read the same",
      core["score"](ix, 200, {"data": fake_answers(R)})["lead_score"] == out["lead_score"])

# parity: the local path gives the same verdict as calling the steps one by one
local = L.score_record(R, inputs, lambda b: (200, fake_answers(R)))
check("parity: score_record == intake + score", (local["lead_score"], local["lead_tier"], local["criteria_json"]) ==
      (out["lead_score"], out["lead_tier"], out["criteria_json"]))
mapped = L.score_record(R, dict([(k, v) for k, v in inputs.items() if k != MAPPED] + [("Mapped column", inputs[MAPPED])]),
                        lambda b: (200, fake_answers(R)), mapping={MAPPED: "Mapped column"})
check("mapping baked into the play: a mapped column reads as its input", mapped["lead_score"] == out["lead_score"])

# expected points: a less sure answer moves the score less
sure = L.score_record(R, inputs, lambda b: (200, fake_answers(R, 0.95)))
unsure = L.score_record(R, inputs, lambda b: (200, fake_answers(R, 0.55)))
check("expected points: unsure answers score lower than sure ones", unsure["lead_score"] < sure["lead_score"])
check("needs_review lists low-confidence answers", unsure["needs_review"] != "none" and sure["needs_review"] == "none")

# failures: a tool error from the play arrives as (statusCode, {category, message})
for code, cat, word in ((401, "authentication", "auth"), (429, "rate_limit", "rate limit"),
                        (402, "billing", "credits"), (503, "upstream", "unavailable"), (500, "", "failed")):
    f = L.score_record(R, inputs, lambda b, c=code, k=cat: (c, {"category": k, "message": "x"}))
    check("failure %s %s: status failed, reason says so" % (code, cat), f["score_status"] == "failed" and word in f["error"], f["error"])
    check("failure %s: keys still all present" % code, all(k in f for k in L.OUTPUT_KEYS))
f = L.score_record(R, inputs, lambda b: (200, {"result": {"answers": {}}}))
check("200 with no answers is a failure, not a zero", f["score_status"] == "failed")


def never(_b):
    raise AssertionError("Jev must not be called")


# nothing to ask / required missing / rule disqualifies: no Jev call
req = [k for k, s in R["inputs"].items() if s["required"]]
if req:
    nr = dict(inputs)
    nr[req[0]] = ""
    x = L.score_record(R, nr, never)
    check("missing required input: not_scored, no Jev call", x["score_status"] == "not_scored" and x["jev_model"] == "not called")
dq_rules = [r for r in R["rules"] if r["kind"] == "match" and r["disqualify"]]
if dq_rules:
    d = dict(inputs)
    d[dq_rules[0]["input"]] = "".join(["https", "://", "www", ".", dq_rules[0]["values"][0], "/"])   # URL form, scheme and www stripped
    x = L.score_record(R, d, never)
    check("rule disqualifier: disqualified before any Jev call", x["score_status"] == "disqualified" and x["jev_model"] == "not called")
thin = dict((k, "") for k in inputs)
for k in req:
    thin[k] = "Only this"


def shrug(body):
    """Jev on a record with almost nothing in it: every choice lands on not_enough_information."""
    ans = {}
    for qid, q in body["questions"].items():
        if q["type"] == "choice":
            p = dict((k, 0.0) for k in q["criteria"])
            p["not_enough_information"] = 0.9
            ans[qid] = {"type": "choice", "choice": "not_enough_information", "probabilities": p}
        elif q["type"] == "boolean":
            ans[qid] = {"type": "boolean", "probability": 0.1}
        else:
            ans[qid] = {"type": "score", "score": 0.0}
    return 200, {"result": {"answers": ans, "response": {"modelId": "typesafe-ai/jev"}}, "usage": {"inputTokens": 300}}


x = L.score_record(R, thin, shrug)
check("thin record: insufficient_data, never a low tier", x["lead_tier"] == "insufficient_data", x["lead_tier"])
check("thin record: says what had no data", "No data for" in x["score_reasons"])

# abstaining answers do not count as coverage
abst = fake_answers(R)
for q in R["questions"]:
    if q["kind"] == "choice":
        p = dict((k, 0.0) for k in q["options"])
        p["not_enough_information"] = 0.9
        abst["result"]["answers"][q["id"]] = {"type": "choice", "choice": "not_enough_information", "probabilities": p}
a1 = L.score_record(R, inputs, lambda b: (200, fake_answers(R)))
a2 = L.score_record(R, inputs, lambda b: (200, abst))
if any(q["kind"] == "choice" for q in R["questions"]):
    check("abstained choice lowers coverage", a2["coverage_pct"] < a1["coverage_pct"])

for q in R["questions"]:
    if q["kind"] == "choice":
        ab = fake_answers(R)
        p = dict((k, 0.0) for k in q["options"])
        p["not_enough_information"] = 0.6
        p[list(q["options"])[0]] = 0.4
        ab["result"]["answers"][q["id"]] = {"type": "choice", "choice": "not_enough_information", "probabilities": p}
        x = L.score_record(R, inputs, lambda b: (200, ab))
        pts = [c["points"] for c in json.loads(x["criteria_json"]) if c["id"] == q["id"]][0]
        check("abstained choice earns no points", pts == 0, pts)
        break
x = L.score_record(R, inputs, lambda b: ("200.0", fake_answers(R)))
check("status code as '200.0' is still a 200", x["score_status"] != "failed", x["error"])
x = L.score_record(R, inputs, lambda b: (500, {"message": "x" * 5000}))
check("reasons and review stay short", len(x["score_reasons"]) <= 500 and len(x["needs_review"]) <= 500)
nodist = fake_answers(R)
for q in R["questions"]:
    if q["kind"] == "choice":
        nodist["result"]["answers"][q["id"]] = {"type": "choice", "choice": list(q["options"])[0]}
certain = json.loads(json.dumps(nodist))
for q in R["questions"]:
    if q["kind"] == "choice":
        certain["result"]["answers"][q["id"]]["probabilities"] = {list(q["options"])[0]: 1.0}
x = L.score_record(R, inputs, lambda b: (200, nodist))
y = L.score_record(R, inputs, lambda b: (200, certain))
check("a choice with no distribution counts as its chosen option, for sure", x["score_status"] == y["score_status"] != "failed" and x["lead_score"] == y["lead_score"],
      (x["score_status"], x["lead_score"], y["lead_score"]))

# a noul or choice disqualifier fires on probability
for q in R["questions"]:
    if q["kind"] == "choice" and any(o["disqualify"] for o in q["options"].values()):
        opt = next(k for k, o in q["options"].items() if o["disqualify"])
        ans = fake_answers(R)
        p = dict((k, 0.0) for k in q["options"])
        p[opt] = 0.85
        p["not_enough_information"] = 0.15
        ans["result"]["answers"][q["id"]] = {"type": "choice", "choice": opt, "probabilities": p}
        x = L.score_record(R, inputs, lambda b: (200, ans))
        check("choice disqualifier at 85%% (%s)" % opt, x["score_status"] == "disqualified")
        break

# reasons: what counted for the record, and what pulled it down
nq = [q for q in R["questions"] if q["kind"] == "noul" and q["points"]["yes"] > q["points"]["no"]]
if nq:
    q = nq[0]
    ans = fake_answers(R)
    ans["result"]["answers"][q["id"]] = {"type": "boolean", "probability": 0.08}
    x = L.score_record(R, inputs, lambda b: (200, ans))
    want = "%s: %s (%d of %d)" % (q["label"], q["says_no"] or "no", round(0.08 * q["points"]["yes"]), round(q["points"]["yes"]))
    check("a 'no' that earned points through Jev's doubt reads as a shortfall, not a win", want in x["score_reasons"],
          x["score_reasons"])
    check("... and is never shown as (+N)", "%s: %s (+" % (q["label"], q["says_no"] or "no") not in x["score_reasons"])
cq = [q for q in R["questions"] if q["kind"] == "choice"]
if cq:
    q = cq[0]
    zero = [k for k, o in q["options"].items() if o["points"] == 0 and k != "not_enough_information" and not o["disqualify"]]
    if zero:
        ans = fake_answers(R)
        p = dict((k, 0.0) for k in q["options"])
        p[zero[0]] = 0.95
        p["not_enough_information"] = 0.05
        ans["result"]["answers"][q["id"]] = {"type": "choice", "choice": zero[0], "probabilities": p}
        x = L.score_record(R, inputs, lambda b: (200, ans))
        want = "%s: %s (0 of %d)" % (q["label"], q["options"][zero[0]]["says"], round(L.item_max(q)))
        check("a zero-point answer that dragged the score down is named", want in x["score_reasons"], x["score_reasons"])

# ------------------------------------------------------------------ rubric checks

bad = [("wrong entity", dict(EXAMPLE, entity="contact" if L.ENTITY == "account" else "account")),
       ("unknown input in reads", dict(EXAMPLE, questions=[dict(EXAMPLE["questions"][0], reads=["nope"])])),
       ("tiers not reaching 0", dict(EXAMPLE, tiers=[{"tier": "A", "min": 50}])),
       ("tier named like a status", dict(EXAMPLE, tiers=[{"tier": "failed", "min": 0}])),
       ("no name", dict(EXAMPLE, name="")),
       ("score with 11 levels", dict(EXAMPLE, rules=[], questions=[{"id": "s", "kind": "score", "reads": [list(EXAMPLE["inputs"])[0]],
                                                                    "instructions": "x", "levels": list("abcdefghijk"), "points": 5}])),
       ("bands out of order", dict(EXAMPLE, questions=[], rules=[{"id": "b", "kind": "bands", "input": list(EXAMPLE["inputs"])[0],
                                                                "bands": [{"below": 50, "points": 1}, {"below": 10, "points": 2}]}])),
       ("duplicate ids", dict(EXAMPLE, rules=EXAMPLE["rules"][:1] * 2)),
       ("min_coverage as a percent", dict(EXAMPLE, min_coverage=50)),
       ("confidence_floor as a percent", dict(EXAMPLE, confidence_floor=60)),
       ("infinite points", dict(EXAMPLE, rules=[{"id": "b", "kind": "bands", "input": list(EXAMPLE["inputs"])[0],
                                                  "bands": [{"points": "inf"}]}])),
       ("source_ref as an input", dict(EXAMPLE, inputs=dict(EXAMPLE["inputs"], source_ref={"label": "x"}))),
       ("choice disqualify_at 0", dict(EXAMPLE, questions=[{"id": "c", "kind": "choice", "reads": [list(EXAMPLE["inputs"])[0]],
                                                             "instructions": "x", "options": {"a": 1, "b": 2}, "disqualify_at": 0}]))]
for name, doc in bad:
    buf = io.StringIO()
    with redirect_stdout(buf):
        refused = raises(lambda d=doc: L.validate_rubric(json.loads(json.dumps(d))))
    check("rubric check rejects: " + name, refused)
lk = json.loads(json.dumps(EXAMPLE))
first = list(lk["inputs"])[0]
lk["rules"] = [{"id": "lk", "label": "Tier", "kind": "lookup", "input": first,
                "table": {"A": {"points": 25, "says": "tier A account"}, "b": 15}, "miss_points": 0}]
LK = L.validate_rubric(lk)
lk_core = L.load_core(LK)
check("lookup rule: case-insensitive hit", lk_core["apply_rule"](dict(LK["rules"][0], _max=25), {first: "a"})["points"] == 25)
check("lookup rule: miss gets miss_points", lk_core["apply_rule"](dict(LK["rules"][0], _max=25), {first: "Z"})["points"] == 0)
check("lookup rule: max is the best value", L.item_max(LK["rules"][0]) == 25)
card = L.rubric_card(R)
check("rubric card prices the run and never says 'a account'", "per 1,000" in card and "a account" not in card)

# ------------------------------------------------------------------ mapping

cols = [{"id": "c1", "name": "Company Name"}, {"id": "c2", "name": "Description"}, {"id": "c3", "name": "Website domain"}]
m = L.propose_map({"company_name": {"label": "Company name"}, "description": {"label": "What it does"},
                   "domain": {"label": "Website domain"}, "industry": {"label": "Industry"}}, cols)
check("mapping: exact and label matches", m == {"company_name": "c1", "description": "c2", "domain": "c3", "industry": None}, m)
m3 = L.propose_map({"started_role_on": {"label": "Started current role"}, "title": {"label": "Job title"},
                    "headline": {"label": "Profile headline or summary"}},
                   [{"id": "x1", "name": "Started role"}, {"id": "x2", "name": "Job title"}, {"id": "x3", "name": "Headline"},
                    {"id": "x4", "name": "Role notes"}])
m4 = L.propose_map({"description": {"label": "What the company does"}}, [{"id": "c", "name": "Company"}])
check("mapping: one shared label word is not a match", m4 == {"description": None}, m4)
check("mapping: close names match (Started role, Headline)", m3 == {"started_role_on": "x1", "title": "x2", "headline": "x3"}, m3)
m2 = L.apply_overrides(dict(m), cols, ["industry=Description"])
check("mapping: --map override by column name", m2["industry"] == "c2")
check("mapping: unknown column stops", raises(lambda: L.apply_overrides(dict(m), cols, ["industry=Nope"])))

# ------------------------------------------------------------------ run ids, read loosely

check("run id: found in a nested object", L.find_run_id({"run": {"runId": "play/x/run/1"}}) == "play/x/run/1")
check("run id: none when absent", L.find_run_id({"ok": True}) is None)

print("")
print("%d failed" % len(FAILS) if FAILS else "all checks passed")
sys.exit(1 if FAILS else 0)
