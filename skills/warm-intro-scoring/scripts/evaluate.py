#!/usr/bin/env python3
"""Offline, stdlib-only paired ranking diagnostics (schema version 1).

Usage: python3 evaluate.py INPUT.json --output NEW.json [--html NEW.html]
Outputs are private mode 0600, created exclusively; existing files are never replaced.
Invalid input exits 2 without a report. Valid reports are diagnostic, never approval.

Schema (unknown keys, duplicate JSON keys, NaN/Infinity and naive dates rejected):
Root required: as_of (evaluation observation cutoff; timezone-aware ISO timestamp), queries (list).
Optional: seed (integer, default 1729), bootstrap_samples (100..100000, default
2000), outcome_window_days (1..3650, default 14), outcomes (list), split (below),
baseline_version/candidate_version (nonempty strings), fictional (boolean).
Query: scored_at (timezone-aware scoring cutoff <= root as_of), id, target_id, account_id (nonempty strings), labels ({path_id: 0|1|null}),
baseline, candidate (ordered lists of every label ID exactly once), paths (list).
Empty universes represent no-route queries. Order is supplied; no score ties or
sorting are inferred. Query IDs must be unique; path IDs unique within query.
Path: id, status (ready|research|blocked), sender_edge and target_edge
(strong|medium|weak|unknown), willingness (yes|no|unknown), feature_dates
(nonempty list of timezone-aware timestamps, each <= query scored_at). Paths must exactly
cover the candidate universe. Ready requires both edges strong/medium and yes.
Split, when supplied, requires train_target_ids, test_target_ids,
train_account_ids, test_account_ids (unique string lists). Train/test sets may not
overlap; each query target/account must belong to the respective test set.
Outcome: id, status (draft|sent), created_at, reply, meeting (each bool|null).
Sent also requires sent_at and observed_through. True outcomes require reply_at
or meeting_at; false/null outcomes must omit those timestamps. Drafts must have
null outcomes and omit sent/observation/event timestamps. All dates <= as_of;
created_at <= sent_at <= observed_through, and event dates are in that interval.
A send is mature only if observed_through >= sent_at + outcome_window_days.
Both reply and meeting must be observed (non-null) for the shared denominator.
Open windows are excluded even after an early success. True events after the
fixed horizon do not count toward its numerator; raw event counts retain them.

Metrics: macro recall@3, full-list MRR, binary nDCG@3 only on fully judged queries
with >=1 relevant path. Paired candidate-minus-baseline query deltas use a seeded
account-cluster bootstrap, percentile 95% intervals (linear interpolation). Account bootstrap assumes independent accounts and retains all queries within each
resampled account. The point estimate remains query-weighted. Small samples
(<30 eligible accounts) are explicitly insufficient. All results
are exploratory, observational, and never prove causal uplift. Metadata gates
cannot establish source truth, independent labels, or actual relationship quality.
"""
import argparse
from datetime import datetime, timedelta
import html
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys


def fail(message):
    raise ValueError(message)


def obj(value, required, optional=(), where='record'):
    if not isinstance(value, dict): fail(f'{where}: expected object')
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    if missing: fail(f'{where}: missing fields {sorted(missing)}')
    if unknown: fail(f'{where}: unknown fields {sorted(unknown)}')


def string(value, where):
    if not isinstance(value, str) or not value.strip(): fail(f'{where}: expected nonempty string')
    return value


def strings(value, where):
    if not isinstance(value, list): fail(f'{where}: expected list')
    for item in value: string(item, where)
    if len(value) != len(set(value)): fail(f'{where}: duplicate IDs')
    return set(value)


def choice(value, choices, where):
    if not isinstance(value, str) or value not in choices: fail(f'{where}: expected one of {sorted(choices)}')


def stamp(value, where):
    string(value, where)
    try: parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError: fail(f'{where}: invalid timestamp')
    if parsed.tzinfo is None or parsed.utcoffset() is None: fail(f'{where}: timezone required')
    return parsed


def no_nonfinite(value):
    if isinstance(value, float) and not math.isfinite(value): fail('nonfinite number')
    if isinstance(value, dict):
        for item in value.values(): no_nonfinite(item)
    elif isinstance(value, list):
        for item in value: no_nonfinite(item)


def loads(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: fail(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda value: fail(f'nonfinite number: {value}'))


def integer(value, lower, upper, where):
    if type(value) is not int or not lower <= value <= upper: fail(f'{where}: integer {lower}..{upper} required')
    return value


def validate(data):
    no_nonfinite(data)
    obj(data, ('as_of', 'queries'), ('seed', 'bootstrap_samples', 'outcome_window_days', 'outcomes', 'split', 'baseline_version', 'candidate_version', 'fictional'), 'root')
    cutoff = stamp(data['as_of'], 'as_of')
    integer(data.get('seed', 1729), 0, 2**63-1, 'seed')
    integer(data.get('bootstrap_samples', 2000), 100, 100000, 'bootstrap_samples')
    integer(data.get('outcome_window_days', 14), 1, 3650, 'outcome_window_days')
    for name in ('baseline_version', 'candidate_version'):
        if name in data: string(data[name], name)
    if 'fictional' in data and type(data['fictional']) is not bool: fail('fictional: boolean required')
    if not isinstance(data['queries'], list): fail('queries: expected list')
    split = data.get('split')
    if 'split' in data and split is None: fail('split: expected object, not null')
    if split is not None:
        keys = ('train_target_ids', 'test_target_ids', 'train_account_ids', 'test_account_ids')
        obj(split, keys, where='split')
        sets = {key: strings(split[key], key) for key in keys}
        for group in ('target', 'account'):
            if sets[f'train_{group}_ids'] & sets[f'test_{group}_ids']: fail(f'train/test {group} leakage')
    query_ids = set()
    for query in data['queries']:
        obj(query, ('id', 'scored_at', 'target_id', 'account_id', 'labels', 'baseline', 'candidate', 'paths'), where='query')
        for name in ('id', 'target_id', 'account_id'): string(query[name], name)
        if query['id'] in query_ids: fail('duplicate query ID')
        query_ids.add(query['id'])
        if split is not None:
            for group in ('target', 'account'):
                if query[f'{group}_id'] not in sets[f'test_{group}_ids']: fail(f'query {group} missing from test split')
        scored_at = stamp(query['scored_at'], 'scored_at')
        if scored_at > cutoff: fail('scored_at after evaluation as_of')
        labels = query['labels']
        if not isinstance(labels, dict): fail('labels: expected object')
        for key, value in labels.items():
            string(key, 'label ID')
            if value is not None and (type(value) is not int or value not in (0, 1)): fail('label must be 0, 1 or null')
        for ranker in ('baseline', 'candidate'):
            if strings(query[ranker], ranker) != set(labels): fail(f'{ranker}: candidate universe mismatch')
        if not isinstance(query['paths'], list): fail('paths: expected list')
        path_ids = set()
        for path in query['paths']:
            obj(path, ('id', 'status', 'sender_edge', 'target_edge', 'willingness', 'feature_dates'), where='path')
            string(path['id'], 'path ID')
            if path['id'] in path_ids: fail('duplicate path ID')
            path_ids.add(path['id'])
            choice(path['status'], ('ready', 'research', 'blocked'), 'path status')
            for edge in ('sender_edge', 'target_edge'): choice(path[edge], ('strong', 'medium', 'weak', 'unknown'), edge)
            choice(path['willingness'], ('yes', 'no', 'unknown'), 'willingness')
            dates = path['feature_dates']
            if not isinstance(dates, list) or not dates: fail('feature_dates: nonempty list required')
            for date in dates:
                if stamp(date, 'feature date') > scored_at: fail('post-scored_at feature leakage')
            if path['status'] == 'ready' and (path['sender_edge'] in ('weak', 'unknown') or path['target_edge'] in ('weak', 'unknown') or path['willingness'] != 'yes'):
                fail('unsafe ready path: both supported edges and yes willingness required')
        if path_ids != set(labels): fail('paths: candidate universe mismatch')
    outcomes = data.get('outcomes', [])
    if not isinstance(outcomes, list): fail('outcomes: expected list')
    ids = set()
    for outcome in outcomes:
        obj(outcome, ('id', 'status', 'created_at', 'reply', 'meeting'), ('sent_at', 'observed_through', 'reply_at', 'meeting_at'), 'outcome')
        string(outcome['id'], 'outcome ID')
        if outcome['id'] in ids: fail('duplicate outcome ID')
        ids.add(outcome['id'])
        choice(outcome['status'], ('draft', 'sent'), 'outcome status')
        dates = {key: stamp(value, key) for key, value in outcome.items() if key.endswith('_at') or key == 'observed_through'}
        if any(date > cutoff for date in dates.values()): fail('outcome timestamp after as_of')
        for event in ('reply', 'meeting'):
            if outcome[event] is not None and type(outcome[event]) is not bool: fail(f'{event}: boolean or null required')
            if (outcome[event] is True) != (f'{event}_at' in dates): fail(f'{event}: true requires timestamp; false/null forbids timestamp')
        if outcome['status'] == 'draft':
            if set(dates) != {'created_at'} or outcome['reply'] is not None or outcome['meeting'] is not None: fail('draft must have unknown outcomes and no sent/event timestamps')
        else:
            if not {'sent_at', 'observed_through'} <= dates.keys(): fail('sent outcome missing timestamps')
            if not dates['created_at'] <= dates['sent_at'] <= dates['observed_through']: fail('invalid sent chronology')
            for event in ('reply_at', 'meeting_at'):
                if event in dates and not dates['sent_at'] <= dates[event] <= dates['observed_through']: fail('event outside observed interval')
    return cutoff


def rank_metrics(ranking, labels):
    relevant = sum(labels.values())
    gains = [labels[key] for key in ranking]
    ideal = sum(1 / math.log2(i+2) for i in range(min(3, relevant)))
    return {'recall@3': sum(gains[:3]) / relevant,
            'mrr': 1 / (gains.index(1)+1),
            'ndcg@3': sum(gain / math.log2(i+2) for i, gain in enumerate(gains[:3])) / ideal}


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values)-1) * fraction
    low = math.floor(position); high = math.ceil(position)
    return values[low] + (values[high]-values[low]) * (position-low)


def outcome_report(data):
    result = dict(total_records=0, drafts=0, sent=0, sent_immature=0, sent_unobserved=0,
                  matured_sent_denominator=0, replies_within_window=0, meetings_within_window=0,
                  raw_reply_events=0, raw_meeting_events=0)
    window = timedelta(days=data.get('outcome_window_days', 14))
    for row in data.get('outcomes', []):
        result['total_records'] += 1
        for event in ('reply', 'meeting'):
            result[f'raw_{event}_events'] += int(row[event] is True)
        if row['status'] == 'draft': result['drafts'] += 1; continue
        result['sent'] += 1
        horizon = stamp(row['sent_at'], 'sent_at') + window
        if stamp(row['observed_through'], 'observed_through') < horizon:
            result['sent_immature'] += 1; continue
        if row['reply'] is None or row['meeting'] is None:
            result['sent_unobserved'] += 1; continue
        result['matured_sent_denominator'] += 1
        for event, key in (('reply', 'replies_within_window'), ('meeting', 'meetings_within_window')):
            if row[event] and stamp(row[f'{event}_at'], event) <= horizon: result[key] += 1
    denominator = result['matured_sent_denominator']
    result.update(window_days=data.get('outcome_window_days', 14),
                  reply_rate=result['replies_within_window']/denominator if denominator else None,
                  meeting_rate=result['meetings_within_window']/denominator if denominator else None,
                  interpretation='Observed selected sends only; no causal comparison between rankers. Null rate means unavailable.')
    return result


def evaluate(data):
    validate(data)
    coverage = dict(total_queries=len(data['queries']), eligible_queries=0, total_labels=0, judged_labels=0,
                    exclusions=dict(incomplete_judgments=0, no_relevant=0))
    rows = []
    for query in data['queries']:
        labels = query['labels']
        coverage['total_labels'] += len(labels)
        coverage['judged_labels'] += sum(value is not None for value in labels.values())
        reason = 'incomplete_judgments' if None in labels.values() else 'no_relevant' if not sum(labels.values()) else None
        row = dict(id=query['id'], scored_at=query['scored_at'], target_id=query['target_id'], account_id=query['account_id'], exclusion=reason)
        if reason: coverage['exclusions'][reason] += 1
        else:
            coverage['eligible_queries'] += 1
            for ranker in ('baseline', 'candidate'): row[ranker] = rank_metrics(query[ranker], labels)
            row['delta'] = {key: row['candidate'][key]-row['baseline'][key] for key in row['baseline']}
        rows.append(row)
    eligible = [row for row in rows if row['exclusion'] is None]
    n = len(eligible); samples = data.get('bootstrap_samples', 2000); seed = data.get('seed', 1729)
    rng = random.Random(seed)
    clusters = {}
    for row in eligible: clusters.setdefault(row['account_id'], []).append(row)
    accounts = sorted(clusters)
    coverage['independent_accounts'] = len(accounts)
    metrics = {}
    # Resample whole accounts, retaining all their queries and paired ranker values.
    bootstrap = {key: [] for key in ('recall@3', 'mrr', 'ndcg@3')}
    if n:
        for _ in range(samples):
            drawn = [row for _ in accounts for row in clusters[accounts[rng.randrange(len(accounts))]]]
            for key in bootstrap: bootstrap[key].append(statistics.fmean(row['delta'][key] for row in drawn))
    for key in bootstrap:
        metrics[key] = dict(baseline=statistics.fmean(row['baseline'][key] for row in eligible) if n else None,
                            candidate=statistics.fmean(row['candidate'][key] for row in eligible) if n else None,
                            delta=statistics.fmean(row['delta'][key] for row in eligible) if n else None,
                            delta_ci95=[percentile(bootstrap[key], .025), percentile(bootstrap[key], .975)] if n else None,
                            paired_query_denominator=n)
    warnings = ['Exploratory diagnostics only; not proven uplift. No automatic promotion or causal inference.',
                'Supplied metadata cannot verify source truth or independently adjudicated labels.']
    insufficient = len(accounts) < 30 or coverage['exclusions']['incomplete_judgments'] > 0 or data.get('fictional', False)
    if len(accounts) < 30: warnings.append('Small sample: fewer than 30 eligible accounts; uncertainty is unstable and evidence is insufficient.')
    if data.get('fictional', False): warnings.append('Fictional fixture: validates behavior only, not real-world accuracy.')
    if 'split' not in data:
        insufficient = True
        warnings.append('Train/test group metadata not supplied; leakage separation is unverified.')
    warnings.append('Account-cluster bootstrap assumes independent accounts; shared connectors and other cross-account dependencies are not modeled.')
    return dict(schema_version=1, as_of=data['as_of'],
                status='insufficient_evidence' if insufficient else 'diagnostic_only',
                promotion_allowed=False, gates=dict(valid=True, split_checked='split' in data),
                versions={key:data.get(key) for key in ('baseline_version', 'candidate_version')},
                coverage=coverage, metrics=metrics, queries=rows, outcomes=outcome_report(data),
                bootstrap=dict(seed=seed, samples=samples, unit='account', method='paired percentile 95%, linear interpolation'),
                warnings=warnings)


def html_report(report):
    def esc(value): return html.escape(str(value))
    def number(value): return 'Unavailable' if value is None else f'{value:.3f}'
    coverage = report['coverage']; outcomes = report['outcomes']
    title = report['status'].replace('_', ' ').capitalize()
    metric_rows = ''.join(
        '<tr><th scope="row">'+esc(name)+'</th><td>'+number(metric['baseline'])+
        '</td><td>'+number(metric['candidate'])+'</td><td>'+number(metric['delta'])+
        '</td><td>'+('Unavailable' if metric['delta_ci95'] is None else
        ' to '.join(number(v) for v in metric['delta_ci95']))+'</td></tr>'
        for name, metric in report['metrics'].items())
    query_rows = ''.join('<tr><th scope="row">'+esc(row['id'])+'</th><td>'+esc(row['account_id'])+
        '</td><td>'+esc(row['exclusion'] or 'Eligible')+'</td><td>'+
        number(row.get('delta', {}).get('recall@3'))+'</td></tr>' for row in report['queries'])
    warnings = ''.join('<li>'+esc(w)+'</li>' for w in report['warnings'])
    details = html.escape(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Warm intro evaluation</title>
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f6f5ef;color:#1d3029;font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;padding:44px 22px}}h1{{font-size:clamp(28px,5vw,48px);line-height:1.1;margin:12px 0}}h2{{font-size:22px}}.eyebrow{{letter-spacing:.12em;text-transform:uppercase;font-size:12px}}.verdict{{border-left:5px solid #a56b15;background:#fff5dc;padding:16px 20px;margin:24px 0}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{padding:20px;border:1px solid #d2d9cf;border-radius:12px;background:white}}.card strong{{font-size:28px;display:block}}section{{margin-top:32px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #dbe0d6;font-variant-numeric:tabular-nums}}thead{{background:#e3ecdf}}p,li{{max-width:85ch}}small{{color:#4c6156}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px}}summary{{cursor:pointer;padding:14px;border:1px solid #aab9a7;border-radius:8px}}summary:focus-visible{{outline:3px solid #315d48}}
</style></head><body><main><div class="eyebrow">Warm intro scoring · evaluation</div>
<h1>Does the new ranking help?</h1><p>A paired comparison with explicit evidence coverage and outcome windows.</p>
<div class="verdict"><strong>{esc(title)}</strong><br>No automatic promotion. These diagnostics do not establish causal uplift.</div>
<div class="cards"><div class="card"><small>Eligible queries / total</small><strong>{coverage['eligible_queries']} / {coverage['total_queries']}</strong></div>
<div class="card"><small>Judged labels / total</small><strong>{coverage['judged_labels']} / {coverage['total_labels']}</strong></div>
<div class="card"><small>Mature observed sends</small><strong>{outcomes['matured_sent_denominator']}</strong></div></div>
<section><h2>Ranking comparison</h2><p>Candidate minus baseline. Intervals resample accounts; repeated relationships across accounts may still be dependent.</p>
<div class="scroll"><table><thead><tr><th scope="col">Metric</th><th scope="col">Baseline</th><th scope="col">Candidate</th><th scope="col">Delta</th><th scope="col">95% interval</th></tr></thead><tbody>{metric_rows}</tbody></table></div></section>
<section><h2>Observed outcomes · {outcomes['window_days']}-day window</h2>
<p>Reply rate: <strong>{number(outcomes['reply_rate'])}</strong> · Meeting rate: <strong>{number(outcomes['meeting_rate'])}</strong>. Rates are proportions, conditional on mature, fully observed sends.</p>
<p>{outcomes['drafts']} drafts · {outcomes['sent_immature']} open windows · {outcomes['sent_unobserved']} mature sends with unknown outcomes. These records are excluded from the rate denominator.</p></section>
<section><h2>Coverage by query</h2><div class="scroll"><table><thead><tr><th scope="col">Query</th><th scope="col">Account</th><th scope="col">Eligibility</th><th scope="col">Recall@3 delta</th></tr></thead><tbody>{query_rows}</tbody></table></div></section>
<section><h2>Interpretation limits</h2><ul>{warnings}</ul></section>
<section><details><summary>Inspect complete scorecard and reproducibility metadata</summary><pre>{details}</pre></details></section>
</main></body></html>\n'''


def write_reports(contents):
    paths = [Path(path).absolute() for path, _ in contents]
    if len(set(paths)) != len(paths): fail('report destinations must be distinct')
    for path in paths:
        if os.path.lexists(path): fail(f'refusing to overwrite: {path}')
    created = []
    try:
        for path, (_, content) in zip(paths, contents):
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as handle: handle.write(content)
    except Exception:
        for path in created: path.unlink(missing_ok=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--html', type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(loads(args.input.read_text(encoding='utf-8')))
        contents = [(args.output, json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n')]
        if args.html: contents.append((args.html, html_report(report)))
        write_reports(contents)
    except (ValueError, OSError, OverflowError) as error:
        print(f'invalid evaluation: {error}', file=sys.stderr)
        return 2
    print(f"{report['status']}: {report['coverage']['eligible_queries']}/{report['coverage']['total_queries']} eligible queries; report written")
    return 0


if __name__ == '__main__': sys.exit(main())
