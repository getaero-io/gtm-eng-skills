#!/usr/bin/env python3
"""OrgAtlas helper: classify leader records from Deepline people search, merge/dedupe, and render the org chart.

Subcommands
  normalize  raw leader records (from Deepline people search output) -> people.json + exclusion report
  render     people.json + company.json [+ theme.json] -> orgchart.html
  extract    pull the embedded dataset back out of a previously built orgchart.html

Everything here is deterministic. It never invents people, titles, emails, or reporting lines.
"""
import argparse, colorsys, datetime as dt, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "orgchart_template.html"  # ships beside this script in scripts/

# ---------------------------------------------------------------- classification
ALWAYS_EXCLUDE = re.compile(
    r"\b(advis[eo]rs?|consultants?|contractors?|freelancer?|interns?|assistant|associate vice president|"
    r"avp|former|retired|emerit(us|a)|chief of staff|office of the|to the|board members?|board of directors|"
    r"non[- ]executive|trustees?|observer|fellow|student)\b", re.I)
DIRECTOR = re.compile(r"\bdirectors?\b", re.I)
FULL_CHIEF = re.compile(r"\bchief\b[\w\s,&/'-]*?\bofficer\b", re.I)
ACRONYM = re.compile(r"\b(ceo|cfo|coo|cto|cio|cmo|cro|cpo|chro|clo|ciso|cso|cdo|cao|cco|cbo)\b", re.I)
PRESIDENT = re.compile(r"(?<!vice )(?<!vice-)\bpresident\b", re.I)
VP = re.compile(
    r"\b(executive vice[- ]president|senior vice[- ]president|group vice[- ]president|vice[- ]president|"
    r"evp|svp|gvp|sr\.? vp|global vp|vp)\b", re.I)
HEAD_OF = re.compile(r"\bhead of\b", re.I)
# Customer-facing or deputy "CTO"-style titles that are not the company's C-Suite seat
NOT_CSUITE = re.compile(r"\b(field|forward[- ]deployed|deputy|regional|divisional|associate|assistant)\b", re.I)

FUNCTIONS = [  # checked in order; first match wins (CEO checked before this list)
    ("Revenue", r"\b(cro|chief revenue|revenue|go[- ]to[- ]market|gtm|commercial)\b"),
    ("Sales", r"\b(sales|business development|partnerships?|alliances|channels?|account management)\b"),
    ("Marketing", r"\b(cmo|marketing|brand|communications|comms|public relations|growth|demand)\b"),
    ("Finance", r"\b(cfo|finance|financial|accounting|controller|treasury|tax|investor relations|fp&a)\b"),
    ("Product", r"\b(product|products|design|ux)\b"),
    ("Engineering", r"\b(cto|cio|ciso|engineering|technology|technical|infrastructure|platform|data|security|it|"
                    r"information|software|ai|machine learning|research|r&d)\b"),
    ("People", r"\b(chro|people|hr|human resources|talent|recruiting|culture|workplace)\b"),
    ("Legal", r"\b(clo|legal|counsel|compliance|privacy|regulatory)\b"),
    ("Operations", r"\b(coo|operations|operating|supply chain|procurement|facilities|logistics|manufacturing)\b"),
    ("Strategy", r"\b(strategy|strategic|corporate development|corp dev|transformation)\b"),
    ("Customer", r"\b(customers?|clients?|success|support|experience|services)\b"),
]
FUNCTIONS = [(n, re.compile(p, re.I)) for n, p in FUNCTIONS]
EXEC = re.compile(r"\b(ceo|chief executive)\b", re.I)
EXEC_FALLBACK = re.compile(r"(?<!vice )(?<!vice-)\b(president|chair(man|woman|person)?|founder|co-?founder)\b", re.I)


def classify_level(title, seniority=None):
    """Return ("C-Suite"|"VP", None) or (None, exclusion_reason)."""
    t = title or ""
    if not t.strip():
        return None, "No current title"
    if ALWAYS_EXCLUDE.search(t):
        return None, "Advisor / board / assistant / consultant / former"
    has_vp = bool(VP.search(t))
    c_level = FULL_CHIEF.search(t) or (ACRONYM.search(t) and not has_vp) or (PRESIDENT.search(t) and not has_vp)
    if c_level and not NOT_CSUITE.search(t):
        return "C-Suite", None
    if c_level:
        return None, "Field / deputy C-title (not the C-Suite seat)"
    if has_vp:
        return "VP", None
    if HEAD_OF.search(t) and seniority and VP.search(str(seniority)):
        return "VP", None
    if DIRECTOR.search(t):
        return None, "Director or below"
    if HEAD_OF.search(t):
        return None, "Head of (no VP seniority from Deepline)"
    return None, "Not C-Suite or VP"


def classify_function(title):
    t = title or ""
    if EXEC.search(t):
        return "Executive"
    for name, rx in FUNCTIONS:
        if rx.search(t):
            return name
    if EXEC_FALLBACK.search(t):
        return "Executive"
    return "Other"


def rank(p):
    t = p["title"].lower()
    if p["level"] == "C-Suite":
        if EXEC.search(t):
            return 0
        if PRESIDENT.search(t) and not FULL_CHIEF.search(t):
            return 1
        return 2
    if re.search(r"executive vice|\bevp\b", t):
        return 3
    if re.search(r"senior vice|\bsvp\b|sr\.? vp", t):
        return 4
    return 5


# ---------------------------------------------------------------- reporting-line inference
# Deepline's search does not return manager relationships. These are INFERRED from titles and
# functions only, always labeled as inferred, and never presented as Deepline data.
SUB_EXEC = [  # (title pattern, ordered parent patterns among the C-Suite)
    (re.compile(r"accounting|\bcao\b", re.I), [r"financial officer|\bcfo\b"]),
    (re.compile(r"security|\bciso\b|\bcso\b", re.I), [r"information officer|\bcio\b", r"technology officer|\bcto\b"]),
]
HEAD_PREF = {  # which C-level title leads a function when several share it
    "Engineering": [r"technology|\bcto\b", r"information officer|\bcio\b"],
    "Finance": [r"financial|\bcfo\b"],
    "People": [r"people|human|\bchro\b"],
}


def tier(p):
    return rank(p)  # 0 CEO, 1 President, 2 other chiefs, 3 EVP, 4 SVP, 5 VP


def infer_reporting(people):
    """Set p['reportsTo'] = {'id','basis','confidence'} or None for the top of the chart."""
    ordered = sorted(people, key=rank)
    root = next((p for p in ordered if p["level"] == "C-Suite" and EXEC.search(p["title"])), None) \
        or next((p for p in ordered if p["level"] == "C-Suite" and PRESIDENT.search(p["title"])), None)
    csuite = [p for p in ordered if p["level"] == "C-Suite" and p is not root]

    def is_sub(p):
        return any(rx.search(p["title"]) for rx, _ in SUB_EXEC)

    def head_for(fn):
        cands = [c for c in csuite if c["function"] == fn and not is_sub(c)]
        for pat in HEAD_PREF.get(fn, []):
            hit = next((c for c in cands if re.search(pat, c["title"], re.I)), None)
            if hit:
                return hit
        return cands[0] if cands else None

    def unplaced(why):  # no evidence for a manager: the page shows these in "Needs review", not under the CEO
        return {"id": None, "basis": why, "confidence": "unplaced"}

    for p in ordered:
        if p is root:
            p["reportsTo"] = None
            continue
        rel = None
        if p["level"] == "C-Suite":
            for rx, parents in SUB_EXEC:
                if rx.search(p["title"]):
                    for pat in parents:
                        mgr = next((c for c in csuite if c is not p and re.search(pat, c["title"], re.I)), None)
                        if mgr:
                            rel = {"id": mgr["id"], "basis": f"{p['title']} usually reports to the {mgr['title']}",
                                   "confidence": "medium"}
                            break
                    break
            if not rel and root:
                rel = {"id": root["id"], "basis": f"C-Suite executives usually report to the {root['title']}",
                       "confidence": "medium"}
            if not rel:
                rel = unplaced("No CEO or President in this dataset")
        else:
            if p["function"] not in ("Other", "Executive"):
                senior = [v for v in ordered if v["level"] == "VP" and v is not p
                          and v["function"] == p["function"] and tier(v) < tier(p)]
                if senior:
                    mgr = max(senior, key=tier)  # closest more-senior tier
                    rel = {"id": mgr["id"], "basis": f"Same function ({p['function']}), more senior VP title",
                           "confidence": "medium"}
                else:
                    head = head_for(p["function"])
                    if head:
                        rel = {"id": head["id"], "basis": f"Same function ({p['function']}) as the {head['title']}",
                               "confidence": "medium"}
            if not rel and root and tier(p) == 3:
                rel = {"id": root["id"], "basis": f"EVPs usually report to the {root['title']}, but no same-function leader was found",
                       "confidence": "low"}
            if not rel:
                rel = unplaced("No same-function leader was found in this dataset")
        p["reportsTo"] = rel
    return people


# ---------------------------------------------------------------- identity / dedupe
def norm_linkedin(url):
    if not url:
        return None
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^([a-z]{2,3}\.)?www\.|^[a-z]{2}\.", "", u)
    u = u.split("?")[0].split("#")[0].rstrip("/")
    return u or None


def norm_name(n):
    return re.sub(r"[^a-z0-9]+", " ", (n or "").lower()).strip()


def keys_for(p, domain):
    ks = []
    if p.get("personId"):
        ks.append("pid:" + str(p["personId"]))
    li = norm_linkedin(p.get("linkedinUrl"))
    if li:
        ks.append("li:" + li)
    if p.get("name"):
        ks.append("nm:" + norm_name(p["name"]) + "@" + (domain or "").lower())
    return ks


def primary_id(p, domain):
    return keys_for(p, domain)[0]


# ---------------------------------------------------------------- normalize
CARRY = ("personId", "location", "linkedinUrl", "email", "phone", "roleStartDate")
START_RE = re.compile(r"^(\d{4})-(\d{2})(?:-\d{2})?(?:[T ].*)?$")


def clean_start(v):
    """The current role's start date (crustdata `...current.start_date`), kept only as YYYY-MM."""
    m = START_RE.match(str(v or "").strip())
    return f"{m.group(1)}-{m.group(2)}" if m and 1 <= int(m.group(2)) <= 12 else None


def normalize(args):
    raw = json.loads(Path(args.raw).read_text())
    if isinstance(raw, dict):
        raw = raw.get("people") or raw.get("results") or []
    company = json.loads(Path(args.company).read_text())
    domain = company.get("domain")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    existing = []
    if args.existing and Path(args.existing).exists():
        existing = json.loads(Path(args.existing).read_text())
    seen = {}
    for p in existing:
        for k in keys_for(p, domain):
            seen[k] = p

    excluded, dupes, fresh = {}, 0, []
    for r in raw:
        name = (r.get("name") or "").strip()
        title = (r.get("title") or "").strip()
        if not name:
            excluded["Missing name"] = excluded.get("Missing name", 0) + 1
            continue
        if r.get("isCurrent") is False:
            excluded["Former employee"] = excluded.get("Former employee", 0) + 1
            continue
        level, why = classify_level(title, r.get("seniority"))
        if not level:
            excluded[why] = excluded.get(why, 0) + 1
            continue
        if r.get("roleStartDate"):
            r = dict(r, roleStartDate=clean_start(r["roleStartDate"]))
        person = {
            "name": name,
            "title": title,
            "level": level,
            "function": classify_function(title),
            "companyName": company.get("name"),
            "currentEmploymentVerified": r.get("isCurrent") is True,
            "buyingRole": "Unclassified",
            "source": "Demo" if args.demo else "Deepline",
            "retrievedAt": r.get("retrievedAt") or now,
        }
        for f in CARRY:
            if r.get(f):
                person[f] = r[f]
        if domain:
            person["companyDomain"] = domain
        ks = keys_for(person, domain)
        hit = next((seen[k] for k in ks if k in seen), None)
        if hit:
            dupes += 1
            for f in CARRY:  # fill gaps only
                if f in person and not hit.get(f):
                    hit[f] = person[f]
            for k in keys_for(hit, domain):
                seen[k] = hit
            continue
        person["id"] = ks[0]
        for k in ks:
            seen[k] = person
        fresh.append(person)

    fresh.sort(key=rank)
    cap = args.limit if args.limit is not None else len(fresh)
    added, overflow = fresh[:cap], fresh[cap:]
    people = existing + added
    people.sort(key=rank)
    infer_reporting(people)
    Path(args.out).write_text(json.dumps(people, indent=2))
    report = {
        "rawRecords": len(raw),
        "added": len(added),
        "total": len(people),
        "cSuite": sum(p["level"] == "C-Suite" for p in people),
        "vp": sum(p["level"] == "VP" for p in people),
        "duplicatesMerged": dupes,
        "qualifiedButOverCap": len(overflow),
        "inferredLines": {c: sum(1 for p in people if (p.get("reportsTo") or {}).get("confidence") == c)
                          for c in ("medium", "low", "unplaced")},
        "excluded": excluded,
    }
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------- theme
def _hex(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)


def _lum(rgb):
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((_lum(_hex(a)), _lum(_hex(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    A, B = _hex(a), _hex(b)
    return _to_hex(tuple(x + (y - x) * t for x, y in zip(A, B)))


def usable_primary(primary, surface, target=4.5):
    """Darken (light surface) or lighten (dark surface) until text/UI contrast is met."""
    toward = "#000000" if _lum(_hex(surface)) > 0.5 else "#ffffff"
    c, t = primary, 0.0
    while contrast(c, surface) < target and t < 1:
        t += 0.05
        c = mix(primary, toward, t)
    return c


DEFAULT_THEME = {
    "brandName": None,
    "primary": "#5B3FD9",
    "fontHeading": "Inter",
    "fontBody": "Inter",
    "googleFontsUrl": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    "logoDataUri": None,
    "source": "OrgAtlas default",
}


def theme_css(theme):
    light_bg, dark_bg = "#FAF9F7", "#15141A"
    p = theme["primary"]
    p_light = usable_primary(p, "#FFFFFF")
    p_dark = usable_primary(p, "#1F1E26")
    on_p = "#FFFFFF" if contrast("#FFFFFF", p_light) >= contrast("#111111", p_light) else "#111111"
    on_pd = "#FFFFFF" if contrast("#FFFFFF", p_dark) >= contrast("#111111", p_dark) else "#111111"
    fh = theme.get("fontHeading") or "Inter"
    fb = theme.get("fontBody") or "Inter"
    stack = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    light = f"""
  --bg:{light_bg}; --surface:#FFFFFF; --surface-2:#F3F2EF; --line:#E4E2DD; --conn:#BDB8AF; --text:#1B1A18; --muted:#5F5C57;
  --primary:{p_light}; --on-primary:{on_p}; --primary-soft:{mix(p_light, '#FFFFFF', 0.88)}; --primary-line:{mix(p_light, '#FFFFFF', 0.6)};
  --ok:#1E7A46; --ok-soft:#E3F4EA; --warn:#8A5A00; --warn-soft:#FFF4DB; --danger:#B42318; --danger-soft:#FDECEA;
  --shadow:0 1px 2px rgba(20,20,30,.06), 0 4px 14px rgba(20,20,30,.06);
  --r-champion:#1E7A46; --r-buyer:#6D3FD1; --r-influencer:#0B6BB8; --r-blocker:#B42318;
  --g1:#0B6BB8; --g2:#6D3FD1; --g3:#C2410C; --g4:#0F7B6C; --g5:#9A6700; --g6:#B4235F; --g7:#6B6F76;
  --new:#C2410C; --new-2:#EA580C; --on-new:#FFFFFF; --new-soft:#FFEDD5;"""
    dark = f"""
  --bg:{dark_bg}; --surface:#1F1E26; --surface-2:#282733; --line:#373645; --conn:#5A586A; --text:#F2F1F6; --muted:#A9A7B6;
  --primary:{p_dark}; --on-primary:{on_pd}; --primary-soft:{mix(p_dark, '#1F1E26', 0.8)}; --primary-line:{mix(p_dark, '#1F1E26', 0.45)};
  --ok:#6FD39A; --ok-soft:#1C3527; --warn:#F2C46B; --warn-soft:#3A2F16; --danger:#FF8A80; --danger-soft:#3D1F1D;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.35); color-scheme:dark;
  --r-champion:#6FD39A; --r-buyer:#B69CFF; --r-influencer:#7CC2FF; --r-blocker:#FF8A80;
  --g1:#7CC2FF; --g2:#B69CFF; --g3:#FFA36B; --g4:#5FD4C0; --g5:#F2C46B; --g6:#FF8FC0; --g7:#A9A7B6;
  --new:#FB923C; --new-2:#FDBA74; --on-new:#1C1006; --new-soft:#3B2211;"""
    fonts = f"--font-heading:'{fh}', {stack}; --font-body:'{fb}', {stack};"
    return (f":root{{{light} {fonts}}}\n"
            f"@media (prefers-color-scheme: dark){{:root:not([data-theme=\"light\"]){{{dark}}}}}\n"
            f":root[data-theme=\"dark\"]{{{dark}}}")


# ---------------------------------------------------------------- news
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def clean_news(raw, people):
    """Keep only well-formed items that link to a real article and name someone on the chart."""
    ids = {p["id"] for p in people}
    items, dropped = [], 0
    for it in raw.get("items", []):
        url = str(it.get("url") or "")
        who = [i for i in it.get("people", []) if i in ids]
        if not (DATE_RE.match(str(it.get("date") or "")) and url.startswith("https://") and it.get("title") and who):
            dropped += 1
            continue
        also = [a for a in it.get("alsoAt", []) if str(a.get("url", "")).startswith("https://") and a.get("source")]
        items.append({"date": it["date"], "title": str(it["title"]), "url": url, "source": str(it.get("source") or ""),
                      "kind": str(it.get("kind") or "News"), "summary": str(it.get("summary") or ""),
                      "people": who, "alsoAt": also})
    items.sort(key=lambda x: x["date"], reverse=True)
    return {"checkedAt": raw.get("checkedAt"), "windowMonths": raw.get("windowMonths", 3), "items": items}, dropped


# ---------------------------------------------------------------- render
def render(args):
    people = json.loads(Path(args.people).read_text())
    company = json.loads(Path(args.company).read_text())
    theme = dict(DEFAULT_THEME)
    if args.theme and Path(args.theme).exists():
        theme.update({k: v for k, v in json.loads(Path(args.theme).read_text()).items() if v})
    retrieved = max((p["retrievedAt"] for p in people), default=None)
    payload = {
        "company": company,
        "people": people,
        "retrievedAt": retrieved,
        "theme": {k: theme.get(k) for k in ("brandName", "primary", "fontHeading", "fontBody",
                                             "googleFontsUrl", "logoDataUri", "source")},
        "builtAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        # the Deepline plays the page's "Find email / mobile" commands name (never credentials)
        "enrich": {},
    }
    if args.enrich and Path(args.enrich).exists():
        payload["enrich"].update(json.loads(Path(args.enrich).read_text()))
    if args.news and Path(args.news).exists():
        payload["news"], dropped = clean_news(json.loads(Path(args.news).read_text()), people)
        if dropped:
            print(f"Dropped {dropped} news item(s): missing date/https link/title, or no one on the chart named")
    data = json.dumps(payload).replace("</", "<\\/")
    font_link = ""
    if theme.get("googleFontsUrl", "").startswith("https://fonts.googleapis.com/"):
        font_link = (f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
                     f'<link rel="stylesheet" href="{theme["googleFontsUrl"]}">')
    title = f"{company.get('name', 'Account')} Org Chart"
    html = (TEMPLATE.read_text()
            .replace("__TITLE__", title.replace("<", ""))
            .replace("__FONT_LINK__", font_link)
            .replace("/*__THEME_CSS__*/", theme_css(theme))
            .replace("__DATA_JSON__", data))
    if args.full_document:
        html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                + html.replace("<!--BODY-->", "</head><body>", 1) + "</body></html>")
    else:
        html = html.replace("<!--BODY-->", "", 1)
    Path(args.out).write_text(html)
    print(f"Wrote {args.out} ({len(people)} people)")


def extract(args):
    html = Path(args.html).read_text()
    m = re.search(r'<script type="application/json" id="orgatlas-data">(.*?)</script>', html, re.S)
    if not m:
        sys.exit("No OrgAtlas dataset found in that file.")
    payload = json.loads(m.group(1).replace("<\\/", "</"))
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "people.json").write_text(json.dumps(payload["people"], indent=2))
    (out / "company.json").write_text(json.dumps(payload["company"], indent=2))
    (out / "theme.json").write_text(json.dumps(payload.get("theme") or {}, indent=2))
    print(f"Extracted {len(payload['people'])} people for {payload['company'].get('name')} into {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("normalize")
    n.add_argument("--raw", required=True)
    n.add_argument("--company", required=True)
    n.add_argument("--out", required=True)
    n.add_argument("--existing")
    n.add_argument("--limit", type=int)
    n.add_argument("--demo", action="store_true")
    r = sub.add_parser("render")
    r.add_argument("--people", required=True)
    r.add_argument("--company", required=True)
    r.add_argument("--theme")
    r.add_argument("--enrich")
    r.add_argument("--news")
    r.add_argument("--out", required=True)
    r.add_argument("--full-document", action="store_true")
    e = sub.add_parser("extract")
    e.add_argument("--html", required=True)
    e.add_argument("--outdir", required=True)
    a = ap.parse_args()
    {"normalize": normalize, "render": render, "extract": extract}[a.cmd](a)


if __name__ == "__main__":
    main()
