# Interaction mechanics — the verified tool contract

Tool IDs, inputs and prices here were read on **2026-09-30** with
`deepline tools describe <id> --json` and `deepline tools get <monitor-tool> --json`.
`describe` publishes inputs and pricing but NOT output fields for these tools, so every
output-field statement below is either from the monitor stream schema (which does
publish columns) or marked as something to confirm on the first response. Re-verify with
the same commands before trusting this after a catalog change.

## The tools

| Tool | Answers | Price (2026-09-30) |
|---|---|---|
| `harvestapi_get_profile_posts` | what did this person post | 0.03 credits per page |
| `harvestapi_get_company_posts` | what did this company page post | 0.03 credits per page |
| `harvestapi_get_post_reactions` | who reacted to this post | 0.03 credits per page |
| `harvestapi_get_post_comments` | who commented on this post | 0.03 credits per page |
| `aviato_get_post_reshares` | who reshared this post | 0.28 credits per call |
| `harvestapi_get_profile_comments` | what did this profile comment on | 0.03 credits per page |
| `harvestapi_search_posts` | posts matching a search, incl. `mentioningCompany` | 0.03 credits per page |
| `harvestapi_get_profile` | resolve an engager's profile (step 7) | usage-priced, read after execution |

`theswarm_get_post_reshares` also exists (free) but showed `connected: false` in the
author's org; check `connected` in `describe` before planning on it.

**Profile-keyed vs post-keyed is the axis that matters.** `get_profile_*` tools are keyed
on a profile and tell you what that profile did. `get_post_*` tools are keyed on a post
and tell you who engaged with it. This play runs one posts-by-author call to find the
posts, then post-keyed calls to find the people. Swapping them inverts the question while
still returning plausible data.

## Inputs, verbatim

### `harvestapi_get_profile_posts` — stage 1

| Parameter | Notes |
|---|---|
| `profile` / `profileId` / `profilePublicIdentifier` | one of them; `profileId` is documented as faster |
| `postedLimit` | `24h`, `week`, `month` — provider-side filter |
| `scrapePostedLimit` | post-filter: `1h`, `24h`, `week`, `month`, `3months`, `6months` |
| `page`, `paginationToken` | pass the token back when the previous page returned one |

The date filters are **buckets**. A user asking for "the last 14 days" gets `month` and
you drop the older posts by reading each post's date. A user asking for "last year" is
past the largest bucket — say that instead of reporting a thin result.

`harvestapi_get_company_posts` takes `company` / `companyId` / `companyUniversalName`
with the same date and paging parameters. Company pages are a supported stage-1 input.

### `harvestapi_get_post_reactions` / `harvestapi_get_post_comments` — stage 2

| Parameter | Notes |
|---|---|
| `post` | URL of the LinkedIn post (documented as required) |
| `page` | default 1 |
| `sortBy` (comments only) | `relevance` or `date` |
| `paginationToken` (comments only) | required only for `relevance` sort past page 1 |

### `aviato_get_post_reshares`

`postUrn` (required), `page`, `perPage`, `paginationToken`. Keyed on the post **URN**, not
the URL — carry the URN from stage 1's payload or derive it from the
`/feed/update/urn:li:…` form.

## Paging is the design constraint

There is no fixed per-post cap on these tools; there is a page budget you choose. That
moves the truncation decision from the platform to you, and the play is built around it:

1. **Page 1 only is a silent recall loss.** Read the first response to learn the page
   size and whether a total is reported, then set the budget per type deliberately.
2. **More pages existing means truncated, not complete.** A full last page, a returned
   pagination token, or a reported total above what you hold all mean ≥ that many
   engagers exist. Record it per post; it is the truncation signal.
3. **A short return proves nothing either.** Observed on Clay's equivalent reactions
   action (2026-08-13, one 0.5-credit probe): a request for 50 returned 48 on a
   well-engaged post. Providers return what they can reach. A short return is
   unexplained rather than complete.
4. **Popular posts are less observable** for the same budget. Ranking accounts by raw
   engagement volume therefore ranks partly by truncation, which is why intensity is
   scored per person over distinct interactions rather than by counting rows.

## Outputs — confirm on the first response

Map these concepts to the real field names before writing the gate:

```
engager name                display name
engager profile URL         ← canonicalize before keying
engager type                person vs organization discriminator (may be absent)
engager headline            the most useful field for identity resolution (may be absent)
interaction type / reaction like / celebrate / love / support …
comment text                comments only — the person's own words
post date                   on stage-1 posts — the window is enforced on this
```

Lessons from the Clay-era contract (2026-08-13) that still apply: the declared output
list was a SUBSET of the live payload (the headline arrived undeclared), so use what
arrives but never depend on an undeclared field; and a reaction's preview text was
synthesized (`"Like by <name>"`), not content.

The engager-type field is a provider field: present when the provider sends it, not
guaranteed. The URL-shape test (`/in/` → person, `/company/` → organization) is the
independent second test, and the play requires both.

## Canonicalization

Strip the query string, strip the trailing slash, lowercase. Necessary because the same
interactor arrives with and without tracking parameters across posts and
un-canonicalized URLs inflate one human into several.

The composite interaction key is
`clean_profile_url | interaction_type | canonical_post_url` — stable across re-runs, which
is what makes a weekly cadence additive instead of duplicative.

## Running it

A few posts run fine as ad-hoc calls:

```bash
deepline tools execute harvestapi_get_post_reactions \
  --input '{"post":"https://www.linkedin.com/posts/<slug>-activity-<id>-<hash>","page":1}'
```

Past ~20 posts, put the post list in a CSV and run a play with one `.withColumn` per
interaction type, so responses persist in the Customer DB and a rerun reuses filled
cells. The suppression gate and ranking are deterministic — a `run_javascript` column or
the agent on the exported rows.

## Standing version (Deepline monitor)

For a **company page**, a standing feed exists: `deepline_native.company_radar` with
`radar_type: company_social_engagements` (payload `domain`, optional `profile_url` for the
exact `linkedin.com/company/…` page), 1.25 credits per accepted event on 2026-09-30. Rows
land in `deepline_native.deepline_native_company_social_engagements` with columns
`post_url`, `post_posted_at`, `engagement_type`, `engagement_content`,
`author_profile_type`, `author_first_name`, `author_last_name`, `author_profile_url`,
`author_title`, `author_company_name`, `author_company_domain`, `author_country`,
`discovered_at` — Steps 5-9 apply to each row unchanged. Monitors are access-gated
(`deepline monitors status --json`); validate with `deepline monitors check` and
`deploy --dry-run`, and deploy only after the user approves the per-event price.

For a **person's** posts (founder, AEs) there is no engagement monitor:
`deepline_native.contact_social_engagements` streams what a tracked contact engages WITH,
which is the inverted question. A person-post watch is a scheduled re-run of this play,
with the interaction key carrying idempotency.

## Adjacent surfaces (not this play)

- **Brand-mention discovery** — posts ABOUT you rather than BY you:
  `harvestapi_search_posts` with `mentioningCompany`, or the `company_mentions` radar
  monitor. A different question; stage 1 here is posts by a profile you name.
- **Review-site intent** — the `company_reviews` radar monitor streams new employer and
  product reviews OF a company; it is not a category-scoped buyer-intent feed.
- **Identified website visitors** — `company_reveal` maps an IP to a company, but only on
  the user's own visitor logs; no Deepline tool lists who visited a site.
