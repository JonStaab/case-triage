import importlib,json,os,tempfile,unittest,itertools
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

class WorkbenchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.env=patch.dict(os.environ,{'DEMO_MODE':'false','OPENAI_API_KEY':'test'});self.env.start();self.addCleanup(self.env.stop)
  self.m=importlib.import_module('Case_Management');self.m.CASES_FILE=Path(self.tmp.name)/'cases.json';self.m.cases.clear();self.client=TestClient(self.m.app)
  self.payload=dict(customer_name='Demo',issue_description='Operations stopped. Restore today.',customer_tier='Low',business_impact='Critical',time_sensitivity='Urgent')
 def create(self):
  r=self.client.post('/cases',json=self.payload);self.assertEqual(r.status_code,200);return r.json()
 def status(self,c,status):return self.client.patch('/cases/'+c['unique_id']+'/status',json=dict(status=status,expected_revision=c['revision']))
 def test_lifecycle_filter_and_reload(self):
  c=self.create();c=self.status(c,'In progress').json();self.assertEqual(c['status'],'In progress')
  c=self.status(c,'Resolved').json();self.assertEqual(self.client.get('/cases?view=active').json(),[])
  self.assertEqual(len(self.client.get('/cases?view=resolved').json()),1)
  self.assertEqual(self.m.load_cases()[0].status,'Resolved')
  c=self.status(c,'Open').json();self.assertEqual(c['status'],'Open')
 def test_trash_confirmation_restore(self):
  c=self.create();url='/cases/'+c['unique_id'];data=dict(expected_revision=0,confirmation='wrong')
  self.assertEqual(self.client.request('DELETE',url,json=data).status_code,422)
  data['confirmation']=c['unique_id'];r=self.client.request('DELETE',url,json=data);self.assertEqual(r.status_code,200)
  self.assertEqual(self.client.get('/cases').json(),[]);self.assertEqual(len(self.client.get('/cases?view=deleted').json()),1)
  r=self.client.post(url+'/restore',json={'expected_revision':1});self.assertEqual(r.json()['status'],'Resolved')
  self.assertEqual(r.json()['issue_description'],c['issue_description'])
 def test_stale_status_and_failed_write(self):
  c=self.create();self.status(c,'In progress');self.assertEqual(self.status(c,'Resolved').status_code,409)
  fresh=self.client.get('/cases/'+c['unique_id']).json()
  with patch.object(self.m,'save_cases',side_effect=OSError('private')):self.assertEqual(self.status(fresh,'Resolved').status_code,503)
  self.assertEqual(self.client.get('/cases/'+c['unique_id']).json(),fresh)
 def test_legacy_json_preserved(self):
  old={k:v for k,v in self.create().items() if k not in ('status','revision','created_at','deleted_at','priority_explanation')};old['priority']='P2'
  self.m.CASES_FILE.write_text(json.dumps([old]));c=self.m.load_cases()[0]
  self.assertEqual(c.status,'Open');self.assertEqual(c.priority,'P2');self.assertIn('earlier policy',self.m.priority_explanation(c))
 def test_priority_matrix(self):
  for tier,impact,urgency in itertools.product(['Low','Medium','High'],['Low','Medium','High','Critical'],['Low','Medium','High','Urgent','Critical']):
   total=['Low','Medium','High'].index(tier)+1+['Low','Medium','High','Critical'].index(impact)+1+['Low','Medium','High','Urgent','Critical'].index(urgency)+1
   expected='P1' if impact=='Critical' or total>=11 else 'P2' if total>=8 else 'P3' if total>=5 else 'P4'
   self.assertEqual(self.m.calculate_priority(urgency,impact,tier),expected)
 def test_ready_stops_required_questions(self):
  s=self.m.TriageSuggestion(business_impact='Critical',impact_reason='Stopped',impact_evidence=['Operations stopped.'],time_sensitivity='Urgent',urgency_reason='Today',urgency_evidence=['Restore today.'],missing_information=['Which serial number?'],next_action='Escalate')
  with patch.object(self.m,'suggest_triage',return_value=s):r=self.client.post('/triage',json={'issue_description':self.payload['issue_description'],'customer_tier':'Low'})
  self.assertEqual(r.json()['assessment_state'],'ready_for_review');self.assertEqual(r.json()['missing_information'],[]);self.assertEqual(len(r.json()['investigation_questions']),1)
 def test_demo_daily_limit_persists(self):
  import demo_controls as d
  with patch.dict(os.environ,{'DEMO_MODE':'true','DEMO_CREATE_DAILY_LIMIT':'1'}):
   d._recent['create'].clear();self.create();d._recent['create'].clear();self.assertEqual(self.client.post('/cases',json=self.payload).status_code,429)
 def test_demo_corrupt_budget_fails_closed(self):
  import demo_controls as d
  with patch.dict(os.environ,{'DEMO_MODE':'true'}):
   d._recent['create'].clear();Path(str(self.m.CASES_FILE)+'.demo-usage.json').write_text('[]')
   self.assertEqual(self.client.post('/cases',json=self.payload).status_code,503);self.assertEqual(self.m.cases,[])
 def test_demo_ai_limit_before_provider(self):
  import demo_controls as d
  with patch.dict(os.environ,{'DEMO_MODE':'true','DEMO_AI_DAILY_LIMIT':'1'}):
   d._recent['ai'].clear();d.consume('ai',self.m.CASES_FILE)
   with patch.object(self.m,'suggest_triage') as mock:
    self.assertEqual(self.client.post('/triage',json={'issue_description':'test','customer_tier':'Low'}).status_code,429);mock.assert_not_called()
 def test_resolved_assessment_requires_reopen(self):
  c=self.status(self.create(),'Resolved').json()
  r=self.client.patch('/cases/'+c['unique_id']+'/clarifications',json={'clarifications':[],'expected_issue_description':c['issue_description'],'expected_revision':1})
  self.assertEqual(r.status_code,409)
if __name__=='__main__':unittest.main()
