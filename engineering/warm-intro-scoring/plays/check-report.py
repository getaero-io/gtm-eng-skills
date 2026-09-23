"""Compare decoded report data and unchanged UI against Python render()."""
import argparse,json,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import tuning
PATTERN=r'(<script type="application/json" id="data">)(.*?)(</script>)'
def payload(html):return json.loads(re.search(PATTERN,html,re.S).group(2))
def shell(html):return re.sub(PATTERN,r'\1__PAYLOAD__\3',html,flags=re.S)
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 subprocess.run([sys.executable,str(Path(__file__).with_name('sync-template.py')),'--check'],check=True)
 fixtures=[]
 for count in [1,5001]:
  fixtures.append(dict(as_of='2026-09-23',requester_name='Demo <requester> & review',paths=[dict(id=f'p{i}',target_id='t',target_name='Fictional Target',connector_id=f'c{i}',connector_name=f'Fictional Connector {i}',baseline_score=0,review_status='needs_confirmation',features={}) for i in range(count)]))
 if a.input:fixtures.append(json.loads(a.input.read_text()))
 with tempfile.TemporaryDirectory() as folder:
  for i,data in enumerate(fixtures):
   inp=Path(folder)/f'{i}.json';out=(a.output if a.output and i==len(fixtures)-1 else Path(folder)/f'{i}.html');inp.write_text(json.dumps(data))
   subprocess.run(['bun',str(Path(__file__).with_name('report-cli.ts')),str(inp),str(out)],check=True,capture_output=True)
   ts=out.read_text();py=tuning.render(data)
   assert shell(ts)==shell(py),'UI template differs'
   assert payload(ts)==payload(py),'Decoded report payload differs'
   assert '__TUNING_DATA__' not in ts
   assert out.stat().st_mode&0o777==0o600
   print(f'Report parity passed: {len(data["paths"])} paths, exact decoded payload and UI template.')
if __name__=='__main__':main()
