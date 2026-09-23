import { definePlay } from 'deepline';
type Row={contact_id:string;name:string;company:string;cached_json?:string};
/** @mermaid
flowchart TD
 people[Known contacts] --> discover[Find public appearances]
 discover --> review[Store candidates for review]
*/
export default definePlay('warm-intro-public-history',async(ctx,input:{csv:string;mode:'cached'|'live'})=>{
 if(!['cached','live'].includes(input.mode))throw new Error('Explicit cached/live mode required');
 // @mermaid-node people type:"dataset"
 const contacts=await ctx.csv<Row>(input.csv,{required:['contact_id','name','company']});
 // @mermaid-node discover type:"dataset"
 const rows=await ctx.dataset('public_history_candidates',contacts).withColumn('evidence',async(row,c)=>{
  if(!row.contact_id||!row.name||!row.company)throw new Error('Contact identity required');
  if(input.mode==='cached'){if(!row.cached_json)throw new Error('Cached evidence missing');return {candidates:JSON.parse(row.cached_json),status:'needs_verification'};}
  const result=await c.tools.execute({id:'public_history',tool:'serper_google_search',input:{query:`"${row.name}" "${row.company}" (podcast OR interview OR panel OR webinar OR speaker)`,gl:'us',hl:'en',page:1,num:10},description:'Find source pages for public history'});
  return {candidates:result.toolResponse.raw,status:'needs_verification'};
 }).run({key:'contact_id',undrawnColumns:['evidence']});
 // @mermaid-node review
 return {rows,count:await rows.count(),interpretation:'Candidate pages do not add points. Verify exact people, event or episode, date, and context.'};
},{description:'Find public appearance evidence'});
