"""Audit reviewed-evidence JSON before scoring. Offline; no profile/provider calls.

Exit 0: passed structural checks (warnings may remain); 1: data-quality failure;
2: malformed JSON or I/O. Reports are private and refuse overwrite. Freshness is
relative to as_of, not today; --max-age-days defaults to a configurable 180 days.
This is not an audit of the live DB or proof that provider claims are true.
"""
import argparse
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from evaluate import loads, write_reports
from score import score

ROOT=Path(__file__).resolve().parents[1]

def audit(data, max_age_days=180):
    if type(max_age_days) is not int or max_age_days < 0:
        raise ValueError('max_age_days must be a nonnegative integer')
    errors=[];warnings=[]; contacts={};urls={};history=set();receipts=set()
    def issue(dest,code,record=None):
        dest.append(dict(code=code,record_id=record))
    coverage=dict(unique_contacts=0,contacts_without_job_history=0,contacts_without_company=0,
                  contacts_without_title=0,paths=0,evidence_records=0)
    try:
        cutoff=date.fromisoformat(data['as_of'])
        paths=data['paths'];evidence=data['evidence']
        if not isinstance(paths,list) or not isinstance(evidence,list): raise ValueError('lists required')
        coverage.update(paths=len(paths),evidence_records=len(evidence))
        if not paths: issue(errors,'empty_candidate_set')
        for p in paths:
            for role in ('connector','target'):
                person=p[role];identifier=person['id']
                if not isinstance(identifier,str) or not identifier.strip(): raise ValueError('contact ID')
                raw=person['linkedin_url'];parsed=urlsplit(raw)
                if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
                    issue(errors,'invalid_profile_url',identifier)
                canonical=urlunsplit(('https',parsed.netloc.lower(),parsed.path.rstrip('/'),'',''))
                signature=(canonical,person['first_name'].strip().casefold(),person['last_name'].strip().casefold())
                if identifier in contacts and contacts[identifier]['identity']!=signature:
                    issue(errors,'contact_identity_conflict',identifier)
                if canonical in urls and urls[canonical]!=identifier:
                    issue(errors,'profile_identity_collision',identifier)
                urls[canonical]=identifier
                if identifier not in contacts: contacts[identifier]=dict(identity=signature,company=False,title=False)
                contacts[identifier]['company'] |= bool(person.get('current_company','').strip())
                contacts[identifier]['title'] |= bool(person.get('current_position','').strip())
                for employment in p.get(role+'_experiences',[]):
                    history.add(identifier)
                    if employment.get('end_date') and date.fromisoformat(employment['end_date'])>cutoff:
                        issue(errors,'future_employment_end',employment.get('id'))
                    if employment.get('is_current') and employment.get('end_date'):
                        issue(errors,'current_job_has_end_date',employment.get('id'))
        for e in evidence:
            age=(cutoff-date.fromisoformat(e['observed_at'])).days
            if age>max_age_days: issue(warnings,'stale_evidence',e['id'])
            key=(e['source'],e['kind'],tuple(sorted(e['subjects'])),e['observed_at'])
            if key in receipts: issue(warnings,'duplicate_source_receipt',e['id'])
            receipts.add(key)
        for identifier,person in contacts.items():
            if identifier not in history:
                coverage['contacts_without_job_history']+=1;issue(warnings,'missing_job_history',identifier)
            for field in ('company','title'):
                if not person[field]:
                    coverage['contacts_without_'+field]+=1;issue(warnings,'missing_'+field,identifier)
        coverage['unique_contacts']=len(contacts)
        try: score(data,ROOT/'vendor')
        except (ValueError,KeyError,TypeError,AttributeError): issue(errors,'scorer_evidence_validation_failed')
    except (ValueError,KeyError,TypeError,AttributeError): issue(errors,'malformed_evidence_contract')
    return dict(schema_version=1,status='fail' if errors else 'pass',errors=errors,warnings=warnings,
                coverage=coverage,max_age_days=max_age_days,
                interpretation='Structural checks only. Missing history is unknown, not a negative relationship. Full-profile source truth and live DB constraints require separate audit.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--max-age-days',type=int,default=180)
    a=p.parse_args()
    try:
        report=audit(loads(a.input.read_text()),a.max_age_days)
        write_reports([(a.output,json.dumps(report,indent=2)+'\n')])
    except (ValueError,OSError):
        print('Invalid input or unavailable output path; no existing report overwritten.');return 2
    print(f"{report['status']}: {len(report['errors'])} errors, {len(report['warnings'])} warnings")
    return 1 if report['errors'] else 0
if __name__=='__main__':raise SystemExit(main())
