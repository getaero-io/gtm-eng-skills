import type { Payload, Result } from './types';
export function transform(p: Payload): Result {
  const e = p.expert, t = p.task;
  const ready = e.vertical === t.vertical && e.specialty === t.specialty && e.availabilityHours >= t.hours && t.assignmentApproved && Boolean(t.brief && t.rubric && t.referenceAnswer);
  return { nextState: ready ? 'review' : 'waiting', reason: ready ? 'Approved task matches specialty and capacity; brief and rubric present' : 'Task match, capacity, brief, or assignment approval unresolved', action: ready ? 'Expert: submit the scenario and reference deliverable' : 'Project lead: review task match without automatic reassignment', facts: { taskId: t.taskId, worldId: t.worldId, hours: t.hours, assignmentCreated: false } };
}
