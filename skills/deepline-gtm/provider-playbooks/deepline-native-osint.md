# Deepline OSINT

Deepline-managed; no API key or connection needed. Submit one email (deepline_native_osint_submit_email_check, 1 credit / $0.10) or one company domain (deepline_native_osint_submit_company_check, 1.5 credits / $0.15) against 1–20 known source slugs, then poll deepline_native_osint_get_email_check_result with both job_id and job_receipt returned by submission. A source answers either for people (email) or for companies (domain), never both; the upstream names misplaced sources in a 400 so you can move them. Each submitted job is charged once, cached answers included; polling is free.

Submission returns immediately. Save job_id, job_receipt, and poll_after. Uncached jobs can wait until the next working day; schedule retrieval after poll_after rather than holding a Play open. Cached jobs still need one poll to retrieve their answers.

All workspaces share one upstream account, so only the authenticated creator can poll: same Deepline API key, session user, or internal workflow within the same organization and auth lane. Keep the encrypted receipt until polling completes. Losing it prevents retrieval. Key rotation of Deepline credential encryption invalidates existing receipts. Do not request organization-wide sources, people, companies, streams, or arbitrary preexisting job IDs.
