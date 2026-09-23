/** The existing offline report, rendered inside a Play without changing its UI. */
import {validatePayload,compareText} from './core';
import {TEMPLATE} from './generatedtemplate';
function signature(value:any):string {
 if(Array.isArray(value))return '['+value.map(signature).join(',')+']';
 if(value!==null&&typeof value==='object')return '{'+Object.keys(value).sort(compareText).map(k=>JSON.stringify(k)+':'+signature(value[k])).join(',')+'}';
 return JSON.stringify(value);
}
export function reviewPayload(data:any,config:any=null):Record<string,any>{
 const payload=validatePayload(data,config);
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
 return TEMPLATE.replace('__TUNING_DATA__',()=>encoded);
}
