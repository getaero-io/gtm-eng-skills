"""Fictional input packaging checks; stdlib only."""
import importlib.util
import json
import csv
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('prepare_inputs', Path(__file__).parents[1] / 'plays/prepare-inputs.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    return dict(as_of='2026-09-23', profiles_checked_at='2026-08-02', requester_name='Example Requester',
                connectors=[dict(id='conn:example', linkedin_url='https://linkedin.com/in/example-connector',
                                 source='fixture:connector', observed_at='2026-08-02', experience=[])],
                profiles=[], targets=[dict(name='Example Target', linkedin_url='https://linkedin.com/in/example-target',
                                          company='Example Company', domain='example.test')])


merge_spec = importlib.util.spec_from_file_location('merge_payloads', Path(__file__).parents[1] / 'plays/merge-payloads.py')
merger = importlib.util.module_from_spec(merge_spec)
merge_spec.loader.exec_module(merger)


class InputPackagingTests(unittest.TestCase):
    def test_preserves_unresolved_targets_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = m.write_inputs(fixture(), Path(tmp) / 'input.csv')[0]
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn('example-target', path.read_text())
            with self.assertRaises(ValueError):
                m.write_inputs(fixture(), path)

    def test_batches_preserve_target_keys(self):
        data = fixture()
        data['targets'] *= 3
        batches = m.batches(data, 2)
        self.assertEqual(len(batches), 2)
        keys = [r['key'] for batch in batches for r in batch if r['section'] == 'targets']
        self.assertEqual(keys, ['target:0', 'target:1', 'target:2'])
        self.assertEqual(json.loads(batches[1][-1]['payload_json'])['target'], data['targets'][2])

    def test_merges_payloads_and_preserves_existing_hold(self):
        payload = dict(as_of='2026-09-23', profiles_checked_at='2026-08-02', requester_name='Example Requester',
                       model='test', weights={}, paths=[dict(id='path:1', target_id='target:1', connector_id='connector:1',
                       review_status='needs_confirmation', features={})], evidence=[])
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'export.csv'
            with source.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=['result']); writer.writeheader()
                writer.writerow({'result': json.dumps({'payload': payload, 'coverage': {'unresolved': []}})})
            previous = {'paths': [dict(payload['paths'][0], review_status='blocked_declined')]}
            self.assertEqual(merger.merge([source], previous)['paths'][0]['review_status'], 'blocked_declined')
            with self.assertRaises(ValueError):
                merger.merge([source, source])

    def test_declines_survive_missing_refresh_and_changed_path_ids(self):
        payload = dict(as_of='2026-09-23', requester_name='Requester', evidence=[], paths=[], model='test', weights={})
        old = dict(id='old', target_id='target', connector_id='connector', review_status='blocked_declined', features={})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'export.csv'
            def write(paths):
                with path.open('w', newline='') as f:
                    writer=csv.DictWriter(f, fieldnames=['result']);writer.writeheader()
                    writer.writerow({'result': json.dumps({'payload': dict(payload, paths=paths)})})
            write([])
            missing = merger.merge([path], {'paths':[old]})
            self.assertEqual(missing['review_state'][0]['review_status'], 'blocked_declined')
            self.assertEqual(len(missing['coverage']['review_states_without_paths']), 1)
            write([dict(old,id='new',review_status='needs_confirmation')])
            restored = merger.merge([path], missing)
            self.assertEqual(restored['paths'][0]['review_status'], 'blocked_declined')
            write([dict(old,review_status='needs_confirmation',features={'x':{'value':0}})])
            prior = {'paths':[dict(old,review_status='ready_for_human_review',features={})]}
            self.assertEqual(merger.merge([path],prior)['paths'][0]['review_status'], 'needs_confirmation')

    def test_missing_target_export_fails_manifest_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'export.csv'
            with path.open('w', newline='') as f:
                writer=csv.DictWriter(f,fieldnames=['key','result']);writer.writeheader()
                writer.writerow({'key':'target:0','result':json.dumps({'payload':{'paths':[],'evidence':[]}})})
            with self.assertRaisesRegex(ValueError,'Missing or unexpected'):
                merger.merge([path], expected_keys=['target:0','target:1'])

    def test_csv_formula_text_is_inert_and_numeric_scores_unchanged(self):
        spec=importlib.util.spec_from_file_location('csv_score', Path(__file__).parents[1]/'scripts/score.py')
        scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
        self.assertEqual(scorer.csv_safe('=HYPERLINK("https://example.test")'), '\'=HYPERLINK("https://example.test")')
        self.assertEqual(scorer.csv_safe('  @formula'), "'  @formula")
        self.assertEqual(scorer.csv_safe(120),120)
        self.assertEqual(scorer.csv_safe('Alex Example'),'Alex Example')

    def test_rejects_bad_shapes_dates_and_record_limits(self):
        data = fixture()
        data['targets'] = 'bad'
        with self.assertRaises(ValueError):
            m.batches(data)
        data = fixture()
        data['connectors'][0]['observed_at'] = '2026-09-24'
        with self.assertRaises(ValueError):
            m.batches(data)
        data = fixture()
        data['targets'] *= 5000
        with self.assertRaises(ValueError):
            m.batches(data)
        self.assertEqual(len(m.batches(data, 1000)), 5)
        with self.assertRaises(ValueError):
            m.batches(fixture(), 0)


if __name__ == '__main__':
    unittest.main()
