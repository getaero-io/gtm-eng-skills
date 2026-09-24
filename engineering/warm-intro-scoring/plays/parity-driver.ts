/* eslint-disable @typescript-eslint/no-explicit-any -- Ported JSON contract/parity boundary; runtime validators reject malformed values. */
/** JSON-lines bridge for independent Python differential checks. */
import {normalize,rank,weights,temporalOverlap,expandPortfolio,validatePayload} from './core';
const input=await Bun.stdin.text();
for(const line of input.trim().split('\n')){
 try{const q=JSON.parse(line);let value:any;
  switch(q.op){case 'normalize':value=normalize(q.data);break;case 'rank':value=rank(q.data,q.config);break;case 'weights':value=weights(q.config);break;case 'temporal':value=temporalOverlap(q.left,q.right,q.as_of);break;case 'portfolio':value=expandPortfolio(q.graph,q.company,q.today);break;case 'payload':value=validatePayload(q.data,q.config);break;default:throw new Error('Unknown operation');}
  console.log(JSON.stringify({ok:true,value}));
 }catch(error){console.log(JSON.stringify({ok:false,error:error instanceof Error?error.message:String(error)}));}
}
