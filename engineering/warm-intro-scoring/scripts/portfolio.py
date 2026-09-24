"""Expand a source-cited company → investor → portfolio graph, offline.

Usage: python3 portfolio.py graph.json --company COMPANY_ID --output expansion.json
The graph comes from bounded source retrieval; this traversal never claims the
public portfolio is exhaustive and never promotes a relationship or intro.
"""
import argparse
from datetime import date
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from evaluate import loads,write_reports

def source_date(value):
    """Parse calendar and ISO-week dates consistently on Python 3.10 and later."""
    if not isinstance(value,str):raise ValueError('Invalid source observation')
    calendar=re.fullmatch(r'([0-9]{4})(?:-([0-9]{2})-([0-9]{2})|([0-9]{2})([0-9]{2}))',value)
    if calendar:
        return date(int(calendar[1]),int(calendar[2] or calendar[4]),int(calendar[3] or calendar[5]))
    week=re.fullmatch(r'([0-9]{4})(?:-W([0-9]{2})(?:-([1-7]))?|W([0-9]{2})([1-7])?)',value)
    if week:
        return date.fromisocalendar(int(week[1]),int(week[2] or week[4]),int(week[3] or week[5] or 1))
    raise ValueError('Invalid source observation')


def expand(graph,company_id):
    def index(rows):
        out={}
        for row in rows:
            key=row.get('id')
            if not isinstance(key,str) or not key.strip() or key in out:raise ValueError('unique canonical IDs required')
            out[key]=row
        return out
    companies=index(graph['companies']);investors=index(graph['investors'])
    if company_id not in companies:raise ValueError('seed company not resolved')
    edges=[];seen=set()
    for edge in graph['edges']:
        company=edge.get('company_id');investor=edge.get('investor_id');source=edge.get('source_url','')
        parsed=urlsplit(source)
        if company not in companies or investor not in investors:raise ValueError('unresolved edge endpoint')
        if parsed.scheme not in ('https','http') or not parsed.hostname:raise ValueError('source URL required')
        observed=source_date(edge['observed_at'])
        if observed>date.today():raise ValueError('future source observation')
        key=(company,investor,source)
        if key not in seen:seen.add(key);edges.append(edge)
    seed_edges=[e for e in edges if e['company_id']==company_id]
    investor_ids={e['investor_id'] for e in seed_edges}
    portfolio_edges=[e for e in edges if e['investor_id'] in investor_ids and e['company_id']!=company_id]
    company_ids={e['company_id'] for e in portfolio_edges}
    return dict(company=companies[company_id],investors=[investors[i] for i in sorted(investor_ids)],
                portfolio_companies=[companies[c] for c in sorted(company_ids)],
                seed_evidence=seed_edges,portfolio_evidence=portfolio_edges,
                coverage_status='partial' if seed_edges else 'no_disclosed_edges',
                source_coverage=graph.get('coverage',graph.get('coverage_report',{})),
                interpretation='All retrievable source-cited edges in this snapshot, not all investments. Portfolio adjacency is context, not proof of a personal tie or board role.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('graph',type=Path);p.add_argument('--company',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    try:
        r=expand(loads(a.graph.read_text()),a.company);write_reports([(a.output,json.dumps(r,indent=2)+'\n')])
    except (ValueError,KeyError,TypeError,OSError):print('Invalid graph, unresolved company or unavailable output path.');return 2
    print(f"{len(r['investors'])} disclosed investors; {len(r['portfolio_companies'])} portfolio companies; {r['coverage_status']}")
    return 0
if __name__=='__main__':raise SystemExit(main())
