#!/usr/bin/env python3
"""Differential checks against the shipped Python implementations. Fictional data only."""
import copy
import csv
from datetime import date
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import evaluate as evaluator
import quality
import score
import temporal
import portfolio

def compare(a,b,where='root'):
    if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)):
        assert abs(a-b)<=1e-12, (where,a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys(),(where,a.keys(),b.keys())
        for k in a:compare(a[k],b[k],where+'.'+k)
    elif isinstance(a,(list,tuple)):
        assert len(a)==len(b),(where,len(a),len(b))
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,f'{where}[{i}]')
    else:assert a==b,(where,a,b)

def run():
    fixture=json.loads((ROOT/'assets/evaluation-example.json').read_text())
    cases=[fixture,{**fixture,'queries':[],'outcomes':[]}]
    rng=random.Random(55)
    for seed in [0,1,1729,2**32+7,2**53-1]:
        d={'as_of':'2026-09-23T12:00:00Z','seed':seed,'bootstrap_samples':100,'queries':[]}
        for i in range(73):
            labels={f'p{j}':rng.randrange(2) for j in range(7)}
            labels['p0']=1
            baseline=list(labels);candidate=list(labels);rng.shuffle(baseline);rng.shuffle(candidate)
            d['queries'].append({'id':str(i),'target_id':f't{i}','account_id':f'a{i%31}','scored_at':d['as_of'],'labels':labels,'baseline':baseline,'candidate':candidate,'paths':[{'id':p,'status':'research','sender_edge':'unknown','target_edge':'unknown','willingness':'unknown','feature_dates':[d['as_of']]}for p in labels]})
        cases.append(d)
    # Exact microsecond boundary: events just after the horizon stay outside it.
    micro=copy.deepcopy(fixture)
    micro['outcomes'][0].update(sent_at='2026-08-02T00:00:00.000001Z',reply_at='2026-08-16T00:00:00.000002Z')
    cases.append(micro)
    legacy=json.loads((ROOT/'assets/example.json').read_text())
    legacy_cases=[legacy]
    for mutate in ['no','stale','same-day-no','signals','unknown-dates','prefix-company','dotted-suffix','future-end','missing-current','duplicate-profile']:
        d=copy.deepcopy(legacy)
        if mutate=='no':d['evidence'].append({'id':'new-no','kind':'willingness','subjects':['owner','connector','target'],'source':'fixture:no','detail':'declined','observed_at':'2026-09-02','value':'no'})
        if mutate=='same-day-no':d['evidence'].append({'id':'same-no','kind':'willingness','subjects':['owner','connector','target'],'source':'fixture:no','detail':'declined','observed_at':'2026-09-01','value':'no'})
        if mutate=='stale':d['evidence'][0]['observed_at']='2020-01-01'
        if mutate=='signals':
            for k in ['school','city','community','appearance','role_industry','investor']:
                d['evidence'].append({'id':k,'kind':k,'subjects':['connector','target'],'source':'fixture:'+k,'detail':'fictional','observed_at':'2026-09-01'})
                d['paths'][0].setdefault('signals',[]).append({'kind':k,'value':k,'evidence_ids':[k]})
        if mutate=='unknown-dates':d['paths'][0]['connector_experiences'][0].pop('start_date')
        if mutate=='prefix-company':d['paths'][0]['connector_experiences'][0]['company_name']='Example Studio Ventures'
        if mutate=='dotted-suffix':d['paths'][0]['connector_experiences'][0]['company_name']='Example Studio L.L.C.'
        if mutate=='future-end':d['paths'][0]['connector_experiences'][0]['end_date']='2027-01-01'
        if mutate=='missing-current':d['paths'][0]['connector_experiences'][0]['is_current']=True
        if mutate=='duplicate-profile':d['paths'][1]['connector']['linkedin_url']=d['paths'][0]['connector']['linkedin_url']
        legacy_cases.append(d)
    invalid=[]
    for change in ['future-feature','unsafe-ready','leakage','duplicate-query','null-split','unknown-field','bad-label','draft-outcome','invalid-date','null-seed','null-bootstrap','null-window']:
        d=copy.deepcopy(cases[2]);q=d['queries'][0]
        if change=='future-feature':q['paths'][0]['feature_dates']=['2027-01-01T00:00:00Z']
        if change=='unsafe-ready':q['paths'][0]['status']='ready'
        if change=='leakage':d['split']={'train_target_ids':[q['target_id']],'test_target_ids':[q['target_id']],'train_account_ids':[],'test_account_ids':[]}
        if change=='duplicate-query':d['queries'].append(q)
        if change=='null-split':d['split']=None
        if change=='unknown-field':q['new_field']=1
        if change=='bad-label':q['labels']['p0']=True
        if change=='draft-outcome':d['outcomes']=[{'id':'d','status':'draft','created_at':d['as_of'],'reply':True,'reply_at':d['as_of'],'meeting':None}]
        if change=='invalid-date':q['paths'][0]['feature_dates']=['2026-02-30T00:00:00Z']
        if change=='null-seed':d['seed']=None
        if change=='null-bootstrap':d['bootstrap_samples']=None
        if change=='null-window':d['outcome_window_days']=None
        invalid.append(d)
    payload={'cases':cases,'legacy':legacy_cases,'invalid':invalid,'today':date.today().isoformat()}
    if len(sys.argv)>1:
        records=[]
        def add(operation,body,expected=None,error=False,raw=None):
            records.append(dict(case_id=f'fictional-{operation}-{len(records):03d}',operation=operation,payload_json=raw or json.dumps(body),expected_json='' if error else json.dumps(expected),expected_error=str(error).lower(),today=date.today().isoformat(),max_age_days=180))
        for body in cases:add('evaluate',body,evaluator.evaluate(body))
        for body in legacy_cases:
            add('legacy',body,score.score(body,ROOT/'vendor'));add('quality',body,quality.audit(body))
        for body in invalid:add('evaluate',body,error=True)
        for raw in ['{"as_of":"2026-01-01T00:00:00Z","queries":[],"queries":[]}', '{"x":NaN}', '{"x":1e999}']:
            add('evaluate',None,error=True,raw=raw)
        for left,right in [({'start':'2020','end':'2022'},{'start':'2021','end':'2023'}),({'start':'2020-01','end':'2020-03'},{'start':'2021','end':'2022'}),({'start':None,'end':None},{'start':'2020','end':'2021'})]:
            body=dict(left=left,right=right,as_of='2026-09-23');add('temporal',body,temporal.overlap(left,right,body['as_of']))
        graph={'companies':[{'id':'seed','name':'Fictional seed'},{'id':'portfolio','name':'Fictional portfolio'}],'investors':[{'id':'fund','name':'Fictional fund'}],'edges':[{'company_id':c,'investor_id':'fund','source_url':'https://example.com/'+c,'observed_at':'2026-08-01'}for c in ['seed','portfolio']]}
        add('portfolio',{'graph':graph,'company_id':'seed'},portfolio.expand(graph,'seed'))
        graph=copy.deepcopy(graph);graph['edges'][0]['source_url']='not-a-url';add('portfolio',{'graph':graph,'company_id':'seed'},error=True)
        with open(sys.argv[1],'w',newline='')as handle:
            writer=csv.DictWriter(handle,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
        print(f'Wrote {len(records)} fictional validation cases')
    runner="""import {evaluate} from './evaluation.ts';import {scoreLegacy} from './legacy.ts';import {auditQuality} from './quality.ts';const d=await Bun.file(process.argv[2]).json();const result={cases:d.cases.map(evaluate),legacy:await Promise.all(d.legacy.map(x=>scoreLegacy(x,d.today))),quality:await Promise.all(d.legacy.map(x=>auditQuality(x,180,d.today))),invalid:d.invalid.map(x=>{try{evaluate(x);return false}catch{return true}})};console.log(JSON.stringify(result));"""
    # Use a temporary runner in this directory for relative module resolution; remove it afterwards.
    with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as inp:
        json.dump(payload,inp);inp.flush()
        with tempfile.NamedTemporaryFile(mode='w',suffix='.ts',dir=ROOT/'plays') as script:
            script.write(runner);script.flush()
            result=json.loads(subprocess.check_output(['bun',script.name,inp.name],text=True))
    for a,b in zip(cases,result['cases']):compare(evaluator.evaluate(a),b)
    for a,b,c in zip(legacy_cases,result['legacy'],result['quality']):compare(score.score(a,ROOT/'vendor'),b);compare(quality.audit(a),c)
    for d,v in zip(invalid,result['invalid']):
        try:evaluator.validate(d);expected=False
        except (ValueError,TypeError):expected=True
        assert v==expected,('validation mismatch',d,v)
    print(f'PASS: {len(cases)} evaluator runs (seeded bootstrap), {len(legacy_cases)} legacy score and audit runs, {len(invalid)} invalid evaluator cases; numeric tolerance 1e-12.')
if __name__=='__main__':run()
