"""Read a conference campaign from the attendee-research API and reshape it for the customer DB.

Every function below the client is pure: it takes a decoded response and returns plain data,
so the whole reshaping layer is exercised by `test_offline.py` with no network and no key.

Two rules this module exists to enforce.

1. **Scan candidate paths; never pin one.** The service documents two response envelopes for
   the same endpoint and its own spec does not describe every block its runtime returns. A
   pinned path that moves resolves to `None`, and a missing value is indistinguishable from a
   contact who genuinely has none. So every read walks a list of places the value is known to
   live and records WHICH one answered.

2. **Distinguish every reason a value is absent.** `enriched` / `ranked_only` / `queued` /
   `failed` / `unranked` are five different facts about a contact, and collapsing them makes
   every downstream rate meaningless. (There is no `locked` state: locked is not something a
   contact reports about itself — it is what `ranked_only` looks like from outside.)
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://lanyard.redlinegrowth.com/api/public/v1"

# **Send a named User-Agent, always.** The service sits behind an edge that rejects Python's
# default agent outright: measured, `Python-urllib/3.x` gets `403` with a Cloudflare error
# page (code 1010) before the request ever reaches the API, while any named agent gets `200`
# on the identical request with the identical key. Nothing about that failure looks like a
# blocked agent — it arrives as a 403 with an HTML body, which reads exactly like a revoked
# key, so a skill that omitted this would tell the installer their key was bad and send them
# round the sign-in loop for ever.
USER_AGENT = "deepline-conference-attendees-skill/1.0"

# Terminal campaign states. Anything else means keep polling.
DONE = "complete"
FAILED = "failed"
TERMINAL = {DONE, FAILED}

# How a contact's dossier can stand. Order is significance, not chronology.
ENRICHED = "enriched"        # a dossier exists and is ours to write
QUEUED = "queued"            # enrichment accepted, not finished — try again later
FAILED_ENRICH = "failed"     # enrichment ran and produced nothing; retrying costs and repeats
RANKED_ONLY = "ranked_only"  # scored and ranked, never enriched — the free allowance ended here
UNRANKED = "unranked"        # discovered, not yet scored


class LanyardError(RuntimeError):
    """An API call that failed in a way the caller has to decide about.

    Carries the whole decoded `payload`, not just the message. Some failures are the most
    actionable responses the API gives: a `402` on an unlock returns `required`, `available`,
    `shortfall` and a `payment_url`, and throwing those away would turn "here is the link to
    top up" into "something went wrong".
    """

    def __init__(self, status, code, message, payload=None):
        self.status = status
        self.code = code
        self.message = message
        self.payload = payload or {}
        super().__init__(f"{status} {code}: {message}")


# --------------------------------------------------------------------------- client


def _request(method, path, key, body=None, query=None, timeout=60):
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("content-type", "application/json")
    req.add_header("accept", "application/json")
    req.add_header("user-agent", USER_AGENT)
    if key:
        req.add_header("authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = None
        if payload is None:
            # A non-JSON body did not come from the API — it came from something in front of
            # it. Saying so is the whole point: an edge 403 and a revoked key are the same
            # status code, and reporting the wrong one sends someone to re-authenticate over
            # and over against a problem that has nothing to do with their key.
            raise LanyardError(e.code, "non_json_response", edge_hint(e.code, raw)) from None
        # The live envelope puts the human sentence in `error` and the slug in `code`.
        # Read both, and never assume which one is which.
        raise LanyardError(
            e.code,
            payload.get("code") or payload.get("error") or "http_error",
            payload.get("message") or payload.get("error") or raw[:300],
            payload,
        ) from None


def edge_hint(status, raw):
    """Explain a response that came from in front of the API rather than from it."""
    snippet = " ".join(raw.split())[:200]
    if status in (401, 403):
        return ("blocked before reaching the API (HTTP %s, non-JSON body). This is an edge "
                "or proxy refusal, NOT a rejected key — a revoked key returns JSON. The usual "
                "cause is the HTTP client's User-Agent: this module sends %r for exactly that "
                "reason. Check network egress, a corporate proxy, or a changed edge rule "
                "before touching the key. Body: %s" % (status, USER_AGENT, snippet))
    if status in (429, 503):
        return ("rate-limited or temporarily unavailable at the edge (HTTP %s). Retry after a "
                "pause. Body: %s" % (status, snippet))
    return "HTTP %s with a non-JSON body: %s" % (status, snippet)


def read_key(env_var="LANYARD_API_KEY", path=None):
    """Read the key from the environment, or from a file of KEY=value lines.

    Never accepts a key as an argument: a key passed on a command line is visible in `ps`
    to every process on the machine.
    """
    if os.environ.get(env_var):
        return os.environ[env_var]
    if path and os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(env_var + "="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    return None


def whoami(key):
    return _request("GET", "/me", key)


def lookup_conference(key, name=None, city=None, year=None, url=None):
    """Resolve a conference. A URL is the tie-breaker when the name is ambiguous.

    Measured against the live service, not read from the spec, which documents neither:

      {"name": "SaaStr Annual"}                     -> SaaStr Annual 2027, Sep, San Mateo
      {"name": "https://www.saastrannual.com/"}     -> SaaStr AI Annual 2027, May, SF Bay
      {"name": "SaaStr Annual", "url": <that same URL>} -> the URL wins over the name
      {"url": "https://www.saastrannual.com/"}      -> same, with no name at all

    Two different real events, and only the URL separates them — which is exactly the case
    where a name lookup returns something confident and wrong. So when the edition that comes
    back is not the one they meant, find the event's own page and ask again with it.

    `url` is sent as its own field AND, when no name is given, as the query, because both
    forms are honoured today and the field is in no published spec.
    """
    if not (name or url):
        raise ValueError("a conference lookup needs a name or a URL")
    body = {"name": name or url}
    if url:
        body["url"] = url
    if city:
        body["city"] = city
    if year:
        body["year"] = str(year)
    return _request("POST", "/conferences/lookup", key, body)


# The campaign body accepts a conference object of exactly these keys. The LOOKUP returns
# more than that — measured, it also returns `edition`, `summary`, `likely_app` and
# `confidence` — so the looked-up object cannot be forwarded verbatim without sending fields
# the create call never documented accepting. Narrow it rather than hoping they are ignored:
# an unknown key is a 422 at best and silently dropped at worst, and neither is worth risking
# on a call that costs a campaign.
CONFERENCE_KEYS = ("name", "city", "start_date", "end_date", "website")


def conference_for_create(conf):
    """Narrow a looked-up conference to the keys the create call documents.

    `edition` is folded into the name when the name does not already carry it, because the
    edition is the whole point of having looked it up — dropping it silently would let the
    service re-guess the year it was just told."""
    if isinstance(conf, str):
        return conf
    out = {k: v for k, v in (conf or {}).items() if k in CONFERENCE_KEYS and v not in (None, "")}
    edition = str((conf or {}).get("edition") or "").strip()
    name = str(out.get("name") or "").strip()
    if edition and name and edition not in name:
        out["name"] = "%s %s" % (name, edition)
    return out


def create_campaign(key, payload):
    return _request("POST", "/campaigns", key, payload)


# The page a signed-in person opens to read their own results. Built from the id rather than
# taken from a response field, because the response's `share_url` is a DIFFERENT thing: it is
# a `/claim?t=<token>` link, and handing that over as "your results" is both the wrong page
# and a quiet act of sharing — the token in it grants access to whoever ends up holding it.
CAMPAIGN_PAGE = "https://lanyard.redlinegrowth.com/campaign/%s"


def campaign_url(campaign_id):
    """The logged-in view of a campaign. Only worth offering once it has results."""
    return CAMPAIGN_PAGE % campaign_id


def get_campaign(key, campaign_id):
    return _request("GET", f"/campaigns/{campaign_id}", key)


def list_contacts(key, campaign_id, limit=500, top=False):
    """Page the full contact list. Returns every contact, best first.

    `limit` is per page and the service caps it at 500; this walks `offset` until the page
    comes back short or `total` is reached, because a single unpaginated read silently
    truncates a large conference at the first page.
    """
    out, offset, total = [], 0, None
    while True:
        page = _request(
            "GET",
            f"/campaigns/{campaign_id}/contacts",
            key,
            query={"limit": limit, "offset": offset, "top": "true" if top else None,
                   # Sent explicitly rather than relying on the server's default. The flat
                   # format drops the dossier's lists, and this skill needs them intact —
                   # that is not a default worth inheriting silently.
                   "format": "default"},
        )
        rows = envelope_rows(page)
        out.extend(rows)
        total = page.get("total", total)
        offset += len(rows)
        if not rows or (total is not None and offset >= total):
            return out, total if total is not None else len(out)


def list_campaigns(key, limit=100):
    """Every campaign this key can see, newest first.

    This is what makes the skill recoverable from nothing but the API key. The campaign id is
    the whole of its state — `load --campaign <id>` is both the first load and every later
    top-up — and before this existed that id lived only in a local file. Lose the working
    directory and dossiers that had been paid for became unreachable.

    Returns campaigns started in the web app too, not only ones this key created.
    """
    out, offset = [], 0
    while True:
        page = _request("GET", "/campaigns", key, query={"limit": limit, "offset": offset})
        rows = page.get("campaigns") or envelope_rows(page)
        out.extend(rows)
        total = page.get("total")
        offset += len(rows)
        if not rows or (total is not None and offset >= total):
            return out, total if total is not None else len(out)


def campaign_haystack(row):
    """Everything about a campaign a person might name it by."""
    conf = row.get("conference") or {}
    if isinstance(conf, str):
        conf = {"name": conf}
    parts = [conf.get("name"), conf.get("edition"), conf.get("city"), row.get("label"),
             row.get("client_url"), row.get("campaign_id")]
    return " ".join(str(p) for p in parts if p).lower()


def match_campaigns(rows, query):
    """Campaigns matching a phrase, best first, with the score that got them there.

    Deliberately simple and deliberately NOT fuzzy: every word of the query must appear
    somewhere in the campaign's name, edition, city, label, client or id. Somebody coming
    back weeks later says "the SaaStr one" or "Disrupt 2026", and that is a substring
    question, not an edit-distance one. A loose matcher that guesses which conference
    somebody meant would write the wrong event's people into their customer DB — and the ids
    are opaque enough that nobody would notice.
    """
    q = " ".join((query or "").lower().split())
    if not q:
        return []
    words = q.split()
    scored = []
    for r in rows:
        hay = campaign_haystack(r)
        if not all(w in hay for w in words):
            continue
        # Prefer a contiguous hit on the whole phrase, then a more recent campaign.
        score = 2 if q in hay else 1
        scored.append((score, str(r.get("created_at") or ""), r))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [r for _s, _c, r in scored]


def unlock(key, campaign_id, selection, dry_run=True):
    """Spend credits to enrich locked contacts. Defaults to dry_run — pricing, not spending.

    `selection` is one of {"contact_ids": [...]}, {"tier": "S"}, {"tiers": [...]}, {"top": N}.

    The default is `dry_run=True` on purpose: the honest default for a function that spends
    somebody's money is the one that does not. A caller that wants to spend has to say so.

    A `402` is NOT a failure to handle by retrying — it carries `payment_url`, and the only
    correct response is to hand that link to a person. Money is never moved from here.
    """
    body = dict(selection)
    body["dry_run"] = bool(dry_run)
    return _request("POST", f"/campaigns/{campaign_id}/unlock", key, body)


def poll_campaign(key, campaign_id, on_stage=None, interval=25, timeout=3600):
    """Poll until the campaign settles. Returns the final campaign object.

    Settles only on a terminal status — never on a stage name, and never on a count that
    looks finished, because counts move while the last dossiers are still being written.
    """
    # Report on a change of STATUS OR MESSAGE. Keying on status alone goes silent for
    # minutes at a time: `queued` covers the whole research phase while the progress message
    # moves underneath it, and a run that prints nothing for ten minutes reads as a hang.
    started, last_seen = time.time(), None
    while True:
        c = get_campaign(key, campaign_id)
        status = c.get("status")
        seen = (status, stage_message(c))
        if on_stage and seen != last_seen:
            on_stage(status, seen[1])
            last_seen = seen
        if status in TERMINAL:
            return c
        if time.time() - started > timeout:
            raise LanyardError(0, "poll_timeout", f"still {status} after {int(time.time()-started)}s")
        time.sleep(interval)


# ----------------------------------------------------------------- pure reshaping


def _dig(obj, *paths, default=None):
    """Return the first non-empty value among several dotted paths."""
    for path in paths:
        cur = obj
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                cur = None
                break
        if cur not in (None, "", [], {}):
            return cur
    return default


def envelope_rows(page):
    """Accept either documented envelope and return the list of contacts.

    The default format keys them under `contacts`; the flat format keys them under `rows`.
    Reading only one of the two turns the other into an empty campaign.
    """
    if not isinstance(page, dict):
        return []
    for key in ("contacts", "rows", "data", "results"):
        rows = page.get(key)
        if isinstance(rows, list):
            return rows
    return []


def stage_message(campaign):
    """The newest human-readable progress line, or the bare status."""
    progress = campaign.get("progress")
    if isinstance(progress, list) and progress:
        last = progress[-1]
        if isinstance(last, dict):
            return last.get("message") or last.get("stage") or campaign.get("status", "")
    return campaign.get("status", "")


def dossier_of(contact):
    """The dossier object, from wherever this envelope keeps it."""
    d = _dig(contact, "dossier")
    if isinstance(d, dict):
        return d
    # The flat envelope carries a summary string rather than an object.
    summary = _dig(contact, "dossier_summary")
    if summary:
        return {"summary": summary}
    return {}


def dossier_state(contact):
    """One of five states. Never a boolean: 'no dossier' has four different causes."""
    if dossier_of(contact):
        return ENRICHED
    status = (_dig(contact, "enrichment_status", "enrichment.status") or "").lower()
    if status == "queued":
        return QUEUED
    if status == "failed":
        return FAILED_ENRICH
    if status == "enriched":
        # Enrichment ran but no dossier came back — not the same as never having tried.
        return FAILED_ENRICH
    if _dig(contact, "score", "rank") is not None:
        return RANKED_ONLY
    return UNRANKED


def is_deliverable(contact):
    """True when this contact has a dossier worth writing into the customer DB."""
    return dossier_state(contact) == ENRICHED


def join_list(value, sep=" · ", limit=2000):
    """Flatten a list of strings into one text value a text column can hold.

    A list written straight to a scalar field arrives as its Python repr — square brackets
    and quotes — which reads as corruption in the app and matches no filter anybody writes.
    """
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        out = value
    elif isinstance(value, (list, tuple)):
        parts = []
        for v in value:
            if isinstance(v, dict):
                v = v.get("text") or v.get("summary") or v.get("title") or json.dumps(v)
            if v not in (None, ""):
                parts.append(str(v).strip())
        out = sep.join(parts)
    elif isinstance(value, dict):
        out = sep.join(f"{k}: {v}" for k, v in value.items() if v not in (None, ""))
    else:
        out = str(value)
    out = " ".join(out.split())
    return out[:limit]


# Mailbox providers. An address at one of these says nothing about where its owner works, so
# it must never become a company's identity — one upsert on `gmail.com` would merge every
# unrelated attendee into a single fictional company.
FREE_MAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "hotmail.com", "outlook.com",
    "live.com", "msn.com", "aol.com", "icloud.com", "me.com", "mac.com", "proton.me",
    "protonmail.com", "gmx.com", "gmx.net", "mail.com", "zoho.com", "yandex.com",
    "fastmail.com", "hey.com", "qq.com", "163.com", "126.com",
}


def domain_from_email(email):
    """A work email's domain, or '' for a mailbox provider or a non-address.

    Measured: this provider returns NO company domain on any contact — the enrichment block
    carries an email, a phone, a profile URL and an avatar, and nothing else. Without this the
    company half of the write can never happen, and every attendee is written unlinked. The
    address is the only evidence of employer available, and for a work address it is strong."""
    local_at, _, dom = (email or "").partition("@")
    if not local_at or not dom:
        return ""
    d = normalize_domain(dom)
    return "" if d in FREE_MAIL else d


def contact_company_domain(contact):
    """The contact's company domain, if any source in the payload knows it.

    Decides whether a company record can exist at all: a company with no domain has no valid
    upsert key, so its people are written unlinked rather than not at all.
    """
    raw = _dig(
        contact,
        "enrichment.company_domain",
        "company_domain",
        "enrichment.domain",
        "company.domain",
        "company_website",
        "enrichment.company_website",
    )
    given = normalize_domain(raw)
    if given:
        return given
    # Nothing supplied one. Fall back to the work email's domain.
    return domain_from_email(_dig(contact, "email", "enrichment.email", default=""))


def normalize_domain(raw):
    """Bare, lowercased host. Returns '' for anything that is not a domain."""
    if not raw or not isinstance(raw, str):
        return ""
    v = raw.strip().lower()
    if "://" in v:
        v = v.split("://", 1)[1]
    v = v.split("/")[0].split("?")[0].split("@")[-1]
    if v.startswith("www."):
        v = v[4:]
    if "." not in v or " " in v or not v.replace(".", "").replace("-", "").isalnum():
        return ""
    return v


def normalize_linkedin(raw):
    """A linkedin.com URL, or ''. The match key is checked for being a LinkedIn URL, not
    merely for being non-empty, and a near-miss fails with wording that reads as 'blank'."""
    if not raw or not isinstance(raw, str):
        return ""
    v = raw.strip()
    if not v:
        return ""
    if v.startswith("//"):
        v = "https:" + v
    elif "://" not in v:
        v = "https://" + v
    host = v.split("://", 1)[1].split("/")[0].lower()
    if not (host == "linkedin.com" or host.endswith(".linkedin.com")):
        return ""
    return v.split("?")[0].rstrip("/")


def normalize_email(raw):
    """A parseable address, or ''."""
    if not raw or not isinstance(raw, str):
        return ""
    v = raw.strip().lower()
    if v.count("@") != 1:
        return ""
    local, _, domain = v.partition("@")
    if not local or not normalize_domain(domain):
        return ""
    return v


def split_name(full):
    """First and last from a single name field, without inventing either."""
    parts = [p for p in (full or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def shape_contact(contact, campaign_ctx):
    """Reshape one API contact into the flat values a record write needs.

    `campaign_ctx` carries what the contact does not know about itself: which campaign it
    came from, which conference, and when this run happened.
    """
    dossier = dossier_of(contact)
    name = _dig(contact, "name", "full_name", default="") or ""
    first, last = split_name(name)
    email = normalize_email(_dig(contact, "email"))
    linkedin = normalize_linkedin(_dig(contact, "linkedin_url", "linkedin"))
    domain = contact_company_domain(contact)
    state = dossier_state(contact)

    return {
        "lanyard_contact_id": str(_dig(contact, "id", "contact_id", default="") or ""),
        "name": name,
        "first_name": first,
        "last_name": last,
        "title": _dig(contact, "title", default="") or "",
        "email": email,
        "linkedin_url": linkedin,
        "phone": (_dig(contact, "phone", default="") or "").strip(),
        "company_name": _dig(contact, "company", "company_name", default="") or "",
        "company_domain": domain,
        "dossier_state": state,
        # Every one of these scans the name the service ACTUALLY uses first and the
        # documented name second. Measured against a live campaign, the published dossier
        # shape shares exactly one key with the real one — `buying_signals` — so a client
        # built from the documentation alone writes a row of empty columns and reports
        # success.
        # Top-level `tier` now, with the dossier and flat-format names kept as fallbacks.
        # It used to exist ONLY in the flat response, which meant fetching every contact a
        # second time and joining the two on identity — the flat rows carry no id. That join
        # was the least sound thing in this client and it is gone.
        "tier": _dig(contact, "tier", "dossier.tier", default="") or "",
        "score": _dig(contact, "score", "dossier.fit_score"),
        "rank": _dig(contact, "rank"),
        "attendance_confidence": _dig(
            contact, "attendance.confidence", "dossier.attending_status",
            "attendance_confidence", "confidence", default="") or "",
        "attendance_evidence": join_list(_dig(
            contact, "attendance.evidence", "why_attending", "source_title", default="")),
        "attendance_source": _dig(
            contact, "attendance.source_url", "source_url", default="") or "",
        "attendance_year": _dig(
            contact, "attendance.year_context", "year_context", default="") or "",
        "score_rationale": join_list(_dig(
            contact, "dossier.fit_rationale", "score_rationale", default="")),
        "headline": join_list(_dig(dossier, "headline", default="")),
        "dossier_summary": join_list(_dig(dossier, "contact_summary", "summary", default="")),
        "company_summary": join_list(_dig(dossier, "company_summary", "company_history",
                                          default="")),
        "buying_signals": join_list(dossier.get("buying_signals")),
        "openers": join_list(_dig(dossier, "conversation_openers", "openers", default="")),
        "value_prop": join_list(_dig(dossier, "value_prop_framing", "value_prop", default="")),
        "conference_name": campaign_ctx.get("conference_name", ""),
        "conference_start": campaign_ctx.get("conference_start", ""),
        "conference_location": campaign_ctx.get("conference_location", ""),
        "campaign_id": campaign_ctx.get("campaign_id", ""),
        "written_at": campaign_ctx.get("written_at", ""),
    }


def campaign_context(campaign, written_at):
    """The per-campaign facts every contact record carries, read defensively."""
    conf = campaign.get("conference") or {}
    if isinstance(conf, str):
        conf = {"name": conf}
    return {
        "campaign_id": _dig(campaign, "campaign_id", "id", default="") or "",
        "conference_name": _dig(conf, "name", "candidate.name", default="") or "",
        "conference_start": _dig(conf, "start_date", "candidate.start_date", default="") or "",
        "conference_location": _dig(conf, "location", "candidate.location", default="") or "",
        "written_at": written_at,
    }


def free_allowance(campaign, create_response=None, account=None):
    """What the run is actually allowed to enrich, and whether a cap bit.

    Three sources may carry this and none is guaranteed: the create response, the campaign
    itself, and the account. Report what was found and say plainly when nothing said.
    """
    out = {"allowed": None, "requested": None, "capped": None, "source": "not_reported"}
    for src, label in ((create_response, "create"), (campaign, "campaign")):
        if not isinstance(src, dict):
            continue
        block = src.get("enrichment")
        if isinstance(block, dict):
            out.update(
                allowed=block.get("allowed"),
                requested=block.get("requested"),
                capped=block.get("free_limit_applied"),
                source=label,
            )
            return out
    counts = (campaign or {}).get("counts") or {}
    if counts:
        out.update(
            allowed=counts.get("enriched"),
            requested=counts.get("requested_enrichment"),
            capped=(
                counts.get("requested_enrichment") is not None
                and counts.get("enriched") is not None
                and counts["enriched"] < counts["requested_enrichment"]
            ),
            source="counts",
        )
    if isinstance(account, dict) and out["allowed"] is None:
        out["allowed"] = account.get("free_dossiers_per_campaign")
        out["source"] = "account"
    return out


def locked_summary(campaign, contacts):
    """How many ranked contacts are still without a dossier.

    Two sources, and they can answer different questions. When the campaign publishes its own
    `locked` block it carries a breakdown BY TIER, which is the useful one.

    When it does not, the breakdown is counted here — and it deliberately breaks down by
    STATE, not by tier. **A locked contact has no tier to report.** Tier is written into the
    dossier, and a locked contact is precisely one whose dossier was never written, so
    bucketing the counted fallback by tier would put every single locked contact into one
    meaningless "unranked" pile and present it as a tier breakdown. What IS knowable locally
    is why each one has no dossier, which is a real answer to a slightly different question.

    `breakdown_by` says which of the two you are looking at, so a caller never presents one
    as the other.
    """
    block = campaign.get("locked") if isinstance(campaign, dict) else None
    if isinstance(block, dict) and block.get("total") is not None:
        return {
            "total": block.get("total"),
            "breakdown_by": "tier",
            "breakdown": {t.get("tier"): t.get("count")
                          for t in block.get("tiers") or [] if isinstance(t, dict)},
            "credits_per_contact": block.get("credits_per_contact"),
            "unlock_url": block.get("unlock_url"),
            "source": "campaign",
        }
    states = {}
    total = 0
    for c in contacts:
        state = dossier_state(c)
        if state in (ENRICHED, UNRANKED):
            continue
        total += 1
        states[state] = states.get(state, 0) + 1
    return {
        "total": total,
        "breakdown_by": "state",
        "breakdown": states,
        "credits_per_contact": None,
        # Falls back to the campaign's own page, never to `share_url`: that one carries an
        # access token, and a fallback should not quietly widen who can see this.
        "unlock_url": (_dig(campaign, "locked.unlock_url", default="")
                       or campaign_url(_dig(campaign, "campaign_id", "id", default=""))),
        "source": "counted",
    }


YEAR_ORDER = ("this_year", "last_year", "prior", "unknown")


def attendance_pool(campaign):
    """The whole candidate pool broken down by which edition its evidence is about.

    The campaign reports this across everything it found, which is a bigger and more useful
    number than the split across the handful that got dossiers: "found 144, 70 of them
    evidenced against the upcoming edition" says what the search actually turned up, where
    "2 of the 5 we wrote" says more about the free allowance than about the event.

    Report both. Returns an ordered list of (edition, count), or [] when the campaign does
    not carry the breakdown — older campaigns do not.
    """
    counts = (campaign or {}).get("counts") or {}
    block = counts.get("attendance")
    if isinstance(block, dict) and block:
        known = [(k, block[k]) for k in YEAR_ORDER if block.get(k)]
        extra = [(k, v) for k, v in block.items() if k not in YEAR_ORDER and v]
        return known + sorted(extra)
    # The listing row carries only the headline figure; still worth showing.
    if counts.get("this_year") is not None:
        return [("this_year", counts["this_year"])]
    return []


def locked_by_tier(contacts):
    """How many contacts are locked, per tier, best tier first.

    Counted from the contact list rather than the campaign's own block because this has to
    agree exactly with what an unlock would match — the campaign's totals and the contacts
    are two different reads, and offering to buy 12 when 11 are available is a bad surprise.
    """
    order = ["S", "A", "B", "C", "F"]
    counts = {}
    for c in contacts:
        if is_deliverable(c):
            continue
        if dossier_state(c) == UNRANKED:
            continue
        t = (_dig(c, "tier", "dossier.tier", default="") or "").upper()
        if t in order:
            counts[t] = counts.get(t, 0) + 1
    return [(t, counts[t]) for t in order if t in counts]


def recommend_unlock(locked, credits_per_contact=5, credits_available=0,
                     sweet_spot=(5, 25)):
    """Suggest what to unlock, and price every option. Returns (options, recommended index).

    `locked` is the output of `locked_by_tier`. Each option is
    `{label, selection, contacts, credits, affordable}`, where `selection` is the body the
    unlock call wants.

    The recommendation is a heuristic and is labelled as one wherever it is shown. It aims at
    a batch big enough to be worth reviewing and small enough to read in one sitting:

      * S alone when that lands in the sweet spot — the top band is the obvious first buy;
      * S plus A when S alone is too thin to be worth a trip;
      * a capped `top N` when S alone is already more than anybody reads at once.

    It never recommends something the balance cannot cover when the balance is non-zero. With
    a zero balance every option is unaffordable, so the cheapest sensible one is recommended
    and the caller's job becomes handing over a payment link rather than asking for a yes.
    """
    lo, hi = sweet_spot
    options = []

    def add(label, selection, n):
        if n <= 0:
            return
        credits = n * credits_per_contact
        options.append({"label": label, "selection": selection, "contacts": n,
                        "credits": credits,
                        "affordable": credits_available >= credits})

    by = dict(locked)
    s_n = by.get("S", 0)
    a_n = by.get("A", 0)

    add("tier S", {"tier": "S"}, s_n)
    # Only when there IS an A tier. Otherwise "tiers S and A" is the same contacts at the
    # same price under a second name, and offering a person two identical options priced
    # identically reads as a bug in the thing quoting them.
    if a_n:
        add("tiers S and A", {"tiers": ["S", "A"]}, s_n + a_n)
    if s_n + a_n > hi:
        add("the top %d" % hi, {"top": hi}, min(hi, s_n + a_n))
    total = sum(n for _t, n in locked)
    if total and total != s_n and total != s_n + a_n:
        add("everything locked", {"tiers": [t for t, _n in locked]}, total)

    if not options:
        return [], None

    def pick():
        # S alone, when it is a sensible size.
        for i, o in enumerate(options):
            if o["label"] == "tier S" and lo <= o["contacts"] <= hi:
                return i
        # S too thin — add A.
        if s_n < lo:
            for i, o in enumerate(options):
                if o["label"] == "tiers S and A" and o["contacts"] >= lo:
                    return i
        # S already bigger than anybody reads at once — cap it.
        for i, o in enumerate(options):
            if o["label"].startswith("the top"):
                return i
        return 0

    rec = pick()
    if credits_available > 0 and not options[rec]["affordable"]:
        # Prefer the largest option the balance actually covers.
        affordable = [i for i, o in enumerate(options) if o["affordable"]]
        if affordable:
            rec = max(affordable, key=lambda i: options[i]["contacts"])
    return options, rec


def delta(contacts, settled_ids):
    """Which contacts this run should write, and why the rest are being skipped.

    This is the whole top-up mechanism. Nothing tells us what a person unlocked in the
    browser, so 'what is new' is recomputed every time: everything that now has a dossier,
    minus everything already settled in the ledger.
    """
    todo, skipped = [], {}
    for c in contacts:
        cid = str(_dig(c, "id", "contact_id", default="") or "")
        state = dossier_state(c)
        if state != ENRICHED:
            skipped[state] = skipped.get(state, 0) + 1
            continue
        if cid and cid in settled_ids:
            skipped["already_written"] = skipped.get("already_written", 0) + 1
            continue
        todo.append(c)
    return todo, skipped
