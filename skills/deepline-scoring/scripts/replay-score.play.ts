import { definePlay } from 'deepline';
import { scoreRow, artifactKey } from './scoring_contract';
import type { Model, Reference, Observation } from './scoring_contract';

type Input = {
  domain: string;
  scored_at: string;
  snapshot_id: string;
  rows: Array<{
    domain: string;
    entity_id: string;
    observations: Observation[];
  }>;
  model: Model;
  reference: Reference;
};

/** Replay only. Source collection and model fitting are deliberately not fabricated. */
export default definePlay(
  'replay-account-score',
  async (ctx, input: Input) => {
    if (!input.snapshot_id) throw new Error('snapshot_id_required');
    if (
      typeof input.domain !== 'string' ||
      !Array.isArray(input.rows) ||
      input.rows.some((row) => typeof row.domain !== 'string')
    )
      throw new Error('invalid_identity_input');
    const domain = input.domain
      .trim()
      .toLowerCase()
      .replace(/^www\./, '');
    if (
      !/^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}$/.test(domain) ||
      domain.includes('..')
    )
      throw new Error('domain_required');
    const matches = input.rows.filter(
      (row) => row.domain.toLowerCase().replace(/^www\./, '') === domain,
    );
    const result =
      matches.length !== 1
        ? {
            ...scoreRow(
              'unresolved',
              input.scored_at,
              [],
              input.model,
              input.reference,
            ),
            entity_id: null,
            status: matches.length ? 'ambiguous_identity' : 'not_in_snapshot',
            miss_reason: matches.length
              ? 'ambiguous_identity'
              : 'not_in_snapshot',
            candidates: matches.map((row) => row.entity_id),
            score: null,
            grade: null,
          }
        : scoreRow(
            matches[0].entity_id,
            input.scored_at,
            matches[0].observations,
            input.model,
            input.reference,
          );
    const replay_key = artifactKey([
      domain,
      input.snapshot_id,
      input.model,
      input.reference,
      input.scored_at,
      matches,
    ]);
    const rows = await ctx
      .dataset('scored_rows', [
        { domain, replay_key, snapshot_id: input.snapshot_id, ...result },
      ])
      .run({ key: 'replay_key' });
    return { rows, delivery: 'replay_only' };
  },
  { description: 'Replay a frozen account score' },
);
