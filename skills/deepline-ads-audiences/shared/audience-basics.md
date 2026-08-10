# Audience Basics

Background for users who have not built a paid ads audience before. Read this when the user asks what a hash is, why their match rate is low, or why the workflow has so many steps. Everything here is explanation, not procedure.

## Contents

- [What an upload actually does](#what-an-upload-actually-does)
- [Why B2B lists match badly](#why-b2b-lists-match-badly)
- [What a hash is](#what-a-hash-is)
- [Hash or raw personal email](#hash-or-raw-personal-email)
- [Why match rate misleads](#why-match-rate-misleads)
- [Platform formatting differences](#platform-formatting-differences)

## What an upload actually does

Uploading a customer list does not buy an audience. It asks the platform which of these people already have an account there. Rows that match become reachable; rows that do not reach nobody, and any enrichment spend on them is wasted.

So the whole workflow optimizes one thing: how many rows carry an identifier the platform recognizes.

## Why B2B lists match badly

CRMs store work emails. People register personal social accounts with personal addresses and mobile numbers. You hold one identifier, the platform holds another, and the same person never gets connected.

Nothing rejects work emails. A Google Workspace address is a real Google account, and Meta accepts any address at signup. The constraint is registration behavior, not policy. That distinction matters when a user asks whether they can "just fix" their CRM data: the fix is acquiring the identifier the person actually used, not cleaning the one you have.

## What a hash is

A hash is a fixed-length code generated from text. SHA-256 turns any input into 64 characters:

```text
jane@corp.com
a2327573224b6c023cc60a440a85830a8894f467ea13f33f36290059e2e8193f
```

Three properties matter:

1. **Same input, same output, always.** This is what makes matching possible.
2. **Any change to the input changes the whole output.** `jane@corp.com` and `Jane@Corp.com` produce entirely unrelated codes. There is no partial match, which is why normalization rules are not optional.
3. **You cannot work backwards.** The recipe discards information, so the code cannot be turned back into the address.

That third property is why both sides can compare lists without exchanging addresses. You hash your copy, the platform hashes its copy, and only the codes are compared. For people who do not match, the platform holds a code it cannot reverse for a person it cannot identify.

## Hash or raw personal email

Users often ask which is better for matching. Neither, because they are the same thing: a hash is a personal email that has been through the recipe. Upload a raw address and the platform hashes it on arrival.

The decision is about whether anyone needs to read the address:

| Use | Buy | Why |
| --- | --- | --- |
| Ads only | The hash | Costs a fraction of a readable address, because you are not paying for contactability |
| Ads plus email or calling | The raw address, hashed locally | You need the readable form too |

## Why match rate misleads

Google reports a match rate percentage; Meta reports a Match score out of ten in half-point increments. Both divide by rows uploaded.

Two consequences worth telling the user:

- Junk rows count against the denominator, so cleaning the file before upload raises the score without buying anything.
- Adding a layer that contributes many rows can lower the percentage while raising the count of reachable people. Judge a run on matched people, not on the ratio. Google states outright that match rate is not an indicator of list performance.

## Platform formatting differences

The two platforms disagree on phone format, so one shared normalizer across both is a bug:

| Field | Google Customer Match | Meta Custom Audiences |
| --- | --- | --- |
| Phone | E.164 with a leading `+` | Digits only, symbols and leading zeroes stripped, country code prefixed |
| Gmail dots and `+suffix` | Strip both, for `gmail.com` and `googlemail.com` only | No equivalent rule |
| Hash | SHA-256, hex | SHA-256 only, hex, lowercase A-F |

Applying Google's gmail rule to other domains breaks matching, because dots are significant everywhere else.

Google needs 100 active users in the last 30 days before a list serves, for lists uploaded or refreshed after February 2024, and recommends at least 5,000. Meta guides toward at least 1,000 per customer list, and separately requires 100 people in a source audience used for a Lookalike. Both take up to a day or two to process, so an empty size right after upload means processing rather than failure.
