import deepline from 'deepline';
import { validatePayload, type Payload } from './types';
import { transform } from './transform';
/** @mermaid
 * flowchart TD
 *   decide[Evaluate learn evidence] --> outcome[Return next state and action]
 */
export const config = { name: 'erm-learn-v1', description: 'Evaluate synthetic learn evidence without external actions.', billing: { maxCreditsPerRun: 1 } };
export default async function (input: { payload: Payload }) {
  validatePayload(input.payload);
  // @mermaid-node decide
  const result = transform(input.payload);
  // @mermaid-node outcome in:"result" out:"$output"
  return result;
}
