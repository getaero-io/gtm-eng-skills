"""Retry two pre-dispatch failures only; preserve original failure evidence."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from workspace import require_workspace
require_workspace()
def cli(*args):
    return subprocess.run(['deepline',*args],text=True,capture_output=True,check=True).stdout
def sql(text):return json.loads(cli('db','query','--sql',text,'--json'))['rows']
def quote(text):return "'"+text.replace("'","''")+"'"
rows=sql("SELECT i.profile,i.payload FROM storage.erm_enrollment_input i JOIN storage.erm_enrollment_output o ON o.profile=i.profile WHERE o.status='failed' AND NOT EXISTS (SELECT 1 FROM storage.erm_enrollment_outbox x WHERE x.profile=i.profile) ORDER BY i.created_at LIMIT 2")
results=[]
for index,row in enumerate(rows):
    target=ROOT/f'enrollment-retry-{index}.json'
    cli('run','erm-enroll-candidate-v1','--input',json.dumps(row['payload']),'--max-credits','2','--json-out',str(target))
    result=json.loads(target.read_text());results.append({'profile':row['profile'],**result})
    sql(f"UPDATE storage.erm_enrollment_output SET status={quote(result['status'])},payload=jsonb_build_object('prior_failure',payload,'retry_result',{quote(json.dumps(result))}::jsonb) WHERE profile={quote(row['profile'])} AND status='failed'")
(ROOT/'enrollment-retry-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps([{'profile':r['profile'],'status':r['status']} for r in results]))
