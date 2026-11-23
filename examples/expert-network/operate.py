"""Explicit, bounded CLI operations with retained receipts. Never installs triggers."""
import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
STATES = ['discover', 'qualify', 'recruit', 'onboard', 'match', 'review', 'learn']

def command(args, label):
    p = subprocess.run(['deepline', *args], cwd=ROOT, text=True, capture_output=True)
    (EVIDENCE / f'{label}.txt').write_text(p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError(f'{label}: {p.stdout}\n{p.stderr}')
    print(f'OK {label}', flush=True)
    return p.stdout

def main():
    EVIDENCE.mkdir(exist_ok=True)
    parser=argparse.ArgumentParser(); parser.add_argument('operation', choices=['check-children','publish-children','schema','publish-parent','pilot'])
    op=parser.parse_args().operation
    auth=json.loads(command(['auth','status','--json'],'workspace'))
    if not os.environ.get('ERM_WORKSPACE_ID') or auth['workspace']['id'] != os.environ['ERM_WORKSPACE_ID']:
        raise RuntimeError('Set ERM_WORKSPACE_ID to the intended authenticated workspace ID')
    if op=='check-children':
        for s in STATES: command(['plays','check',str(ROOT/'transitions'/s/f'erm-{s}.play.ts')],f'check-{s}')
    elif op=='publish-children':
        for s in STATES:
            name=f'erm-{s}-v1'
            pub=json.loads(command(['plays','publish',str(ROOT/'transitions'/s/f'erm-{s}.play.ts'),'--json'],f'publish-{s}'))
            print(json.dumps(pub)[:500],flush=True)
            live=command(['plays','get',name],f'live-{s}')
            if 'Live max credits per run: 1' not in live: raise RuntimeError(f'Cannot verify cap: {live}')
            command(['plays','versions','--name',name],f'versions-{s}')
            command(['plays','settings','set','--play',name,'--name','path','--value',f'team/Expert Relationship Engine/Transitions/{s}'],f'folder-set-{s}')
            command(['plays','settings','get','--play',name,'--name','path'],f'folder-get-{s}')
    elif op=='schema':
        for n,sql in enumerate((ROOT/'schema.sql').read_text().split(';')):
            if sql.strip(): command(['db','query','--sql',sql.strip()],f'schema-{n}')
    elif op=='publish-parent':
        name='expert-relationship-engine-v1'
        command(['plays','check',str(ROOT/'expert-relationship-engine.play.ts')],'check-parent')
        command(['plays','publish',str(ROOT/'expert-relationship-engine.play.ts'),'--json'],'publish-parent')
        live=command(['plays','get',name],'live-parent')
        if 'Live max credits per run: 1' not in live: raise RuntimeError(f'Cannot verify cap: {live}')
        command(['plays','versions','--name',name],'versions-parent')
        command(['plays','settings','set','--play',name,'--name','path','--value','team/Expert Relationship Engine'],'folder-set-parent')
        command(['plays','settings','get','--play',name,'--name','path'],'folder-get-parent')
    elif op=='pilot':
        # Total bound: exactly three records plus one replay, all at a 1-credit cap.
        for i,label in [(1,'pilot-1'),(2,'pilot-2'),(3,'pilot-3'),(1,'replay-1')]:
            if label=='replay-1':
                states=STATES+['complete','waiting','declined','invalid']
                sql=' UNION ALL '.join(f"SELECT '{s}' state,'{role}' role,count(*)::int n FROM storage.erm_v1_{s}_{role}" for s in states for role in ['input','output'])
                baseline=command(['db','query','--sql',sql,'--max-rows','30','--json'],'counts-before-replay')
                (EVIDENCE/'counts-before-replay.json').write_text(baseline)
            command(['run','expert-relationship-engine-v1','--input-file',str(ROOT/'fixtures'/f'pilot-{i}.json'),'--json-out',str(EVIDENCE/f'{label}.json')],label)
            result=json.loads((EVIDENCE/f'{label}.json').read_text())
            if result.get('state') != {1:'complete',2:'waiting',3:'declined'}[i]:
                raise RuntimeError(f'Unexpected {label} result; stop before further runs')

if __name__=='__main__': main()
