import { isIP } from './native';
import suffixText from './assets/public-suffix-list.txt';
import { sha256 } from './json';

type HTMLHandlers = {
  onopentag?: (name: string, attributes: Record<string, string>) => void;
  onclosetag?: (name: string) => void;
  ontext?: (value: string) => void;
};
type HTMLParserConstructor = new (
  handlers: HTMLHandlers,
  options: { decodeEntities: boolean },
) => { end(value: string): void };
type IDNA = {
  toASCII(value: string, options: Record<string, boolean>): string | null;
  toUnicode(
    value: string,
    options: Record<string, boolean>,
  ): { domain: string; error: boolean };
};
// eslint-disable-next-line @typescript-eslint/no-require-imports -- Static package adapters retain bundling and explicit types in the Play checker.
export const Parser = require('htmlparser2').Parser as HTMLParserConstructor;
// eslint-disable-next-line @typescript-eslint/no-require-imports -- Static package adapters retain bundling and explicit types in the Play checker.
const tr46 = require('tr46') as IDNA;

export const VERSION = 'domain-evidence-v1.5';
export const PSL_HASH = sha256(suffixText);
export const BLOCKED_SUFFIXES = [
  '.localhost',
  '.local',
  '.internal',
  '.lan',
  '.home',
  '.test',
  '.invalid',
  '.onion',
];
const idnaOptions = {
  useSTD3ASCIIRules: true,
  checkBidi: true,
  checkJoiners: true,
  checkHyphens: true,
  transitionalProcessing: false,
  verifyDNSLength: true,
};

function idna(value: string): string {
  const result = tr46.toASCII(value, idnaOptions);
  if (!result) throw new Error('invalid_idna_domain');
  const decoded = tr46.toUnicode(result, idnaOptions);
  if (decoded.error) throw new Error('invalid_idna_domain');
  for (const label of decoded.domain.split('.')) {
    const chars = [...label];
    for (let i = 0; i < chars.length; i++) {
      const c = chars[i];
      if (/^[\p{L}\p{M}\p{Nd}-]$/u.test(c) || c === '\u200c' || c === '\u200d')
        continue;
      if (c === '\u00b7' && chars[i - 1] === 'l' && chars[i + 1] === 'l')
        continue;
      if (c === '\u0375' && /\p{Script=Greek}/u.test(chars[i + 1] ?? ''))
        continue;
      if (
        (c === '\u05f3' || c === '\u05f4') &&
        /\p{Script=Hebrew}/u.test(chars[i - 1] ?? '')
      )
        continue;
      if (
        c === '\u30fb' &&
        /[\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}]/u.test(
          label.replaceAll('\u30fb', ''),
        )
      )
        continue;
      throw new Error('invalid_idna_domain');
    }
    if (/[\u0660-\u0669]/u.test(label) && /[\u06f0-\u06f9]/u.test(label))
      throw new Error('invalid_idna_domain');
  }
  return result.toLowerCase();
}

type Suffix = {
  domain: string;
  suffix: string;
  is_private: boolean;
  top_domain_under_public_suffix: string;
};
const suffixRules = new Map<string, boolean>();
let privateRule = false;
for (const line of suffixText.split(/\r?\n/)) {
  if (line.includes('===BEGIN PRIVATE DOMAINS===')) privateRule = true;
  const rule = line.trim();
  if (!rule || rule.startsWith('//')) continue;
  const prefix = rule.startsWith('!') ? '!' : rule.startsWith('*.') ? '*.' : '';
  const ascii = tr46.toASCII(rule.slice(prefix.length), idnaOptions);
  if (!ascii) throw new Error('invalid_frozen_psl_rule');
  suffixRules.set(prefix + ascii, privateRule);
}

export function EXTRACT(host: string): Suffix {
  const labels = host.toLowerCase().replace(/\.$/, '').split('.');
  let suffix = '',
    is_private = false;
  for (let i = 0; i < labels.length; i++) {
    const tail = labels.slice(i).join('.');
    if (suffixRules.has('!' + tail)) {
      suffix = labels.slice(i + 1).join('.');
      is_private = suffixRules.get('!' + tail)!;
      break;
    }
    const wildcard =
      i + 1 < labels.length ? '*.' + labels.slice(i + 1).join('.') : '';
    if (suffixRules.has(tail) || suffixRules.has(wildcard)) {
      suffix = tail;
      is_private = suffixRules.get(tail) ?? suffixRules.get(wildcard)!;
      break;
    }
  }
  const suffixLength = suffix ? suffix.split('.').length : 0;
  const domain = labels[labels.length - suffixLength - 1] ?? '';
  return {
    domain,
    suffix,
    is_private,
    top_domain_under_public_suffix:
      domain && suffix ? `${domain}.${suffix}` : '',
  };
}

function parts(value: string) {
  const match =
    /^([A-Za-z][A-Za-z\d+.-]*):\/\/([^/?#]*)([^?#]*)(?:\?([^#]*))?(?:#.*)?$/su.exec(
      value,
    );
  if (!match) throw new Error('unsupported_url');
  const [, schemeRaw, authority, path, query = ''] = match;
  const scheme = schemeRaw.toLowerCase();
  if (!['https', 'http'].includes(scheme) || authority.includes('@'))
    throw new Error('unsupported_scheme_or_credentials');
  if (authority.includes('\\') || authority.includes('%'))
    throw new Error('invalid_idna_domain');
  if (authority.startsWith('[')) throw new Error('ip_literal_not_domain');
  const colon = authority.lastIndexOf(':');
  const host = (colon < 0 ? authority : authority.slice(0, colon)).replace(
    /\.$/,
    '',
  );
  const portText = colon < 0 ? '' : authority.slice(colon + 1);
  if (portText && !/^\d+$/.test(portText)) throw new Error('nonstandard_port');
  const port = portText ? Number(portText) : null;
  if (port !== null && ![80, 443].includes(port))
    throw new Error('nonstandard_port');
  return { scheme, host, port, path, query };
}

export function normalize_domain(value: string) {
  if (typeof value !== 'string') throw new Error('domain_must_be_string');
  const raw = value.trim();
  if (!raw || /[\s\u0000-\u001f]/u.test(raw))
    throw new Error('empty_domain_or_whitespace');
  const p = parts(raw.includes('://') ? raw : 'https://' + raw);
  if (isIP(p.host)) throw new Error('ip_literal_not_domain');
  const host = idna(p.host);
  // WHATWG also recognizes numeric IPv4 spellings such as 127.1 and 0x7f000001.
  let urlHost: string;
  try {
    urlHost = new URL(`https://${host}`).hostname;
  } catch {
    throw new Error('invalid_idna_domain');
  }
  if (isIP(urlHost)) throw new Error('ip_literal_not_domain');
  if (
    host.length > 253 ||
    !host.includes('.') ||
    BLOCKED_SUFFIXES.some((s) => host.endsWith(s))
  )
    throw new Error('nonpublic_domain_name');
  const extracted = EXTRACT(host);
  if (!extracted.suffix || !extracted.domain)
    throw new Error('unknown_or_bare_public_suffix');
  return {
    ascii_domain: host,
    unicode_domain: tr46.toUnicode(host, idnaOptions).domain,
    registrable_domain: extracted.top_domain_under_public_suffix,
    public_suffix: extracted.suffix,
    private_suffix: extracted.is_private,
    input_had_path: !['', '/'].includes(p.path),
    input_scheme: raw.includes('://') ? p.scheme : null,
  };
}

export function safe_url(value: string): string {
  if (
    typeof value !== 'string' ||
    value.length > 4096 ||
    /[\s\u0000-\u001f]/u.test(value)
  )
    throw new Error('invalid_url');
  const p = parts(value),
    normalized = normalize_domain(value);
  if (p.port !== null && p.port !== (p.scheme === 'https' ? 443 : 80))
    throw new Error('scheme_port_mismatch');
  const encode = (component: string, query: boolean) => {
    let output = '';
    for (let i = 0; i < component.length; ) {
      const c = String.fromCodePoint(component.codePointAt(i)!);
      if (c === '%' && /^[\da-fA-F]{2}$/.test(component.slice(i + 1, i + 3))) {
        output += component.slice(i, i + 3);
        i += 3;
        continue;
      }
      output +=
        /^[A-Za-z\d/:@!$&'()*+,;=\-._~]$/.test(c) || (query && c === '?')
          ? c
          : encodeURIComponent(c);
      i += c.length;
    }
    return output;
  };
  try {
    return `${p.scheme}://${normalized.ascii_domain}${encode(p.path || '/', false)}${p.query ? '?' + encode(p.query, true) : ''}`;
  } catch {
    throw new Error('invalid_unicode_url_component');
  }
}

export type DNSRecord = {
  name?: string;
  ttl_seconds?: number;
  type: string;
  value: string;
};
export type DNSResult = {
  status: string;
  records: DNSRecord[];
  [key: string]: unknown;
};
export function address_records(dns: Record<string, DNSResult>): string[] {
  return [
    ...new Set(
      ['A', 'AAAA'].flatMap((q) =>
        (dns[q]?.records ?? []).filter((r) => r.type === q).map((r) => r.value),
      ),
    ),
  ].sort();
}
export function classify_mx(dns: Record<string, DNSResult>) {
  const mx = dns.MX;
  if (!mx) throw new Error('missing_mx_query');
  if (mx.status !== 'ANSWER') {
    const state =
      mx.status === 'NXDOMAIN'
        ? 'DOMAIN_NXDOMAIN'
        : mx.status !== 'NODATA'
          ? 'UNKNOWN_DNS_ERROR'
          : address_records(dns).length
            ? 'IMPLICIT_MX_POSSIBLE'
            : ['A', 'AAAA'].some(
                  (q) => !['NODATA', 'NXDOMAIN'].includes(dns[q]?.status),
                )
              ? 'UNKNOWN_ADDRESS_DNS_ERROR'
              : 'NO_DNS_MAIL_ROUTE';
    return { state, mailbox_verified: false };
  }
  const entries: Array<{ priority: number; exchange: string }> = [];
  for (const rec of mx.records.filter((r) => r.type === 'MX')) {
    const fields = rec.value.trim().split(/\s+/);
    if (fields.length !== 2 || !/^\d+$/.test(fields[0]))
      return { state: 'INVALID_MX', mailbox_verified: false };
    entries.push({
      priority: Number(fields[0]),
      exchange: fields[1].toLowerCase().replace(/\.$/, '') || '.',
    });
  }
  const nulls = entries.filter((e) => e.exchange === '.');
  const state = nulls.length
    ? entries.length === 1 && nulls[0].priority === 0
      ? 'NULL_MX'
      : 'INVALID_NULL_MX_MIX'
    : 'EXPLICIT_MX';
  return {
    state,
    exchangers: entries,
    mailbox_verified: false,
    entity_identity_evidence: false,
  };
}

const LEGAL_RE =
  /\b(terms|privacy|legal|impressum|conditions|tos|agb|cgv|cgu|mentions l[eé]gales)\b/i;
const TERMS_RE =
  /(?:^|[^a-z0-9])(?:terms|conditions|tos|agb|cgv|cgu)(?:$|[^a-z0-9])/i;
const ENTITY_PHRASE_RE =
  /\b(registered office|registered (?:in|under)|operated by|provided by|data controller|company number|legal entity|contracting entity)\b/i;
const ENTITY_NAME_RE =
  /\b[A-Z][\p{L}\p{N}_&'-]*(?: [A-Z][\p{L}\p{N}_&'-]*){0,7},? (?:Inc(?:orporated)?\.?|LLC|L\.L\.C\.|Ltd\.?|Limited|GmbH|Corporation|Corp\.?)(?=[\s,.;:)]|$)/u;
const PARKED_RE =
  /\b(domain (?:is )?for sale|buy this domain|domain parking|this domain is parked)\b/i;
type LegalLink = { url: string; anchor_text?: string; discovery: string };
const compact = (value: string) => value.replace(/\s+/g, ' ').trim();

export function legal_priority(candidate: {
  url: string;
  anchor_text?: string;
}): number {
  let path = new URL(candidate.url).pathname;
  try {
    path = decodeURIComponent(path);
  } catch {
    /* Retain malformed escaping as captured text. */
  }
  const text = `${path} ${candidate.anchor_text ?? ''}`.replace(
    /([a-z])([A-Z])/g,
    '$1 $2',
  );
  return TERMS_RE.test(text) ? 0 : /legal|impressum/i.test(text) ? 1 : 2;
}
export function html_evidence(body: Uint8Array | string, base_url: string) {
  const links: Array<{ href: string; text: string }> = [],
    text: string[] = [];
  let anchor: { href: string; text: string } | null = null,
    ignore = 0;
  const hidden = new Set(['script', 'style', 'noscript', 'svg']);
  const parser = new Parser(
    {
      onopentag(tag, attrs) {
        if (hidden.has(tag)) ignore++;
        if (ignore) return;
        if (tag === 'a') anchor = { href: attrs.href ?? '', text: '' };
        if (
          [
            'p',
            'div',
            'li',
            'br',
            'h1',
            'h2',
            'h3',
            'footer',
            'section',
          ].includes(tag)
        )
          text.push('\n');
      },
      onclosetag(tag) {
        if (hidden.has(tag)) ignore = Math.max(0, ignore - 1);
        if (ignore) return;
        if (tag === 'a' && anchor) {
          links.push(anchor);
          anchor = null;
        }
        if (['p', 'div', 'li', 'h1', 'h2', 'h3', 'section'].includes(tag))
          text.push('\n');
      },
      ontext(data) {
        if (ignore) return;
        text.push(data);
        if (anchor) anchor.text += data;
      },
    },
    { decodeEntities: true },
  );
  parser.end(typeof body === 'string' ? body : new TextDecoder().decode(body));
  const lines = text.join('').split(/\r?\n/).map(compact).filter(Boolean),
    legal: LegalLink[] = [],
    rejected: Array<Record<string, unknown>> = [],
    seen = new Set<string>(),
    base = new URL(safe_url(base_url));
  for (const link of links) {
    if (!link.href.trim()) {
      if (LEGAL_RE.test(link.text))
        rejected.push({
          url: null,
          reason: 'missing_or_empty_legal_href_requires_review',
          anchor_text: compact(link.text).slice(0, 160),
        });
      continue;
    }
    if (!LEGAL_RE.test(link.text + ' ' + link.href.replace(/[-_]/g, ' ')))
      continue;
    let target: string;
    try {
      target = safe_url(new URL(link.href, base_url).href);
    } catch {
      continue;
    }
    const dest = new URL(target),
      same =
        dest.protocol === base.protocol &&
        dest.host === base.host &&
        dest.pathname.replace(/\/+$/, '') ===
          base.pathname.replace(/\/+$/, '') &&
        dest.search === base.search;
    if (
      same ||
      (dest.host === base.host && dest.pathname === '/' && !dest.search)
    ) {
      rejected.push({
        url: target,
        reason: 'self_or_homepage_legal_link_requires_review',
      });
      continue;
    }
    if (!seen.has(target)) {
      seen.add(target);
      legal.push({
        url: target,
        anchor_text: compact(link.text).slice(0, 160),
        discovery: 'page_link',
      });
    }
  }
  legal.sort((a, b) => legal_priority(a) - legal_priority(b));
  return {
    legal_links: legal.slice(0, 30),
    legal_links_truncated: legal.length > 30,
    rejected_legal_links: rejected.slice(0, 30),
    rejected_legal_links_truncated: rejected.length > 30,
    organization_text_excerpts: lines
      .filter((l) => ENTITY_PHRASE_RE.test(l) || ENTITY_NAME_RE.test(l))
      .slice(0, 8)
      .map((line) => ({
        text: line.slice(0, 500),
        truncated: line.length > 500,
        source_url: base_url,
        interpretation: 'candidate_text_requires_review',
      })),
    parking_text_signals: lines
      .filter((l) => PARKED_RE.test(l))
      .slice(0, 3)
      .map((l) => l.slice(0, 300)),
    text_extraction: 'static_html_no_javascript',
  };
}
export function legal_candidates(
  primary: { legal_links?: LegalLink[] },
  final_url: string,
): LegalLink[] {
  const candidates = [...(primary.legal_links ?? [])];
  if (!candidates.some((c) => legal_priority(c) === 0))
    candidates.unshift({
      url: new URL('/terms', final_url).href,
      discovery: 'conventional_path_probe',
    });
  if (
    candidates.length === 1 &&
    candidates[0].discovery === 'conventional_path_probe'
  )
    for (const path of ['/privacy', '/legal'])
      candidates.push({
        url: new URL(path, final_url).href,
        discovery: 'conventional_path_probe',
      });
  return candidates.sort((a, b) => legal_priority(a) - legal_priority(b));
}
export function body_issue_codes(result: Record<string, unknown>): string[] {
  return [
    ['body_incomplete_read', 'BODY_INCOMPLETE_READ'],
    ['body_truncated', 'BODY_TRUNCATED'],
  ]
    .filter(([key]) => result[key])
    .map(([, code]) => code);
}
export function evidence_page(
  input: Record<string, unknown>,
): Record<string, unknown> {
  const { body: raw, ...rest } = input,
    result = { ...rest } as Record<string, unknown>,
    body =
      typeof raw === 'string'
        ? new TextEncoder().encode(raw)
        : raw instanceof Uint8Array
          ? raw
          : new Uint8Array(),
    issues = body_issue_codes(result);
  result.body_sha256 = body.length ? sha256(body) : null;
  result.body_completeness = result.error
    ? 'UNAVAILABLE'
    : issues.length === 2
      ? 'INCOMPLETE_READ_AND_BYTE_LIMIT'
      : result.body_incomplete_read
        ? 'INCOMPLETE_READ'
        : result.body_truncated
          ? 'BYTE_LIMIT'
          : 'COMPLETE';
  if (body.length) {
    const headers = (result.headers ?? {}) as Record<string, string>,
      ctype = (headers['content-type'] ?? '').toLowerCase(),
      encoding = (headers['content-encoding'] ?? 'identity').toLowerCase();
    if (!['', 'identity'].includes(encoding))
      result.extraction_status = 'UNSUPPORTED_CONTENT_ENCODING';
    else if (
      ctype.includes('html') ||
      (!ctype &&
        /^(?:<!|<html)/.test(new TextDecoder().decode(body).trimStart()))
    ) {
      const parsed = html_evidence(body, String(result.final_url));
      Object.assign(result, parsed);
      result.extraction_status = issues.length
        ? 'PARTIAL_STATIC_HTML'
        : 'STATIC_HTML';
      result.organization_text_excerpts = parsed.organization_text_excerpts.map(
        (e) => ({ ...e, source_body_completeness: result.body_completeness }),
      );
    } else result.extraction_status = 'NON_HTML';
  }
  return result;
}
