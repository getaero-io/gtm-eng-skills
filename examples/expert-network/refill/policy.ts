export const TARGET = 100;
export const DOMAINS = [
  { domain: 'mckinsey.com', vertical: 'consulting' },
  { domain: 'lw.com', vertical: 'law' },
  { domain: 'bcg.com', vertical: 'consulting' },
  { domain: 'skadden.com', vertical: 'law' },
  { domain: 'bain.com', vertical: 'consulting' },
];
export const ACTIVE = ['research_pending', 'ready', 'contacted', 'onboarding'];
export function slots(count: number) { return Math.max(0, TARGET - count); }
export function normalize(raw: Record<string, any>, domain: string, vertical: string) {
  const name = raw.full_name || [raw.first_name, raw.last_name].filter(Boolean).join(' ');
  const title = String(raw.title || '');
  const profile = raw.linkedin_url || (raw.linkedin_id ? `https://www.linkedin.com/in/${raw.linkedin_id}` : '');
  if (!name || !/^https:\/\/(www\.)?linkedin\.com\/in\/[^/?#]+\/?$/i.test(profile)) return null;
  if (String(raw.company_domain || '').toLowerCase() !== domain || raw.country !== 'United States') return null;
  if (/recruit|talent|human resources|\bHR\b|chief |onboarding|marketing|administrative assistant|executive assistant|intern\b|retired/i.test(title)) return null;
  if (vertical === 'law' && /director|career|development|HRIS|head of knowledge/i.test(title)) return null;
  const relevant = vertical === 'law' ? /associate|counsel|partner|attorney|lawyer/i.test(title) : /consultant|engagement manager|associate partner|principal|partner|project leader/i.test(title);
  if (!relevant) return null;
  return { profile: profile.toLowerCase().replace(/^https:\/\/linkedin.com/, 'https://www.linkedin.com').replace(/\/$/, ''), name, title, domain, vertical, company: raw.company_name || domain, location: raw.location || '', source: 'search_contact', evidence: 'Provider-reported current role; specialty and credentials not independently verified' };
}
export const q = (s: string) => `'${s.replaceAll("'", "''")}'`;
export const j = (v: unknown) => `${q(JSON.stringify(v))}::jsonb`;
