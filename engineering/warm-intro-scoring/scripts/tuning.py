"""Validate normalized evidence features and render a private, offline weight tuner."""
import argparse
from datetime import date
import json
import math
import os
from pathlib import Path

DEFAULT_WEIGHTS = dict(direct_intro=160, work_overlap=80, school_overlap=20,
                       relationship=15, role_industry=20, investor_portfolio=3,
                       appearance=20, board_overlap=30,
                       city_overlap=10, industry_match=10, community_match=2, investor_role=120)
TIMED = {'work_overlap', 'school_overlap', 'board_overlap', 'city_overlap', 'investor_role'}
TIMING = {'verified_overlap', 'non_overlap', 'unknown', 'not_applicable'}
MODEL = 'evidence-feature-heuristic-v3'
REVIEW_STATUSES = {'needs_confirmation', 'blocked_declined', 'ready_for_human_review'}


def number(value, label, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (maximum is not None and value > maximum):
        raise ValueError(f'{label} must be finite and nonnegative' + (' and <= 1' if maximum == 1 else ''))
    return value


def weights(config=None):
    config = {} if config is None else config
    if not isinstance(config, dict) or set(config) - DEFAULT_WEIGHTS.keys():
        raise ValueError('Unknown weight keys or invalid configuration')
    return {key: number(config.get(key, default), key) for key, default in DEFAULT_WEIGHTS.items()}


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty string')
    return value


def exact_date(value, label):
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label} must be a full YYYY-MM-DD date') from None
    if value != parsed.isoformat():
        raise ValueError(f'{label} must be a full YYYY-MM-DD date')
    return parsed


def normalize(data):
    if not isinstance(data, dict) or not isinstance(data.get('paths'), list) or not data['paths']:
        raise ValueError('Input must contain a nonempty paths list')
    as_of = exact_date(data.get('as_of'), 'as_of')
    rows, seen, pairs = [], set(), set()
    for raw in data['paths']:
        if not isinstance(raw, dict):
            raise ValueError('Each path must be an object')
        row = {key: required_text(raw.get(key), key) for key in ('id','target_id','target_name','connector_id','connector_name','review_status')}
        if row['id'] in seen:
            raise ValueError('Duplicate path ID')
        seen.add(row['id'])
        pair = (row['connector_id'], row['target_id'])
        if pair[0] == pair[1]:
            raise ValueError('Connector and target must be different people')
        if pair in pairs:
            raise ValueError('Duplicate connector/target pair')
        pairs.add(pair)
        if row['review_status'] not in REVIEW_STATUSES:
            raise ValueError('Unsupported review status')
        for key in ('target_company', 'target_title', 'connector_company', 'connector_title', 'requester_name'):
            if key in raw:
                row[key] = required_text(raw[key], key)
        row['baseline_score'] = number(raw.get('baseline_score'), 'baseline_score')
        supplied = raw.get('features', {})
        if not isinstance(supplied, dict) or set(supplied) - DEFAULT_WEIGHTS.keys():
            raise ValueError('Unsupported feature keys or invalid features')
        row['features'] = {}
        for key in DEFAULT_WEIGHTS:
            f = supplied.get(key)
            if f is None:
                f = dict(value=0, evidence_ids=[], explanation='Unknown: no evidence supplied', timing_status='unknown')
            if not isinstance(f, dict):
                raise ValueError('Feature must be an object')
            value = number(f.get('value'), key, 1)
            ids = f.get('evidence_ids', [])
            if not isinstance(ids, list) or any(not isinstance(x, str) or not x.strip() for x in ids) or (value > 0 and not ids):
                raise ValueError('Positive features require nonempty evidence IDs')
            explanation = required_text(f.get('explanation'), 'explanation')
            timing = f.get('timing_status', 'unknown')
            if timing not in TIMING:
                raise ValueError('Unsupported timing status')
            feature = dict(value=value, evidence_ids=list(ids), explanation=explanation, timing_status=timing)
            if key in TIMED and value > 0:
                if timing != 'verified_overlap':
                    raise ValueError(f'{key} requires verified dated overlap')
                start = exact_date(f.get('overlap_start'), 'overlap_start')
                end = exact_date(f.get('overlap_end'), 'overlap_end')
                if start > end or end > as_of:
                    raise ValueError('Overlap must have start <= end <= as_of')
                feature.update(overlap_start=start.isoformat(), overlap_end=end.isoformat())
            row['features'][key] = feature
        rows.append(row)
    return rows


def rank(data, config=None):
    chosen = weights(config)
    rows = normalize(data)
    for row in rows:
        row['tuned_score'] = number(sum(row['features'][key]['value'] * w for key, w in chosen.items()), 'tuned_score')
        row['ready_for_human_review'] = row['review_status'] == 'ready_for_human_review'
    return sorted(rows, key=lambda r: (-r['tuned_score'], r['connector_name'].casefold(), r['id']))


def render(data, config=None):
    payload = dict(paths=rank(data, config), as_of=data['as_of'], weights=weights(config), defaults=DEFAULT_WEIGHTS, model=MODEL)
    for key in ('requester_name', 'profiles_checked_at'):
        if key in data:
            payload[key] = required_text(data[key], key)
    registry = data.get('evidence', [])
    if not isinstance(registry, list):
        raise ValueError('evidence must be a list')
    payload['evidence'] = []
    ids = set()
    for record in registry:
        if not isinstance(record, dict):
            raise ValueError('Each evidence record must be an object')
        clean = {key: required_text(record.get(key), key) for key in ('id', 'source', 'detail', 'observed_at')}
        if exact_date(clean['observed_at'], 'observed_at') > exact_date(data['as_of'], 'as_of'):
            raise ValueError('Evidence observation cannot be after as_of')
        if clean['id'] in ids:
            raise ValueError('Duplicate evidence ID')
        ids.add(clean['id'])
        payload['evidence'].append(clean)
    if 'evidence' in data:
        for row in payload['paths']:
            for feature in row['features'].values():
                if feature['value'] > 0 and any(identifier not in ids for identifier in feature['evidence_ids']):
                    raise ValueError('Positive feature references a missing evidence record')
    research = data.get('target_research', {})
    if not isinstance(research, dict):
        raise ValueError('target_research must be an object')
    payload['target_research'] = {}
    for target_id, records in research.items():
        required_text(target_id, 'target_id')
        if not isinstance(records, list):
            raise ValueError('Target research must be a list')
        cleaned = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError('Research record must be an object')
            clean = {key: required_text(record.get(key), key) for key in ('label', 'detail', 'source_url', 'observed_at', 'provider')}
            if exact_date(clean['observed_at'], 'observed_at') > exact_date(data['as_of'], 'as_of'):
                raise ValueError('Research observation cannot be after as_of')
            cleaned.append(clean)
        payload['target_research'][target_id] = cleaned
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return (Path(__file__).resolve().parents[1] / 'assets/tuning.html').read_text().replace('__TUNING_DATA__', encoded)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--weights', type=Path, help='JSON object mapping dimension names to weights')
    a = p.parse_args()
    output = render(json.loads(a.input.read_text()), json.loads(a.weights.read_text()) if a.weights else None)
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        f.write(output)
    print(f'Private local artifact: {a.output.resolve()}')

if __name__ == '__main__':
    main()
