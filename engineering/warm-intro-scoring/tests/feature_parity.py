"""Compare extracted paths with a frozen Python reference; never writes personal data.
Usage: python3 tests/feature_parity.py reference.json extracted.json report.json
Reports evidence ID, date, feature, baseline and coverage drift. Explanatory wording
and unused registry records are intentionally outside the numerical parity contract.
"""
import collections,json,sys
from pathlib import Path
FIELDS=('value','timing_status','overlap_start','overlap_end','work_context')
def compare(reference,actual):
    old={p['id']:p for p in reference['paths']};new={p['id']:p for p in actual['paths']}
    count=collections.Counter();examples=[]
    def fail(reason,path,feature=None):
        count[reason]+=1
        if len(examples)<20:examples.append(dict(path_id=path,feature=feature,reason=reason))
    for pid in old.keys()-new.keys():fail('missing_path',pid)
    for pid in new.keys()-old.keys():fail('extra_path',pid)
    for pid in old.keys()&new.keys():
        a,b=old[pid],new[pid]
        for key in ('target_id','connector_id','target_name','target_company','target_title','connector_name','connector_company','connector_title','baseline_score','review_status'):
            if a.get(key)!=b.get(key):fail(key,pid)
        for key in set(a['features'])|set(b['features']):
            x,y=a['features'].get(key,{}),b['features'].get(key,{})
            for field in FIELDS:
                if x.get(field)!=y.get(field):fail('feature_'+field,pid,key)
            if set(x.get('evidence_ids',[]))!=set(y.get('evidence_ids',[])):fail('evidence_ids',pid,key)
    registry={e['id']:e for e in actual.get('evidence',[])}
    for p in new.values():
        for key,f in p['features'].items():
            if f['value'] and any(e not in registry for e in f['evidence_ids']):fail('missing_evidence_record',p['id'],key)
    return dict(passed=not count,reference_paths=len(old),extracted_paths=len(new),difference_counts=dict(count),examples=examples,coverage=actual.get('coverage'),excluded_comparisons=['explanatory wording','unused evidence registry records'])
if __name__=='__main__':
    report=compare(json.loads(Path(sys.argv[1]).read_text()),json.loads(Path(sys.argv[2]).read_text()))
    Path(sys.argv[3]).write_text(json.dumps(report,indent=2));Path(sys.argv[3]).chmod(0o600)
    print(json.dumps({k:v for k,v in report.items() if k not in ('examples','coverage')},indent=2))
    raise SystemExit(0 if report['passed'] else 1)
