import {requireEvidenceRegistry} from './guardrails';
/** The existing offline report, rendered inside a Play without changing its UI. */
import {validatePayload,compareText} from './core';
import {TEMPLATE} from './generatedtemplate';
function signature(value:any):string {
 if(Array.isArray(value))return '['+value.map(signature).join(',')+']';
 if(value!==null&&typeof value==='object')return '{'+Object.keys(value).sort(compareText).map(k=>JSON.stringify(k)+':'+signature(value[k])).join(',')+'}';
 return JSON.stringify(value);
}
export function reviewPayload(data:any,config:any=null):Record<string,any>{
 requireEvidenceRegistry(data);
 const payload=validatePayload(data,config);
 if(data.coverage!==undefined){if(!data.coverage||!Array.isArray(data.coverage.unresolved))throw Error('Coverage must include unresolved targets');payload.coverage=data.coverage;}
 if(payload.paths.length>5000){
  const catalog:any[]=[],index=new Map<string,number>();
  for(const row of payload.paths)for(const [key,feature] of Object.entries(row.features)){
   const id=signature(feature);let position=index.get(id);
   if(position===undefined){position=catalog.length;catalog.push(feature);index.set(id,position);}
   row.features[key]=position;
  }
  payload.feature_catalog=catalog;
 }
 return payload;
}
export function renderReview(data:any,config:any=null):string{
 const encoded=JSON.stringify(reviewPayload(data,config)).replaceAll('<','\\u003c').replaceAll('>','\\u003e').replaceAll('&','\\u0026');
 let html=TEMPLATE.replace('__TUNING_DATA__',()=>encoded);
 if(data.coverage){
  const esc=(v:any)=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
  const missing=data.coverage.unresolved||[],orphans=data.coverage.review_states_without_paths||[];
  const note=`<section aria-label="Source coverage"><h2>Source coverage</h2><p>${missing.length} unresolved targets. ${orphans.length} prior review states retained without a current path. Export completeness: ${esc(data.coverage.export_completeness||'not verified')}.</p><ul>${missing.map((r:any)=>`<li>${esc(r.target?.name||r.target?.id||'Unknown target')}: ${esc(r.reason)}</li>`).join('')}</ul></section>`;
  html=html.replace('</main>',()=>note+'</main>');
 }
 return html;
}
