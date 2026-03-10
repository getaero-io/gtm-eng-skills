---
name: contact-to-email
description: |
  Find and verify email addresses for contacts. Handles three common starting points:
  name + company, LinkedIn URL, or name + domain (with pattern matching).

  Triggers:
  - "find email for [name] at [company]"
  - "get email addresses for my contact list"
  - "email enrichment"
  - "I have LinkedIn URLs and need emails"
---

# Contact -> Email

This skill is a router. Do not invent your own email workflow here. Read the `gtm-meta-skill` doc `enrich-waterfall.md` and use the native plays documented there.

## Use these entrypoints

- Name + company -> `name_and_company_to_email_waterfall`
- LinkedIn URL -> `person_linkedin_to_email_waterfall`
- First name + last name + domain -> `cost_aware_first_name_and_domain_to_email_waterfall`

## Extractor contract

- Canonical scalar targets for `extract("<target>")`: `email`, `phone`, `linkedin`, `first_name`, `last_name`, `full_name`, `title`
- Use `extract("<target>")` only for those canonical scalar targets.
- Use `extractList({ keys: [...] })` only for list waterfalls. `keys` must be canonical target names the tool knows about.
- If you need explicit paths, shaping, filtering, or logic, write JS instead.

## Required read path

- For `name + company -> email`, read the `name_and_company_to_email_waterfall` section in `gtm-meta-skill/enrich-waterfall.md`.
- For `LinkedIn URL -> email`, read the `person_linkedin_to_email_waterfall` section in `gtm-meta-skill/enrich-waterfall.md`.
- For `name + domain -> email`, read the `cost_aware_first_name_and_domain_to_email_waterfall` section in `gtm-meta-skill/enrich-waterfall.md`.

## Hard rules

- Use `deepline enrich`, not ad-hoc shell scripts.
- Prefer native plays over hand-written waterfalls.
- Run a one-row pilot first.
- Validate the winning email before treating it as final.
