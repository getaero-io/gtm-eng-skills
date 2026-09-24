"""Regression cases from historical asks. Fixtures are fictional; no calls."""
import importlib.util
from pathlib import Path
import unittest
from check import fixture
from score import score

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ask_contract', ROOT / 'vendor/examples/office-hours/warm-intro-ask-threads/draft_asks.py')
asks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asks)


class AskHandoff(unittest.TestCase):
    def test_decline_blocks_even_with_override(self):
        data = fixture()
        data['evidence'].append(dict(id='later-decline', kind='willingness',
            subjects=['owner', 'connector', 'target'], source='fixture:decline',
            detail='Declined', observed_at='2026-09-02', value='no'))
        row = score(data, ROOT / 'vendor')[0]
        self.assertGreater(row['total_score'], 0)
        self.assertEqual(row['review_status'], 'blocked_declined')
        row['reviewed_override'] = 'true'
        self.assertEqual(asks.draft_asks([row], '', None, 'unused', False, True), [])

    def test_missing_target_edge_cannot_draft(self):
        data = fixture()
        data['paths'][0].update(target_relationship_confidence='unknown', target_relationship_evidence_ids=[])
        row = score(data, ROOT / 'vendor')[0]
        self.assertEqual(asks.draft_asks([row], '', None, 'unused', False), [])

    def test_weak_signals_do_not_claim_access(self):
        for signal in ['investor_overlap', 'role_industry', 'school_city_community']:
            with self.subTest(signal=signal):
                text = asks.build_signal_description(dict(shared_signal=signal, shared_detail='Fictional shared context'))
                self.assertIn('does not establish that they know each other', text)

    def test_wrong_identity_rejected_before_drafting(self):
        row = score(fixture(), ROOT / 'vendor')[0]
        row['target_id'] = 'different-target'
        with self.assertRaisesRegex(ValueError, 'identity'):
            asks.draft_asks([row], '', None, 'unused', False)


if __name__ == '__main__':
    unittest.main()
