"""Offline check: run the packaged copy graph (base and Exa variants) with a fake Deepline CLI. Run: python3 test_graph_runner.py"""
import json, os, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
import graph_runner
from exa import extend

ROOT = Path(__file__).resolve().parents[1]
TODAY = time.strftime('%Y-%m-%d')
OFFER = 'We implement outbound research workflows for revenue teams.'
calls = []


def fake(tool, payload):
    calls.append(tool)
    if tool == 'generic_http_request':
        assert payload['headers']['x-api-key'] == 'test-key' and payload['body_json']['urls']
        url = payload['body_json']['urls'][0]
        past = 'snapshotAsOf' in payload['body_json']
        text = ('Old positioning for small teams only. ' if past else 'New enterprise plan for large revenue teams. ') * 3
        return {'status_code': 200, 'ok': True, 'data': {'requestId': 'r-' + str(past), 'results': [{'url': url, 'title': 'Home', 'text': text}],
                'statuses': [{'id': url, 'status': 'success', 'source': 'cached' if past else 'crawled'}]}}
    assert tool == 'deeplineagent' and '{{' not in payload['prompt']
    props = payload['jsonSchema']['properties']
    obj = {}
    for k, v in props.items():
        obj[k] = {'boolean': True, 'number': 4, 'integer': 4}.get(v['type'], '')
    for k in ('contradiction', 'works_without_signal'):
        if k in obj: obj[k] = False
    obj.update({k: v for k, v in {
        'mode': 'dated_event', 'event_date': TODAY, 'observation': 'Northstar launched an enterprise plan.',
        'current_url': 'https://northstar.example/news', 'identity_url': 'https://northstar.example',
        'current_excerpt': 'launched an enterprise plan', 'selected_capability': OFFER, 'subject': 'Enterprise plan',
        'implication': 'That could make account selection more specific.', 'cta': 'Would a short walkthrough be useful?', 'temporal_basis': 'Dated announcement',
        'checked_urls': 'https://northstar.example/news'}.items() if k in obj})
    return {'extracted_json': obj, 'meta': {'model': payload['model'], 'totalCostUsd': 0.01}}


def run(graph, **extra):
    inputs = {'offer': OFFER, 'icp': 'B2B software', 'company_domain': 'northstar.example', 'company_name': 'Northstar',
              'recipient_name': 'Mira', 'sender_name': 'Alex', 'greeting': 'Hi {{first_name}},', 'cta': 'Would a short walkthrough be useful?',
              'comparison_mode': 'auto', 'source_record_id': 'row-1', **extra}
    out, _ = graph_runner.execute(graph, inputs, log=lambda *_: None)
    final = out.get('deliver') or out.get('hold')
    assert final and final['state'] in ('DRAFT_READY_FOR_REVIEW', 'COPY_REVIEW_REQUIRED', 'RESEARCH_REQUIRED'), out.keys()
    assert final['source_record_id'] == 'row-1' and final['sent'] is False
    return out, final


if __name__ == '__main__':
    graph_runner.deepline = fake
    base = json.loads((ROOT / 'references/blueprint.json').read_text())
    out, final = run(base)
    print('base:', final['state'], final.get('hold_reasons'))
    os.environ['EXA_API_KEY'] = 'test-key'
    calls.clear()
    out, final = run(extend(base), comparison_mode='before_after', comparison_as_of='2025-01-01')
    assert calls.count('generic_http_request') == 2 and out['exa_normalize']['retrieval_state'] == 'EXA_PAIR_RETRIEVED'
    assert 'test-key' not in json.dumps(out), 'secret leaked into node outputs'
    print('exa:', final['state'], final.get('hold_reasons'))
    print('ok')
