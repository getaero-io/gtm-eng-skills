# Public technology evidence

Reviewed 2026-09-09. These are collection and interpretation rules, not a deployed crawler or proof of predictive value. Read deepline-pre-research before selecting providers. Freeze signatures before holdout evaluation, just like keyword rules.

## Collect these surfaces

| Surface | Check | Interpretation / trap |
| --- | --- | --- |
| HTML | script src, iframe src, form action, meta generator, stylesheet hosts | An embedded reference is not proof of a successful load. |
| Tags and snippets | Vendor-specific data attributes, widget initialization, structured configuration | Record a reviewed signature ID, not arbitrary script contents. Comments, samples, and unused config are not runtime evidence. |
| Rendered DOM | Widgets inserted after page load, public scheduler/chat frames | Record route, viewport, consent state, and capture time. |
| Network | Request hostname, resource type, response status, frame/initiator grouping | A completed 2xx response is stronger than a tag; still not proof of execution, a paid subscription, or organization-wide use. |
| Public portals | Official-site links to customer, payment, booking, partner or competitor portals | A public link suggests a relationship. A generic vendor login does not establish a customer account. Do not attempt login or guess tenants. |
| Official partner evidence | Named customer directory, certification, marketplace listing, case study | Match the legal entity/brand and date. Partner status is different from installed software. |
| Public infrastructure | DNS CNAME for an already-discovered custom portal; observed redirects | Shared hosting/CDN/agency tags do not establish common ownership. No broad security scans. |
| Historical changes | Same page and conditions across dated captures | Appearance/removal is a migration hypothesis; failed loads and consent changes are alternatives. |
| Hiring/docs | Explicit role duties and system names | Separate candidate mentions, desired experience and planned migrations from current use. |

Start with the homepage and discovered booking, contact, customer-portal and careers pages. Set an explicit page/time budget. Do not infer absence from the homepage alone. Record unvisited and blocked pages.

## Source routes and live contract findings

Public documentation checked before catalog inspection; Deepline tools were searched and described on the review date. No paid retrieval pilot was run. Re-describe before execution; credentials shown as connected are not a guarantee of successful collection.

| Route | Best use | Contract / cost boundary |
| --- | --- | --- |
| Native Firecrawl: `firecrawl_scrape` | First pass for page source, links and text | Request `rawHtml`, not only markdown or cleaned `html`; `onlyMainContent:false`. Live base price: 0.02 Deepline credits/page; options add cost. Declared Deepline output schema exposes html/markdown/metadata but omits rawHtml: inspect actual rawV2 in an approved pilot. Missing rawHtml is a connector gap, not an empty site. |
| Native Browserbase: `browserbase_create_session` + custom Playwright collector | Runtime requests, injected widgets, frames | Session alone does not collect evidence. Connect an authorized CDP client; attach listeners before navigation, use bounded waits and close in finally. Runtime/bandwidth pricing is usage-based, not a quoted fixed price. Never persist connectUrl/signingKey. |
| Native BuiltWith: `builtwith_domain_lookup` | Independent indexed technographics and detection history | Inspect Results -> Result.Paths -> Technologies, entity and LastDetected. Usage-based price unresolved until estimate/pilot. Free lookup provides category summaries, not vendor-level proof. Indexed current status is not a live browser test. |
| Generic public HTTP / local Playwright | Static HTML baseline or self-managed runtime | Only where credentials, permitted access and runtime are available. No new service necessary just for parsing. Respect TLS, rate limits and access restrictions. |
| Private customer systems | Actual usage, contracts, seats, support volumes | Separate owner-authorized source. No inference from a public portal replaces this. |

Firecrawl raw HTML is not a network trace. Browserbase Fetch is not interchangeable with a fully instrumented browser session. A headless session may miss region-, consent-, interaction-, or identity-dependent tools. Do not evade access blocks. Disable automatic CAPTCHA solving and stealth escalation; stop at access restrictions. A failed page status can coexist with a successful scrape API response.

Before scale, search/describe an existing technology-audit play. If none provides raw DOM + network evidence + provenance, record that mismatch and author the missing collection layer through the current plays workflow. Do not claim this reference is already an executable play.

## Normalized observation contract

One row per observation, not one guessed boolean per account:

`account_id, page_url, observed_at, kind, resource_url, status, resource_type, signature_id, signature_source, vendor_domain, component_id, collection_limits`.

- `kind`: mention, public_link, embedded, snippet, network.
- `observed_at`: timezone-aware timestamp. Retain source publication/cache time separately when known.
- `component_id`: ties DOM, script and requests from one widget together. Three traces from one widget are not three independent confirmations.
- Signatures must specify vendor/product, exact host or controlled suffix, context, source URL, review date, version, and positive/negative fixtures. Shared CDNs require a product-specific path or snippet signature; a hostname alone is insufficient.
- The offline gate requires signature provenance but cannot authenticate it, parse arbitrary HTML or validate registry ownership. Upstream normalization and human registry review remain required.
- Export only hostnames and signature IDs by default. Drop URL paths, queries, fragments, userinfo, cookies, headers, response bodies and raw snippets from the report; they can contain identifiers or tokens. Keep any necessary source artifact separately with restricted access and retention.
- Output levels: mention_only, public_link, embedded_reference, snippet_candidate, requested, response_observed, failed_request, unmatched_domain. None means contracted, actively used, or scoring eligible.
- Track collection status separately: complete_for_scope, partial, blocked, error. No match always means not_observed, never absent.

## Release and adversarial gates

Require no false confirmations on: vendor.com.evil.test; evilvendor.com; URL userinfo; vendor name only in query; commented script; sample code; generic GTM tag; blocked request; redirected login; old cached page; shared agency tag; duplicated widget traces. Test genuine subdomains and successful resource responses too. Human-review snippets in executable context; a regex hit remains a candidate.

Use a labeled, cross-vertical site set and known counterexamples before release. Report precision by evidence level, coverage by page/consent/region, unknown rate, source freshness, incremental recall over the static baseline, and credits per verified finding. Do not optimize for raw match count. Offline tests are not live collection validation.

Sources: [Firecrawl formats and page status](https://docs.firecrawl.dev/features/scrape), [Browserbase sessions](https://docs.browserbase.com/platform/browser/getting-started/using-browser-session), [Playwright network events](https://playwright.dev/docs/network).
