"""
Shared helpers for the "Person Active At Company (Jev)" skill: the code that runs inside the
Deepline play, where state lives, and how the Deepline CLI is driven.

Rules this file keeps:

  * Jev judges, code decides. A LinkedIn work history is a LIST of roles, and Jev's own
    documentation says it does not count or compare dates reliably and does best with one
    literal question per item. So code finds the roles that could be at the company, works out
    every date, and asks Jev small questions about ONE role each: is this the same company, what
    kind of role is it, is it still held, is it the main job. Code combines the answers into one
    verdict from a fixed set.
  * The verdict code is ONE source (CORE below, plain JavaScript). The generated play embeds it,
    and the local preview runs the very same rendered text under `node`, so a preview verdict is
    the verdict the play returns for the same profile and the same Jev answers.
  * Jev is reached through Deepline's `ai_evaluate` tool (model `typesafe-ai/jev`), billed to the
    Deepline workspace. A profile is bought with `crustdata_v3_person_enrich`. There is no key.
  * State lives at a path this library COMPUTES from the Deepline workspace, never one an agent
    composes per run.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SKILL = "check-employment-with-jev"
PLAY_NAME = "person-active-at-company-jev"
WORKFLOW_NAME = "Person Active At Company (Jev)"

# Jev through Deepline. The gateway lists only the unversioned "typesafe-ai/jev" (checked
# 2026-09-30), so the version cannot be pinned on this route; every verdict records the model id
# that answered. The 0.6 / 0.4 thresholds were tuned on jev-1.13.0.
JEV = {"tool": "ai_evaluate", "model": "typesafe-ai/jev", "list_price_per_mtok": 0.042}
ENRICH_TOOL = "crustdata_v3_person_enrich"   # LinkedIn URL in, profile with work history out; priced per match

# The play's interface. Inputs arrive as flat fields; every output key is always present.
INPUT_KEYS = ("company_name", "company_domain", "company_linkedin_url", "profile", "linkedin_url",
              "full_name", "skip_enrichment", "max_profile_age_days", "source_ref")
OUTPUT_KEYS = ("active_at_company", "relationship", "verdict_confidence", "check_status", "check_note", "company_checked", "evidence",
               "needs_review", "role_title", "role_company", "role_started", "role_ended",
               "months_in_role", "other_current_roles", "main_employer", "profile_source",
               "profile_age_days", "roles_json", "jev_model", "jev_input_tokens", "error", "source_ref",
               "checked_at")
ACTIVE_VALUES = ("yes", "passive", "no", "unsure", "not_checked")
RELATIONSHIPS = ("primary_job", "side_job", "advisor_or_board", "investor", "honorary", "former",
                 "no_record", "unknown")
CHECK_STATUSES = ("checked", "no_profile", "blocked_missing_input", "failed")


# ---------------------------------------------------------------- output

def say(msg):
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
        return {"error": (r.stderr or out)[:600], "exit": r.returncode, "data": data}
    fail("deepline %s failed (exit %s): %s" % (" ".join(args[:3]), r.returncode, (r.stderr or out)[:600]))


def workspace():
    who = deepline("auth", "status")
    ws = who.get("workspace") or {}
    if not ws.get("id"):
        fail("`deepline auth status` did not return a workspace. Run `deepline auth register --wait auto`, then re-run.")
    return {"id": str(ws["id"]), "name": ws.get("name")}


def find_run_id(obj):
    """The run id in whatever JSON `plays run` or --run-id-file wrote. Read loosely: the field
    names were not observed live for this skill."""
    if isinstance(obj, dict):
        for k in ("runId", "run_id", "workflowId", "id"):
            if isinstance(obj.get(k), str) and obj[k]:
                return obj[k]
        vals = list(obj.values())
    elif isinstance(obj, list):
        vals = obj
    else:
        return None
    for v in vals:
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


# ======================================================================= the code that runs in the play
# One source, plain JavaScript. The play embeds it; the local preview and the offline tests run
# the identical text under `node`.

CORE = r'''
const JEV = __JEV__;
const MAX_ROLES = 6;            // roles at (or possibly at) the company that get questions
const MAX_CONTEXT = 5;          // other current roles shown to Jev as context
const FLOOR = 0.6;              // an answer less sure than this is listed in needs_review
// The clock: set once per run from a checkpointed ctx.step in the play (the wall clock is
// not replay-safe there), and from the local clock in the preview.
let NOW_MS = 0;
const LEGAL = new Set(["inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "co", "company",
  "gmbh", "ag", "sa", "sas", "sarl", "srl", "spa", "bv", "nv", "plc", "lp", "llp", "pty",
  "pvt", "oy", "ab", "as", "kk", "the", "group", "holdings", "holding", "and"]);
const MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
  "october", "november", "december"];
const TWO_PART = new Set(["co", "com", "org", "net", "ac", "gov", "edu", "ne", "or"]);

const KIND_OPTIONS = {
  employee: "Works for this company as an employee or executive: a job title such as engineer, " +
    "manager, director, head of, vice president, partner, or chief officer. Includes " +
    "founders, co-founders and owners who run the company.",
  contractor: "Works for this company as a contractor, consultant, freelancer, fractional or " +
    "interim executive, or through an agency, rather than as an employee.",
  intern: "An intern, apprentice, trainee or working student at this company.",
  advisor_or_board: "An advisor, board member, board observer, mentor or committee member of " +
    "this company, without working in it day to day.",
  investor: "An investor in this company: angel, backer, shareholder or limited partner. A " +
    "partner or principal EMPLOYED by an investment firm is an employee of that firm.",
  honorary: "A volunteer, ambassador, community member, alumnus, fellow, emeritus, or an " +
    "honorary or ceremonial title at this company.",
  not_enough_information: "The title and description do not say what the role is."};
const WORKING = ["employee", "contractor", "intern"];
const PASSIVE = ["advisor_or_board", "investor", "honorary"];

// ---------------------------------------------------------------- small readers

function _s(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v).trim();
}

function _r2(x) { return Math.round(x * 100) / 100; }

function _has(v) {
  // Python truthiness for the values profiles carry: no null, "", [], {}, false or 0.
  if (v === null || v === undefined || v === "" || v === false || v === 0) return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "object") return Object.keys(v).length > 0;
  return true;
}

function _isobj(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }

function _crust(o) {
  // Crustdata's person enrich comes back as [{matches: [{person_data: {...}}]}], with the work
  // history under experience.employment_details.{current, past}. Flatten it into the plain shape
  // the readers below take. Anything else passes through untouched.
  if (Array.isArray(o) && o.length && _isobj(o[0]) && (o[0].matches || o[0].person_data)) o = o[0];
  if (_isobj(o) && (Array.isArray(o.data) || (_isobj(o.data) && (o.data.matches || o.data.person_data)))) {
    o = Array.isArray(o.data) ? o.data[0] : o.data;
  }
  if (_isobj(o) && Array.isArray(o.matches)) o = (o.matches[0] || {}).person_data || {};
  if (_isobj(o) && _isobj(o.person_data)) o = o.person_data;
  const ed = _isobj(o) && _isobj(o.experience) ? o.experience.employment_details : null;
  if (!_isobj(ed)) return o;
  const bp = o.basic_profile || {};
  const role = (x, cur) => ({company: x.name, title: x.title, start_date: x.start_date, end_date: x.end_date,
    is_current: cur, description: x.description, employment_type: x.employment_type,
    company_domain: x.company_website_domain || x.company_website,
    company_linkedin_url: x.company_professional_network_profile_url});
  return {name: bp.name, headline: bp.headline, last_updated: bp.last_updated || o.updated_at,
          experience: (ed.current || []).map(x => role(x, true)).concat((ed.past || []).map(x => role(x, false)))};
}

function _obj(v) {
  // An object from an object or from JSON text; {} otherwise. Columns can arrive as either.
  if (_isobj(v) || Array.isArray(v)) {
    const c = _crust(v);
    return Array.isArray(c) ? {experience: c} : c;
  }
  const t = _s(v);
  if (t.slice(0, 1) === "{" || t.slice(0, 1) === "[") {
    let o;
    try { o = JSON.parse(t); } catch (e) { return {}; }
    return _obj(o);
  }
  return {};
}

function _first(d, keys) {
  if (!_isobj(d)) return null;
  for (const k of keys) {
    const v = d[k];
    if (!(v === null || v === undefined || v === "" || (Array.isArray(v) && !v.length) ||
          (_isobj(v) && !Object.keys(v).length))) return v;
  }
  return null;
}

function _truthy(v) { return ["true", "yes", "1", "y"].indexOf(_s(v).toLowerCase()) >= 0; }

function _digits(s) { return /^\d+$/.test(s); }

function _pad(n, w) { return String(n).padStart(w, "0"); }

function _date(v) {
  // YYYY-MM-DD, YYYY-MM or YYYY from what profiles carry: ISO text, 'Mar 2021', 'March 2021',
  // '2021', or {"year":2021,"month":3,"day":1}. '' when there is no date.
  if (_isobj(v)) {
    const y = v.year;
    if (!_has(y)) return "";
    let out = _pad(parseInt(y, 10), 4);
    if (_has(v.month)) {
      out += "-" + _pad(parseInt(v.month, 10), 2);
      if (_has(v.day)) out += "-" + _pad(parseInt(v.day, 10), 2);
    }
    return out;
  }
  const t = _s(v).toLowerCase().replace(/,/g, " ").replace(/\./g, " ");
  if (!t || ["present", "current", "now", "null", "none"].indexOf(t) >= 0) return "";
  if (t.length >= 4 && _digits(t.slice(0, 4))) {
    const parts = t.slice(0, 10).split("-");
    if (parts.length >= 2 && _digits(parts[1].slice(0, 2))) {
      if (parts.length >= 3 && _digits(parts[2].slice(0, 2)))
        return parts[0] + "-" + parts[1].slice(0, 2) + "-" + parts[2].slice(0, 2);
      return parts[0] + "-" + parts[1].slice(0, 2);
    }
    return t.slice(0, 4);
  }
  const words = t.split(/\s+/).filter(w => w);
  const year = words.find(w => w.length === 4 && _digits(w)) || "";
  if (!year) return "";
  for (const w of words) {
    for (let i = 0; i < MONTHS.length; i++) {
      if (w.length >= 3 && MONTHS[i].startsWith(w)) return year + "-" + _pad(i + 1, 2);
    }
  }
  return year;
}

function _day_number(y, m, d) {
  // Days from 1970-01-01 to a calendar date, by arithmetic: no Date parsing, which reads
  // partial dates and time zones differently across runtimes.
  y -= m <= 2 ? 1 : 0;
  const era = Math.floor((y >= 0 ? y : y - 399) / 400);
  const yoe = y - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
  return era * 146097 + doe - 719468;
}

function _epoch(d) {
  // Seconds since 1970 for YYYY[-MM[-DD]] (month and day default to 1); null if unreadable.
  if (!d || d.length < 4 || !_digits(d.slice(0, 4))) return null;
  const y = parseInt(d.slice(0, 4), 10);
  const ms = d.length >= 7 ? d.slice(5, 7) : "1";
  const ds = d.length >= 10 ? d.slice(8, 10) : "1";
  if (!/^\s*\d+\s*$/.test(ms) || !/^\s*\d+\s*$/.test(ds)) return null;
  const m = parseInt(ms, 10), dd = parseInt(ds, 10);
  if (!(m >= 1 && m <= 12 && dd >= 1 && dd <= 31)) return null;
  return _day_number(y, m, dd) * 86400;
}

function _days_since(d) {
  const e = _epoch(d);
  return e === null ? null : Math.floor((NOW_MS / 1000 - e) / 86400);
}

function _words_date(d) {
  // 'March 2021' for Jev: it reads words better than digits, and it never compares them.
  if (!d) return "not stated";
  if (d.length >= 7) {
    const m = parseInt(d.slice(5, 7), 10);
    if (m >= 1 && m <= 12) return MONTHS[m - 1].charAt(0).toUpperCase() + MONTHS[m - 1].slice(1) + " " + d.slice(0, 4);
    return d.slice(0, 4);
  }
  return d.slice(0, 4);
}

function _months_between(a, b) {
  const ea = _epoch(a);
  const eb = b ? _epoch(b) : NOW_MS / 1000;
  if (ea === null || eb === null || eb < ea) return null;
  return Math.floor((eb - ea) / (86400 * 30.44));
}

function _domain(v) {
  let t = _s(v).toLowerCase();
  for (const p of ["https://", "http://"]) if (t.startsWith(p)) t = t.slice(p.length);
  t = t.split("/")[0].split("?")[0].split(":")[0].trim().replace(/^\.+|\.+$/g, "");
  if (t.startsWith("www.")) t = t.slice(4);
  return t.indexOf(".") >= 0 && t.indexOf(" ") < 0 ? t : "";
}

function _root(d) {
  const parts = d.split(".").filter(p => p);
  const n = parts.length;
  if (n >= 3 && TWO_PART.has(parts[n - 2]) && parts[n - 1].length === 2) return parts.slice(-3).join(".");
  return parts.slice(-2).join(".");
}

function _li_company(v) {
  // The company page slug (or numeric id) from a LinkedIn company URL; '' otherwise.
  const t = _s(v).toLowerCase();
  for (const marker of ["linkedin.com/company/", "linkedin.com/school/", "linkedin.com/showcase/"]) {
    const i = t.indexOf(marker);
    if (i >= 0) return t.slice(i + marker.length).split("/")[0].split("?")[0].trim();
  }
  return "";
}

function _tokens(name) {
  const out = [];
  let cur = "";
  for (const ch of _s(name).toLowerCase() + " ") {
    if (/[\p{L}\p{N}]/u.test(ch)) cur += ch;
    else if (cur) { out.push(cur); cur = ""; }
  }
  return out.filter(t => !LEGAL.has(t));
}

function _name_tokens(v) { return new Set(_tokens(v).filter(w => w.length >= 2)); }

function _li_person(v) {
  const t = _s(v).toLowerCase();
  return t.indexOf("linkedin.com/in/") >= 0 || t.indexOf("linkedin.com/sales/") >= 0 || t.indexOf("linkedin.com/talent/") >= 0;
}

function _seteq(a, b) { return a.size === b.size && [...a].every(x => b.has(x)); }
function _subset(a, b) { return [...a].every(x => b.has(x)); }

// ---------------------------------------------------------------- reading a profile

const ROLE_LISTS = ["experience", "experiences", "positions", "work_experience", "employment_history",
  "jobs", "employments", "workExperience", "current_experience"];

function _roles_list(p) {
  for (const k of ROLE_LISTS) {
    const v = p[k];
    if (Array.isArray(v) && v.length) return v;
  }
  for (const k of ["profile", "person", "data", "result"]) {
    if (_isobj(p[k])) {
      const got = _roles_list(_crust(p[k]));
      if (got.length) return got;
    }
  }
  return [];
}

function _role(x) {
  // One role in one shape, whatever the provider called the fields.
  if (!_isobj(x)) return null;
  const comp = x.company;
  const cd = _isobj(comp) ? comp : {};
  let company = _has(cd) ? _first(cd, ["name", "company_name"]) : comp;
  company = _s(_has(company) ? company : _first(x, ["company_name", "companyName", "org", "organization",
    "organization_name", "employer", "employer_name"]));
  let title = x.title;
  if (_isobj(title)) title = title.name;
  title = _s(_has(title) ? title : _first(x, ["job_title", "position", "role", "name_of_role"]));
  if (!company && !title) return null;
  const start = _date(_first(x, ["start_date", "starts_at", "startDate", "start", "date_from", "from"]));
  const end = _date(_first(x, ["end_date", "ends_at", "endDate", "end", "date_to", "to"]));
  let cur = _first(x, ["is_current", "current", "isCurrent", "is_primary"]);
  cur = cur === null ? null : _truthy(cur);
  const domain = _domain(_has(cd) ? _first(cd, ["website", "domain", "company_domain"]) : "") ||
    _domain(_first(x, ["company_domain", "domain", "company_website", "website"]));
  const li = _li_company(_has(cd) ? _first(cd, ["linkedin_url", "url", "linkedin"]) : "") ||
    _li_company(_first(x, ["company_linkedin_url", "company_url", "url", "linkedin_url"]));
  const desc = _s(_first(x, ["summary", "description", "desc"])).slice(0, 300);
  const ended_past = !!end && (_days_since(end) || 0) > 0;
  const is_open = cur === true || (!end && cur !== false) || (!!end && !ended_past);
  return {company: company.slice(0, 120), title: title.slice(0, 160), start: start, end: end,
          is_current: cur, open: !!is_open, domain: domain, linkedin: li, description: desc,
          work_type: _s(_first(x, ["location_type", "employment_type", "workplace_type"])).slice(0, 40)};
}

function read_profile(p) {
  // [roles, facts] from a profile object. Roles are de-duplicated on company+title+start.
  p = _crust(p) || {};
  const roles = [], seen = new Set();
  for (const x of _roles_list(p)) {
    const r = _role(x);
    if (!r) continue;
    const k = JSON.stringify([r.company.toLowerCase(), r.title.toLowerCase(), r.start]);
    if (seen.has(k)) continue;
    seen.add(k);
    roles.push(r);
  }
  const refreshed = _date(_first(p, ["last_refresh", "last_updated", "updated_at", "lastRefresh"]));
  const facts = {headline: _s(_first(p, ["headline", "occupation"])).slice(0, 200),
                 name: _s(_first(p, ["name", "full_name", "fullName"])),
                 refreshed: refreshed, age_days: _days_since(refreshed)};
  return [roles, facts];
}

// ---------------------------------------------------------------- is this role at the company?

function _label_tokens(dom) {
  // The words of a website's name: 'fabrikam-freight.co.uk' -> {'fabrikam', 'freight'}.
  return new Set(_tokens(_root(dom).split(".")[0].replace(/-/g, " ")).filter(w => w.length >= 3));
}

function target_of(inp) {
  const name = _s(inp.company_name).slice(0, 120);
  const dom = _domain(inp.company_domain);
  const li = _li_company(inp.company_linkedin_url);
  const toks = new Set(_tokens(name));
  if (dom) for (const w of _label_tokens(dom)) toks.add(w);
  return {name: name, domain: dom, linkedin: li, tokens: toks};
}

function identity(r, t) {
  // How this role's company relates to the target, decided in code where code can decide:
  // 'confirmed' (same website or same LinkedIn company page), 'name_match' / 'name_overlap' /
  // 'id_conflict' (Jev is asked whether it is the same company), or 'none'.
  if (t.domain && r.domain && _root(t.domain) === _root(r.domain)) return ["confirmed", "same website (" + _root(r.domain) + ")"];
  if (t.linkedin && r.linkedin && t.linkedin === r.linkedin) return ["confirmed", "same LinkedIn company page"];
  const rt = new Set(_tokens(r.company));
  if (r.domain) for (const w of _label_tokens(r.domain)) rt.add(w);
  if (!rt.size || !t.tokens.size) return ["none", ""];
  const conflict = (t.domain && r.domain) || (t.linkedin && r.linkedin);
  const rc = new Set(_tokens(r.company));
  if (_seteq(rt, t.tokens) || (rc.size && _seteq(rc, new Set(_tokens(t.name))))) return [conflict ? "id_conflict" : "name_match", "same name"];
  const [small, big] = rt.size <= t.tokens.size ? [rt, t.tokens] : [t.tokens, rt];
  if (_subset(small, big) && [...small].some(w => w.length >= 3)) return [conflict ? "id_conflict" : "name_overlap", "names overlap"];
  return ["none", ""];
}

function _role_for_jev(r) {
  const out = {company: r.company || "not stated", job_title: r.title || "not stated",
               started: _words_date(r.start),
               ended: r.open ? "no end date (listed as current)" : _words_date(r.end)};
  if (r.description) out.description = r.description;
  if (r.work_type) out.work_type = r.work_type;
  if (r.domain) out.company_website = r.domain;
  return out;
}

function _target_for_jev(t) {
  const out = {};
  if (t.name) out.name = t.name;
  if (t.domain) out.website = t.domain;
  if (t.linkedin) out.linkedin_company_page = t.linkedin;
  return out;
}

function questions_for(i, r, t, others, later) {
  // The Jev questions for ONE role. Each states one condition and describes both answers:
  // Jev reads literally, and a question it has to interpret is one it can misread.
  const role = _role_for_jev(r);
  const qs = {};
  if (r.identity !== "confirmed") {
    qs["same_" + i] = {type: "boolean", instructions: {
      target_company: _target_for_jev(t), role: role,
      question: "Is the company in `role` the same company as `target_company`?"},
      criteria: {true: "The same company, one of its brands or divisions, or the same company " +
                       "under an earlier or later name.",
                 false: "A different organization, even if the two names share a word."}};
  }
  qs["kind_" + i] = {type: "choice", instructions: {
    role: role, question: "What relationship with the company in `role` does this role describe?"},
    criteria: KIND_OPTIONS};
  // The next two are only USED when another current role is itself a job (code decides that
  // from the other_* answers): a trustee seat never replaces a CEO job, and never outranks it.
  if (r.open && later.length) {
    qs["held_" + i] = {type: "boolean", instructions: {
      role: role, later_jobs: later,
      question: "`role` has no end date, and the person started the jobs in `later_jobs` after it. " +
                "Does the person most likely still hold `role` today?"},
      criteria: {true: "Still holds it. People commonly hold `role` at the same time as the jobs " +
                       "in `later_jobs`: several part-time, fractional, contract or consulting " +
                       "roles at once, or a founder or owner who also works somewhere else.",
                 false: "Most likely left without updating the profile: `role` is a full-time job " +
                        "and a full-time job in `later_jobs` replaced it."}};
  }
  if (r.open && others.length) {
    qs["main_" + i] = {type: "boolean", instructions: {
      role: role, other_current_roles: others,
      question: "Is `role` this person's main job, the one they spend most of their working time on?"},
      criteria: {true: "`role` is the main job, and the roles in `other_current_roles` get less " +
                       "of their time.",
                 false: "One of `other_current_roles` is the main job and `role` gets less of their time."}};
  }
  return qs;
}

function other_question(role) {
  // What kind of role each OTHER current role is (a job, or a side role). Code uses it to decide
  // whether "did they leave?" and "is this the main job?" are real questions for this person.
  return {type: "choice", instructions: {
    role: role, question: "What relationship with the company in `role` does this role describe?"},
    criteria: KIND_OPTIONS};
}

// ---------------------------------------------------------------- the steps

function intake(inp) {
  // Before anything is spent: is there a company to check against, is there a profile, and
  // does the profile have to be bought (crustdata_v3_person_enrich, priced per match)?
  inp = inp || {};
  const t = target_of(inp);
  const prof = _obj(inp.profile);
  const [roles, facts] = _has(prof) ? read_profile(prof) : [[], {age_days: null}];
  const url = _s(inp.linkedin_url) || _s(_first(prof, ["url", "linkedin_url", "profile_url"]));
  const skip = _truthy(inp.skip_enrichment);
  let max_age = null;
  if (_s(inp.max_profile_age_days)) {
    const n = Number(_s(inp.max_profile_age_days));
    max_age = isFinite(n) ? Math.trunc(n) : null;
  }
  const stale = roles.length > 0 && max_age !== null && facts.age_days !== null && facts.age_days > max_age;
  let need = (!roles.length || stale) && _li_person(url) && !skip;
  let why = "";
  if (!(t.name || t.domain || t.linkedin)) {
    need = false;
    why = "no company to check against: send company_name, company_domain or company_linkedin_url";
  } else if (!roles.length && !need) {
    if (skip && _li_person(url)) why = "no profile supplied and skip_enrichment is set";
    else if (url && !_li_person(url)) why = "no profile supplied, and linkedin_url is not a LinkedIn profile URL";
    else why = "no profile and no LinkedIn profile URL to enrich";
  }
  const keep = {};
  for (const k of ["company_name", "company_domain", "company_linkedin_url", "profile", "full_name", "source_ref"])
    keep[k] = inp[k] === undefined ? null : inp[k];
  return {need_enrichment: !!need, linkedin_url: need ? url : "",
          enrich_reason: need && stale ? "profile older than " + max_age + " days" : (need ? "no profile supplied" : ""),
          blocked: why, stale_supplied: !!(stale && need), inp: keep, source_ref: _s(inp.source_ref)};
}

function prepare(ix, found) {
  // Pick the profile (supplied or just bought), find the roles that could be at the company,
  // and build ONE ai_evaluate request with a few small questions per role.
  ix = ix || {};
  const inp = ix.inp || {};
  const t = target_of(inp);
  let source = "none";
  let prof = {};
  const got = _obj(found);
  if (ix.need_enrichment && _roles_list(got).length) { prof = got; source = "enriched"; }
  else if (_has(_obj(inp.profile))) { prof = _obj(inp.profile); source = "supplied"; }
  const [roles, facts] = _has(prof) ? read_profile(prof) : [[], {age_days: null, refreshed: ""}];
  const base = {ask: false, blocked: ix.blocked || "", target: {name: t.name, domain: t.domain, linkedin: t.linkedin},
                source: source, facts: facts, roles: [], context: [], jev_body: null,
                source_ref: ix.source_ref || "", enrich_note: ""};
  if (ix.need_enrichment && source !== "enriched") {
    if (_isobj(found) && found._not_run) base.enrich_note = "not enriched: this preview does not buy profiles (add --enrich)";
    else base.enrich_note = "the profile lookup returned no work history for " + (ix.linkedin_url || "the URL");
    if (ix.stale_supplied) base.enrich_note += "; the supplied (older) profile was used instead";
  }
  if (base.blocked) return base;
  if (!roles.length) { base.blocked = "no_profile"; return base; }
  // The work history as read, so a bought profile can be checked again elsewhere.
  base.profile_roles = roles.slice(0, 25).map(r => ({company: r.company, title: r.title, start: r.start, end: r.end,
    is_current: r.is_current, domain: r.domain, linkedin: r.linkedin, description: r.description, work_type: r.work_type}));
  for (const r of roles) [r.identity, r.identity_why] = identity(r, t);
  let cands = roles.filter(r => r.identity !== "none");
  const key = r => [r.open ? 0 : 1, r.identity === "confirmed" ? 0 : 1, -(_epoch(r.start) || 0)];
  cands.sort((a, b) => { const x = key(a), y = key(b); for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] - y[i]; return 0; });
  let open_other = roles.filter(r => r.identity === "none" && r.open);
  if (!cands.length && open_other.length) {
    // Nothing on the profile names the company. The company may have changed its name, or the
    // role may be listed under a parent: ask Jev about each current role, cheaply.
    for (const r of open_other) { r.identity = "name_unrelated"; r.identity_why = "no shared name; asked in case of a rename"; }
    cands = open_other;
    open_other = [];
  }
  cands = cands.slice(0, MAX_ROLES);
  open_other = open_other.slice(0, MAX_CONTEXT);
  base.context = open_other.map(_role_for_jev);
  base.roles = cands;
  const want = _s(inp.full_name);
  const got_name = _s(facts.name);
  if (want && got_name) {
    const g = _name_tokens(got_name);
    if (![..._name_tokens(want)].some(w => g.has(w)))
      base.name_mismatch = "the profile is for " + got_name.slice(0, 60) + ", not " + want.slice(0, 60);
  }
  if (!cands.length) return base;
  const questions = {};
  open_other.forEach((o, k) => { questions["other_" + k] = other_question(_role_for_jev(o)); });
  cands.forEach((r, i) => {
    const e = _epoch(r.start);
    r.other_idx = r.open ? open_other.map((_, k) => k) : [];
    r.later_idx = open_other.map((o, k) => k).filter(k => r.open && e !== null && (_epoch(open_other[k].start) || 0) > e);
    r.asked_held = r.later_idx.length > 0;
    r.asked_main = r.other_idx.length > 0;
    r.others = r.open ? open_other.map(o => o.company + ": " + o.title) : [];
    Object.assign(questions, questions_for(i, r, t, r.other_idx.map(k => _role_for_jev(open_other[k])),
                                           r.later_idx.map(k => _role_for_jev(open_other[k]))));
  });
  base.ask = true;
  base.jev_body = {model: JEV.model, state: {person_headline: facts.headline || "not stated"}, questions: questions};
  return base;
}

// ---------------------------------------------------------------- the verdict

const JEV_ERRORS = {
  authentication: "Deepline refused the call (authentication): run `deepline auth status`, then re-run",
  authorization: "Deepline refused the call (authorization): check the workspace's access to ai_evaluate",
  billing: "Deepline credits ran out (billing): top up, then re-run these people",
  rate_limit: "Jev rate limit: re-run these people later",
  network: "Jev could not be reached (network): re-run these people later",
  upstream: "Jev is unavailable or overloaded (upstream): re-run these people later",
  validation: "Jev rejected the request as malformed (validation)"};

function _p(a, key) {
  if (!a || a[key] === undefined || a[key] === null) return null;
  const x = Number(a[key]);
  return isNaN(x) ? null : Math.max(0, Math.min(1, x));
}

function _margin(probs) {
  // Our confidence for a distribution: the top probability minus the runner-up (for a yes/no it
  // equals |2p - 1|). ai_evaluate returns no confidence field. null when no distribution came back.
  const vals = Object.keys(probs || {}).map(k => Number(probs[k]) || 0).sort((a, b) => b - a);
  if (!vals.length) return null;
  return vals[0] - (vals.length > 1 ? vals[1] : 0);
}

function _maxBy(xs, f) { return xs.reduce((best, x) => (f(x) > f(best) ? x : best)); }

function judge(pr, answers) {
  // Per role: P(same company), P(still held), the kind of role, P(main job). Then the four
  // things the verdict needs: P(works there now), P(holds only a passive role), P(was there).
  const out = [], notes = [];
  const cur_ctx = pr.context || [];
  const job = [];          // for each other current role: P(it is a job rather than a side role)
  for (let k = 0; k < cur_ctx.length; k++) {
    const pk = (answers["other_" + k] || {}).probabilities || {};
    job.push(Object.keys(pk).length ? WORKING.reduce((s, x) => s + (Number(pk[x]) || 0), 0) : 0.5);
  }
  (pr.roles || []).forEach((r, i) => {
    const a_same = answers["same_" + i], a_kind = answers["kind_" + i];
    const a_held = answers["held_" + i], a_main = answers["main_" + i];
    const p_same = r.identity === "confirmed" ? 1 : (a_same ? (_p(a_same, "probability") || 0) : 0);
    // Replaced only if a later current role is a job: weigh Jev's "still holds it?" by how likely
    // that is. A later advisory seat leaves the role held.
    const p_rep = Math.max(0, ...(r.later_idx || []).filter(k => k < job.length).map(k => job[k]));
    let p_held;
    if (!r.open) p_held = 0;
    else if (r.asked_held && a_held) p_held = p_rep * (_p(a_held, "probability") || 0) + (1 - p_rep);
    else p_held = 1;
    const probs = (a_kind || {}).probabilities || {};
    const pkeys = Object.keys(probs);
    const kind = (a_kind || {}).choice || (pkeys.length ? _maxBy(pkeys, k => Number(probs[k]) || 0) : "not_enough_information");
    const k_conf = _margin(probs);
    let work = WORKING.reduce((s, k) => s + (Number(probs[k]) || 0), 0);
    let passive = PASSIVE.reduce((s, k) => s + (Number(probs[k]) || 0), 0);
    if (!pkeys.length) { work = 0; passive = 0; }
    const p_other_job = Math.max(0, ...(r.other_idx || []).filter(k => k < job.length).map(k => job[k]));
    const p_main = !(r.asked_main && a_main) ? 1 : p_other_job * (_p(a_main, "probability") || 0) + (1 - p_other_job);
    // Only a role that is likely a JOB competes for "main job"; a board seat is never a rival.
    const rivals = (r.other_idx || []).filter(k => k < job.length && job[k] >= 0.5);
    const rival = rivals.length ? _maxBy(rivals, k => job[k]) : null;
    out.push({company: r.company, title: r.title, started: r.start, ended: r.end,
              listed_current: r.open, identity: r.identity, why: r.identity_why,
              same_company: _r2(p_same), still_held: _r2(p_held), kind: kind,
              kind_confidence: k_conf === null ? null : _r2(k_conf),
              working_share: _r2(work), passive_share: _r2(passive),
              passive_kind: _maxBy(PASSIVE, k => Number(probs[k]) || 0),
              main_job: _r2(p_main), other_current_roles: r.others || [],
              other_job_likely: _r2(p_other_job), replaced_by_job_likely: _r2(p_rep),
              rival_job: rival !== null && rival < cur_ctx.length ? cur_ctx[rival].company : "",
              p_work: p_same * p_held * work, p_passive: p_same * p_held * passive, p_was_there: p_same});
    const label = (r.title || "role") + " at " + (r.company || "?");
    if (r.identity !== "confirmed" && a_same && Math.abs(2 * p_same - 1) < FLOOR && p_same >= 0.2)
      notes.push("same company? " + label + ": unsure (" + Math.round(p_same * 100) + "% yes)");
    if (p_same >= 0.5 && k_conf !== null && k_conf < FLOOR && kind !== "not_enough_information") {
      const top = pkeys.slice().sort((x, y) => (Number(probs[y]) || 0) - (Number(probs[x]) || 0)).slice(0, 2);
      notes.push("kind of role, " + label + ": unsure (" + top.map(o => o + " " + Math.round((Number(probs[o]) || 0) * 100) + "%").join(", ") + ")");
    }
    if (p_same >= 0.5 && r.asked_held && a_held && p_rep >= 0.5 && Math.abs(2 * p_held - 1) < FLOOR)
      notes.push("still in it? " + label + ": unsure (" + Math.round(p_held * 100) + "% yes)");
  });
  return [out, notes];
}

function _unwrap(b) {
  // ai_evaluate's output, whether it came as the tool's raw envelope or one level down.
  if (typeof b === "string") { try { b = JSON.parse(b); } catch (e) { b = {raw: b}; } }
  b = _isobj(b) ? b : {};
  if (!b.result && _isobj(b.data)) b = b.data;
  return b;
}

function verdict(pr, status_code, body) {
  // The one answer for one person. Keys are always all present. Rules, first match wins:
  // blocked → no profile → Jev failed → nothing at the company → works there (primary or side
  // job) → holds only a passive role → was there and left → unsure.
  pr = pr || {};
  let model = "not called", tokens = 0, err = "";
  let answers = {};
  if (pr.ask) {
    const b = _unwrap(body);
    answers = b.result && _isobj(b.result.answers) ? b.result.answers : {};
    const code = Math.trunc(Number(status_code)) || 0;
    if (code !== 200 || !Object.keys(answers).length) {
      err = JEV_ERRORS[b.category] ||
        (code === 200 ? "Jev returned no answers: " : "Jev call failed (" + (b.category || code || "error") + "): ") +
        (b.message ? String(b.message) : JSON.stringify(b)).slice(0, 300);
      return finish(pr, "not_checked", "unknown", 0, "failed", "Not checked: " + err, "none", {}, [], model, 0, err);
    }
    model = _s((b.result.response || {}).modelId) || _s((b.meta || {}).model) || JEV.model;
    tokens = Number((b.usage || {}).inputTokens) || 0;
  }
  const blocked = pr.blocked || "";
  if (blocked && blocked !== "no_profile")
    return finish(pr, "not_checked", "unknown", 0, "blocked_missing_input", "Not checked: " + blocked, "none", {}, [], model, tokens, "");
  if (blocked === "no_profile") {
    const why = pr.enrich_note || "the profile has no work history";
    return finish(pr, "not_checked", "unknown", 0, "no_profile", "Not checked: " + why, "none", {}, [], model, tokens, "");
  }
  const t = pr.target || {};
  const tname = t.name || t.domain || t.linkedin || "the company";
  const [rows, notes] = judge(pr, answers);
  const cur_ctx = pr.context || [];
  const other_now = cur_ctx.map(c => c.company + ": " + c.job_title);
  const same = rows.filter(x => x.same_company >= 0.5);
  if (!same.length) {
    let ev = "No role at " + tname + " on this profile";
    const near = rows.filter(x => ["name_match", "name_overlap", "id_conflict"].indexOf(x.identity) >= 0);
    if (near.length) {
      ev += " (" + [...new Set(near.map(x => x.company))].sort().slice(0, 2).join("; ") + ": a different company, " +
        Math.round(100 * Math.max(...near.map(x => x.same_company))) + "% same)";
    }
    if (other_now.length) ev += "; currently: " + other_now.slice(0, 3).join("; ");
    const conf = 100 - Math.round(100 * Math.max(0, ...rows.map(x => x.same_company)));
    return finish(pr, "no", "no_record", conf, "checked", ev, notes.join("; ") || "none", {}, rows,
                  model, tokens, "", _main_from_context(cur_ctx));
  }
  // Near-ties (two current roles at the company, both within 0.05 of the best) go to the most
  // recently started: a promotion the profile never closed leaves the old title "current" too,
  // and the evidence should name the role the person holds now.
  const pick = (key) => {
    const top = Math.max(...same.map(x => x[key]));
    return _maxBy(same.filter(x => x[key] >= top - 0.05), x => x.started || "");
  };
  const best_work = pick("p_work"), best_pass = pick("p_passive");
  const p_work = best_work.p_work, p_pass = best_pass.p_passive;
  const p_was = Math.max(...same.map(x => x.p_was_there));
  let role, rel, active, conf;
  if (p_work >= 0.6) {
    role = best_work;
    rel = role.main_job >= 0.5 ? "primary_job" : "side_job";
    active = "yes"; conf = p_work;
  } else if (p_pass >= 0.6) {
    role = best_pass;
    rel = role.passive_kind;
    active = "passive"; conf = p_pass;
  } else if (same.every(x => x.still_held < 0.4)) {
    role = _maxBy(same, x => x.ended || x.started || "");
    rel = "former"; active = "no"; conf = p_was * (1 - Math.max(...same.map(x => x.still_held)));
  } else {
    role = _maxBy(same, x => x.p_work + x.p_passive);
    rel = "unknown"; active = "unsure"; conf = 1 - Math.max(p_work, p_pass);
    notes.push("unsure overall: works there " + Math.round(p_work * 100) + "%, passive role " + Math.round(p_pass * 100) + "%");
  }
  const own = (role.other_current_roles || []).filter(o => o);
  const others = own.length ? own : other_now;
  const main = rel === "primary_job" ? tname : (role.rival_job || _main_from_context(cur_ctx, role));
  const ev = _evidence(role, rel, tname, others);
  return finish(pr, active, rel, Math.round(100 * conf), "checked", ev, notes.join("; ") || "none", role,
                rows, model, tokens, "", main, others);
}

function _main_from_context(cur_ctx, role) {
  if (role && (role.main_job === undefined ? 1 : role.main_job) < 0.5 && cur_ctx.length) return cur_ctx[0].company;
  return cur_ctx.length === 1 ? cur_ctx[0].company : "";
}

const KIND_WORDS = {employee: "works there", contractor: "works there as a contractor or consultant",
  intern: "works there as an intern", advisor_or_board: "advisor or board member",
  investor: "investor", honorary: "honorary or volunteer role",
  not_enough_information: "role type unclear"};

function _evidence(role, rel, tname, others) {
  const title = role.title || "untitled role";
  const since = _words_date(role.started || "");
  let s;
  if (rel === "former" && role.ended) {
    s = title + " at " + (role.company || tname) + ", " + since + " to " + _words_date(role.ended) + " (ended)";
  } else if (rel === "former") {
    s = title + " at " + (role.company || tname) + " since " + since +
      ", still listed as current, but replaced by a later full-time job" + (role.rival_job ? " at " + role.rival_job : "");
  } else {
    s = title + " at " + (role.company || tname) + " since " + since + " (" + (KIND_WORDS[role.kind] || "role");
    if (rel === "primary_job" || rel === "side_job") s += "; " + (rel === "primary_job" ? "main job" : "not the main job");
    s += ")";
    if (role.identity !== "confirmed") s += "; same company as " + tname + ": " + Math.round(100 * (role.same_company || 0)) + "% sure";
  }
  if (others.length) s += ". Also current: " + others.slice(0, 3).join("; ");
  return s;
}

function finish(pr, active, rel, conf, status, evidence, review, role, rows, model, tokens, err, main, others) {
  const facts = pr.facts || {};
  const age = facts.age_days === undefined ? null : facts.age_days;
  if (status === "checked" && age !== null && age > 365)
    review = (review === "none" ? "" : review + "; ") + "profile last refreshed " + age + " days ago";
  if (pr.name_mismatch && status === "checked") {
    review = (review === "none" ? "" : review + "; ") + pr.name_mismatch;
    conf = Math.min(conf, 50);
  }
  if (pr.enrich_note && status === "checked") review = (review === "none" ? "" : review + "; ") + pr.enrich_note;
  role = role || {};
  let months = "";
  if (role.started) {
    const m = _months_between(role.started, rel === "former" ? role.ended : null);
    months = m === null ? "" : m;
  }
  const clean = rows.map(x => { const c = Object.assign({}, x); delete c.p_work; delete c.p_passive; delete c.p_was_there; return c; });
  const t = pr.target || {};
  return {active_at_company: active, relationship: rel, verdict_confidence: Math.max(0, Math.min(100, conf)),
          check_status: status, evidence: evidence, needs_review: review || "none",
          check_note: status === "checked" ? "none" : evidence,
          company_checked: t.name || t.domain || t.linkedin || "none given",
          role_title: role.title || "", role_company: role.company || "",
          role_started: role.started || "", role_ended: rel === "former" ? (role.ended || "") : "",
          months_in_role: months, other_current_roles: (others || []).join("; "),
          main_employer: main || "", profile_source: pr.source || "none",
          profile_age_days: age === null ? "" : age, roles_json: JSON.stringify(clean),
          jev_model: model, jev_input_tokens: tokens || 0, error: err, source_ref: pr.source_ref || "",
          checked_at: new Date(NOW_MS).toISOString().replace(/\.\d+Z$/, "Z")};
}
'''

NODE_MAIN = r'''
const FNS = {_date, _days_since, _root, _role, _obj, read_profile, target_of, intake, prepare, verdict,
  identity: (r, t) => identity(r, Object.assign({}, t, {tokens: new Set(t.tokens)}))};
let buf = "";
process.stdin.on("data", d => { buf += d; });
process.stdin.on("end", () => {
  NOW_MS = Date.now();
  const q = JSON.parse(buf);
  const out = FNS[q.fn](...q.args);
  process.stdout.write(JSON.stringify(out === undefined ? null : out, (k, v) => v instanceof Set ? [...v] : v));
});
'''


def render_core():
    return CORE.replace("__JEV__", json.dumps({"tool": JEV["tool"], "model": JEV["model"]}))


def node_call(fn, *args):
    """Run one CORE function under node, exactly the text the play embeds."""
    if not shutil.which("node"):
        fail("`node` is not on PATH. It ships with the Deepline CLI's install (npm); install Node 18+.")
    r = subprocess.run(["node", "-e", render_core() + NODE_MAIN],
                       input=json.dumps({"fn": fn, "args": list(args)}), capture_output=True, text=True)
    if r.returncode != 0:
        fail("verdict code failed under node: %s" % (r.stderr or r.stdout)[:800])
    return json.loads(r.stdout)


def load_core():
    """The verdict code as callables, for the local preview and tests. Every call runs the same
    text the play runs."""
    return {name: (lambda *a, _n=name: node_call(_n, *a))
            for name in ("_date", "_days_since", "_root", "_role", "_obj", "read_profile", "target_of",
                         "identity", "intake", "prepare", "verdict")}


def _execute(tool, body, timeout="90s"):
    """One Deepline tool call from this machine. (200, raw output) or (code, {category, message})."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(body, f)
    try:
        res = deepline("tools", "execute", tool, "--input", "@" + path, "--timeout", timeout,
                       allow_fail=True, timeout=240)
    finally:
        os.unlink(path)
    if "exit" in res:
        d = res.get("data") if isinstance(res.get("data"), dict) else {}
        e = d.get("error") if isinstance(d.get("error"), dict) else {}
        return (e.get("statusCode") or e.get("status") or 0,
                {"category": e.get("category") or e.get("code") or "", "message": str(res.get("error"))[:300]})
    tr = res.get("toolResponse") or {}
    return 200, tr.get("raw") or tr.get("rawV2") or res.get("result") or res


def ask_jev(body):
    return _execute(JEV["tool"], body)


def enrich_profile(url):
    """Buy one profile with crustdata_v3_person_enrich (priced per matched record)."""
    st, raw = _execute(ENRICH_TOOL, {"professional_network_profile_urls": [url],
                                     "fields": ["basic_profile", "experience"]})
    return raw if st == 200 else None


def check_record(record, call=None, enrich=None):
    """One person, locally, exactly as the play would: intake, (enrich), prepare, (Jev), verdict.
    `call(body)` -> (status, body) is the Jev call (default: ai_evaluate through the CLI);
    `enrich(url)` -> profile is the paid lookup (default: none, so a URL-only record comes back
    no_profile rather than spending)."""
    core = load_core()
    ix = core["intake"](record)
    found = None
    if ix["need_enrichment"]:
        found = enrich(ix["linkedin_url"]) if enrich else {"_not_run": True}
    pr = core["prepare"](ix, found)
    if not pr["ask"]:
        return core["verdict"](pr, None, None)
    status, body = (call or ask_jev)(pr["jev_body"])
    return core["verdict"](pr, status, body)


# ======================================================================= the play

PLAY = r'''/** @mermaid __PLAY_NAME__
 * flowchart TD
 * records[("People: a CSV, rows, or one webhook record")] --> loop
 * subgraph loop["For each person"]
 *   enrich["Buy a profile if only a URL"] --> jev["Ask Jev about each role"]
 *   jev --> verdict["Verdict: code combines answers"]
 * end
 * loop --> out["Return the verdicts"]
 */
// @ts-nocheck
import { definePlay } from 'deepline';
// Generated by check-employment-with-jev (build_workflow.py). Do not edit by hand: change
// scripts/active_lib.py, run test_offline.py, and rebuild.
__CORE__

function _body(t) { return t.view === 'data' ? t.rawV2.data : t.rawV2; }

export default definePlay(
  '__PLAY_NAME__',
  async (ctx, input: any) => {
    NOW_MS = await ctx.step('now', async () => Date.now());
    const items: any = input && input.csv ? await ctx.csv(input.csv)
      : Array.isArray(input && input.rows) ? input.rows : [input || {}];
    // @mermaid-node records type:"dataset" out:"records"
    const records = await ctx
      .dataset('records', items)
      // @mermaid-node enrich out:"found"
      .withColumn('found', async (row: any, rowCtx) => {
        const ix = intake(row);
        if (!ix.need_enrichment) return null;
        try {
          const r: any = await rowCtx.tools.execute({
            id: 'enrich_profile',
            tool: 'crustdata_v3_person_enrich',
            input: { professional_network_profile_urls: [ix.linkedin_url], fields: ['basic_profile', 'experience'] },
            description: 'Buy the work history for a person sent with only a LinkedIn URL.',
          });
          return _body(r.toolResponse);
        } catch (e: any) {
          // No profile is not a verdict: the person comes back no_profile, with the reason.
          return { _enrich_error: String(e?.message || e) };
        }
      })
      // @mermaid-node jev out:"jev"
      .withColumn('jev', async (row: any, rowCtx) => {
        const pr = prepare(intake(row), row.found);
        if (!pr.ask) return null;
        try {
          const r: any = await rowCtx.tools.execute({
            id: 'ask_jev',
            tool: 'ai_evaluate',
            input: pr.jev_body as any,
            description: 'Ask Jev the small questions about each role, in one request.',
          });
          return { status: 200, body: _body(r.toolResponse) };
        } catch (e: any) {
          // A failed Jev call never becomes a verdict: the person comes back failed.
          return { status: e?.statusCode || 0, body: { category: e?.category || e?.code || '', message: String(e?.message || e) } };
        }
      })
      // @mermaid-node verdict out:"verdict"
      .withColumn('verdict', (row: any) => verdict(prepare(intake(row), row.found), row.jev ? row.jev.status : null, row.jev ? row.jev.body : null))
__FLAT_COLUMNS__
      .run({ description: 'Check whether each person still works at the company.', undrawnColumns: __UNDRAWN__ });
    // @mermaid-node out out:"$output"
    return { records };
  },
  {
    description: 'Person Active At Company (Jev): whether a person still works at a company, and in what capacity. Roles judged by Jev (ai_evaluate), decided in code.',
    webhook: {},
  },
);
'''


def render_play():
    flat = "\n".join("      .withColumn('%s', (row: any) => row.verdict.%s)" % (k, k) for k in OUTPUT_KEYS)
    return (PLAY.replace("__CORE__", render_core())
                .replace("__PLAY_NAME__", PLAY_NAME)
                .replace("__FLAT_COLUMNS__", flat)
                .replace("__UNDRAWN__", json.dumps(list(OUTPUT_KEYS))))


def read_records(path, limit=None):
    """Records from a CSV, a JSON array (or {"records": [...]}) or JSON lines."""
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
    return recs[:limit] if limit else recs
