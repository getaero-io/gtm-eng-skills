#!/usr/bin/env python3
"""Merge include_payload CSV exports into one report input, offline.

python3 plays/merge-payloads.py export-*.csv --out report-input.json
python3 plays/merge-payloads.py export-*.csv --review-state previous-input.json --out report-input.json

Use --review-state on refreshes to preserve human review holds. This command does
not publish reports, update production tables, or connect a scheduled pipeline.
"""
import argparse
import csv
import json
import os
from pathlib import Path


def merge(exports, previous=None):
    csv.field_size_limit(50_000_000)
    combined = None
    paths, evidence, research, unresolved = {}, {}, {}, []
    statuses = {'needs_confirmation', 'blocked_declined', 'ready_for_human_review'}
    for source in exports:
        with Path(source).open(newline='') as handle:
            for row in csv.DictReader(handle):
                result = json.loads(row['result'])
                payload = result.get('payload')
                if not isinstance(payload, dict):
                    raise ValueError('Export has no full payload; rerun one target with include_payload=true')
                if combined is None:
                    combined = {k: v for k, v in payload.items()
                                if k not in ('paths', 'evidence', 'target_research', 'coverage')}
                for key in ('as_of', 'profiles_checked_at', 'requester_name', 'model', 'weights'):
                    if payload.get(key) != combined.get(key):
                        raise ValueError('Incompatible payload metadata: ' + key)
                for path in payload['paths']:
                    if path['id'] in paths:
                        raise ValueError('Duplicate path in exports: ' + path['id'])
                    if path['review_status'] not in statuses:
                        raise ValueError('Invalid review status')
                    paths[path['id']] = path
                for record in payload.get('evidence', []):
                    old = evidence.get(record['id'])
                    if old is not None and old != record:
                        raise ValueError('Conflicting evidence ID: ' + record['id'])
                    evidence[record['id']] = record
                for key, value in payload.get('target_research', {}).items():
                    if key in research and research[key] != value:
                        raise ValueError('Conflicting target research: ' + key)
                    research[key] = value
                unresolved.extend(result.get('coverage', {}).get('unresolved', []))
    if combined is None:
        raise ValueError('No payload rows found')
    if previous is not None:
        seen = set()
        for old in previous['paths']:
            if old['id'] in seen:
                raise ValueError('Duplicate path in previous review state')
            seen.add(old['id'])
            if old['review_status'] not in statuses:
                raise ValueError('Invalid prior review status')
            current = paths.get(old['id'])
            if current:
                if any(old[k] != current[k] for k in ('target_id', 'connector_id')):
                    raise ValueError('Path identity changed while preserving review state')
                current['review_status'] = old['review_status']
    combined.update(paths=list(paths.values()), evidence=list(evidence.values()),
                    target_research=research, coverage={'unresolved': unresolved})
    for path in combined['paths']:
        for feature in path['features'].values():
            if feature['value'] and any(eid not in evidence for eid in feature['evidence_ids']):
                raise ValueError('Positive feature is missing evidence')
    return combined


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('exports', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--review-state', type=Path)
    args = parser.parse_args()
    try:
        previous = json.loads(args.review_state.read_text()) if args.review_state else None
        result = merge(args.exports, previous)
        with os.fdopen(os.open(args.out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as handle:
            json.dump(result, handle, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f'Payload merge failed: {exc}\n')
    print(json.dumps({'paths': len(result['paths']), 'unresolved': len(result['coverage']['unresolved']),
                      'prior_review_state_applied': previous is not None, 'out': str(args.out.resolve())}))


if __name__ == '__main__':
    main()
