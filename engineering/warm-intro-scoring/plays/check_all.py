#!/usr/bin/env python3
"""One offline handoff check. Fictional fixtures only; no credentials or network."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    if shutil.which('bun') is None:
        raise SystemExit('Bun is required. Install Bun, then rerun python3 plays/check_all.py.')
    commands=[
        ('Existing Python package', [sys.executable,str(ROOT/'check_all.py')]),
        ('Generated report templates', [sys.executable,str(ROOT/'plays/sync-template.py'),'--check']),
        ('Scoring, dates, portfolio and payload parity', [sys.executable,str(ROOT/'plays/check_parity.py')]),
        ('Feature extraction regression cases', ['bun','test',str(ROOT/'tests/features.test.ts'),str(ROOT/'tests/adversarial.test.ts')]),
        ('Feature input packaging', [sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_prepare_inputs.py']),
        ('Evaluator, legacy scorer and audit parity', [sys.executable,str(ROOT/'plays/parity-evaluation.py')]),
        ('Tuning report parity', [sys.executable,str(ROOT/'plays/check-report.py')]),
        ('Evaluation and legacy report parity', [sys.executable,str(ROOT/'plays/parity-reports.py')]),
    ]
    for label,command in commands:
        print(f'Checking: {label}',flush=True)
        subprocess.run(command,cwd=ROOT,check=True)
    print('PASS: offline package checks and TypeScript regression/parity checks. No credentials, private inputs, provider calls, or database writes.')

if __name__=='__main__':main()
