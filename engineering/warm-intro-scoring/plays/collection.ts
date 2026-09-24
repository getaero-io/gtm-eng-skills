import {exactDate} from './core';
import {canonicalLinkedIn,type Snapshot} from './features';
/** Preserve the retained receipt date; reading cached data never refreshes it. */
export function normalizeCollectedProfile(profile:any,contactId:string,url:string,source:string,requestedDate:string,retainedDate?:string,accountDomain?:string):Snapshot {
 const key=canonicalLinkedIn(url);if(!key||canonicalLinkedIn(String(profile.linkedinUrl||profile.linkedin_url||''))!==key)throw Error('Profile identity mismatch');
 const dates=[retainedDate,profile.observed_at,profile.scrapedAt].filter(v=>v!==undefined&&v!==null&&v!=='');
 if(!dates.length)throw Error('Cached profile requires its original observation date');
 const observed=dates.map(v=>{if(typeof v!=='string')throw Error('Invalid original observation date');const day=v.slice(0,10);exactDate(day,'profile observation');return day;}).sort()[0];
 if(observed>requestedDate)throw Error('Profile observation is after collection cutoff');
 for(const field of ['experience','education'])if(profile[field]!==undefined&&(!Array.isArray(profile[field])||profile[field].some((v:any)=>!v||typeof v!=='object'||Array.isArray(v))))throw Error('Invalid profile history shape');
 if(accountDomain!==undefined&&!/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(accountDomain))throw Error('Invalid reviewed account domain');
 const experience=profile.experience||[],education=profile.education||[];
 const current=experience.find((j:any)=>String(j.endDate?.text||'').toLowerCase()==='present');
 return {id:contactId,linkedin_url:url,first_name:String(profile.firstName||profile.first_name||''),last_name:String(profile.lastName||profile.last_name||''),source,observed_at:observed,company:current?.companyName||'',title:current?.position||'',experience,education,...(accountDomain?{domain:accountDomain.toLowerCase()}: {})};
}
