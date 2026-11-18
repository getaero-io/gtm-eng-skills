"""Offline check: run the packaged blueprint end to end with a fake Deepline CLI. Run: python3 test_graph_runner.py"""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
import graph_runner

ROOT = Path(__file__).resolve().parents[1]
DIMS = ['fit', 'proof', 'insight', 'usefulness']


def fake(tool, payload):
    assert tool == 'deeplineagent' and payload['model'] == 'openai/gpt-5.4'
    assert '{{' not in payload['prompt'], 'unrendered template variable'
    props = payload['jsonSchema']['properties']
    if 'qualification_contract' in props:
        obj = {k: '' for k in props} | {f'{d}_weight': 0.25 for d in DIMS} | {
            'allowed_entity_types': 'person,agency', 'learning_lanes': 'builder,educator,agency',
            'search_queries': 'a\nb\nc'}
    elif 'candidates_json' in props:
        obj = {'candidates_json': json.dumps([
            {'name': 'Mira Example', 'entity_type': 'person', 'domain': 'mira.example', 'profile_url': 'https://mira.example/about'},
            {'name': 'Northwind Lab', 'entity_type': 'agency', 'domain': 'northwind.example', 'profile_url': 'https://northwind.example'}]),
            'discovery_notes': 'fake'}
    elif 'fit_claim' in props:
        item = json.loads(payload['prompt'].split('CANDIDATE: ', 1)[1].split('\n', 1)[0])
        obj = {k: '' for k in props} | {'candidate_id': item['candidate_id'], 'name': item['name'], 'entity_type': item['entity_type'],
               'domain': item['domain'], 'lane': 'builder', 'identity_confirmed': True, 'identity_url': item['profile_url'], 'disqualifiers': 'NONE'}
        for i, d in enumerate(DIMS):
            obj |= {f'{d}_claim': d + ' claim', f'{d}_url': f'https://{item["domain"]}/{d}', f'{d}_source_type': 'primary',
                    f'{d}_strength': 4, f'{d}_attributed': True, f'{d}_date': ''}
    elif 'verified_ids' in props:
        cid = payload['prompt'].split('"candidate_id": "', 1)[1].split('"', 1)[0]
        weak = cid.startswith('agency')
        obj = {'candidate_id': cid, 'identity_verified': True, 'verified_ids': 'fit' if weak else ','.join(DIMS),
               'rejected_ids': '', 'contradicted_ids': '', 'reason': '', 'missing_proof': '', 'checked_urls': ''}
    elif 'feature_brief' in props:
        obj = {'feature_brief': 'brief'}
    else:
        raise AssertionError(sorted(props))
    return {'extracted_json': obj, 'meta': {'model': payload['model'], 'totalCostUsd': 0.01}}


def run(memory='', feedback='[]'):
    graph = json.loads((ROOT / 'references/blueprint.json').read_text())
    out, rec = graph_runner.execute(graph, {'focus': 'Find GTM builders', 'memory_json': memory,
                                            'feedback_json': feedback, 'settings_json': '{}'}, log=lambda *_: None)
    return out, rec


if __name__ == '__main__':
    graph_runner.deepline = fake
    out, rec = run()
    score = out['score']
    assert score['researched_count'] == 2 and score['qualified_count'] == 1, score
    assert 'brief' in out and 'hold' not in out and 'empty' not in out
    ranked = json.loads(score['ranking_json'])
    assert ranked[0]['decision'] == 'QUALIFIED_FOR_REVIEW' and ranked[1]['decision'] == 'RESEARCH_REQUIRED'
    assert rec['cost_usd'] > 0
    # Feedback carried through memory moves priority, never the verdict.
    memory = score['memory_json']
    cid = ranked[0]['candidate_id']
    out2, _ = run(memory, json.dumps([{'candidate_id': cid, 'rating': 1, 'feedback_id': 'r1'}]))
    top = json.loads(out2['score']['ranking_json'])[0]
    assert top['learning_bonus'] > 0 and top['score'] == ranked[0]['score'], top
    print('ok')
