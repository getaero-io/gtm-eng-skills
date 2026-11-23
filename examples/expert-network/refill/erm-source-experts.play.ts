import deepline from 'deepline';
import { DOMAINS, normalize } from './policy';
/** @mermaid
 * flowchart TD
 *   search[Find relevant professionals] --> filter[Keep matching US practitioners]
 */
export const config = { name: 'erm-source-experts-v1', description: 'Find up to 25 US law or consulting candidates at an allowlisted firm; return evidence, not qualification claims.', billing: { maxCreditsPerRun: 2 } };
export default async function (input: { domain: string; limit: number; excludedNames: string[] }) {
  const scope = DOMAINS.find(d => d.domain === input.domain);
  if (!scope || !Number.isInteger(input.limit) || input.limit < 1 || input.limit > 25) throw new Error('INVALID_SEARCH_SCOPE');
  // @mermaid-node search in:"input" out:"found"
  const found = await deepline.tools.execute({ id: 'source-experts', tool: 'search_contact', staleAfterSeconds: 86400,
    input: { domain: scope.domain, location_countries: ['United States'], page_size: input.limit, page_number: 1,
      excluded_names: input.excludedNames.filter(n => n.length >= 4).slice(0,100),
      title_filters: [{name:'Expert practitioners',filter:scope.vertical === 'law' ? 'Associate OR Counsel OR Attorney' : 'Engagement Manager OR Associate Partner OR Consultant OR Project Leader'}] },
    description: 'Find professional profiles at the selected firm' });
  const raw = found.fields.persons.values as Record<string, any>[];
  if (!Array.isArray(raw)) throw new Error('SOURCE_SHAPE_MISMATCH');
  // @mermaid-node filter in:"raw" out:"$output" show:"candidates,returned,rejected"
  return { candidates: raw.map(p => normalize(p,scope.domain,scope.vertical)).filter(Boolean), returned: raw.length, rejected: raw.filter(p => !normalize(p,scope.domain,scope.vertical)).length };
}
