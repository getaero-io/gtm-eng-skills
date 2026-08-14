#!/usr/bin/env python3
"""Mine Clay HAR captures into a full endpoint surface map.

Normalizes ids (t_xxx, gv_xxx, wb_xxx, f_xxx, r_xxx, numeric) into {placeholders}
so distinct routes collapse into one row each.
"""
import json, re, sys, glob, os
from collections import defaultdict

# Each pattern is anchored to a COMPLETE path segment via (?=/|$). Without that
# boundary '/v3/12345abc' would normalize to '/v3/{NUM_ID}abc' and collapse
# unrelated routes. UUIDs are matched case-insensitively so uppercase variants
# do not fragment an otherwise identical route.
_END = r'(?=/|$)'
ID_PATTERNS = [
    (re.compile(r'/t_[A-Za-z0-9]{8,}' + _END), '/{TABLE_ID}'),
    (re.compile(r'/gv_[A-Za-z0-9]{8,}' + _END), '/{VIEW_ID}'),
    (re.compile(r'/wb_[A-Za-z0-9]{8,}' + _END), '/{WORKBOOK_ID}'),
    (re.compile(r'/f_[A-Za-z0-9]{8,}' + _END), '/{FIELD_ID}'),
    (re.compile(r'/r_[A-Za-z0-9]{8,}' + _END), '/{RECORD_ID}'),
    (re.compile(r'/ws_[A-Za-z0-9]{8,}' + _END), '/{WORKSPACE_ID}'),
    (re.compile(r'/src_[A-Za-z0-9]{8,}' + _END), '/{SOURCE_ID}'),
    (re.compile(r'/s_[A-Za-z0-9]{8,}' + _END), '/{SOURCE_ID}'),
    (re.compile(r'/aa_[A-Za-z0-9]{8,}' + _END), '/{APP_ACCOUNT_ID}'),
    (re.compile(r'/act_[A-Za-z0-9]{8,}' + _END), '/{ACTION_ID}'),
    (re.compile(r'/fol_[A-Za-z0-9]{8,}' + _END), '/{FOLDER_ID}'),
    (re.compile(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' + _END,
        re.IGNORECASE), '/{UUID}'),
    (re.compile(r'/\d{4,}' + _END), '/{NUM_ID}'),
]

def norm(path):
    for pat, rep in ID_PATTERNS:
        path = pat.sub(rep, path)
    return path

def shape(v, depth=0):
    """Compact type-shape of a JSON value."""
    if depth > 2:
        return '...'
    if isinstance(v, dict):
        if not v:
            return '{}'
        ks = list(v.keys())[:12]
        return '{' + ','.join(ks) + (',...' if len(v) > 12 else '') + '}'
    if isinstance(v, list):
        if not v:
            return '[]'
        return '[' + shape(v[0], depth + 1) + ']'
    return type(v).__name__

def main(files):
    routes = defaultdict(lambda: {
        'methods': set(), 'statuses': set(), 'count': 0,
        'req_shapes': set(), 'resp_shapes': set(), 'queries': set(),
        'sources': set(), 'example': None,
    })
    for fp in files:
        name = os.path.basename(fp)
        try:
            har = json.load(open(fp))
        except Exception as e:
            print(f'  !! {name}: {e}', file=sys.stderr)
            continue
        log = har.get('log') if isinstance(har, dict) else None
        entries = log.get('entries') if isinstance(log, dict) else None
        if not isinstance(entries, list):
            print(f'  !! {name}: no log.entries array', file=sys.stderr)
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            req = e.get('request')
            req = req if isinstance(req, dict) else {}
            url = req.get('url') or ''
            if not isinstance(url, str) or 'clay.com' not in url:
                continue
            m = re.match(r'https?://([^/]+)(/[^?#]*)(\?[^#]*)?', url)
            if not m:
                continue
            host, path, qs = m.group(1), m.group(2), (m.group(3) or '')
            # only API hosts, skip static assets
            if not (host.startswith('api.') or '/v3/' in path or '/v1/' in path or '/api/' in path):
                continue
            if re.search(r'\.(js|css|png|jpg|svg|woff2?|ico|map)$', path):
                continue
            key = (host, norm(path))
            r = routes[key]
            resp = e.get('response')
            resp = resp if isinstance(resp, dict) else {}
            r['methods'].add(req.get('method') or '?')
            r['statuses'].add(resp.get('status') or 0)
            r['count'] += 1
            r['sources'].add(name)
            if qs:
                for part in qs.lstrip('?').split('&'):
                    if '=' in part:
                        r['queries'].add(part.split('=')[0])
            post = req.get('postData')
            pd = post.get('text') if isinstance(post, dict) else None
            if isinstance(pd, str) and pd:
                try:
                    r['req_shapes'].add(shape(json.loads(pd)))
                except Exception:
                    pass
            content = resp.get('content')
            content = content if isinstance(content, dict) else {}
            txt = content.get('text')
            mime = content.get('mimeType') or ''
            if isinstance(txt, str) and txt and isinstance(mime, str) and mime.startswith('application/json'):
                try:
                    r['resp_shapes'].add(shape(json.loads(txt)))
                except Exception:
                    pass
            if r['example'] is None:
                r['example'] = path
    return routes

if __name__ == '__main__':
    files = sys.argv[1:] or glob.glob(os.path.expanduser('~/Downloads/app.clay.com*.har'))
    print(f'mining {len(files)} HAR files...', file=sys.stderr)
    routes = main(files)
    out = []
    for (host, path), r in sorted(routes.items(), key=lambda kv: (-kv[1]['count'], kv[0])):
        out.append({
            'host': host, 'path': path,
            'methods': sorted(r['methods']),
            'statuses': sorted(r['statuses']),
            'calls': r['count'],
            'queryParams': sorted(r['queries'])[:15],
            'requestShapes': sorted(r['req_shapes'])[:3],
            'responseShapes': sorted(r['resp_shapes'])[:3],
            'seenIn': sorted(r['sources']),
            'example': r['example'],
        })
    outdir = os.path.dirname(os.path.abspath(sys.argv[0]))
    json.dump(out, open(os.path.join(outdir, 'clay_endpoints.json'), 'w'), indent=2)
    print(f'{len(out)} distinct routes -> clay_endpoints.json', file=sys.stderr)
    for o in out:
        print(f"{','.join(o['methods']):12} {o['host']}{o['path']}  [{o['calls']}x, {o['statuses']}]")
