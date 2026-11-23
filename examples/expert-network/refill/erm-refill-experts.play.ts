import deepline from 'deepline';
import { DOMAINS, q, j, slots } from './policy';
/** @mermaid
 * flowchart TD
 *   lock[Claim refill lease] --> count[Count active real candidates]
 *   count --> search[[Find more experts when below 100]]
 *   search --> persist[Deduplicate and queue up to 100]
 *   persist --> result[Show candidates and outreach readiness]
 */
export const config = { name:'erm-refill-experts-v1', description:'Keep a real candidate queue at 100. Search US lawyers and management consultants; deduplicate by profile. Outreach waits for a configured real program.', billing:{maxCreditsPerRun:12} };
export default async function (input: { batchLimit?: number }) {
  const batchLimit=input.batchLimit ?? 100;
  if(!Number.isInteger(batchLimit)||batchLimit<1||batchLimit>100) throw new Error('BATCH_LIMIT_1_TO_100');
  const token=deepline.run.id;
  // @mermaid-node lock in:"token" out:"lease"
  const lease=await deepline.customerDb.query(`UPDATE storage.erm_recruiting_control SET lock_token=${q(token)},lock_until=now()+interval '15 minutes' WHERE id='main' AND search_enabled AND (lock_until IS NULL OR lock_until<now() OR lock_token=${q(token)}) RETURNING id`,{id:'claim-refill',staleAfterSeconds:0,maxRows:1});
  if(!lease.length) return {status:'skipped',reason:'Disabled or another refill holds the lease',candidates:[]};
  let inserted=0,returned=0,rejected=0;
  try {
    // @mermaid-node count in:"lease" out:"before"
    const [before]=await deepline.customerDb.query(`SELECT count(*)::int n FROM storage.erm_candidate_queue WHERE status IN ('research_pending','ready','contacted','onboarding') AND NOT suppressed`,{id:'count-active',staleAfterSeconds:0,maxRows:1});
    const initial=Number(before.n);
    for(const scope of DOMAINS) {
      const [current]=await deepline.customerDb.query(`SELECT count(*)::int n FROM storage.erm_candidate_queue WHERE status IN ('research_pending','ready','contacted','onboarding') AND NOT suppressed`,{id:'recheck-active',staleAfterSeconds:0,maxRows:1});
      const limit=Math.min(batchLimit<=6?3:25,slots(Number(current.n)),batchLimit-inserted);
      if(limit<=0) break;
      const prior=await deepline.customerDb.query(`SELECT name FROM storage.erm_candidate_queue WHERE domain=${q(scope.domain)} ORDER BY created_at LIMIT 100`,{id:'exclude-known',staleAfterSeconds:0,maxRows:100});
      // @mermaid-node search type:"play" in:"scope,limit,prior" out:"found"
      const found=await deepline.runPlay<{candidates:Record<string,any>[];returned:number;rejected:number}>('find-experts','erm-source-experts-v1',{domain:scope.domain,limit,excludedNames:prior.map(p=>String(p.name))},{description:'Source more experts only while queue is below 100'});
      returned+=found.returned;rejected+=found.rejected;
      for(const c of found.candidates) {
        // @mermaid-node persist in:"c" out:"added"
        const added=await deepline.customerDb.query(`INSERT INTO storage.erm_candidate_queue(profile,name,title,domain,vertical,company,location,source,evidence,status,source_run) SELECT ${q(c.profile)},${q(c.name)},${q(c.title)},${q(c.domain)},${q(c.vertical)},${q(c.company)},${q(c.location)},'search_contact',${j(c)},'research_pending',${q(token)} WHERE EXISTS(SELECT 1 FROM storage.erm_recruiting_control WHERE id='main' AND lock_token=${q(token)} AND lock_until>now()) AND (SELECT count(*) FROM storage.erm_candidate_queue WHERE status IN ('research_pending','ready','contacted','onboarding') AND NOT suppressed)<100 ON CONFLICT(profile) DO NOTHING RETURNING profile`,{id:'queue-candidate',staleAfterSeconds:0,maxRows:1});
        inserted+=added.length;
      }
    }
    const candidates=await deepline.customerDb.query(`SELECT name,title,company,vertical,profile,status FROM storage.erm_candidate_queue WHERE NOT suppressed AND status IN ('research_pending','ready','contacted','onboarding') ORDER BY created_at LIMIT 100`,{id:'show-queue',staleAfterSeconds:0,maxRows:100});
    await deepline.customerDb.query(`INSERT INTO storage.erm_refill_runs(id,before_count,after_count,inserted_count,returned_count,rejected_count) VALUES(${q(token)},${initial},${candidates.length},${inserted},${returned},${rejected}) ON CONFLICT DO NOTHING`,{id:'record-refill',staleAfterSeconds:0,maxRows:1});
    // @mermaid-node result in:"candidates" out:"$output" show:"before,after,inserted,outreachStatus,candidates"
    return {status:'completed',target:100,before:initial,after:candidates.length,inserted,returned,rejected,outreachStatus:'blocked_pending_real_sender_and_opportunity',sent:0,candidates};
  } finally {
    await deepline.customerDb.query(`UPDATE storage.erm_recruiting_control SET lock_token=NULL,lock_until=NULL WHERE id='main' AND lock_token=${q(token)}`,{id:'release-refill',staleAfterSeconds:0,maxRows:1});
  }
}
