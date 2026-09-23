"""Fictional evaluator regression tests; run: python3 -m unittest discover -s scripts."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import evaluate


def fixture():
    return {
        'as_of': '2026-09-01T00:00:00Z', 'bootstrap_samples': 200, 'seed': 7,
        'queries': [{
            'id': '<fictional>', 'scored_at': '2026-08-15T00:00:00Z', 'target_id': 'target-a', 'account_id': 'account-a',
            'labels': {'a': 1, 'b': 0, 'c': 0, 'd': 1},
            'baseline': ['b', 'c', 'd', 'a'], 'candidate': ['a', 'd', 'b', 'c'],
            'paths': [dict(id=i, status='ready', sender_edge='strong', target_edge='medium',
                           willingness='yes', feature_dates=['2026-08-01T00:00:00Z'])
                      for i in 'abcd'],
        }],
    }


class EvaluationTests(unittest.TestCase):
    def test_html_has_readable_metric_table_and_verdict(self):
        from html.parser import HTMLParser
        class Cells(HTMLParser):
            def __init__(self):
                super().__init__(); self.tags=[]
            def handle_starttag(self, tag, attrs): self.tags.append(tag)
        report=evaluate.evaluate(fixture())
        page=evaluate.html_report(report)
        parsed=Cells(); parsed.feed(page)
        self.assertGreaterEqual(parsed.tags.count('td'), 12)
        self.assertGreaterEqual(parsed.tags.count('th'), 4)
        self.assertIn('Insufficient evidence', page)

    def test_explicit_null_split_is_invalid(self):
        data=fixture(); data['split']=None
        with self.assertRaises(ValueError): evaluate.evaluate(data)

    def test_known_metrics_and_repeatable_paired_bootstrap(self):
        data = fixture()
        report = evaluate.evaluate(data)
        self.assertEqual(report, evaluate.evaluate(data))
        self.assertEqual(report['metrics']['recall@3']['baseline'], .5)
        self.assertEqual(report['metrics']['recall@3']['candidate'], 1)
        self.assertAlmostEqual(report['metrics']['mrr']['delta'], 2/3)
        expected = 1 - .5 / (1 + 1/math.log2(3))
        self.assertAlmostEqual(report['metrics']['ndcg@3']['delta'], expected)
        self.assertEqual(report['metrics']['recall@3']['delta_ci95'], [.5, .5])
        self.assertIn('not proven uplift', ' '.join(report['warnings']))

    def test_account_cluster_bootstrap_and_independent_count(self):
        data=fixture()
        extra=copy.deepcopy(data['queries'][0]); extra['id']='second-query'
        extra['target_id']='target-b'
        extra['baseline'],extra['candidate']=extra['candidate'],extra['baseline']
        data['queries'].append(extra)
        report=evaluate.evaluate(data)
        self.assertEqual(report['bootstrap']['unit'], 'account')
        self.assertEqual(report['coverage']['independent_accounts'], 1)
        self.assertEqual(report['metrics']['recall@3']['delta_ci95'], [0, 0])
        self.assertEqual(report['status'], 'insufficient_evidence')

    def test_exclusions_and_coverage(self):
        data = fixture()
        missing = copy.deepcopy(data['queries'][0]); missing['id'] = 'missing'
        missing['labels']['b'] = None
        zero = copy.deepcopy(data['queries'][0]); zero['id'] = 'zero'
        zero['labels'] = dict.fromkeys('abcd', 0)
        data['queries'] += [missing, zero]
        report = evaluate.evaluate(data)
        self.assertEqual(report['coverage']['total_queries'], 3)
        self.assertEqual(report['coverage']['eligible_queries'], 1)
        self.assertEqual(report['coverage']['judged_labels'], 11)
        self.assertEqual(report['coverage']['total_labels'], 12)
        self.assertEqual(report['coverage']['exclusions'], {'incomplete_judgments': 1, 'no_relevant': 1})
        data['queries'] = [missing]
        self.assertIsNone(evaluate.evaluate(data)['metrics']['mrr']['delta'])

    def test_fail_closed_inputs(self):
        mutations = [
            lambda d: d['queries'][0]['candidate'].pop(),
            lambda d: d['queries'][0]['candidate'].__setitem__(0, 'd'),
            lambda d: d['queries'][0]['labels'].__setitem__('a', True),
            lambda d: d['queries'][0]['paths'][0].__setitem__('status', 'shipped'),
            lambda d: d['queries'][0]['paths'][0].pop('feature_dates'),
            lambda d: d.__setitem__('seed', float('nan')),
            lambda d: d.__setitem__('as_of', '2026-09-01'),
            lambda d: d.__setitem__('outcomes', [{'id':'o','status':'sent','outcome':'mystery'}]),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data = fixture(); mutation(data)
                with self.assertRaises(ValueError): evaluate.evaluate(data)

    def test_leakage_and_ready_gates(self):
        mutations = [
            lambda d: d['queries'][0]['paths'][0].__setitem__('feature_dates', ['2026-09-02T00:00:00Z']),
            lambda d: d['queries'][0]['paths'][0].__setitem__('sender_edge', 'weak'),
            lambda d: d['queries'][0]['paths'][0].__setitem__('target_edge', 'unknown'),
            lambda d: d['queries'][0]['paths'][0].__setitem__('willingness', 'unknown'),
            lambda d: d.__setitem__('split', dict(train_target_ids=['target-a'],test_target_ids=['target-a'],train_account_ids=[],test_account_ids=['account-a'])),
            lambda d: d.__setitem__('split', dict(train_target_ids=[],test_target_ids=['target-a'],train_account_ids=['account-a'],test_account_ids=['account-a'])),
        ]
        for mutation in mutations:
            data=fixture(); mutation(data)
            with self.assertRaises(ValueError): evaluate.evaluate(data)

    def test_outcomes_matured_sent_only(self):
        data=fixture()
        def event(i, status='sent', reply=True, meeting=False, sent='2026-08-01T00:00:00Z', through='2026-09-01T00:00:00Z'):
            value=dict(id=i,status=status,created_at='2026-07-30T00:00:00Z',reply=reply,meeting=meeting)
            if status=='sent': value.update(sent_at=sent, observed_through=through)
            if reply is True: value['reply_at']=sent
            if meeting is True: value['meeting_at']=sent
            return value
        data['outcomes']=[event('reply'), event('meeting',meeting=True),
                          event('none',reply=False), event('draft',status='draft',reply=None,meeting=None),
                          event('unknown',reply=None,meeting=None),
                          event('pending',sent='2026-08-30T00:00:00Z')]
        out=evaluate.evaluate(data)['outcomes']
        self.assertEqual(out['matured_sent_denominator'],3)
        self.assertEqual(out['reply_rate'],2/3)
        self.assertEqual(out['meeting_rate'],1/3)
        self.assertEqual(out['drafts'],1)
        self.assertEqual(out['sent_unobserved'],1)
        self.assertEqual(out['sent_immature'],1)
        data['outcomes'][0].pop('reply_at')
        with self.assertRaises(ValueError): evaluate.evaluate(data)

    def test_late_events_do_not_inflate_fixed_window_rates(self):
        data=fixture()
        data['outcomes']=[dict(id='late',status='sent',created_at='2026-07-01T00:00:00Z',
            sent_at='2026-07-01T00:00:00Z',observed_through='2026-09-01T00:00:00Z',
            reply=True,meeting=True,reply_at='2026-08-15T00:00:00Z',meeting_at='2026-08-16T00:00:00Z')]
        out=evaluate.evaluate(data)['outcomes']
        self.assertEqual(out['matured_sent_denominator'],1)
        self.assertEqual(out['reply_rate'],0)
        self.assertEqual(out['meeting_rate'],0)
        self.assertEqual(out['raw_reply_events'],1)

    def test_split_requires_all_evaluated_groups_in_test(self):
        data=fixture()
        data['split']=dict(train_target_ids=['target-a'],test_target_ids=['different'],
                           train_account_ids=[],test_account_ids=['account-a'])
        with self.assertRaises(ValueError): evaluate.evaluate(data)

    def test_features_cannot_leak_between_scoring_and_evaluation(self):
        data=fixture()
        data['queries'][0]['paths'][0]['feature_dates']=['2026-08-20T00:00:00Z']
        with self.assertRaises(ValueError): evaluate.evaluate(data)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError): evaluate.loads('{"queries": [], "queries": []}')
        with self.assertRaises(ValueError): evaluate.loads('{"seed": NaN}')

    def test_cli_private_no_overwrite_and_escaped_html(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'input.json'; output=root/'report.json'; page=root/'report.html'
            source.write_text(json.dumps(fixture()))
            command=[sys.executable, str(Path(evaluate.__file__)), str(source), '--output', str(output), '--html', str(page)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(page.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('<fictional>',page.read_text())
            self.assertIn('&lt;fictional&gt;',page.read_text())
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)


if __name__ == '__main__': unittest.main()
