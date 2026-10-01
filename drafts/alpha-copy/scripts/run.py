"""Preview or run Alpha Copy locally through the Deepline CLI: one manual brief, or one brief applied to each CSV row."""
import argparse,csv,json,sys,time
sys.dont_write_bytecode=True
from pathlib import Path
from graph_runner import execute,save

PER_ROW={'company_domain','company_name','recipient_name','recipient_role','source_record_id','evidence_json','past_observation_json','current_observation_json','comparison_page_path'}

def rows(a,brief):
 if not a.csv:return [brief]
 if not a.field_map:raise ValueError('--csv needs --field-map {input_name: csv_column}')
 mapping=json.loads(a.field_map.read_text())
 if set(mapping)-PER_ROW:raise ValueError('Unsupported mapped input: '+', '.join(sorted(set(mapping)-PER_ROW)))
 if not {'company_domain','source_record_id'}<=set(mapping):raise ValueError('Map company_domain and a stable source_record_id')
 if PER_ROW & set(brief):raise ValueError('Shared brief contains per-person fields: '+', '.join(sorted(PER_ROW & set(brief))))
 out=[]
 with open(a.csv,newline='') as f:
  for row in csv.DictReader(f):
   values=dict(brief)
   for target,column in mapping.items():
    if column not in row:raise ValueError('CSV column is missing: '+column)
    values[target]=row[column] or ''
   # Never guess the employer domain from an email address; a missing mapped value fails.
   if not values['company_domain'] or not values['source_record_id']:raise ValueError('Row lacks company_domain or source_record_id: '+json.dumps(row)[:200])
   values.setdefault('source_kind','csv');out.append(values)
 return out[:a.limit] if a.limit else out

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--state',type=Path,required=True,help='Private run-history folder outside the package')
 p.add_argument('--brief',type=Path,help='JSON object of named workflow inputs (shared brief; plus company fields for a manual run)')
 p.add_argument('--csv',type=Path,help='Optional CSV of people/companies; each row runs the graph once')
 p.add_argument('--field-map',type=Path,help='JSON {input_name: csv_column} for --csv')
 p.add_argument('--limit',type=int,help='Process only the first N CSV rows (bounded test)')
 p.add_argument('--exa',action='store_true',help='Add the Exa Time Machine nodes; needs EXA_API_KEY in the environment')
 p.add_argument('--start',action='store_true')
 p.add_argument('--status',action='store_true')
 a=p.parse_args();package=Path(__file__).resolve().parents[1]
 if a.state.resolve().is_relative_to(package):raise ValueError('Keep run history outside the portable package')
 index=a.state/'state.json';state=json.loads(index.read_text()) if index.exists() else {}
 if a.status:
  if not state.get('last_batch'):raise ValueError('No run recorded by this runner')
  print(Path(state['last_batch']).read_text());return
 if not a.brief:raise ValueError('--brief is required')
 brief=json.loads(a.brief.read_text())
 if not isinstance(brief,dict):raise ValueError('Brief must be an object')
 if any(any(w in k.lower() for w in ['api_key','apikey','token','secret','authorization']) for k in brief):raise ValueError('Keep credentials in the environment, not the brief')
 if not (brief.get('offer') or brief.get('icp') or brief.get('sender_offer_json')):raise ValueError('Enter an offer or ICP')
 todo=rows(a,brief)
 if not a.csv and not brief.get('company_domain'):raise ValueError('Brief needs company_domain')
 print(json.dumps({'runs':len(todo),'first_inputs':todo[0] if todo else None,'exa':a.exa,'will_start':a.start,'will_send':False},indent=2))
 if not a.start:return
 if a.exa:
  import os
  if not os.environ.get('EXA_API_KEY'):raise ValueError('Set EXA_API_KEY for the Exa Time Machine path')
 graph=json.loads((package/'references/blueprint.json').read_text())
 if a.exa:
  from exa import extend
  graph=extend(graph)
 batch=time.strftime('%Y%m%dT%H%M%S');ledger=a.state/'runs'/batch/'results.jsonl'
 state['last_batch']=str(ledger);save(index,state);ledger.parent.mkdir(parents=True,exist_ok=True)
 for i,inputs in enumerate(todo):
  record=ledger.parent/f'{i:04d}.json'
  try:
   outputs,rec=execute(graph,{k:(v if isinstance(v,str) else json.dumps(v)) for k,v in inputs.items()},record)
   final=outputs.get('deliver') or outputs.get('hold') or {'state':'PIPELINE_ERROR','hold_reasons':['No terminal node ran; inspect '+str(record)]}
   cost=rec['cost_usd']
  except Exception as e:  # one failed record must not stop the batch; it stays visible
   final={'state':'PIPELINE_ERROR','hold_reasons':[str(e)[:500]],'source_record_id':inputs.get('source_record_id','')};cost=None
  row={'source_record_id':final.get('source_record_id',inputs.get('source_record_id','')),'state':final.get('state'),'subject':final.get('subject',''),
       'body':final.get('body',''),'hold_reasons':final.get('hold_reasons'),'alpha_score':final.get('alpha_score'),'agent_cost_usd':cost,'record':str(record),'sent':False}
  with ledger.open('a') as f:f.write(json.dumps(row)+'\n')
  print(json.dumps(row,indent=2))
 print('Ledger:',ledger)
if __name__=='__main__':main()
