"""One-command offline handoff verification: python3 check_all.py."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent

def run(*args):
    subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)

def main():
    manifest=json.loads((ROOT/'vendor-manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise SystemExit(f'Pinned dependency changed: {name}; review and update manifest intentionally.')
    run('-m','unittest','discover','-s',ROOT/'scripts','-p','test_*.py')
    run(ROOT/'scripts/check.py')
    with tempfile.TemporaryDirectory() as tmp:
        output=Path(tmp)
        run(ROOT/'scripts/quality.py',ROOT/'assets/example.json','--output',output/'quality.json')
        run(ROOT/'scripts/score.py',ROOT/'assets/example.json','--output',output/'scores.csv')
        run(ROOT/'scripts/render.py',output/'scores.csv','--output',output/'paths.html')
        run(ROOT/'scripts/tuning.py',ROOT/'assets/tuning-example.json','--output',output/'tuning.html')
        run(ROOT/'scripts/evaluate.py',ROOT/'assets/evaluation-example.json','--output',output/'evaluation.json','--html',output/'evaluation.html')
    print('PASS: dependency integrity, unit tests, scorer checks, data quality and artifact smoke tests. No network calls.')

if __name__=='__main__':main()
