import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import quality

ROOT=Path(__file__).resolve().parents[1]
def fixture(): return json.loads((ROOT/'assets/example.json').read_text())
class QualityTests(unittest.TestCase):
    def test_supported_fixture_passes_with_coverage(self):
        report=quality.audit(fixture())
        self.assertEqual(report['status'],'pass')
        self.assertGreater(report['coverage']['unique_contacts'],0)
        self.assertEqual(report['errors'],[])
    def test_same_profile_cannot_be_two_people(self):
        data=fixture();p=data['paths'][0];p['connector']['linkedin_url']=p['target']['linkedin_url']
        self.assertIn('profile_identity_collision',[x['code'] for x in quality.audit(data)['errors']])
    def test_one_id_cannot_change_profile_between_paths(self):
        data=fixture();p=copy.deepcopy(data['paths'][0]);p['target']['linkedin_url']='https://example.com/in/different';data['paths'].append(p)
        self.assertIn('contact_identity_conflict',[x['code'] for x in quality.audit(data)['errors']])
    def test_missing_features_are_unknown_and_counted(self):
        data=fixture()
        for p in data['paths']:
            for role in ('connector','target'):
                p[role].pop('current_company',None);p[role].pop('current_position',None);p.pop(role+'_experiences',None)
        report=quality.audit(data)
        self.assertGreater(report['coverage']['contacts_without_job_history'],0)
        self.assertIn('missing_job_history',[x['code'] for x in report['warnings']])
    def test_stale_and_duplicate_source_receipts_warn(self):
        data=fixture();e=copy.deepcopy(data['evidence'][0]);e['id']='duplicate-source';data['evidence'].append(e)
        report=quality.audit(data,max_age_days=1)
        self.assertIn('duplicate_source_receipt',[x['code'] for x in report['warnings']])
        self.assertIn('stale_evidence',[x['code'] for x in report['warnings']])
    def test_invalid_foreign_reference_is_error(self):
        data=fixture();data['paths'][0]['direct_intro_evidence_ids']=['missing']
        self.assertEqual(quality.audit(data)['status'],'fail')
    def test_future_end_date_rejected_without_start(self):
        data=fixture();p=data['paths'][0]['connector_experiences'][0];p['start_date']=None;p['end_date']='2099-01-01'
        self.assertIn('future_employment_end',[x['code'] for x in quality.audit(data)['errors']])
    def test_empty_input_is_not_success(self):
        data=fixture();data['paths']=[]
        self.assertEqual(quality.audit(data)['status'],'fail')
    def test_cli_bad_quality_exits_nonzero_and_writes_private_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);data=fixture();data['paths']=[];(path/'input.json').write_text(json.dumps(data))
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/quality.py'),str(path/'input.json'),'--output',str(path/'quality.json')],capture_output=True)
            self.assertEqual(proc.returncode,1)
            self.assertEqual((path/'quality.json').stat().st_mode & 0o777,0o600)
