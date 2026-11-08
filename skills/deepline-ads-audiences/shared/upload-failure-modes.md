# Upload failure modes

Failures observed on live Google Customer Match and Meta Custom Audience runs.
Each one uploads cleanly and reports success, so nothing downstream surfaces it.

## Contents

- [Mixed identifier types in one column](#mixed-identifier-types-in-one-column)
- [Hash-of-hash audit](#hash-of-hash-audit)
- [The connector forwards hashes verbatim](#the-connector-forwards-hashes-verbatim)
- [Meta locks an audience while it ingests](#meta-locks-an-audience-while-it-ingests)
- [Blank string fields are rejected](#blank-string-fields-are-rejected)
- [Phone normalization](#phone-normalization)
- [Gmail addresses need the canonical form on Google](#gmail-addresses-need-the-canonical-form-on-google)
- [Plain names beside hashed emails](#plain-names-beside-hashed-emails)
- [Match rate lives in contactIdInfo](#match-rate-lives-in-contactidinfo)
- [Acceptance count is not a match rate](#acceptance-count-is-not-a-match-rate)
- [Sheets destroys all-digit hashes](#sheets-destroys-all-digit-hashes)

## Mixed identifier types in one column

Meta applies one normalization rule per column. It trims, lowercases and hashes
whatever it finds. That is correct for a raw address and destructive for a value
that is already hashed: the result is `sha256(sha256(email))`, which matches
nothing and raises no error.

A customer file failed this way. Its `email_1` column held 3,725 raw addresses
and 945 SHA-256 hashes, so 951 contacts became unmatchable while the upload
reported success. The hashing was correct. Only the column placement was wrong.

The broken file also looked better on the number people check: 11,251 distinct
identifiers against 9,244 in the clean rebuild. A larger list that matches worse
is how this survives review.

Assert per column that every populated value is the same kind: all raw, or all
64-character lowercase hex. A column holding both is a blocker.

## Hash-of-hash audit

Take every hash in the payload. Check whether its own SHA-256 also appears in the
payload. A hit means a value was hashed twice.

Run this as a gate before upload, not as a report afterwards. The entire failure
mode is that nothing else surfaces it.

## The connector forwards hashes verbatim

`email_sha256` and `phone_sha256` reach the platform exactly as supplied.
Deepline hashes only `external_id`.

A correct hash arrives intact. A double-hashed one arrives intact too. No layer
repairs it, so the audit above is the only check between a mistake and a dead
audience.

## Meta locks an audience while it ingests

Meta sets `operation_status: 414` when it accepts a write, then rejects further
writes with `UPSTREAM_BAD_INPUT` / HTTP 422 until ingestion finishes. Observed
holding for over four hours.

Batching cannot work against this. The first batch lands, later batches bounce,
and the audience keeps part of the list while the run appears to progress.

- Send the whole audience in one `sync_audience_members` call. The tool accepts
  `maxItems: 300000`. Verified: 10,664 rows in one call completed in 16 seconds;
  the same list in 2,000-row batches wedged on the second batch. Google accepted
  the same list in one call with no lock, so one call is correct on both.
- Pass a large input as a file: `--input-file sync.json`, one JSON object
  holding the account, audience, mode and `rows` (SKILL.md Step 5). Inline JSON
  for a real audience exceeds the shell argument limit and fails with
  `OSError: [Errno 7] Argument list too long` before reaching Deepline.
- Do not resume a half-landed batched run with `append`. The source file may have
  changed. Create a new audience and `replace` once.
- `approximate_count: 1000` during a lock is a placeholder. A 5,000-row and a
  13,236-row upload both reported exactly 1000 while locked.
- A locked audience still reports `delivery_status: 200`. That describes the
  previously ingested audience. Only `operation_status: 200` means settled.

## Blank string fields are rejected

Every string field in the row schema declares `minLength: 1`. Sending
`first_name: ""` fails the whole batch with 422. Omit the key instead.

This applies most often to ContactOut-pool rows, which carry no name or country.

## Phone normalization

The two platforms hash different strings for the same number.

- Meta: _"Remove symbols, letters, and any leading zeroes. You should prefix the
  country code if the COUNTRY field is not specified."_ Digits only, no `+`.
  Meta documents `15559876543` hashing to
  `1ef970831d7963307784fa8688e8fce101a15685d62aa765fed23f3a2c576a4e`.
- Google: E.164 **with the leading plus**, so the hashed string is
  `+15559876543`. Google's Data Manager formatting page: "Include the plus sign
  (+) and the country code."

A pipeline that reproduces Meta's digest and hashes `+` plus the same digits for
Google handles phones correctly. One digest sent to both platforms matches on at
most one of them, which is why the standard file carries `phone_google` and
`phone_meta` as separate columns. `phoneHashes()` in
`plays/shared/audience-hash.ts` returns the pair.

Provider-supplied phone hashes carry no record of which string was hashed. Keep
them in the column of the platform the provider built them for, and never move a
digest between columns.

Both platforms accept a phone digest beside an email digest on one row.
Verified: 13,236 rows carrying 10,664 email and 6,982 phone hashes uploaded to
Google with `invalid_count: 0` and to Meta with `status=completed`.

Hashing phones the customer already supplied costs nothing. Buying mobile numbers
costs far more per contact than hashed emails, so treat that as a separate
decision.

## Gmail addresses need the canonical form on Google

Google matches Gmail on the canonical address: the local part with every dot and
the `+tag` removed. `jane.doe+ads@gmail.com` is matched as `janedoe@gmail.com`,
so the literal hash never matches on Google. Meta matches the literal form the
person registered with. Hash both forms and put both in the `email` column;
`emailHashes()` does this and returns one digest for every other domain.

Observed on a 2,493-contact B2B list: 50 source addresses were Gmail, all 50
hashed literally, so 2% of the baseline could not match on Google. A tiny share
of a B2B list, but a large one of a consumer list, and the fix costs nothing.

## Plain names beside hashed emails

Google reads a customer-list file as either fully plain or fully hashed for the
private fields (Email, Phone, First Name, Last Name). A file with hashed emails
and plain names is rejected: "Content in columns C, D doesn't match the column
header", and without a Zip column, "Zip is missing. To continue, remove the
other address columns." The names were never going to help: Google only matches
on name when first name, last name, country and zip are all present.

The damage comes from the repair. A customer who hits this error hands the file
to a script or an assistant to "hash the names", and if that step hashes every
column it also hashes the already-hashed email column. The file then uploads
with no error and matches nothing.

Ship email and phone digests only, unless all four address fields are known for
the row. When they are, hash first and last name (lowercase, trimmed) and leave
country and zip plain. `auditUploadFile()` fails a file that has plain values in
an identifier column or a partial address block, and the audit play runs it
before every upload.

## Match rate lives in contactIdInfo

Google reports the match rate as a percentage at
`ingestedUserListInfo.contactIdInfo.matchRatePercentage`. The `matchRateRange`
enum beside it often stays unset, so a caller reading only the enum reports
`null` for an audience with a real rate. Deepline's status response copies the
percentage to `data.audience.match_rate_percentage`.

Measured on one account and one source list:

| Audience             | Rows   | Match rate |
| -------------------- | ------ | ---------- |
| Email hashes only    | 10,664 | 79%        |
| Email + phone hashes | 13,236 | 84%        |

Treat `null` as not yet computed, never as zero. Google can take hours. A report
that renders `null` as 0% turns a successful upload into an apparent failure.

Meta exposes no per-audience match rate. It returns
`approximate_count_lower_bound` and `upper_bound` only.

## Acceptance count is not a match rate

`sync_audience_members` returns `uploaded_count` and `invalid_count`. These state
whether rows parsed, not whether people were found. An upload reports
`invalid_count: 0` even when every hash is double-hashed.

Report the two separately. Acceptance is available immediately and proves the
file is well formed. Match rate arrives hours later and decides whether the
enrichment spend paid off. Meta returns no per-row counts.

## Sheets destroys all-digit hashes

Google Sheets converts all-digit strings to numbers. A hash of `0000...0001`
becomes `1`. Most SHA-256 digests contain a letter and survive; an all-digit
digest does not.

Check for all-digit values before publishing, and import the column as text.

`google_workspace_export_dataset` takes a Play `run_id`, not a local path. Run a
play that emits the rows as a dataset, then export that run. Two constraints:
`materialize()` refuses more than 10,000 rows, so page the file and export one
tab per page; and the export appends a run-id suffix to the tab name, so a later
`values.get` must quote the full title.

Verify published tabs by row count, not by export status. One tab returned
`status: completed` and did not appear in the spreadsheet.
