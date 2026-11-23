"""Apply additive tables; publish in dependency order without changing triggers."""
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from workspace import require_workspace
require_workspace()
if 'YOUR_PAUSED_CAMPAIGN_ID' in (ROOT/'enrollment-policy.ts').read_text():
    raise RuntimeError('Configure your paused campaign in enrollment-policy.ts before publishing')
def cli(*args):
    p=subprocess.run(['deepline',*args],text=True,capture_output=True,check=True)
    return p.stdout
for sql in (ROOT/'enrollment-schema.sql').read_text().split(';'):
    if sql.strip():cli('db','query','--sql',sql)
for filename,cap in [('erm-qualify-candidate',2),('erm-enroll-candidate',2),('erm-qualify-enroll',12),('erm-recruitment-cycle',24)]:
    source=str(ROOT/(filename+'.play.ts'));name=filename+'-v1'
    print(cli('plays','check',source),flush=True)
    print(cli('plays','publish',source),flush=True)
    live=cli('plays','get',name)
    assert f'Live max credits per run: {cap}' in live
    print(live,flush=True)
    path='team/Expert Relationship Engine/Acquisition' if filename=='erm-recruitment-cycle' else 'team/Expert Relationship Engine/Acquisition/Qualification and Enrollment'
    cli('plays','settings','set','--play',name,'--name','path','--value',path)
    assert path in unquote(cli('plays','settings','get','--play',name,'--name','path'))
