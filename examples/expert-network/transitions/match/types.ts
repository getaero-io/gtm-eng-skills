export const VERSION = 'erm-synthetic-v1';
export const STATES = ['discover', 'qualify', 'recruit', 'onboard', 'match', 'review', 'learn', 'complete', 'waiting', 'declined'] as const;
export type State = typeof STATES[number];
export const TERMINAL: State[] = ['complete', 'waiting', 'declined'];
export const EDGES: Record<State, State[]> = {
  discover: ['qualify', 'waiting'], qualify: ['recruit', 'waiting', 'declined'],
  recruit: ['onboard', 'waiting', 'declined'], onboard: ['match', 'waiting'],
  match: ['review', 'waiting'], review: ['learn', 'waiting'],
  learn: ['complete'], complete: [], waiting: [], declined: [],
};
export type Expert = {
  expertId: string; name: string; vertical: 'law' | 'consulting'; specialty: string;
  sourceRef: string; identityReviewed: boolean; credentialReviewed: boolean;
  qualification: 'approved' | 'rejected' | 'pending';
  response: 'interested' | 'declined' | 'pending';
  consent: boolean; conflictsCleared: boolean; agreementSigned: boolean;
  trainingComplete: boolean; availabilityHours: number;
};
export type Task = {
  taskId: string; worldId: string; vertical: 'law' | 'consulting'; specialty: string;
  brief: string; rubric: string; referenceAnswer: string; hours: number;
  assignmentApproved: boolean; submissionId: string;
  review: 'accepted' | 'revision' | 'pending'; reviewerId: string;
  qualityScore: number | null; revisions: number;
};
export type Usage = { eventId: string; taskId: string; worldId: string; acceptedUses: number; abandonmentCount: number; feedback: string };
export type Payload = { synthetic: true; expert: Expert; task: Task; usage: Usage[] };
export type EngineInput = { episodeId: string; payload: Payload };
export type Result = { nextState: State; reason: string; action: string; facts: Record<string, unknown> };
export type Output = { key: string; expertId: string; episodeId: string; fromState: string; toState: string | null; status: 'completed' | 'failed' | 'invalid'; input: Payload; result: Result | null; error: string | null; play: string; version: string };
export const playName = (state: string) => `erm-${state}-v1`;
export const keyFor = (input: EngineInput, state: string) => JSON.stringify([VERSION, input.payload.expert.expertId, input.episodeId, state]);
export function validatePayload(p: Payload) {
  if (p.synthetic !== true || !p.expert.expertId.startsWith('syn-')) throw new Error('SYNTHETIC_ONLY');
  if (!p.expert.name || !p.task.taskId || !['law', 'consulting'].includes(p.expert.vertical)) throw new Error('INVALID_IDENTITY');
  if (!Number.isFinite(p.expert.availabilityHours) || p.expert.availabilityHours < 0 || !Number.isFinite(p.task.hours) || p.task.hours <= 0) throw new Error('INVALID_HOURS');
  if (!['approved', 'rejected', 'pending'].includes(p.expert.qualification) || !['interested', 'declined', 'pending'].includes(p.expert.response) || !['accepted', 'revision', 'pending'].includes(p.task.review)) throw new Error('INVALID_DECISION');
  if (new Set(p.usage.map(x => x.eventId)).size !== p.usage.length) throw new Error('DUPLICATE_USAGE_EVENT');
  for (const u of p.usage) if (!Number.isInteger(u.acceptedUses) || u.acceptedUses < 0 || !Number.isInteger(u.abandonmentCount) || u.abandonmentCount < 0) throw new Error('INVALID_USAGE');
}
