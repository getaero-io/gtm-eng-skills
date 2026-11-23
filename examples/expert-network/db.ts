import type { DeeplinePlayRuntimeContext } from 'deepline';
import { STATES, VERSION, keyFor, type EngineInput, type Output, type State } from './types';
import type { Store } from './engine';
export const q = (value: string) => `'${value.replaceAll("'", "''")}'`;
export const j = (value: unknown) => `${q(JSON.stringify(value))}::jsonb`;
export const table = (state: string, role: 'input' | 'output') => `storage.erm_v1_${STATES.includes(state as State) ? state : 'invalid'}_${role}`;
export function databaseStore(ctx: DeeplinePlayRuntimeContext): Store {
  const query = <T extends Record<string, unknown>>(_label: string, sql: string) => ctx.customerDb.query<T>(sql, { id: 'erm-db-query', staleAfterSeconds: 0, maxRows: 1 });
  return {
    async accept(input) {
      const id = JSON.stringify([VERSION, input.payload.expert.expertId, input.episodeId]);
      await query('accept-episode', `INSERT INTO storage.erm_v1_episodes(id,payload) VALUES(${q(id)},${j(input.payload)}) ON CONFLICT DO NOTHING`);
      const [row] = await query('verify-episode', `SELECT payload=${j(input.payload)} AS same FROM storage.erm_v1_episodes WHERE id=${q(id)} LIMIT 1`);
      if (row?.same !== true) throw new Error('EPISODE_INPUT_CONFLICT: use a new episodeId for new evidence');
    },
    async input(input: EngineInput, state: State, prior: string | null) {
      await query(`input-${state}`, `INSERT INTO ${table(state,'input')}(id,expert_id,episode_id,state,payload,prior_transition,workflow_version) VALUES(${q(keyFor(input,state))},${q(input.payload.expert.expertId)},${q(input.episodeId)},${q(state)},${j(input.payload)},${prior ? q(prior) : 'NULL'},${q(VERSION)}) ON CONFLICT DO NOTHING`);
    },
    async read(key, state) {
      const [row] = await query('read-completed', `SELECT record FROM ${table(state,'output')} WHERE id=${q(key)} LIMIT 1`);
      return row ? row.record as Output : null;
    },
    async save(o) {
      await query('save-outcome', `INSERT INTO ${table(o.fromState,'output')}(id,expert_id,episode_id,from_state,to_state,status,record,workflow_version,transition_play,transition_version) VALUES(${q(o.key)},${q(o.expertId)},${q(o.episodeId)},${q(o.fromState)},${o.toState ? q(o.toState) : 'NULL'},${q(o.status)},${j(o)},${q(VERSION)},${q(o.play)},'erm-synthetic-v1') ON CONFLICT(id) DO UPDATE SET status=EXCLUDED.status,to_state=EXCLUDED.to_state,record=EXCLUDED.record,processed_at=now() WHERE ${table(o.fromState,'output')}.status <> 'completed'`);
    },
  };
}
