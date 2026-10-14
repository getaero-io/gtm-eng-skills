"""Decide what a customer-DB write may contain, and which lane it goes down.

The failure this module exists to prevent used to be the quiet one: in Clay Audiences (where
this skill was first built), a value the field's declared type could not parse was
**accepted**, reported as written, read back verbatim, and matched no filter, ever.

In the Deepline customer DB the columns are real Postgres types, so the same value fails
LOUDLY instead — and takes the whole batch statement down with it. Either way the remedy is
the same: every value is checked against its column's real type BEFORE the write, and
anything that fails is dropped with a named reason rather than sent and hoped for.
"""

import datetime
import math
import re

# ------------------------------------------------------------------ the field plan

# (display name, type, column). The column is the snake_case source key, and it is the name
# in `storage.conference_attendees` / `storage.conference_companies`. The display name is
# what the report prints.
#
# Types are chosen for what has to be FILTERABLE afterwards, which is why `score` and `rank`
# are the only numbers here and why nothing is a boolean: a boolean column cannot be
# coverage-checked — `= false` and "never set" are easy to conflate in a segment.

PEOPLE_FIELDS = [
    ("Conference", "text", "conference_name"),
    ("Conference start", "date", "conference_start"),
    ("Conference location", "text", "conference_location"),
    ("Conference campaign id", "text", "campaign_id"),
    ("Attendee record id", "text", "lanyard_contact_id"),
    ("Attendee tier", "text", "tier"),
    ("Attendee score", "number", "score"),
    ("Attendee rank", "number", "rank"),
    ("Attendance confidence", "text", "attendance_confidence"),
    ("Attendance evidence", "text", "attendance_evidence"),
    ("Attendance source", "text", "attendance_source"),
    # Which edition the evidence is about. Load-bearing once a list can be seeded: seeding
    # LAST year's attendee list is legitimate evidence that somebody may come again, and is
    # not evidence that they are coming. This column is where that difference lives, so a
    # segment can require this year rather than assuming it.
    ("Attendance year", "text", "attendance_year"),
    ("Dossier state", "text", "dossier_state"),
    ("Dossier headline", "text", "headline"),
    ("Dossier summary", "text", "dossier_summary"),
    ("Their company", "text", "company_summary"),
    ("Why they score", "text", "score_rationale"),
    ("Buying signals", "text", "buying_signals"),
    ("Conversation openers", "text", "openers"),
    ("Value prop", "text", "value_prop"),
    ("Dossier written at", "date", "written_at"),
]

# TIER COMES FROM THE OTHER RESPONSE FORMAT, not from the dossier. Measured: no contact in
# the rich format carries a tier under any key, so a client reading only that format writes a
# permanently empty tier column. The flat projection has it for every contact, and a second
# read costs nothing on this API — so both are read
# and merged on identity. Tier is worth the round trip: "who are the S-tiers" is the first
# question anybody asks of a conference list.

COMPANY_FIELDS = [
    ("Conference", "text", "conference_name"),
    ("Conference campaign id", "text", "campaign_id"),
    ("Attending this conference", "text", "attending_flag"),
    ("Dossier written at", "date", "written_at"),
]

# Identity columns written alongside the plan, all text.
PEOPLE_BUILTINS = ["name", "first_name", "last_name", "title", "email", "linkedin_url", "phone",
                   "company_name", "company_domain"]
COMPANY_BUILTINS = ["org_name", "domain"]

# Plan type -> Postgres column type.
SQL_TYPES = {"text": "text", "number": "numeric", "date": "date"}

# The company is always matched on its domain: a company with no domain cannot be keyed, and
# its people are written unlinked (company_domain NULL) instead.
ACCOUNT_MATCH_KEY = "domain"


# --------------------------------------------------------------------- validation

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ].*)?$")
_NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")


def validate_value(value, data_type):
    """Return (ok, coerced, reason). `reason` is set only when ok is False.

    A False here means the value is dropped from the write, not that the write fails: a
    contact with an unparseable score is still worth having, minus the score.
    """
    if value is None or value == "":
        return False, None, "empty"

    if data_type in ("text", "string"):
        return True, str(value), None

    if data_type == "number":
        if isinstance(value, bool):
            return False, None, "boolean_into_number"
        if isinstance(value, (int, float)):
            return True, value, None
        if isinstance(value, float) and not math.isfinite(value):
            return False, None, "not_a_number"
        cleaned = str(value).strip().replace(",", "")
        cleaned = cleaned.lstrip("$£€")
        if _NUMERIC.match(cleaned):
            return True, float(cleaned) if "." in cleaned else int(cleaned), None
        # In Clay Audiences this shape was silently accepted and then filtered as empty; in
        # Postgres it fails the statement.
        return False, None, "not_a_number"

    if data_type == "date":
        v = str(value).strip()
        if _ISO_DATE.match(v):
            try:
                # A shape check alone passes 2026-13-45, which Postgres then rejects and takes
                # the whole batch with it.
                return True, datetime.date.fromisoformat(v[:10]).isoformat(), None
            except ValueError:
                pass
        return False, None, "not_an_iso_date"

    if data_type == "email":
        v = str(value).strip().lower()
        if v.count("@") == 1 and "." in v.split("@")[1] and " " not in v:
            return True, v, None
        return False, None, "not_an_email"

    if data_type == "url":
        v = str(value).strip()
        if "://" in v and " " not in v and "." in v:
            return True, v, None
        if "." in v and " " not in v and v:
            return True, "https://" + v.lstrip("/"), None
        return False, None, "not_a_url"

    if data_type == "boolean":
        # Deliberately unreachable from the field plan. Kept so an added boolean field fails
        # loudly here instead of producing a column nobody can measure coverage on.
        return False, None, "boolean_fields_cannot_be_coverage_checked"

    return True, str(value), None


# ------------------------------------------------------------------------ routing

# Four lanes: matched on LinkedIn or on email, linked to a company or not. In the DB a lane is
# just which person_key is used and whether company_domain is set; it is kept as a label
# because the report counts by it.

ROUTE_LINKED_EMAIL = "linked_email"
ROUTE_LINKED_LINKEDIN = "linked_linkedin"
ROUTE_UNLINKED_EMAIL = "unlinked_email"
ROUTE_UNLINKED_LINKEDIN = "unlinked_linkedin"
ROUTE_UNWRITABLE = "unwritable"


def route_for(shaped, link_company=True):
    """Pick the writer lane for one contact. Returns (route, reason).

    LinkedIn is preferred over email as the match key: for a conference attendee it is the
    more stable identity, and two people at one company can share an inbox alias while never
    sharing a profile.
    """
    has_linkedin = bool(shaped.get("linkedin_url"))
    has_email = bool(shaped.get("email"))
    linked = bool(link_company and shaped.get("company_domain"))

    if not has_linkedin and not has_email:
        return ROUTE_UNWRITABLE, "no valid match key: neither a LinkedIn URL nor an email"

    if has_linkedin:
        return (ROUTE_LINKED_LINKEDIN if linked else ROUTE_UNLINKED_LINKEDIN), "matched on LinkedIn URL"
    return (ROUTE_LINKED_EMAIL if linked else ROUTE_UNLINKED_EMAIL), "matched on email"


def route_is_linked(route):
    return route in (ROUTE_LINKED_EMAIL, ROUTE_LINKED_LINKEDIN)


def route_match_key(route):
    return "email" if route in (ROUTE_LINKED_EMAIL, ROUTE_UNLINKED_EMAIL) else "linkedin_url"


def plan_writes(shaped_contacts, link_company=True):
    """Group a run's contacts by lane, and separate out the ones nothing can write.

    Returns (by_route, unwritable) so the plan shown before any write states both.
    """
    by_route, unwritable = {}, []
    for s in shaped_contacts:
        route, reason = route_for(s, link_company=link_company)
        if route == ROUTE_UNWRITABLE:
            unwritable.append((s, reason))
        else:
            by_route.setdefault(route, []).append(s)
    return by_route, unwritable
