"""Demonstrate outcome metrics; production inputs must be supplied explicitly."""
import argparse
import csv
import json
from datetime import datetime,timedelta
from pathlib import Path
def timestamp(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
def calculate(rows,as_of,synthetic=False):
    events={}
    for row in rows:
        if (row['is_synthetic'].lower()=='true')!=synthetic:continue
        if timestamp(row['occurred_at'])>=as_of:continue
        if row['event_id'] in events and events[row['event_id']]!=row:raise ValueError('Conflicting duplicate event ID')
        events[row['event_id']]=row
    accepted={};ready={};withdrawn=set()
    for row in events.values():
        key=(row['expert_id'],row['artifact_id']);time=timestamp(row['occurred_at']);expert=row['expert_id']
        if row['event_type']=='expert_ready':ready[expert]=min(time,ready.get(expert,time))
        if row['event_type']=='acceptance_withdrawn':withdrawn.add(key)
        if row['event_type']=='artifact_accepted' and row['artifact_type']=='production':
            if not row['artifact_id']:raise ValueError('Acceptance requires artifact identity')
            accepted[key]=min(time,accepted.get(key,time))
    times={}
    for (expert,artifact),time in accepted.items():
        if (expert,artifact) not in withdrawn:times.setdefault(expert,[]).append(time)
    first={expert:min(values) for expert,values in times.items()}
    start=as_of-timedelta(days=28)
    retained=[expert for expert,values in times.items() if any(t<start for t in values) and any(start<=t<as_of for t in values)]
    mature_ready=[expert for expert,t in ready.items() if t+timedelta(days=30)<=as_of]
    activated=[expert for expert in mature_ready if expert in first and ready[expert]<=first[expert]<ready[expert]+timedelta(days=30)]
    mature_active=[expert for expert,t in first.items() if t+timedelta(days=60)<=as_of]
    repeat=[expert for expert in mature_active if any(first[expert]+timedelta(days=30)<=t<first[expert]+timedelta(days=60) for t in times[expert])]
    def rate(n,d):return {'numerator':n,'denominator':d,'rate':n/d if d else None}
    return {'mode':'synthetic illustration' if synthetic else 'supplied production events only',
      'as_of_utc':as_of.isoformat(),'retained_contributing_experts_28d':len(retained),
      'newly_activated_28d':sum(start<=t<as_of for t in first.values()),
      'activation_within_30d_of_ready':rate(len(activated),len(mature_ready)),
      'mature_cohort_repeat_days_30_to_60':rate(len(repeat),len(mature_active))}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('csv');parser.add_argument('--as-of',required=True);parser.add_argument('--synthetic',action='store_true');args=parser.parse_args()
    print(json.dumps(calculate(list(csv.DictReader(Path(args.csv).open())),timestamp(args.as_of),args.synthetic),indent=2))
