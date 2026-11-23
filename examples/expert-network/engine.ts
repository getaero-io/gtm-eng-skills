import { EDGES, STATES, TERMINAL, VERSION, keyFor, playName, validatePayload, type EngineInput, type Output, type Result, type State } from './types';
export interface Store {
  accept(input: EngineInput): Promise<void>;
  input(input: EngineInput, state: State, prior: string | null): Promise<void>;
  read(key: string, state: string): Promise<Output | null>;
  save(output: Output): Promise<void>;
}
export async function advance(input: EngineInput, store: Store, dispatch: (state: State, input: EngineInput) => Promise<Result>, initial: string = 'discover') {
  validatePayload(input.payload);
  if (!input.episodeId || input.episodeId.length > 100) throw new Error('INVALID_EPISODE');
  await store.accept(input);
  let state = initial as State;
  let prior: string | null = null;
  let replayed = 0;
  let last: Result | null = null;
  for (let hop = 0; hop < 12; hop++) {
    const known = STATES.includes(state);
    const key = keyFor(input, state);
    if (known) await store.input(input, state, prior);
    const base: Output = { key, expertId: input.payload.expert.expertId, episodeId: input.episodeId, fromState: state, toState: null, status: 'failed', input: input.payload, result: null, error: null, play: playName(state), version: VERSION };
    if (!known) {
      await store.save({ ...base, status: 'invalid', error: 'UNKNOWN_STATE' });
      throw new Error('UNKNOWN_STATE');
    }
    if (TERMINAL.includes(state)) {
      await store.save({ ...base, status: 'completed', result: last });
      return { expert: input.payload.expert.name, expertId: input.payload.expert.expertId, state, reason: last?.reason ?? 'Terminal episode', recommendedAction: last?.action ?? 'None', facts: last?.facts ?? {}, synthetic: true, replayedTransitions: replayed };
    }
    const saved = await store.read(key, state);
    let result: Result;
    if (saved?.status === 'completed' && saved.result) { result = saved.result; replayed++; }
    else {
      try {
        result = await dispatch(state, input);
        if (!result || !EDGES[state].includes(result.nextState) || typeof result.reason !== 'string' || typeof result.action !== 'string' || !result.facts || typeof result.facts !== 'object') throw new Error('INVALID_CHILD_RESULT');
      } catch (error) {
        const code = error instanceof Error ? error.message : 'CHILD_FAILURE';
        await store.save({ ...base, status: code === 'INVALID_CHILD_RESULT' ? 'invalid' : 'failed', error: code });
        throw error;
      }
      await store.save({ ...base, status: 'completed', toState: result.nextState, result });
    }
    // Handoff is repaired from the saved output on replay, even after an interrupted write.
    await store.input(input, result.nextState, key);
    prior = key; state = result.nextState; last = result;
  }
  throw new Error('HOP_LIMIT');
}
