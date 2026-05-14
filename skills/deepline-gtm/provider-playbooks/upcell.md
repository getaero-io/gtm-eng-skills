# Upcell

Use Upcell when the workflow needs mobile phone availability checks or matched
mobile phone reveal for a known person.

Prefer `upcell_contact_existence` first when the user only needs to know whether
a mobile exists, because it is free. Use `upcell_enrich_contact` when the mobile
number itself is needed.

For both actions, provide at least one strong matcher:

- `linkedinUrl`
- `email`
- `personalEmail`
- `firstName`, `lastName`, `title`, and `companyName`
- `firstName`, `lastName`, and either `companyDomain` or `companySocialUrl`

Only mobile workflows are currently enabled. Email, social URL, and usage stats
endpoints are intentionally not exposed until pricing and availability are
confirmed.
