import assert from 'node:assert/strict';
import Module from 'node:module';
import {CAMPAIGN} from './enrollment-policy';
const input={profile:'https://www.linkedin.com/in/fixture',email:'fixture@lw.com',firstName:'Test',lastName:'Person',company:'Fixture'};
let count=99, claimed=false, sends=0, suppressed=false, existing=false, uncertain=false, campaignStatus='paused';
let pagination:'normal'|'second-page'|'incomplete'='normal';
let changes:string[]=[], childCalls:string[]=[];
const fake:any={run:{id:'fixture-run'},customerDb:{query:async(sql:string)=>{
  changes.push(sql);
  if(sql.startsWith('SELECT count')) return [{n:count}];
  if(sql.startsWith('SELECT profile')) return [{profile:input.profile}];
  if(sql.startsWith('INSERT INTO storage.erm_enrollment_outbox')) {if(claimed)return [];claimed=true;return [{profile:input.profile}];}
  return [];
}},runPlay:async(_id:string,name:string)=>{childCalls.push(name);return {status:'completed'};},tools:{execute:async(args:any)=>{
  if(args.tool==='lemlist_get_campaign') return {toolResponse:{rawV2:{_id:CAMPAIGN,status:campaignStatus}}};
  if(args.tool==='lemlist_list_unsubscribed_variables') {
    if(pagination==='incomplete'||(pagination==='second-page'&&args.input.offset===0)) return {toolResponse:{rawV2:Array.from({length:100},(_,i)=>({value:`unrelated-${i}@example.com`}))}};
    return {toolResponse:{rawV2:suppressed||pagination==='second-page'?[{value:input.email}]:[]}};
  }
  if(args.tool==='lemlist_get_contacts') {
    if(args.input.idsOrEmails) return {toolResponse:{rawV2:[{email:input.email,linkedinUrl:input.profile,campaigns:[{campaignId:CAMPAIGN,leadId:'fixture-lead'}]}]}};
    return {toolResponse:{rawV2:{data:existing?[{email:input.email}]:[],total:existing?1:0}}};
  }
  if(args.tool==='lemlist_add_to_campaign') {sends++;if(uncertain)throw new Error('response lost');return {toolResponse:{rawV2:{accepted:true}}};}
  if(args.tool==='lemlist_get_campaign_leads') return {toolResponse:{rawV2:[{email:input.email}]}};
  throw new Error('Unexpected tool '+args.tool);
}}};
const loader=(Module as any)._load;
(Module as any)._load=function(name:string,...args:any[]){return name==='deepline'?{__esModule:true,default:fake}:loader.call(this,name,...args);};
const enroll=require('./erm-enroll-candidate.play').default;
const cycle=require('./erm-recruitment-cycle.play').default;
async function main(){
  assert.equal((await enroll(input)).status,'confirmed');assert.equal(sends,1);
  assert.equal((await enroll(input)).status,'already_claimed');assert.equal(sends,1);
  assert(changes.some(s=>s.includes("status='confirmed'")));
  claimed=false;suppressed=true;assert.equal((await enroll(input)).status,'suppressed');assert.equal(sends,1);
  suppressed=false;existing=true;assert.equal((await enroll(input)).status,'held');assert.equal(sends,1);
  existing=false;pagination='second-page';assert.equal((await enroll(input)).status,'suppressed');assert.equal(sends,1);
  pagination='incomplete';await assert.rejects(()=>enroll(input),/SCAN_INCOMPLETE/);assert.equal(sends,1);
  pagination='normal';
  existing=false;campaignStatus='running';await assert.rejects(()=>enroll(input),/PAUSED/);assert.equal(sends,1);
  campaignStatus='paused';uncertain=true;await assert.rejects(()=>enroll(input),/response lost/);
  assert(changes.some(s=>s.includes("status='uncertain'")));assert.equal(sends,2);
  assert.equal((await enroll(input)).status,'already_claimed');assert.equal(sends,2);
  for(count of [100,101]) {childCalls=[];assert.equal((await cycle({})).status,'skipped');assert.equal(childCalls.length,0);}
  count=99;childCalls=[];assert.equal((await cycle({})).status,'completed');
  assert.deepEqual(childCalls,['erm-qualify-enroll-v1','erm-refill-experts-v1']);
  console.log('PASS: threshold routing, suppression, existing contacts, paused campaign, confirmed readback, replay, ambiguous-write protection.');
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{(Module as any)._load=loader;});
