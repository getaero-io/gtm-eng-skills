"""Compile explicit CSV joins into one synthetic Engine input; no network."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))

def boolean(value):
    if value.lower() not in ('true', 'false'):
        raise ValueError(f'Expected explicit true/false, got {value!r}')
    return value.lower() == 'true'

def unique(data, field):
    result = {r[field]: r for r in data}
    if len(result) != len(data): raise ValueError(f'Duplicate {field}')
    return result

def compile_input(folder, expert_id, episode):
    experts=unique(rows(folder/'experts.csv'),'expertId')
    tasks=unique(rows(folder/'tasks.csv'),'taskId')
    assignments=unique(rows(folder/'assignments.csv'),'expertId')
    events=list(unique(rows(folder/'world_model_usage_data.csv'),'eventId').values())
    e=experts[expert_id].copy(); t=tasks[assignments[expert_id]['taskId']].copy()
    for field in ['identityReviewed','credentialReviewed','consent','conflictsCleared','agreementSigned','trainingComplete']: e[field]=boolean(e[field])
    e['availabilityHours']=float(e['availabilityHours'])
    t['assignmentApproved']=boolean(t['assignmentApproved'])
    t['hours']=float(t['hours']); t['revisions']=int(t['revisions']); t['qualityScore']=float(t['qualityScore']) if t['qualityScore'] else None
    usage=[]
    for event in events:
        if event['taskId']==t['taskId'] and event['worldId']==t['worldId']:
            event['acceptedUses']=int(event['acceptedUses']); event['abandonmentCount']=int(event['abandonmentCount']); usage.append(event)
    if not expert_id.startswith('syn-'): raise ValueError('Synthetic experts only')
    return dict(episodeId=episode,payload=dict(synthetic=True,expert=e,task=t,usage=usage))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--fixtures',type=Path,default=ROOT/'fixtures'); p.add_argument('--expert',required=True); p.add_argument('--episode',required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); result=compile_input(a.fixtures,a.expert,a.episode)
    a.out.write_text(json.dumps(result,indent=2)+'\n'); print(a.out)

if __name__=='__main__': main()
