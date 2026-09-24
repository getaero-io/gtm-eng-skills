/* eslint-disable @typescript-eslint/no-explicit-any -- Ported JSON contract/parity boundary; runtime validators reject malformed values. */
/** Reviewed-evidence wrapper parity with scripts/score.py and its pinned pair scorer.
 * This does not expose legacy SQL lookup or unreviewed contact-search scoring.
 */
import {casefold, compareText, exactDate} from './core.ts';
type R = Record<string, any>;
const get=(o:R,k:string,d:any)=>k in o?o[k]:d;
const fail=(s:string):never=>{throw new Error(s)};
export function dateOnly(s:any):number { exactDate(s,'date'); if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(s)) fail('ISO date required'); const n=Date.parse(s+'T00:00:00Z'); if(!Number.isFinite(n)||new Date(n).toISOString().slice(0,10)!==s) fail('invalid date'); return n; }
const cmp=compareText;
const legal = new Set('ag bv co company corp corporation gmbh inc incorporated limited llc ltd nv plc pte pty sa srl'.split(' '));
const suffix = new Set([...legal,'com','io','ai','net','org']);
function words(s:string) { return (s||'').normalize('NFKD').replace(/[^\x00-\x7f]/g,'').toLowerCase().replace(/[^\w\s]/g,' ').trim().split(/\s+/).filter(Boolean); }
function norm(s:string,identity=false) { const w=words(s); while(w.length) { if((identity?legal:suffix).has(w[w.length-1])) {w.pop();continue;} if(identity && ['i n c','l l c','l t d'].includes(w.slice(-3).join(' '))) {w.splice(-3);continue;} break;}return w.join(' '); }
function companiesMatch(a:string,b:string) { const x=norm(a),y=norm(b); if(!x||!y)return false; const xs=new Set(x.split(' ')),ys=new Set(y.split(' '));return [...xs].every(t=>ys.has(t))||[...ys].every(t=>xs.has(t)); }
async function pathId(parts:any[]) { const normalized=parts.map(v=>{const s=String(v||'').trim();if(!s)fail('stable identity required');return s;}); const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(['warm-path-v1',...normalized]))); return 'path-'+[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,16); }
export const LEGACY_FIELDS='model_version baseline_segment target_relationship_confidence connector_willingness review_status campaign_id owner_id connector_id target_id path_id connector_name connector_linkedin connector_company target_name target_title target_company shared_signal shared_detail relationship_confidence direct_intro_score work_overlap_score relationship_score school_city_community_score role_industry_score investor_score total_score segment reviewed_override evidence_ids'.split(' ');
export async function scoreLegacy(data:R,todayISO:string):Promise<R[]> {
 const asOf=dateOnly(data.as_of); if(asOf>dateOnly(todayISO)) fail('as_of must not be in the future'); const registry=new Map<string,R>();
 for(const e of data.evidence) {if(!e.id||registry.has(e.id)||!e.detail||!e.source)fail('Evidence requires unique ID, detail and source');if(dateOnly(e.observed_at)>asOf)fail('future evidence');registry.set(e.id,e);}
 const cited=(ids:any[],subjects:string[],kind:string)=>{if(!ids.length)fail('evidence IDs required');for(const id of ids){const e=registry.get(id);if(!e||e.kind!==kind||!subjects.every(s=>(e.subjects??[]).includes(s)))fail('evidence kind or subjects mismatch');}};
 const person=(p:R)=>{for(const k of ['id','first_name','last_name','linkedin_url'])if(typeof p[k]!=='string'||!p[k].trim())fail('contact identity required');const allowed='id first_name last_name linkedin_url email current_company current_position headline location connected_on enriched_at'.split(' ');if(Object.keys(p).some(k=>!allowed.includes(k)))fail('unknown contact field');return p;};
 const history=(items:R[],contact:R):R[]=>items.map(r=>{cited([r.id],[contact.id],'employment');if(r.contact_id!==contact.id)fail('employment owner mismatch');const start=r.start_date?dateOnly(r.start_date):null,end=r.end_date?dateOnly(r.end_date):null;if(start!==null&&(start>asOf||(end!==null&&end<start)))fail('invalid employment interval');if('is_current'in r&&typeof r.is_current!=='boolean')fail('is_current boolean required');if(!('company_name'in r))fail('company required');const allowed='id contact_id company_name company_linkedin_url title description location start_date end_date is_current'.split(' ');if(Object.keys(r).some(k=>!allowed.includes(k)))fail('unknown experience field');return {...r,start,end};});
 const rows:R[]=[],seen=new Set();
 for(const p of data.paths) {
  const c=person(p.connector),t=person(p.target),owner=data.owner_id;if(new Set([owner,c.id,t.id]).size!==3)fail('distinct identities required');
  const conf=get(p,'relationship_confidence','unknown'),tc=get(p,'target_relationship_confidence','unknown'),rel=get(p,'relationship_evidence_ids',[]),tr=get(p,'target_relationship_evidence_ids',[]);
  for(const [v,ids,subjects]of [[conf,rel,[owner,c.id]],[tc,tr,[c.id,t.id]]] as any[]) {if(!['unknown','low','medium','high','confirmed'].includes(v))fail('unknown confidence');if(v!=='unknown'||ids.length){cited(ids,subjects,'relationship');if(v!=='unknown'&&ids.some((id:string)=>registry.get(id)!.confidence!==v))fail('confidence evidence mismatch');}}
  let willingness=get(p,'connector_willingness','unknown'),wi=get(p,'willingness_evidence_ids',[]);if(!['unknown','yes','no'].includes(willingness))fail('unknown willingness');if(willingness!=='unknown'||wi.length)cited(wi,[owner,c.id,t.id],'willingness');
  const rw=[...registry.values()].filter(e=>e.kind==='willingness'&&[owner,c.id,t.id].every(s=>(e.subjects??[]).includes(s)));
  if(rw.some(e=>!['yes','no'].includes(e.value)))fail('explicit willingness required');if(wi.some((id:string)=>registry.get(id)!.value!==willingness))fail('willingness contradiction');
  if(rw.length){const latest=rw.map(e=>e.observed_at).sort().at(-1);const current=rw.filter(e=>e.observed_at===latest);if(current.some(e=>e.value==='no')){willingness='no';wi=[...new Set([...wi,...current.filter(e=>e.value==='no').map(e=>e.id)])].sort(compareText);}}
  const direct=get(p,'direct_intro_evidence_ids',[]);if(direct.length)cited(direct,[c.id,t.id],'direct_intro');
  const sig:R={school:[],city:[],community:[],appearance:[],role_industry:[],investor:[]},allIds=[...tr,...wi];
  for(const f of get(p,'signals',[])) {if(!(f.kind in sig)||typeof f.value!=='string'||!f.value.trim())fail('unsupported signal');cited(f.evidence_ids,[c.id,t.id],f.kind);sig[f.kind].push(f.value);allIds.push(...f.evidence_ids);}
  const overlaps:R[]=[],proximity=new Set<string>();
  const ch=history(get(p,'connector_experiences',[]),c),th=history(get(p,'target_experiences',[]),t);
  for(const cr of ch)for(const tt of th){if(!companiesMatch(cr.company_name,tt.company_name))continue;proximity.add(cr.company_name);if(norm(cr.company_name,true)!==norm(tt.company_name,true)||cr.start===null||tt.start===null)continue;const ce=cr.end??(cr.is_current?asOf:null),te=tt.end??(tt.is_current?asOf:null);if(ce===null||te===null)continue;const start=Math.max(cr.start,tt.start),end=Math.min(ce,te,asOf);if(start<=end)overlaps.push({cr,tt,start,end});}
  const community=[...new Set<string>([...sig.school,...sig.city,...sig.community,...sig.appearance])];
  const ds=direct.length?160:0,ws=overlaps.length?80:0,rs=({low:5,medium:10,high:15,confirmed:15}as R)[conf]??0,ss=community.length?40:0,is=sig.role_industry.length?20:0,investor=Math.min(new Set(sig.investor).size,3);
  let signal='',detail='';
  if(ds){signal='direct_introduction';detail='Recorded introduction between connector and target; inspect the cited record before a new ask.';}
  else if(overlaps.length){const x=[...overlaps].sort((a,b)=>a.start-b.start||a.end-b.end||cmp(norm(a.cr.company_name),norm(b.cr.company_name)))[0];signal='verified_work_overlap';detail=`${x.cr.company_name}, ${new Date(x.start).toISOString().slice(0,10)} to ${new Date(x.end).toISOString().slice(0,10)}`;}
  else if(proximity.size){signal='company_proximity';detail=`${[...proximity].sort((a,b)=>cmp(casefold(a),casefold(b)))[0]}; employment dates unavailable or non-overlapping`;}
  else if(community.length){signal='school_city_community';detail=community.join('; ');}
  else if(sig.role_industry.length){signal='role_industry';detail=sig.role_industry.join('; ');}
  else if(sig.investor.length){signal='investor_overlap';detail=sig.investor.join('; ');}
  let segment=(ds||ws)&&rs?'strong_warm_intro':signal&&signal!=='investor_overlap'?'review_warm_intro':'no_strong_path'; const baseline=segment;let review='needs_confirmation';
  if(willingness==='no'){segment='no_strong_path';review='blocked_declined';}else if(segment==='strong_warm_intro'){if(['medium','high','confirmed'].includes(tc)&&['medium','high','confirmed'].includes(conf)&&willingness==='yes')review='ready_for_human_review';else segment='review_warm_intro';}
  const id=data.campaign_id&&owner?await pathId([data.campaign_id,owner,c.id,t.id]):'';if(seen.has(id))fail('duplicate path');seen.add(id);
  const ids=[...new Set([...allIds,...direct,...rel,...overlaps.flatMap(x=>[x.cr.id,x.tt.id])])].sort(compareText);
  rows.push({model_version:'office-hours-160-80-v1+two-edge-review-v1',baseline_segment:baseline,target_relationship_confidence:tc,connector_willingness:willingness,review_status:review,campaign_id:data.campaign_id,owner_id:owner,connector_id:c.id,target_id:t.id,path_id:id,connector_name:`${c.first_name} ${c.last_name}`,connector_linkedin:c.linkedin_url,connector_company:c.current_company||'',target_name:`${t.first_name} ${t.last_name}`,target_title:t.current_position||'',target_company:t.current_company||'',shared_signal:signal,shared_detail:detail,relationship_confidence:conf,direct_intro_score:ds,work_overlap_score:ws,relationship_score:rs,school_city_community_score:ss,role_industry_score:is,investor_score:investor,total_score:ds+ws+rs+ss+is+investor,segment,reviewed_override:'false',evidence_ids:ids.join(';')});
 }
 return rows.sort((a,b)=>b.total_score-a.total_score||cmp(casefold(a.connector_name),casefold(b.connector_name))||cmp(a.path_id,b.path_id));
}
