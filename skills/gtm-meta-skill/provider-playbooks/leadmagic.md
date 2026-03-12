Use LeadMagic as a contact-resolution and verification layer.

- Treat `leadmagic_job_change_detector` and `leadmagic_email_finder` as high-signal fallback, not first-pass signal.
- For changed-company recovery, prefer quality-first enrichment (`crustdata_person_enrichment`, `peopledatalabs_enrich_contact`) before LeadMagic finder.
- `leadmagic_email_validation` is the final outbound validity gate for this layer.
- LeadMagic returns five distinct validation statuses. Accept the first three; reject the last two:

| Status | Meaning | Accept? | Cost |
|---|---|---|---|
| `valid` | SMTP-verified deliverable, <1% bounce | ✅ Yes | Charged |
| `valid_catch_all` | Catch-all domain + engagement signal confirms address, <5% bounce | ✅ Yes (best for catch-all) | Charged |
| `catch_all` | Domain accepts all; unverifiable without engagement signal | ✅ Yes (same risk as before) | Free |
| `unknown` | Server no response, could not verify | ❌ No | Free |
| `invalid` | Will bounce | ❌ No | Charged |

**Critical:** `valid_catch_all` was historically mislabeled as invalid in many scripts. It is the highest-confidence result for catch-all domains and should always be accepted. Check for it explicitly:

```js
const result = (data.result || data.status || data.email_status || '').toLowerCase();
return result === 'valid' || result === 'valid_catch_all' || result === 'catch-all' || result === 'catch_all';
```
- If fallback validation is noisy on pilot rows, pause and switch upstream source before scaling.

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
