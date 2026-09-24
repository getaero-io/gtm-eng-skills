import {exactDate} from './core';
export type ReviewEvidence={id:string;source:string;observed_at:string;subject_ids:string[];text:string};
export type ReviewClaim={id:string;factor:string;claim:string;as_of:string;subject_ids:string[];evidence:ReviewEvidence[];deterministic_status:'unclear'|'supported'|'contradicted';review_status:'needs_confirmation'|'blocked_declined'|'ready_for_human_review'};
export const REVIEW_VERSION='warm-intro-uncertainty-v1';
export const FACTORS=['identity','work_overlap','school_overlap','investor_role','investor_portfolio','board_overlap','city_overlap','role_industry','appearance','industry_match','community_match','direct_intro','relationship','freshness'];
export function validateClaim(c:ReviewClaim):void {
 if(!c||typeof c.id!=='string'||!c.id||typeof c.claim!=='string'||!c.claim.trim()||c.claim.length>4000||!FACTORS.includes(c.factor))throw Error('Invalid review claim');
 exactDate(c.as_of,'as_of');
 if(!['unclear','supported','contradicted'].includes(c.deterministic_status)||!['needs_confirmation','blocked_declined','ready_for_human_review'].includes(c.review_status))throw Error('Invalid review state');
 if(!Array.isArray(c.subject_ids)||!c.subject_ids.length||c.subject_ids.some(x=>typeof x!=='string'||!x)||new Set(c.subject_ids).size!==c.subject_ids.length)throw Error('Canonical subject IDs required');
 if(!Array.isArray(c.evidence)||c.evidence.length>20)throw Error('Review accepts at most 20 source excerpts');
 const ids=new Set();let chars=0;
 for(const e of c.evidence){if(typeof e.id!=='string'||!e.id||ids.has(e.id)||typeof e.source!=='string'||!e.source||typeof e.text!=='string'||!e.text||!Array.isArray(e.subject_ids)||e.subject_ids.some(x=>typeof x!=='string'||!x))throw Error('Invalid review evidence');ids.add(e.id);exactDate(e.observed_at,'observed_at');if(e.observed_at>c.as_of)throw Error('Future evidence cannot support a claim');chars+=e.text.length;}
 if(chars>40000)throw Error('Review excerpt bound exceeded');
}
export function citationGate(c:ReviewClaim,proposal:any):{ok:boolean;reason:string} {
 if(!proposal||!['supported','contradicted','insufficient_evidence'].includes(proposal.verdict)||typeof proposal.reason!=='string'||!Array.isArray(proposal.citations))return {ok:false,reason:'invalid_agent_output'};
 if(proposal.verdict==='insufficient_evidence')return {ok:false,reason:'insufficient_evidence'};
 if(!proposal.citations.length)return {ok:false,reason:'missing_citations'};
 const sources=new Map(c.evidence.map(e=>[e.id,e]));const subjects=new Set<string>();
 for(const ref of proposal.citations){const e=sources.get(ref.evidence_id);if(!e||typeof ref.quote!=='string'||!ref.quote.trim()||!e.text.includes(ref.quote))return {ok:false,reason:'citation_not_in_retained_source'};for(const id of e.subject_ids)subjects.add(id);}
 if(c.subject_ids.some(id=>!subjects.has(id)))return {ok:false,reason:'missing_subject_binding'};
 return {ok:true,reason:'source_quotes_and_subject_ids_match'};
}
export function finalReview(c:ReviewClaim,proposal:any,jev:{supported:boolean;contradicted:boolean}|null){
 const gate=citationGate(c,proposal);const agrees=gate.ok&&jev&&jev.supported!==jev.contradicted&&((proposal.verdict==='supported'&&jev.supported)||(proposal.verdict==='contradicted'&&jev.contradicted));
 return {claim_id:c.id,factor:c.factor,verdict:agrees?proposal.verdict:'insufficient_evidence',reason:agrees?proposal.reason:gate.ok?'reviewers_disagree_or_uncertain':gate.reason,citations:agrees?proposal.citations:[],additional_sources:proposal?.additional_sources||[],review_status:c.review_status==='blocked_declined'?'blocked_declined':'needs_confirmation',score_delta:0,automatic_score_update:false,version:REVIEW_VERSION};
}
export const REVIEW_SCHEMA={type:'object',additionalProperties:false,required:['verdict','reason','citations','additional_sources'],properties:{verdict:{type:'string',enum:['supported','contradicted','insufficient_evidence']},reason:{type:'string'},citations:{type:'array',items:{type:'object',additionalProperties:false,required:['evidence_id','quote'],properties:{evidence_id:{type:'string'},quote:{type:'string'}}}},additional_sources:{type:'array',items:{type:'string'}}}};
/** Jev returns probabilities for boolean questions, not literal booleans.
 * These cutoffs are conservative routing policy, not calibrated truth rates. */
export function jevDecision(answers:any):{supported:boolean;contradicted:boolean} {
 const p=(key:string)=>{const a=answers?.[key];if(a?.type!=='boolean'||typeof a.probability!=='number'||!Number.isFinite(a.probability)||a.probability<0||a.probability>1)throw Error('Unrecognized Jev probability envelope');return a.probability;};
 const support=p('supported'),contra=p('contradicted');
 return {supported:support>=0.9&&contra<=0.1,contradicted:contra>=0.9&&support<=0.1};
}
