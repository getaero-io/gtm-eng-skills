import deepline from 'deepline';
/** @mermaid
 * flowchart TD
 *   count[Count recruiting queue] --> gate{Below 100?}
 *   gate -->|yes| qualify[[Qualify and enroll in Lemlist]]
 *   qualify --> refill[[Refill remaining queue capacity]]
 *   gate -->|no| skip[No sourcing or enrollment]
 */
export const config={name:'erm-recruitment-cycle-v1',description:'When the real candidate queue is below 100, qualify up to five candidates, enroll eligible new contacts in paused Lemlist, and refill capacity.',billing:{maxCreditsPerRun:24}};
export default async function(input:{qualificationLimit?:number;refillLimit?:number}) {
  // @mermaid-node count
  const [count]=await deepline.customerDb.query(`SELECT count(*)::int n FROM storage.erm_candidate_queue WHERE status IN ('research_pending','ready','contacted','onboarding') AND NOT suppressed`,{id:'queue-count',staleAfterSeconds:0,maxRows:1});
  // @mermaid-node gate
  if(Number(count.n)>=100) {
    // @mermaid-node skip
    return {status:'skipped',reason:'Queue is at least 100',count:Number(count.n)};
  }
  // @mermaid-node qualify type:"play"
  const qualification=await deepline.runPlay('qualify-and-enroll','erm-qualify-enroll-v1',{limit:input.qualificationLimit??5},{description:'Qualify pending candidates and enroll eligible contacts'});
  // @mermaid-node refill type:"play"
  const refill=await deepline.runPlay('refill-queue','erm-refill-experts-v1',{batchLimit:input.refillLimit??100},{description:'Refill remaining recruiting queue capacity'});
  return {status:'completed',before:Number(count.n),qualification,refill};
}
