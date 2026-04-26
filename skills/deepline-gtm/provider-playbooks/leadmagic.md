Use LeadMagic as a contact-resolution, verification, and intent layer.

- Start with cheaper gates: `leadmagic_email_validation`, `leadmagic_company_search`, and `leadmagic_jobs_finder`.
- Escalate to premium contact discovery only after the target is worth it: `leadmagic_email_finder`, `leadmagic_mobile_finder`, `leadmagic_profile_search`, `leadmagic_b2b_social_email`, and `leadmagic_email_to_profile`.
- For role-based discovery, use `leadmagic_role_finder` for a single decision-maker and `leadmagic_employee_finder` when you need a wider company roster.
- `leadmagic_email_validation` is the final outbound validity gate for this layer. Default acceptance rule is `email_status == valid`; treat `catch_all` and `unknown` as unresolved unless the user explicitly accepts risk.
- LeadMagic is **conservative on catch-all domains** (many Google Workspace and corporate domains). `email_status: "invalid"` with a populated `mx_record` + `mx_provider` usually means "mailbox not provable," not "does not deliver." Don't auto-discard these rows — fall back to `deepline_native` validation or a second provider (`zerobounce`, `bettercontact`) before giving up on the lead.
- If LeadMagic profile or phone quality is noisy on pilot rows, switch to quality-first enrichment (`crustdata_person_enrichment`, `peopledatalabs_enrich_contact`) before scaling.

Operational pattern:
1. Run 1-row pilots for identity + email candidates.
2. Validate with `leadmagic_email_validation` on every candidate.
3. Keep fallback chains explicit in your `--with-waterfall` order.
4. Promote only after pilot success and clear assumptions are set.

```bash
deepline enrich --input contacts.csv --output contacts.csv.out.csv \
  --with-waterfall "email-verify" \
  --with '{"alias":"verify_primary","tool":"leadmagic_email_validation","payload":{"email":"{{email_1}}"}}' \
  --with '{"alias":"verify_secondary","tool":"leadmagic_email_validation","payload":{"email":"{{email_2}}"}}' \
  --end-waterfall
```

Related docs:
- [leadmagic_email_validation reference](https://code.deepline.com/tools/leadmagic_email_validation)
- [leadmagic_email_finder reference](https://code.deepline.com/tools/leadmagic_email_finder)
