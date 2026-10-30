"""Case ownership, actions and append-only application events."""
import copy, datetime, uuid
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def record(case,kind,details,actor='System',occurred_at=None,source='system'):
 if len(case.workflow['events'])>=1000:raise HTTPException(409,'Case timeline is full. Contact the owner before making more changes.')
 case.workflow['events'].append(dict(id=uuid.uuid4().hex,kind=kind,details=details,actor=actor,source=source,recorded_at=now(),occurred_at=occurred_at or now()))
class Change(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 expected_revision:int=Field(ge=0)
 actor:str=Field(min_length=1,max_length=100)
class Ownership(Change):
 owner:str=Field(min_length=1,max_length=100)
class ActionCreate(Change):
 description:str=Field(min_length=1,max_length=600)
 responsible:str=Field(min_length=1,max_length=100)
 waiting_on:str=Field(default='',max_length=100)
 due_at:datetime.datetime
 @field_validator('due_at')
 @classmethod
 def aware(cls,value):
  if value.tzinfo is None:raise ValueError('Include a timezone')
  return value.astimezone(datetime.timezone.utc)
class ActionFinish(Change):
 outcome:str=Field(min_length=1,max_length=1000)
class Activity(Change):
 kind:str=Field(pattern=r'^(initial_response|information_requested|follow_up|information_received|client_updated|resolution_note|note)$')
 details:str=Field(min_length=1,max_length=2000)
 occurred_at:datetime.datetime|None=None
 @field_validator('occurred_at')
 @classmethod
 def occurred(cls,value):
  if value is not None and (value.tzinfo is None or value>datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=5)):raise ValueError('Use a timezone and a time no later than now')
  return value.astimezone(datetime.timezone.utc) if value else value

def install(app,m):
 def change(case_id,data,work,allow_resolved=False):
  with m.case_lock:
   for index,c in enumerate(m.cases):
    if c.unique_id!=case_id:continue
    m.check_revision(c,data.expected_revision)
    if c.deleted_at:raise HTTPException(409,'Restore this case first.')
    if not allow_resolved:m.ensure_editable(c)
    updated=m.Case(**m.case_to_dict(c));work(updated);updated.revision+=1
    return m.persist_case_change(index,updated)
   raise HTTPException(404,'Case not found')
 @app.patch('/cases/{case_id}/owner')
 def owner(case_id:str,data:Ownership):
  def work(c):
   old=c.workflow['owner'];c.workflow['owner']=data.owner
   record(c,'owner_assigned',{'previous':old,'owner':data.owner},data.actor,source='manual')
  return change(case_id,data,work)
 @app.post('/cases/{case_id}/actions')
 def action(case_id:str,data:ActionCreate):
  def work(c):
   if len(c.workflow['actions'])>=100:raise HTTPException(409,'Case action limit reached.')
   item=dict(id=uuid.uuid4().hex,description=data.description,responsible=data.responsible,waiting_on=data.waiting_on,due_at=data.due_at.isoformat(),created_at=now(),completed_at=None,outcome=None)
   c.workflow['actions'].append(item);record(c,'action_assigned',copy.deepcopy(item),data.actor,source='manual')
  return change(case_id,data,work)
 @app.post('/cases/{case_id}/actions/{action_id}/complete')
 def complete(case_id:str,action_id:str,data:ActionFinish):
  def work(c):
   item=next((a for a in c.workflow['actions'] if a['id']==action_id),None)
   if not item:raise HTTPException(404,'Action not found')
   if item['completed_at']:raise HTTPException(409,'Action already completed.')
   item['completed_at']=now();item['outcome']=data.outcome
   record(c,'action_completed',copy.deepcopy(item),data.actor,source='manual')
  return change(case_id,data,work)
 @app.post('/cases/{case_id}/activities')
 def activity(case_id:str,data:Activity):
  return change(case_id,data,lambda c:record(c,data.kind,data.details,data.actor,data.occurred_at.isoformat() if data.occurred_at else None,'manual'),allow_resolved=True)
