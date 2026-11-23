import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from workspace import require_workspace
require_workspace()
def run(args,label):
    p=subprocess.run(['deepline',*args],text=True,capture_output=True,cwd=ROOT)
    (ROOT/f'{label}.txt').write_text(p.stdout+p.stderr)
    if p.returncode: raise RuntimeError(p.stdout+p.stderr)
    print(label,flush=True)
    return p.stdout
for n,sql in enumerate((ROOT/'schema.sql').read_text().split(';')):
    if sql.strip():run(['db','query','--sql',sql],f'schema-{n}')
run(['plays','check',str(ROOT/'erm-source-experts.play.ts')],'check-source')
run(['plays','publish',str(ROOT/'erm-source-experts.play.ts'),'--json'],'publish-source')
run(['plays','check',str(ROOT/'erm-refill-experts.play.ts')],'check-refill')
run(['plays','publish',str(ROOT/'erm-refill-experts.play.ts'),'--json'],'publish-refill')
for name in ['erm-refill-experts-v1','erm-source-experts-v1']:
    live=run(['plays','get',name],f'live-{name}')
    assert f'Live max credits per run: {12 if "refill" in name else 2}' in live
    run(['plays','versions','--name',name],f'versions-{name}')
    run(['plays','settings','set','--play',name,'--name','path','--value','team/Expert Relationship Engine/Acquisition'],f'folder-set-{name}')
    run(['plays','settings','get','--play',name,'--name','path'],f'folder-get-{name}')
