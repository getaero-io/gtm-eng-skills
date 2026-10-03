Use LeadMagic as a contact-resolution, verification, and intent layer.

- Start with cheaper gates: `leadmagic_email_validation`, `leadmagic_company_search`, and `leadmagic_jobs_finder`.
- Escalate to premium contact discovery only after the target is worth it: `leadmagic_email_finder`, `leadmagic_mobile_finder`, `leadmagic_profile_search`, `leadmagic_b2b_social_email`, and `leadmagic_email_to_profile`.
- For role-based discovery, use `leadmagic_role_finder` for a single decision-maker and `leadmagic_employee_finder` when you need a wider company roster.
- `leadmagic_email_validation` is the final outbound validity gate for this layer. Default acceptance rule is `email_status == valid`; treat `catch_all` and `unknown` as unresolved unless the user explicitly accepts risk.
- LeadMagic is **conservative on catch-all domains** (many Google Workspace and corporate domains). `email_status: "invalid"` with a populated `mx_record` + `mx_provider` usually means "mailbox not provable," not "does not deliver." Don't auto-discard these rows — fall back to `deepline_native` validation or a second provider (`zerobounce`, `bettercontact`) before giving up on the lead.
- If LeadMagic profile or phone quality is noisy on pilot rows, switch to quality-first enrichment (`crustdata_v3_person_enrich`, `peopledatalabs_enrich_contact`) before scaling. Confirm the current schema with `deepline tools describe <tool-id> --json`: CrustData V3 takes exactly one identifier family, `professional_network_profile_urls` or `business_emails`, as an array. Request the needed `fields` explicitly (for example, `contact` for contact data); do not copy the older camelCase person-enrichment payload into V3.

Operational pattern:

1. For larger or uncertain authorized work, test identity + email candidates on a representative row before scaling. A small supplied Play needs no extra pilot or repeated approval.
2. Validate with `leadmagic_email_validation` on every candidate.
3. Keep fallback order explicit in Play control flow: verify `email_1` first, then `email_2` only if the first candidate is absent or does not pass the validity gate. Tool completion alone is not a valid-email verdict.
4. Scale larger work after checking quality and assumptions. Provider changes or paid fallback calls must fit the existing authorization; inspecting a completed run does not authorize paid repair.

Use a supplied Play when it fits. When selecting one, start with
`deepline plays search "email verification" --json` and
`deepline plays describe <play-ref> --json`. Confirm the tool's current contract
with `deepline tools describe leadmagic_email_validation --json`.

For a custom workflow, save this as `email-verify.play.ts`. The order and payload
stay the same, but the success gate is explicit and each attempted verdict remains
available for inspection. Catch-all/unknown are unresolved, not permission to send.

```ts
import { definePlay } from 'deepline';

export default definePlay(
  'email-verify',
  async (ctx, input: { csv: string }) => {
    const contacts = await ctx.csv(input.csv, { required: ['email_1', 'email_2'] });
    const rows = await ctx.dataset('contacts', contacts)
      .withColumn('email_verification', async (row, rowCtx) => {
        const attempts = [];
        for (const [id, email] of [
          ['verify_primary', row.email_1],
          ['verify_secondary', row.email_2],
        ] as const) {
          if (!email) continue;
          const result = await rowCtx.tools.execute({
            id,
            tool: 'leadmagic_email_validation',
            input: { email },
            description: 'Verify this candidate email before accepting it.',
          });
          if (!['completed', 'no_result'].includes(result.status)) {
            throw new Error(`Email verification did not complete: ${result.status}`);
          }
          const verdict = result.extractedValues.email_status?.get();
          const emailStatus = verdict?.status ?? null;
          attempts.push({ email, emailStatus, verdict, response: result.toolResponse });
          if (emailStatus === 'valid') return { email, attempts };
        }
        return { email: null, attempts };
      })
      .run({});
    return { rows };
  },
  { description: 'Verify primary and fallback emails for supplied contacts.' },
);
```

```bash
deepline plays check email-verify.play.ts --json
deepline plays run --file email-verify.play.ts --csv contacts.csv --watch
```

Validation, authentication, billing, and unexpected execution failures remain
errors; do not turn them into candidate misses. Keep the original row and evidence,
including MX fields needed for the catch-all caveat above. Retrieve existing output
with `deepline runs get <run-id> --json` and its full-result/export commands (for
example, save to `contacts.csv.out.csv`), rather than rerunning to inspect it.

Related docs:

- [leadmagic_email_validation reference](https://code.deepline.com/tools/leadmagic_email_validation)
- [leadmagic_email_finder reference](https://code.deepline.com/tools/leadmagic_email_finder)
