import {normalizeCollectedProfile} from './collection';
import {strictJSON} from './strict-json';
import { definePlay } from 'deepline';
import { exactDate } from './core';
import { canonicalLinkedIn } from './features';
type Row={contact_id:string;linkedin_url:string;profile_json?:string;posts_json?:string;profile_observed_at?:string;account_domain?:string};
function records(result:any):any[]{
 const raw=result?.toolResponse?.rawV2??result?.toolResponse?.raw;
 if(Array.isArray(raw))return raw;
 if(raw?.state==='awaiting_apify')throw new Error('Provider still running; retain run receipt and recover before accepting data');
 throw new Error('Provider returned an unrecognized record envelope');
}
function profile(rows:any[],url:string){const key=canonicalLinkedIn(url);const matches=rows.filter(p=>canonicalLinkedIn(String(p.linkedinUrl||p.linkedin_url||''))===key);if(matches.length!==1)throw new Error('Profile identity missing or ambiguous');return matches[0];}
/** @mermaid
flowchart TD
 contacts[Contact list] --> profiles[Collect profiles and posts]
 profiles --> saved[Save source records]
*/
export default definePlay('warm-intro-collect',async(ctx,input:{csv:string;mode:'cached'|'live';observed_at:string;max_posts?:number})=>{
 if(!['cached','live'].includes(input.mode)||!/^\d{4}-\d{2}-\d{2}$/.test(input.observed_at))throw new Error('Explicit collection mode and observation date required');
 exactDate(input.observed_at,'observed_at');
 const maxPosts=input.max_posts??50;if(!Number.isInteger(maxPosts)||maxPosts<1||maxPosts>100)throw new Error('max_posts must be 1..100');
 // @mermaid-node contacts type:"dataset"
 const contacts=await ctx.csv<Row>(input.csv,{required:['contact_id','linkedin_url']});
 // @mermaid-node profiles type:"dataset"
 const rows=await ctx.dataset('contact_sources',contacts).withColumn('sources',async(row,c)=>{
  if(!row.contact_id||!canonicalLinkedIn(row.linkedin_url))throw new Error('Stable contact ID and valid LinkedIn URL required');
  if(input.mode==='cached'){
   if(!row.profile_json)throw new Error('Cached profile receipt missing');
   const p=strictJSON(row.profile_json);const posts=row.posts_json?strictJSON(row.posts_json):[];
   if(!Array.isArray(posts))throw new Error('Posts must be an array');
   const selected=profile(Array.isArray(p)?p:[p],row.linkedin_url);const normalized=normalizeCollectedProfile(selected,row.contact_id,row.linkedin_url,'retained:'+row.contact_id,input.observed_at,row.profile_observed_at,row.account_domain);
   return {profile:selected,normalized_profile:normalized,posts,observed_at:normalized.observed_at,source:'retained_receipts',posts_status:row.posts_json?'retained':'not_collected'};
  }
  const [p,posts]=await Promise.all([
   c.tools.execute({id:'full_profile',tool:'apify_run_actor_sync',input:{actorId:'harvestapi/linkedin-profile-scraper',input:{profileScraperMode:'Profile details no email ($4 per 1k)',urls:[row.linkedin_url]},timeoutMs:90000},description:'Collect full public profile'}),
   c.tools.execute({id:'public_posts',tool:'apify_run_actor_sync',input:{actorId:'harvestapi/linkedin-profile-posts',input:{targetUrls:[row.linkedin_url],maxPosts,includeReposts:false},timeoutMs:90000},description:'Collect public post evidence'})
  ]);
  const selected=profile(records(p),row.linkedin_url);const normalized=normalizeCollectedProfile(selected,row.contact_id,row.linkedin_url,'apify:'+row.contact_id,input.observed_at,input.observed_at,row.account_domain);
  return {profile:selected,normalized_profile:normalized,posts:records(posts),observed_at:normalized.observed_at,source:'apify',posts_status:'collected'};
 }).run({key:'contact_id',undrawnColumns:['sources'],description:'Store profiles and posts with source dates'});
 // @mermaid-node saved
 return {rows,count:await rows.count(),mode:input.mode,interpretation:'Collection is not relationship confirmation. Missing or ambiguous identities fail the row.'};
},{description:'Collect profile and post evidence'});
