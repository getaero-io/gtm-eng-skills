# Source connections

Use the approved read source. Follow the safety rule before creating a connection or transferring private records.

1. Inspect existing connection metadata.
2. Verify the service, CRM account or database, schema, permissions, and native keys.
3. Record snapshot time, extraction limits, completed pages, and mapping version.
4. Select only fields needed for the task.
5. Map source fields to the input contract.
6. Report missing fields, incomplete pages, and access failures.

Do not substitute another account when access fails. Request a connection reference, not credentials in chat. Use the approved secret manager or environment wrapper. Keep credentials and connection strings out of reports.

For production SQL, verify read-only permissions and required approval first. Prefer the existing query or export interface. Record replication time and lineage. Review imported queries before execution.

Keep observation time, effective time, and extraction time separate. Keep missing, malformed, redacted, unavailable, and confirmed-false states distinct.

Verify custom endpoint contracts before use. A retained response tests the parser; it does not prove live access. A generic HTTP tool does not prove authorization.

Before an approved remote batch, verify input paths and hashes. After a failure, resume only unfinished work. Retain completed results and charges.

Follow the approved source order. Retain conflicts and source versions. A warehouse or outbound system is not necessarily the field authority.
