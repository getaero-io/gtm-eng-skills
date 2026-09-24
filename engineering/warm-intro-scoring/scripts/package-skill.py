#!/usr/bin/env python3
"""Build a reproducible test archive from hash-pinned sources, never private outputs."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def build():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = ROOT / 'package-manifest.json'
    pinned = json.loads(manifest.read_text())['files']
    content = {}
    for name, expected in sorted(pinned.items()):
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts or any(p.startswith('.') and p != '.gitignore' for p in rel.parts):
            raise SystemExit(f'Unsafe package path: {name}')
        path = ROOT / rel
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise SystemExit(f'Package path escapes source tree: {name}')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f'Source drift: {name}; review changes and refresh package-manifest.json.')
        content[name] = raw
    content['package-manifest.json'] = manifest.read_bytes()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in sorted(content.items()):
            info = tarfile.TarInfo('warm-intro-scoring/' + name)
            info.size = len(raw)
            info.mode = 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(raw))
    data = gzip.compress(buffer.getvalue(), mtime=0)
    with args.output.open('xb') as out:
        args.output.chmod(0o600)
        out.write(data)
    print(json.dumps({'output': str(args.output.resolve()), 'files': len(content),
                      'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}))


if __name__ == '__main__':
    build()
