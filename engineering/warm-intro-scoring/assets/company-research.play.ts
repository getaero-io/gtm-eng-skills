import { definePlay } from 'deepline';
/** @mermaid
flowchart TD
  targets[Target domains] --> lookup[Get company data]
  lookup --> results[Store source receipts]
*/
export default definePlay('warm-intro-company-research',async(ctx,input:{companies:Array<{company_id:string,domain:string}>})=>{
 // @mermaid-node targets
 const companies = input.companies;
 // @mermaid-node lookup type:"dataset" in:"companies" out:"rows"
 const rows=await ctx.dataset('target_companies', companies).withColumn('akta',async(row,c)=>{
  const result=await c.tools.execute({id:'akta_company_data',tool:'akta_company_enrichment',input:{company:'https://'+row.domain,sections:'firmographic,industry,funding_detail,management_profile'},description:'Get company data. Keep source receipt.'});
  return result.toolResponse.rawV2;
 }).run({key:'domain',undrawnColumns:['akta']});
 // @mermaid-node results
 return {rows,count:await rows.count()};
},{description:'Get company data for the existing warm intro target set. No contact changes.'});
