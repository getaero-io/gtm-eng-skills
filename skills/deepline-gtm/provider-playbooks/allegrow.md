# Allegrow Workflow Guidance

Allegrow specialises in B2B catch-all domain resolution and primary-email identification. Use it as a final-layer validator after cheaper/faster verifiers (ZeroBounce, Findymail, etc.) have already run and returned `catch_all` or when you need to distinguish an executive's primary address from their secondary ones.

## Status Interpretation

| `result.status`    | Meaning                                              | Action             |
|--------------------|------------------------------------------------------|--------------------|
| `safe`             | Valid, safe to send                                  | **Send**           |
| `do_not_mail_abuse`| Valid address but high spam-report risk              | Skip email; use LinkedIn/phone instead |
| `some_risk`        | Inconclusive, risk factors identified                | Hold 30 days; re-validate before next send |
| `block_bounce_risk`| Invalid; will hard-bounce                            | Remove from list   |
| `dead_email`       | Invalid account on a catch-all host (won't bounce)  | Use other channels; remove from active send list |
| `spamtrap`         | Spamtrap or trap-like mailbox                        | Remove from list   |
| `more_time_required`| Validation still processing                         | Poll later         |
| `missing_email`    | Request did not include an email                     | Fix input          |

`result.subStatus`:
- `primary`: Allegrow identified this as the contact's **main email**. Especially useful for execs and senior decision-makers who have multiple valid addresses.
- `null`: No additional context.

## Usage Patterns

- **After ZeroBounce returns `catch_all`**: Run Allegrow on those rows to resolve dead vs safe. Allegrow's B2B specialisation makes it materially better than generic verifiers on corporate domains.
- **Executive lists**: Use `subStatus == primary` to prefer the primary address when multiple candidates exist.
- **Do not use** `allegrow_validate` as a bulk first-pass verifier. It costs per call and is slower than SMTP-based verifiers. Reserve it for catch-all resolution and high-value contacts.
- **Polling**: The sync endpoint has a 30-second timeout. A 202 response includes `pollUrl` and `retryAfter`. If your run context supports polling, retry after `retryAfter` seconds. In `deepline enrich` this is handled automatically.
- **Async validation**: Use `allegrow_validate_async` only when a configured webhook or later polling via `allegrow_validate_status` fits the workflow.
- **Bulk CSV**: Use the CSV job endpoints when the user explicitly needs Allegrow's bulk CSV workflow. `allegrow_create_csv_validation_job` only creates the job and upload URL; the CSV upload itself is a direct PUT to the returned presigned URL.

## Known Limitations

- No balance/credit endpoint exposed in the API; quota resets are managed with your account manager.
- owner.com and similar corporate domains return `dead_email` even for likely-valid addresses. Allegrow is conservative on fully catch-all domains with no MX activity evidence. Cross-reference against CRM data before removing these.
- The exact purchased validation USD rate is not in the docs. Keep `ALLEGROW_PROVIDER_CURRENCY_TO_USD_RATE` blocked at 0 until the contract rate is supplied.
