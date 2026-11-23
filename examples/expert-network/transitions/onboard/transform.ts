import type { Payload, Result } from './types';
export function transform(p: Payload): Result {
  const e = p.expert;
  const missing = [!e.conflictsCleared && 'conflicts review', !e.agreementSigned && 'agreement', !e.trainingComplete && 'orientation', e.availabilityHours <= 0 && 'availability'].filter(Boolean);
  return { nextState: missing.length ? 'waiting' : 'match', reason: missing.length ? `Missing: ${missing.join(', ')}` : 'Recorded onboarding prerequisites complete', action: missing.length ? 'Expert ops: collect outstanding prerequisites' : 'Project lead: select a task within confirmed capacity', facts: { missing, availabilityHours: e.availabilityHours } };
}
