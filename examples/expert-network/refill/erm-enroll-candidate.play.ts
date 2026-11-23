import deepline from 'deepline';
import { CAMPAIGN, raw, contacts, isCampaignMember } from './enrollment-policy';
import { q, j } from './policy';
export const config = {name:'erm-enroll-candidate-v1',description:'Enroll a qualified candidate in the dedicated paused Lemlist campaign, with suppression checks and a durable one-attempt outbox.',billing:{maxCreditsPerRun:2}};
export default async function(input:{profile:string;email:string;firstName:string;lastName:string;company:string}) {
  const [candidate]=await deepline.customerDb.query(`SELECT profile FROM storage.erm_candidate_queue WHERE profile=${q(input.profile)} AND email=${q(input.email)} AND email_verified AND status='ready' AND NOT suppressed`,{id:'verify-ready',staleAfterSeconds:0,maxRows:1});
  if(!candidate) return {status:'held',reason:'Candidate is not ready or is suppressed'};
  const campaign=raw(await deepline.tools.execute({id:'campaign-check',tool:'lemlist_get_campaign',input:{campaign_id:CAMPAIGN},staleAfterSeconds:0,description:'Require the dedicated campaign to be paused or draft'}));
  if(campaign?._id!==CAMPAIGN || !['paused','draft'].includes(campaign.status)) throw new Error('CAMPAIGN_MUST_BE_PAUSED_OR_DRAFT');
  const blockedValues=new Set([input.email.toLowerCase(),input.email.split('@')[1].toLowerCase(),input.profile.toLowerCase().replace(/\/$/,'')]);
  let complete=false;
  for(let offset=0;offset<10000;offset+=100) {
    // The API clamps page size to 100. Only a short page proves completion.
    const page=raw(await deepline.tools.execute({id:'suppression-page',tool:'lemlist_list_unsubscribed_variables',input:{limit:100,offset},staleAfterSeconds:0,description:'Read complete current suppression pages before enrollment'}));
    if(!Array.isArray(page)) throw new Error('SUPPRESSION_PAGE_INVALID');
    if(page.some((entry:any)=>typeof entry.value!=='string')) throw new Error('SUPPRESSION_VALUE_INVALID');
    if(page.some((entry:any)=>blockedValues.has(entry.value.toLowerCase().replace(/^@/,'').replace(/\/$/,'')))) return {status:'suppressed',reason:'Lemlist variable suppression'};
    if(page.length<100) {complete=true;break;}
  }
  if(!complete) throw new Error('SUPPRESSION_SCAN_INCOMPLETE');
  const existing=contacts(await deepline.tools.execute({id:'existing-contact',tool:'lemlist_get_contacts',input:{email:input.email,limit:100},staleAfterSeconds:0,description:'Hold existing contacts for contact-level suppression and campaign review'}));
  if(existing.length) return {status:'held',reason:'Existing Lemlist contact requires campaign and contact-level suppression review'};
  const claim=await deepline.customerDb.query(`INSERT INTO storage.erm_enrollment_outbox(campaign_id,profile,email,status,request) VALUES(${q(CAMPAIGN)},${q(input.profile)},${q(input.email.toLowerCase())},'submitting',${j(input)}) ON CONFLICT DO NOTHING RETURNING profile`,{id:'claim-enrollment',staleAfterSeconds:0,maxRows:1});
  if(!claim.length) return {status:'already_claimed',reason:'Existing outbox entry; reconcile instead of duplicate enrollment'};
  try {
    const receipt=raw(await deepline.tools.execute({id:'enroll-once',tool:'lemlist_add_to_campaign',input:{campaign_id:CAMPAIGN,contacts:[{email:input.email,linkedin_url:input.profile,firstName:input.firstName,lastName:input.lastName,companyName:input.company,custom_fields:{ermProfile:input.profile,ermQualification:'role_and_verified_email'}}]},staleAfterSeconds:0,description:'Submit one qualified new contact to the paused campaign'}));
    // Provider acknowledgment is not proof of a message sent or even enrollment: preserve it for readback.
    await deepline.customerDb.query(`UPDATE storage.erm_enrollment_outbox SET status='submitted',receipt=${j(receipt)},updated_at=now() WHERE campaign_id=${q(CAMPAIGN)} AND profile=${q(input.profile)}`,{id:'record-submission',staleAfterSeconds:0,maxRows:1});
    const readback=contacts(await deepline.tools.execute({id:'verify-membership',tool:'lemlist_get_contacts',input:{idsOrEmails:input.email},staleAfterSeconds:0,description:'Verify exact email and profile membership in the destination campaign'}));
    if(isCampaignMember(readback,input.email,input.profile)) {
      await deepline.customerDb.query(`UPDATE storage.erm_enrollment_outbox SET status='confirmed',updated_at=now() WHERE campaign_id=${q(CAMPAIGN)} AND profile=${q(input.profile)}`,{id:'confirm-membership',staleAfterSeconds:0,maxRows:1});
      return {status:'confirmed',campaignId:CAMPAIGN,receipt};
    }
    return {status:'submitted',campaignId:CAMPAIGN,reason:'Submission acknowledged; membership readback not yet confirmed',receipt};
  } catch(error) {
    await deepline.customerDb.query(`UPDATE storage.erm_enrollment_outbox SET status='uncertain',receipt=${j({error:String(error)})},updated_at=now() WHERE campaign_id=${q(CAMPAIGN)} AND profile=${q(input.profile)}`,{id:'record-uncertain',staleAfterSeconds:0,maxRows:1});
    throw error;
  }
}
