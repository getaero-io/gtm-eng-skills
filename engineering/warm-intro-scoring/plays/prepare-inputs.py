#!/usr/bin/env python3
"""Package retained source snapshots for features.play.ts. Offline; no provider calls.

python3 plays/prepare-inputs.py sources.json --out run-input.csv
python3 plays/prepare-inputs.py sources.json --out run-input.csv --targets-per-file 25

Batching repeats the source context and partitions targets. Every emitted CSV must
fit the Play's 5,000-record bound. Connector-shard merging is not supported. Use the local TypeScript feature core if context alone is
larger. Output files contain private profiles and are created with mode 0600.
"""
import argparse
import csv
import json
import os
from datetime import date
from pathlib import Path

SECTIONS = ('connectors', 'profiles', 'company_sizes', 'funding_edges',
            'verified_firms', 'owner_portfolio')
CONFIG = ('as_of', 'profiles_checked_at', 'requester_name', 'requester_company',
          'excluded_connector_urls', 'target_research')
LIMIT = 5000


def require(value, description):
    if not value:
        raise ValueError(description)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def day(value, label):
    require(text(value), f'{label} must be a YYYY-MM-DD date')
    parsed = date.fromisoformat(value)
    require(parsed.isoformat() == value, f'{label} must be a YYYY-MM-DD date')
    return parsed


def validate(data):
    require(isinstance(data, dict), 'Input must be a JSON object')
    allowed = set(SECTIONS + CONFIG + ('targets',))
    require(not set(data) - allowed, 'Unknown fields: ' + ', '.join(sorted(set(data) - allowed)))
    cutoff = day(data.get('profiles_checked_at'), 'profiles_checked_at')
    require(cutoff <= day(data.get('as_of'), 'as_of'), 'Profile cutoff is after as_of')
    require(text(data.get('requester_name')), 'requester_name is required')
    for section in SECTIONS + ('targets',):
        rows = data.get(section, [])
        require(isinstance(rows, list), f'{section} must be an array')
        require(all(isinstance(r, dict) for r in rows), f'{section} rows must be objects')
    require(bool(data.get('targets')), 'targets must not be empty')
    require(bool(data.get('connectors')), 'connectors must not be empty')
    require('profiles' in data, 'profiles array is required; use [] for missing profiles')
    for section in ('connectors', 'profiles'):
        for i, row in enumerate(data[section]):
            label = f'{section}[{i}]'
            for field in ('id', 'linkedin_url', 'source', 'observed_at'):
                require(text(row.get(field)), f'{label}.{field} is required')
            require(day(row['observed_at'], label + '.observed_at') <= cutoff,
                    f'{label} is newer than profiles_checked_at')
            for field in ('experience', 'education'):
                values = row.get(field)
                require(values is None or (isinstance(values, list) and
                        all(isinstance(v, dict) for v in values)), f'{label}.{field} must be an array of objects')
    for i, row in enumerate(data['targets']):
        for field in ('name', 'linkedin_url', 'company', 'domain'):
            require(text(row.get(field)), f'targets[{i}].{field} is required')
    if 'excluded_connector_urls' in data:
        require(isinstance(data['excluded_connector_urls'], list) and
                all(text(v) for v in data['excluded_connector_urls']),
                'excluded_connector_urls must be an array of URLs')
    if 'target_research' in data:
        require(isinstance(data['target_research'], dict), 'target_research must be an object')
    return data


def record(section, key, payload):
    return dict(section=section, key=key,
                payload_json=json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False))


def batches(data, targets_per_file=None):
    validate(data)
    if targets_per_file is not None:
        require(isinstance(targets_per_file, int) and not isinstance(targets_per_file, bool)
                and targets_per_file > 0, 'targets_per_file must be a positive integer')
    context = [record('config', 'config', {k: data[k] for k in CONFIG if k in data})]
    for section in SECTIONS:
        context.extend(record(section, f'{section}:{i}', row)
                       for i, row in enumerate(data.get(section, [])))
    size = targets_per_file or len(data['targets'])
    require(len(context) + min(size, len(data['targets'])) <= LIMIT,
            f'CSV exceeds {LIMIT} source records; use --targets-per-file; if shared context alone exceeds the limit, use local TypeScript feature extraction (connector-shard merging is unsupported)')
    output = []
    for start in range(0, len(data['targets']), size):
        # Position in the full input preserves identity across partitioning and retains
        # unresolved or duplicate target rows for review instead of silently dropping them.
        target_rows = [record('targets', f'target:{i}', {'target': row})
                       for i, row in enumerate(data['targets'][start:start + size], start)]
        output.append(context + target_rows)
    return output


def write_inputs(data, destination, targets_per_file=None):
    groups = batches(data, targets_per_file)
    base = Path(destination)
    paths = [base] if len(groups) == 1 else [base.with_name(f'{base.stem}.{i:03d}{base.suffix or ".csv"}')
                                           for i in range(1, len(groups) + 1)]
    require(all(not p.exists() for p in paths), 'An output file already exists; choose a new --out path')
    for path, rows in zip(paths, groups):
        with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['section', 'key', 'payload_json'])
            writer.writeheader()
            writer.writerows(rows)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--targets-per-file', type=int)
    args = parser.parse_args()
    try:
        data = json.loads(args.source.read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
        paths = write_inputs(data, args.out, args.targets_per_file)
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f'Input packaging failed: {exc}\n')
    print(json.dumps({'files': [str(p.resolve()) for p in paths], 'targets': len(data['targets'])}))


if __name__ == '__main__':
    main()
