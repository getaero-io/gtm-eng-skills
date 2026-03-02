Use LeadMagic as a contact-resolution and verification layer.

- Treat `leadmagic_job_change_detector` and `leadmagic_email_finder` as high-signal fallback, not first-pass signal.
- For changed-company recovery, prefer quality-first enrichment (`crustdata_person_enrichment`, `peopledatalabs_enrich_contact`) before LeadMagic finder.
- `leadmagic_email_validation` is the final outbound validity gate for this layer.
- Default acceptance rule is `email_status == valid`; treat `catch_all` and `unknown` as unresolved unless user explicitly accepts risk.
- If fallback validation is noisy on pilot rows, pause and switch upstream source before scaling.

Operational pattern:
1. Run 1-row pilots for identity + email candidates.
2. Validate with `leadmagic_email_validation` on every candidate.
3. Keep fallback chains explicit in your `--with-waterfall` order.
4. Promote only after pilot success and clear assumptions are set.

```bash
deepline enrich --input contacts.csv --output contacts.csv.out.csv \
  --with-waterfall "email-verify" \
  --with 'verify_primary=leadmagic_email_validation:{"email":"{{email_1}}"}' \
  --with 'verify_secondary=leadmagic_email_validation:{"email":"{{email_2}}"}' \
  --end-waterfall --json
```

Related docs:
- [leadmagic_email_validation reference](https://code.deepline.com/tools/leadmagic_email_validation)
- [leadmagic_email_finder reference](https://code.deepline.com/tools/leadmagic_email_finder)
