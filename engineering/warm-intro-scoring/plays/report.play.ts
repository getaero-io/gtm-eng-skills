import {requireEvidenceRegistry,expandFeatureCatalog} from './guardrails';
import {strictJSON} from './strict-json';
import {definePlay} from 'deepline';
import {renderReview} from './report';
import {renderLegacy,renderEvaluation} from './reports';
import {LEGACY_TEMPLATE} from './generatedtemplate';
/** @mermaid
flowchart TD
  input[Evidence batches] --> report[Render private review]
  subgraph storage[Workspace storage]
    store[Store private HTML]
  end
  report --> store
  store --> files[Artifact receipts]
*/
export default definePlay('warm-intro-review-report',async(ctx,input:{csv:string})=>{
 // @mermaid-node input type:"dataset"
 const batches=await ctx.csv<{case_id:string,payload_json:string,weights_json?:string,artifact_path?:string,report_kind?:string}>(input.csv,{required:['case_id','payload_json']});
 // @mermaid-node report type:"dataset"
 const reports=await ctx.dataset('review_reports',batches).withColumn('artifact',async(row,c)=>{
  const data=strictJSON(row.payload_json);
  expandFeatureCatalog(data);
  const kind=row.report_kind||'tuning';
  if(!['tuning','legacy','evaluation'].includes(kind))throw new Error('Unsupported report_kind');
  if(kind==='tuning')requireEvidenceRegistry(data);
  const html=kind==='legacy'?renderLegacy(data,LEGACY_TEMPLATE):kind==='evaluation'?renderEvaluation(data):renderReview(data,row.weights_json?strictJSON(row.weights_json):undefined);
  const bytes=new TextEncoder().encode(html).length;
  // Bounded cloud pilot; full reports can use this renderer offline or split by account.
  if(bytes>1000000)throw new Error('Cloud report exceeds the 1 MB safety cap. Render with report.ts offline or split by target account.');
  if(!/^[A-Za-z0-9_-]+$/.test(row.case_id))throw new Error('case_id must contain only letters, numbers, underscores or hyphens');
  const path=row.artifact_path||`warm-intro-scoring/reviews/${row.case_id}.html`;
  if(!/^warm-intro-scoring\/reviews\/[A-Za-z0-9_/-]+\.html$/.test(path)||path.includes('..'))throw new Error('Artifact path must be inside warm-intro-scoring/reviews');
  // @mermaid-node store out:"result"
  const result=await c.tools.execute({id:'store_review',tool:'upsert_customer_db_file',input:{path,content:html},description:'Store the private review in the workspace file store'});
  const receipt=result.toolResponse.raw as any;
  if(!receipt?.ok||receipt.path!==path)throw new Error('File store did not confirm the requested artifact');
  return {path,bytes,report_kind:kind,paths:kind==='tuning'?data.paths.length:kind==='legacy'?data.length:null,receipt};
 }).run({key:'case_id',undrawnColumns:['artifact'],description:'Render and retain the private review artifact'});
 // @mermaid-node files
 return {reports,count:await reports.count()};
},{description:'Render warm introduction reviews'});
