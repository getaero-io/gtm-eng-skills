import {
  CtxFetchHttpError,
  type DeeplinePlayRuntimeContext,
  type PlayFetchResponse,
} from 'deepline';
import {
  normalize_domain,
  safe_url,
  classify_mx,
  address_records,
  evidence_page,
  legal_candidates,
  body_issue_codes,
  VERSION,
  PSL_HASH,
} from './domain';
import { classify_company_url } from './domain-policy';
import { sha256, type JsonObject } from './json';

export type DomainContext = Pick<
  DeeplinePlayRuntimeContext,
  'fetch' | 'step' | 'run'
>;
export type DomainOptions = {
  timeout?: number;
  max_bytes?: number;
  max_legal_pages?: number;
  max_redirects?: number;
};
const RR: Record<number, string> = { 1: 'A', 5: 'CNAME', 15: 'MX', 28: 'AAAA' };
const RCODES: Record<number, string> = {
  0: 'NOERROR',
  1: 'FORMERR',
  2: 'SERVFAIL',
  3: 'NXDOMAIN',
  4: 'NOTIMP',
  5: 'REFUSED',
};
const EVIDENCE_HEADERS = new Set(['content-type', 'content-encoding']);
function url_role(value: string) {
  const { category, eligible_company_domain, reason, policy_version } =
    classify_company_url(value);
  return { category, eligible_company_domain, reason, policy_version };
}
function object(value: unknown): value is JsonObject {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
export function redact_evidence_url(
  value: string,
  domainInput = false,
): string | null {
  const input = domainInput ? value.trim() : value,
    domainOnly = domainInput && !input.includes('://');
  try {
    if (domainInput) normalize_domain(value);
    const url = new URL(domainOnly ? `https://${input}` : input);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    url.username = '';
    url.password = '';
    url.search = '';
    url.hash = '';
    return domainOnly
      ? url.host + (url.pathname === '/' ? '' : url.pathname)
      : url.href;
  } catch {
    return null;
  }
}
export function redact_domain_input(value: string) {
  const sanitized = redact_evidence_url(value, true);
  return {
    value: sanitized,
    state: !value.trim()
      ? 'missing'
      : sanitized === null
        ? 'invalid'
        : sanitized === value
          ? 'unchanged'
          : 'normalized_or_redacted',
  };
}
function redact_evidence_urls(
  record: JsonObject,
  seen = new WeakSet<object>(),
): JsonObject {
  if (seen.has(record)) return record;
  seen.add(record);
  for (const [key, value] of Object.entries(record)) {
    if (key === 'input_domain' && typeof value === 'string') {
      const input = redact_domain_input(value);
      record[key] = input.value;
      record.input_domain_state = input.state;
    } else if (
      ['url', 'requested_url', 'final_url', 'source_url'].includes(key) &&
      typeof value === 'string'
    ) {
      const sanitized = redact_evidence_url(value);
      record[key] = sanitized;
      record[`${key}_sha256`] = sha256(value);
      record[`${key}_redaction_state`] =
        sanitized === null
          ? 'invalid_omitted'
          : sanitized === value
            ? 'unchanged'
            : 'normalized_or_redacted';
    } else if (Array.isArray(value)) {
      for (const item of value)
        if (object(item)) redact_evidence_urls(item, seen);
    } else if (object(value)) redact_evidence_urls(value, seen);
  }
  return record;
}
function transportFailure(error: unknown): JsonObject | null {
  if (!object(error)) return null;
  if (
    error.code === 'CTX_FETCH_TIMEOUT' ||
    ['AbortError', 'TimeoutError', 'CtxFetchTimeoutError'].includes(error.name)
  )
    return { error: 'TIMEOUT', error_type: error.name ?? 'Error' };
  if (error.name === 'UnsafeOutboundUrlError')
    return { error: 'SAFETY_OR_RESOLUTION_BLOCK', error_type: error.name };
  const cause = object(error.cause) ? error.cause : {};
  if (
    [
      'ENOTFOUND',
      'EAI_AGAIN',
      'ECONNRESET',
      'ECONNREFUSED',
      'ETIMEDOUT',
      'ERR_TLS_CERT_ALTNAME_INVALID',
      'CERT_HAS_EXPIRED',
      'DEPTH_ZERO_SELF_SIGNED_CERT',
      'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
    ].includes(String(error.code ?? cause.code)) ||
    (error instanceof TypeError &&
      /fetch failed|terminated|network/i.test(error.message))
  )
    return {
      error: 'TRANSPORT_ERROR',
      error_type: error.name ?? 'Error',
      transport_code: (error as JsonObject).code ?? cause.code ?? null,
    };
  return null;
}
export function parse_doh(value: unknown, qtype: string): JsonObject {
  if (
    !object(value) ||
    !Number.isInteger(value.Status) ||
    value.Status < 0 ||
    value.Status > 23 ||
    (value.Answer !== undefined && !Array.isArray(value.Answer))
  )
    throw new Error('Malformed DNS-over-HTTPS response');
  const records: JsonObject[] = [];
  for (const answer of value.Answer ?? []) {
    if (
      !object(answer) ||
      typeof answer.name !== 'string' ||
      !Number.isInteger(answer.type) ||
      typeof answer.data !== 'string' ||
      !Number.isInteger(answer.TTL) ||
      answer.TTL < 0
    )
      throw new Error('Malformed DNS resource record');
    records.push({
      name: answer.name.replace(/\.$/, '').toLowerCase(),
      ttl_seconds: answer.TTL,
      type: RR[answer.type] ?? `TYPE${answer.type}`,
      value: answer.data,
    });
  }
  const rcode = RCODES[value.Status] ?? `RCODE_${value.Status}`;
  return {
    query_type: qtype,
    status:
      value.Status !== 0
        ? rcode
        : records.some((r) => r.type === qtype)
          ? 'ANSWER'
          : 'NODATA',
    rcode,
    records,
    tool_returncode: null,
    resolver_transport: 'dns_over_https_json',
    dnssec_authenticated: typeof value.AD === 'boolean' ? value.AD : null,
    truncated_response: value.TC === true,
  };
}
export async function dns_query(
  ctx: DomainContext,
  domain: string,
  qtype: 'A' | 'AAAA' | 'CNAME' | 'MX',
  timeout = 8,
  observedAt: string | null = null,
): Promise<JsonObject> {
  let response: PlayFetchResponse;
  try {
    response = await ctx.fetch(
      'crm-domain-dns',
      `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(domain + '.')}&type=${qtype}`,
      {
        headers: { accept: 'application/dns-json' },
        signal: AbortSignal.timeout(timeout * 1000),
        redirect: 'error',
      },
      { staleAfterSeconds: 0 },
    );
  } catch (error) {
    const failure = transportFailure(error);
    if (!(error instanceof CtxFetchHttpError) && !failure) throw error;
    return {
      query_name: domain,
      query_type: qtype,
      status: failure?.error === 'TIMEOUT' ? 'TIMEOUT' : 'TOOL_ERROR',
      rcode: null,
      records: [],
      error_type: error instanceof Error ? error.name : 'Error',
      http_status: error instanceof CtxFetchHttpError ? error.status : null,
      observed_at: observedAt,
      elapsed_ms: null,
      resolver_transport: 'dns_over_https_json',
    };
  }
  try {
    const parsed = parse_doh(response.json, qtype);
    if (parsed.truncated_response)
      return {
        ...parsed,
        query_name: domain,
        status: 'TRUNCATED_DNS_RESPONSE',
        observed_at: observedAt,
        elapsed_ms: null,
      };
    return {
      ...parsed,
      query_name: domain,
      observed_at: observedAt,
      elapsed_ms: null,
    };
  } catch {
    return {
      query_name: domain,
      query_type: qtype,
      status: 'TOOL_ERROR',
      rcode: null,
      records: [],
      error_type: 'MalformedDohResponse',
      http_status: response.status,
      observed_at: observedAt,
      elapsed_ms: null,
      resolver_transport: 'dns_over_https_json',
    };
  }
}
export async function fetch_url(
  ctx: DomainContext,
  url: string,
  options: DomainOptions = {},
  observedAt: string | null = null,
): Promise<JsonObject> {
  const timeout = options.timeout ?? 8,
    maxBytes = options.max_bytes ?? 262144,
    maxRedirects = options.max_redirects ?? 5;
  const chain: JsonObject[] = [],
    visited = new Set<string>();
  let current = url;
  for (let hop = 0; hop <= maxRedirects; hop++) {
    try {
      current = safe_url(current);
      if (visited.has(current)) throw new Error('redirect_loop');
      visited.add(current);
    } catch (error) {
      return {
        requested_url: url,
        final_url: current,
        redirect_chain: chain,
        error: 'SAFETY_OR_RESOLUTION_BLOCK',
        error_detail: error instanceof Error ? error.message : String(error),
      };
    }
    const role = url_role(current);
    if (!role.eligible_company_domain)
      return {
        requested_url: url,
        final_url: current,
        redirect_chain: chain,
        error: 'INELIGIBLE_URL_ROLE',
        url_role: role,
      };
    let response: PlayFetchResponse;
    try {
      response = await ctx.fetch(
        'crm-domain-web',
        current,
        {
          method: 'GET',
          redirect: 'manual',
          signal: AbortSignal.timeout(timeout * 1000),
          headers: {
            'User-Agent': 'CRM-Domain-Evidence/2.0 (read-only research)',
            Accept: 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.1',
            'Accept-Encoding': 'identity',
          },
        },
        { staleAfterSeconds: 0 },
      );
    } catch (error) {
      if (error instanceof CtxFetchHttpError) response = error.response;
      else {
        const failure = transportFailure(error);
        if (!failure) throw error;
        chain.push({ url: current, ...failure });
        return {
          requested_url: url,
          final_url: current,
          redirect_chain: chain,
          ...failure,
          body_incomplete_read: null,
          connected_address: null,
          tls: { verified: null, version: null },
          transport_details:
            'Not exposed by guarded ctx.fetch; no IP binding or TLS-version claim',
        };
      }
    }
    const body = new TextEncoder().encode(response.bodyText),
      truncated = body.length > maxBytes;
    const metadata = {
      status: response.status,
      headers: Object.fromEntries(
        Object.entries(response.headers)
          .filter(([name]) => EVIDENCE_HEADERS.has(name.toLowerCase()))
          .map(([name, value]) => [name.toLowerCase(), value]),
      ),
      connected_address: null,
      tls: { verified: null, version: null },
      body_truncated: truncated,
      body_incomplete_read: false,
      extraction_byte_limit: maxBytes,
      transport_byte_limit: null,
      body_representation:
        'utf8_materialized_response_text_after_runtime_redaction',
      transport_details:
        'Deepline guards outbound addresses; resolved address and TLS session are not exposed',
      body_limit_scope:
        'Extraction limit after guarded transport completed; not a network download cap',
    };
    chain.push({ url: current, ...metadata });
    if (
      [301, 302, 303, 307, 308].includes(response.status) &&
      response.headers.location
    ) {
      try {
        current = new URL(response.headers.location, current).href;
      } catch {
        return {
          requested_url: url,
          final_url: current,
          redirect_chain: chain,
          error: 'SAFETY_OR_RESOLUTION_BLOCK',
          error_detail: 'invalid_redirect_location',
        };
      }
      continue;
    }
    return {
      requested_url: url,
      final_url: response.url || current,
      redirect_chain: chain,
      ...metadata,
      body: body.slice(0, maxBytes),
      observed_at: observedAt,
    };
  }
  return {
    requested_url: url,
    final_url: current,
    redirect_chain: chain,
    error: 'REDIRECT_LIMIT',
  };
}
export async function collectDomain(
  ctx: DomainContext,
  domain: string,
  options: DomainOptions = {},
): Promise<JsonObject> {
  const timeout = options.timeout ?? 8,
    maxBytes = options.max_bytes ?? 262144,
    maxLegal = options.max_legal_pages ?? 2,
    maxRedirects = options.max_redirects ?? 5;
  if (
    !(
      Number.isFinite(timeout) &&
      timeout > 0 &&
      timeout <= 30 &&
      Number.isInteger(maxBytes) &&
      maxBytes >= 1024 &&
      maxBytes <= 1048576 &&
      Number.isInteger(maxLegal) &&
      maxLegal >= 0 &&
      maxLegal <= 5 &&
      Number.isInteger(maxRedirects) &&
      maxRedirects >= 0 &&
      maxRedirects <= 5
    )
  )
    throw new Error('Invalid domain collection limits');
  const observedAt = await ctx.step(
    'domain-collection-clock',
    async () => new Date().toISOString(),
    { semanticKey: `${ctx.run.id}:${domain}` },
  );
  const record: JsonObject = {
    schema_version: VERSION,
    observed_at: observedAt,
    input_domain: domain,
    source_kind: 'public_dns_http',
    stage_errors: [],
    stage_skips: [],
    flags: [],
    collector: {
      version: 'domain-evidence-play.v1',
      psl_sha256: PSL_HASH,
      transport: 'guarded_ctx_fetch',
      dns: 'cloudflare_doh_json',
      freshness:
        'staleAfterSeconds=0; durable resume may reuse a completed same-run request',
      observation_clock:
        'checkpointed collection-start processing time; physical request time is retained in runtime receipts',
      limits: {
        timeout,
        max_bytes: maxBytes,
        max_legal_pages: maxLegal,
        max_redirects: maxRedirects,
      },
      byte_limit_scope: 'extraction_after_full_runtime_transport',
      url_redaction: 'userinfo_query_fragment_removed',
      crm_mutations: 0,
    },
    url_role: url_role(domain),
  };
  try {
    record.normalization = normalize_domain(domain);
  } catch (error) {
    const missing = typeof domain === 'string' && !domain.trim();
    record.stage_errors.push({
      stage: 'normalization',
      code: missing ? 'MISSING_DOMAIN' : 'INVALID_INPUT',
      detail: error instanceof Error ? error.message : String(error),
    });
    record.flags.push(
      missing ? 'missing_domain_input' : 'invalid_domain_input',
    );
    return redact_evidence_urls(record);
  }
  if (!record.url_role.eligible_company_domain) {
    record.flags.push('non_company_url_role_requires_review');
    record.stage_skips = ['dns', 'website', 'legal'].map((stage) => ({
      stage,
      code: 'INELIGIBLE_URL_ROLE',
    }));
    record.legal = {
      status: 'SKIPPED_BY_URL_ROLE',
      pages: [],
      identity_conclusion: 'NOT_DETERMINED',
    };
    return redact_evidence_urls(record);
  }
  const host = record.normalization.ascii_domain,
    dns: JsonObject = {};
  for (const type of ['A', 'AAAA', 'CNAME', 'MX'] as const)
    dns[type] = await dns_query(ctx, host, type, timeout, observedAt);
  record.dns = dns;
  record.mx = { ...classify_mx(dns), query_name: host };
  for (const [type, result] of Object.entries(dns) as Array<
    [string, JsonObject]
  >)
    if (!['ANSWER', 'NODATA'].includes(result.status))
      record.stage_errors.push({
        stage: `dns_${type.toLowerCase()}`,
        code: result.status,
      });
  if (!address_records(dns).length)
    record.flags.push('input_domain_has_no_observed_address');
  if (
    ['NULL_MX', 'NO_DNS_MAIL_ROUTE', 'INVALID_NULL_MX_MIX'].includes(
      record.mx.state,
    )
  )
    record.flags.push('mail_domain_attention');
  const opts = {
    timeout,
    max_bytes: maxBytes,
    max_legal_pages: maxLegal,
    max_redirects: maxRedirects,
  };
  const https = evidence_page(
    await fetch_url(ctx, `https://${host}`, opts, observedAt),
  ) as JsonObject;
  record.website = { https };
  let primary = https;
  if (https.error) {
    const http = evidence_page(
      await fetch_url(ctx, `http://${host}`, opts, observedAt),
    ) as JsonObject;
    record.website.http_fallback = http;
    if (!http.error) primary = http;
  }
  for (const [name, result] of Object.entries(record.website) as Array<
    [string, JsonObject]
  >) {
    if (result.error)
      record.stage_errors.push({
        stage: `website_${name}`,
        code: result.error,
        detail: result.error_detail ?? null,
      });
    else if (result.status >= 400)
      record.stage_errors.push({
        stage: `website_${name}`,
        code: `HTTP_${result.status}`,
      });
    for (const code of body_issue_codes(result))
      record.stage_errors.push({ stage: `website_${name}`, code });
  }
  record.website.selected_evidence =
    primary === https ? 'https' : 'http_fallback';
  record.legal = {
    status: 'NOT_ATTEMPTED',
    pages: [],
    identity_conclusion: 'NOT_DETERMINED',
  };
  if (!primary.error && primary.status >= 200 && primary.status < 300) {
    const finalUrl = primary.final_url,
      finalHost = normalize_domain(finalUrl);
    if (
      finalHost.registrable_domain !== record.normalization.registrable_domain
    )
      record.flags.push('cross_registrable_domain_redirect_requires_review');
    if (primary.parking_text_signals?.length)
      record.flags.push('possible_parked_domain_requires_review');
    const candidates = legal_candidates(primary, finalUrl),
      eligible: typeof candidates = [];
    for (const candidate of candidates) {
      const role = url_role(candidate.url);
      if (role.eligible_company_domain) eligible.push(candidate);
      else
        record.stage_skips.push({
          stage: 'legal',
          code: 'INELIGIBLE_URL_ROLE',
          url: candidate.url,
          url_role: role,
          candidates_not_attempted: 1,
        });
    }
    // Reconsider the Terms probe after excluded links are removed.
    const eligibleCandidates = legal_candidates(
        { legal_links: eligible },
        finalUrl,
      ),
      discoveredUrls = new Set(candidates.map((candidate) => candidate.url)),
      limited = Math.max(0, eligibleCandidates.length - maxLegal);
    record.legal.discovered_candidates = [
      ...candidates,
      ...eligibleCandidates.filter(
        (candidate) => !discoveredUrls.has(candidate.url),
      ),
    ];
    record.legal.candidates_blocked_by_url_role =
      candidates.length - eligible.length;
    record.legal.candidates_not_attempted =
      record.legal.candidates_blocked_by_url_role + limited;
    if (limited)
      record.stage_skips.push({
        stage: 'legal',
        code: 'LEGAL_PAGE_LIMIT',
        candidates_not_attempted: limited,
      });
    record.flags.push(
      ...new Set(
        (primary.rejected_legal_links ?? []).map(
          (link: JsonObject) => link.reason,
        ),
      ),
    );
    for (const candidate of eligibleCandidates.slice(0, maxLegal)) {
      const page = evidence_page(
        await fetch_url(ctx, candidate.url, opts, observedAt),
      ) as JsonObject;
      page.discovery = candidate.discovery;
      const final = new URL(page.final_url ?? candidate.url),
        website = new URL(finalUrl);
      const sameDocument =
        final.host === website.host &&
        final.pathname.replace(/\/$/, '') ===
          website.pathname.replace(/\/$/, '') &&
        final.search === website.search;
      const sameHome =
        final.host === website.host && final.pathname === '/' && !final.search;
      page.legal_context_eligible = !(sameDocument || sameHome);
      if (!page.legal_context_eligible) {
        page.legal_context_note =
          'candidate_resolved_to_website_document_or_homepage';
        record.flags.push('legal_candidate_redirected_home_requires_review');
      }
      record.legal.pages.push(page);
      if (page.error || page.status >= 400)
        record.stage_errors.push({
          stage: 'legal',
          url: candidate.url,
          code: page.error ?? `HTTP_${page.status}`,
        });
      for (const code of body_issue_codes(page))
        record.stage_errors.push({ stage: 'legal', url: candidate.url, code });
    }
    record.legal.status = record.legal.pages.some(
      (p: JsonObject) =>
        p.legal_context_eligible &&
        p.status >= 200 &&
        p.status < 300 &&
        p.organization_text_excerpts?.length,
    )
      ? 'CANDIDATE_TEXT_COLLECTED'
      : 'NO_ELIGIBLE_CANDIDATE_TEXT_FOUND';
    record.legal.body_evidence_partial =
      body_issue_codes(primary).length > 0 ||
      record.legal.pages.some(
        (p: JsonObject) => body_issue_codes(p).length > 0,
      );
    if (maxLegal === 0) record.legal.status = 'SKIPPED_BY_LIMIT';
    else if (
      record.legal.body_evidence_partial ||
      record.legal.candidates_not_attempted
    )
      record.legal.status = `PARTIAL_${record.legal.status}`;
  } else record.legal.status = 'BLOCKED_BY_WEBSITE_RESULT';
  if (record.stage_errors.length)
    record.flags.push('stage_failures_require_review');
  record.completed_at = await ctx.step(
    'domain-completion-clock',
    async () => new Date().toISOString(),
    { semanticKey: `${ctx.run.id}:${domain}` },
  );
  // Keep request URLs until legal-link checks finish. Redact only saved evidence.
  return redact_evidence_urls(record);
}
