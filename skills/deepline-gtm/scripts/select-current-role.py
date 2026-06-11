#!/usr/bin/env python3
"""
Select a person's CURRENT primary WORK role from a LinkedIn scrape.

Why this exists: the top-level `jobTitle` from LinkedIn scrapers is often a stale
or secondary entry (an old job, or a concurrent board seat). The reliable current
role is the most-recently-started ACTIVE work experience, with board/advisory/
charity/retired excluded when a real operating role also exists, and the
company-name-in-title scrape artifact repaired.

Usage:
    # From a CSV whose `li_scrape` column holds the raw scraper JSON
    python3 select-current-role.py enriched.csv --scrape-col li_scrape \
        --out-title current_title --out-company current_company --out-start job_start

    # Eval against fixtures
    python3 select-current-role.py --fixtures fixtures_current_role.json
"""
import argparse
import csv
import json
import re
import sys

NONWORK_RE = re.compile(
    r"\b(board\s+member|member\s+board\s+of\s+directors?|board\s+of\s+directors?|"
    r"of\s+the\s+board|chair(?:man|person)?\s+of\s+the\s+board|advisor|advisory|"
    r"trustee|volunteer|mentor|charit|foundation|non-?profit|self-?employed|"
    r"council\s+member|committee\s+member|emeritus|retired|ambassador)\b",
    re.I,
)
NONPROFIT_ORG_RE = re.compile(
    r"\b(foundation|charit|trees\s+for|habitat|rotary|united\s+way|church|ministr|non-?profit)\b",
    re.I,
)
# A LinkedIn headline is usually "<Role> @ <Company>" / "<Role> at <Company>" /
# "<Role> | <Company>" / "<Role> - <Company>", sometimes with the company on a second
# line. The role is the leading segment before the first company separator/newline.
# This is role-AGNOSTIC on purpose: it recovers a CFO, a VP Engineering, a Head of
# Sales, an Office Manager, whatever the headline leads with.
HEADLINE_SPLIT_RE = re.compile(
    r"\s*(?:@|\bat\b|\||\u00b7|\u2014|\u2013|\n|\r|\s-\s)\s*",
    re.I,
)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _truthy(v):
    """Coerce a possibly-stringified boolean. Scrapers serialize jobStillWorking
    as a real bool, or as the STRING "false"/"true"/"0"/"1"/"no"/"yes". Python's
    bool("false") is True, so a naive cast marks a long-ended role as current and
    it can beat the real current role. Normalize before trusting it."""
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y", "t")
    return bool(v)


def is_nonwork(title, company, target_role=None):
    title_norm = _norm(title)
    target_norm = _norm(target_role)
    target_is_advisor_role = "advisor" in target_norm or "advisory" in target_norm
    if target_is_advisor_role and title_norm and (target_norm in title_norm or title_norm in target_norm):
        # "Security Advisor" is a real target role when the campaign asks for
        # security advisors. Generic "Advisor" still counts as non-work when no
        # target-role context is supplied, and "Engineering Advisor" still loses
        # to "VP Engineering" for an engineering campaign.
        return bool(NONPROFIT_ORG_RE.search(company or ""))
    blob = f"{title or ''} {company or ''}"
    return bool(NONWORK_RE.search(blob)) or bool(NONPROFIT_ORG_RE.search(company or ""))


def _start_key(e):
    """Parse 'MM-YYYY' / 'YYYY-MM' / 'YYYY' -> sortable int. Missing -> 0."""
    s = str(e.get("start") or e.get("jobStartedOn") or "")
    m = re.match(r"(\d{1,2})-(\d{4})$", s)
    if m:
        return int(m.group(2)) * 100 + int(m.group(1))
    m = re.match(r"(\d{4})-(\d{2})", s)
    if m:
        return int(m.group(1)) * 100 + int(m.group(2))
    m = re.search(r"(\d{4})", s)
    return int(m.group(1)) * 100 if m else 0


def _experiences(profile):
    """Normalize the experiences array from either scraper shape."""
    out = []
    if not isinstance(profile, dict):
        return out
    raw = profile.get("experiences") or profile.get("experience") or []
    if not isinstance(raw, list):
        return out
    for e in raw:
        if not isinstance(e, dict):
            continue
        title = (e.get("title") or e.get("position") or "").strip()
        company = (e.get("companyName") or e.get("company") or "").strip()
        sd = e.get("jobStartedOn") or e.get("startDate")
        start = sd.get("text") if isinstance(sd, dict) else (sd or "")
        end = e.get("jobEndedOn") or e.get("endDate") or ""
        current = _truthy(e.get("jobStillWorking")) if "jobStillWorking" in e else not end
        out.append({"title": title, "company": company, "start": start,
                    "start_key": _start_key({"start": start}), "end": end, "current": current})
    return out


def _role_from_headline(headline, company, target_role=None):
    """Recover a role title from a 'Role @ Company' headline, role-agnostically.
    If target_role is given (the campaign's target function, e.g. 'engineering',
    'sales', 'finance'), prefer a headline segment containing it; otherwise take the
    leading segment that isn't the company name."""
    headline = (headline or "").strip()
    if not headline:
        return None
    segs = [s.strip(" .,-|·").strip() for s in HEADLINE_SPLIT_RE.split(headline) if s.strip()]
    # Drop any segment that IS the company or is contained in it (or contains it):
    # "Engineering Works" vs company "Engineering Works LLC" is the company, not a role.
    cn = _norm(company)
    def _is_company(s):
        ns = _norm(s)
        return bool(ns) and bool(cn) and (ns == cn or ns in cn or cn in ns)
    segs = [s for s in segs if s and not _is_company(s)]
    if not segs:
        return None
    # Trim each segment's trailing non-work appositive ("CFO, Board Member" -> "CFO")
    # BEFORE deciding if the segment is itself a non-work seat. Otherwise a real role
    # with a board suffix gets wrongly discarded and we fall through to junk like a
    # "(Nasdaq: TICKER)" line. Drop segments that are *purely* non-work or empty.
    trimmed = [(_trim_role(s), s) for s in segs]
    work = [t for (t, _orig) in trimmed if t and not is_nonwork(t, "", target_role)]
    if target_role:
        # Prefer a work segment that mentions the target role; never return a
        # board/advisory/charity segment just because it contains the role word
        # ("Engineering Advisor" must lose to "VP Engineering").
        for t in work:
            if re.search(re.escape(target_role), t, re.I):
                return t
    if work:
        return work[0]
    # Nothing reads as a work role: fall back to the first trimmed segment, or None.
    return next((t for (t, _o) in trimmed if t), None)


def _trim_role(seg):
    """Drop a trailing comma-appositive when it's a non-work secondary role.
    'SVP & Chief Financial Officer (CFO), Board Member' -> 'SVP & Chief Financial Officer (CFO)'.
    Leaves real compound titles ('VP Finance, Treasury') intact."""
    parts = [p.strip() for p in seg.split(",")]
    while len(parts) > 1 and is_nonwork(parts[-1], ""):
        parts.pop()
    return ", ".join(parts).strip()


def select_current_role(profile, target_role=None):
    """Return dict: {title, company, start, role_kind}. role_kind in
    work_current / nonwork_only_current / work_recent_no_current / nonwork_recent / none.
    target_role (optional): the campaign's target function, used only to disambiguate
    a company-name-in-title repair from a multi-role headline. Role-agnostic without it."""
    if not isinstance(profile, dict):
        # Malformed/None/non-dict input (a stray null cell, a list, a string) must not
        # crash a 10k-row run. Return an empty role rather than raising.
        return {"title": "", "company": "", "start": "", "role_kind": "none"}
    exps = _experiences(profile)
    current = [e for e in exps if e["current"]]
    cur_work = [e for e in current if not is_nonwork(e["title"], e["company"], target_role)]

    chosen, kind = None, "none"
    if cur_work:
        chosen, kind = max(cur_work, key=lambda e: e["start_key"]), "work_current"
    elif current:
        chosen, kind = max(current, key=lambda e: e["start_key"]), "nonwork_only_current"
    else:
        work = [e for e in exps if not is_nonwork(e["title"], e["company"], target_role)]
        if work:
            chosen, kind = max(work, key=lambda e: e["start_key"]), "work_recent_no_current"
        elif exps:
            chosen, kind = max(exps, key=lambda e: e["start_key"]), "nonwork_recent"

    if not chosen:
        # last resort: top-level fields
        t = (profile.get("jobTitle") or "").strip()
        c = (profile.get("companyName") or "").strip()
        return {"title": t, "company": c, "start": profile.get("jobStartedOn", ""), "role_kind": "none" if not t else "toplevel_only"}

    title, company, start = chosen["title"], chosen["company"], chosen["start"]

    # Repair company-name-in-title artifact. The whole discipline distrusts the
    # top-level `jobTitle` (it's often a stale/secondary entry), so prefer the
    # HEADLINE first (the person's own current-role summary) and fall back to the
    # top-level title only when the headline yields nothing usable. Doing it the
    # other way round returns a decade-old "Software Engineer" over a current
    # "VP Engineering" that the headline plainly states.
    if title and company and _norm(title) == _norm(company):
        recovered = _role_from_headline(profile.get("headline"), company, target_role)
        if recovered and _norm(recovered) != _norm(company):
            title = recovered
        else:
            top = (profile.get("jobTitle") or "").strip()
            if top and not is_nonwork(top, company, target_role) and _norm(top) != _norm(company):
                title = top

    return {"title": title, "company": company, "start": start, "role_kind": kind}


def _load_scrape(cell):
    """Unwrap a CSV cell that may be a {"result":{"data":[...]}} envelope or raw JSON."""
    try:
        j = json.loads(cell)
    except Exception:
        return None
    res = j.get("result", j) if isinstance(j, dict) else j
    data = res.get("data") if isinstance(res, dict) else None
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        return data
    return res if isinstance(res, dict) and ("experiences" in res or "experience" in res or "jobTitle" in res) else None


def run_fixtures(path):
    cases = json.load(open(path))
    passed = failed = 0
    for c in cases:
        got = select_current_role(c["profile"], c.get("target_role"))
        exp = c["expected"]
        ok = (_norm(got["title"]) == _norm(exp.get("title", "")) and
              (not exp.get("company") or _norm(got["company"]) == _norm(exp["company"])))
        if exp.get("role_kind"):
            ok = ok and got["role_kind"] == exp["role_kind"]
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  {status} [{c.get('name','?')}] expected {exp} got {got}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--scrape-col", default="li_scrape")
    ap.add_argument("--out-title", default="current_title")
    ap.add_argument("--out-company", default="current_company")
    ap.add_argument("--out-start", default="job_start")
    ap.add_argument("--out-kind", default="role_kind")
    ap.add_argument("--target-role", default=None,
                    help="optional campaign target function (e.g. 'engineering', 'sales', "
                         "'finance') to disambiguate a multi-role headline during title repair")
    ap.add_argument("--fixtures")
    a = ap.parse_args()
    if a.fixtures:
        run_fixtures(a.fixtures)
        return
    csv.field_size_limit(10 ** 7)
    rows = list(csv.DictReader(open(a.csv)))
    fields = list(rows[0].keys()) if rows else []
    for col in (a.out_title, a.out_company, a.out_start, a.out_kind):
        if col not in fields:
            fields.append(col)
    for r in rows:
        prof = _load_scrape(r.get(a.scrape_col, ""))
        res = select_current_role(prof, a.target_role) if prof else {"title": "", "company": "", "start": "", "role_kind": "none"}
        r[a.out_title], r[a.out_company], r[a.out_start], r[a.out_kind] = (
            res["title"], res["company"], res["start"], res["role_kind"])
    w = csv.DictWriter(sys.stdout, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)


if __name__ == "__main__":
    main()
