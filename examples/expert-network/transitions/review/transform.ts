import type { Payload, Result } from './types';
export function transform(p: Payload): Result {
  const t = p.task;
  const accepted = Boolean(t.submissionId && t.reviewerId) && t.review === 'accepted';
  return { nextState: accepted ? 'learn' : 'waiting', reason: accepted ? 'Human reviewer accepted the submitted artifact' : `Submission review: ${t.review}`, action: accepted ? 'Data ops: join usage evidence to this accepted task' : t.review === 'revision' ? 'Expert and reviewer: clarify rubric and revise artifact' : 'Reviewer: assess submitted work against rubric', facts: { taskId: t.taskId, submissionId: t.submissionId, qualityScore: t.qualityScore, revisions: t.revisions, reviewerId: t.reviewerId } };
}
