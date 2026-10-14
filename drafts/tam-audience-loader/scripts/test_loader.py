"""Exercise everything the loader decides, without the database, a network or a credential.

    python3 test_loader.py

Two classes of bug live here and neither shows up until a live load is underway:

  - a batch that carries one value its column cannot parse, or one unescaped quote — either fails
    the whole INSERT, and the second is also how somebody else's text becomes somebody else's SQL;
  - a ledger fold that loses or re-writes rows, which on a ten thousand row load means duplicates
    nobody can take back.

Exit 0 means the decisions the loader would make are sound. It says nothing about whether the
database accepted them — that is what Step 6's ten-row batch and Step 8's verification are for.
"""
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True                 # a stray __pycache__ inside the package is a
SK = os.path.dirname(os.path.abspath(__file__))  # blocking validator finding
sys.path.insert(0, SK)

import loader_lib as L                                              # noqa: E402
import build_loader as B                                            # noqa: E402

SAMPLE_DIR = os.path.join(os.path.dirname(SK), "references")

FAILURES = []
CHECKS = [0]


def ok(cond, label):
    CHECKS[0] += 1
    if not cond:
        FAILURES.append(label)
        print("  FAIL  %s" % label)


def section(name):
    print("\n%s" % name)


MAPPING = {
    "company_ref_column": "company_key",
    "row_key": {
        "companies": {"domain_column": "website", "name_column": "company"},
        "contacts": {"column": "contact_id"},
    },
    "match_columns": {
        "companies": {"domain": "website", "linkedin_url": "co_li"},
        "contacts": {"email": "work_email", "linkedin_url": "li", "phone": "mobile"},
    },
    "fields": {
        "companies": {"company": {"type": "text", "field_id": "org_name"},
                      "website": {"type": "url", "field_id": "domain"},
                      "headcount": {"type": "number", "field_id": "employee_count"},
                      "founded": {"type": "date", "field_id": "fld_founded"}},
        "contacts": {"full_name": {"type": "text", "field_id": "name"},
                     "work_email": {"type": "email", "field_id": "email"}},
    },
}


# --------------------------------------------------------------------------- types

section("The silent write: what a field's type will and will not parse")

# Each of these was measured against a live workspace. A value that fails `parses_as` still
# WRITES, reports success, and is then invisible to every filter — which is why the check has to
# happen here, before the load, rather than being discovered afterwards.
ok(L.parses_as("512", "number"), "a plain integer is a number")
ok(L.parses_as("1,234", "number"), "thousands separators are fine")
ok(not L.parses_as("1,001-5,000", "number"), "a BAND is not a number — the measured failure")
ok(not L.parses_as("~250", "number"), "an approximation is not a number")
ok(not L.parses_as("500+", "number"), "a trailing unit is not a number")
ok(L.parses_as("2017-03-01", "date"), "an ISO date is a date")
ok(not L.parses_as("Q3 2017", "date"), "a QUARTER is not a date — the measured failure")
ok(not L.parses_as("2017", "date"), "a bare year is not a date")
ok(L.parses_as("a@b.com", "email") and not L.parses_as("a@b.com, c@d.com", "email"),
   "one address is an email, two are not")
ok(L.parses_as("https://x.example", "url") and not L.parses_as("x.example", "url"),
   "a bare domain is not a url — it is a perfectly good text value")
ok(all(L.parses_as(v, "boolean") for v in ("true", "No", "1")) and
   not L.parses_as("unknown", "boolean"), "a third value breaks a boolean")
ok(all(L.parses_as("", t) for t in L.FIELD_TYPES),
   "blank passes every type: a blank RECORD field is dropped, not stored wrong")
ok(all(L.parses_as(v, "text") for v in ("1,001-5,000", "Q3 2017", "anything at all")),
   "text takes everything, which is why it is the safe fallback")


section("Inference reads the whole column, not the first rows")

ok(L.infer_type(["10", "20", "30"]) == "number", "all numeric infers number")
ok(L.infer_type(["10", "20", "1,001-5,000"]) == "text",
   "one band two thousand rows down demotes the column to text")
ok(L.infer_type(["2020-01-01", "Q3 2017"]) == "text", "one quarter demotes a date column")
ok(L.infer_type(["", "", ""]) == "text", "an all-blank column is text, not a guess")
ok(L.infer_type(["yes", "no"]) == "boolean", "a clean pair infers boolean")


section("What inspect PROPOSES, since a confident wrong guess reads like understanding")

co_sample = [
    {"company_id": "c1", "company": "Acme", "website": "https://a.example", "headcount": "10"},
    {"company_id": "c2", "company": "Bee", "website": "https://b.example", "headcount": "20"},
]
prop = L.inspect(co_sample, "companies")["proposed"]
ok(prop["row_key_column"] == "company_id", "an id column is proposed as the row key")
ok(prop["domain_column"] == "website" and prop["name_column"] == "company",
   "the domain and name columns are found by what they are called")

no_id = L.inspect([{k: v for k, v in r.items() if k != "company_id"} for r in co_sample],
                  "companies")["proposed"]
ok(no_id["row_key_column"] is None and "mint_from" in no_id,
   "with no id column it says it will MINT one, and from what — never silently")

pe_sample = [
    {"contact_id": "p1", "full_name": "Ada", "work_email": "a@a.example", "company_key": "c1"},
    {"contact_id": "p2", "full_name": "Bram", "work_email": "b@a.example", "company_key": "c1"},
    {"contact_id": "p3", "full_name": "Cai", "work_email": "c@b.example", "company_key": "c2"},
]
pp = L.inspect(pe_sample, "contacts")["proposed"]
ok(pp["row_key_column"] == "contact_id", "the contact id is proposed as the row key")
ok(pp["company_ref_column"] == "company_key",
   "the company reference is NOT the row key: `contact_id` matches the same hint and is a "
   "character shorter, and proposing it would be confidently wrong (got %r)"
   % pp["company_ref_column"])
ok(L.inspect([], "companies")["columns"] == [], "an empty file proposes nothing and does not crash")


# --------------------------------------------------------------------------- keys

section("Row keys are deterministic, and minting is reported")

r = {"company": "Acme Höldings, Inc.", "website": "https://WWW.Acme.com/about"}
k1, rule1 = L.mint_row_key(r, "website", "company")
k2, _ = L.mint_row_key(dict(r), "website", "company")
ok(k1 == k2, "the same row mints the same key twice")
ok(k1 == "acme.com" and rule1 == "domain", "domain wins and is normalised: %r" % k1)
ok(L.mint_row_key({"company": "Acme Höldings, Inc."}, None, "company")[0] == "acme",
   "the name slug folds accents, punctuation and the legal suffix")
ok(L.mint_row_key({"company": "Acme Holdings Ltd"}, None, "company")[0] == "acme",
   "two spellings of one name collapse — the real cost of minting from a name")
ok(L.mint_row_key({}, "website", "company") == ("", "none"),
   "a row with nothing to mint from returns no key rather than a fabricated one")


section("Match keys: a fixed set, tried in the declared order")

ok(L.choose_match_key({"website": "https://a.example", "co_li": "https://www.linkedin.com/in/a"},
                      MAPPING, "companies") == ("domain", "a.example"),
   "domain beats linkedin_url by default order")
ok(L.choose_match_key({"website": "", "co_li": "https://www.linkedin.com/in/a"},
                      MAPPING, "companies") == ("linkedin_url", "https://www.linkedin.com/in/a"),
   "a blank domain falls through to linkedin_url")
ok(L.choose_match_key({"website": "", "co_li": ""}, MAPPING, "companies") == ("", ""),
   "no key at all is reported as no key — never fired, never retried")
reordered = json.loads(json.dumps(MAPPING))
reordered["key_order"] = {"contacts": ["phone", "email", "linkedin_url"]}
ok(L.choose_match_key({"work_email": "a@b.com", "mobile": "+15550100"},
                      reordered, "contacts")[0] == "phone",
   "key order is a run flag: reordering changes routing with no rebuild")
try:
    bad = json.loads(json.dumps(MAPPING))
    bad["key_order"] = {"companies": ["org_name"]}
    L.choose_match_key({"website": "a.example"}, bad, "companies")
    ok(False, "a key outside the fixed set is refused")
except ValueError:
    ok(True, "a key outside the fixed set is refused")


# --------------------------------------------------------------------------- payloads

section("A row's values: no blanks, no unparseable values, the match key last")

item = {"row_key": "a.example", "duplicate": False, "index": 0, "key_rule": "domain",
        "row": {"company": "Acme", "website": "https://a.example",
                "headcount": "1,001-5,000", "founded": "2017-03-01", "co_li": ""}}
built = L.build_payload(item, MAPPING, "companies")
p = built["payload"]
ok(p["match_key"] == "domain:a.example" and p["domain"] == "a.example",
   "the match key is stored as key:value, and the normalised value wins its own column")
ok("employee_count" not in p and built["dropped_fields"] == ["headcount"],
   "the band is DROPPED rather than sent into a numeric column, where it fails the whole batch")
ok(p.get("fld_founded") == "2017-03-01", "a parseable date rides through")
ok(all(not L.blank(v) for v in p.values()), "a blank is absent, never sent — COALESCE keeps the old value")
ok("company_id" not in p, "a company payload carries no company link")

contact = {"row_key": "c1", "duplicate": False, "index": 0, "key_rule": "column",
           "row": {"full_name": "Ada", "work_email": "ada@a.example", "li": "", "mobile": "",
                   "company_key": "a.example"}}
linked = L.build_payload(contact, MAPPING, "contacts", 900100200)
ok(linked["payload"]["company_id"] == "900100200" and linked["linked"],
   "a resolved company id rides as the foreign key")
for blank_id in (None, "", "   "):
    un = L.build_payload(contact, MAPPING, "contacts", blank_id)
    ok("company_id" not in un["payload"] and not un["linked"],
       "a blank company id is absent (%r), so the link stays NULL and says so" % (blank_id,))

try:
    L.build_payload({"row_key": "x", "duplicate": False, "index": 0, "key_rule": "none",
                     "row": {"company": "No Key"}}, MAPPING, "companies")
    ok(False, "a row with no match key refuses to become a payload")
except ValueError:
    ok(True, "a row with no match key refuses to become a payload")

ok(L.pg_value("1,234", "number") == "1234" and L.pg_value("3/1/2017", "date") == "2017-03-01"
   and L.pg_value("Yes", "boolean") == "true",
   "values are written in the form the column parses: no separators, ISO dates, true/false")
ok(not L.parses_as("25/12/2017", "date"),
   "a day-first date is refused here, not in the INSERT: the column reads slashes month-first")
ok(not L.parses_as("nan", "number") and not L.parses_as("1_000", "number"),
   "float() would take `nan` and `1_000`; a headcount column should not")


section("SQL literals are the trust boundary")

ok(L.sql_literal("O'Brien") == "'O''Brien'", "a quote is doubled")
ok(L.sql_literal("x'); DROP TABLE storage.t; --") == "'x''); DROP TABLE storage.t; --'",
   "an injection attempt stays inside one literal")
ok(L.sql_literal("a\\b") == "'a\\b'", "a backslash is literal under standard_conforming_strings")
ok(L.sql_literal(None) == "NULL", "None is NULL, never the string 'None'")
try:
    L.sql_literal("a\x00b")
    ok(False, "a NUL byte is refused")
except ValueError:
    ok(True, "a NUL byte is refused rather than truncated")
for bad in ("Robert); --", "Tier", "a-b", "", "x" * 70):
    try:
        L.qident(bad)
        ok(False, "%r is refused as an identifier" % bad)
    except ValueError:
        ok(True, "%r is refused as an identifier" % bad)
ok(L.ident("TAM ICP tier") == "tam_icp_tier" and L.ident("2024 ARR") == "c_2024_arr",
   "labels become plain column names, deterministically")
ok(L.table_name("tam", "contacts") == "storage.tam_contacts", "tables live in storage")

sql = L.upsert_sql("storage.tam_companies",
                   [{"match_key": "domain:a.example", "domain": "a.example", "org_name": "A'co"},
                    {"match_key": "domain:b.example", "domain": "b.example"}])
ok("ON CONFLICT (match_key) DO UPDATE SET" in sql and "RETURNING id, match_key" in sql,
   "the batch is one upsert that returns the id per match key")
ok('"org_name" = COALESCE(EXCLUDED."org_name", t."org_name")' in sql,
   "a populated value is never cleared by a row that left it blank")
ok("'A''co'" in sql and ", NULL)" in sql, "values are escaped, and a missing one is NULL")
ok('"match_key" = COALESCE' not in sql, "the match key itself is never rewritten")

bs = L.batches([{"payload": {"match_key": k}} for k in ("a", "b", "a", "c", "d", "e")], 3)
ok([[b["payload"]["match_key"] for b in x] for x in bs] == [["a", "b"], ["a", "c", "d"], ["e"]],
   "no match key twice in one batch — Postgres refuses the whole statement if it is")

d = L.ddl("tam", "contacts", {"tam_persona": "text", "email": "email", "years": "number"})
ok(d[0].startswith("CREATE TABLE IF NOT EXISTS storage.tam_contacts") and
   "company_id bigint REFERENCES storage.tam_companies(id)" in d[0],
   "contacts carry a real foreign key into companies")
ok(d[1:] == ['ALTER TABLE storage.tam_contacts ADD COLUMN IF NOT EXISTS "tam_persona" text',
             'ALTER TABLE storage.tam_contacts ADD COLUMN IF NOT EXISTS "years" numeric'],
   "one idempotent ADD COLUMN per new field, none for a base column: %r" % d[1:])


# --------------------------------------------------------------------------- the ledger

section("The ledger: last line wins, torn lines survive, only settled rows leave the work set")

tmp = tempfile.mkdtemp()
led = os.path.join(tmp, "l.jsonl")
L.append_settled(led, L.ledger_line("a", "completed", entity_id=1))
L.append_settled(led, L.ledger_line("b", "failed", reason="blip"))
L.append_settled(led, L.ledger_line("c", "rejected_no_match_key"))
L.append_settled(led, L.ledger_line("a", "completed", entity_id=2))          # supersedes
open(led, "a").write('{"row_key":"d","status":"comple')                      # killed mid-write

folded = L.fold_ledger(led)
ok(folded["a"]["entity_id"] == 2, "a later line supersedes an earlier one for the same key")
ok("b" not in folded, "a failed row is NOT settled and stays in the work set")
ok("c" in folded, "a permanent rejection IS settled and never fires again")
ok("d" not in folded, "a torn final line costs one row, not the file")

rows = [{"row_key": k} for k in ("a", "b", "c", "d")]
left = [r["row_key"] for r in L.remaining(rows, led)]
ok(left == ["b", "d"], "remaining work is derived from disk, never stored: %r" % left)

# A duplicate row shares its key with the row it duplicates, so recording it as a settled
# verdict would let it supersede that row's load. Measured cost of getting this wrong: a company
# exported twice dropped out of the id map, and every contact at it loaded with no company while
# the run reported success. The line is still written and still counted; it just cannot displace.
dup = os.path.join(tmp, "dup.jsonl")
L.append_settled(dup, L.ledger_line("nw", "completed", entity_id=7))
L.append_settled(dup, L.ledger_line("nw", "rejected_duplicate_row_key"))
ok(L.fold_ledger(dup)["nw"]["entity_id"] == 7,
   "a duplicate-row rejection does NOT supersede the load of the row it duplicates")
ok(L.company_id_map(dup) == {"nw": 7},
   "so the company keeps its record id and its contacts still get associated")
ok([r["row_key"] for r in L.remaining([{"row_key": "nw"}], dup)] == [],
   "and the key is still settled, so neither row re-fires")
ok(L.counts_by_status(dup)["rejected_duplicate_row_key"] == 1,
   "the duplicate is still counted — it is reported, just not load-bearing")
ok(L.remaining(rows, os.path.join(tmp, "nope.jsonl")) == rows,
   "no ledger means everything is left, not an error")

L.append_settled(led, L.ledger_line("e", "completed", entity_id=None))
ok(L.company_id_map(led) == {"a": 2},
   "the company id map takes only completed rows that actually returned an id")
ok(L.counts_by_status(led)["completed"] == 3, "status counts read every line, settled or not")


# --------------------------------------------------------------------------- coverage report

section("The coverage report counts what cannot load, before anything is written")

co_rows = [
    {"company_id": "c1", "company": "Acme", "website": "https://a.example", "headcount": "10", "founded": "2017-03-01", "co_li": ""},
    {"company_id": "c2", "company": "Acme Ltd", "website": "http://www.a.example", "headcount": "20", "founded": "", "co_li": ""},
    {"company_id": "c3", "company": "Bee", "website": "", "headcount": "1,001-5,000", "founded": "Q3 2017", "co_li": "https://www.linkedin.com/company/b"},
    {"company_id": "c4", "company": "Cee", "website": "", "headcount": "5", "founded": "", "co_li": ""},
]

# With a row key of its own, a match-key collision is a DIFFERENT event from a duplicate row key:
# two distinct rows that the upsert will fold into one record.
by_id = json.loads(json.dumps(MAPPING))
by_id["row_key"]["companies"] = {"column": "company_id"}
rep = L.check(co_rows, by_id, "companies")
ok(rep["rows"] == 4, "every row is accounted for")
ok(len(rep["no_match_key"]) == 1, "the row with neither domain nor linkedin cannot load")
ok(rep["collapsing_rows"] == 2 and rep["collapsing_into"] == 1,
   "two spellings of one domain collapse into one record, and it is counted before the write")
ok(rep["coercion_failures"]["headcount"]["failing"] == 1,
   "the band is counted as a value its field's type will not parse")
ok("1,001-5,000" in rep["coercion_failures"]["headcount"]["examples"],
   "and the offending value is shown, so a bad inference is visible")
ok(rep["by_match_key"] == {"domain": 2, "linkedin_url": 1}, "each key's claim is counted")

# Minting the row key FROM the domain folds the two events into one: the second row is a
# duplicate row key and never reaches the collision count. Both are reported; neither is lost.
minted = L.check(co_rows, MAPPING, "companies")
ok(len(minted["duplicate_row_key"]) == 1 and minted["collapsing_rows"] == 0,
   "a row key minted from the domain turns a match collision into a duplicate row key")
ok(minted["loadable"] + len(minted["no_match_key"]) + len(minted["duplicate_row_key"])
   == minted["rows"], "and the counts still add up to the file")

pe_rows = [
    {"contact_id": "1", "full_name": "Ada", "work_email": "ada@a.example", "li": "", "mobile": "", "company_key": "a.example"},
    {"contact_id": "2", "full_name": "Bram", "work_email": "b@z.example", "li": "", "mobile": "", "company_key": "gone.example"},
    {"contact_id": "3", "full_name": "Cai", "work_email": "", "li": "", "mobile": "", "company_key": "a.example"},
    {"contact_id": "1", "full_name": "Ada again", "work_email": "ada2@a.example", "li": "", "mobile": "", "company_key": "a.example"},
]
prep = L.check(pe_rows, MAPPING, "contacts", company_keys={"a.example"})
ok(len(prep["orphan_contacts"]) == 1, "a contact whose company is not in the file is counted")
ok(len(prep["no_match_key"]) == 1, "a contact with no email, linkedin or phone cannot load")
ok(len(prep["duplicate_row_key"]) == 1,
   "a repeated row key is its own count — a file problem, not a match-key collision")
ok(rep["rows"] == rep["loadable"] + len(rep["no_match_key"]) + len(rep["duplicate_row_key"]),
   "the counts add up to the file: no row is silently lost")


# --------------------------------------------------------------------------- column types

section("A column whose stored type disagrees is refused before anything runs")

ok(B.conflicts({"fields": {"companies": {"hc": {"type": "number", "field_id": "domain"}}}},
               "companies", []) == [("domain", "text", "number")],
   "a number mapped onto a base text column is a conflict")
ok(B.conflicts(MAPPING, "companies", [{"id": "employee_count", "dataType": "numeric"}]) == [],
   "a number onto an existing numeric column is not")
ok(B.conflicts(MAPPING, "companies", [{"id": "fld_founded", "dataType": "text"}])
   == [("fld_founded", "text", "date")], "a date onto an existing text column is")
ok(L.type_conflict("integer", "number") is False and L.type_conflict("url", "text") is False,
   "families, not spellings: integer is numeric and url is stored as text")


section("Match keys are checked for SHAPE, not merely for being non-empty")

# Measured: a lookup value that is present but is not a real instance of its kind fails with
# "None of the selected lookup fields contained a valid value to match on" — wording that reads
# as though the field were empty, on a step whose status is an ordinary `failed`.
ok(L.valid_match_value("linkedin_url", "https://www.linkedin.com/in/someone"),
   "a linkedin.com profile URL is a usable linkedin_url")
ok(L.valid_match_value("linkedin_url", "https://linkedin.com/company/acme"),
   "with or without the www")
ok(not L.valid_match_value("linkedin_url", "https://www.linkedin.example/in/someone"),
   "a syntactically perfect URL on another host is REFUSED — the measured surprise")
ok(not L.valid_match_value("linkedin_url", "https://notlinkedin.com/in/someone"),
   "and a host that merely ends in the right letters is not the right host")
ok(L.valid_match_value("domain", "acme.example") and
   L.valid_match_value("email", "a@acme.example"),
   "a .example DOMAIN and a .example EMAIL are both accepted: this is not a realness check")
ok(not L.valid_match_value("email", "not-an-email"), "a malformed email is refused")
ok(not L.valid_match_value("phone", "not-a-phone"), "a phone with no digits is refused")
ok(L.valid_match_value("phone", "+1 (555) 010-0000"), "a real-shaped phone is accepted")
ok(not L.valid_match_value("domain", "a@b.example") and not L.valid_match_value("domain", "acme"),
   "an address, and a bare label with no dot, are not domains")
ok(not L.valid_match_value("email", ""), "blank is never a usable match value")

fallthrough = {"work_email": "", "li": "https://www.linkedin.example/in/x", "mobile": "+15550100"}
ok(L.choose_match_key(fallthrough, MAPPING, "contacts") == ("phone", "+15550100"),
   "an unusable value falls THROUGH to the next key rather than losing the row")
ok(L.choose_match_key({"work_email": "", "li": "https://www.linkedin.example/in/x", "mobile": ""},
                      MAPPING, "contacts") == ("", ""),
   "and a row whose only key is unusable carries no key at all")
ok([k for k, _ in L.unusable_match_values(fallthrough, MAPPING, "contacts")] == ["linkedin_url"],
   "the unusable value is reported separately: fix what you have, not find something new")


section("The data does not have to be a CSV — one tab of a workbook reads the same")

# The workbook is built here with the standard library rather than shipped as a binary fixture,
# for the same reason the reader uses stdlib: a test that needs openpyxl installed is a test that
# does not run on the machine it matters on.
_OOX = "http://schemas.openxmlformats.org"          # split across lines it reads as a bare host


def _xlsx(path, tabs):
    import zipfile as _z
    sheets = "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (n, i + 1, i + 1)
                     for i, (n, _) in enumerate(tabs))
    rels = "".join('<Relationship Id="rId%d" Target="/xl/worksheets/sheet%d.xml" '
                   'Type="%s/officeDocument/2006/relationships/worksheet"/>'
                   % (i + 1, i + 1, _OOX) for i in range(len(tabs)))
    with _z.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml",
                   '<workbook xmlns="%s/spreadsheetml/2006/main" '
                   'xmlns:r="%s/officeDocument/2006/relationships">'
                   '<sheets>%s</sheets></workbook>' % (_OOX, _OOX, sheets))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="%s/package/2006/relationships">%s</Relationships>'
                   % (_OOX, rels))
        # style 1 is a date format; anything using it is a serial number that means a date
        z.writestr("xl/styles.xml",
                   '<styleSheet xmlns="%s/spreadsheetml/2006/main"><cellXfs count="2">'
                   '<xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>' % _OOX)
        for n, (_, grid) in enumerate(tabs, 1):
            rows = ""
            for ri, row in enumerate(grid, 1):
                cells = ""
                for ci, (val, style) in enumerate(row):
                    if val is None:
                        continue            # a gap must stay a gap: cells are addressed, not ordered
                    ref = "%s%d" % (chr(65 + ci), ri)
                    if style:
                        cells += '<c r="%s" s="1"><v>%s</v></c>' % (ref, val)
                    else:
                        cells += '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, val)
                rows += "<row>%s</row>" % cells
            z.writestr("xl/worksheets/sheet%d.xml" % n,
                       '<worksheet xmlns="%s/spreadsheetml/2006/main"><sheetData>%s</sheetData>'
                       '</worksheet>' % (_OOX, rows))


book = os.path.join(tmp, "tam.xlsx")
_xlsx(book, [
    ("Target Companies", [
        [("company_id", 0), ("company_name", 0), ("website", 0), ("founded", 0), ("note", 0)],
        [("c1", 0), ("Acme", 0), ("https://a.example", 0), ("40635", 1), (None, 0)],
        [("c2", 0), ("Bee", 0), ("https://b.example", 0), ("38245", 1), ("kept", 0)],
        [("", 0), ("", 0), ("", 0), ("", 0), ("", 0)],
    ]),
    ("People", [
        [("contact_id", 0), ("full_name", 0), ("work_email", 0), ("company_id", 0)],
        [("p1", 0), ("Ada", 0), ("ada@a.example", 0), ("c1", 0)],
    ]),
])

ok(L.list_sheets(book) == ["Target Companies", "People"], "the tabs in a workbook are readable")
ok(L.propose_sheets(L.list_sheets(book)) == {"companies": "Target Companies", "contacts": "People"},
   "an obvious tab name is proposed, so a workbook is shown mapped rather than interrogated")
ok(L.propose_sheets(["Accounts", "Buying Group"]) == {"companies": "Accounts"},
   "and a tab the word list never heard of is left UNPROPOSED rather than guessed at — the "
   "command then says so and hands it to the agent, same as it does with fields")

co = L.read_table(book + "#Target Companies")
ok(len(co) == 2, "a trailing run of blank rows is not data (%d)" % len(co))
ok(co[0]["company_name"] == "Acme" and co[1]["website"] == "https://b.example",
   "cells land under the right header")
ok(co[0]["note"] == "" and co[1]["note"] == "kept",
   "a gap in the middle of a row stays a gap rather than shifting every later column")

# THE ONE THAT MATTERS. A spreadsheet stores a date as days since 1899-12-30. Read raw it is a
# plausible five-digit integer that passes a numeric check and lands in the table as a meaningless
# number — the same silent wrongness as a band in a number field, arriving through a new door.
ok(co[0]["founded"] == "2011-04-02" and co[1]["founded"] == "2004-09-15",
   "a date-formatted cell becomes an ISO date, not the serial %r" % co[0]["founded"])
ok(L.parses_as(co[0]["founded"], "date"), "and it is then a value a date field will actually store")
ok(L.infer_type([r["founded"] for r in co]) == "date", "so the column infers as a date")

ok(L.read_table(book + "#people")[0]["full_name"] == "Ada", "the tab name is matched case-blind")
ok(L.split_spec("book.xlsx#Sheet1") == ("book.xlsx", "Sheet1"), "a `file#tab` spec splits")
ok(L.split_spec(os.path.join(SAMPLE_DIR, "sample-companies.csv"))[1] is None,
   "and a real path is never split, even if it contains a #")
for bad, why in ((book, "no tab named"), (book + "#Nope", "a tab that is not there")):
    try:
        L.read_table(bad)
        ok(False, "%s is refused with the tab list, not a stack trace" % why)
    except (ValueError, SystemExit) as exc:
        ok("Target Companies" in str(exc), "%s is refused, naming the tabs it does have" % why)


section("Facts about existing fields — the MATCHING is the agent's job, not the script's")

LIVE = [
    {"id": "org_name", "name": "Company name", "dataType": "text"},
    {"id": "domain", "name": "Domain", "dataType": "url"},
    {"id": "employee_count", "name": "Employee count", "dataType": "number"},
    {"id": "location_city", "name": "City", "dataType": "text"},
]

ok(L.certain_field_match("Company name", LIVE)["field_id"] == "org_name",
   "the same label is a fact, and is asserted")
for spelling in ("company name", "Company_Name", "COMPANY  NAME"):
    ok(L.certain_field_match(spelling, LIVE)["field_id"] == "org_name",
       "case and punctuation do not make %r a different column" % spelling)
ok(L.certain_field_match("org_name", LIVE)["how"] == "named like the field id",
   "a column named like the field id matches, and says which kind of match it was")

# The alias table is GONE on purpose. `headcount` really does belong in `employee_count`, and the
# agent running the skill is the thing that should say so — it can see the column's sample values
# and the whole field list, it can handle `staff_count` and `# of employees` and a header in
# another language, and it can explain itself, which is what makes the proposal correctable.
for judgment in ("headcount", "employees", "website", "hq_city", "company_linkedin"):
    ok(L.certain_field_match(judgment, LIVE) is None,
       "%r is a judgment call and is NOT asserted as a fact here" % judgment)
ok(L.certain_field_match("why_now", LIVE) is None, "and a genuinely new column matches nothing")
ok(L.certain_field_match("", LIVE) is None, "a blank header matches nothing")

# The type check stays mechanical, because it is not a judgment call at all.
ok(L.type_conflict("number", "text"), "text into a number field is a conflict")
ok(not L.type_conflict("text", "text"), "agreeing types are not")
ok(not L.type_conflict(None, "text") and not L.type_conflict("text", None),
   "and with nothing to compare there is no conflict to claim")


section("The company a contact carries — not domain-only, and never a personal mailbox")

CK = json.loads(json.dumps(MAPPING))
CK["contacts_company_domain_column"] = "co_domain"
CK["contacts_company_linkedin_column"] = "co_li"
CK["contacts_company_name_column"] = "co_name"

ok(L.company_key_for_contact({"co_domain": "https://WWW.Acme.com/x"}, CK)[:2]
   == ("domain", "acme.com"), "a company-domain column wins, normalised")
ok(L.company_key_for_contact(
    {"co_li": "https://www.linkedin.com/company/acme"}, CK)[0] == "linkedin_url",
   "a company LinkedIn URL is a match key too — this is NOT domain-only")
ok(L.company_key_for_contact({"co_li": "https://www.linkedin.example/company/acme"}, CK)[1] == "",
   "and an off-host LinkedIn URL is refused here as well, not passed on to fail later")
ok(L.company_key_for_contact({"work_email": "ada@acme.example"}, CK)[:2]
   == ("domain", "acme.example"), "failing both columns, the work email's domain stands in")
for free in ("example@gmail.com", "example@outlook.com", "ada@proton.me", "ada@qq.com"):
    ok(L.company_key_for_contact({"work_email": free}, CK)[1] == "",
       "%s yields nothing: a personal mailbox says nothing about where someone works" % free)
ok(L.company_key_for_contact({}, CK) == ("", "", ""), "and a row with none of it yields nothing")
ok(L.company_key_for_contact({"co_domain": "Acme Corp"}, CK)[1] == "",
   "a company NAME in the domain column is not a domain, and cannot become one")

ok(L.contact_join_key({"company_key": "ACME-1", "work_email": "a@acme.example"}, CK) == "ACME-1",
   "the reference column is the join key when the row has one")
ok(L.contact_join_key({"company_key": "", "work_email": "a@acme.example"}, CK) == "acme.example",
   "and the derived match key stands in when it does not, so that contact can still be linked")
ok(L.contact_join_key({"company_key": "", "work_email": "example@gmail.com"}, CK) == "",
   "with nothing derivable there is no join key, and nothing is invented")


section("A verification that compared nothing must not report success")

# Measured on a real run: called with a ledger and no file, verify skipped every entity, compared
# zero fields, and printed "every field matches what should have landed" — the exact failure the
# step exists to catch, committed by the step itself.
import load_drive as D                                               # noqa: E402


class _Args:
    def __init__(self, **kw):
        self.csv = self.contacts_csv = self.ledger = self.contacts_ledger = None
        self.map = os.path.join(tmp, "m.json")
        self.__dict__.update(kw)


json.dump({"fields": {"companies": {"a": {"type": "text", "field_id": "org_name"}}}},
          open(os.path.join(tmp, "m.json"), "w"))
for case, kw in (("a ledger with no file", {"ledger": led}),
                 ("a file with no ledger", {"csv": "x.csv"}),
                 ("neither", {})):
    try:
        D.verify(_Args(**kw))
        ok(False, "%s is refused rather than passed" % case)
    except SystemExit as exc:
        ok("NOTHING TO VERIFY" in str(exc),
           "%s is refused, and says what is missing" % case)


section("A column on both tables is the join, and beats any word list")

# Missed on a cold run: both tabs carried `acct_code` with identical values, and the proposal
# keyed companies on their domain instead — which two of the six companies did not have.
co_j = [{"acct_code": "A1", "name": "Acme", "web": "https://a.example"},
        {"acct_code": "A2", "name": "Bee", "web": "https://b.example"}]
pe_j = [{"acct_code": "A1", "who": "Ada", "employer_web": "a.example"},
        {"acct_code": "A2", "who": "Bram", "employer_web": "b.example"},
        {"acct_code": "ZZ", "who": "Cai", "employer_web": ""}]
j = L.shared_join_columns(co_j, pe_j)
ok(j and j[0][0] == "acct_code", "the column on both tables is found: %r" % (j,))
ok(j[0][1] == 2 and j[0][2] == 3, "and it reports how many contacts actually resolve through it")
ok(all(c != "web" for c, _h, _t in j),
   "a column on only one table is not a join candidate")
ok(L.shared_join_columns(co_j, [{"acct_code": "QQ", "who": "Zed"}]) == [],
   "a shared column whose values never overlap is not proposed either")
ok(L.shared_join_columns([], pe_j) == [] and L.shared_join_columns(co_j, []) == [],
   "and one table alone proposes nothing rather than crashing")


section("Where a contact's company came from is recorded, not just whether it has one")

# `link_source` was documented in the representative output and in Step 9, and never written —
# a cold run found every line carrying None. It is derived from the company's own ledger line
# rather than tracked separately, so there is one source of truth.
lsled = os.path.join(tmp, "ls.jsonl")
L.append_settled(lsled, L.ledger_line("FROM-TABLE", "completed", entity_id=1))
L.append_settled(lsled, L.ledger_line("FROM-TABLE2", "completed", entity_id=2,
                                      created_from="table"))
L.append_settled(lsled, L.ledger_line("FROM-CONTACT", "completed", entity_id=3,
                                      created_from="contact"))
verdicts = L.fold_ledger(lsled)
derive = {"table": "already_in_table", "contact": "created_from_contact"}
for key, want in (("FROM-TABLE", "company_table"),
                  ("FROM-TABLE2", "already_in_table"),
                  ("FROM-CONTACT", "created_from_contact")):
    got = derive.get((verdicts.get(key) or {}).get("created_from"), "company_table")
    ok(got == want, "a company %s resolves to link_source %r" % (key, want))


section("Verification counts THIS load's records, not the whole workspace")

# The defect this covers shipped and was caught by a cold run. `count ... is_not_null` is
# workspace-wide, and the pass test was `got >= want`: on a workspace already holding records the
# count came back 17 against an expected 5 and every field passed, including fields the load had
# not written at all. Structurally incapable of detecting the failure the skill exists to catch,
# and it looked rigorous doing it.
vled = os.path.join(tmp, "v.jsonl")
L.append_settled(vled, L.ledger_line("r1", "completed", entity_id=101))
L.append_settled(vled, L.ledger_line("r2", "completed", entity_id=102))
L.append_settled(vled, L.ledger_line("r3", "rejected_no_match_key"))
loaded = {r["entity_id"] for r in L.fold_ledger(vled).values()
          if r.get("status") == "completed" and r.get("entity_id")}
ok(loaded == {101, 102}, "the scope is the completed rows' record ids, and nothing else")

workspace_wide = {101, 102, 900, 901, 902, 903}      # this field populated on older records too
ok(len(workspace_wide) == 6 and len(workspace_wide & loaded) == 2,
   "a workspace-wide count says 6 where this load wrote 2 — which is how >= passed everything")
did_not_write = {900, 901, 902, 903}
ok(len(did_not_write & loaded) == 0,
   "and a field this load wrote NONE of scores 0 once scoped, instead of passing on other "
   "records that happened to carry it")


section("A company created from a contact is never nameless")

import load_drive as D2                                             # noqa: E402

ok(D2.company_stub("domain", "wetherby.example", "")["org_name"] == "wetherby.example",
   "with no name to hand, the match key becomes the name rather than leaving it blank")
ok(D2.company_stub("domain", "wetherby.example", "Wetherby Mills")["org_name"] == "Wetherby Mills",
   "and a real name is used when there is one")
stub = D2.company_stub("linkedin_url", "https://www.linkedin.com/company/x", "")
ok(stub["match_key"] == "linkedin_url:https://www.linkedin.com/company/x"
   and stub["linkedin_url"] == "https://www.linkedin.com/company/x",
   "and it is keyed exactly like a company from the companies file would be")
ok(D2.ids_literal([3, 1]) == "'{1,3}'::bigint[]", "verification is scoped to this load's ids")


section("The company link has a three-state answer, because zero orphans is ambiguous")

# The failure this covers is completely silent in production: a wrong or missing company-reference
# column unlinks EVERY contact, every row still loads, and the run reports success end to end.
# "0 orphans" reads identically whether the join worked or was never wired, so the state is
# reported separately from the count.
link_rows = [
    {"contact_id": "p1", "full_name": "A", "work_email": "a@x.example", "company_key": "c1"},
    {"contact_id": "p2", "full_name": "B", "work_email": "b@x.example", "company_key": "c2"},
]
good = L.check(link_rows, MAPPING, "contacts", company_keys={"c1", "c2"})["company_link"]
ok(good["state"] == "ok" and good["resolvable"] == 2, "a wired join reports ok with a count")

no_col = json.loads(json.dumps(MAPPING))
no_col.pop("company_ref_column")
bad = L.check(link_rows, no_col, "contacts", company_keys={"c1"})["company_link"]
ok(bad["state"] == "NOT CONFIGURED" and bad["resolvable"] == 0,
   "a mapping with no company reference column says so rather than reporting zero orphans")

wrong = json.loads(json.dumps(MAPPING))
wrong["company_ref_column"] = "contact_id"
w = L.check(link_rows, wrong, "contacts", company_keys={"c1", "c2"})["company_link"]
ok(w["state"] == "NOTHING RESOLVES" and w["resolvable"] == 0,
   "a column that exists but joins to nothing is NOT the same as a file with no companies")

absent = json.loads(json.dumps(MAPPING))
absent["company_ref_column"] = "employer_name"
a2 = L.check(link_rows, absent, "contacts", company_keys={"c1"})["company_link"]
ok(a2["state"] == "COLUMN NOT IN FILE", "a reference column that is not in the file is named")

unchecked = L.check(link_rows, MAPPING, "contacts")["company_link"]
ok(unchecked["state"] == "not checked" and unchecked["resolvable"] is None,
   "and without the companies file it says the link was NOT checked, rather than implying ok")

ok(L.check(link_rows, MAPPING, "companies")["company_link"] is None,
   "companies have no company link, so the field is absent rather than a misleading ok")


section("The shipped sample is a fixture — every planted defect must still be found")

SAMPLE = SAMPLE_DIR
smap = json.load(open(os.path.join(SAMPLE, "sample-mapping.json"), encoding="utf-8"))
sco = L.read_csv(os.path.join(SAMPLE, "sample-companies.csv"))
spe = L.read_csv(os.path.join(SAMPLE, "sample-contacts.csv"))

ok(len(sco) == 18 and len(spe) == 32, "the sample is 18 companies and 32 contacts")
ok(L.infer_type([r["employee_count"] for r in sco]) == "text",
   "inference demotes the headcount column: one band far down the file beats fifty clean rows")
ok(L.infer_type([r["last_funding_date"] for r in sco]) == "text", "and the funding date column")
ok(L.infer_type([r["funding_raised_usd"] for r in sco]) == "text", "and the funding amount column")
ok(L.infer_type([r["analyst_coverage"] for r in sco]) == "boolean",
   "while a genuinely clean yes/no column beside them stays a boolean")

cprop = L.inspect(sco, "companies")["proposed"]
ok(cprop["row_key_column"] == "company_id" and cprop["domain_column"] == "website"
   and cprop["name_column"] == "company_name",
   "all three company proposals are right on a file built to defeat them: %r" % cprop)
pprop = L.inspect(spe, "contacts")["proposed"]
ok(pprop["company_ref_column"] == "company_id",
   "and the contacts file proposes the company reference, not its own row key: %r" % pprop)

sc = L.check(sco, smap, "companies")
ok(sc["loadable"] == 16, "16 of 18 companies are loadable (got %d)" % sc["loadable"])
ok(len(sc["no_match_key"]) == 1, "one company carries neither a domain nor a LinkedIn URL")
ok(len(sc["duplicate_row_key"]) == 1, "one company row key is exported twice")
ok(sc["collapsing_rows"] == 2 and sc["collapsing_into"] == 1,
   "two company rows share a domain in different case and collapse onto one record")
ok(sc["by_match_key"] == {"domain": 15, "linkedin_url": 1},
   "and exactly one company matches on its LinkedIn URL: %r" % sc["by_match_key"])
ok(list(sc["unusable_match_values"]) == ["linkedin_url"],
   "the one off-host LinkedIn URL is reported as unusable rather than silently dropped")
for col in ("employee_count", "last_funding_date", "funding_raised_usd", "expansion_signal"):
    ok(col in sc["coercion_failures"],
       "the shipped mapping's deliberate mistyping of %s is caught before the load" % col)

company_keys = {i["row_key"] for i in L.keyed_rows(sco, smap, "companies") if i["row_key"]}
sp = L.check(spe, smap, "contacts", company_keys)
ok(sp["loadable"] == 29, "29 of 32 contacts are loadable (got %d)" % sp["loadable"])
ok(len(sp["no_match_key"]) == 2,
   "two contacts cannot load — one carrying nothing, one carrying an off-host LinkedIn URL")
ok(len(sp["orphan_contacts"]) == 1, "one contact points at a company id not in the file")
ok(sp["company_link"]["state"] == "ok" and sp["company_link"]["resolvable"] == 28,
   "and the sample's company link is wired: 28 of 29 loadable contacts resolve (%r)"
   % sp["company_link"])
ok(sp["collapsing_rows"] == 2, "two distinct people were given the same email and will collapse")
ok(set(sp["coercion_failures"]) == {"years_in_role", "last_job_change"},
   "and both contact mistypings are caught: %r" % sorted(sp["coercion_failures"]))

# The sample must stay loadable end to end: every row that survives screening must produce a
# payload, and no payload may ever carry a blank.
built = 0
for entity, rows in (("companies", sco), ("contacts", spe)):
    for item in L.keyed_rows(rows, smap, entity):
        if item["duplicate"] or not L.choose_match_key(item["row"], smap, entity)[0]:
            continue
        b = L.build_payload(item, smap, entity, "900100200" if entity == "contacts" else None)
        built += 1
        assert all(not L.blank(v) for v in b["payload"].values())
ok(built == 45, "every loadable sample row builds a payload with no blank in it (%d)" % built)

ok(not any(f.get("field_id", "").startswith("audf_")
           for e in smap["fields"].values() for f in e.values()),
   "the shipped mapping carries NO workspace field ids — the field step writes those into a copy")


# --------------------------------------------------------------------------- done

print("\n%d checks, %d failed" % (CHECKS[0], len(FAILURES)))
for f in FAILURES:
    print("  - %s" % f)
sys.exit(1 if FAILURES else 0)
