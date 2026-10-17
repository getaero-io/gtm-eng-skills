import { normalize_domain, safe_url, EXTRACT } from './domain';

export type CompanyURLClassification = {
  category: string;
  eligible_company_domain: boolean;
  reason: string;
  raw_url: unknown;
  normalized_url: string | null;
  hostname: string | null;
  registrable_domain: string | null;
  policy_version: string;
  next_step: string;
};
const under = (host: string, root: string) =>
  host === root || host.endsWith('.' + root);
const refs = (value: unknown): value is string[] =>
  Array.isArray(value) &&
  value.length > 0 &&
  value.every((x) => typeof x === 'string' && Boolean(x.trim()));
export function classify_company_url(
  raw: unknown,
  context?: unknown,
): CompanyURLClassification {
  const result: CompanyURLClassification = {
    category: 'invalid',
    eligible_company_domain: false,
    reason: 'invalid_input',
    raw_url: raw ?? null,
    normalized_url: null,
    hostname: null,
    registrable_domain: null,
    policy_version: POLICY_VERSION,
    next_step: 'discover_and_verify_company_domain',
  };
  if (raw == null || (typeof raw === 'string' && !raw.trim()))
    return {
      ...result,
      category: 'missing',
      reason: 'missing_company_website',
    };
  if (typeof raw !== 'string') return result;
  let value = raw.trim();
  if (value.length > 4096 || /[\s\u0000-\u001f\\]/u.test(value))
    return { ...result, reason: 'unsafe_or_malformed_url' };
  if (value.startsWith('//')) value = 'https:' + value;
  else if (!value.includes('://')) value = 'https://' + value;
  let normalized: ReturnType<typeof normalize_domain>, safe: string;
  try {
    normalized = normalize_domain(value);
    safe = safe_url(value);
  } catch (error) {
    return {
      ...result,
      reason: error instanceof Error ? error.message : 'invalid_input',
    };
  }
  const host = normalized.ascii_domain,
    reg = normalized.registrable_domain,
    parts = new URL(safe);
  Object.assign(result, {
    normalized_url: safe,
    hostname: host,
    registrable_domain: reg,
  });
  for (const label of normalized.unicode_domain.split('.')) {
    const scripts = [
      /\p{Script=Latin}/u,
      /\p{Script=Cyrillic}/u,
      /\p{Script=Greek}/u,
    ].filter((re) => re.test(label));
    if (scripts.length > 1)
      return { ...result, reason: 'mixed_script_hostname_requires_review' };
  }
  let category: string | null = null;
  const extracted = EXTRACT(host),
    google =
      !extracted.is_private &&
      extracted.domain === 'google' &&
      reg === 'google.' + extracted.suffix;
  if (google)
    category =
      host.startsWith('maps.') || /^\/maps(?:\/.*)?$/i.test(parts.pathname)
        ? 'mapping'
        : 'platform_utility';
  else if (under(host, 'bing.com'))
    category = parts.pathname.toLowerCase().startsWith('/maps')
      ? 'mapping'
      : 'platform_utility';
  else if (
    under(host, 'maps.app.goo.gl') ||
    (under(host, 'goo.gl') && parts.pathname.toLowerCase().startsWith('/maps'))
  )
    category = 'mapping';
  else
    for (const [kind, roots] of Object.entries(ROOTS)) {
      if (roots.some((root) => under(host, root))) {
        category = kind;
        break;
      }
    }
  if (
    !category &&
    HOSTED_ROOTS.some((root) => host === root || host === 'www.' + root)
  )
    category = 'platform_utility';
  if (
    !category &&
    PATH_TENANT_ROOTS.some((root) => under(host, root)) &&
    (!['', '/'].includes(parts.pathname) || under(host, 'wixsite.com'))
  )
    return {
      ...result,
      category: 'hosted_path',
      reason: 'path_scoped_hosted_site_requires_identity_review',
      next_step: 'preserve_full_url_and_verify_tenant_identity',
    };
  if (category) {
    const exception =
      context && typeof context === 'object' && !Array.isArray(context)
        ? (context as Record<string, unknown>).platform_self
        : null;
    if (
      exception &&
      typeof exception === 'object' &&
      !Array.isArray(exception)
    ) {
      const self = exception as Record<string, unknown>;
      if (
        self.verified === true &&
        self.hostname === host &&
        refs(self.evidence_refs) &&
        ['', '/'].includes(parts.pathname) &&
        !parts.search
      )
        return {
          ...result,
          category: 'platform_self',
          eligible_company_domain: true,
          reason: 'verified_exact_platform_origin',
          next_step: 'retain_evidence_and_validate_freshness',
        };
    }
    return {
      ...result,
      category,
      reason: category + '_is_not_company_website',
      next_step:
        category === 'shortener'
          ? 'resolve_full_url_and_verify_destination'
          : 'discover_official_website_and_verify_identity',
    };
  }
  return {
    ...result,
    category: HOSTED_ROOTS.some((root) => host !== root && under(host, root))
      ? 'hosted_site'
      : 'company_candidate',
    eligible_company_domain: true,
    reason: 'eligible_candidate_not_identity_verification',
    next_step: 'collect_dns_mx_web_legal_and_verify_identity',
  };
}
export function is_eligible_company_domain(
  raw: unknown,
  context?: unknown,
): boolean {
  return classify_company_url(raw, context).eligible_company_domain;
}
export const POLICY_VERSION = 'company-domain-role.v1.3';
export const ROOTS = {
  social_profile: [
    'linkedin.com',
    'lnkd.in',
    'facebook.com',
    'fb.com',
    'instagram.com',
    'twitter.com',
    'x.com',
    'tiktok.com',
    'youtube.com',
    'youtu.be',
    'pinterest.com',
    'threads.net',
    'threads.com',
    'reddit.com',
    'snapchat.com',
    'xing.com',
    'vk.com',
    'weibo.com',
    'fb.me',
  ],
  shortener: [
    'bit.ly',
    'bitly.com',
    'tinyurl.com',
    't.co',
    'goo.gl',
    'ow.ly',
    'buff.ly',
    'rebrand.ly',
    'shorturl.at',
    'cutt.ly',
    'rb.gy',
    'is.gd',
    's.id',
    'lnk.to',
    'short.io',
    'tiny.cc',
    'urlz.fr',
    'goo.gle',
  ],
  directory: [
    'crunchbase.com',
    'zoominfo.com',
    'apollo.io',
    'dnb.com',
    'dandb.com',
    'yellowpages.com',
    'yelp.com',
    'glassdoor.com',
    'indeed.com',
    'opencorporates.com',
    'pitchbook.com',
    'bloomberg.com',
    'rocketreach.co',
    'theorg.com',
    'manta.com',
    'trustpilot.com',
    'wellfound.com',
    'angel.co',
    'foursquare.com',
    'bbb.org',
    'kompass.com',
  ],
  aggregator: [
    'linktr.ee',
    'linktree.com',
    'bio.link',
    'beacons.ai',
    'about.me',
    'solo.to',
    'lnk.bio',
    'campsite.bio',
    'allmylinks.com',
  ],
  free_email: [
    'gmail.com',
    'googlemail.com',
    'yahoo.com',
    'ymail.com',
    'hotmail.com',
    'outlook.com',
    'live.com',
    'msn.com',
    'aol.com',
    'icloud.com',
    'me.com',
    'hotmail.fr',
    'hotmail.de',
    'yahoo.it',
    'yahoo.fr',
    'yahoo.com.br',
    'qq.com',
    '163.com',
    '126.com',
    'sympatico.ca',
    'proton.me',
    'protonmail.com',
    'gmx.com',
    'gmx.de',
    'mail.com',
    'yahoo.co.jp',
    'windowslive.com',
    'yandex.ru',
    'web.de',
    'zohomail.in',
  ],
  mapping: [
    'maps.app.goo.gl',
    'maps.google.com',
    'maps.apple.com',
    'binged.it',
    'g.page',
    'map.baidu.com',
    'mapquest.com',
    'openstreetmap.org',
    'waze.com',
    'here.com',
  ],
  platform_utility: [
    'docs.google.com',
    'drive.google.com',
    'forms.gle',
    'forms.google.com',
    'calendar.google.com',
    'sites.google.com',
    'wa.me',
    'api.whatsapp.com',
    'business.site',
    'yandex.com',
    'github.com',
    'gitlab.com',
    'notion.so',
    'onmicrosoft.com',
    'open.spotify.com',
    'txt.att.net',
  ],
};
export const HOSTED_ROOTS = [
  'github.io',
  'gitlab.io',
  'wordpress.com',
  'webflow.io',
  'wixsite.com',
  'squarespace.com',
  'myshopify.com',
  'netlify.app',
  'vercel.app',
  'pages.dev',
  'blogspot.com',
  'notion.site',
];
export const PATH_TENANT_ROOTS = [
  'wixsite.com',
  'github.io',
  'gitlab.io',
  'notion.site',
];
