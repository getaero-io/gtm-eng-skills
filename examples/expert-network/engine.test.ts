import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { advance, type Store } from './engine';
import { EDGES, keyFor, type EngineInput, type Output, type State } from './types';
import { transform as discover } from './transitions/discover/transform';
import { transform as qualify } from './transitions/qualify/transform';
import { transform as recruit } from './transitions/recruit/transform';
import { transform as onboard } from './transitions/onboard/transform';
import { transform as match } from './transitions/match/transform';
import { transform as review } from './transitions/review/transform';
import { transform as learn } from './transitions/learn/transform';
const transforms = { discover, qualify, recruit, onboard, match, review, learn };
const fixture = (): EngineInput => JSON.parse(readFileSync(new URL('./fixtures/pilot-1.json', import.meta.url), 'utf8'));
class Memory implements Store {
  episodes = new Map<string, string>(); inputs = new Map<string, string | null>(); outputs = new Map<string, Output>(); calls: State[] = [];
  async accept(i: EngineInput) { const k = i.payload.expert.expertId + i.episodeId; const s = JSON.stringify(i.payload); if(this.episodes.has(k) && this.episodes.get(k)!==s) throw Error('EPISODE_INPUT_CONFLICT'); this.episodes.set(k,s); }
  async input(i: EngineInput, s: State, prior: string | null) { const k=keyFor(i,s); if (!this.inputs.has(k)) this.inputs.set(k,prior); }
  async read(k: string) { return this.outputs.get(k) ?? null; }
  async save(o: Output) { if (this.outputs.get(o.key)?.status!=='completed') this.outputs.set(o.key,structuredClone(o)); }
  dispatch = async (s: State, i: EngineInput) => { this.calls.push(s); return transforms[s as keyof typeof transforms](i.payload); };
}
async function main() {
  const covered = new Set<string>();
  const scenarios: [string, (i: EngineInput)=>void, string][] = [
    ['complete',()=>{},'complete'], ['identity missing',i=>{i.payload.expert.identityReviewed=false;},'waiting'],
    ['qualification pending',i=>{i.payload.expert.qualification='pending';},'waiting'],
    ['qualification rejected',i=>{i.payload.expert.qualification='rejected';},'declined'],
    ['response pending',i=>{i.payload.expert.response='pending';},'waiting'],
    ['response declined',i=>{i.payload.expert.response='declined';},'declined'],
    ['consent missing',i=>{i.payload.expert.consent=false;},'waiting'],
    ['agreement missing',i=>{i.payload.expert.agreementSigned=false;},'waiting'],
    ['capacity missing',i=>{i.payload.expert.availabilityHours=1;},'waiting'],
    ['specialty mismatch',i=>{i.payload.task.specialty='other';},'waiting'],
    ['assignment unapproved',i=>{i.payload.task.assignmentApproved=false;},'waiting'],
    ['revision',i=>{i.payload.task.review='revision';},'waiting'],
    ['no submission',i=>{i.payload.task.submissionId='';},'waiting'],
    ['usage missing',i=>{i.payload.usage=[];},'complete'],
  ];
  for (const [label, change, terminal] of scenarios) {
    const i=fixture(), m=new Memory(); change(i);
    const r=await advance(i,m,m.dispatch); assert.equal(r.state,terminal,label);
    for(const o of m.outputs.values()) if(o.toState) covered.add(`${o.fromState}:${o.toState}`);
    assert.equal(m.inputs.size,m.outputs.size,label);
    const count=m.calls.length; const outCount=m.outputs.size;
    await advance(i,m,m.dispatch); assert.equal(m.calls.length,count); assert.equal(m.outputs.size,outCount);
    if(label==='usage missing') assert.equal(r.facts.acceptedUses,null);
  }
  for(const [s, edges] of Object.entries(EDGES)) for(const e of edges) assert(covered.has(`${s}:${e}`),`uncovered ${s}:${e}`);
  for(const fail of ['CHILD_FAILURE','INVALID_CHILD_RESULT']) {
    const i=fixture(),m=new Memory();
    await assert.rejects(advance(i,m,async()=>{if(fail==='CHILD_FAILURE') throw Error(fail); return {nextState:'complete',reason:'bad edge',action:'none',facts:{}};}));
    assert.equal(m.outputs.get(keyFor(i,'discover'))?.status,fail==='CHILD_FAILURE'?'failed':'invalid'); assert.equal(m.inputs.size,1);
  }
  const bad=new Memory(); await assert.rejects(advance(fixture(),bad,bad.dispatch,'corrupt')); assert.equal([...bad.outputs.values()][0].status,'invalid');
  const m=new Memory(), i=fixture(); await advance(i,m,m.dispatch);
  m.inputs.delete(keyFor(i,'qualify')); const calls=m.calls.length; await advance(i,m,m.dispatch); assert(m.inputs.has(keyFor(i,'qualify'))); assert.equal(m.calls.length,calls);
  const changed=fixture(); changed.payload.expert.availabilityHours=9; await assert.rejects(advance(changed,m,m.dispatch),/CONFLICT/);
  const second=fixture(); second.payload.expert.expertId='syn-independent'; await advance(second,m,m.dispatch); assert.equal(m.episodes.size,2);
  const dup=fixture(); dup.payload.usage.push(dup.payload.usage[0]); await assert.rejects(advance(dup,new Memory(),m.dispatch),/DUPLICATE/);
  const real=fixture(); real.payload.synthetic=false as true; await assert.rejects(advance(real,new Memory(),m.dispatch),/SYNTHETIC_ONLY/);
  const concurrent=new Memory(); await Promise.all([advance(fixture(),concurrent,concurrent.dispatch),advance(fixture(),concurrent,concurrent.dispatch)]); assert.equal(concurrent.outputs.size,8); assert.equal(concurrent.inputs.size,8);
  console.log(`PASS: ${scenarios.length} scenarios; all ${covered.size} edges; terminal, replay, handoff repair, invalid state/result, child failure, input conflict, identity isolation, concurrent deterministic runs, synthetic guard and duplicate events.`);
}
main().catch(e=>{console.error(e);process.exitCode=1;});
