"""Offline checks. No platform, no network, no credentials, no key of any kind.

Run: `python3 test_offline.py`

Everything that decides what gets written is pure, so all of it is checked here against a
fixture carrying deliberate defects — the same defects a real conference produces: a contact
with no usable identifier, a score that is a range rather than a number, a list where a
string is expected, a profile URL pointing at the wrong site, a company with no domain.

A green run here does not prove the tables build. It proves that the layer deciding WHAT to
write and WHERE to route it behaves, which is the layer that otherwise fails one row at a
time in production, silently.
"""

import os.path
import sys

# Run it from anywhere: the scripts live next to this file, not in the shell's directory.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import audience_lib as A
import lanyard_lib as L

PASS = FAIL = 0
FAILURES = []


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{label}\n     got:  {got!r}\n     want: {want!r}")


def truthy(label, got):
    check(label, bool(got), True)


# --------------------------------------------------------------------- the fixture
#
# Nine attendees. Every one carries a defect that has to be handled without losing the
# contact, except the two that genuinely cannot be written.

CONTACTS = [
    {   # 0 — the clean one. Everything present, dossier complete, company has a domain.
        "id": "c-001", "name": "Dana Whitfield", "title": "VP Revenue Operations",
        "company": "Northbeam", "linkedin_url": "https://linkedin.com/in/danawhitfield/",
        "email": "Dana@Northbeam.EXAMPLE", "phone": "", "source": "web", "confidence": "confirmed",
        "score": 92, "rank": 1, "is_top": True, "enrichment_status": "enriched",
        "attendance": {"confidence": "confirmed", "evidence": "Listed as a panelist on the agenda page.",
                       "source_url": "https://example.test/agenda"},
        "score_rationale": "Exact ICP title at a mid-market SaaS already using gifting.",
        "enrichment": {"company_domain": "https://www.northbeam.example/careers"},
        # THE REAL SHAPE, copied from a live campaign. It shares exactly one key
        # (`buying_signals`) with the shape the API's own documentation describes.
        "dossier": {
            "headline": "Driving post-purchase loyalty for Northbeam's B2B expansion",
            "contact_summary": "Owns outbound tooling decisions for a 900-person SaaS.",
            "company_summary": "Series D, $120M raised; expanding into B2B.",
            "buying_signals": ["Hiring 4 SDRs", "Posted about AI outbound in July"],
            "conversation_openers": ["Ask about their SDR ramp experiment"],
            "value_prop_framing": "Signal-native sequencing without ripping out their CRM.",
            "fit_rationale": "Exact ICP title at a mid-market SaaS already using gifting.",
            "fit_score": 95,
            "attending_status": "likely",
            "rapport_match": None,
        },
    },
    {   # 1 — score arrives as a RANGE. The silent-write trap in its natural habitat.
        "id": "c-002", "name": "Marcus Oyelaran", "title": "Head of Demand Gen",
        "company": "Kestrel Data", "linkedin_url": "linkedin.com/in/moyelaran",
        "email": "", "score": "1,001-5,000", "rank": 2, "enrichment_status": "enriched",
        "enrichment": {"company_domain": "kestreldata.com"},
        "dossier": {"headline": "Runs paid and lifecycle.", "conversation_openers": []},
    },
    {   # 2 — profile URL points at the company site, not LinkedIn. Must not become a key.
        "id": "c-003", "name": "Priya Raghunathan", "title": "Director of Sales Ops",
        "company": "Vantage Loop", "linkedin_url": "https://vantageloop.example/team/priya",
        "email": "priya@vantageloop.example", "score": 81, "enrichment_status": "enriched",
        "enrichment": {"company_domain": "vantageloop.example"},
        # The DOCUMENTED shape. Kept so the fallback path stays covered — the service may
        # differ by deployment, and a client that reads only one of the two is wrong somewhere.
        "dossier": {"tier": "A", "summary": "Owns the ops tooling budget.",
                    "openers": ["Ask about their renewal"], "value_prop": "Fewer tools."},
    },
    {   # 3 — company has no domain anywhere. Writable, but must go down an UNLINKED lane.
        "id": "c-004", "name": "Tom Vestergaard", "title": "Founder",
        "company": "Stillwater Consulting", "linkedin_url": "https://www.linkedin.com/in/tvest?trk=x",
        "email": "", "score": 74, "enrichment_status": "enriched",
        "dossier": {"contact_summary": "Boutique consultancy, two-person team."},
    },
    {   # 4 — no LinkedIn, malformed email. Nothing can match on this person.
        "id": "c-005", "name": "Unknown Delegate", "title": "", "company": "",
        "linkedin_url": "", "email": "bad@@example", "score": 40,
        "enrichment_status": "enriched", "dossier": {"headline": "Thin."},
    },
    {   # 5 — ranked, never enriched. This is what the free allowance leaves behind.
        "id": "c-006", "name": "Alina Kowalczyk", "title": "CRO", "company": "Brightpath",
        "linkedin_url": "https://linkedin.com/in/akowalczyk", "email": "alina@brightpath.example",
        "score": 88, "rank": 3, "enrichment_status": "none", "dossier": None, "tier": "A",
    },
    {   # 6 — enrichment still running.
        "id": "c-007", "name": "Sam Iheanacho", "company": "Ridgeline",
        "linkedin_url": "https://linkedin.com/in/siheanacho", "score": 70,
        "enrichment_status": "queued", "dossier": None,
    },
    {   # 7 — enrichment ran and produced nothing. Retrying costs and repeats.
        "id": "c-008", "name": "Rhea Malhotra", "company": "Foldspace",
        "linkedin_url": "https://linkedin.com/in/rmalhotra", "score": 66,
        "enrichment_status": "failed", "dossier": None,
    },
    {   # 8 — discovered, not yet scored.
        "id": "c-009", "name": "Nobody Ranked", "enrichment_status": "none", "dossier": None,
    },
]

CAMPAIGN = {
    "campaign_id": "cmp-123", "status": "complete",
    "share_url": "https://example.test/campaign/cmp-123",
    "progress": [{"at": "2026-09-16T10:00:00Z", "stage": "complete", "message": "Done"}],
    "counts": {"attendees": 9, "enriched": 5, "dossiers": 5, "requested_enrichment": 25},
    "conference": {"name": "INBOUND 2026", "start_date": "2026-09-03", "location": "San Francisco, CA"},
}

CTX = L.campaign_context(CAMPAIGN, "2026-09-16")
SHAPED = [L.shape_contact(c, CTX) for c in CONTACTS]


# ------------------------------------------------------------------ envelope reading

check("envelope: default key", len(L.envelope_rows({"contacts": CONTACTS})), 9)
check("envelope: flat key", len(L.envelope_rows({"rows": CONTACTS})), 9)
check("envelope: neither key", L.envelope_rows({"total": 9}), [])
check("envelope: not a dict", L.envelope_rows(None), [])
check("stage message", L.stage_message(CAMPAIGN), "Done")


# ---------------------------------------------------------------- dossier states

check("state: complete dossier", L.dossier_state(CONTACTS[0]), L.ENRICHED)
check("state: ranked only", L.dossier_state(CONTACTS[5]), L.RANKED_ONLY)
check("state: queued", L.dossier_state(CONTACTS[6]), L.QUEUED)
check("state: failed", L.dossier_state(CONTACTS[7]), L.FAILED_ENRICH)
check("state: unranked", L.dossier_state(CONTACTS[8]), L.UNRANKED)
check("deliverable count", sum(1 for c in CONTACTS if L.is_deliverable(c)), 5)
# Five distinct states, not one boolean. Collapsing these makes every rate meaningless.
check("state: all five reachable",
      sorted({L.dossier_state(c) for c in CONTACTS}),
      sorted([L.ENRICHED, L.RANKED_ONLY, L.QUEUED, L.FAILED_ENRICH, L.UNRANKED]))


# ------------------------------------------------------------------- normalisation

check("domain: strips scheme, www and path", L.normalize_domain("https://www.northbeam.example/careers"), "northbeam.example")
check("domain: bare passes", L.normalize_domain("kestreldata.com"), "kestreldata.com")
check("domain: junk rejected", L.normalize_domain("not a domain"), "")
check("domain: empty rejected", L.normalize_domain(None), "")
check("linkedin: adds scheme", L.normalize_linkedin("linkedin.com/in/moyelaran"), "https://linkedin.com/in/moyelaran")
check("linkedin: strips query and slash", L.normalize_linkedin("https://www.linkedin.com/in/tvest?trk=x"), "https://www.linkedin.com/in/tvest")
check("linkedin: wrong host rejected", L.normalize_linkedin("https://vantageloop.example/team/priya"), "")
check("email: lowercased", L.normalize_email("Dana@Northbeam.EXAMPLE"), "dana@northbeam.example")
check("email: double-at rejected", L.normalize_email("bad@@example"), "")
check("email: no tld rejected", L.normalize_email("x@localhost"), "")
check("name: two parts", L.split_name("Dana Whitfield"), ("Dana", "Whitfield"))
check("name: three parts keeps last", L.split_name("Priya Devi Raghunathan"), ("Priya", "Raghunathan"))
check("name: one part", L.split_name("Cher"), ("Cher", ""))
check("name: empty", L.split_name(""), ("", ""))


# --------------------------------------------------------------------- flattening

check("join: list becomes prose", L.join_list(["Hiring 4 SDRs", "Posted about AI outbound in July"]),
      "Hiring 4 SDRs · Posted about AI outbound in July")
check("join: empty list is blank", L.join_list([]), "")
check("join: string passes through", L.join_list("already text"), "already text")
check("join: whitespace collapsed", L.join_list("two\n\nlines   here"), "two lines here")
# The defect this prevents: a raw list reaching a scalar field arrives as its repr.
truthy("join: no brackets survive", "[" not in L.join_list(["a", "b"]))


# ------------------------------------------------------------------------ shaping

s0 = SHAPED[0]
check("shape: company domain cleaned", s0["company_domain"], "northbeam.example")
check("shape: headline lifted from the real key", s0["headline"],
      "Driving post-purchase loyalty for Northbeam's B2B expansion")
check("shape: summary from contact_summary", s0["dossier_summary"],
      "Owns outbound tooling decisions for a 900-person SaaS.")
check("shape: company summary from company_summary", s0["company_summary"],
      "Series D, $120M raised; expanding into B2B.")
check("shape: openers from conversation_openers", s0["openers"], "Ask about their SDR ramp experiment")
check("shape: value prop from value_prop_framing", s0["value_prop"],
      "Signal-native sequencing without ripping out their CRM.")
check("shape: rationale prefers fit_rationale", s0["score_rationale"],
      "Exact ICP title at a mid-market SaaS already using gifting.")
check("shape: attendance source captured", s0["attendance_source"], "https://example.test/agenda")
# Which EDITION the evidence is about. Load-bearing once last year's list can be seeded.
check("shape: attendance year captured", SHAPED[0]["attendance_year"], "")
check("shape: year read when present",
      L.shape_contact({"attendance": {"year_context": "this_year"}}, CTX)["attendance_year"],
      "this_year")
check("plan: the year has a column",
      [n for n, _t, _s in A.PEOPLE_FIELDS if n == "Attendance year"], ["Attendance year"])
# And the DOCUMENTED names still resolve, for a deployment that uses them.
check("shape: documented `summary` still read", SHAPED[2]["dossier_summary"], "Owns the ops tooling budget.")
check("shape: documented `openers` still read", SHAPED[2]["openers"], "Ask about their renewal")
check("shape: documented `value_prop` still read", SHAPED[2]["value_prop"], "Fewer tools.")
# Tier now arrives on the contact itself. It used to exist ONLY in the flat response, which
# meant fetching every contact twice and joining on identity because the flat rows carry no
# id — the least sound thing in this client, and now deleted rather than patched.
check("shape: tier read from the contact", SHAPED[5]["tier"], "A")
check("shape: dossier tier still works as a fallback", SHAPED[2]["tier"], "A")
check("shape: no tier at all is blank, not None", SHAPED[8]["tier"], "")
check("plan: the tier column is fed from the contact",
      [n for n, _t, _s in A.PEOPLE_FIELDS if n == "Attendee tier"], ["Attendee tier"])
check("the identity-join workaround is gone", hasattr(L, "tier_map"), False)
check("shape: signals joined", s0["buying_signals"], "Hiring 4 SDRs · Posted about AI outbound in July")
check("shape: evidence from nested attendance", s0["attendance_evidence"], "Listed as a panelist on the agenda page.")
check("shape: campaign id carried", s0["campaign_id"], "cmp-123")
check("shape: conference carried", s0["conference_name"], "INBOUND 2026")
check("shape: names split", (s0["first_name"], s0["last_name"]), ("Dana", "Whitfield"))
check("shape: bad linkedin dropped", SHAPED[2]["linkedin_url"], "")
check("shape: bad email dropped", SHAPED[4]["email"], "")
check("shape: missing domain is blank not None", SHAPED[3]["company_domain"], "")
# Measured: this provider returns NO company domain on any contact. Without deriving one from
# the work email, the company half of the write never happens and every attendee is unlinked.
check("domain: derived from a work email", L.domain_from_email("dana.reeve@northbeam.example"), "northbeam.example")
# A mailbox provider must NEVER become a company — one upsert on gmail.com would merge every
# unrelated attendee into a single fictional company.
check("domain: gmail refused", L.domain_from_email("example@gmail.com"), "")
check("domain: outlook refused", L.domain_from_email("example@outlook.com"), "")
check("domain: icloud refused", L.domain_from_email("someone@icloud.com"), "")
check("domain: junk refused", L.domain_from_email("nope"), "")
check("domain: empty refused", L.domain_from_email(""), "")
check("domain: a supplied domain still wins over the email",
      L.contact_company_domain({"enrichment": {"company_domain": "given.com"}, "email": "x@other.com"}),
      "given.com")
check("domain: the email is used only when nothing supplied one",
      L.contact_company_domain({"email": "x@other.com"}), "other.com")
check("domain: a free-mail contact stays unlinked",
      L.contact_company_domain({"email": "example@gmail.com"}), "")
# Every key is guaranteed present even when blank — blank is a value, not an absence.
for i, s in enumerate(SHAPED):
    missing = [k for k in SHAPED[0] if k not in s]
    check(f"shape: contact {i} has every key", missing, [])


# ----------------------------------------------------------------- value validation

check("number: integer ok", A.validate_value(92, "number"), (True, 92, None))
check("number: numeric string ok", A.validate_value("92", "number"), (True, 92, None))
check("number: comma thousands ok", A.validate_value("1200.50", "number"), (True, 1200.5, None))
check("number: currency stripped", A.validate_value("$1,200.50", "number"), (True, 1200.5, None))
# The measured silent-write case: accepted by the platform, invisible to every filter.
check("number: RANGE rejected", A.validate_value("1,001-5,000", "number"), (False, None, "not_a_number"))
check("number: prose rejected", A.validate_value("about ninety", "number"), (False, None, "not_a_number"))
check("number: bool rejected", A.validate_value(True, "number"), (False, None, "boolean_into_number"))
check("date: iso ok", A.validate_value("2026-09-03", "date"), (True, "2026-09-03", None))
check("date: iso timestamp ok", A.validate_value("2026-09-03T10:00:00Z", "date")[0], True)
check("date: QUARTER rejected", A.validate_value("Q3 2017", "date"), (False, None, "not_an_iso_date"))
check("date: us order rejected", A.validate_value("09/03/2026", "date"), (False, None, "not_an_iso_date"))
check("email type: ok", A.validate_value("a@b.com", "email"), (True, "a@b.com", None))
check("email type: rejected", A.validate_value("nope", "email"), (False, None, "not_an_email"))
check("url type: bare gets scheme", A.validate_value("northbeam.example", "url"), (True, "https://northbeam.example", None))
check("url type: junk rejected", A.validate_value("no dots here", "url"), (False, None, "not_a_url"))
check("text: anything", A.validate_value("1,001-5,000", "text"), (True, "1,001-5,000", None))
check("empty is not an error", A.validate_value("", "text"), (False, None, "empty"))
check("none is not an error", A.validate_value(None, "number"), (False, None, "empty"))
# A boolean field cannot be coverage-checked, so the plan must never contain one.
check("boolean refused outright", A.validate_value(True, "boolean")[0], False)
check("plan contains no boolean", [t for _n, t, _s in A.PEOPLE_FIELDS + A.COMPANY_FIELDS if t == "boolean"], [])


# ------------------------------------------------------------------------ routing

check("route: linkedin preferred over email", A.route_for(SHAPED[0])[0], A.ROUTE_LINKED_LINKEDIN)
check("route: falls back to email when profile is wrong host", A.route_for(SHAPED[2])[0], A.ROUTE_LINKED_EMAIL)
check("route: no domain means unlinked", A.route_for(SHAPED[3])[0], A.ROUTE_UNLINKED_LINKEDIN)
check("route: no key at all", A.route_for(SHAPED[4])[0], A.ROUTE_UNWRITABLE)
check("route: linking can be turned off", A.route_for(SHAPED[0], link_company=False)[0], A.ROUTE_UNLINKED_LINKEDIN)
check("route: unwritable carries a reason", bool(A.route_for(SHAPED[4])[1]), True)
check("match key for email lane", A.route_match_key(A.ROUTE_LINKED_EMAIL), "email")
check("match key for linkedin lane", A.route_match_key(A.ROUTE_UNLINKED_LINKEDIN), "linkedin_url")
check("linked lanes identified", [A.route_is_linked(r) for r in
      (A.ROUTE_LINKED_EMAIL, A.ROUTE_LINKED_LINKEDIN, A.ROUTE_UNLINKED_EMAIL, A.ROUTE_UNLINKED_LINKEDIN)],
      [True, True, False, False])

deliverable = [s for s, c in zip(SHAPED, CONTACTS) if L.is_deliverable(c)]
by_route, unwritable = A.plan_writes(deliverable)
check("plan: one contact unwritable", len(unwritable), 1)
check("plan: four writable", sum(len(v) for v in by_route.values()), 4)
check("plan: lanes used", sorted(by_route), sorted([A.ROUTE_LINKED_LINKEDIN, A.ROUTE_LINKED_EMAIL, A.ROUTE_UNLINKED_LINKEDIN]))


# ------------------------------------------------------------------ the top-up delta

todo, skipped = L.delta(CONTACTS, set())
check("delta: first run takes every dossier", len(todo), 5)
check("delta: ranked-only counted separately", skipped.get(L.RANKED_ONLY), 1)
check("delta: queued counted separately", skipped.get(L.QUEUED), 1)
check("delta: failed counted separately", skipped.get(L.FAILED_ENRICH), 1)
check("delta: unranked counted separately", skipped.get(L.UNRANKED), 1)

settled = {"c-001", "c-002", "c-003", "c-004", "c-005"}
todo2, skipped2 = L.delta(CONTACTS, settled)
check("delta: second run with nothing unlocked writes nothing", len(todo2), 0)
check("delta: and says why", skipped2.get("already_written"), 5)

# The top-up itself: someone unlocks two more in the browser. Nothing tells us — the same
# call simply returns dossiers where there were none, and only the new ones are written.
unlocked = [dict(c) for c in CONTACTS]
unlocked[5]["dossier"] = {"tier": "S", "summary": "Now unlocked."}
unlocked[5]["enrichment_status"] = "enriched"
unlocked[7]["dossier"] = {"tier": "B", "summary": "Also unlocked."}
unlocked[7]["enrichment_status"] = "enriched"
todo3, skipped3 = L.delta(unlocked, settled)
check("top-up: only the newly unlocked", sorted(c["id"] for c in todo3), ["c-006", "c-008"])
check("top-up: the already-written are not rewritten", skipped3.get("already_written"), 5)

# A lost ledger must cost redundant writes, never duplicates — the write is an upsert.
todo4, _ = L.delta(unlocked, set())
check("torn ledger: re-derives the full set, no duplicates in it", len(todo4), len({c["id"] for c in todo4}))
check("torn ledger: set is everything with a dossier", len(todo4), 7)


# ------------------------------------------------------ what the run has to disclose

allowance = L.free_allowance(CAMPAIGN)
check("allowance: falls back to counts when no block is published", allowance["source"], "counts")
check("allowance: a cap is detected from the counts", allowance["capped"], True)
check("allowance: reports what was allowed", allowance["allowed"], 5)
check("allowance: and what was asked for", allowance["requested"], 25)

with_block = dict(CAMPAIGN)
check("allowance: prefers a published block",
      L.free_allowance(with_block, {"enrichment": {"requested": 25, "allowed": 5, "free_limit_applied": True}})["source"],
      "create")
check("allowance: says so plainly when nothing reports it",
      L.free_allowance({}, {})["source"], "not_reported")

locked = L.locked_summary(CAMPAIGN, CONTACTS)
check("locked: counted from the contacts when no block exists", locked["source"], "counted")
check("locked: unranked are not counted as locked", locked["total"], 3)
check("locked: credits per contact unknown is None, not zero", locked["credits_per_contact"], None)
# A locked contact has NO TIER — tier lives in the dossier, and a locked contact is exactly
# one whose dossier was never written. So the counted fallback breaks down by state, and says
# so, rather than presenting one meaningless "unranked" pile as a tier breakdown.
check("locked: counted fallback breaks down by state", locked["breakdown_by"], "state")
check("locked: and the states are the real ones", locked["breakdown"],
      {L.RANKED_ONLY: 1, L.QUEUED: 1, L.FAILED_ENRICH: 1})
check("locked: no tier key is invented", "unranked" in locked["breakdown"], False)

locked_pub = L.locked_summary(
    {"locked": {"total": 161, "tiers": [{"tier": "S", "count": 4}], "credits_per_contact": 5,
                "unlock_url": "https://example.test/u"}}, CONTACTS)
check("locked: prefers a published block", locked_pub["total"], 161)
check("locked: a published block IS by tier", locked_pub["breakdown_by"], "tier")
check("locked: tiers read from the block", locked_pub["breakdown"], {"S": 4})


# ---------------------------------------------------------- the SQL the writer sends
#
# Everything sent to the customer DB is generated here, so it is checked here: the quoting
# (the trust boundary — dossier text is third-party), the table shape, and the upsert.

import json         # noqa: E402
import os           # noqa: E402
import tempfile     # noqa: E402

import conference_lib as C           # noqa: E402
import drive_load as D                # noqa: E402

check("sql: NULL for None", C.sql_literal(None), "NULL")
check("sql: a quote is doubled", C.sql_literal("O'Brien"), "'O''Brien'")
check("sql: an injection attempt stays inside the literal",
      C.sql_literal("x'); DROP TABLE storage.conference_attendees; --"),
      "'x''); DROP TABLE storage.conference_attendees; --'")
# standard_conforming_strings = on (verified): a backslash is an ordinary character, so it is
# NOT escaped — escaping it would double it in the stored text.
check("sql: a backslash is left alone", C.sql_literal("a\\'b"), "'a\\''b'")
check("sql: numbers are bare", (C.sql_literal(92), C.sql_literal(4.5)), ("92", "4.5"))
for bad in ("a\x00b", float("nan"), float("inf"), True):
    try:
        C.sql_literal(bad)
        check("sql: refuses %r" % (bad,), "accepted", "ValueError")
    except ValueError:
        check("sql: refuses %r" % (bad,), "ValueError", "ValueError")

DDL = C.ddl(C.ATTENDEES)
check("ddl: idempotent create", DDL[0].startswith("CREATE TABLE IF NOT EXISTS storage.conference_attendees"), True)
check("ddl: keyed on campaign and person", "PRIMARY KEY (campaign_id, person_key)" in DDL[0], True)
check("ddl: score is numeric", "score numeric" in DDL[0], True)
check("ddl: start date is a date", "conference_start date" in DDL[0], True)
check("ddl: every column can be added later",
      len(DDL) - 1, len(C.people_columns()))
check("ddl: no column twice", len(C.people_columns()), len({c for c, _ in C.people_columns()}))
check("ddl: companies keyed on domain", "PRIMARY KEY (domain)" in C.ddl(C.COMPANIES)[0], True)
check("ddl: writes only to storage", all(t.startswith("storage.") for t in C.TABLES), True)
try:
    C._ident("x; drop")
    check("ddl: a bad identifier is refused", "accepted", "ValueError")
except ValueError:
    check("ddl: a bad identifier is refused", "ValueError", "ValueError")

UP = C.upsert_sql(C.ATTENDEES, [{"campaign_id": "k1", "person_key": "p1", "title": "CRO"}])
check("upsert: conflicts on the key", "ON CONFLICT (campaign_id, person_key) DO UPDATE" in UP, True)
# A None must never clear what an earlier write filled — that is what COALESCE is for.
check("upsert: a blank keeps the existing value", "title = COALESCE(EXCLUDED.title, t.title)" in UP, True)
check("upsert: the key is not overwritten", "person_key = COALESCE" in UP, False)
check("upsert: returns the key as evidence", UP.rstrip().endswith("RETURNING campaign_id, person_key"), True)
check("upsert: absent values are NULL", "NULL" in UP, True)


# ------------------------------------------------------------- shaping a write row

TYPES = {C.ATTENDEES: {c: t for c, t in C.people_columns()},
         C.COMPANIES: {c: t for c, t in C.company_columns()}}

p0, c0, d0 = D.rows_for(SHAPED[0], A.ROUTE_LINKED_LINKEDIN, TYPES)
check("row: LinkedIn is the person key", p0["person_key"], "https://linkedin.com/in/danawhitfield")
check("row: match key recorded", p0["match_key"], "linkedin_url")
check("row: domain is the company link", p0["company_domain"], "northbeam.example")
check("row: score is a number", p0["score"], 92)
check("row: no empty strings anywhere", [k for k, v in p0.items() if v == ""], [])
check("row: nothing dropped from the clean one", d0, {})
check("row: a company row comes with a linked lane", c0["domain"], "northbeam.example")
check("row: the company is flagged as attending", c0["attending_flag"], "yes")
check("row: every column is one the table has", [k for k in p0 if k not in TYPES[C.ATTENDEES]], [])

p1, _c1, d1 = D.rows_for(SHAPED[1], A.ROUTE_LINKED_LINKEDIN, TYPES)
check("row: the range score is not sent", p1["score"], None)
check("row: and named as a drop", d1.get("Attendee score"), "not_a_number")

p3, c3, _ = D.rows_for(SHAPED[3], A.ROUTE_UNLINKED_LINKEDIN, TYPES)
check("row: unlinked lane carries no company", (p3["company_domain"], c3), (None, None))

pe, _, _ = D.rows_for({"email": "A@B.example", "campaign_id": "k"}, A.ROUTE_UNLINKED_EMAIL, TYPES)
check("row: email is the fallback key, lower-cased", pe["person_key"], "email:a@b.example")

# A column somebody retyped to text by hand is respected: the number is kept as text.
retyped = {C.ATTENDEES: dict(TYPES[C.ATTENDEES], score="text"), C.COMPANIES: TYPES[C.COMPANIES]}
pr, _, dr = D.rows_for(SHAPED[1], A.ROUTE_LINKED_LINKEDIN, retyped)
check("row: validates against the column's real type", (pr["score"] is not None, dr.get("Attendee score")), (True, None))

# Adoption: what exists is adopted, what is missing is created, a mismatch is named.
EXIST = C.existing_types([
    {"table_name": "conference_attendees", "column_name": "campaign_id", "data_type": "text"},
    {"table_name": "conference_attendees", "column_name": "score", "data_type": "text"},
    {"table_name": "conference_attendees", "column_name": "rank", "data_type": "integer"},
])
cr, ad, mm = C.column_plan(C.ATTENDEES, EXIST)
check("adopt: existing columns are adopted", sorted(ad), ["campaign_id", "rank"])
check("adopt: a type mismatch is reported, not recreated", mm, [("score", "text", "number")])
check("adopt: the rest would be created", len(cr), len(C.people_columns()) - 3)
check("adopt: a table that does not exist creates everything",
      len(C.column_plan(C.COMPANIES, EXIST)[0]), len(C.company_columns()))

check("settle: write failure is not spelled like the dossier state",
      D.WRITE_FAILED == L.FAILED_ENRICH, False)


# ------------------------------------------------------------------- the ledger

tmpdir = tempfile.mkdtemp()
led = D.Ledger(os.path.join(tmpdir, "ledger.jsonl"))
check("ledger: empty to start", led.settled_ids(), set())
led.append(contact_id="c-001", verdict=D.SETTLED, name="Dana")
led.append(contact_id="c-002", verdict=D.WRITE_FAILED, name="Marcus", error="boom")
led.append(contact_id="c-003", verdict=D.UNWRITABLE, name="Nobody")
check("ledger: only a written record settles", led.settled_ids(), {"c-001"})
# A failure must stay in the work set: retrying it untouched is the whole recovery story.
check("ledger: a failure is NOT settled", "c-002" in led.settled_ids(), False)
check("ledger: unwritable is NOT settled either", "c-003" in led.settled_ids(), False)
check("ledger: every line is kept", len(led.rows()), 3)
check("ledger: each line is stamped", all(r.get("at") for r in led.rows()), True)

# An interrupted append leaves a torn final line. Everything before it must still read.
with open(led.path, "a") as fh:
    fh.write('{"contact_id": "c-004", "verdict": "wri')
check("ledger: survives a torn final line", len(led.rows()), 3)
check("ledger: and still reports the settled set", led.settled_ids(), {"c-001"})
led.append(contact_id="c-005", verdict=D.SETTLED, name="Later")
check("ledger: appends after a torn line still count", "c-005" in led.settled_ids(), True)


# ------------------------------------- reading an attendee list the installer already has

import attendee_list as AL   # noqa: E402

# No upload endpoint is involved: up to 500 seeds go inline with the campaign.
check("seeds: the cap is the create call's cap", AL.MAX_SEEDS, 500)

GOOD = "Full Name,Job Title,Company,Email,LinkedIn URL,Phone\n" \
       "Dana Whitfield,VP RevOps,Northbeam,dana@northbeam.example,https://linkedin.com/in/dw,+15551234\n" \
       "Marcus Oyelaran,Head of Demand Gen,Kestrel,,,\n"
seeds, rep = AL.parse_rows(GOOD)
check("seeds: both rows seeded", len(seeds), 2)
check("seeds: every API field mapped", sorted(seeds[0]),
      ["company", "email", "linkedin_url", "name", "phone", "title"])
check("seeds: a sparse row keeps only what it has", sorted(seeds[1]), ["company", "name", "title"])
check("seeds: nothing blank is sent", [k for k, v in seeds[1].items() if not v], [])

# Header spellings vary and a person should not have to care.
for header in ("name", "Name", "FULL NAME", "full_name", "Attendee", "contact name"):
    got, _r = AL.parse_rows(header + "\nDana Whitfield\n")
    check("seeds: header %r understood" % header, got and got[0]["name"], "Dana Whitfield")
# First + last is a real-world shape and must be joined, not dropped.
got, rep2 = AL.parse_rows("First Name,Last Name,Company\nDana,Whitfield,Northbeam\n")
check("seeds: first + last joined", got[0]["name"], "Dana Whitfield")
check("seeds: and the join is reported", rep2["built_name_from_parts"], 1)
# Tab-separated, decided from content not extension.
got, _r = AL.parse_rows("Name\tCompany\nDana Whitfield\tNorthbeam\n")
check("seeds: tabs sniffed", got[0]["company"], "Northbeam")

# A row with no name cannot be seeded, and a silent drop is the failure mode here.
got, rep3 = AL.parse_rows("Name,Company\n,Northbeam\nDana,Kestrel\n")
check("seeds: nameless row dropped", len(got), 1)
check("seeds: and the drop is counted", rep3["dropped_no_name"], 1)
check("seeds: the drop appears in the report text",
      any("DROPPED" in ln for ln in AL.describe(rep3)), True)

# No name column at all is an error with the headers named, not an empty result.
got, rep4 = AL.parse_rows("Company,Email\nNorthbeam,a@b.com\n")
check("seeds: no name column is an error", got, [])
truthy("seeds: the error names what it looked for", "name column" in rep4["error"])
truthy("seeds: and shows the headers it saw", "Company" in rep4["error"])

check("seeds: empty file is an error, not zero rows", AL.parse_rows("")[1].get("error") is not None, True)
check("seeds: a spreadsheet is refused with a fix",
      "CSV" in AL.load_file("/nonexistent/list.xlsx")[1]["error"], True)
check("seeds: a missing file is an error", AL.load_file("/nonexistent/x.csv")[1].get("error") is not None, True)

# Over the cap: truncate, and SAY so. A silently trimmed list looks like a small conference.
BIG = "Name\n" + "".join("Person %d\n" % i for i in range(600))
got, rep5 = AL.parse_rows(BIG)
check("seeds: truncated to the cap", len(got), 500)
check("seeds: and the overflow is counted", rep5["truncated"], 100)
check("seeds: truncation is reported loudly",
      any("TRUNCATED" in ln for ln in AL.describe(rep5)), True)
check("seeds: unmapped columns are listed",
      AL.parse_rows("Name,Badge Colour\nDana,red\n")[1]["unmapped_columns"], ["Badge Colour"])


# ------------------------------------------- what to suggest unlocking, and what it costs

LOCKED = L.locked_by_tier(CONTACTS)
check("locked: counted per tier, best first", LOCKED, [("A", 1)])

def opts(locked, avail=0, per=5):
    o, r = L.recommend_unlock(locked, per, avail)
    return [(x["label"], x["contacts"], x["credits"]) for x in o], (o[r]["label"] if r is not None else None)

# S alone in the sweet spot is the obvious first buy.
o, rec = opts([("S", 12), ("A", 15), ("B", 18)])
check("suggest: S alone when it is a sensible size", rec, "tier S")
check("suggest: every option priced", o[0], ("tier S", 12, 60))
check("suggest: S+A offered too", o[1], ("tiers S and A", 27, 135))
# S too thin to be worth a trip — add A.
check("suggest: S+A when S is thin", opts([("S", 2), ("A", 9)])[1], "tiers S and A")
# S already more than anybody reads at once — cap it.
check("suggest: capped when S is huge", opts([("S", 80)])[1], "the top 25")
check("suggest: nothing locked, nothing offered", L.recommend_unlock([]), ([], None))
# Affordability is stated per option, and a real balance steers the suggestion.
o2, r2 = L.recommend_unlock([("S", 12), ("A", 15)], 5, 60)
check("suggest: affordable flagged", [x["affordable"] for x in o2][:2], [True, False])
check("suggest: a real balance picks what it covers", o2[r2]["label"], "tier S")
o3, r3 = L.recommend_unlock([("S", 12), ("A", 15)], 5, 20)
check("suggest: nothing affordable still suggests something", r3 is not None, True)
# With a zero balance every option is unaffordable — the caller's job becomes the link.
o4, _r4 = L.recommend_unlock([("S", 12)], 5, 0)
check("suggest: zero balance marks all unaffordable", [x["affordable"] for x in o4], [False])
check("suggest: the selection is the API's own body shape",
      L.recommend_unlock([("S", 3), ("A", 9)], 5, 0)[0][1]["selection"], {"tiers": ["S", "A"]})


# ------------------------------------------ pricing an unlock without spending anything

# A shortfall is NOT an error to retry. It is a price and a link, and the only correct move is
# to put both in front of a person and stop. The dry run answers in its OWN shape —
# `matched`/`credits_required`/`credits_available` — not the shape a real unlock returns, and
# the published spec documents only the second one. So both are read.
DRY = {"dry_run": True, "matched": 12, "credits_required": 60, "credits_available": 0,
       "payment_url": "https://example.test/credits"}
check("quote: the dry-run shape is understood",
      (DRY.get("matched", DRY.get("unlocked")),
       DRY.get("credits_required", DRY.get("credits_spent")),
       DRY.get("credits_available", DRY.get("credits_remaining"))), (12, 60, 0))
REAL = {"unlocked": 17, "credits_spent": 85, "credits_remaining": 415, "dossiers_pending": 7}
check("quote: the real shape is understood too",
      (REAL.get("matched", REAL.get("unlocked")),
       REAL.get("credits_required", REAL.get("credits_spent"))), (17, 85))
# `unlock` defaults to dry_run: the honest default for a function that spends somebody's
# money is the one that does not.
import inspect  # noqa: E402
check("unlock: defaults to NOT spending",
      inspect.signature(L.unlock).parameters["dry_run"].default, True)
# A failure has to carry its payload, or a 402's payment_url is unreachable and "here is the
# link to top up" degrades into "something went wrong".
err = L.LanyardError(402, "insufficient_credits", "needs 60, has 0", DRY)
check("error: carries the whole payload", err.payload["payment_url"], "https://example.test/credits")
check("error: and still reads as a message", "needs 60" in str(err), True)
check("error: an empty payload is a dict, never None", L.LanyardError(500, "x", "y").payload, {})


# --------------------------------- the request shapes, learned from the live service

# MEASURED: the service sits behind an edge that rejects Python's default agent outright —
# `Python-urllib/3.x` gets 403 with an HTML error page before reaching the API, while the
# identical request with a named agent and the same key gets 200. Every call would fail, and
# it would look exactly like a revoked key.
truthy("user agent: a named agent is declared", L.USER_AGENT)
check("user agent: it is not python's default", "urllib" in L.USER_AGENT.lower(), False)

# An edge refusal and a rejected key are the same status code; only the body differs. Calling
# a non-JSON 403 a bad key sends someone round the sign-in loop against an unrelated problem.
hint = L.edge_hint(403, "<!doctype html><h1>Access denied</h1>")
check("edge: a non-JSON 403 is named as an edge refusal", "NOT a rejected key" in hint, True)
check("edge: and points at the real cause", "User-Agent" in hint, True)
check("edge: 429 is described as rate limiting", "rate-limited" in L.edge_hint(429, "x"), True)
check("edge: an unknown status still reports the body", "HTTP 500" in L.edge_hint(500, "boom"), True)

# The lookup returns MORE keys than the create call documents accepting, so the looked-up
# object cannot be forwarded verbatim.
LIVE_LOOKUP = {"name": "HubSpot INBOUND", "edition": "2026", "start_date": "2026-09-22",
               "end_date": "2026-09-24", "location": "San Francisco, USA",
               "website": "https://www.inbound.com", "likely_app": "custom",
               "summary": "...", "confidence": "high"}
narrowed = L.conference_for_create(LIVE_LOOKUP)
check("conference: only documented keys survive",
      sorted(narrowed), ["end_date", "name", "start_date", "website"])
# The edition is why the lookup was worth doing; dropping it would let the service re-guess
# the year it was just told.
check("conference: the edition is folded into the name", narrowed["name"], "HubSpot INBOUND 2026")
check("conference: an edition already in the name is not repeated",
      L.conference_for_create({"name": "INBOUND 2026", "edition": "2026"})["name"], "INBOUND 2026")
check("conference: a bare string passes through", L.conference_for_create("SaaStr"), "SaaStr")
check("conference: blanks are dropped, not sent",
      L.conference_for_create({"name": "X", "website": "", "city": None}), {"name": "X"})


# ------------------------------- refusing to send the example file's own instructions

check("placeholders: a REPLACE marker is caught",
      D.placeholders_in({"domain": "REPLACE — your own company's website."}),
      ["body.domain = \"REPLACE — your own company's website.\""])
# The real trap is prose nested inside team or context, which a copied example leaves behind
# and which is truthy, so it is sent as a real teammate.
check("placeholders: found inside a list of teammates",
      len(D.placeholders_in({"team": [{"name": "Optional — who is going from your side"}]})), 1)
check("placeholders: found inside a nested object",
      len(D.placeholders_in({"context": {"client": "Optional. Anything about your business"}})), 1)
check("placeholders: a filled config is clean",
      D.placeholders_in({"domain": "acme.com", "goals": "meet revenue leaders",
                         "team": [{"name": "Dana Whitfield", "title": "CRO"}],
                         "context": {"client": "we sell to mid-market SaaS"}}), [])
check("placeholders: empty optionals are clean", D.placeholders_in({"team": [], "context": {}}), [])
# And the shipped example must itself be safe to POST once the two marked keys are filled.
_ex = json.load(open(os.path.join(HERE, "conference-config.example.json")))
check("example config: every optional that is SENT is falsy by default",
      [k for k in ("context", "team", "attendees", "label") if _ex.get(k)], [])



# ------------------------------------ a URL resolves the edition, and runs live outside a repo

_sent = {}


def _fake_request(method, path, key, body=None, query=None, timeout=60):
    _sent.clear()
    _sent.update({"method": method, "path": path, "body": body})
    return {"conference": {"name": "SaaStr AI Annual 2027"}}


_real_request = L._request
L._request = _fake_request
try:
    L.lookup_conference("k", "SaaStr Annual")
    check("lookup: a bare name is sent as the name", _sent["body"], {"name": "SaaStr Annual"})

    L.lookup_conference("k", "SaaStr Annual", url="https://www.saastrannual.com/")
    check("lookup: a URL rides alongside the name",
          _sent["body"], {"name": "SaaStr Annual", "url": "https://www.saastrannual.com/"})

    L.lookup_conference("k", None, url="https://www.saastrannual.com/")
    check("lookup: a URL with no name becomes the query",
          _sent["body"], {"name": "https://www.saastrannual.com/",
                          "url": "https://www.saastrannual.com/"})

    L.lookup_conference("k", "INBOUND", city="Boston", year=2026)
    check("lookup: city and year still ride along",
          _sent["body"], {"name": "INBOUND", "city": "Boston", "year": "2026"})

    try:
        L.lookup_conference("k")
        check("lookup: neither a name nor a URL is refused", "no error", "ValueError")
    except ValueError:
        check("lookup: neither a name nor a URL is refused", "ValueError", "ValueError")
finally:
    L._request = _real_request

_cfg = {"workspace_id": "123456"}
_run = C.run_dir(_cfg, date="2026-09-23")
check("run_dir: lands under the writer, keyed by workspace and date",
      _run.endswith("/.deepline-conference-writer/123456/runs/2026-09-23"), True)
check("run_dir: is absolute, so it cannot resolve inside the session's repo",
      os.path.isabs(_run), True)
check("run_dir: defaults to today rather than failing", bool(C.run_dir(_cfg)), True)

# ------------------------------------ the candidate pool, broken down by which edition

# The campaign reports this across EVERYTHING it found, which is the fairer number: the split
# across the written handful says as much about the free allowance as about the event.
POOL = {"counts": {"attendees": 144,
                   "attendance": {"this_year": 70, "last_year": 54, "prior": 19, "unknown": 1}}}
check("pool: read from the campaign, best edition first",
      L.attendance_pool(POOL), [("this_year", 70), ("last_year", 54), ("prior", 19), ("unknown", 1)])
check("pool: zero buckets are left out",
      L.attendance_pool({"counts": {"attendance": {"this_year": 5, "prior": 0}}}), [("this_year", 5)])
# An edition name nobody has seen yet must still be reported rather than dropped.
check("pool: an unknown bucket still shows",
      L.attendance_pool({"counts": {"attendance": {"this_year": 2, "next_year": 3}}}),
      [("this_year", 2), ("next_year", 3)])
# Older campaigns predate the block; the listing row carries only the headline.
check("pool: falls back to the headline figure",
      L.attendance_pool({"counts": {"this_year": 70}}), [("this_year", 70)])
check("pool: a campaign without it reports nothing rather than guessing",
      L.attendance_pool({"counts": {"attendees": 9}}), [])
check("pool: junk input is safe", L.attendance_pool({}), [])
check("pool: None is safe", L.attendance_pool(None), [])


# ------------------------------- coming back later: finding the campaign from a phrase

ROWS = [
    {"campaign_id": "c-saastr", "created_at": "2026-03-01",
     "conference": {"name": "SaaStr Annual", "edition": "2026", "city": "San Mateo"},
     "label": "Acme prospecting"},
    {"campaign_id": "c-inbound", "created_at": "2026-05-01",
     "conference": {"name": "INBOUND", "edition": "2026", "city": "San Francisco"}},
    {"campaign_id": "c-inbound-25", "created_at": "2025-05-01",
     "conference": {"name": "INBOUND", "edition": "2025", "city": "Boston"}},
]
def ids(q): return [r["campaign_id"] for r in L.match_campaigns(ROWS, q)]

check("match: by conference name", ids("saastr"), ["c-saastr"])
check("match: case does not matter", ids("SaaStr"), ["c-saastr"])
check("match: by label", ids("acme"), ["c-saastr"])
check("match: by city", ids("mateo"), ["c-saastr"])
check("match: by id", ids("c-inbound-25"), ["c-inbound-25"])
# Every word must appear — this is the check that stops "the SaaStr one" matching INBOUND.
check("match: all words must appear", ids("saastr inbound"), [])
check("match: a year narrows an ambiguous name", ids("inbound 2025"), ["c-inbound-25"])
# An ambiguous phrase returns BOTH rather than guessing, and the caller refuses.
check("match: ambiguity returns every hit", sorted(ids("inbound")), ["c-inbound", "c-inbound-25"])
check("match: newest first when equally good", ids("inbound")[0], "c-inbound")
check("match: nothing matches, nothing returned", ids("web summit"), [])
check("match: an empty query matches nothing, never everything", ids(""), [])
check("match: whitespace is not a query", ids("   "), [])
# The haystack must not reach into fields that would make unrelated campaigns collide.
truthy("match: the haystack carries the conference name", "saastr" in L.campaign_haystack(ROWS[0]))
check("match: a row with no conference does not crash", L.match_campaigns([{"campaign_id": "x"}], "x"),
      [{"campaign_id": "x"}])


# --------------------------------------- the link a person opens to read their results

# `share_url` is a /claim?t=<token> link whose token IS the access. Handing it over as "your
# results" is the wrong page and quietly shares the campaign with whoever ends up holding it.
check("link: built from the id, not from a response field",
      L.campaign_url("abc-123"), "https://lanyard.redlinegrowth.com/campaign/abc-123")
check("link: carries no token", "?" in L.campaign_url("abc-123"), False)
check("link: is not the claim page", "claim" in L.campaign_url("abc-123"), False)
# The unlock fallback must not widen access either.
lk = L.locked_summary({"campaign_id": "abc-123",
                       "share_url": "https://lanyard.redlinegrowth.com/campaign/abc-123/claim?t=SECRET"},
                      CONTACTS)
check("link: the unlock fallback never falls back to a token link", "SECRET" in (lk["unlock_url"] or ""), False)
check("link: it falls back to the campaign page", lk["unlock_url"],
      "https://lanyard.redlinegrowth.com/campaign/abc-123")
# A published unlock_url still wins, because that one is authoritative.
lk2 = L.locked_summary({"campaign_id": "abc-123",
                        "locked": {"total": 3, "unlock_url": "https://example.test/pay"}}, CONTACTS)
check("link: a published unlock_url is preferred", lk2["unlock_url"], "https://example.test/pay")


# ------------------------------------ one writer per workspace, not one per conference

w1 = C.writer_config_path({"workspace_id": "123456"})
check("writer: same workspace resolves to the same config, always",
      w1, C.writer_config_path({"workspace_id": "123456"}))
check("writer: a different workspace gets its own", w1 == C.writer_config_path({"workspace_id": "9"}), False)
check("writer: the path carries the workspace id", "123456" in w1, True)
check("writer: an explicit writer_dir wins",
      C.writer_config_path({"workspace_id": "1", "writer_dir": "/tmp/x"}), "/tmp/x/writer-config.json")
check("writer: ~ is expanded", w1.startswith("~"), False)
truthy("writer: a config with no workspace id still resolves", C.writer_config_path({}))


# ----------------------------------------------------------------------- the report

print()
for f in FAILURES:
    print("  FAIL " + f)
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
