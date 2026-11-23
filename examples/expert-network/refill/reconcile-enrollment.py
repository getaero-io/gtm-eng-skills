"""Confirm submitted/uncertain outbox rows from Lemlist; never submit contacts."""
import json
import os
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from workspace import require_workspace
require_workspace()
CAMPAIGN=os.environ['ERM_CAMPAIGN_ID']
if not CAMPAIGN.startswith('cam_'):
    raise RuntimeError('Set ERM_CAMPAIGN_ID to the same campaign as enrollment-policy.ts')
def cli(*args):return subprocess.run(['deepline',*args],capture_output=True,text=True,check=True).stdout
def quote(text):return "'"+text.replace("'","''")+"'"
def sql(query):return json.loads(cli('db','query','--sql',query,'--json'))['rows']
rows=sql("SELECT profile,email FROM storage.erm_enrollment_outbox WHERE campaign_id="+quote(CAMPAIGN)+" AND status IN ('submitted','uncertain','submitting') LIMIT 100")
confirmed=[]
for index,row in enumerate(rows):
    target=ROOT/f'enrollment-readback-{index}.json'
    cli('run','lemlist_get_contacts','--input',json.dumps({'idsOrEmails':row['email']}),'--json-out',str(target))
    matches=json.loads(target.read_text())
    if not isinstance(matches,list):raise RuntimeError('Unexpected exact-contact response')
    found=next((c for c in matches if c.get('email','').lower()==row['email'].lower() and c.get('linkedinUrl','').lower().rstrip('/')==row['profile'].lower().rstrip('/') and any(x.get('campaignId')==CAMPAIGN and x.get('leadId') for x in c.get('campaigns',[]))),None)
    if not found:continue
    evidence={'status':'confirmed','campaignId':CAMPAIGN,'contactId':found['_id'],'profile':row['profile'],'campaigns':found['campaigns']}
    sql(f"UPDATE storage.erm_enrollment_outbox SET status='confirmed',receipt=coalesce(receipt,'{{}}'::jsonb) || {quote(json.dumps(evidence))}::jsonb,updated_at=now() WHERE campaign_id={quote(CAMPAIGN)} AND profile={quote(row['profile'])}")
    sql(f"UPDATE storage.erm_enrollment_output SET status='confirmed',payload=payload || jsonb_build_object('membership_readback',{quote(json.dumps(evidence))}::jsonb) WHERE profile={quote(row['profile'])}")
    confirmed.append(evidence)
(ROOT/'enrollment-reconciled.json').write_text(json.dumps(confirmed,indent=2)+'\n')
print(f'Confirmed {len(confirmed)} campaign memberships; no submissions made.')
