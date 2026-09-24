#!/usr/bin/env python3
"""Merge include_payload CSV exports into one report input, offline.

python3 plays/merge-payloads.py export-*.csv --out report-input.json
python3 plays/merge-payloads.py export-*.csv --review-state previous-input.json --out report-input.json

Use --review-state on refreshes to preserve human review holds. This command does
not publish reports, update production tables, or connect a scheduled pipeline.
"""
import hashlib
import argparse
import csv
import json
import os
from pathlib import Path


def merge(exports, previous=None, expected_keys=None):
    csv.field_size_limit(50_000_000)
    combined = None
    export_keys = set()
    paths, evidence, research, unresolved = {}, {}, {}, []
    statuses = {'needs_confirmation', 'blocked_declined', 'ready_for_human_review'}
    for source in exports:
        with Path(source).open(newline='') as handle:
            for row in csv.DictReader(handle):
                if row.get('key'):
                    if row['key'] in export_keys:
                        raise ValueError('Duplicate target export key')
                    export_keys.add(row['key'])
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
    if expected_keys is not None and export_keys != set(expected_keys):
        raise ValueError('Missing or unexpected target exports; compare with source manifest')
    if combined is None:
        raise ValueError('No payload rows found')
    def fingerprint(path):
        return hashlib.sha256(json.dumps(path.get('features'), sort_keys=True,
                              separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    ledger = {}
    if previous is not None:
        if previous.get('requester_name') not in (None, combined.get('requester_name')):
            raise ValueError('Prior review state belongs to a different requester')
        seen = set()
        for old in previous.get('paths', []):
            if old['id'] in seen:
                raise ValueError('Duplicate path in previous review state')
            seen.add(old['id'])
        for old in previous.get('review_state', []) + previous.get('paths', []):
            if old['review_status'] not in statuses:
                raise ValueError('Invalid prior review status')
            key = (old['connector_id'], old['target_id'])
            state = dict(id=old['id'], connector_id=key[0], target_id=key[1],
                         review_status=old['review_status'],
                         feature_hash=old.get('feature_hash', fingerprint(old)))
            if ledger.get(key, {}).get('review_status') != 'blocked_declined':
                ledger[key] = state
            current = paths.get(old['id'])
            if current and any(old[k] != current[k] for k in ('target_id', 'connector_id')):
                raise ValueError('Path identity changed while preserving review state')
    current_keys = set()
    for path in paths.values():
        key = (path['connector_id'], path['target_id'])
        if key in current_keys:
            raise ValueError('Duplicate connector-target identity')
        current_keys.add(key)
        old = ledger.get(key)
        if old:
            state = old['review_status']
            if state == 'ready_for_human_review' and old['feature_hash'] != fingerprint(path):
                state = 'needs_confirmation'
            path['review_status'] = state
        ledger[key] = dict(id=path['id'], connector_id=key[0], target_id=key[1],
                           review_status=path['review_status'], feature_hash=fingerprint(path))
    orphaned = [state for key, state in ledger.items() if key not in current_keys]
    combined.update(paths=list(paths.values()), evidence=list(evidence.values()),
                    target_research=research, review_state=list(ledger.values()), coverage={'unresolved': unresolved, 'review_states_without_paths': orphaned, 'export_completeness': 'verified' if expected_keys is not None else 'not_verified_without_source_manifest', 'exported_targets': len(export_keys)})
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
    parser.add_argument('--source-input', type=Path, help='Original FeatureInput JSON; require exactly one export for each target key')
    args = parser.parse_args()
    try:
        previous = json.loads(args.review_state.read_text()) if args.review_state else None
        expected = ['target:' + str(i) for i in range(len(json.loads(args.source_input.read_text())['targets']))] if args.source_input else None
        result = merge(args.exports, previous, expected)
        with os.fdopen(os.open(args.out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as handle:
            json.dump(result, handle, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f'Payload merge failed: {exc}\n')
    print(json.dumps({'paths': len(result['paths']), 'unresolved': len(result['coverage']['unresolved']),
                      'prior_review_state_applied': previous is not None, 'out': str(args.out.resolve())}))


if __name__ == '__main__':
    main()
