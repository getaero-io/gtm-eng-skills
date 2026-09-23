"""Offline checks using fictional evidence; run from any directory with --repo."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
from score import score
from render import render


def fixture():
    def person(id,name):return dict(id=id,first_name=name,last_name='Example',linkedin_url=f'https://example.com/in/{id}',current_company='Example Studio',current_position='GTM Engineer')
    connector,target=person('connector','Alex'),person('target','Sam')
    evidence=[]
    def e(id,kind,subjects):
        evidence.append(dict(id=id,kind=kind,subjects=subjects,source=f'fixture:{id}',detail='Fictional reviewed evidence',observed_at='2026-09-01'))
        if kind=='relationship':evidence[-1]['confidence']='high'
        if kind=='willingness':evidence[-1]['value']='yes'
        return id
    rel=e('owner-edge','relationship',['owner','connector'])
    direct=e('intro','direct_intro',['connector','target'])
    target_rel=e('target-edge','relationship',['connector','target'])
    willingness=e('yes','willingness',['owner','connector','target'])
    work=[]
    for who in (connector,target):
        eid=e(who['id']+'-job','employment',[who['id']])
        work.append(dict(id=eid,contact_id=who['id'],company_name='Example Studio',start_date='2020-01-01',end_date='2022-12-31',is_current=False))
    path=dict(connector=connector,target=target,relationship_confidence='high',relationship_evidence_ids=[rel],target_relationship_confidence='high',target_relationship_evidence_ids=[target_rel],connector_willingness='yes',willingness_evidence_ids=[willingness],direct_intro_evidence_ids=[direct],connector_experiences=[work[0]],target_experiences=[work[1]])
    return dict(campaign_id='fictional-demo',owner_id='owner',as_of='2026-09-23',evidence=evidence,paths=[path])


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]/'vendor');p.add_argument('--write-demo',type=Path);a=p.parse_args()
    d=fixture(); row=score(d,a.repo)[0]
    assert row['total_score']==255 and row['segment']=='strong_warm_intro'
    assert row['reviewed_override']=='false'
    checks=1
    for change,segment,points in [
        ({'target_relationship_confidence':'unknown','target_relationship_evidence_ids':[]},'review_warm_intro',255),
        ({'relationship_confidence':'unknown','relationship_evidence_ids':[]},'review_warm_intro',240),
        ({'connector_willingness':'unknown','willingness_evidence_ids':[]},'review_warm_intro',255),

        ({'direct_intro_evidence_ids':[],'target_experiences':[]},'no_strong_path',15),
    ]:
        x=copy.deepcopy(d);x['paths'][0].update(change);r=score(x,a.repo)[0]
        assert r['segment']==segment and r['total_score']==points;checks+=1
    x=copy.deepcopy(d)
    x['evidence'].append(dict(id='decline',kind='willingness',subjects=['owner','connector','target'],source='fixture:decline',detail='Later decline',observed_at='2026-09-02',value='no'))
    assert score(x,a.repo)[0]['review_status']=='blocked_declined';checks+=1
    x['evidence'][-1]['observed_at']='2026-09-01'
    assert score(x,a.repo)[0]['review_status']=='blocked_declined';checks+=1
    x=copy.deepcopy(d);x['paths'][0]['direct_intro_evidence_ids']=[];x['paths'][0]['target_experiences'][0]['start_date']='2023-01-01';x['paths'][0]['target_experiences'][0]['end_date']='2024-01-01'
    assert score(x,a.repo)[0]['segment']=='review_warm_intro'
    assert score(x,a.repo)[0]['work_overlap_score']==0;checks+=1
    for mutation in (
        lambda x:x['evidence'][0].update(subjects=['stranger']),
        lambda x:x['evidence'][0].update(confidence='low'),
        lambda x:next(e for e in x['evidence'] if e['kind']=='willingness').update(value='no'),
        lambda x:x['evidence'][0].update(observed_at='2026-09-24'),
        lambda x:x['paths'][0].update(relationship_evidence_ids=[]),
        lambda x:x['paths'].append(copy.deepcopy(x['paths'][0])),
        lambda x:x['paths'][0]['connector_experiences'][0].update(end_date='2010-01-01'),
    ):
        x=copy.deepcopy(d);mutation(x)
        try:score(x,a.repo)
        except ValueError:checks+=1
        else:raise AssertionError('Invalid evidence accepted')
    hostile=dict(row,connector_name='</script><script>alert(1)</script>')
    assert '</script><script>alert(1)' not in render([hostile]);checks+=1
    # The real downstream CSV loader and signal builder must accept skill exports.
    import csv,tempfile
    from score import FIELDS
    askfile=a.repo/'examples/office-hours/warm-intro-ask-threads/draft_asks.py'
    spec=importlib.util.spec_from_file_location('ask_drafter_check',askfile);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    with tempfile.TemporaryDirectory() as tmp:
        f=Path(tmp)/'paths.csv'
        with f.open('w',newline='') as out:w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader();w.writerow(row)
        loaded=m.load_scored_csv(str(f));assert len(loaded)==1 and 'confirmed' in m.build_signal_description(loaded[0]).lower();checks+=1
    if a.write_demo:a.write_demo.write_text(json.dumps(d,indent=2)+'\n')
    print(f'{checks} offline behavior checks passed; no model calls or sends.')

if __name__=='__main__':main()
