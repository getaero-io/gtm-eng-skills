import { definePlay } from 'deepline';
import { validatePayload, DEFAULT_WEIGHTS, MODEL } from './core';
/** @mermaid
flowchart TD
  input[Versioned evidence batches] --> validate[Validate and score]
  validate --> output[Persist scores and parity receipts]
*/
export default definePlay('warm-intro-score', async(ctx,input:{csv:string})=>{
 // @mermaid-node input type:"dataset"
 const batches=await ctx.csv<{case_id:string,payload_json:string,weights_json?:string,expected_json?:string}>(input.csv,{required:['case_id','payload_json']});
 // @mermaid-node validate type:"dataset"
 const rows=await ctx.dataset('scored_batches',batches).withColumn('result',(row)=>{
  const data=JSON.parse(row.payload_json);
  if(data.feature_catalog)for(const p of data.paths)for(const key of Object.keys(p.features))p.features[key]=data.feature_catalog[p.features[key]];
  const config=row.weights_json?JSON.parse(row.weights_json):undefined;
  const payload=validatePayload(data,config);
  const scores=payload.paths.map((p:any)=>({id:p.id,target_id:p.target_id,connector_id:p.connector_id,score:p.tuned_score,review_status:p.review_status,features:Object.fromEntries(Object.keys(DEFAULT_WEIGHTS).map(k=>[k,p.features[k].value*payload.weights[k]]))}));
  const expected=row.expected_json?JSON.parse(row.expected_json):null;
  if(expected){
   const byId=new Map(scores.map((p:any)=>[p.id,p]));
   if(expected.length!==scores.length)throw new Error('Parity failed: path count');
   for(const e of expected){const actual:any=byId.get(e.id);if(!actual||actual.score!==e.score||actual.review_status!==e.review_status||Object.keys(DEFAULT_WEIGHTS).some(k=>actual.features[k]!==e.features[k]))throw new Error('Parity failed: score, contribution, identity, or hold');}
   if(expected.some((e:any,i:number)=>e.id!==scores[i].id))throw new Error('Parity failed: rank order');
  }
  return {model:MODEL,count:scores.length,expected_checked:expected!==null,parity:expected?'pass':'not_checked',scores};
 }).run({key:'case_id',undrawnColumns:['result'],description:'Score evidence and compare frozen outputs'});
 // @mermaid-node output
 return {rows,batches:await rows.count(),model:MODEL};
},{description:'Score warm introduction paths'});
