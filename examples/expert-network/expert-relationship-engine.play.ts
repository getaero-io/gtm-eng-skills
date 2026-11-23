import deepline from 'deepline';
import { advance } from './engine';
import { databaseStore } from './db';
import type { Payload, Result } from './types';
/** @mermaid
 * flowchart TD
 *   process[Advance expert episode] --> discover[[Resolve expert identity]]
 *   discover --> qualify[[Read qualification decision]]
 *   qualify --> recruit[[Read interest and consent]]
 *   recruit --> onboard[[Check onboarding prerequisites]]
 *   onboard --> match[[Check task fit and capacity]]
 *   match --> review[[Read submission review]]
 *   review --> learn[[Join quality and usage evidence]]
 *   learn --> result[Show next action and evidence]
 */
export const config = {
  name: 'expert-relationship-engine-v1',
  description: 'Synthetic expert relationship demo: find, qualify, recruit, onboard, match, review and learn. Recommendations only.',
  billing: { maxCreditsPerRun: 1 },
};
export default async function (input: { episodeId: string; payload: Payload }) {
  // @mermaid-node process in:"input" out:"result"
  const result = await advance(input, databaseStore(deepline), async (state, row) => {
    const payload = { payload: row.payload };
    switch (state) {
      case 'discover':
        // @mermaid-node discover type:"play" in:"payload" out:"discover"
        return deepline.runPlay<Result>('discover', 'erm-discover-v1', payload, { description: 'Resolve expert identity evidence' });
      case 'qualify':
        // @mermaid-node qualify type:"play" in:"payload" out:"qualify"
        return deepline.runPlay<Result>('qualify', 'erm-qualify-v1', payload, { description: 'Read human qualification decision' });
      case 'recruit':
        // @mermaid-node recruit type:"play" in:"payload" out:"recruit"
        return deepline.runPlay<Result>('recruit', 'erm-recruit-v1', payload, { description: 'Read interest and consent' });
      case 'onboard':
        // @mermaid-node onboard type:"play" in:"payload" out:"onboard"
        return deepline.runPlay<Result>('onboard', 'erm-onboard-v1', payload, { description: 'Check onboarding prerequisites' });
      case 'match':
        // @mermaid-node match type:"play" in:"payload" out:"match"
        return deepline.runPlay<Result>('match', 'erm-match-v1', payload, { description: 'Match specialty and availability to approved task' });
      case 'review':
        // @mermaid-node review type:"play" in:"payload" out:"review"
        return deepline.runPlay<Result>('review', 'erm-review-v1', payload, { description: 'Read human submission review' });
      case 'learn':
        // @mermaid-node learn type:"play" in:"payload" out:"learn"
        return deepline.runPlay<Result>('learn', 'erm-learn-v1', payload, { description: 'Join task quality and platform usage' });
      default: throw new Error('UNKNOWN_STATE');
    }
  });
  // @mermaid-node result in:"result" out:"$output"
  return result;
}
