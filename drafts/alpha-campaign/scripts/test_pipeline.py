"""Offline check: parent + per-person child graphs end to end with a fake Deepline CLI. Run: python3 test_pipeline.py"""
import json, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
import graph_runner
from build import parent, child
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'references'))
from pipeline import reconcile

DIMS = ['fit', 'proof', 'insight', 'usefulness']
TODAY = time.strftime('%Y-%m-%d')
OFFER = 'We implement outbound research workflows for revenue teams.'
CTA = 'Would a short walkthrough be useful?'
PEOPLE = [('Mira Example', 'northstar.example', 'mira@northstar.example', 'valid'),
          ('Rowan Example', 'harbor.example', 'rowan@harbor.example', 'catch-all'),
          ('Avery Example', 'summit.example', None, None)]


def fake(tool, payload):
    if tool == 'findymail_find_from_name':
        email = next(p[2] for p in PEOPLE if p[0] == payload['name'])
        if not email: raise RuntimeError('findymail_find_from_name: not found')
        return {'contact': {'email': email, 'domain': payload['domain'], 'name': payload['name']}}
    if tool == 'zerobounce_validate':
        status = next(p[3] for p in PEOPLE if p[2] == payload['email'])
        return {'address': payload['email'], 'status': status, 'sub_status': '', 'free_email': 'false'}
    assert tool == 'deeplineagent' and '{{' not in payload['prompt'], tool
    props = payload['jsonSchema']['properties']
    if 'qualification_contract' in props:
        obj = {k: '' for k in props} | {f'{d}_weight': 0.25 for d in DIMS} | {
            'allowed_entity_types': 'person', 'learning_lanes': 'ops,leader,builder', 'search_queries': 'a\nb\nc'}
    elif 'candidates_json' in props:
        obj = {'candidates_json': json.dumps([{'name': n, 'first_name': n.split()[0], 'company_name': d.split('.')[0].title(), 'role': 'RevOps lead',
               'entity_type': 'person', 'domain': d, 'profile_url': 'https://www.linkedin.com/in/' + n.split()[0].lower()} for n, d, *_ in PEOPLE]),
               'discovery_notes': 'fake'}
    elif 'fit_claim' in props:
        item = json.loads(payload['prompt'].split('CANDIDATE: ', 1)[1].split('\n', 1)[0])
        obj = {k: '' for k in props} | {'candidate_id': item['candidate_id'], 'name': item['name'], 'entity_type': 'person',
               'domain': item['domain'], 'lane': 'ops', 'identity_confirmed': True, 'identity_url': item['profile_url'], 'disqualifiers': 'NONE'}
        for d in DIMS:
            obj |= {f'{d}_claim': d, f'{d}_url': f'https://{item["domain"]}/{d}', f'{d}_source_type': 'primary',
                    f'{d}_strength': 4, f'{d}_attributed': True}
    elif 'verified_ids' in props:
        cid = payload['prompt'].split('"candidate_id": "', 1)[1].split('"', 1)[0]
        obj = {'candidate_id': cid, 'identity_verified': True, 'verified_ids': 'fit' if 'avery' in cid else ','.join(DIMS),
               'rejected_ids': '', 'contradicted_ids': '', 'reason': '', 'missing_proof': '', 'checked_urls': ''}
    else:  # Alpha Copy agents
        obj = {k: {'boolean': True, 'number': 4, 'integer': 4}.get(v['type'], '') for k, v in props.items()}
        for k in ('contradiction', 'works_without_signal'):
            if k in obj: obj[k] = False
        obj.update({k: v for k, v in {'mode': 'dated_event', 'event_date': TODAY, 'observation': 'Northstar launched an enterprise plan.',
                    'current_url': 'https://northstar.example/news', 'identity_url': 'https://northstar.example', 'current_excerpt': 'enterprise plan',
                    'selected_capability': OFFER, 'subject': 'Enterprise plan', 'implication': 'That could make account selection more specific.',
                    'cta': CTA, 'temporal_basis': 'Dated announcement', 'checked_urls': 'https://northstar.example/news'}.items() if k in obj})
    return {'extracted_json': obj, 'meta': {'totalCostUsd': 0.01}}


class Ctx:
    def __init__(self, v): self.v = v
    def get_input(self, k): return self.v.get(k)


if __name__ == '__main__':
    graph_runner.deepline = fake
    brief = {'offer': OFFER, 'icp': 'B2B software', 'sender_name': 'Alex', 'greeting': 'Hi {{first_name}},', 'cta': CTA}
    out, _ = graph_runner.execute(parent(), {'brief_json': json.dumps(brief), 'audience_brief': 'RevOps leaders', 'max_people': 3,
                                             'batch_id': 't', 'memory_json': '', 'feedback_json': ''}, log=lambda *_: None)
    d = out['dispatch']
    assert d['dispatch_count'] == 2 and [h['status'] for h in d['held']] == ['QUALIFICATION_HELD'], d
    results = []
    for e in d['entries']:
        o, _ = graph_runner.execute(child(), e['inputs'], log=lambda *_: None)
        results.append(next(o[k] for k in ['finish_deliver', 'finish_hold', 'no_email', 'bad_email'] if k in o))
    ledger = reconcile(Ctx({'dispatch': d, 'results': results}))
    assert ledger['counts'] == {'QUALIFICATION_HELD': 1, 'DRAFT_READY_FOR_REVIEW': 1, 'EMAIL_HELD': 1}, ledger['counts']
    ready = next(p for p in ledger['people'] if p['status'] == 'DRAFT_READY_FOR_REVIEW')
    assert ready['email'] == 'mira@northstar.example' and ready['body'].startswith('Hi Mira,') and ready['sent'] is False
    print('ok', ledger['counts'])
