import {definePlay} from 'deepline';
import {buildFeatures, type FeatureInput} from './features';
import {validatePayload,DEFAULT_WEIGHTS,MODEL} from './core';
/** @mermaid
flowchart TD
  input[Retained source records] --> targets[Resolve target contacts]
  targets --> extract[Extract evidence and score each target]
  subgraph computation[Feature extraction]
    result[Extract features and compare independent hashes]
  end
  extract --> result
  result --> output[Persist parity receipts and scores]
*/
/** CSV columns: section,key,payload_json. Sections use FeatureInput field names.
 * Scalar fields live in one config record; array fields use one item per row.
 * targets rows may carry expected_feature_sha256 and expected_score_sha256 in payload.
 * Input is intentionally bounded to 5,000 source records. Use separate runs above this bound.
 * include_payload=true returns full scored evidence for one target per run.
 * This play does not fetch profiles, claim personal relationships, or send introductions.
 */
export default definePlay('warm-intro-features',async(ctx,input:{csv:string,include_payload?:boolean})=>{
 // @mermaid-node input type:"dataset"
 const source=await ctx.csv<{section:string,key:string,payload_json:string}>(input.csv,{required:['section','key','payload_json']});
 if(await source.count()>5000)throw new Error('Source record limit exceeded; partition the run');
 const records=await source.materialize(5000);
 const config=records.filter(r=>r.section==='config');
 if(config.length!==1)throw new Error('Exactly one config record is required');
 const shared:FeatureInput={...JSON.parse(config[0].payload_json),targets:[],connectors:[],profiles:[]};
 const sections=new Set(['connectors','profiles','company_sizes','funding_edges','verified_firms','owner_portfolio']);
 for(const section of sections)(shared as any)[section]=records.filter(r=>r.section===section).map(r=>JSON.parse(r.payload_json));
 if(records.some(r=>!sections.has(r.section)&&!['config','targets'].includes(r.section)))throw new Error('Unknown source record section');
 const targetRecords=records.filter(r=>r.section==='targets');
 if(input.include_payload&&targetRecords.length!==1)throw new Error('include_payload requires one target per run; use --targets-per-file 1');
 // @mermaid-node targets type:"dataset"
 const targets=await ctx.dataset('target_inputs',targetRecords).run({key:'key'});
 const hash=async(value:unknown)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))).map(x=>x.toString(16).padStart(2,'0')).join('');
 // @mermaid-node extract type:"dataset"
 const rows=await ctx.dataset('feature_results',targets)
 // @mermaid-node result out:"result"
 .withColumn('result',async row=>{
  const item=JSON.parse(row.payload_json),data=buildFeatures({...shared,targets:[item.target||item]});
  const featureVector=data.paths.slice().sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0).map(p=>[p.id,p.baseline_score,p.review_status,Object.keys(DEFAULT_WEIGHTS).sort().map(k=>{const f=p.features[k],c=f.work_context;return[k,f.value,f.timing_status,f.overlap_start||null,f.overlap_end||null,[...f.evidence_ids].sort(),c?[c.company_size,c.same_function,c.same_location]:null];})]);
  const featuresSha256=await hash(featureVector);
  const payload=data.paths.length?validatePayload(data):null;
  const scores=(payload?.paths||[]).map((p:any)=>({id:p.id,score:p.tuned_score,review_status:p.review_status,contributions:Object.keys(DEFAULT_WEIGHTS).sort().map(k=>[k,p.features[k].value*payload!.weights[k]])}));
  const scoresSha256=await hash(scores);
  if(item.expected_feature_sha256&&item.expected_feature_sha256!==featuresSha256)throw new Error('Raw feature parity failed for '+row.key);
  if(item.expected_score_sha256&&item.expected_score_sha256!==scoresSha256)throw new Error('Score or rank parity failed for '+row.key);
  return{model:MODEL,coverage:data.coverage,feature_sha256:featuresSha256,score_sha256:scoresSha256,feature_parity:item.expected_feature_sha256?'pass':'not_checked',score_parity:item.expected_score_sha256?'pass':'not_checked',scores:scores.map((p:any)=>({id:p.id,score:p.score,review_status:p.review_status})),...(input.include_payload?{payload:payload||{...data,weights:DEFAULT_WEIGHTS,defaults:DEFAULT_WEIGHTS,model:MODEL}}:{})};
 }).run({key:'key',description:'Extract raw profile evidence and validate frozen parity'});
 // @mermaid-node output in:"rows" out:"receipt"
 const receipt={rows,targets:await rows.count(),model:MODEL};
 return receipt;
},{description:'Extract warm introduction evidence from retained sources'});
