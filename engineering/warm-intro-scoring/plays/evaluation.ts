/** Offline evaluator. Explicit as_of is its clock; no sends or automatic promotion. */
import {compareText} from './core.ts';
type RecordValue = Record<string, any>;
const get = (o:RecordValue,k:string,d:any) => k in o ? o[k] : d;
const fail = (message: string): never => { throw new Error(message); };
const object = (v: any, required: string[], optional: string[] = []) => {
  if (!v || typeof v !== 'object' || Array.isArray(v)) fail('expected object');
  if (required.some(k => !(k in v)) || Object.keys(v).some(k => !required.includes(k) && !optional.includes(k))) fail('missing or unknown fields');
};
const string = (v: any) => { if (typeof v !== 'string' || !v.trim()) fail('nonempty string required'); return v; };
const strings = (v: any): Set<string> => { if (!Array.isArray(v)) fail('list required'); v.forEach(string); const s = new Set<string>(v); if (s.size !== v.length) fail('duplicate IDs'); return s; };
const same = (a: Set<any>, b: Set<any>) => a.size === b.size && [...a].every(k => b.has(k));
const choice = (v: any, values: string[]) => { if (!values.includes(v)) fail('invalid choice'); };
export const timestamp = (v: any): bigint => {
  string(v);
  const m = v.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:[.,](\d+))?(Z|[+-]\d{2}:\d{2})$/);
  if (!m) fail('ISO timestamp with timezone required');
  const [year,month,day,hour,minute,second] = m.slice(1,7).map(Number);
  const leap = year%4===0 && (year%100!==0 || year%400===0);
  const days = [31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
  if (year<1 || month<1 || month>12 || day<1 || day>days[month-1] || hour>23 || minute>59 || second>59) fail('invalid timestamp');
  if (m[8] !== 'Z' && (Number(m[8].slice(1,3))>23 || Number(m[8].slice(4,6))>59)) fail('invalid timezone');
  const whole = `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}${m[8]}`;
  const milliseconds = Date.parse(whole); if (!Number.isFinite(milliseconds)) fail('invalid timestamp');
  // Python datetime truncates excess fractional digits; retain exact microseconds.
  return BigInt(milliseconds)*1000n + BigInt((m[7] ?? '').padEnd(6,'0').slice(0,6));
};
const integer = (v: any, lo: number, hi: number) => { if (!Number.isSafeInteger(v) || v < lo || v > hi) fail('integer out of range'); };
function finite(v: any) { if (typeof v === 'number' && !Number.isFinite(v)) fail('nonfinite number'); if (v && typeof v === 'object') Object.values(v).forEach(finite); }

export function validateEvaluation(data: RecordValue) {
  finite(data);
  object(data, ['as_of','queries'], ['seed','bootstrap_samples','outcome_window_days','outcomes','split','baseline_version','candidate_version','fictional']);
  const cutoff = timestamp(data.as_of);
  // JS transports cannot exactly represent integer seeds above 2^53-1: reject, never round silently.
  integer(get(data,'seed',1729), 0, Number.MAX_SAFE_INTEGER); integer(get(data,'bootstrap_samples',2000), 100, 100000); integer(get(data,'outcome_window_days',14), 1, 3650);
  for (const key of ['baseline_version','candidate_version']) if (key in data) string(data[key]);
  if ('fictional' in data && typeof data.fictional !== 'boolean') fail('fictional must be boolean');
  if (!Array.isArray(data.queries)) fail('queries list required');
  let sets: Record<string, Set<string>> | undefined;
  if ('split' in data) {
    const keys = ['train_target_ids','test_target_ids','train_account_ids','test_account_ids']; object(data.split, keys);
    sets = Object.fromEntries(keys.map(k => [k, strings(data.split[k])]));
    for (const g of ['target','account']) if ([...sets[`train_${g}_ids`]].some(k => sets![`test_${g}_ids`].has(k))) fail('train/test leakage');
  }
  const queryIds = new Set();
  for (const q of data.queries) {
    object(q, ['id','scored_at','target_id','account_id','labels','baseline','candidate','paths']);
    ['id','target_id','account_id'].forEach(k => string(q[k]));
    if (queryIds.has(q.id)) fail('duplicate query ID'); queryIds.add(q.id);
    if (sets) for (const g of ['target','account']) if (!sets[`test_${g}_ids`].has(q[`${g}_id`])) fail('query outside test split');
    const scored = timestamp(q.scored_at); if (scored > cutoff) fail('scored_at after as_of');
    if (!q.labels || typeof q.labels !== 'object' || Array.isArray(q.labels)) fail('labels object required');
    for (const [k,v] of Object.entries(q.labels)) { string(k); if (v !== null && v !== 0 && v !== 1) fail('invalid label'); }
    const universe = new Set(Object.keys(q.labels));
    for (const ranker of ['baseline','candidate']) if (!same(strings(q[ranker]), universe)) fail('ranking universe mismatch');
    if (!Array.isArray(q.paths)) fail('paths list required'); const ids = new Set();
    for (const p of q.paths) {
      object(p, ['id','status','sender_edge','target_edge','willingness','feature_dates']); string(p.id);
      if (ids.has(p.id)) fail('duplicate path ID'); ids.add(p.id);
      choice(p.status, ['ready','research','blocked']); for (const e of ['sender_edge','target_edge']) choice(p[e], ['strong','medium','weak','unknown']); choice(p.willingness, ['yes','no','unknown']);
      if (!Array.isArray(p.feature_dates) || !p.feature_dates.length) fail('feature dates required');
      p.feature_dates.forEach((v: any) => { if (timestamp(v) > scored) fail('feature leakage'); });
      if (p.status === 'ready' && (!['strong','medium'].includes(p.sender_edge) || !['strong','medium'].includes(p.target_edge) || p.willingness !== 'yes')) fail('unsafe ready path');
    }
    if (!same(ids, universe)) fail('path universe mismatch');
  }
  if ('outcomes' in data && !Array.isArray(data.outcomes)) fail('outcomes list required'); const ids = new Set();
  for (const o of data.outcomes ?? []) {
    object(o, ['id','status','created_at','reply','meeting'], ['sent_at','observed_through','reply_at','meeting_at']); string(o.id);
    if (ids.has(o.id)) fail('duplicate outcome ID'); ids.add(o.id); choice(o.status, ['draft','sent']);
    const dates: Record<string,bigint> = {}; for (const k of Object.keys(o).filter(k => k.endsWith('_at') || k === 'observed_through')) { dates[k] = timestamp(o[k]); if (dates[k] > cutoff) fail('future outcome'); }
    for (const e of ['reply','meeting']) { if (o[e] !== null && typeof o[e] !== 'boolean') fail('invalid outcome'); if ((o[e] === true) !== (`${e}_at` in dates)) fail('event timestamp mismatch'); }
    if (o.status === 'draft') { if (Object.keys(dates).length !== 1 || o.reply !== null || o.meeting !== null) fail('draft has observed outcomes'); }
    else { if (!('sent_at' in dates) || !('observed_through' in dates) || dates.created_at > dates.sent_at || dates.sent_at > dates.observed_through) fail('invalid sent chronology');
      for (const e of ['reply_at','meeting_at']) if (e in dates && (dates[e] < dates.sent_at || dates[e] > dates.observed_through)) fail('event outside observation'); }
  }
  return cutoff;
}

/** CPython integer seeding (init_by_array), MT19937 and _randbelow_with_getrandbits. */
export class PythonRandom {
  private mt = new Uint32Array(624); private index = 624;
  constructor(seed: number) {
    const key: number[] = []; let n = BigInt(seed); do { key.push(Number(n & 0xffffffffn)); n >>= 32n; } while (n);
    this.mt[0] = 19650218;
    for (let i = 1; i < 624; i++) this.mt[i] = (Math.imul(1812433253, this.mt[i-1] ^ (this.mt[i-1] >>> 30)) + i) >>> 0;
    let i = 1, j = 0;
    for (let k = Math.max(624,key.length); k; k--) { this.mt[i] = ((this.mt[i] ^ Math.imul(this.mt[i-1] ^ (this.mt[i-1] >>> 30),1664525)) + key[j] + j) >>> 0; i++; j++; if (i >= 624) { this.mt[0] = this.mt[623]; i = 1; } if (j >= key.length) j = 0; }
    for (let k = 623; k; k--) { this.mt[i] = ((this.mt[i] ^ Math.imul(this.mt[i-1] ^ (this.mt[i-1] >>> 30),1566083941)) - i) >>> 0; i++; if (i >= 624) { this.mt[0] = this.mt[623]; i = 1; } }
    this.mt[0] = 0x80000000;
  }
  private word() {
    if (this.index >= 624) { for (let i = 0; i < 624; i++) { const y = (this.mt[i] & 0x80000000) | (this.mt[(i+1)%624] & 0x7fffffff); this.mt[i] = this.mt[(i+397)%624] ^ (y >>> 1) ^ ((y & 1) ? 0x9908b0df : 0); } this.index = 0; }
    let y = this.mt[this.index++]; y ^= y >>> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >>> 18; return y >>> 0;
  }
  randrange(n: number) { const bits = Math.floor(Math.log2(n)) + 1; let r; do { r = this.word() >>> (32-bits); } while (r >= n); return r; }
}
const keys = ['recall@3','mrr','ndcg@3'];
function mean(xs: number[]) { // Compensated summation reduces differences from Python statistics.fmean.
  let sum = 0, c = 0; for (const x of xs) { const t = sum+x; c += Math.abs(sum) >= Math.abs(x) ? (sum-t)+x : (x-t)+sum; sum = t; } return (sum+c)/xs.length;
}
export function rankMetrics(ranking: string[], labels: Record<string,number>) {
  const gains = ranking.map(k => labels[k]), relevant = Object.values(labels).reduce((a,b) => a+b,0);
  const ideal = Array.from({length:Math.min(3,relevant)}, (_,i) => 1/Math.log2(i+2)).reduce((a,b) => a+b,0);
  return {'recall@3':gains.slice(0,3).reduce((a,b)=>a+b,0)/relevant,mrr:1/(gains.indexOf(1)+1),'ndcg@3':gains.slice(0,3).reduce((a,g,i)=>a+g/Math.log2(i+2),0)/ideal};
}
function percentile(xs: number[], fraction: number) { const a = [...xs].sort((a,b)=>a-b), p = (a.length-1)*fraction; return a[Math.floor(p)]+(a[Math.ceil(p)]-a[Math.floor(p)])*(p-Math.floor(p)); }
export function outcomeReport(data: RecordValue) {
  const r: RecordValue = {total_records:0,drafts:0,sent:0,sent_immature:0,sent_unobserved:0,matured_sent_denominator:0,replies_within_window:0,meetings_within_window:0,raw_reply_events:0,raw_meeting_events:0};
  const days = get(data,'outcome_window_days',14);
  for (const o of data.outcomes ?? []) { r.total_records++; for (const e of ['reply','meeting']) r[`raw_${e}_events`] += Number(o[e] === true);
    if (o.status === 'draft') { r.drafts++; continue; } r.sent++; const horizon = timestamp(o.sent_at)+BigInt(days)*86400000000n;
    if (timestamp(o.observed_through) < horizon) { r.sent_immature++; continue; }
    if (o.reply === null || o.meeting === null) { r.sent_unobserved++; continue; } r.matured_sent_denominator++;
    for (const [e,k] of [['reply','replies_within_window'],['meeting','meetings_within_window']]) if (o[e] && timestamp(o[`${e}_at`]) <= horizon) r[k]++;
  }
  return {...r,window_days:days,reply_rate:r.matured_sent_denominator ? r.replies_within_window/r.matured_sent_denominator : null,meeting_rate:r.matured_sent_denominator ? r.meetings_within_window/r.matured_sent_denominator : null,interpretation:'Observed selected sends only; no causal comparison between rankers. Null rate means unavailable.'};
}
export function evaluate(data: RecordValue) {
  validateEvaluation(data);
  const coverage: RecordValue = {total_queries:data.queries.length,eligible_queries:0,total_labels:0,judged_labels:0,exclusions:{incomplete_judgments:0,no_relevant:0}};
  const rows: RecordValue[] = data.queries.map((q: RecordValue) => { const values = Object.values(q.labels); coverage.total_labels += values.length; coverage.judged_labels += values.filter(v=>v!==null).length;
    const reason = values.includes(null) ? 'incomplete_judgments' : !values.includes(1) ? 'no_relevant' : null;
    const row: RecordValue = {id:q.id,scored_at:q.scored_at,target_id:q.target_id,account_id:q.account_id,exclusion:reason};
    if (reason) coverage.exclusions[reason]++; else { coverage.eligible_queries++; row.baseline=rankMetrics(q.baseline,q.labels); row.candidate=rankMetrics(q.candidate,q.labels); row.delta=Object.fromEntries(keys.map(k=>[k,row.candidate[k]-row.baseline[k]])); } return row;
  });
  const eligible = rows.filter(r=>r.exclusion===null), n=eligible.length, samples=get(data,'bootstrap_samples',2000), seed=get(data,'seed',1729), rng=new PythonRandom(seed);
  const clusters = new Map<string,RecordValue[]>(); for (const r of eligible) { if (!clusters.has(r.account_id)) clusters.set(r.account_id,[]); clusters.get(r.account_id)!.push(r); }
  const accounts=[...clusters.keys()].sort(compareText); coverage.independent_accounts=accounts.length;
  const bootstrap: Record<string,number[]> = Object.fromEntries(keys.map(k=>[k,[]]));
  if (n) for (let i=0;i<samples;i++) { const drawn=accounts.flatMap(()=>clusters.get(accounts[rng.randrange(accounts.length)])!); for (const k of keys) bootstrap[k].push(mean(drawn.map(r=>r.delta[k]))); }
  const metrics=Object.fromEntries(keys.map(k=>[k,{baseline:n?mean(eligible.map(r=>r.baseline[k])):null,candidate:n?mean(eligible.map(r=>r.candidate[k])):null,delta:n?mean(eligible.map(r=>r.delta[k])):null,delta_ci95:n?[percentile(bootstrap[k],.025),percentile(bootstrap[k],.975)]:null,paired_query_denominator:n}]));
  const warnings=['Exploratory diagnostics only; not proven uplift. No automatic promotion or causal inference.','Supplied metadata cannot verify source truth or independently adjudicated labels.'];
  let insufficient=accounts.length<30 || coverage.exclusions.incomplete_judgments>0 || !!data.fictional;
  if(accounts.length<30) warnings.push('Small sample: fewer than 30 eligible accounts; uncertainty is unstable and evidence is insufficient.');
  if(data.fictional) warnings.push('Fictional fixture: validates behavior only, not real-world accuracy.');
  if(!('split' in data)) { insufficient=true; warnings.push('Train/test group metadata not supplied; leakage separation is unverified.'); }
  warnings.push('Account-cluster bootstrap assumes independent accounts; shared connectors and other cross-account dependencies are not modeled.');
  return {schema_version:1,as_of:data.as_of,status:insufficient?'insufficient_evidence':'diagnostic_only',promotion_allowed:false,gates:{valid:true,split_checked:'split'in data},versions:{baseline_version:data.baseline_version??null,candidate_version:data.candidate_version??null},coverage,metrics,queries:rows,outcomes:outcomeReport(data),bootstrap:{seed,samples,unit:'account',method:'paired percentile 95%, linear interpolation'},warnings};
}
