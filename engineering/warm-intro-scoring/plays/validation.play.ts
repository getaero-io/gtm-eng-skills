/* eslint-disable @typescript-eslint/no-explicit-any -- Ported JSON contract/parity boundary; runtime validators reject malformed values. */
import { definePlay } from 'deepline';
import { evaluate } from './evaluation';
import { scoreLegacy } from './legacy';
import { auditQuality } from './quality';
import { temporalOverlap, expandPortfolio } from './core';
import { strictJSON } from './strict-json';
function compare(actual:any,expected:any,path='result'):string|null {
 if(typeof actual==='number'&&typeof expected==='number')return Number.isFinite(actual)&&Number.isFinite(expected)&&Math.abs(actual-expected)<=1e-12?null:`${path}: numeric mismatch`;
 if(actual===expected)return null;
 if(!actual||!expected||typeof actual!=='object'||typeof expected!=='object'||Array.isArray(actual)!==Array.isArray(expected))return `${path}: value mismatch`;
 const a=Object.keys(actual).sort(),b=Object.keys(expected).sort();if(JSON.stringify(a)!==JSON.stringify(b))return `${path}: keys mismatch`;
 for(const k of a){const difference=compare(actual[k],expected[k],`${path}.${k}`);if(difference)return difference;}return null;
}
/** @mermaid
flowchart TD
 input[Versioned validation cases] --> validate[Run pure operations]
 validate --> output[Persist results and parity receipts]
*/
export default definePlay('warm-intro-validation',async(ctx,input:{csv:string})=>{
 // @mermaid-node input type:"dataset"
 const cases=await ctx.csv<{case_id:string,operation:string,payload_json:string,expected_json?:string,expected_error?:string,today:string,max_age_days?:string}>(input.csv,{required:['case_id','operation','payload_json','today']});
 // @mermaid-node validate type:"dataset"
 const results=await ctx.dataset('validation_cases',cases).withColumn('result',async(row)=>{
  const expectedError=row.expected_error==='true';
  if(row.expected_error&& !['true','false'].includes(row.expected_error))throw new Error('expected_error must be true or false');
  if(!['evaluate','quality','legacy','temporal','portfolio'].includes(row.operation))throw new Error('Unknown operation');
  const expected=row.expected_json?strictJSON(row.expected_json):undefined;let output:any;
  try {
   const payload=strictJSON(row.payload_json);
   switch(row.operation){case 'evaluate':output=evaluate(payload);break;case 'quality':output=await auditQuality(payload,row.max_age_days?Number(row.max_age_days):180,row.today);break;case 'legacy':output=await scoreLegacy(payload,row.today);break;case 'temporal':output=temporalOverlap(payload.left,payload.right,payload.as_of);break;case 'portfolio':output=expandPortfolio(payload.graph,payload.company_id,row.today);break;}
  }catch(error){
   // Only explicit contract/parser rejections count; runtime TypeErrors remain failures.
   const validation=error instanceof Error&&['Error','SyntaxError'].includes(error.name);
   return {operation:row.operation,parity:expectedError&&validation?'pass':'fail',expected_error:expectedError,observed_error:true,error_type:error instanceof Error?error.name:'unknown',error:error instanceof Error?error.message:String(error),output:null};
  }
  const mismatch=expected===undefined?null:compare(output,expected);
  return {operation:row.operation,parity:expectedError||mismatch?'fail':expected===undefined?'not_checked':'pass',expected_error:expectedError,observed_error:false,mismatch:expectedError?'Expected validation rejection did not occur':mismatch,output};
 }).run({key:'case_id',undrawnColumns:['result'],description:'Check evaluator, audit and scorer parity'});
 // @mermaid-node output
 return {results,cases:await results.count(),numeric_tolerance:1e-12,automatic_promotion:false};
},{description:'Validate warm introduction scoring'});
