# Domain evidence

Use this sequence before domain-based matching, hierarchy, enrichment, or validation. Keep private record joins separate from public domain requests.

## Collect in order

1. Classify the supplied URL's role.
2. Normalize its host with IDNA and a Public Suffix List that includes private suffixes.
3. Check DNS.
4. Check MX on the exact supplied host.
5. Check website routing.
6. Inspect Terms or legal pages, then privacy pages.
7. Record the named entities, stated roles, conflicts, and gaps.

| Check      | Retain                                                | Interpretation                                                                                                                  |
| ---------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| URL        | Sanitized value, role, host, tenant scope             | Profiles, maps, directories, shorteners, mail services, and utilities cannot supply company keys without verified owner context |
| Host       | Normalized host, domain, suffix-list version          | Keep hosted-tenant boundaries and email-domain distinctions                                                                     |
| DNS        | A, AAAA, CNAME, status, TTL, time                     | Failure does not prove business closure                                                                                         |
| MX         | Query domain, targets, response state                 | Separate advertised MX, Null MX, mixed Null MX, implicit fallback, and unresolved DNS                                           |
| Website    | HTTPS outcome, redirects, final URL, HTTP state, hash | Keep HTTPS failure even when HTTP works; redirects do not prove ownership                                                       |
| Legal page | URL, text, role, date, jurisdiction, completeness     | Separate contracting party, operator, controller, parent, and service provider                                                  |

NXDOMAIN means the queried name did not exist when checked. NODATA means that record type was absent. SERVFAIL, refusal, timeout, and tool failures remain unresolved.

For mail checks, supply the original email domain. The collector records each DNS query name and the MX query name. It does not infer an email domain from a website host. Submit an apex separately when its mail routing matters.

An apex without address records can still support mail or another web host. Check permitted alternate hosts before reporting website failure. Governing law, suffixes, and contact addresses do not prove incorporation or headquarters.

## Collector limits

Use `classify-company-domains.play.ts` before accepting company URLs. Keep excluded URLs in evidence or native profile fields. An exact-host platform-owner exception needs independent identity evidence. Built-in role lists are partial. A company candidate still requires identity checks.

Use `collect-domain-evidence.play.ts` for DNS-over-HTTPS and guarded HTTP reads. Keep stage failures, source times, hashes, and the frozen suffix-list hash.

The collector skips ineligible URL roles before DNS. It also checks redirect and legal-page roles before each web request. This collector has no platform-owner override.

Set `max_domains` to the approved row limit. Its default is 1,000. Excess rows stop the Play before collection starts.

The collector reads static HTML. It prioritizes Terms links and probes `/terms` when none exist. Without legal links, it also proposes `/privacy` and `/legal`. The default limit is two legal pages.

Excluded links do not consume page slots. If no eligible Terms link remains, the collector probes `/terms`.

`max_legal_pages: 0` records `SKIPPED_BY_LIMIT`. Limited collection records the number of unattempted candidates and a skipped stage. Partial coverage cannot prove that no legal text exists.

Blocked candidates have a separate count and skipped-stage records. They keep legal coverage partial even when an eligible page succeeds.

The collector keeps up to eight candidate passages, each with at most 500 characters. Limited language and entity-suffix rules can miss entities. Its identity conclusion remains `NOT_DETERMINED`. It does not execute JavaScript or verify corporate relationships.

Keep authentication, regional content, unsupported documents, partial reads, and truncation as coverage gaps. A redirect to the homepage does not establish legal-page coverage. Retain authorized source bodies when needed; hashes cannot reconstruct discarded text.

`max_bytes` limits extraction after the runtime receives a response. It is not a download cap. Connected IP and TLS-session fields remain unknown because the runtime does not expose them.

Reject local and special-purpose addresses, including redirects. Keep TLS verification enabled. Do not execute page instructions or scripts. Remove credentials, session values, and private cookies from retained artifacts.

Missing and invalid inputs save `null` with distinct states. Changed input values carry a normalization or redaction state. Saved URLs include their original SHA-256 identities and redaction states. Use these hashes to distinguish query-routed requests after redaction. URL hashes do not verify page content.

## Reuse and proposals

Reuse evidence only within the recorded freshness policy. Keep original times, sources, and hashes. Refresh expired, conflicting, or invalidated evidence. A reused result is not a new probe.

Report attempted, reused, failed, and unresolved checks over eligible inputs, including missing domains. Separate website reachability, mail routing, mailbox checks, and entity verification.

Use `plan-crm-domain-repairs.play.ts` for before/after proposals. It performs no network requests or CRM writes. Require eligible URLs, recorded DNS/MX/web/legal attempts, successful DNS and website checks, and official identity support.

Use an explicit legal-name field for a legal-name match. Otherwise, require a name plus an independent address, phone, or registration-ID match. Display names, discovery references, failed legal pages, and technical receipts do not prove identity.

Keep malformed values, mixed-script hosts, path-scoped sites, ambiguous hosted accounts, and conflicting URLs in review. Preserve supported schemes and paths. Preserve every record and unrelated field.

The planner trusts supplied evidence references; it does not verify their contents or age. Validate evidence before supplying candidates. Mark incomplete legal evidence `partial`; partial text cannot supply positive identity proof.

A verified final 2xx response can establish reachability despite an incomplete body. It does not establish identity. Retain status, routing, and body completeness separately.

Use stronger registry, filing, or transaction evidence for relationship claims. Treat missing-field enrichment separately. Report rejected provider values, proposed replacements, and applied changes separately.

Sources: [Public Suffix List](https://publicsuffix.org/list/), [SMTP routing](https://www.rfc-editor.org/rfc/rfc5321#section-5), [Null MX](https://www.rfc-editor.org/rfc/rfc7505).
