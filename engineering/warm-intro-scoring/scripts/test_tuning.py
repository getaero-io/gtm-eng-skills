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

    def test_context_does_not_change_scores_or_holds(self):
        base = {'as_of':'2026-09-23', 'paths':[path('a', 1)]}
        enriched = copy.deepcopy(base)
        enriched['paths'][0].update(target_company='Example', target_title='Engineer', requester_name='Owner')
        enriched['evidence'] = [dict(id='e1',source='https://example.com',detail='Documented holding',observed_at='2026-09-23')]
        enriched['target_research'] = {'t':[dict(label='Funding', detail='Public funding report', source_url='https://example.com', observed_at='2026-09-23', provider='Example')]}
        self.assertEqual(tuning.rank(base)[0]['tuned_score'],tuning.rank(enriched)[0]['tuned_score'])
        self.assertEqual(tuning.rank(enriched)[0]['review_status'],'needs_confirmation')
        html=tuning.render(enriched)
        self.assertIn('Documented holding', html)
        self.assertIn('Public funding report',html)
        enriched['evidence'].append(enriched['evidence'][0])
        with self.assertRaises(ValueError): tuning.render(enriched)

    def test_context_is_escaped_and_malformed_context_is_rejected(self):
        data={'as_of':'2026-09-23', 'paths':[path('a',1)]}
        attack='</script><script>alert(1)</script>'
        data['requester_name']=attack
        data['evidence']=[dict(id='e1',source='javascript:alert(1)',detail=attack,observed_at='2026-09-23')]
        self.assertNotIn(attack,tuning.render(data))
        data['target_research']={'t':'invalid'}
        with self.assertRaises(ValueError): tuning.render(data)
        del data['target_research']
        data['paths'][0]['target_company'] = {'bad':'shape'}
        with self.assertRaises(ValueError): tuning.render(data)

    def test_present_registry_requires_all_positive_references(self):
        data={'as_of':'2026-09-23','paths':[path('a',1)],'evidence':[]}
        with self.assertRaisesRegex(ValueError,'missing evidence'): tuning.render(data)
        data['evidence']=[dict(id='e1',source='https://example.com',detail='Company link',observed_at='2026-09-23')]
        tuning.render(data)
        data['paths'][0]['features']['investor_portfolio']['evidence_ids'].append('missing')
        with self.assertRaisesRegex(ValueError,'missing evidence'): tuning.render(data)
        del data['evidence']
        tuning.render(data)  # Backward-compatible IDs-only input has no registry to resolve.

    def test_source_dates_are_full_dates_at_or_before_cutoff(self):
        data={'as_of':'2026-09-23','paths':[path('a',1)]}
        for observed in ('2026','2026-09-24','2026-02-30'):
            data['evidence']=[dict(id='e1',source='https://example.com',detail='Company link',observed_at=observed)]
            with self.assertRaises(ValueError): tuning.render(data)
        data['evidence'][0]['observed_at']='2026-09-23'
        for observed in ('2026','2026-09-24','2026-02-30'):
            data['target_research']={'t':[dict(label='Fact',detail='Context',source_url='https://example.com',observed_at=observed,provider='Example')]}
            with self.assertRaises(ValueError): tuning.render(data)

    def test_fallbacks_add_points_without_claiming_a_relationship(self):
        p=path()
        p['features'].update(
            city_overlap=dict(value=1,evidence_ids=['city'],explanation='Same work city during the stated period.',timing_status='verified_overlap',overlap_start='2022-01-01',overlap_end='2023-01-01'),
            industry_match=dict(value=1,evidence_ids=['industry'],explanation='Both companies serve the same industry.',timing_status='not_applicable'),
            community_match=dict(value=1,evidence_ids=['community'],explanation='Both list the same professional group.',timing_status='not_applicable'))
        data={'as_of':'2026-09-23','paths':[p]}
        row=tuning.rank(data)[0]
        self.assertEqual(row['tuned_score'],22)
        self.assertEqual(row['review_status'],'needs_confirmation')
        self.assertFalse(row['ready_for_human_review'])
        self.assertEqual(tuning.rank(data,{'city_overlap':0})[0]['tuned_score'],12)
        p['features']['city_overlap']['timing_status']='unknown'
        with self.assertRaises(ValueError): tuning.rank(data)

    def test_direct_investor_role_ranks_above_work_and_community(self):
        investor=path('investor')
        investor['features']['investor_role']=dict(value=1,evidence_ids=['role','target'],explanation='Investor in the target company during target tenure.',timing_status='verified_overlap',overlap_start='2024-01-01',overlap_end='2025-01-01')
        worker=path('worker')
        worker['features']['work_overlap']=dict(value=1,evidence_ids=['work'],explanation='Shared employer.',timing_status='verified_overlap',overlap_start='2024-01-01',overlap_end='2025-01-01')
        worker['features']['community_match']=dict(value=1,evidence_ids=['group'],explanation='Shared professional group.',timing_status='not_applicable')
        data={'as_of':'2026-09-23','paths':[worker,investor]}
        rows=tuning.rank(data)
        self.assertEqual([(r['id'],r['tuned_score']) for r in rows],[('investor',120),('worker',82)])
        self.assertTrue(all(r['review_status']=='needs_confirmation' for r in rows))
        self.assertEqual(rows[0]['features']['work_overlap']['value'],0)
        investor['features']['investor_role']['timing_status']='unknown'
        with self.assertRaises(ValueError):tuning.rank(data)

    def test_large_company_overlap_requires_same_role_context(self):
        def result(size, function, location):
            p=path()
            p['features']['work_overlap']=dict(value=1,evidence_ids=['jobs'],explanation='Dated jobs at one company.',timing_status='verified_overlap',overlap_start='2020-01-01',overlap_end='2021-01-01',work_context=dict(company_size=size,same_function=function,same_location=location))
            # Other jobs or current titles must not inflate historical overlap.
            p['features']['role_industry']=dict(value=1,evidence_ids=['current'],explanation='Same current function.',timing_status='not_applicable')
            return tuning.normalize({'as_of':'2026-09-23','paths':[p]})[0]['features']['work_overlap']['value']*80
        self.assertEqual(result(1000,False,False),20)
        self.assertEqual(result(1000,False,True),40)
        self.assertEqual(result(1000,True,False),50)
        self.assertEqual(result(1000,True,True),80)
        self.assertEqual(result(999,False,False),80)
        self.assertEqual(result(None,None,None),20)
        for size in (True,-1,0,1.5):
            with self.assertRaises(ValueError):result(size,False,False)
        with self.assertRaises(ValueError):result(1000,'yes',True)
