/* eslint-disable @typescript-eslint/no-explicit-any -- Ported JSON contract/parity boundary; runtime validators reject malformed values. */
import {strictJSON} from './strict-json';
import { definePlay } from 'deepline';
import { exactDate } from './core';
type Row={record_id:string;kind:string;revision:string;observed_at:string;payload_json:string};
const quote=(s:string)=>"'"+s.replace(/'/g,"''")+"'";
function canonical(v:any):string {if(v===null||typeof v!=='object')return JSON.stringify(v);if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';}
function raw(r:any){const v=r?.toolResponse?.rawV2??r?.toolResponse?.raw;if(!v||!Array.isArray(v.rows))throw new Error('Database returned an unrecognized receipt');return v;}
/** @mermaid
flowchart TD
 input[Versioned source records] --> schema[Ensure snapshot table]
 schema --> snapshots[Validate and save immutable versions]
 snapshots --> receipt[Verify persisted records]
*/
export default definePlay('warm-intro-snapshots',async(ctx,input:{csv:string;execute:boolean})=>{
 // @mermaid-node input type:"dataset"
 const source=await ctx.csv<Row>(input.csv,{required:['record_id','kind','revision','observed_at','payload_json']});
 // @mermaid-node schema in:"input.execute" out:"snapshot_schema"
 if(input.execute)await ctx.tools.execute({id:'snapshot_schema',tool:'query_customer_db',input:{sql:'CREATE TABLE IF NOT EXISTS analytics.warm_intro_play_snapshots (record_id text NOT NULL, kind text NOT NULL, revision text NOT NULL, observed_at date NOT NULL, content_hash text NOT NULL, payload jsonb NOT NULL, PRIMARY KEY (kind,record_id,revision))',max_rows:1},description:'Create additive snapshot table'});
 // @mermaid-node snapshots type:"dataset"
 const rows=await ctx.dataset('snapshot_receipts',source).withColumn('receipt',async(row,c)=>{
  if(!row.record_id||!row.revision||!['contact','target','investor_edge','relationship','willingness','feedback','tombstone'].includes(row.kind)||!/^\d{4}-\d{2}-\d{2}$/.test(row.observed_at))throw new Error('Snapshot identity, kind, revision and date required');
  exactDate(row.observed_at,'observed_at');
  const payload=canonical(strictJSON(row.payload_json));const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(payload)));const hash=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
  const sql=`INSERT INTO analytics.warm_intro_play_snapshots (record_id,kind,revision,observed_at,content_hash,payload) VALUES (${quote(row.record_id)},${quote(row.kind)},${quote(row.revision)},${quote(row.observed_at)}::date,${quote(hash)},${quote(payload)}::jsonb) ON CONFLICT (kind,record_id,revision) DO UPDATE SET content_hash=EXCLUDED.content_hash WHERE warm_intro_play_snapshots.content_hash=EXCLUDED.content_hash AND warm_intro_play_snapshots.observed_at=EXCLUDED.observed_at RETURNING record_id,kind,revision,content_hash`;
  if(!input.execute)return {status:'planned',record_id:row.record_id,kind:row.kind,revision:row.revision,content_hash:hash,table:'analytics.warm_intro_play_snapshots'};
  const write=raw(await c.tools.execute({id:'save_snapshot',tool:'query_customer_db',input:{sql,max_rows:1},description:'Save immutable source revision'}));
  if(write.rows.length!==1)throw new Error('Revision conflict: same identity has different content or date');
  const check=raw(await c.tools.execute({id:'verify_snapshot',tool:'query_customer_db',input:{sql:`SELECT content_hash FROM analytics.warm_intro_play_snapshots WHERE kind=${quote(row.kind)} AND record_id=${quote(row.record_id)} AND revision=${quote(row.revision)}`,max_rows:1},staleAfterSeconds:0,description:'Verify saved source revision'}));
  if(check.rows.length!==1||check.rows[0].content_hash!==hash)throw new Error('Saved snapshot failed read-back verification');
  return {status:'applied',record_id:row.record_id,kind:row.kind,revision:row.revision,content_hash:hash};
 }).run({key:(r)=>r.kind+':'+r.record_id+':'+r.revision,undrawnColumns:['receipt']});
 // @mermaid-node receipt
 return {rows,count:await rows.count(),execute:input.execute,interpretation:'New versions are preserved. This manual import does not enable schedules or send introductions.'};
},{description:'Store versioned scoring evidence'});
