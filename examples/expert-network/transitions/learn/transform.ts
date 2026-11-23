import type { Payload, Result } from './types';
export function transform(p: Payload): Result {
  const events = p.usage.filter(u => u.taskId === p.task.taskId && u.worldId === p.task.worldId);
  const acceptedUses = events.reduce((n, u) => n + u.acceptedUses, 0);
  const abandonmentCount = events.reduce((n, u) => n + u.abandonmentCount, 0);
  return { nextState: 'complete', reason: events.length ? 'Accepted work joined to observed synthetic usage, with source event IDs' : 'Accepted work recorded; usage evidence unavailable', action: events.length ? 'Relationship owner: review feedback and discuss the next matching brief' : 'Data ops: instrument task usage before inferring usefulness', facts: { specialty: p.expert.specialty, taskId: p.task.taskId, worldId: p.task.worldId, qualityScore: p.task.qualityScore, revisions: p.task.revisions, acceptedUses: events.length ? acceptedUses : null, abandonmentCount: events.length ? abandonmentCount : null, feedback: events.map(u => u.feedback), eventIds: events.map(u => u.eventId), availableHours: p.expert.availabilityHours, reputationScore: null, paymentExecuted: false } };
}
