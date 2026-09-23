import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import tuning

ROOT = Path(__file__).resolve().parents[1]

def path(id='a', value=0):
    return dict(id=id, target_id='t', target_name='Target', connector_id=id,
                connector_name=id, baseline_score=10, review_status='needs_confirmation',
                features={'investor_portfolio': dict(value=value, evidence_ids=['e1'] if value else [],
                          explanation='Documented portfolio connection', timing_status='not_applicable')})

class TuningTests(unittest.TestCase):
    def test_portfolio_can_be_prioritized_without_clearing_hold(self):
        a=path('a',1); b=path('b'); b['features']['direct_intro']=dict(value=1,evidence_ids=['intro'],explanation='Recorded intro',timing_status='not_applicable')
        data={'as_of':'2026-09-23','paths':[a,b]}; original=copy.deepcopy(data)
        self.assertEqual(tuning.rank(data)[0]['id'],'b')
        ranked=tuning.rank(data,{'investor_portfolio':300})
        self.assertEqual(ranked[0]['id'],'a')
        self.assertEqual(ranked[0]['review_status'],'needs_confirmation')
        self.assertFalse(ranked[0]['ready_for_human_review'])
        self.assertEqual(data,original)
    def test_bad_weights(self):
        for weights in ({'nope':1},{'appearance':-1},{'appearance':float('nan')},{'appearance':float('inf')},{'appearance':True}):
            with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[path()]},weights)
    def test_missing_features_are_unknown_zero(self):
        row=tuning.rank({'as_of':'2026-09-23','paths':[path()]})[0]
        self.assertEqual(row['features']['school_overlap']['timing_status'],'unknown')
        self.assertEqual(row['features']['school_overlap']['value'],0)
    def test_positive_requires_citation_and_timed_overlap(self):
        for key in ('work_overlap','school_overlap','board_overlap'):
            p=path(); p['features'][key]=dict(value=1,evidence_ids=['e'],explanation='Shared tenure',timing_status='verified_overlap')
            with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
            p['features'][key].update(overlap_start='2020-01-01',overlap_end='2021-01-01')
            self.assertGreater(tuning.rank({'as_of':'2026-09-23','paths':[p]})[0]['tuned_score'],0)
            p['features'][key]['timing_status']='unknown'
            with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
        p=path('a',1);p['features']['investor_portfolio']['evidence_ids']=[]
        with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
    def test_invalid_feature_and_dates(self):
        for value in (-1,1.01,float('nan'),True):
            p=path('a',value)
            with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
        p=path();p['features']['unknown_key']={}
        with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
        p=path();p['features']['work_overlap']=dict(value=1,evidence_ids=['e'],explanation='tenure',timing_status='verified_overlap',overlap_start='2021',overlap_end='2022')
        with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
    def test_no_status_promoted_and_duplicate_rejected(self):
        for status in ('blocked_declined','needs_confirmation','ready_for_human_review'):
            p=path('a',1);p['review_status']=status
            row=tuning.rank({'as_of':'2026-09-23','paths':[p]},{'investor_portfolio':500})[0]
            self.assertEqual(row['ready_for_human_review'],status=='ready_for_human_review')
        with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[path(),path()]})
    def test_cutoff_is_required_exact_and_preserved(self):
        for cutoff in (None, '2026', '20260923', '2026-02-30', 2026):
            data={'paths':[path()]}
            if cutoff is not None: data['as_of']=cutoff
            with self.assertRaises(ValueError): tuning.rank(data)
        html=tuning.render({'as_of':'2026-09-23','paths':[path()]})
        self.assertIn('"as_of": "2026-09-23"',html)
    def test_overlap_cannot_extend_after_cutoff(self):
        for key in ('work_overlap','school_overlap','board_overlap'):
            p=path();p['features'][key]=dict(value=1,evidence_ids=['e'],explanation='tenure',timing_status='verified_overlap',overlap_start='2020-01-01',overlap_end='2026-09-24')
            with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
            p['features'][key]['overlap_end']='2026-09-23'
            self.assertGreater(tuning.rank({'as_of':'2026-09-23','paths':[p]})[0]['tuned_score'],0)
    def test_self_pair_duplicate_pair_and_unknown_status_rejected(self):
        p=path();p['connector_id']=p['target_id']
        with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
        a=path();b=copy.deepcopy(a);b['id']='distinct-path-id'
        with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[a,b]})
        p=path();p['review_status']='unknown'
        with self.assertRaises(ValueError): tuning.rank({'as_of':'2026-09-23','paths':[p]})
    def test_safe_render_and_private_cli(self):
        p=path();p['connector_name']='</script><img src=x onerror=alert(1)>'
        html=tuning.render({'as_of':'2026-09-23','paths':[p]})
        self.assertNotIn(p['connector_name'],html)
        self.assertIn('\\u003c/script',html)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.json'; dest=Path(tmp)/'review.html'
            source.write_text(json.dumps({'as_of':'2026-09-23','paths':[p]}))
            subprocess.run([sys.executable,str(ROOT/'scripts/tuning.py'),str(source),'--output',str(dest)],check=True,capture_output=True)
            self.assertEqual(dest.stat().st_mode & 0o777,0o600)
            self.assertNotEqual(subprocess.run([sys.executable,str(ROOT/'scripts/tuning.py'),str(source),'--output',str(dest)],capture_output=True).returncode,0)
