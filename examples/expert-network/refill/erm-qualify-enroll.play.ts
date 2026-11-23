import deepline from 'deepline';
import {q,j} from './policy';
export const config={name:'erm-qualify-enroll-v1',description:'Qualify up to five queued candidates and enroll eligible new contacts in a paused Lemlist campaign. Persist each state for replay.',billing:{maxCreditsPerRun:12}};
export default async function(input:{limit?:number}) {
  const limit=input.limit??5;
  if(!Number.isInteger(limit)||limit<1||limit>5) throw new Error('LIMIT_1_TO_5');
  const token=deepline.run.id;
  const lease=await deepline.customerDb.query(`UPDATE storage.erm_recruiting_control SET lock_token=${q(token)},lock_until=now()+interval '15 minutes' WHERE id='enrollment' AND (lock_until IS NULL OR lock_until<now()) RETURNING id`,{id:'claim-batch',staleAfterSeconds:0,maxRows:1});
  if(!lease.length) return {status:'busy',results:[]};
  const results:any[]=[];
  try {
    const rows=await deepline.customerDb.query(`SELECT c.* FROM storage.erm_candidate_queue c LEFT JOIN storage.erm_qualification_output q ON q.profile=c.profile LEFT JOIN storage.erm_enrollment_output e ON e.profile=c.profile WHERE c.status IN ('research_pending','ready') AND NOT c.suppressed AND e.profile IS NULL AND (q.profile IS NULL OR q.status='qualified') ORDER BY c.created_at,c.profile LIMIT ${limit}`,{id:'pending-candidates',staleAfterSeconds:0,maxRows:5});
    for(const c of rows) {
      await deepline.customerDb.query(`INSERT INTO storage.erm_qualification_input(profile,payload) VALUES(${q(String(c.profile))},${j(c)}) ON CONFLICT DO NOTHING`,{id:'qualification-input',staleAfterSeconds:0,maxRows:1});
      const [prior]=await deepline.customerDb.query(`SELECT payload FROM storage.erm_qualification_output WHERE profile=${q(String(c.profile))}`,{id:'qualification-replay',staleAfterSeconds:0,maxRows:1});
      let result:any=prior?.payload;
      if(!result) {
        try {
          result=await deepline.runPlay<any>('qualify-candidate','erm-qualify-candidate-v1',{profile:c.profile,domain:c.domain,vertical:c.vertical},{description:'Qualify current role and work email'});
          if(!['qualified','held'].includes(result.status)) throw new Error('INVALID_QUALIFICATION_STATE');
        } catch(error) {result={status:'failed',reason:String(error)};}
        await deepline.customerDb.query(`INSERT INTO storage.erm_qualification_output(profile,status,payload) VALUES(${q(String(c.profile))},${q(result.status)},${j(result)}) ON CONFLICT DO NOTHING`,{id:'qualification-output',staleAfterSeconds:0,maxRows:1});
      }
      if(result.status!=='qualified') {results.push({profile:c.profile,status:result.status,reason:result.reason});continue;}
      const enrollment={profile:c.profile,email:result.email.email,firstName:result.profile.first_name||'',lastName:result.profile.last_name||'',company:result.profile.company_name||String(c.company)};
      await deepline.customerDb.query(`UPDATE storage.erm_candidate_queue SET email=${q(enrollment.email)},email_verified=true,status='ready',evidence=evidence || ${j({qualification:result})} WHERE profile=${q(String(c.profile))} AND status IN ('research_pending','ready') AND NOT suppressed`,{id:'mark-ready',staleAfterSeconds:0,maxRows:1});
      await deepline.customerDb.query(`INSERT INTO storage.erm_enrollment_input(profile,payload) VALUES(${q(String(c.profile))},${j(enrollment)}) ON CONFLICT DO NOTHING`,{id:'enrollment-input',staleAfterSeconds:0,maxRows:1});
      let output:any;
      try {
        output=await deepline.runPlay<any>('enroll-candidate','erm-enroll-candidate-v1',enrollment,{description:'Enroll qualified new contact with suppression and duplicate protection'});
        if(!['confirmed','submitted','already_claimed','held','suppressed'].includes(output.status)) throw new Error('INVALID_ENROLLMENT_STATE');
      } catch(error) {output={status:'failed',reason:String(error)};}
      await deepline.customerDb.query(`INSERT INTO storage.erm_enrollment_output(profile,status,payload) VALUES(${q(String(c.profile))},${q(output.status)},${j(output)}) ON CONFLICT DO NOTHING`,{id:'enrollment-output',staleAfterSeconds:0,maxRows:1});
      if(output.status==='suppressed') await deepline.customerDb.query(`UPDATE storage.erm_candidate_queue SET suppressed=true WHERE profile=${q(String(c.profile))}`,{id:'save-suppression',staleAfterSeconds:0,maxRows:1});
      results.push({profile:c.profile,...output});
    }
    return {status:'completed',results};
  } finally {
    await deepline.customerDb.query(`UPDATE storage.erm_recruiting_control SET lock_token=NULL,lock_until=NULL WHERE id='enrollment' AND lock_token=${q(token)}`,{id:'release-batch',staleAfterSeconds:0,maxRows:1});
  }
}
