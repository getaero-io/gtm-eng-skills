import type { Payload, Result } from './types';
export function transform(p: Payload): Result {
  const nextState = p.expert.response === 'declined' ? 'declined' : p.expert.response === 'interested' && p.expert.consent ? 'onboard' : 'waiting';
  return { nextState, reason: `Recorded response: ${p.expert.response}; consent: ${p.expert.consent}`, action: nextState === 'onboard' ? 'Expert ops: start onboarding checklist' : nextState === 'declined' ? 'Do not contact for this opportunity' : 'Recruiter: await response and recorded permission', facts: { sent: false, response: p.expert.response, consent: p.expert.consent } };
}
