/** Structural audit; source truth and live database constraints are separate. */
import {casefold,compareText} from './core.ts';
import { dateOnly, scoreLegacy } from './legacy.ts';
type R=Record<string,any>;
export async function auditQuality(data:R,maxAgeDays:number,todayISO:string) {
 if(!Number.isInteger(maxAgeDays)||maxAgeDays<0)throw new Error('max_age_days must be a nonnegative integer');
 const errors:R[]=[],warnings:R[]=[],contacts=new Map<string,R>(),urls=new Map<string,string>(),history=new Set<string>(),receipts=new Set<string>();
 const issue=(dest:R[],code:string,record:any=null)=>dest.push({code,record_id:record});
 const coverage:R={unique_contacts:0,contacts_without_job_history:0,contacts_without_company:0,contacts_without_title:0,paths:0,evidence_records:0};
 try {
  const cutoff=dateOnly(data.as_of),paths=data.paths,evidence=data.evidence;if(!Array.isArray(paths)||!Array.isArray(evidence))throw new Error('lists required');Object.assign(coverage,{paths:paths.length,evidence_records:evidence.length});if(!paths.length)issue(errors,'empty_candidate_set');
  for(const p of paths)for(const role of ['connector','target']) {
   const person=p[role],id=person.id;if(typeof id!=='string'||!id.trim())throw new Error('contact ID');
   const raw=person.linkedin_url; if(typeof raw!=='string')throw new Error('profile URL');
   // Preserve Python urlsplit canonical behavior: host case, port, query removal and trailing slash.
   const m=raw.match(/^(?:([A-Za-z][A-Za-z\d+.-]*):)?(?:\/\/([^/?#]*))?([^?#]*)/)!;
   const scheme=(m[1]??'').toLowerCase(),netloc=m[2]??'',path=m[3]??'';
   if(!['http','https'].includes(scheme)||!netloc||netloc.includes('@'))issue(errors,'invalid_profile_url',id);
   const canonical=netloc?'https://'+netloc.toLowerCase()+path.replace(/\/+$/,''):'https:'+path.replace(/\/+$/,'');
   const signature=JSON.stringify([canonical,casefold(person.first_name.trim()),casefold(person.last_name.trim())]);
   if(contacts.has(id)&&contacts.get(id)!.identity!==signature)issue(errors,'contact_identity_conflict',id);
   if(urls.has(canonical)&&urls.get(canonical)!==id)issue(errors,'profile_identity_collision',id);urls.set(canonical,id);
   if(!contacts.has(id))contacts.set(id,{identity:signature,company:false,title:false});const record=contacts.get(id)!;record.company ||=!!('current_company' in person?person.current_company:'').trim();record.title ||=!!('current_position' in person?person.current_position:'').trim();
   for(const e of p[role+'_experiences']??[]) {history.add(id);if(e.end_date&&dateOnly(e.end_date)>cutoff)issue(errors,'future_employment_end',e.id??null);if(e.is_current&&e.end_date)issue(errors,'current_job_has_end_date',e.id??null);}
  }
  for(const e of evidence){const age=(cutoff-dateOnly(e.observed_at))/86400000;if(age>maxAgeDays)issue(warnings,'stale_evidence',e.id);const key=JSON.stringify([e.source,e.kind,[...e.subjects].sort(compareText),e.observed_at]);if(receipts.has(key))issue(warnings,'duplicate_source_receipt',e.id);receipts.add(key);}
  for(const[id,p]of contacts){if(!history.has(id)){coverage.contacts_without_job_history++;issue(warnings,'missing_job_history',id);}for(const field of ['company','title'])if(!p[field]){coverage['contacts_without_'+field]++;issue(warnings,'missing_'+field,id);}}
  coverage.unique_contacts=contacts.size;
  try{await scoreLegacy(data,todayISO);}catch{issue(errors,'scorer_evidence_validation_failed');}
 } catch {issue(errors,'malformed_evidence_contract');}
 return {schema_version:1,status:errors.length?'fail':'pass',errors,warnings,coverage,max_age_days:maxAgeDays,interpretation:'Structural checks only. Missing history is unknown, not a negative relationship. Full-profile source truth and live DB constraints require separate audit.'};
}
