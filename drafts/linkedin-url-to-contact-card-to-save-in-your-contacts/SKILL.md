---
name: linkedin-url-to-contact-card-to-save-in-your-contacts
description: >-
  Use when the user pastes a LinkedIn profile URL (or asks for work email,
  mobile, and a contact/VCF card from LinkedIn) and you should enrich that
  person with Deepline then generate a .vcf.
ported_from: clay-run/clay-skill-creator/skills/alex-lindahl/linkedin-url-to-contact-card-to-save-in-your-contacts
---

# LinkedIn URL to Contact Card (to save in your contacts)

Turn a LinkedIn person profile URL into a full contact card (name, title, company, work email, mobile) via Deepline, then generate a downloadable `.vcf` the user can add to their contacts.

## Input

- Required: a LinkedIn person URL (`https://www.linkedin.com/in/...`).
- Reject company pages, search URLs, or non-LinkedIn links; ask for a person profile URL instead.
- One URL per run unless the user explicitly asks for a small batch.

## Prerequisites

1. Run `deepline preflight --json`. If the CLI is missing: `npm install -g deepline && deepline auth register --wait auto`, then re-run preflight. Tell the user which org it reports.
2. Check prices before spending: `deepline plays describe prebuilt/person-linkedin-to-email --json`, `deepline plays describe prebuilt/person-to-phone --json`, `deepline tools describe harvestapi_get_profile --json` (`pricing`). Balance is in the preflight output (`deepline billing` for detail).

## Steps

### 1. Enrich profile fields (name, title, company)

1. Normalize the URL (trim; prefer `https://www.linkedin.com/in/<slug>`).
2. Fetch the profile: `deepline tools execute harvestapi_get_profile --input '{"url":"<url>","main":"true"}' --json`. Read `result.element.firstName`, `result.element.lastName`, `result.element.headline`, `result.element.linkedinUrl`; take title and company from the current experience entry (check the exact field names in the first response — the headline is not always the job title).
3. Fallback if the profile does not resolve: `crustdata_v3_person_enrich` with `{"professional_network_profile_urls":["<url>"],"fields":["basic_profile","experience"]}` (name at `matches[0].person_data.basic_profile.name`, current employer under `experience.employment_details.current[0]`).

### 2. Enrich contact details (work email + mobile)

1. Work email: `deepline plays run prebuilt/person-linkedin-to-email --input '{"linkedin_url":"<url>"}' --watch`. Use `email` only when `email_found_and_valid` is true; otherwise report `miss_reason`.
2. Mobile: `deepline plays run prebuilt/person-to-phone --input '{"first_name":"<first>","last_name":"<last>","linkedin_url":"<url>","email":"<work email if found>","domain":"<company domain if known>"}' --watch` (first/last name are required, so run step 1 first). Use `phone` only when `phone_validated` is true; report `phone_line_type` and `phone_reject_reason` when present.
3. If a run is still in progress, read it with `deepline runs get <run-id> --full --json` until it finishes. Never claim a field is missing before the run has finished.
4. Required card fields to collect:
   - **Name** (FN / N)
   - **Title** (TITLE)
   - **Company** (ORG)
   - **Work Email** (EMAIL;TYPE=WORK)
   - **Mobile** (TEL;TYPE=CELL)
5. Never invent any of these. Leave a field blank in the VCF if Deepline did not return it; tell the user which fields were missing.

### 3. Generate a VCF and deliver it

1. Write a vCard 3.0 file in the working directory named from the person, e.g. `Kieran_Flanagan.vcf` (sanitize spaces to underscores; ASCII-safe filename).
2. Use this shape (omit lines for fields that are truly empty):

```
BEGIN:VCARD
VERSION:3.0
N:Last;First;;;
FN:Full Name
TITLE:Job Title
ORG:Company
EMAIL;TYPE=INTERNET,WORK:work@example.com
TEL;TYPE=CELL:+15551234567
URL:https://www.linkedin.com/in/slug/
END:VCARD
```

3. Split `FN` into `N` as `Last;First;;;` when the name is two+ parts (last token = family name; remainder = given name). If only one token, use `N:Name;;;;` and the same for `FN`.
4. Escape commas/semicolons/newlines in vCard values per vCard 3.0 (`\\`, `\,`, `\;`).
5. Send the user:
   - A short contact summary in chat (Name, Title, Company, Work Email, Mobile, LinkedIn)
   - The `.vcf` path (attach it if the surface supports file attachments)
6. Mention they can open/download the VCF to add it to Contacts.

## Guardrails

- Enrichments cost Deepline credits; state the price from `describe` and do not batch large URL lists without an explicit ask. For a small batch use `prebuilt/person-linkedin-to-email-batch` and `prebuilt/person-to-phone-batch` with `--input '{"csv":"urls.csv"}'`.
- Do not push results into CRM, Slack, or email unless the user asks.
- Do not scrape LinkedIn in the browser for email/phone; the Deepline waterfalls are the source of truth.
- If Deepline is unavailable and the user declines connecting it, stop and say what you need.
- Always produce the VCF when at least name + one of email/phone is available; still attach a partial card and note missing fields.

## Alternative path (a waterfall misses)

If the work-email play misses and the company domain is known from step 1, run `prebuilt/name-and-domain-to-email-waterfall` with `{"first_name","last_name","domain","linkedin_url"}`; use `email` only when `email_validated` is true. Never pattern-guess an address.
