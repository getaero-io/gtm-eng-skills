"""Replay fixed inputs in two package folders. No provider calls or sends."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def compare(before, after, evidence=None, features=None):
    cases = [
        ('scores.csv', 'score.py', evidence or before / 'assets/example.json', []),
        ('evaluation.json', 'evaluate.py', before / 'assets/evaluation-example.json', []),
        ('tuning.html', 'tuning.py', features or before / 'assets/tuning-example.json', []),
    ]
    receipts = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, script, source, flags in cases:
            outputs = []
            for index, root in enumerate((before, after)):
                output = Path(tmp) / f'{index}-{name}'
                subprocess.run([sys.executable, str(root / 'scripts' / script),
                                str(source), '--output', str(output), *flags],
                               cwd=root, check=True, capture_output=True)
                outputs.append(output.read_bytes())
            if outputs[0] != outputs[1]:
                raise AssertionError(f'Output changed: {name}')
            receipts.append({'output': name, 'exact_match': True,
                             'sha256': hashlib.sha256(outputs[0]).hexdigest()})
    return receipts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--features', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.before.resolve(), args.after.resolve(),
                             args.evidence.resolve() if args.evidence else None,
                             args.features.resolve() if args.features else None), indent=2))
