"""Render scored-path CSV as a standalone private review artifact (stdlib only)."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
from score import FIELDS


def render(rows):
    clean=[]
    seen=set()
    for row in rows:
        if not all(row.get(k) for k in ('campaign_id','owner_id','connector_id','target_id','path_id')):
            raise ValueError('Stable path identities required')
        if row['path_id'] in seen:
            raise ValueError('Duplicate path ID')
        seen.add(row['path_id'])
        for k in ('total_score','direct_intro_score','work_overlap_score','relationship_score','school_city_community_score','role_industry_score','investor_score'):
            if not math.isfinite(float(row[k])) or float(row[k]) < 0:
                raise ValueError('Scores must be finite and nonnegative')
        clean.append({k:row.get(k,'') for k in FIELDS})
    template=(Path(__file__).parent.parent/'assets/review.html').read_text()
    # Escape HTML parser delimiters inside JSON, not just JavaScript quotes.
    payload=json.dumps(clean,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return template.replace('__PATH_DATA__',payload)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    with a.input.open(newline='') as f: output=render(list(csv.DictReader(f)))
    with os.fdopen(os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:f.write(output)
    print(f'Private local artifact: {a.output.resolve()}')
