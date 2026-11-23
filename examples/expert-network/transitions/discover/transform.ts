import type { Payload, Result } from './types';
export function transform(p: Payload): Result {
  const ready = Boolean(p.expert.sourceRef) && p.expert.identityReviewed;
  return { nextState: ready ? 'qualify' : 'waiting', reason: ready ? 'Source and identity review recorded' : 'Identity evidence needs review', action: ready ? 'Review specialty and credential evidence' : 'Research ops: resolve identity before recruiting', facts: { sourceRef: p.expert.sourceRef, specialty: p.expert.specialty } };
}
