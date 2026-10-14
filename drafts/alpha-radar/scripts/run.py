"""Run Alpha Radar locally through the Deepline CLI; carry review memory from the prior local run record."""
import argparse, json, sys, time
sys.dont_write_bytecode=True
from pathlib import Path
from graph_runner import execute, save

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--state',type=Path,required=True,help='Private run-history folder OUTSIDE the skill package')
    p.add_argument('--brief',help='New audience and objective. Omit only to repeat the preceding brief.')
    p.add_argument('--settings',type=Path,help='Optional JSON settings file outside the package')
    p.add_argument('--like',action='append',default=[],help='Candidate ID or exact name explicitly approved by the human')
    p.add_argument('--dislike',action='append',default=[],help='Candidate ID or exact name explicitly rejected by the human')
    p.add_argument('--start',action='store_true',help='Run the paid Deepline calls; omission previews')
    p.add_argument('--status',action='store_true',help='Print the last run record without starting anything')
    args=p.parse_args()
    package=Path(__file__).resolve().parents[1]
    if args.state.resolve().is_relative_to(package): raise ValueError('Keep run history outside the portable package')
    index=args.state/'state.json'
    state=json.loads(index.read_text()) if index.exists() else {}
    prior=json.loads(Path(state['last_run']).read_text()) if state.get('last_run') else None
    if args.status:
        if prior is None: raise ValueError('No run has started')
        print(json.dumps(prior,indent=2));return
    if prior and 'finished_at' not in prior:
        raise ValueError('The previous run record is unfinished. Inspect it before starting another.')
    trigger=(prior or {}).get('outputs',{}).get('trigger',{})
    old_focus=trigger.get('focus')
    focus=args.brief or old_focus
    if not focus: raise ValueError('Supply an audience and objective with --brief')
    previous_settings=trigger.get('settings_json')
    settings=json.loads(args.settings.read_text()) if args.settings else json.loads(previous_settings or '{}')
    # The score node holds the updated memory for the next run.
    memory=json.loads(((prior or {}).get('outputs',{}).get('score') or {}).get('memory_json') or '{}')
    same_brief=' '.join(focus.lower().split())==' '.join((old_focus or '').lower().split())
    same_settings=settings==json.loads(previous_settings or '{}')
    if not same_brief or not same_settings: memory={}
    feedback=[];used=set()
    for rating,labels in [(1,args.like),(0,args.dislike)]:
        for label in labels:
            candidates=[cid for cid,row in memory.get('seen',{}).items() if cid==label or row.get('name','').lower()==label.lower()]
            if len(candidates)!=1: raise ValueError('Review must identify exactly one candidate from the same ICP memory: '+label)
            cid=candidates[0]
            if cid in used: raise ValueError('Conflicting or duplicate review for '+label)
            used.add(cid)
            feedback.append({'candidate_id':cid,'rating':rating,'feedback_id':state['last_run_id']+':'+cid+':'+str(rating)})
    payload={'focus':focus,'memory_json':json.dumps(memory) if memory else '', 'feedback_json':json.dumps(feedback),'settings_json':json.dumps(settings)}
    print(json.dumps({'focus':focus,'settings':settings,'remembered_candidates':len(memory.get('seen',{})),'human_reviews_to_apply':len(feedback),'starts_run':args.start},indent=2))
    if not args.start:return
    graph=json.loads((package/'references/blueprint.json').read_text())
    run_id=time.strftime('%Y%m%dT%H%M%S')
    record=args.state/'runs'/(run_id+'.json')
    state.update(last_run=str(record),last_run_id=run_id);save(index,state)
    outputs,rec=execute(graph,payload,record)
    final={k:outputs[k] for k in ('score','brief','hold','empty') if k in outputs}
    print(json.dumps({'run_id':run_id,'record':str(record),'agent_cost_usd':round(rec['cost_usd'],4),**final},indent=2,default=str))

if __name__=='__main__':main()
