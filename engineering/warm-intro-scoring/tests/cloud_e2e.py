#!/usr/bin/env python3
"""Opt-in cloud E2E test: fictional cached data only; writes isolated test revisions.
Run from the intended Deepline workspace after preflight:
python3 /path/to/tests/cloud_e2e.py --out /private/new-directory
No providers, email, consent, or triggers. CLI credentials use the caller's scope.
"""
import argparse,csv,hashlib,importlib.util,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
csv.field_size_limit(50_000_000)
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path);args=ap.parse_args()
 args.out.mkdir(mode=0o700,parents=True,exist_ok=False);out=args.out;os.umask(0o077)
 env=dict(os.environ,DEEPLINE_SKIP_SELF_UPDATE='1');receipt={'status':'running','scope':'fictional cached cloud pipeline','runs':{}};prefix='e2e-'+str(time.time_ns())
 def save(): (out/'receipt.json').write_text(json.dumps(receipt,indent=2))
 def command(argv,name):
  with (out/(name+'.log')).open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=900)
 def write_csv(name,rows):
  path=out/(name+'.csv')
  with path.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  return path
 def run(stage,rows,extra=None,dataset='result.rows'):
  path=write_csv(stage,rows);rid=out/(stage+'-run.json');command(['deepline','plays','run',str(ROOT/'plays'/(stage+'.play.ts')),'--input',json.dumps({'csv':str(path),**(extra or {})}),'--debug','--run-id-file',str(rid)],stage)
  runid=json.loads(rid.read_text())['runId'];receipt['runs'][stage]=runid;save();dest=out/(stage+'-export.csv')
  command(['deepline','runs','export',runid,'--dataset',dataset,'--out',str(dest)],stage+'-export')
  result=list(csv.DictReader(dest.open()));assert len(result)==len(rows),(stage,'missing output',len(result),len(rows));return result
 try:
  data=json.loads((ROOT/'tests/e2e-fixture.json').read_text());people=data['connectors']+data['profiles'];raw={}
  for p in people:
   raw[p['id']]={'linkedinUrl':p['linkedin_url'],'firstName':p['first_name'],'lastName':p['last_name'],'experience':p['experience'],'education':p['education']}
  collected=run('collect',[dict(contact_id=p['id'],linkedin_url=p['linkedin_url'],profile_json=json.dumps(raw[p['id']]),posts_json='[]',profile_observed_at=p['observed_at'],account_domain=p['domain']) for p in people],{'mode':'cached','observed_at':data['profiles_checked_at']})
  by_id={r['contact_id']:json.loads(r['sources']) for r in collected};assert set(by_id)==set(raw)
  # Use the actual collection adapter output; keep manifest account assignment separate.
  for p in people:
   source=by_id[p['id']];assert source['profile']==raw[p['id']];assert source['posts']==[]
   normalized=source['normalized_profile'];assert normalized['id']==p['id'];p.update(normalized)
  written=run('snapshots',[dict(record_id=prefix,kind='target',revision='1',observed_at=data['profiles_checked_at'],payload_json=json.dumps(data))],{'execute':True})
  assert json.loads(written[0]['receipt'])['status']=='applied'
  source=run('read-sources',[dict(source_id=prefix,schema_name='analytics',table_name='warm_intro_play_snapshots',key_column='record_id')])
  saved=[r for r in json.loads(source[0]['snapshot'])['records'] if r['record_id']==prefix];assert len(saved)==1
  readback=saved[0]['payload'];readback=json.loads(readback) if isinstance(readback,str) else readback;assert readback==data
  pack=load_module('package_inputs',ROOT/'plays/prepare-inputs.py');feature_rows=pack.batches(readback)[0]
  # run() expects one output per target, not one per input source record.
  path=write_csv('features',feature_rows);rid=out/'features-run.json'
  command(['deepline','plays','run',str(ROOT/'plays/features.play.ts'),'--input',json.dumps({'csv':str(path),'include_payload':True}),'--debug','--run-id-file',str(rid)],'features')
  runid=json.loads(rid.read_text())['runId'];receipt['runs']['features']=runid;save();export=out/'features-export.csv'
  command(['deepline','runs','export',runid,'--dataset','result.rows','--out',str(export)],'features-export')
  rows=list(csv.DictReader(export.open()));assert len(rows)==1
  result=json.loads(rows[0]['result']);assert result['coverage']['unresolved']==[]
  payload=result['payload'];assert len(payload['paths'])==4
  totals={p['connector_id']:p['tuned_score'] for p in payload['paths']};assert totals=={'investor':120,'coworker':80,'company':20,'sparse':0},totals
  # A review hold must survive a refresh and reweighting.
  previous={'paths':[dict(payload['paths'][0],review_status='blocked_declined')]}
  merger=load_module('merge_payloads',ROOT/'plays/merge-payloads.py');merged=merger.merge([export],previous,['target:0'])
  assert next(p for p in merged['paths'] if p['connector_id']=='investor')['review_status']=='blocked_declined'
  (out/'report-input.json').write_text(json.dumps(merged))
  scored=run('score',[dict(case_id=prefix,payload_json=json.dumps(merged),weights_json='{"work_overlap":160}')])
  score=json.loads(scored[0]['result']);assert [p['connector_id'] for p in score['scores']]==['coworker','investor','company','sparse']
  assert [p['score'] for p in score['scores']]==[160,120,40,0]
  assert score['scores'][1]['review_status']=='blocked_declined'
  rendered=run('report',[dict(case_id=prefix,payload_json=json.dumps(merged),weights_json='{"work_overlap":160}',artifact_path='warm-intro-scoring/reviews/'+prefix+'.html')],dataset='result.reports')
  artifact=json.loads(rendered[0]['artifact']);assert artifact['paths']==4 and artifact['receipt']['ok']
  # Read the stored file independently; do not accept a write receipt alone.
  command(['deepline','tools','execute','get_customer_db_file','--input',json.dumps({'path':artifact['path']}),'--json'],'file-readback')
  stored=json.loads((out/'file-readback.log').read_text());(out/'file-readback.json').write_text(json.dumps(stored))
  def html_in(v):
   if isinstance(v,str) and '<html' in v.lower():return v
   if isinstance(v,dict):
    for value in v.values():
     found=html_in(value)
     if found:return found
   return None
  html=html_in(stored);assert html and 'blocked_declined' in html and 'coworker' in html
  (out/'review.html').write_text(html)
  receipt.update(status='pass',contacts=5,targets=1,paths=4,default_scores=totals,tuned_scores=[160,120,40,0],review_hold_preserved=True,artifact=artifact['path'],artifact_sha256=hashlib.sha256(html.encode()).hexdigest(),limits=['Fictional retained Apify shape; live provider acquisition not tested','Normalization supports the retained Harvest profile shape; other provider schemas need adapters','No automatic incremental scheduler tested'])
 except Exception as exc:
  receipt.update(status='fail',error=str(exc));save();raise
 save();print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
