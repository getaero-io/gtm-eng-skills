"""Score reviewed evidence with the existing office-hours scorer; no network calls."""
import argparse
import csv
import importlib
import json
import os
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

FIELDS = 'model_version baseline_segment target_relationship_confidence connector_willingness review_status campaign_id owner_id connector_id target_id path_id connector_name connector_linkedin connector_company target_name target_title target_company shared_signal shared_detail relationship_confidence direct_intro_score work_overlap_score relationship_score school_city_community_score role_industry_score investor_score total_score segment reviewed_override evidence_ids'.split()
SIGNALS = {'school':'shared_schools','city':'shared_cities','community':'shared_communities','appearance':'shared_appearances','role_industry':'role_industry_matches','investor':'investor_overlaps'}


def score(data, repo):
    sys.path.insert(0, str(Path(repo).resolve()))
    mod = importlib.import_module('examples.office-hours.warm-intro-scoring.scorer')
    models = importlib.import_module('examples.office-hours.warm-intro-scoring.models')
    as_of = date.fromisoformat(data['as_of'])
    if as_of > date.today():
        raise ValueError('as_of must not be in the future')
    registry = {}
    for e in data['evidence']:
        if not e.get('id') or e['id'] in registry or not e.get('detail') or not e.get('source'):
            raise ValueError('Evidence requires unique ID, detail and source locator')
        if date.fromisoformat(e['observed_at']) > as_of:
            raise ValueError('Evidence observed after as_of leaks future information')
        registry[e['id']] = e

    def cited(ids, subjects, kind):
        if not ids:
            raise ValueError('Scored facts require evidence IDs')
        for eid in ids:
            e = registry.get(eid)
            if not e or e.get('kind') != kind or not set(subjects) <= set(e.get('subjects', [])):
                raise ValueError('Evidence must support this kind and these exact subjects')

    def person(raw):
        for key in ('id','first_name','last_name','linkedin_url'):
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise ValueError('Stable contact IDs, names and profile URLs are required')
        return models.Contact(**raw)

    def history(items, contact):
        out = []
        for raw in items:
            r = dict(raw)
            cited([r['id']], [contact.id], 'employment')
            if r.get('contact_id') != contact.id:
                raise ValueError('Employment belongs to a different contact')
            for key in ('start_date','end_date'):
                r[key] = date.fromisoformat(r[key]) if r.get(key) else None
            if r['start_date'] and (r['start_date'] > as_of or (r['end_date'] and r['end_date'] < r['start_date'])):
                raise ValueError('Invalid employment interval')
            if type(r.get('is_current',False)) is not bool:
                raise ValueError('is_current must be boolean')
            out.append(models.Experience(**r))
        return out

    rows, seen = [], set()
    for p in data['paths']:
        connector, target = person(p['connector']), person(p['target'])
        owner = data['owner_id']
        if len({owner,connector.id,target.id}) != 3:
            raise ValueError('Owner, connector and target must be distinct identities')
        confidence = p.get('relationship_confidence','unknown')
        if confidence not in ('unknown','low','medium','high','confirmed'):
            raise ValueError('Unknown relationship confidence label')
        rel = p.get('relationship_evidence_ids',[])
        if confidence != 'unknown' or rel:
            cited(rel, [owner,connector.id], 'relationship')
            if confidence != 'unknown' and any(registry[eid].get('confidence') != confidence for eid in rel):
                raise ValueError('Owner confidence must match cited reviewed relationship')
        target_confidence = p.get('target_relationship_confidence','unknown')
        if target_confidence not in ('unknown','low','medium','high','confirmed'):
            raise ValueError('Unknown target relationship confidence label')
        target_rel = p.get('target_relationship_evidence_ids',[])
        if target_confidence != 'unknown' or target_rel:
            cited(target_rel,[connector.id,target.id],'relationship')
            if target_confidence != 'unknown' and any(registry[eid].get('confidence') != target_confidence for eid in target_rel):
                raise ValueError('Target confidence must match cited reviewed relationship')
        willingness = p.get('connector_willingness','unknown')
        if willingness not in ('unknown','yes','no'):
            raise ValueError('Unknown willingness label')
        willingness_ids = p.get('willingness_evidence_ids',[])
        if willingness != 'unknown' or willingness_ids:
            cited(willingness_ids,[owner,connector.id,target.id],'willingness')
        relevant_willingness = [e for e in registry.values() if e.get('kind') == 'willingness'
                               and {owner,connector.id,target.id} <= set(e.get('subjects',[]))]
        if any(e.get('value') not in ('yes','no') for e in relevant_willingness):
            raise ValueError('Willingness evidence needs explicit yes/no value')
        if any(registry[eid]['value'] != willingness for eid in willingness_ids):
            raise ValueError('Willingness flag contradicts cited evidence')
        if relevant_willingness:
            latest = max(e['observed_at'] for e in relevant_willingness)
            current = [e for e in relevant_willingness if e['observed_at'] == latest]
            # Date-only conflicts fail closed; do not assume an order within one day.
            if any(e['value'] == 'no' for e in current):
                willingness = 'no'
                willingness_ids = sorted(set(willingness_ids) | {e['id'] for e in current if e['value']=='no'})
        direct = p.get('direct_intro_evidence_ids',[])
        if direct:
            cited(direct,[connector.id,target.id],'direct_intro')
        kwargs = {name:[] for name in SIGNALS.values()}
        all_ids = [*target_rel,*willingness_ids]
        for fact in p.get('signals',[]):
            kind = fact['kind']
            if kind not in SIGNALS or not isinstance(fact.get('value'),str) or not fact['value'].strip():
                raise ValueError('Unsupported or empty shared signal')
            cited(fact['evidence_ids'],[connector.id,target.id],kind)
            kwargs[SIGNALS[kind]].append(fact['value'])
            all_ids.extend(fact['evidence_ids'])
        match = mod.WarmIntroScorer().score_target_connector(
            connector,history(p.get('connector_experiences',[]),connector),
            target,history(p.get('target_experiences',[]),target),
            relationship_confidence=confidence,relationship_evidence_ids=tuple(rel),
            direct_intro_evidence_ids=tuple(direct), evidence_ids=tuple(all_ids),
            as_of=as_of,campaign_id=data['campaign_id'],owner_id=owner,**kwargs)
        if match.path_id in seen:
            raise ValueError('Duplicate owner/connector/target path')
        seen.add(match.path_id)
        row = asdict(match)
        if direct:
            row['shared_detail']='Recorded introduction between connector and target; inspect the cited record before a new ask.'
        row.update(model_version='office-hours-160-80-v1+two-edge-review-v1',
                   baseline_segment=match.segment,target_relationship_confidence=target_confidence,
                   connector_willingness=willingness,review_status='needs_confirmation')
        if willingness == 'no':
            row.update(segment='no_strong_path',review_status='blocked_declined')
        elif match.segment == 'strong_warm_intro':
            if target_confidence in ('medium','high','confirmed') and confidence in ('medium','high','confirmed') and willingness == 'yes':
                row['review_status']='ready_for_human_review'
            else:
                row['segment']='review_warm_intro'
        # A factual score is retained even when permission/relationship gates hold the ask.
        row.update(connector_name=connector.full_name,connector_linkedin=connector.linkedin_url,
                   connector_company=connector.current_company or '',total_score=match.total_score,
                   reviewed_override='false',evidence_ids=';'.join(match.evidence_ids))
        rows.append({k:row.get(k,'') for k in FIELDS})
    return sorted(rows,key=lambda r:(-r['total_score'],r['connector_name'].casefold(),r['path_id']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--repo',type=Path,required=True,help='GTM Eng Skills checkout containing examples/')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    rows=score(json.loads(args.input.read_text()),args.repo)
    # Exclusive creation prevents accidentally overwriting a reviewed/private export.
    with os.fdopen(os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    print(f'{len(rows)} paths written; no asks sent or approved.')

if __name__=='__main__':
    main()
