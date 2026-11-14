"""Everything the loader decides without talking to the database.

Reading a CSV, a TSV or one tab of an Excel workbook, inferring a type per column, minting a row
key, deciding which match key a row can use, counting what cannot load, building one batch's
upsert SQL, and folding a ledger back into a work set. None of it needs the Deepline customer DB,
a network or a credential, which is why the test suite can cover the parts that otherwise only
fail on row 4,000 of a live load. The one exception is `db()`, the thin wrapper around
`deepline db query` that the two drivers share.

    python3 loader_lib.py sheets  --companies <book.xlsx>              # what tabs are in there
    python3 loader_lib.py inspect --companies <file[#tab]> [--contacts <file[#tab]>]
    python3 loader_lib.py check   --companies <file[#tab]> [--contacts <file[#tab]>] --map <map.json>

`inspect` proposes a mapping. `check` scores a confirmed one and prints the coverage report that
the gate is built on. Both are read-only and free.
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

# The keys a record is matched on, and nothing else. The upsert target is one `match_key` column
# holding `<key>:<value>` (`domain:acme.com`, `email:ada@acme.com`) with a UNIQUE constraint, so
# two rows carrying the same key and value land on one record however they arrived.
MATCH_KEYS = {
    "companies": ("domain", "linkedin_url"),
    "contacts": ("email", "linkedin_url", "phone"),
}

# The order the keys are tried, per row. A run flag, not a property of the tables: the driver
# writes the key it chose into `match_key`, so reordering never rebuilds anything.
DEFAULT_KEY_ORDER = {
    "companies": ["domain", "linkedin_url"],
    "contacts": ["email", "linkedin_url", "phone"],
}

FIELD_TYPES = ("text", "number", "email", "url", "date", "boolean")

# A verdict that settles the ROW KEY. `rejected_duplicate_row_key` is deliberately NOT in here,
# and the reason is a bug this cost before it was found: the ledger is indexed by row key and a
# duplicate row shares its key with the real one, so recording it as a settled verdict lets a
# redundant row supersede the load it is a duplicate OF. Measured — a company exported twice
# loaded correctly, its second row was rejected, the fold resolved the key to the rejection, the
# company dropped out of the id map, and every contact at that company loaded with no company
# attached while the run reported success on all of them.
#
# Left out of this tuple, the line is still written and still counted; it just cannot displace
# what the real row did. A duplicate row is filtered out on the next pass anyway, because its
# key is settled by the row it duplicates.
SETTLED = ("completed", "rejected_no_match_key", "skipped_no_company")

_TRUE = ("true", "yes", "y", "1", "t")
_FALSE = ("false", "no", "n", "0", "f")
_LEGAL_SUFFIX = ("inc", "llc", "ltd", "limited", "corp", "corporation", "gmbh", "plc", "sa", "bv",
                 "ag", "co", "company", "holdings", "group", "pty", "srl", "oy", "ab", "as")


# --------------------------------------------------------------------------- values and types

def blank(v):
    """Blank is a value, and the only definition of it used anywhere in this loader."""
    return v is None or str(v).strip() == ""


def parses_as(value, field_type):
    """Will this value go into a column of the declared type?

    This is the whole point of the pre-load check. A typed Postgres column refuses a value it
    cannot parse, and it refuses it LOUDLY: one `1,001-5,000` in a numeric column fails the whole
    INSERT, so every other row in that batch fails with it. (On Clay Audiences, measured 2026, the
    same value was the opposite and worse: accepted, echoed back, and invisible to every filter.)
    The quiet failure here is the dodge: type the column `text` to make the error go away, and
    `> 100` then compares strings, so `88` sorts above `512`.
    """
    if blank(value):
        return True                       # a blank record field is dropped, not stored wrong
    s = str(value).strip()
    if field_type == "text":
        return True
    if field_type == "number":
        # Thousands separators are fine; a band, a range or an approximation is not. A regex, not
        # float(): float() also takes `nan`, `inf` and `1_000`, none of which mean a headcount.
        return bool(_NUMBER.fullmatch(s.replace(",", "").replace(" ", "")))
    if field_type == "boolean":
        return s.lower() in _TRUE + _FALSE
    if field_type == "email":
        return s.count("@") == 1 and " " not in s and "." in s.split("@")[-1]
    if field_type == "url":
        return s.lower().startswith(("http://", "https://"))
    if field_type == "date":
        return _parses_as_date(s)
    raise ValueError("unknown field type: %s" % field_type)


_NUMBER = re.compile(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?")
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d")


def _iso_date(s):
    """The ISO date this value means, or None. Deliberately narrow: `Q3 2017` and a bare year must
    fail. Slashed dates are read month-first, the database's own default, and a value that is not
    a real calendar day under that reading (`25/12/2017`) fails here rather than in the INSERT."""
    s = s.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ].*", s):
        s = s[:10]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _parses_as_date(s):
    return _iso_date(s) is not None


def infer_type(values):
    """Propose a type from every non-blank value in the column. `text` is the safe fallback.

    Sampling the first N rows is how a band two thousand rows down becomes a number field, so
    this reads the lot: the file is already in memory and being wrong is expensive.
    """
    vals = [v for v in values if not blank(v)]
    if not vals:
        return "text"
    for t in ("boolean", "number", "email", "url", "date"):
        if all(parses_as(v, t) for v in vals):
            return t
    return "text"


# --------------------------------------------------------------------------- keys

def norm_domain(v):
    if blank(v):
        return ""
    s = str(v).strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.split("/")[0].strip()


def slug(v):
    """Fold a company name to a stable slug: accents, punctuation and legal suffixes removed."""
    if blank(v):
        return ""
    s = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    parts = [p for p in s.split() if p not in _LEGAL_SUFFIX]
    return "-".join(parts or s.split())


def mint_row_key(row, domain_col=None, name_col=None):
    """Mint a deterministic row key. Same row in, same key out, on any machine.

    Returns (key, rule) — the rule is reported, because minting silently is the failure. Two
    different companies sharing a name collapse under `name-slug`, and that is a real cost the
    installer has to be told about rather than discover.
    """
    if domain_col and not blank(row.get(domain_col)):
        d = norm_domain(row[domain_col])
        if d:
            return d, "domain"
    if name_col and not blank(row.get(name_col)):
        s = slug(row[name_col])
        if s:
            return s, "name-slug"
    return "", "none"


def valid_match_value(key, value):
    """Is this value THIS KIND of key — not merely a non-empty string?

    A table will happily store `email:not-an-email` as a match key, and then nothing anyone
    else holds will ever match it. So a key is checked for shape: a malformed email, a phone with
    no digits, and a LinkedIn URL whose host is anything other than linkedin.com are refused.
    (The same three were measured as refused by Clay Audiences' upsert, 2026, with wording that
    read as though the field were blank.) A `.example` domain and a `.example` email address are
    both accepted: this is a shape check, not a check on registrability.
    """
    if blank(value):
        return False
    s = str(value).strip()
    if key == "domain":
        return "." in s and " " not in s and "@" not in s
    if key == "linkedin_url":
        host = re.sub(r"^https?://", "", s.lower()).split("/")[0]
        return host == "linkedin.com" or host.endswith(".linkedin.com")
    if key == "email":
        return parses_as(s, "email")
    if key == "phone":
        return len(re.sub(r"\D", "", s)) >= 7
    return True


def choose_match_key(row, mapping, entity):
    """Which of the match keys can this row actually be matched on?

    Falls through to the next key in the declared order when a value is missing OR unusable, so
    a company with a broken LinkedIn URL and a good domain still loads on the domain.

    Returns (key, value) or ("", "") when the row carries none — which is not a failure to
    retry, it is a row that cannot be loaded at all. Screening it here is what keeps a permanent
    rejection out of the retry set.
    """
    order = mapping.get("key_order", {}).get(entity) or DEFAULT_KEY_ORDER[entity]
    cols = mapping.get("match_columns", {}).get(entity, {})
    for key in order:
        if key not in MATCH_KEYS[entity]:
            raise ValueError("%s is not a match key for %s" % (key, entity))
        col = cols.get(key)
        if col and not blank(row.get(col)):
            v = norm_domain(row[col]) if key == "domain" else str(row[col]).strip()
            if valid_match_value(key, v):
                return key, v
    return "", ""


# A personal mailbox says nothing about where someone works, so its domain must never become a
# company. Creating `gmail.com` as an account and hanging contacts off it is worse than leaving
# them unlinked, because it looks like it worked.
FREE_EMAIL_DOMAINS = frozenset("""
gmail.com googlemail.com yahoo.com yahoo.co.uk ymail.com hotmail.com hotmail.co.uk outlook.com
live.com msn.com aol.com icloud.com me.com mac.com proton.me protonmail.com pm.me gmx.com gmx.de
gmx.net mail.com mail.ru yandex.com yandex.ru zoho.com fastmail.com hey.com qq.com 163.com 126.com
naver.com daum.net rediffmail.com web.de t-online.de orange.fr free.fr laposte.net comcast.net
verizon.net att.net sbcglobal.net bellsouth.net cox.net btinternet.com sky.com virginmedia.com
optonline.net shaw.ca rogers.com telus.net bigpond.com outlook.co.uk hotmail.fr hotmail.it
""".split())


def _norm_label(s):
    """`HQ_City`, `hq city` and `HQ  City` are the same label, and a match must see that."""
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def certain_field_match(column, existing):
    """The field this column is the SAME LABEL as, once case and punctuation are ignored.

    Deliberately narrow: this answers a question of fact, not of meaning. `Company_Name` is
    `Company name`; that needs no judgment and should not be left to any.

    **Everything else is the agent's job, not this function's.** An earlier version carried a table
    of known spellings — `headcount` -> `employee_count`, `website` -> `domain` — which is judgment
    encoded as a lookup. It could not see `staff_count`, `# of employees`, `Employee Range` or a
    header in another language, and its worst property was that a miss printed "no field yet",
    which reads as an answer rather than as nobody having looked. The skill hands the column list
    and the field list to the agent running it and asks for a reasoned mapping instead.
    """
    want = _norm_label(column)
    if not want:
        return None
    for f in existing:
        if _norm_label(f.get("name")) == want:
            return {"field_id": f.get("id"), "field_name": f.get("name"),
                    "stored_type": f.get("dataType"), "how": "same label"}
    for f in existing:
        if _norm_label(f.get("id")) == want:
            return {"field_id": f.get("id"), "field_name": f.get("name"),
                    "stored_type": f.get("dataType"), "how": "named like the field id"}
    return None


# The loader's types, as the column type each one is stored in. `email` and `url` are text with a
# shape check in front of them; the check is the loader's, not the column's.
PG_TYPE = {"text": "text", "email": "text", "url": "text", "number": "numeric", "date": "date",
           "boolean": "boolean"}
# What `information_schema.columns.data_type` reports, folded to the same families.
_PG_FAMILY = {"character varying": "text", "integer": "numeric", "bigint": "numeric",
              "smallint": "numeric", "double precision": "numeric", "real": "numeric"}


def storage_type(t):
    """`url` -> `text`, `integer` -> `numeric`: the family a value is actually stored as."""
    return PG_TYPE.get(t) or _PG_FAMILY.get(t, t)


def type_conflict(stored_type, proposed_type):
    """Reusing a column whose stored type disagrees is the headline failure through the back door:
    a `text` column fed numbers sorts `88` above `512`, and a `numeric` column fed bands fails
    every batch it is in. This is a mechanical check and stays mechanical — never a judgment."""
    return bool(stored_type and proposed_type
                and storage_type(stored_type) != storage_type(proposed_type))


def company_key_for_contact(row, mapping):
    """The match key a contact carries for its company: (type, value, where it came from).

    **Not domain-only.** A company is matched on `domain` OR `linkedin_url`, so this resolves to
    whichever the contact can supply, in the same order the companies loader uses. Three sources:
    a company-domain column, a company-LinkedIn column, then the work email's domain.

    Returns ("", "", "") when nothing usable is there, which is a real outcome rather than a
    failure: a contact on a personal mailbox carries no evidence of where they work.

    A company NAME is deliberately not a source. Nothing can be keyed on one — `match_key` takes
    only domain and linkedin_url — and matching on a name that is not unique attaches a
    contact to the wrong company, which is the silent wrongness this whole skill refuses.
    """
    col = mapping.get("contacts_company_domain_column")
    if col and not blank(row.get(col)):
        d = norm_domain(row[col])
        if valid_match_value("domain", d):
            return "domain", d, "domain column"

    li_col = mapping.get("contacts_company_linkedin_column")
    if li_col and not blank(row.get(li_col)):
        v = str(row[li_col]).strip()
        if valid_match_value("linkedin_url", v):
            return "linkedin_url", v, "linkedin column"

    email_col = (mapping.get("match_columns", {}).get("contacts", {}) or {}).get("email")
    if email_col and not blank(row.get(email_col)):
        addr = str(row[email_col]).strip().lower()
        if addr.count("@") == 1:
            d = addr.split("@")[-1].strip()
            if d not in FREE_EMAIL_DOMAINS and valid_match_value("domain", d):
                return "domain", d, "email domain"
    return "", "", ""


def company_name_for_contact(row, mapping):
    col = mapping.get("contacts_company_name_column")
    return str(row.get(col) or "").strip() if col else ""


def contact_join_key(row, mapping):
    """The key the contacts load will look up in the company ledger.

    The reference column when the row has one — that is what joins to the companies table. When it
    does not, the derived match key stands in, so a contact carrying only an email domain can
    still be linked to a company the pre-pass found or created for it.
    """
    ref_col = mapping.get("company_ref_column")
    ref = str(row.get(ref_col) or "").strip() if ref_col else ""
    if ref:
        return ref
    _t, v, _s = company_key_for_contact(row, mapping)
    return v


# Kept as a thin alias: the orphan report only ever wants "is there something to go on".
def company_domain_for_contact(row, mapping):
    t, v, src = company_key_for_contact(row, mapping)
    return (v, src) if t else ("", "")


def unusable_match_values(row, mapping, entity):
    """Keys this row carries a value for that is not that kind of key. Counted separately from carrying
    nothing at all, because the remedy is different: fix the value you have, not find a new one."""
    cols = mapping.get("match_columns", {}).get(entity, {})
    out = []
    for key in MATCH_KEYS[entity]:
        col = cols.get(key)
        if col and not blank(row.get(col)):
            v = norm_domain(row[col]) if key == "domain" else str(row[col]).strip()
            if not valid_match_value(key, v):
                out.append((key, v))
    return out


# --------------------------------------------------------------------------- reading

def read_csv(path):
    delim = "\t" if path.lower().endswith((".tsv", ".tab")) else ","
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter=delim)]


# --------------------------------------------------------------------------- spreadsheets
#
# An .xlsx is a zip of XML, so this reads one with nothing but the standard library. That is a
# deliberate choice over openpyxl or pandas: the installer may have neither, and a loader that
# cannot open the file it was pointed at is no loader. Nothing here writes, and no network is used.

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_RELNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKGREL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
# Built-in number formats that mean "this is a date". Anything else is checked for y/m/d below.
_DATE_FMT_IDS = set(range(14, 23)) | set(range(45, 48)) | {27, 30, 36, 50, 57}


def _col_index(ref):
    """`A1` -> 0, `AA7` -> 26. Cells are addressed, not ordered, so a gap must stay a gap."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _excel_serial_to_iso(value):
    """Excel stores a date as a number of days. Left raw it reads as a plausible integer, sails
    through a numeric check, and lands in the table as a meaningless five-digit number — which is
    exactly the silent wrongness this skill exists to stop. 1899-12-30 is the correct epoch: it
    absorbs Excel's deliberate 1900-is-a-leap-year bug."""
    try:
        days = float(value)
    except (TypeError, ValueError):
        return value
    base = datetime.date(1899, 12, 30)
    whole = int(days)
    out = base + datetime.timedelta(days=whole)
    frac = days - whole
    if frac > 0:
        secs = int(round(frac * 86400))
        return "%sT%02d:%02d:%02d" % (out.isoformat(), secs // 3600, (secs % 3600) // 60, secs % 60)
    return out.isoformat()


def _xlsx_parts(zf):
    shared = []
    if "xl/sharedStrings.xml" in zf.namelist():
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in root.findall("%ssi" % _NS):
            shared.append("".join(t.text or "" for t in si.iter("%st" % _NS)))

    date_styles = set()
    if "xl/styles.xml" in zf.namelist():
        root = ET.fromstring(zf.read("xl/styles.xml"))
        custom = {}
        for nf in root.iter("%snumFmt" % _NS):
            code = (nf.get("formatCode") or "").lower()
            stripped = re.sub(r"\[[^\]]*\]|\"[^\"]*\"", "", code)
            if any(c in stripped for c in "ymd") and "0.00" not in stripped:
                custom[int(nf.get("numFmtId"))] = True
        xfs = root.find("%scellXfs" % _NS)
        for i, xf in enumerate(xfs.findall("%sxf" % _NS) if xfs is not None else []):
            fid = int(xf.get("numFmtId") or 0)
            if fid in _DATE_FMT_IDS or custom.get(fid):
                date_styles.add(i)
    return shared, date_styles


def list_sheets(path):
    """Tab names, in workbook order."""
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("xl/workbook.xml"))
        return [s.get("name") for s in root.iter("%ssheet" % _NS)]


def read_xlsx(path, sheet=None):
    """One tab as a list of dicts, keyed by the header row. Blank trailing columns are dropped."""
    with zipfile.ZipFile(path) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets = list(wb.iter("%ssheet" % _NS))
        names = [s.get("name") for s in sheets]
        if sheet is None:
            if len(sheets) != 1:
                raise ValueError("%s has %d tabs (%s) — name the one to read as `%s#<tab>`"
                                 % (os.path.basename(path), len(names), ", ".join(names), path))
            target = sheets[0]
        else:
            matches = [s for s in sheets if (s.get("name") or "").lower() == sheet.lower()]
            if not matches:
                raise ValueError("%s has no tab called %r. It has: %s"
                                 % (os.path.basename(path), sheet, ", ".join(names)))
            target = matches[0]

        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        by_id = {r.get("Id"): r.get("Target") for r in rels.iter("%sRelationship" % _PKGREL)}
        # A rel target may be written three ways by three different writers:
        # `worksheets/sheet1.xml` (relative), `/xl/worksheets/sheet1.xml` (package-absolute) and
        # `xl/worksheets/sheet1.xml`. Normalise before prefixing, or the absolute form becomes
        # `xl/xl/...` and the file "has no sheets".
        tgt = (by_id.get(target.get("%sid" % _RELNS)) or "").lstrip("/")
        member = tgt if tgt.startswith("xl/") else "xl/" + tgt

        shared, date_styles = _xlsx_parts(zf)
        grid = []
        for row in ET.fromstring(zf.read(member)).iter("%srow" % _NS):
            cells = {}
            for c in row.findall("%sc" % _NS):
                idx = _col_index(c.get("r") or "A1")
                t, s_attr = c.get("t"), c.get("s")
                v = c.find("%sv" % _NS)
                if t == "inlineStr":
                    is_el = c.find("%sis" % _NS)
                    val = "".join(x.text or "" for x in is_el.iter("%st" % _NS)) if is_el is not None else ""
                elif v is None:
                    val = ""
                elif t == "s":
                    val = shared[int(v.text)] if v.text and int(v.text) < len(shared) else ""
                elif t == "b":
                    val = "true" if v.text == "1" else "false"
                else:
                    val = v.text or ""
                    if s_attr is not None and int(s_attr) in date_styles:
                        val = _excel_serial_to_iso(val)
                    elif val.endswith(".0"):
                        val = val[:-2]
                cells[idx] = val
            grid.append(cells)

    if not grid:
        return []
    header_cells = grid[0]
    width = max(header_cells) + 1 if header_cells else 0
    headers = [str(header_cells.get(i, "")).strip() for i in range(width)]
    while headers and not headers[-1]:
        headers.pop()
    if not headers:
        return []

    out = []
    for cells in grid[1:]:
        row = {h: str(cells.get(i, "")).strip() for i, h in enumerate(headers) if h}
        if any(row.values()):                 # a run of blank rows under the data is not data
            out.append(row)
    return out


def split_spec(spec):
    """`book.xlsx#Contacts` -> (path, "Contacts"). A bare path keeps its `#`, which is legal in
    a filename, whenever that path exists on disk."""
    if "#" in spec and not os.path.exists(spec):
        path, _, sheet = spec.rpartition("#")
        return path, (sheet or None)
    return spec, None


def read_table(spec):
    """Read one table from wherever it lives: a CSV, a TSV, or one tab of an Excel workbook.

    A Google Sheet is not readable from here — it needs credentials this skill does not take and
    must never ask for. Export the tab (File -> Download -> Comma-separated values) and point at
    the file, or have an agent with a Drive connector fetch it first.
    """
    path, sheet = split_spec(spec)
    if not os.path.exists(path):
        low = str(spec).lower()
        if low.startswith("http") and "docs.google.com" in low:
            raise SystemExit(
                "That is a Google Sheets link, and this reads files on disk — it takes no "
                "credentials and will not ask for any.\n"
                "  In the sheet: File -> Download -> Comma-separated values (.csv), once per tab\n"
                "  (that downloads the tab you are looking at, so switch tabs and repeat)\n"
                "Then point me at the two files. If your agent has a Google Drive connector, it "
                "can fetch them for you instead.")
        raise SystemExit("no such file: %s" % path)
    if path.lower().endswith((".xlsx", ".xlsm")):
        return read_xlsx(path, sheet)
    if path.lower().endswith(".xls"):
        raise SystemExit(
            "%s is the old binary .xls format, which this cannot read. Open it and use "
            "File -> Save As -> .xlsx, or export each tab as CSV." % os.path.basename(path))
    if sheet:
        raise SystemExit("%s is not a workbook, so it has no tab %r" % (path, sheet))
    return read_csv(path)


_COMPANY_TAB_HINTS = ("compan", "account", "organi", "firm", "business", "target")
_CONTACT_TAB_HINTS = ("contact", "people", "person", "lead", "customer", "prospect")


def propose_sheets(names):
    """Guess which tab is which, so a workbook can be shown mapped rather than interrogated."""
    out = {}
    for entity, hints in (("companies", _COMPANY_TAB_HINTS), ("contacts", _CONTACT_TAB_HINTS)):
        for n in names:
            if any(h in (n or "").lower() for h in hints):
                out[entity] = n
                break
    return out


def keyed_rows(rows, mapping, entity):
    """Attach a row key to every row, flagging the second sighting of one rather than losing it."""
    spec = mapping.get("row_key", {}).get(entity, {})
    col, domain_col, name_col = spec.get("column"), spec.get("domain_column"), spec.get("name_column")
    out, seen = [], set()
    for i, row in enumerate(rows):
        if col and not blank(row.get(col)):
            key, rule = str(row[col]).strip(), "column"
        else:
            key, rule = mint_row_key(row, domain_col, name_col)
        dup = bool(key) and key in seen
        if key:
            seen.add(key)
        out.append({"row": row, "row_key": key, "key_rule": rule, "duplicate": dup, "index": i})
    return out


# --------------------------------------------------------------------------- the coverage report

_ROW_KEY_HINTS = ("id", "key", "uuid", "ref", "slug")
_DOMAIN_HINTS = ("domain", "website", "url", "site", "web")
_NAME_HINTS = ("company", "account", "org", "name", "employer")


def _propose(cols, rows, hints, unique_wanted=False, exclude=(), prefer=()):
    """Pick the column whose NAME reads like the thing, preferring one that is actually usable.

    A proposal, never a decision: it is shown beside two real values so a wrong guess is visible
    next to the right answer, which is cheaper for the installer than being asked to recall their
    own headers.

    `prefer` carries the tokens that make a match SPECIFIC rather than merely plausible. Without
    it a contacts file proposes `contact_id` as the column pointing at a company, because `id`
    matches and it is a character shorter than `company_key` — a guess that is confidently wrong
    and reads as if the file had been understood.
    """
    best = None
    for c in cols:
        low = c.lower()
        if c in exclude or not any(h in low for h in hints):
            continue
        vals = [r.get(c) for r in rows]
        filled = sum(1 for v in vals if not blank(v))
        uniq = len({str(v).strip() for v in vals if not blank(v)})
        specific = any(p in low for p in prefer)
        # A foreign key repeats; a row key does not. Where uniqueness is not wanted, fewer
        # distinct values than rows is evidence the column points at something else.
        repeats = 0 if unique_wanted else (1 if 0 < uniq < len(vals) else 0)
        score = (int(specific), repeats, filled, uniq if unique_wanted else 0, -len(c))
        if best is None or score > best[0]:
            best = (score, c)
    return best[1] if best else None


def inspect(rows, entity):
    """Propose a mapping: every column, its inferred type, two real values, its blank count — and
    which columns look like the row key, the domain and the company reference."""
    cols = list(rows[0].keys()) if rows else []
    report = []
    for c in cols:
        vals = [r.get(c) for r in rows]
        nonblank = [v for v in vals if not blank(v)]
        report.append({
            "column": c,
            "inferred_type": infer_type(vals),
            "samples": [str(v).strip() for v in nonblank[:2]],
            "blank": len(vals) - len(nonblank),
            "rows": len(vals),
        })

    # Every proposal excludes the row key and names the tokens that make a match SPECIFIC. Both
    # guards were added because a realistic export defeated the naive version three times: a
    # `pricing_page_url` column beat `website` for "the domain" on `url`, `company_id` beat
    # `company_name` for "the name" on `company`, and `contact_id` beat `company_key` for "the
    # company this contact belongs to" on `id`. Each guess was confident, wrong, and read as if
    # the file had been understood.
    proposed = {}
    rk = _propose(cols, rows, _ROW_KEY_HINTS, unique_wanted=True)
    proposed["row_key_column"] = rk
    skip = (rk,) if rk else ()
    if entity == "companies":
        proposed["domain_column"] = _propose(cols, rows, _DOMAIN_HINTS, exclude=skip,
                                             prefer=("domain", "website"))
        proposed["name_column"] = _propose(cols, rows, _NAME_HINTS, exclude=skip,
                                           prefer=("name",))
        if not rk:
            proposed["mint_from"] = ("domain, falling back to a slug of the name"
                                     if proposed["domain_column"] else "a slug of the name")
    else:
        proposed["company_ref_column"] = _propose(
            cols, rows, tuple(h for h in _NAME_HINTS + _ROW_KEY_HINTS if h != "name"),
            exclude=skip, prefer=("company", "account", "org", "employer"))

    return {"entity": entity, "rows": len(rows), "columns": report, "proposed": proposed}


def shared_join_columns(company_rows, contact_rows):
    """Columns that appear on BOTH tables and whose values overlap.

    A column carrying the same name and the same values on both sheets is the join the file was
    built around, and it is a far stronger signal than any word list. Missed on a cold run: both
    tabs carried `acct_code` with identical values, and the proposal keyed companies on their
    domain instead — which two of the six companies did not have.

    Returns a list of (column, how many contact values resolve, how many contact rows), best
    first. Empty when the two tables share no such column.
    """
    if not company_rows or not contact_rows:
        return []
    shared = set(company_rows[0].keys()) & set(contact_rows[0].keys())
    out = []
    for col in sorted(shared):
        have = {str(r.get(col)).strip() for r in company_rows if not blank(r.get(col))}
        if not have:
            continue
        hits = sum(1 for r in contact_rows
                   if not blank(r.get(col)) and str(r[col]).strip() in have)
        if hits:
            out.append((col, hits, len(contact_rows)))
    return sorted(out, key=lambda t: -t[1])


def check(rows, mapping, entity, company_keys=None):
    """Everything that decides whether the load works, counted before anything is written."""
    kr = keyed_rows(rows, mapping, entity)
    fields = mapping.get("fields", {}).get(entity, {})

    no_key, dup_row_key, loadable = [], [], []
    by_match, orphan, unusable = {}, [], {}
    orphan_domains, orphan_domain_source, orphan_no_domain = {}, {}, []
    ref_col = mapping.get("company_ref_column")

    for item in kr:
        if item["duplicate"]:
            dup_row_key.append(item["row_key"])
            continue
        for k, v in unusable_match_values(item["row"], mapping, entity):
            unusable.setdefault(k, []).append(v)
        key, val = choose_match_key(item["row"], mapping, entity)
        if not key:
            no_key.append(item["row_key"] or "row %d" % (item["index"] + 2))
            continue
        by_match.setdefault((key, val), []).append(item["row_key"])
        loadable.append(item)
        if entity == "contacts" and company_keys is not None:
            ref = item["row"].get(ref_col) if ref_col else None
            if blank(ref) or str(ref).strip() not in company_keys:
                orphan.append(item["row_key"])
                # An orphan is not one outcome. It either carries a domain — in which case its
                # company can be found in the table or created — or it carries nothing to go
                # on, which no option can rescue. The gate needs those apart.
                d, src = company_domain_for_contact(item["row"], mapping)
                if d:
                    orphan_domains.setdefault(d, []).append(item["row_key"])
                    orphan_domain_source[src] = orphan_domain_source.get(src, 0) + 1
                else:
                    orphan_no_domain.append(item["row_key"])

    collisions = {"%s=%s" % k: v for k, v in by_match.items() if len(v) > 1}

    # The one to lead with: values that would fail their whole batch, or tempt a retype to text.
    coercion = {}
    for col, spec in fields.items():
        ftype = spec["type"] if isinstance(spec, dict) else spec
        bad = [str(i["row"].get(col)).strip() for i in loadable
               if not parses_as(i["row"].get(col), ftype)]
        if bad:
            coercion[col] = {"type": ftype, "failing": len(bad), "examples": bad[:2],
                             "carried": sum(1 for i in loadable if not blank(i["row"].get(col)))}

    # The company link is the one thing that fails ENTIRELY SILENTLY when it is misconfigured: a
    # wrong or missing `company_ref_column` unlinks every contact, every row still loads, and the
    # run reports success. So it gets its own three-state answer rather than being folded into the
    # orphan count, where "0 orphans" reads the same whether the join worked or was never wired.
    link = None
    if entity == "contacts":
        if not ref_col:
            link = {"state": "NOT CONFIGURED", "resolvable": 0,
                    "detail": "the mapping has no `company_ref_column`, so NO contact can be "
                              "linked to a company"}
        elif ref_col not in (rows[0].keys() if rows else []):
            link = {"state": "COLUMN NOT IN FILE", "resolvable": 0,
                    "detail": "`%s` is not a column in the contacts file" % ref_col}
        elif company_keys is None:
            link = {"state": "not checked", "resolvable": None,
                    "detail": "pass the companies file too and this is counted"}
        else:
            n = sum(1 for i in loadable
                    if not blank(i["row"].get(ref_col))
                    and str(i["row"][ref_col]).strip() in company_keys)
            link = {"state": "ok" if n else "NOTHING RESOLVES", "resolvable": n,
                    "detail": "%d of %d loadable contacts resolve to a company in the companies "
                              "file via `%s`" % (n, len(loadable), ref_col)}

    return {
        "entity": entity,
        "rows": len(rows),
        "loadable": len(loadable),
        "company_link": link,
        "no_match_key": no_key,
        "duplicate_row_key": dup_row_key,
        "match_key_collisions": collisions,
        "collapsing_rows": sum(len(v) for v in collisions.values()),
        "collapsing_into": len(collisions),
        "orphan_contacts": orphan,
        "orphan_company_domains": orphan_domains,
        "orphan_domain_source": orphan_domain_source,
        "orphan_no_domain": orphan_no_domain,
        "unusable_match_values": unusable,
        "coercion_failures": coercion,
        "by_match_key": _count_by_key(loadable, mapping, entity),
    }


def _count_by_key(loadable, mapping, entity):
    counts = {}
    for item in loadable:
        key, _ = choose_match_key(item["row"], mapping, entity)
        counts[key] = counts.get(key, 0) + 1
    return counts


# --------------------------------------------------------------------------- one row's values

BASE_COLUMNS = {
    # Every table has these, typed text, plus `id bigserial` and the UNIQUE `match_key`. A mapped
    # field whose column is one of them reuses it rather than adding a second.
    "companies": ("row_key", "domain", "linkedin_url", "org_name"),
    "contacts": ("row_key", "email", "linkedin_url", "phone"),
}
_IDENT = re.compile(r"[a-z_][a-z0-9_]{0,62}")


def ident(name):
    """A column name from a label: `TAM ICP tier` -> `tam_icp_tier`. Deterministic."""
    s = re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")
    return ("c_" + s) if s[:1].isdigit() else s


def column_for(col, spec):
    """The column a mapped field lands in: its `field_id` when it names one, else its label."""
    spec = spec if isinstance(spec, dict) else {"type": spec}
    return spec.get("field_id") or ident(spec.get("field_name") or col)


def qident(name):
    """Quote an identifier, refusing anything that is not a plain lower-case name. Column and
    table names come from a mapping file, and a mapping file is input."""
    if not isinstance(name, str) or not _IDENT.fullmatch(name):
        raise ValueError("not a safe column or table name: %r" % (name,))
    return '"%s"' % name


def table_name(prefix, entity):
    """`storage.<prefix>_<entity>`. Writes are only allowed to schema-qualified `storage` tables."""
    qident(prefix)
    return "storage.%s_%s" % (prefix, entity)


def sql_literal(v):
    """A value as a SQL string literal. THE trust boundary of this loader: every value in a TAM
    file is somebody else's text, and it is spliced into SQL here and nowhere else.

    Quotes are doubled, which is complete under `standard_conforming_strings = on` (verified on
    the customer DB: backslashes are literal there). A NUL byte cannot be stored in text at all,
    so it is refused rather than truncated. Numbers and dates arrive as strings that have already
    passed `parses_as`; they are quoted too, and the destination column does the cast."""
    if v is None:
        return "NULL"
    s = str(v)
    if "\x00" in s:
        raise ValueError("a NUL byte cannot be written: %r" % s[:40])
    return "'" + s.replace("'", "''") + "'"


def pg_value(v, field_type):
    """The string written for a value that has already passed `parses_as`."""
    s = str(v).strip()
    if field_type == "number":
        return s.replace(",", "").replace(" ", "")
    if field_type == "date":
        return _iso_date(s)
    if field_type == "boolean":
        return "true" if s.lower() in _TRUE else "false"
    return s


def build_payload(item, mapping, entity, company_record_id=None):
    """One row's column values, plus the fields dropped on the way.

    A blank is ABSENT, never sent: an absent column becomes NULL, and the upsert keeps whatever
    the record already held (`COALESCE(EXCLUDED.c, t.c)`), so a re-load never empties a field.
    A value its type cannot parse is dropped and named, because sent it would fail the whole batch.
    """
    row = item["row"]
    key, val = choose_match_key(row, mapping, entity)
    if not key:
        raise ValueError("row %s carries no match key and must not be written" % item["row_key"])

    payload = {"row_key": item["row_key"]}
    dropped = []
    for col, spec in mapping.get("fields", {}).get(entity, {}).items():
        ftype = spec["type"] if isinstance(spec, dict) else spec
        v = row.get(col)
        if blank(v):
            continue
        if not parses_as(v, ftype):
            dropped.append(col)            # sent, it would fail every row in its batch
            continue
        payload[column_for(col, spec)] = pg_value(v, ftype)

    # The match key goes in LAST and wins. A key is usually also a mapped field — `domain` is
    # both — and it must be the normalised value: the record then stores the value it was matched
    # on, and `https://www.a.example/` does not become a second record beside `a.example`.
    payload[key] = val
    payload["match_key"] = "%s:%s" % (key, val)

    linked = False
    if entity == "contacts" and not blank(company_record_id):
        payload["company_id"] = str(company_record_id).strip()
        linked = True

    return {"payload": payload, "dropped_fields": dropped, "match_key": key,
            "match_value": val, "linked": linked}


def batches(built_items, size):
    """Split into batches of at most `size` with no `match_key` twice in one batch. Postgres
    refuses an upsert that would touch the same row twice in one statement ("ON CONFLICT DO
    UPDATE command cannot affect row a second time"), and the refusal fails the whole batch."""
    out, cur, seen = [], [], set()
    for b in built_items:
        mk = b["payload"]["match_key"]
        if len(cur) >= size or mk in seen:
            out.append(cur)
            cur, seen = [], set()
        cur.append(b)
        seen.add(mk)
    if cur:
        out.append(cur)
    return out


def upsert_sql(table, payloads):
    """One INSERT for a batch. On a match it fills only what the row carried and keeps the rest,
    and RETURNING hands back the id per match key — the positive evidence a ledger row settles on."""
    cols = sorted({c for p in payloads for c in p})
    head = "INSERT INTO %s AS t (%s) VALUES\n" % (table, ", ".join(qident(c) for c in cols))
    rows = ",\n".join("(%s)" % ", ".join(sql_literal(p.get(c)) for c in cols) for p in payloads)
    sets = ", ".join("%s = COALESCE(EXCLUDED.%s, t.%s)" % (qident(c), qident(c), qident(c))
                     for c in cols if c != "match_key")
    return (head + rows + "\nON CONFLICT (match_key) DO "
            + ("UPDATE SET %s" % sets if sets else "NOTHING")
            + "\nRETURNING id, match_key")


def ddl(prefix, entity, columns):
    """CREATE TABLE IF NOT EXISTS plus one ADD COLUMN IF NOT EXISTS per mapped column — every
    statement idempotent, so a second build over the same prefix creates only what is missing.
    `columns` is {column: loader type}. Contacts carry `company_id`, a real foreign key: the link
    is a value the database enforces and anyone can query, not an inference from a domain."""
    t = table_name(prefix, entity)
    base = ", ".join("%s text" % qident(c) for c in BASE_COLUMNS[entity])
    extra = ""
    if entity == "contacts":
        extra = ", company_id bigint REFERENCES %s(id)" % table_name(prefix, "companies")
    out = ["CREATE TABLE IF NOT EXISTS %s (id bigserial PRIMARY KEY, match_key text NOT NULL "
           "UNIQUE, %s%s)" % (t, base, extra)]
    for c, ftype in sorted(columns.items()):
        if c in BASE_COLUMNS[entity]:
            continue
        out.append("ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s %s" % (t, qident(c), PG_TYPE[ftype]))
    return out


def db(sql, max_rows=None):
    """Run one statement through `deepline db query` and return its JSON (`rows`, `row_count`).

    The SQL goes through a file (`--sql @file`): a batch is too long for an argument and carries
    real contact data, which an argument would show in `ps`. A non-zero exit raises."""
    import subprocess
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".sql")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(sql)
        cmd = ["deepline", "db", "query", "--sql", "@" + path, "--json"]
        if max_rows:
            cmd += ["--max-rows", str(max_rows)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    finally:
        os.unlink(path)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "deepline db query failed").strip()[:400])
    return json.loads(r.stdout)


# --------------------------------------------------------------------------- the ledger

def fold_ledger(path):
    """Index a ledger by row key, last line wins. A torn final line costs one row, not the file."""
    settled = {}
    if not os.path.exists(path):
        return settled
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue                   # a process killed mid-write leaves partial JSON
            if rec.get("status") in SETTLED and rec.get("row_key"):
                settled[rec["row_key"]] = rec
    return settled


def remaining(rows_with_keys, ledger_path):
    """What is left, derived from disk rather than remembered. Never stored."""
    settled = fold_ledger(ledger_path)
    return [i for i in rows_with_keys if i["row_key"] not in settled]


def company_id_map(company_ledger_path):
    """Fold the company ledger into row key -> company record id (`id` in the companies table).

    This IS the read-back. The id came back from each company's own upsert, free and at the
    moment it was known; nothing looks a company up again.
    """
    out = {}
    for key, rec in fold_ledger(company_ledger_path).items():
        if rec.get("status") == "completed" and rec.get("entity_id"):
            out[key] = rec["entity_id"]
    return out


def ledger_line(row_key, status, **kw):
    rec = {"row_key": row_key, "status": status}
    rec.update(kw)
    return json.dumps(rec, sort_keys=True)


def _last_byte(path):
    with open(path, "rb") as fh:
        fh.seek(-1, os.SEEK_END)
        return fh.read(1)


def append_settled(path, line):
    """One row settles, one line is appended, immediately. Never a batch."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    # A process killed mid-write leaves a line with no newline. Appending straight onto it welds
    # the two together and loses BOTH — the torn row and the first row of the resumed run. Cost
    # one row for the torn line, never two.
    torn = os.path.exists(path) and os.path.getsize(path) > 0 and _last_byte(path) != b"\n"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(("\n" if torn else "") + line + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def counts_by_status(path):
    tally = {}
    if not os.path.exists(path):
        return tally
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            tally[rec.get("status", "?")] = tally.get(rec.get("status", "?"), 0) + 1
    return tally


# --------------------------------------------------------------------------- cli

def _print_inspect(rep):
    print("\n%s — %d rows" % (rep["entity"], rep["rows"]))
    print("%-28s %-9s %-7s %s" % ("column", "type", "blank", "two values"))
    for c in rep["columns"]:
        print("%-28s %-9s %-7d %s" % (c["column"][:28], c["inferred_type"], c["blank"],
                                      " | ".join(c["samples"])[:60]))
    print("  proposed, correct any of these:")
    for k, v in rep["proposed"].items():
        print("    %-20s %s" % (k, v if v else "none found"))


def _print_check(rep):
    print("\n%s — %d rows, %d loadable" % (rep["entity"], rep["rows"], rep["loadable"]))
    print("  no match key ............. %d" % len(rep["no_match_key"]))
    print("  duplicate row key ........ %d" % len(rep["duplicate_row_key"]))
    print("  sharing a match key ...... %d rows into %d records"
          % (rep["collapsing_rows"], rep["collapsing_into"]))
    if rep["entity"] == "contacts":
        link = rep["company_link"] or {}
        print("  COMPANY LINK ............. %s — %s" % (link.get("state"), link.get("detail")))
        print("  company not in companies . %d" % len(rep["orphan_contacts"]))
        if rep["orphan_contacts"]:
            print("      of those, %d have a company domain to go on (%d distinct companies, from %s)"
                  % (len(rep["orphan_contacts"]) - len(rep["orphan_no_domain"]),
                     len(rep["orphan_company_domains"]),
                     rep["orphan_domain_source"] or "nothing"))
            print("      and %d have none, so nothing can link them"
                  % len(rep["orphan_no_domain"]))
    print("  matched by ............... %s" % (rep["by_match_key"] or "-"))
    if rep["unusable_match_values"]:
        print("  values that are not that kind of key — present, and refused like a blank:")
        for k, vals in rep["unusable_match_values"].items():
            print("    %-24s %d   e.g. %s" % (k, len(vals), ", ".join(vals[:2])))
    if rep["coercion_failures"]:
        print("  values their type cannot parse — sent, each one fails its whole batch:")
        for col, d in rep["coercion_failures"].items():
            print("    %-24s %s  %d of %d carried   e.g. %s"
                  % (col, d["type"], d["failing"], d["carried"], ", ".join(d["examples"])))
    else:
        print("  values their type cannot parse: none")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("inspect", "check", "sheets"))
    ap.add_argument("--companies", metavar="FILE[#TAB]",
                    help="a CSV, a TSV, or one tab of an .xlsx as `book.xlsx#Companies`")
    ap.add_argument("--contacts", metavar="FILE[#TAB]")
    ap.add_argument("--map")
    a = ap.parse_args(argv)

    if a.command == "sheets":
        for spec in (a.companies, a.contacts):
            if not spec:
                continue
            path, _ = split_spec(spec)
            names = list_sheets(path)
            guess = propose_sheets(names)
            print("%s — %d tabs:" % (os.path.basename(path), len(names)))
            for n in names:
                mine = [e for e in ("companies", "contacts") if guess.get(e) == n]
                print("  %-34s %s" % (n, ("looks like the %s tab" % mine[0]) if mine else ""))
            unnamed = [e for e in ("companies", "contacts") if not guess.get(e)]
            if unnamed:
                # Same rule as field matching: the tab names are a fact, which of them is which is
                # a judgment, and a tab called "Buying Group" or "Q4 Targets" belongs to whoever
                # can read it rather than to a list of words somebody thought of in advance.
                print("\n  Nothing in the names above says which tab is %s. That is yours to "
                      "decide — read the tab names, and where they do not settle it run `inspect` "
                      "on each and look at the columns." % " or ".join(unnamed))
            print("\n  read a tab with:  --companies '%s#<tab>'" % path)
        return 0

    if a.command == "inspect":
        tables = {}
        for entity, path in (("companies", a.companies), ("contacts", a.contacts)):
            if path:
                tables[entity] = read_table(path)
                _print_inspect(inspect(tables[entity], entity))
        if len(tables) == 2:
            shared = shared_join_columns(tables["companies"], tables["contacts"])
            print("\ncolumns on BOTH tables whose values line up — the likeliest join:")
            for col, hits, total in shared[:3]:
                print("    %-24s %d of %d contacts resolve to a company through it"
                      % (col, hits, total))
            if not shared:
                print("    none — the two tables share no column with overlapping values, so the "
                      "join has to be named explicitly")
        return 0

    if not a.map:
        ap.error("check needs --map")
    mapping = json.load(open(a.map, encoding="utf-8"))
    company_keys = None
    if a.companies:
        co = read_table(a.companies)
        company_keys = {i["row_key"] for i in keyed_rows(co, mapping, "companies") if i["row_key"]}
        _print_check(check(co, mapping, "companies"))
    if a.contacts:
        if company_keys is None:
            print("\n!! --companies was not given, so the company link cannot be checked. Every "
                  "contact could load with no company attached and this report would not say so.")
        _print_check(check(read_table(a.contacts), mapping, "contacts", company_keys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
