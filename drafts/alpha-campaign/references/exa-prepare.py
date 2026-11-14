"""Prepare two fixed-endpoint requests. The Exa key is supplied by the runner from EXA_API_KEY at call time, never here."""
import json,re,time

def handler(context):
 raw=context.get_input('contract_json');c=json.loads(raw) if isinstance(raw,str) else raw
 raw=context.get_input('evidence_json');existing=json.loads(raw) if isinstance(raw,str) else (raw or [])
 if existing:raise ValueError('Automatic Exa mode retrieves its own evidence; clear imported evidence columns')
 date=c.get('comparison',{}).get('as_of')
 if not date:raise ValueError('Choose comparison_as_of YYYY-MM-DD before automatic Exa retrieval')
 # The upstream contract already validated the calendar date. Recheck the URL boundary.
 domain=c['company_domain']
 if not re.fullmatch(r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',domain):raise ValueError('Use a public company DNS domain')
 page=str(context.get_input('comparison_page_path') or '/').strip()
 if not page.startswith('/') or page.startswith('//') or any(v in page for v in ['?','#','@','\\']) or any(ord(v)<33 for v in page):
  raise ValueError('Comparison page path must be a same-company path such as / or /pricing; no query or credentials')
 url='https://'+domain+page
 # Preserve auto mode: missing history may fall back to a verified dated event.
 c['comparison']['retrieval']='exa_http_byo_key'
 c['comparison']['page_url']=url
 past={'urls':[url],'text':True,'snapshotAsOf':date+'T00:00:00Z'}
 now={'urls':[url],'text':True,'maxAgeHours':0}
 return {'contract_json':json.dumps(c),'past_body':json.dumps(past),'current_body':json.dumps(now),
         'request_url':url,'requested_as_of':past['snapshotAsOf'],
         'requested_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
