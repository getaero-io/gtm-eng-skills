"""Read-only reconciliation of live pilot outputs, receipts and durable tables."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from workspace import require_workspace

ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
STATES=['discover','qualify','recruit','onboard','match','review','learn','complete','waiting','declined','invalid']

def run(args):
    p=subprocess.run(['deepline',*args],cwd=ROOT,text=True,capture_output=True,check=True)
    return p.stdout

def counts(label):
    sql=' UNION ALL '.join(f"SELECT '{s}' state,'{role}' role,count(*)::int n FROM storage.erm_v1_{s}_{role}" for s in STATES for role in ['input','output'])
    output=run(['db','query','--sql',sql,'--max-rows','30','--json'])
    (E/f'{label}.json').write_text(output)
    return output

def main():
    require_workspace()
    summary=[]
    for label,expected in [('pilot-1','complete'),('pilot-2','waiting'),('pilot-3','declined'),('replay-1','complete')]:
        if not (E/f'{label}.json').exists():
            print(f'UNVERIFIED {label}: no completed result file')
            continue
        result=json.loads((E/f'{label}.json').read_text()); assert result['state']==expected
        receipt=(E/f'{label}.txt').read_text()
        run_id=re.search(r'^Run Id: (.+)$',receipt,re.M)[1]
        log_path=re.search(r'^Logs: (.+)$',receipt,re.M)
        if log_path: shutil.copyfile(log_path[1],E/f'{label}-trace.txt')
        details=run(['runs','get',run_id,'--json']); (E/f'{label}-run.json').write_text(details)
        summary.append(dict(label=label,runId=run_id,state=expected,result=result))
    (E/'pilot-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    counts('counts-after-attempt')
    before=json.loads((E/'counts-before-replay.json').read_text())['rows']
    after=json.loads((E/'counts-after-attempt.json').read_text())['rows']
    assert before == after, 'Replay attempt changed durable row counts'
    assert len(summary)==4, 'All four pilot/replay receipts are required'
    if summary[-1]['label']=='replay-1': assert summary[-1]['result']['replayedTransitions']==7
    sql=' UNION ALL '.join(f"SELECT record FROM storage.erm_v1_{s}_output" for s in STATES)
    (E/'persisted-transition-history.json').write_text(run(['db','query','--sql',sql,'--max-rows','100','--json']))
    (E/'runs.json').write_text(run(['runs','list','--play','expert-relationship-engine-v1','--limit','10','--json']))
    for state in STATES[:7]+['parent']:
        pub=json.loads((E/f'publish-{state}.txt').read_text())
        live=(E/f'live-{state}.txt').read_text(); versions=(E/f'versions-{state}.txt').read_text()
        assert f"Live version: {pub['liveVersion']}" in live
        assert 'Live max credits per run: 1' in live
        assert f"v{pub['liveVersion']} " in versions
    print(f'Verified {len(summary)} completed results and all eight live versions/caps; saved full traces and DB counts. Missing results remain unverified.')

if __name__=='__main__': main()
