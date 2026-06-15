# EnformionGO Integration Guide

Consumer skip-trace API (Galaxy) for finding an individual's **personal contact info** — personal emails and mobile phones — from name + city/state.

Tool quick-pick:
- **Personal email** → `enformion_person_search` (Person database; returns `emailAddresses[]` flagged `nonBusiness:1`). Do NOT use `enformion_workplace_search` for personal email — it returns other-employer work emails.
- **Personal mobile (phone-first)** → `enformion_contact_enrich` (skip-trace, ~53% mobile hit rate).
- **Officers of a business** → `enformion_business_search` → officer `tahoeId` → `enformion_person_search` by tahoeId.

## When to use

Use `enformion_contact_enrich` when you need to find the personal mobile of a small business owner (restaurant, retail, local services) who has:
- No LinkedIn profile
- No company domain email
- No B2B database presence

This is the right tool after you've already extracted the owner's name from a public source (Google search, Yelp, SOS officer records, OpenMart staff).

## Critical gotchas — read before calling

### 1. Strip middle initials from last_name (automatic)
The integration automatically strips middle initials. You do NOT need to pre-process — just pass the raw last name. But be aware:
- `"K Tarzai"` → bare last = `"Tarzai"` ✓
- `"De La Cruz Castillo"` → bare last = `"Castillo"` ✓
- `"Smith Jr."` → bare last = `"Smith"` ✓

If you want to override this, pass only the bare last word yourself.

### 2. FL SOS officer names (use reverseFlOfficerName helper)
Florida SOS returns officer names as `"LASTNAME, FIRSTNAME MIDDLE"`. You must reverse these before calling:
- `"SMITH, JOHN EDWARD"` → `"John Smith"` ✓
- `"DE LA CRUZ, MARIA"` → `"Maria De La Cruz"` ✓

The helper `reverseFlOfficerName()` is exported from `actions/enformion-shared.ts`.

### 3. Rate limits
No documented rate limit, but runs degrade with >200 concurrent requests. The Deepline rate limiter caps at 10 req/s which is safe for all batch sizes.

### 4. No-result interpretation
- `identityScore: 0` = no match found (not billed)
- `identityScore: 75–100` = high confidence match
- `person.phones[]` empty = found the person but no phone on record

## Response structure

```json
{
  "person": {
    "name": { "firstName": "Gary", "lastName": "Lincoln" },
    "age": "45",
    "addresses": [...],
    "phones": [
      {
        "number": "(856) 725-5922",
        "type": "mobile",
        "isConnected": true,
        "firstReportedDate": "...",
        "lastReportedDate": "..."
      }
    ],
    "emails": [...]
  },
  "identityScore": 100,
  "isError": false
}
```

Extract the mobile: `person.phones.find(p => p.type === "mobile" && p.isConnected === true)?.number`

## Validation

After finding a phone via EnformionGO, validate it with `trestle_phone_validation`:
- `line_type: "Mobile"` + `activity_score >= 60` = confirmed owner mobile
- `line_type: "Landline"` or `line_type: "FixedVOIP"` = store/office phone — discard

## Credentials

Requires two custom headers set from stored credentials:
- `galaxy-ap-name`: your API key name
- `galaxy-ap-password`: your API key password

Set via Deepline dashboard → Integrations → EnformionGO, or via `ENFORMION_KEY_NAME` + `ENFORMION_KEY_PASSWORD` environment variables.

API endpoint: `https://devapi.enformion.com/Contact/Enrich`

---

## enformion_person_search — PERSONAL emails (use this, not workplace_search)

### When to use

Use `enformion_person_search` whenever you need a person's **personal email** (and/or phone). This is the Galaxy "Person Search" database (`galaxy-search-type: Person`). Unlike Workplace Search — which returns the owner's *other-employer* work emails 97% of the time — Person Search returns the individual's personal addresses (gmail/yahoo/comcast), each flagged `nonBusiness: 1`.

Two lookup modes:
- **By name + city/state** — the common path. `enformion_person_search({ first_name, last_name, city_state })`.
- **By tahoe_id** — exact-person lookup. Pass `{ tahoe_id }` to pin one identity (e.g. an officer tahoeId returned by `enformion_business_search`). When `tahoe_id` is set, the name/location fields are ignored.

Middle initials and compound surname prefixes are stripped automatically (same silent-zero-result bug as Contact/Enrich).

### Recommended flow for business officers (vendor-recommended)

To get the personal contact info of a business's officers/agents:

1. `enformion_business_search({ name, city_state })` → business record with `officers[]` / agents, each carrying a `tahoeId`.
2. For each officer, `enformion_person_search({ tahoe_id })` → that person's `emailAddresses[]` + `phoneNumbers[]`.

**Entitlement note:** Business Search is a *separately entitled* Galaxy product. If the access profile is not provisioned for it, the call returns `isError: true` ("Access Profile does not permit client to call Business Search."). When that happens, **fall back to person-search-by-name** using the officer name you already resolved (from Google/Yelp/SOS) — Person Search is entitled and returns the same personal contact data. (As of 2026-06-09 the `aeroailabs` profile has Person Search but not Business Search.)

### Response structure (Person Search)

```json
{
  "persons": [
    {
      "tahoeId": "G-2492258155993150029",
      "fullName": "Maria Delcarmen Castillo",
      "name": { "firstName": "Maria", "lastName": "Castillo" },
      "age": 49,
      "emailAddresses": [
        { "emailAddress": "mcastillo12692@gmail.com", "emailOrdinal": 1, "isPremium": true, "nonBusiness": 1 }
      ],
      "phoneNumbers": [
        { "phoneNumber": "(305) 555-0142", "phoneType": "Wireless", "isConnected": true }
      ],
      "addresses": [ { "fullAddress": "...", "city": "Miami", "state": "FL" } ]
    }
  ],
  "isError": false
}
```

Extract the best personal email: `persons[0].emailAddresses[0].emailAddress` (prefer entries with `isPremium: true`). No result: `persons` is an empty array.

### Billing

Billed per match (`post_deduct`, $0.35) only when the top match has a personal email or a connected phone. No charge on empty / no-match.

API endpoint: `https://devapi.enformion.com/PersonSearch` (`galaxy-search-type: Person`).
Business Search endpoint: `https://devapi.enformion.com/BusinessSearch` (`galaxy-search-type: Business`).

---

## enformion_workplace_search

### When to use

Use `enformion_workplace_search` as a **fallback** when `enformion_contact_enrich` returns `identityScore: 0` or an empty phones array. It queries a separate B2B employment profile database and has a different rate-limit bucket, so it does not compete with Contact/Enrich capacity.

`city_state` is optional here (unlike Contact/Enrich where it is required). Omitting it broadens the match at the cost of potentially more ambiguous results.

### Critical warning: emailAddresses[]

`emailAddresses[]` in Workplace Search results are almost always the owner's OTHER employer (a corporate day job, a franchise group, etc.) and NOT the restaurant's email. In practice:
- 97% of returned email addresses belong to a different employer.
- Only use an email address if the domain matches the target restaurant's domain (e.g., `gary@lincolnautogroup.com` is useless if you want `gary@lincolndiner.com`).

### Rate-limit bucket

Workplace Search uses a **separate** rate-limit bucket from Contact/Enrich. Both can run concurrently without reducing each other's throughput. The Deepline rate limiter treats them as independent pools.

### Response structure

```json
{
  "workplaceRecords": [
    {
      "fullName": "Gary Lincoln",
      "firstName": "Gary",
      "lastName": "Lincoln",
      "professionalTitles": "Owner",
      "phoneNumbers": ["+18567255922"],
      "emailAddresses": ["gary.lincoln@someemployer.com"],
      "currentEmployment": [
        {
          "employer": "Lincoln Auto Group",
          "jobTitle": "Owner",
          "level": "Owner",
          "department": "Management"
        }
      ]
    }
  ]
}
```

Extract phone: `workplaceRecords[0]?.phoneNumbers?.[0]`

No result: `workplaceRecords` will be an empty array `[]`.

### Billing

Billed per match (`post_deduct`, $0.50) only when a workplace record with a phone or email is returned. No charge on empty / no-match.
