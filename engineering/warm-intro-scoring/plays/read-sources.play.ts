/* eslint-disable @typescript-eslint/no-explicit-any -- Ported JSON contract/parity boundary; runtime validators reject malformed values. */
import { definePlay } from 'deepline';
type Source={source_id:string;schema_name:string;table_name:string;key_column:string};
const identifier=(s:string)=>{if(!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(s))throw new Error('Invalid SQL identifier');return '"'+s+'"';};
const quote=(s:string)=>"'"+s.replace(/'/g,"''")+"'";
/** @mermaid
flowchart TD
 sources[Customer database sources] --> pages[Read complete bounded snapshots]
 pages --> stored[Retain source records]
*/
export default definePlay('warm-intro-read-sources',async(ctx,input:{csv:string;max_rows_per_source?:number})=>{
 const limit=input.max_rows_per_source??5000;if(!Number.isInteger(limit)||limit<1||limit>5000)throw new Error('Source limit must be 1..5000');
 // @mermaid-node sources type:"dataset"
 const sources=await ctx.csv<Source>(input.csv,{required:['source_id','schema_name','table_name','key_column']});
 // @mermaid-node pages type:"dataset"
 const rows=await ctx.dataset('source_snapshots',sources).withColumn('snapshot',async(row,c)=>{
  const table=identifier(row.schema_name)+'.'+identifier(row.table_name),key=identifier(row.key_column);let cursor:string|null=null;const records:any[]=[];const seen=new Set<string>();
  const counts=await c.tools.execute({id:'validate_source_keys',tool:'query_customer_db',input:{sql:`SELECT COUNT(*) AS total, COUNT(${key}) AS keyed, COUNT(DISTINCT ${key}::text) AS unique_keys FROM ${table}`,max_rows:1},staleAfterSeconds:0,description:'Require complete unique source identities'});
  const countRaw:any=counts.toolResponse.rawV2??counts.toolResponse.raw;const stats=countRaw?.rows?.[0];
  if(!stats||Number(stats.total)!==Number(stats.keyed)||Number(stats.total)!==Number(stats.unique_keys))throw new Error('Source key must be unique and non-null; supply a source view with stable unique IDs');
  const expected=Number(stats.total);if(!Number.isSafeInteger(expected)||expected>limit)throw new Error('Source exceeds configured bound; partition it before reading');
  while(true){
   const sql=`SELECT * FROM ${table} WHERE ${key} IS NOT NULL${cursor===null?'':` AND ${key}::text > ${quote(cursor)}`} ORDER BY ${key}::text LIMIT 250`;
   const result=await c.tools.execute({id:'read_source_page',tool:'query_customer_db',input:{sql,max_rows:250},staleAfterSeconds:0,description:'Read versioned source page'});
   const raw:any=result.toolResponse.rawV2??result.toolResponse.raw;
   if(!raw||!Array.isArray(raw.rows)||raw.truncated)throw new Error('Source page is missing or truncated');
   for(const item of raw.rows){const id=String(item[row.key_column]);if(seen.has(id))throw new Error('Source key is not unique');seen.add(id);records.push(item);}
   if(records.length>limit)throw new Error('Source exceeds configured bound; partition the source instead of dropping rows');
   if(raw.rows.length<250)break;
   cursor=String(raw.rows[raw.rows.length-1][row.key_column]);
  }
  if(records.length!==expected)throw new Error('Source changed during pagination; retry a stable snapshot');
  return {source_id:row.source_id,table,count:records.length,records};
 }).run({key:'source_id',undrawnColumns:['snapshot']});
 // @mermaid-node stored
 return {rows,count:await rows.count(),interpretation:'Source records retain their own observation dates. Reading a record does not refresh the profile.'};
},{description:'Read scoring source snapshots'});
