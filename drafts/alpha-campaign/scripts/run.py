"""Preview or run a bounded Alpha Campaign batch locally through the Deepline CLI. Keep inputs and receipts outside the package."""
import argparse, json, sys, time
sys.dont_write_bytecode=True
from pathlib import Path
from graph_runner import execute, save
from build import parent, child
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'references'))
from pipeline import reconcile

class Ctx:
 def __init__(self,v):self.v=v
 def get_input(self,k):return self.v.get(k)

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--state',required=True,type=Path,help='Private run-history folder outside the package')
 p.add_argument('--brief',type=Path);p.add_argument('--audience-brief',default='');p.add_argument('--max-people',type=int,default=5)
 p.add_argument('--batch-id',default='');p.add_argument('--memory',type=Path);p.add_argument('--feedback',type=Path)
 p.add_argument('--exa',action='store_true',help='Add Exa Time Machine retrieval to Copy; needs EXA_API_KEY')
 p.add_argument('--start',action='store_true');p.add_argument('--status',action='store_true',help='Print the last batch ledger')
 a=p.parse_args();package=Path(__file__).resolve().parents[1]
 if a.state.resolve().is_relative_to(package):raise ValueError('Keep run history outside the portable package')
 index=a.state/'state.json';state=json.loads(index.read_text()) if index.exists() else {}
 if a.status:
  if not state.get('last_batch'):raise ValueError('No batch recorded by this runner')
  print(Path(state['last_batch'],'ledger.json').read_text());return
 if not a.brief:raise ValueError('Provide --brief')
 if not 1<=a.max_people<=100:raise ValueError('max-people must be 1–100')
 brief=json.loads(a.brief.read_text())
 if any(k in brief for k in ['api_key','apiKey','token','secret','authorization']):raise ValueError('Credentials belong in the environment, not the brief')
 inputs={'brief_json':json.dumps(brief),'audience_brief':a.audience_brief,'max_people':a.max_people,'batch_id':a.batch_id,
  'memory_json':a.memory.read_text() if a.memory else '', 'feedback_json':a.feedback.read_text() if a.feedback else ''}
 print(json.dumps({'inputs':inputs,'exa':a.exa,'will_start':a.start,'sends_email':False},indent=2))
 if not a.start:return
 if a.exa:
  import os
  if not os.environ.get('EXA_API_KEY'):raise ValueError('Set EXA_API_KEY for the Exa Time Machine path')
 batch=a.state/'runs'/time.strftime('%Y%m%dT%H%M%S')
 if batch.exists():raise ValueError('Batch folder already exists; inspect it, do not accidentally restart it')
 state['last_batch']=str(batch);save(index,state)
 out,_=execute(parent(),inputs,batch/'parent.json')
 if 'dispatch' not in out:  # zero candidates: the empty-search receipt is the result
  ledger={'status':'NO_CANDIDATES','people':[],'empty':out.get('empty'),'memory_json':(out.get('empty') or {}).get('memory_json',''),'sent':False}
 else:
  d=out['dispatch'];results=[];graph=child(a.exa)
  for i,entry in enumerate(d['entries']):
   try:
    o,_=execute(graph,entry['inputs'],batch/f'person-{i:03d}.json')
    results.append(next((o[k] for k in ['finish_deliver','finish_hold','no_email','bad_email'] if k in o),
                        {'candidate_id':entry['candidate_id'],'status':'PIPELINE_ERROR','reason':'No terminal node ran'}))
   except Exception as e:  # a failed person stays visible as PIPELINE_ERROR; the batch continues
    results.append({'candidate_id':entry['candidate_id'],'status':'PIPELINE_ERROR','reason':str(e)[:500],'subject':'','body':''})
  ledger=reconcile(Ctx({'dispatch':d,'results':results}))
  ledger['rejected']=out['normalize'].get('rejected',[]);ledger['discovery_notes']=out['normalize'].get('discovery_notes',[])
 save(batch/'ledger.json',ledger)
 if ledger.get('memory_json'):(batch/'memory.json').write_text(ledger['memory_json'])
 print(json.dumps({k:ledger.get(k) for k in ['status','counts','terminal_count','ready_count']},indent=2));print('Ledger:',batch/'ledger.json')
if __name__=='__main__':main()
