"""Convert successful native HTTP responses into evidence; never expose request headers."""
import json,time,re

def obj(value):return json.loads(value) if isinstance(value,str) else value

def response(value):
 data=obj(value)
 if not isinstance(data,dict) or data.get('success') is False:raise ValueError('Exa HTTP request did not succeed')
 # Native tool outputs wrap action data in result; HTTP metadata wrappers vary.
 data=obj(data.get('result',data))
 for _ in range(3):
  if not isinstance(data,dict):raise ValueError('Exa response was not an object')
  if any(data.get(k) for k in ['error','errors','tag']):raise ValueError('Exa returned an API error; inspect the native HTTP step')
  status=data.get('statusCode',data.get('status_code'))
  if status is not None and str(status)!='200':raise ValueError('Exa HTTP status was not 200')
  if isinstance(data.get('results'),list):return data
  key=next((k for k in ['body','data','response'] if k in data),None)
  if key is None:break
  data=obj(data[key])
 raise ValueError('Unrecognized Exa response shape; inspect the native HTTP result before mapping it')

def canonical(url):
 value=str(url)
 if not value.startswith('https://'):raise ValueError('Exa result must identify an HTTPS page')
 host,_,path=value[8:].partition('/')
 return host.lower().removeprefix('www.')+'/'+path.rstrip('/')

def receipt(raw,role,url,cutoff,observed):
 data=response(raw);rows=data['results']
 if len(rows)!=1:raise ValueError('Expected one Exa result for the one requested URL')
 row=rows[0]
 if not isinstance(row,dict) or canonical(row.get('url'))!=canonical(url):raise ValueError('Exa returned a different company or page')
 statuses=data.get('statuses')
 if not isinstance(statuses,list) or len(statuses)!=1 or statuses[0].get('status')!='success':raise ValueError('Exa did not confirm successful page retrieval')
 source=statuses[0].get('source')
 if role=='current' and source!='crawled':raise ValueError('Current Exa response was not confirmed freshly crawled')
 if role=='past' and source=='crawled':raise ValueError('Historical request unexpectedly returned a live crawl')
 text=row.get('text')
 if not isinstance(text,str) or len(text.strip())<30:raise ValueError('Exa has no substantive page text; title-only/missing history is not a change')
 plain=re.sub(r'\[([^]]*)\]\([^)]*\)',r'\1',text).strip(' .#\n\t').lower()
 if plain in ['permanent redirect','temporary redirect','redirect','redirecting','moved permanently']:raise ValueError('Exa returned a redirect placeholder, not page evidence')
 title=str(row.get('title') or '').strip()
 substantive=re.sub(r'\s+',' ',text).strip()
 if title:substantive=substantive.replace(title,'').strip(' #\n|—-')
 if len(substantive)<30:raise ValueError('Exa returned title-only text; no substantive observation')
 if not data.get('requestId'):raise ValueError('Missing Exa request receipt ID')
 # publishedDate is deliberately not used as a capture timestamp.
 result={'id':'exa-'+role+'-'+str(data['requestId']),'provider':'exa_snapshot' if role=='past' else 'source_capture',
         'role':role,'url':row['url'],'text':text[:30000],'title':str(row.get('title') or ''),
         'observed_at':observed,'captured_at':None,'provider_request_id':data['requestId'],
         'provenance':'Exa /contents response via Deepline generic_http_request using the user-supplied EXA_API_KEY',
         'response_source':source,'text_truncated':len(text)>30000}
 if role=='past':result['requested_as_of']=cutoff
 return result

def handler(context):
 c=obj(context.get_input('contract_json'));url=context.get_input('request_url');cutoff=context.get_input('requested_as_of')
 observed=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 receipts=[];unavailable=[]
 for role in ['past','current']:
  try:receipts.append(receipt(context.get_input(role+'_response'),role,url,cutoff,observed))
  except (ValueError,TypeError,KeyError) as error:
   if c['comparison']['mode']=='before_after':raise
   unavailable.append(role+': '+str(error))
 c['comparison']['unavailable_observations']=unavailable
 # Auto permits independently verified dated-event research; it never invents the missing side.
 return {'contract_json':json.dumps(c),'evidence_json':json.dumps(receipts),
         'retrieval_state':'EXA_PAIR_RETRIEVED' if len(receipts)==2 else 'EXA_PARTIAL_OR_UNAVAILABLE','request_ids':[r['provider_request_id'] for r in receipts]}
