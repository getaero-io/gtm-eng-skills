"""Differential tests against the existing Python oracle. No customer data required.

Optional --input privately tests every row in a normalized scoring snapshot.
"""
import argparse,copy,json,random,subprocess,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import tuning,temporal,portfolio

def run(q):
 try:
  op=q['op']
  if op=='normalize':value=tuning.normalize(q['data'])
  elif op=='rank':value=tuning.rank(q['data'],q.get('config'))
  elif op=='weights':value=tuning.weights(q.get('config'))
  elif op=='temporal':value=temporal.overlap(q['left'],q['right'],q['as_of'])
  elif op=='portfolio':
   class FrozenDate(date):
    @classmethod
    def today(cls):return date.fromisoformat(q['today'])
   original=portfolio.date;portfolio.date=FrozenDate
   try:value=portfolio.expand(q['graph'],q['company'])
   finally:portfolio.date=original
  elif op=='payload':
   html=tuning.render(q['data'],q.get('config'))
   import re
   match=re.search(r'<script type="application/json" id="data">(.*?)</script>',html,re.S)
   if not match:raise RuntimeError('Cannot extract Python payload')
   value=json.loads(match.group(1))
  return dict(ok=True,value=value)
 except (ValueError,TypeError,KeyError,AttributeError):return dict(ok=False)

def row(i=0,name='Connector'):
 return dict(id=f'p{i}',target_id='target',target_name='Target',connector_id=f'c{i}',connector_name=name,review_status='needs_confirmation',baseline_score=0,features={})
def dataset(rows=None):return dict(as_of='2026-09-23',paths=rows or [row()])
def cases():
 q=[]
 for config in [None,{},dict(work_overlap=0),dict(appearance=.1),[],dict(fake=1),dict(work_overlap=True),dict(work_overlap=-1),dict(work_overlap=None)]:q.append(dict(op='weights',config=config))
 for data in [None,{},dict(paths=[]),dataset(),dataset([row(i,n) for i,n in enumerate(['Straße','STRASSE','Σ','ς','İ','I','\ue000','😀','ﬃ','FFI'])])]:q.append(dict(op='rank',data=data))
 for size in [None,999,1000,1001,0,True,'1000']:
  for fn in [None,False,True]:
   for loc in [None,False,True]:
    d=dataset();d['paths'][0]['features']['work_overlap']=dict(value=1,evidence_ids=['e'],explanation='Shared employer',timing_status='verified_overlap',overlap_start='2020-02-29',overlap_end='2021-01-01',work_context=dict(company_size=size,same_function=fn,same_location=loc));q.append(dict(op='rank',data=d))
 for change in [dict(baseline_score=True),dict(review_status='ready'),dict(id=' '),dict(features=None),dict(features={'wrong':{}}),dict(connector_id='target')]:
  d=dataset();d['paths'][0].update(change);q.append(dict(op='normalize',data=d))
 for start,end in [('2020-02-30','2021-01-01'),('0000-01-01','2021-01-01'),('2022-01-01','2021-01-01'),('2020-01-01','2027-01-01'),('0001-01-01','0001-01-02')]:
  d=dataset();d['paths'][0]['features']['school_overlap']=dict(value=1,evidence_ids=['e'],explanation='School',timing_status='verified_overlap',overlap_start=start,overlap_end=end);q.append(dict(op='rank',data=d))
 for f in [None,[],{},dict(value=True),dict(value=.5,evidence_ids=[],explanation='X'),dict(value=0,evidence_ids=[None],explanation='X'),dict(value=0,evidence_ids=[],explanation='X',timing_status=None)]:
  d=dataset();d['paths'][0]['features']['appearance']=f;q.append(dict(op='rank',data=d))
 for d in [dataset([row(),row()]),dataset([row(),dict(row(1),connector_id='c0')])]:q.append(dict(op='rank',data=d))
 dates=[None,'2020','2020-02','2020-02-29','2021-02-29','0001-01-01','9999-12-31','2022-05','2023-01-01']
 rng=random.Random(9)
 for _ in range(140):
  l=dict(start=rng.choice(dates),end=rng.choice(dates));r=dict(start=rng.choice(dates),end=rng.choice(dates));q.append(dict(op='temporal',left=l,right=r,as_of='2026-09-23'))
 for observed in ['2026-09-23','2026-09','2026-09-24',None]:q.append(dict(op='temporal',left=dict(start='2020',current=True,observed_at=observed),right=dict(start='2021',end='2023'),as_of='2026-09-23'))
 graph=dict(companies=[dict(id='seed'),dict(id='next')],investors=[dict(id='fund')],edges=[dict(company_id=c,investor_id='fund',source_url='https://example.org/funding',observed_at='2026-09-23') for c in ['seed','next','next']])
 q.append(dict(op='portfolio',graph=graph,company='seed',today='2026-09-23'))
 for source in ['mailto:a@example.org','https:example.org','https://example.org','http://','ftp://example.org']:
  g=copy.deepcopy(graph);g['edges'][0]['source_url']=source;q.append(dict(op='portfolio',graph=g,company='seed',today='2026-09-23'))
 for observed in ['20260923','2026-W39-3','2026W393','2026-W39','2021-W53-1','2020-W53-7','00010101','9999-W52-7']:
  g=copy.deepcopy(graph);g['edges'][0]['observed_at']=observed;q.append(dict(op='portfolio',graph=g,company='seed',today='2026-09-23'))
 for registry in [[],None,[dict(id='e',source='https://example.org',detail='Observed',observed_at='2027-01-01')],[dict(id='e',source='https://example.org',detail='Observed',observed_at='2026-09-23')]]:
  d=dataset();d['evidence']=registry;d['paths'][0]['features']['appearance']=dict(value=1,evidence_ids=['e'],explanation='Observed');q.append(dict(op='payload',data=d))
 q.append(dict(op='payload',data=dataset()))
 return q

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path);a=p.parse_args();qs=cases()
 if a.input:
  data=json.loads(a.input.read_text());qs.append(dict(op='rank',data=data));print(f"Checking {len(data['paths'])} private paths; no row data is printed.")
 process=subprocess.run(['bun',str(Path(__file__).with_name('parity-driver.ts'))],input='\n'.join(json.dumps(q) for q in qs),text=True,capture_output=True,check=True)
 actual=[json.loads(line) for line in process.stdout.splitlines()]
 assert len(actual)==len(qs),'Driver response count mismatch'
 for i,(q,got) in enumerate(zip(qs,actual)):
  expected=run(q)
  assert got['ok']==expected['ok'],f'Case {i} {q["op"]}: acceptance differs'
  if expected['ok']:assert got['value']==expected['value'],f'Case {i} {q["op"]}: output differs'
 print(f'{len(qs)} Python/TypeScript differential checks passed.')
if __name__=='__main__':main()
