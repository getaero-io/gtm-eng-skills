"""Create reproducible synthetic inputs and schema. No network or credentials."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).parent
STATES = ['discover', 'qualify', 'recruit', 'onboard', 'match', 'review', 'learn', 'complete', 'waiting', 'declined', 'invalid']

def main():
    fixtures = ROOT / 'fixtures'
    fixtures.mkdir(exist_ok=True)
    experts, tasks, usages = [], [], []
    for i, (name, vertical, specialty) in enumerate([
        ('Alex Example', 'law', 'commercial_contracts'),
        ('Morgan Example', 'consulting', 'pricing_strategy'),
        ('Taylor Example', 'law', 'employment_law'),
    ], 1):
        expert = dict(expertId=f'syn-expert-{i}', name=name, vertical=vertical, specialty=specialty,
                      sourceRef=f'synthetic://expert-source/{i}', identityReviewed=True, credentialReviewed=True,
                      qualification='approved', response='interested', consent=True, conflictsCleared=True,
                      agreementSigned=True, trainingComplete=True, availabilityHours=6)
        task = dict(taskId=f'syn-task-{i}', worldId=f'syn-world-{vertical}', vertical=vertical, specialty=specialty,
                    brief='Create a fictional contract negotiation with competing renewal terms.' if vertical == 'law' else 'Create a fictional SaaS pricing case with churn and segment constraints.',
                    rubric='Check internal consistency, evidence, alternatives, explicit assumptions, and reproducibility.',
                    referenceAnswer='Synthetic reference: identify constraints, compare two options, justify the selected option.',
                    hours=3, assignmentApproved=True, submissionId=f'syn-submission-{i}', review='revision' if i == 2 else 'accepted',
                    reviewerId='syn-reviewer-1', qualityScore=4 if i != 2 else 2, revisions=1 if i == 2 else 0)
        if i == 3:
            expert['response'] = 'declined'
        usage = dict(eventId=f'syn-event-{i}', taskId=task['taskId'], worldId=task['worldId'], acceptedUses=12,
                     abandonmentCount=2, feedback='Useful branching choices; clarify the evidence available at each step.')
        payload = dict(synthetic=True, expert=expert, task=task, usage=[usage])
        (fixtures / f'pilot-{i}.json').write_text(json.dumps(dict(episodeId='demo-2026-11-19', payload=payload), indent=2)+'\n')
        experts.append(expert); tasks.append(task); usages.append(usage)
    for name, rows in [('experts.csv', experts), ('tasks.csv', tasks), ('world_model_usage_data.csv', usages)]:
        with (fixtures / name).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
        with (fixtures / name).open(newline='') as f:
            assert len(list(csv.DictReader(f))) == 3
    statements = ['CREATE TABLE IF NOT EXISTS storage.erm_v1_episodes (id text PRIMARY KEY, payload jsonb NOT NULL, received_at timestamptz NOT NULL DEFAULT now())']
    for state in STATES:
        statements.append(f'''CREATE TABLE IF NOT EXISTS storage.erm_v1_{state}_input (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, state text NOT NULL,
 payload jsonb NOT NULL, prior_transition text, workflow_version text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now())''')
        statements.append(f'''CREATE TABLE IF NOT EXISTS storage.erm_v1_{state}_output (
 id text PRIMARY KEY, expert_id text NOT NULL, episode_id text NOT NULL, from_state text NOT NULL,
 to_state text, status text NOT NULL CHECK(status IN ('completed','failed','invalid')), record jsonb NOT NULL,
 workflow_version text NOT NULL, transition_play text NOT NULL, transition_version text NOT NULL,
 processed_at timestamptz NOT NULL DEFAULT now())''')
    (ROOT / 'schema.sql').write_text(';\n\n'.join(statements)+';\n')
    for state in STATES[:7]:
        (ROOT / 'transitions' / state / 'types.ts').write_text((ROOT / 'types.ts').read_text())
        (ROOT / 'transitions' / state / f'erm-{state}.play.ts').write_text(f'''import deepline from 'deepline';
import {{ validatePayload, type Payload }} from './types';
import {{ transform }} from './transform';
/** @mermaid
 * flowchart TD
 *   decide[Evaluate {state} evidence] --> outcome[Return next state and action]
 */
export const config = {{ name: 'erm-{state}-v1', description: 'Evaluate synthetic {state} evidence without external actions.', billing: {{ maxCreditsPerRun: 1 }} }};
export default async function (input: {{ payload: Payload }}) {{
  validatePayload(input.payload);
  // @mermaid-node decide
  const result = transform(input.payload);
  // @mermaid-node outcome in:"result" out:"$output"
  return result;
}}
''')
    print('Created 3 synthetic CSVs, 3 pilot inputs, 23 table definitions and 7 child Plays.')

if __name__ == '__main__':
    main()
