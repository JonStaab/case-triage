"""Private, opt-in Gmail intake. No Google credentials are stored by this app."""
import base64, binascii, datetime, email, json, os, secrets, tempfile
from email import policy
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
from threading import RLock
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

lock = RLock()
def enabled(): return os.getenv('EMAIL_INTAKE_ENABLED','false').lower() == 'true'
def store_path(): return Path(os.environ['EMAIL_DRAFTS_FILE']) if os.getenv('EMAIL_DRAFTS_FILE') else Path(os.getenv('CASES_FILE',str(Path(__file__).parent/'cases.json'))).with_name('email-drafts.json')
def configured():
 return (os.getenv('DEMO_MODE','true').lower() in ('false','0','no') and len(os.getenv('EMAIL_WEBHOOK_SECRET',''))>=32 and len(os.getenv('PRIVATE_PASSWORD',''))>=16 and bool(os.getenv('PRIVATE_USERNAME')) and bool(os.getenv('GMAIL_INTAKE_MAILBOX')))
def load():
 try:
  data=json.loads(store_path().read_text(encoding='utf-8'))
  if not isinstance(data,list) or any(not isinstance(d,dict) or not isinstance(d.get('messages'),list) or not d['messages'] or not isinstance(d.get('revision'),int) or not isinstance(d.get('id'),str) or any(not isinstance(m,dict) or not all(isinstance(m.get(k),str) for k in ('message_id','subject','sender','body','date')) for m in d['messages']) for d in data):raise ValueError()
  return data
 except FileNotFoundError:return []
 except (ValueError,OSError):raise HTTPException(503,'Email drafts could not be read. Contact the owner.')
def save(data):
 path=store_path();path.parent.mkdir(parents=True,exist_ok=True);tmp=None
 try:
  with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
   tmp=f.name;json.dump(data,f);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 except OSError:raise HTTPException(503,'Email draft could not be saved. Connector may retry.')
 finally:
  if tmp and os.path.exists(tmp):os.unlink(tmp)
class TextHTML(HTMLParser):
 def __init__(self):super().__init__();self.out=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.skip+=1
  elif tag in ('p','br','div','li'):self.out.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style') and self.skip:self.skip-=1
 def handle_data(self,text):
  if not self.skip:self.out.append(text)
def parse_message(raw):
 try:
  decoded=base64.urlsafe_b64decode(raw+'='*((-len(raw))%4))
  if len(decoded)>250000:raise ValueError()
  message=email.message_from_bytes(decoded,policy=policy.default)
  if message.is_attachment():raise ValueError()
  part=message.get_body(preferencelist=('plain','html')) if message.is_multipart() else message
  if not part or part.get_content_type() not in ('text/plain','text/html') or part.is_attachment():raise ValueError()
  text=part.get_content()
  if part.get_content_type()=='text/html':
   parser=TextHTML();parser.feed(text);text=''.join(parser.out)
  text=text.strip();subject=str(message.get('Subject','(no subject)'))[:300]
  sender=parseaddr(str(message.get('From','')))[1]
  if not sender or not text or len(text)>8000:raise ValueError()
  return {'subject':subject,'sender':sender,'body':text,'date':str(message.get('Date',''))[:100]}
 except (ValueError,TypeError,LookupError,binascii.Error):raise HTTPException(422,'Unsupported, empty or oversized email. Plain text/HTML up to 8000 characters is supported; attachments are not imported.')
class Delivery(BaseModel):
 model_config=ConfigDict(extra='forbid')
 mailbox:str=Field(min_length=3,max_length=254)
 message_id:str=Field(pattern=r'^[a-fA-F0-9]{1,64}$')
 thread_id:str=Field(pattern=r'^[a-fA-F0-9]{1,64}$')
 raw:str=Field(min_length=1,max_length=340000)
def draft_for_review(identifier,revision):
 if not enabled() or not configured():raise HTTPException(404,'Email intake is disabled.')
 with lock:
  draft=next((d for d in load() if d['id']==identifier),None)
  if not draft:raise HTTPException(404,'Email draft not found.')
  if draft['revision']!=revision:raise HTTPException(409,'New email arrived. Reload the draft before reviewing.')
  description='\n\n'.join('Subject: '+m['subject']+'\nFrom: '+m['sender']+'\n'+m['body'] for m in draft['messages'])
  if len(description)>10000:raise HTTPException(422,'Thread is too long for one case. Review and summarize it manually.')
  return draft,description

def install(app,get_cases):
 @app.middleware('http')
 async def private_access(request:Request,call_next):
  if not (enabled() or os.getenv('PRIVATE_MODE','false').lower()=='true' or store_path().exists()):return await call_next(request)
  if request.url.path=='/health':return await call_next(request)
  if not configured():return JSONResponse({'detail':'Private email pilot is not configured.'},status_code=503)
  if enabled() and request.url.path=='/integrations/gmail' and request.method=='POST':
   supplied=request.headers.get('authorization','')
   if not secrets.compare_digest(supplied.encode(),('Bearer '+os.environ['EMAIL_WEBHOOK_SECRET']).encode()):return JSONResponse({'detail':'Unauthorized'},status_code=401)
   size=request.headers.get('content-length','0')
   if not size.isdigit() or int(size)>350000:return JSONResponse({'detail':'Message too large'},status_code=413)
   chunks=[];total=0
   async for chunk in request.stream():
    total+=len(chunk)
    if total>350000:return JSONResponse({'detail':'Message too large'},status_code=413)
    chunks.append(chunk)
   request._body=b''.join(chunks)
  else:
   try:
    auth=request.headers.get('authorization','');scheme,encoded=auth.split(' ',1)
    if scheme.lower()!='basic':raise ValueError()
    name,password=base64.b64decode(encoded,validate=True).decode().split(':',1)
    valid=secrets.compare_digest(name.encode(),os.environ['PRIVATE_USERNAME'].encode()) & secrets.compare_digest(password.encode(),os.environ['PRIVATE_PASSWORD'].encode())
   except (ValueError,UnicodeError,binascii.Error):valid=False
   if not valid:return JSONResponse({'detail':'Manager sign-in required'},status_code=401,headers={'WWW-Authenticate':'Basic realm="Case Triage private pilot", charset="UTF-8"','Cache-Control':'no-store'})
  response=await call_next(request);response.headers['Cache-Control']='no-store';return response
 @app.post('/integrations/gmail')
 def deliver(data:Delivery):
  if not enabled():raise HTTPException(404,'Email intake is disabled.')
  if data.mailbox.casefold()!=os.environ['GMAIL_INTAKE_MAILBOX'].casefold():raise HTTPException(403,'Mailbox does not match configured intake.')
  with lock:
   drafts=load()
   if any(data.message_id==m['message_id'] for d in drafts for m in d['messages']):return {'status':'duplicate'}
   parsed=parse_message(data.raw)
   identifier=data.thread_id.lower();draft=next((d for d in drafts if d['id']==identifier),None)
   if draft is None:
    if len(drafts)>=200:raise HTTPException(429,'Pilot draft storage is full. Contact the owner.')
    draft={'id':identifier,'revision':0,'messages':[]};drafts.append(draft)
   if len(draft['messages'])>=20:raise HTTPException(429,'Thread message limit reached. Review manually.')
   draft['messages'].append({**parsed,'message_id':data.message_id})
   draft['revision']+=1;draft['received_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
   save(drafts)
   return {'status':'draft_saved','draft_id':identifier}
 @app.get('/email-drafts')
 def list_drafts():
  if not enabled():raise HTTPException(404,'Email intake is disabled.')
  with lock:
   result=[]
   for d in reversed(load()):
    case=next((c for c in get_cases() if getattr(c,'source_email_draft_id',None)==d['id']),None)
    result.append({**d,'linked_case_id':case.unique_id if case else None,'has_new_messages':bool(case and getattr(case,'source_email_revision',0)<d['revision'])})
   return result
