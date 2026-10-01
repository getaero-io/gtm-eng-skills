"""Deterministic batch boundaries and ledger reconciliation for the graph runner's code nodes."""
import json, re, math

def parse(v, default=None):
    return json.loads(v) if isinstance(v,str) and v.strip() else (default if v in (None,'') else v)

def domain(v):
    value=str(v or '').lower().strip().removeprefix('www.')
    if not re.fullmatch(r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',value):
        raise ValueError('A real employer domain is required')
    return value

def profile(v):
    match=re.fullmatch(r'https?://([^/?#]+)(/[^?#]*)?(?:[?#].*)?',str(v or '').strip())
    if not match:raise ValueError('Person identity URL required')
    host=domain(match.group(1))
    return host+(match.group(2) or '').rstrip('/').lower()

def records(v, marker):
    v=parse(v,{})
    if isinstance(v,dict):
        if marker in v:return [v]
        return [r for child in v.values() if isinstance(child,(dict,list)) for r in records(child,marker)]
    if isinstance(v,list):return [r for child in v if isinstance(child,(dict,list)) for r in records(child,marker)]
    return []

def batch_entry(c):
    brief=parse(c.get_input('brief_json'),{})
    if not isinstance(brief,dict):raise ValueError('Brief must be a JSON object')
    allowed={'offer','icp','cta','greeting','signature','sender_name','comparison_mode','comparison_as_of','comparison_focus','comparison_page_path','settings_json'}
    if set(brief)-allowed:raise ValueError('Unknown brief fields; never supply credentials in a brief')
    for key in allowed:
        value=c.get_input(key)
        if value not in (None,''):
            if key in brief and brief[key]!=value:raise ValueError('Conflicting plain and advanced brief input: '+key)
            brief[key]=value
    if not brief.get('offer') or not brief.get('icp'):raise ValueError('Combined sourcing and copy requires actual offer and ICP at the beginning')
    if not brief.get('sender_name') and not brief.get('signature'):raise ValueError('Sender or signature required')
    limit=c.get_input('max_people')
    if limit is None or limit=='':limit=5
    if isinstance(limit,bool) or not isinstance(limit,(int,float)) or not math.isfinite(limit) or int(limit)!=limit or not 1<=limit<=100:
        raise ValueError('max_people must be an integer from 1 through 100')
    limit=int(limit)
    focus=str(c.get_input('audience_brief') or brief['icp']).strip()
    focus+='\nSource actual people at their current employer. Commercial offer: '+brief['offer']+'\nICP: '+brief['icp']
    settings=parse(c.get_input('radar_settings_json'),{})
    if not isinstance(settings,dict) or 'max_candidates' in settings:raise ValueError('Set candidate count using max_people, not radar settings')
    settings['max_candidates']=limit
    return {'brief_json':json.dumps(brief),'focus':focus,'settings_json':json.dumps(settings),'max_people':limit,
            'batch_id':str(c.get_input('batch_id') or ''),'memory_json':c.get_input('memory_json') or '',
            'feedback_json':c.get_input('feedback_json') or ''}

def search_plan(c):
    icp=parse(c.get_input('icp_json'));limit=icp['settings']['max_candidates']
    queries=[x.strip() for x in str(icp.get('search_queries','')).splitlines() if x.strip()]
    tasks=[{'shard_id':i//10+1,'limit':min(10,limit-i),'search_angle':queries[(i//10)%len(queries)] if queries else 'ICP-specific primary sources',
            'alternative_queries':queries,'instruction':'Start with the search angle, then use other ICP queries and source families if it is unproductive. The angle is not a restriction on the allowed employers. Cover the whole brief within this shard limit.'} for i in range(0,limit,10)]
    return {'search_tasks':tasks,'requested':limit}

def normalize(c):
    shards=records(c.get_input('discovery'),'candidates_json'); limit=int(c.get_input('max_people')); seen=set();orgs=set();out=[];rejected=[]
    for shard in shards:
        rows=parse(shard.get('candidates_json'),[])
        if not isinstance(rows,list):raise ValueError('Discovery must return an array')
        for row in rows[:10]:
            try:
                if row.get('entity_type')!='person':raise ValueError('People only')
                if not all(str(row.get(k) or '').strip() for k in ['name','first_name','company_name','role']):raise ValueError('Name, first name, company and actual role required')
                ident=profile(row.get('profile_url'));org=domain(row.get('domain'))
                if ident in seen:raise ValueError('Duplicate person')
                if org in orgs:raise ValueError('Employer already represented')
                if len(out)>=limit:raise ValueError('Batch cap reached')
                seen.add(ident);orgs.add(org)
                out.append({**row,'candidate_id':'person:'+ident,'domain':org})
            except (ValueError,TypeError,AttributeError) as e:rejected.append({'name':str(row.get('name','')) if isinstance(row,dict) else '', 'reason':str(e)})
    return {'candidates':out,'candidate_count':len(out),'rejected':rejected,'requested':limit,'discovery_notes':[s.get('discovery_notes','') for s in shards]}

def dispatch(c):
    ranked=parse(c.get_input('ranking_json'),[]); candidates=parse(c.get_input('candidates'),[])
    by_id={r['candidate_id']:r for r in candidates};brief=parse(c.get_input('brief_json'));batch=c.get_input('batch_id') or ''
    entries=[];held=[]
    for r in ranked:
        cid=r['candidate_id'];source=by_id.get(cid)
        if r.get('decision')!='QUALIFIED_FOR_REVIEW' or not source:
            held.append({'candidate_id':cid,'name':r.get('name'),'status':'QUALIFICATION_HELD','reasons':r.get('hold_reasons',[]) or ['Identity missing from discovery ledger'],'subject':'','body':''});continue
        if str(r.get('domain','')).lower()!=source['domain'] or r.get('identity_confirmed') is not True:
            held.append({'candidate_id':cid,'name':r.get('name'),'status':'IDENTITY_HELD','reasons':['Employer or identity changed during research'],'subject':'','body':''});continue
        lead={**source,'radar_score':r['score'],'priority_score':r['priority_score'],'identity_verified':True,'batch_id':batch,'radar_evidence':r.get('verified_evidence',[])}
        entries.append({'candidate_id':cid,'inputs':{'lead_json':json.dumps(lead),'brief_json':json.dumps(brief)}})
    # Missing model rows must have a terminal result too.
    known={r['candidate_id'] for r in ranked}
    held.extend({'candidate_id':r['candidate_id'],'name':r['name'],'status':'RESEARCH_REQUIRED','reasons':['No scored dossier returned'],'subject':'','body':''} for r in candidates if r['candidate_id'] not in known)
    return {'entries':entries,'dispatch_count':len(entries),'held':held,'memory_json':c.get_input('memory_json') or ''}

def child_entry(c):
    lead=parse(c.get_input('lead_json'),{});brief=parse(c.get_input('brief_json'),{})
    if not lead.get('candidate_id') or lead.get('identity_verified') is not True:raise ValueError('Verified Radar identity required')
    if not all(lead.get(k) for k in ['name','first_name','company_name','role']):raise ValueError('Complete person identity required')
    org=domain(lead.get('domain'));profile(lead.get('profile_url'))
    if not brief.get('offer') or not brief.get('icp'):raise ValueError('Offer and ICP required')
    values={**brief,'company_domain':org,'company_name':lead['company_name'],'recipient_name':lead['first_name'],
            'recipient_role':lead['role'],'source_record_id':lead['candidate_id'],'source_kind':'manual',
            'source_id':'alpha-campaign','batch_id':lead.get('batch_id',''),'full_name':lead['name'],
            'lead_json':json.dumps(lead),'candidate_id':lead['candidate_id'],
            'qualification_json':json.dumps({'person':lead['name'],'role':lead['role'],'company_domain':org,'profile_url':lead['profile_url'],'starting_url':lead.get('discovery_url',''),'starting_reason':lead.get('discovery_reason',''),'radar_evidence':lead.get('radar_evidence',[]),'rule':'Reopen sources to verify company use and current identity. Company configuration is not a personal accomplishment or proof of buying intent.'})}
    return values

def found_email(c):
    # Deepline findymail_find_from_name returns {contact:{email,domain,name}}; a failed call is {ok:false,error}.
    raw=parse(c.get_input('finder'),{});result=raw.get('contact') or {};email=str(result.get('email') or '').strip().lower()
    org=domain(c.get_input('company_domain'));ok=bool(raw.get('ok') is not False and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email))
    ok=ok and email.rsplit('@',1)[-1]==org
    return {'email':email if ok else '', 'found':ok,'finder_receipt':raw,
            'reason':'' if ok else 'No work address matching the verified employer was returned'}

def verified_email(c):
    # Deepline zerobounce_validate returns ZeroBounce's own fields; catch-all comes back as status=catch-all.
    r=parse(c.get_input('verification'),{});email=str(c.get_input('email') or '').lower()
    status=str(r.get('status') or '').lower();sub=str(r.get('sub_status') or '').lower()
    free=r.get('free_email')  # boolean or string depending on response
    accepted=r.get('ok') is not False and str(r.get('address') or '').lower()==email and status=='valid' and sub in ('','none') and free in (False,'false','False')
    raw=r
    return {'verified':accepted,'email':email,'verification_receipt':raw,'verification_status':status or 'unknown',
            'reason':'' if accepted else 'Email must match the request and be valid, non-catch-all, non-role and non-free'}

def email_hold(c):
    lead=parse(c.get_input('lead_json'));v=parse(c.get_input('email_state'),{})
    return {'candidate_id':lead['candidate_id'],'name':lead['name'],'company_name':lead['company_name'],
            'status':'EMAIL_HELD','email':'','subject':'','body':'','reason':v.get('reason','Email not verified'),
            'email_state':v,'radar_score':lead.get('radar_score')}

def finish_copy(c):
    lead=parse(c.get_input('lead_json'));copy=parse(c.get_input('copy'),{});v=parse(c.get_input('verification'),{})
    if v.get('verified') is not True:raise ValueError('Copy cannot be delivered without accepted verification')
    if copy.get('source_record_id') not in (None,'',lead['candidate_id']):raise ValueError('Copy identity mismatch')
    return {**copy,'status':copy.get('state') or 'COPY_REVIEW_REQUIRED','candidate_id':lead['candidate_id'],'name':lead['name'],'company_name':lead['company_name'],
            'email':v['email'],'email_verified':True,'email_verification':v,'radar_score':lead.get('radar_score'),
            'priority_score':lead.get('priority_score'),'batch_id':lead.get('batch_id',''),'sent':False}

def reconcile(c):
    expected=parse(c.get_input('dispatch'),{});raw=c.get_input('results');found=records(raw,'candidate_id');by_id={}
    for row in found:
        if 'status' in row:by_id.setdefault(row['candidate_id'],[]).append(row)
    out=list(expected.get('held',[]))
    for entry in expected.get('entries',[]):
        cid=entry['candidate_id'];matches=by_id.get(cid,[])
        if len(matches)!=1:out.append({'candidate_id':cid,'status':'PIPELINE_ERROR','reason':'Missing or ambiguous child result; inspect native run before retrying','subject':'','body':''})
        else:out.append(matches[0])
    # Never approve a draft whose verification/output identity is missing.
    for row in out:
        if row.get('status')=='DRAFT_READY_FOR_REVIEW' and (row.get('email_verified') is not True or not row.get('email') or not row.get('body')):
            row.update(status='PIPELINE_ERROR',subject='',body='',reason='Final evidence incomplete')
    counts={}
    for row in out:counts[row['status']]=counts.get(row['status'],0)+1
    return {'status':'BATCH_REVIEW_READY','people':out,'people_json':json.dumps(out),'terminal_count':len(out),'counts':counts,
            'ready_count':counts.get('DRAFT_READY_FOR_REVIEW',0),'memory_json':expected.get('memory_json',''),'sent':False}
