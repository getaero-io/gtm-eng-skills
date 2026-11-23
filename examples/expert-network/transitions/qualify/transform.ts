import type { Payload, Result } from './types';
export function transform(p: Payload): Result {
  const e = p.expert;
  const nextState = e.qualification === 'rejected' ? 'declined' : e.qualification === 'approved' && e.credentialReviewed ? 'recruit' : 'waiting';
  return { nextState, reason: `Reviewer qualification: ${e.qualification}; credential review: ${e.credentialReviewed}`, action: nextState === 'recruit' ? 'Recruiter: prepare a relevant invitation for approval' : 'Domain lead: resolve qualification evidence', facts: { vertical: e.vertical, specialty: e.specialty, qualification: e.qualification } };
}
