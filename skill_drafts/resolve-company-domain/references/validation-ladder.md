# The validation ladder — probes, gates, entity rules, arms

Arms confirmed with `deepline tools describe` 2026-09-30; re-check prices with
`describe` before quoting (prices and contracts drift). Behaviour notes marked
"measured on Clay" were observed on Clay's equivalent actions, 2026-08-11, and are
kept as cautions, not Deepline facts.

## Arms + costs

| Arm | Cost | Role |
|---|---|---|
| `crustdata_v3_company_identify` (`names` → domain, LinkedIn URL) | free | candidate generator, name-only rows. Commodity by itself — this skill IS its verification lever. Name-only matches can be unrelated even at `confidence_score: 1.0` |
| `generic_http_request` GET | free | the liveness probe — returns `status_code`, `ok`, `final_url` (with `follow_redirects`) and `data`. Read status and final URL directly; set a User-Agent header |
| DNS resolution (`dig`, any local tool) | free | NXDOMAIN / no-resolve pre-gate; dead domains grind scrapers for 60s+ while DNS answers instantly |
| `contextdev_get_web_scrape_markdown` | free | site-content check on survivors only (`markdown`, `metadata`). A `success` flag is not page-existence — read the body |
| `crustdata_v3_company_enrich` | 0.8 credits/result | entity corroboration ONLY — never liveness: enrichment returns last-known firmographics for dead AND acquired companies (measured on Clay's Enrich Company; assume the same of any cached index). Read the company website field, never a shortener-prone link field |
| `crustdata_v3_company_search` | 0.02 credits/returned result | secondary candidates only when hints exist; recall-not-exact — can miss the canonical entity and rank unrelated orgs above it; gate on match confidence, never position |
| `serper_google_search` / `exa_search` | per `describe` | the news screen for zombie-site and acquisition corroboration |

## The ladder, in order (cheap kills first)

1. **Normalize** (code): lowercase, strip scheme/`www.`/paths/query; registrable
   label via public-suffix-aware extraction (a naive `split(".")[-2]` kills
   co.uk-family domains).
2. **DNS / liveness probe** (free): NXDOMAIN → dead candidate. The HTTP probe's
   verdict: a non-2xx `status_code` → dead/broken; a 2xx with `follow_redirects` on
   returns `final_url` (cross-check the body's canonical/og:url tags) — validate THAT
   destination domain (brand→corporate redirects are normal; note
   the hop). A destination on social media or a registrar/parking body → inactive
   candidate, not an operating site.
3. **Site-content check** (free, survivors only): homepage markdown must plausibly
   BE the company — brand/name present (allowing rebrand/acquisition with
   reasoning), coherent business content, not a parking/for-sale/soft-404 body.
   Quote the line that convinced you into provenance.
4. **Semantic name↔domain match**: does the site represent the NAMED company —
   subsidiary and REBRAND acceptable with the reasoning stated; **acquisition is
   NOT a pass** — "X is now part of Y" / acquirer branding / redirect-to-acquirer
   means the X domain is stale: verdict `acquired`, acquirer domain as candidate.
   A similarly-named different business is the fail case. Name-boundary
   discipline: `<Name> Partners|Group|Capital|Holdings` and vessel/product
   designations are DIFFERENT entities.
5. **Operating-entity check** (judgment + optional corroboration): holding parent
   vs operating company vs franchise brand — say which the domain hosts; when the
   user's intent is unclear, resolve to the operating entity and flag the
   hierarchy. Corroborate with `crustdata_v3_company_enrich` (website field) when the site is
   thin.

## The override bar and the zombie-site trap (iteration-3 rules)

- **An acquisition-language signal on the candidate's own page is overridden only by
  positive counter-evidence** — the language provably refers to a different entity,
  or to THIS company acquiring others. "Looks like boilerplate" is not
  counter-evidence: unresolved acquisition signals degrade the row to a flag
  (`acquired` if the acquirer is identifiable, `ambiguous` otherwise), never to a
  clean assertion.
- **A live site with a matching name is necessary, not sufficient, when any signal
  conflicts.** Zombie sites are real: acquired or defunct companies leave their
  marketing site running with no banner. When an acquisition flag, a liveness
  conflict, or staleness indicators (old copyright year, dead blog, stale news)
  exist on an otherwise-passing candidate, corroborate independently before
  asserting — the news screen (`serper_google_search`, "<name> acquired OR shut down",
  past-year `tbs` window) and/or the enrich payload's website field. Corroboration clean → assert;
  corroboration reveals absorption/shutdown → the matching verdict; corroboration
  silent but the conflict stands → flag, don't assert.
- **Bot-blocked roots (403/429/challenge) are UNVERIFIED, not alive.** Without
  content evidence the confidence vocabulary cannot reach `validated`: corroborate
  independently (enrichment + hints) to assert at `corroborated`, else degrade to
  `ambiguous` with the block noted.
- **Probe surface unavailable = same discipline, different cause.** When the
  environment can't reach sites at all (egress-blocked agent, or the probe tool
  erroring instead of returning a status), rungs 2-3 are NOT skippable-as-passed: corroborate via
  enrichment to assert at `corroborated`, never `validated`, and say why. A DNS
  answer through a proxy can be synthetic — a half-signal, not liveness. Bonus
  while corroborating: the identify and enrich payloads carry the company's
  LinkedIn URL — harvest it into the row; downstream skills' high-accuracy arms
  (headcount, people finds) key off it for free.

## Ambiguity policy (the refusal gate)

- A common-word or multi-entity name (the lookup will still answer confidently) →
  `ambiguous` + candidate list (one evidence line each). Signals: the name is a
  dictionary word; hints (geo/industry) don't discriminate; two living candidates
  both pass content checks.
- Hints narrow BEFORE refusing: country/region, industry, a known person there, a
  LinkedIn company URL — each can pin the entity. Refuse only when hints are
  exhausted.
- The confidence vocabulary: `validated` (ladder passed on the site's own
  evidence) · `corroborated` (ladder + independent enrichment agree) — nothing
  weaker ships as resolved.

## Batch mechanics

Dedupe names first (case/suffix-insensitive: "Acme", "Acme Inc.", "ACME" are one
lookup). Free gates run across the whole batch before any paid step; paid
corroboration only on candidates that survived. For 1-20 rows call the tools
directly:

```bash
deepline tools execute crustdata_v3_company_identify --input '{"names":["Brightloop"]}' --json
deepline tools execute generic_http_request --input '{"url":"https://brightloop.example","method":"GET","follow_redirects":true}' --json
deepline tools execute contextdev_get_web_scrape_markdown --input '{"url":"https://brightloop.example","useMainContentOnly":true}' --json
```

For larger batches write a play (CSV in, one `.withColumn` per rung; see the
`deepline-gtm` skill's recipes/deepline-plays.md) and pilot on 3 rows first. Read
actual spend from `deepline runs get <run-id> --full --json` or `deepline billing`.
Gate on an actual domain value in the payload, never on run status (a completed
call with an empty result is the ordinary miss shape).
