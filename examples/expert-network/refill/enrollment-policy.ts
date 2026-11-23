import { normalize } from './policy';
// Replace this value with your own dedicated paused campaign before publishing.
export const CAMPAIGN = 'YOUR_PAUSED_CAMPAIGN_ID';
export function raw(result: any): any {
  return result?.toolResponse?.rawV2 ?? result?.toolResponse ?? result;
}
export function roleFit(candidate: any, profile: any) {
  if (profile.needs_verification !== false || profile.company_found !== true) return false;
  if (String(profile.linkedin_url || '').toLowerCase().replace(/\/$/,'') !== candidate.profile) return false;
  return !!normalize({ full_name: profile.full_name, title: profile.title,
    linkedin_url: profile.linkedin_url, company_domain: profile.company_domain,
    country: 'United States' }, candidate.domain, candidate.vertical);
}
export function emailFit(domain: string, found: any) {
  return found.email_validated === true && found.email_validation_status === 'valid'
    && typeof found.email === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(found.email)
    && found.email.split('@')[1].toLowerCase() === domain;
}
export function contacts(result: any): any[] {
  const value = raw(result);
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.data) && typeof value.total === 'number' && value.total <= value.data.length) return value.data;
  throw new Error('CONTACT_LOOKUP_INCOMPLETE_OR_INVALID');
}
export function isCampaignMember(rows:any[], email:string, profile:string) {
  return rows.some(c=>String(c.email||'').toLowerCase()===email.toLowerCase()
    && String(c.linkedinUrl||'').toLowerCase().replace(/\/$/,'')===profile.toLowerCase().replace(/\/$/,'')
    && Array.isArray(c.campaigns) && c.campaigns.some((x:any)=>x.campaignId===CAMPAIGN && typeof x.leadId==='string'));
}
