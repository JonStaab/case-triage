import importlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.env=patch.dict(os.environ,{'DEMO_MODE':'false','EMAIL_INTAKE_ENABLED':'false','PRIVATE_MODE':'false','EMAIL_DRAFTS_FILE':str(Path(self.tmp.name)/'drafts.json')});self.env.start();self.addCleanup(self.env.stop)
  self.m=importlib.import_module('Case_Management');self.m.CASES_FILE=Path(self.tmp.name)/'cases.json';self.m.cases.clear();self.client=TestClient(self.m.app)
  self.case=self.client.post('/cases',json=dict(customer_name='Demo',issue_description='Shipment delayed',customer_tier='Low',business_impact='High',time_sensitivity='Urgent')).json();self.url='/cases/'+self.case['unique_id']
 def post(self,path,data):return self.client.post(self.url+path,json={'actor':'Demo PM','expected_revision':0,**data})
 def test_creation_and_legacy_history(self):
  self.assertEqual(self.case['workflow']['events'][0]['kind'],'case_created')
  legacy=self.m.Case('old','Demo','Issue','Low','Low','Low','P4');self.assertEqual(legacy.workflow['events'],[])
 def test_owner_persistence_stale_conflict(self):
  data={'actor':'PM','owner':'Sarah','expected_revision':0};r=self.client.patch(self.url+'/owner',json=data);self.assertEqual(r.status_code,200);self.assertEqual(self.m.load_cases()[0].workflow['owner'],'Sarah');self.assertEqual(self.client.patch(self.url+'/owner',json=data).status_code,409)
 def test_action_and_completion(self):
  r=self.post('/actions',dict(description='Request vendor recovery plan',responsible='Sarah',waiting_on='Vendor',due_at='2026-11-01T12:00:00-05:00'));self.assertEqual(r.status_code,200);a=r.json()['workflow']['actions'][0]
  r=self.post('/actions/'+a['id']+'/complete',{'expected_revision':1,'outcome':'Vendor supplied plan'});self.assertEqual(r.status_code,200);self.assertTrue(r.json()['workflow']['actions'][0]['completed_at']);self.assertEqual(len(self.m.load_cases()[0].workflow['events']),3)
 def test_activity_occurrence_and_recording(self):
  r=self.post('/activities',{'kind':'information_requested','details':'Requested delivery commitment; reference email 17.','occurred_at':'2026-10-27T09:00:00-04:00'});self.assertEqual(r.status_code,200);e=r.json()['workflow']['events'][-1];self.assertEqual(e['source'],'manual');self.assertNotEqual(e['occurred_at'],e['recorded_at'])
 def test_invalid_dates_and_empty_owner(self):
  self.assertEqual(self.post('/actions',dict(description='Ask',responsible='PM',due_at='2026-11-01T12:00:00')).status_code,422)
  self.assertEqual(self.post('/activities',dict(kind='client_updated',details='Sent update',occurred_at='2099-01-01T00:00:00Z')).status_code,422)
  self.assertEqual(self.client.patch(self.url+'/owner',json=dict(actor='PM',owner=' ',expected_revision=0)).status_code,422)
 def test_failure_does_not_change_events(self):
  with patch.object(self.m,'save_cases',side_effect=OSError()):r=self.post('/activities',dict(kind='follow_up',details='Called vendor'))
  self.assertEqual(r.status_code,503);self.assertEqual(self.client.get(self.url).json(),self.case)
 def test_status_history_and_context_keeps_owner(self):
  self.client.patch(self.url+'/owner',json=dict(actor='PM',owner='Sarah',expected_revision=0))
  r=self.client.patch(self.url+'/clarifications',json=dict(clarifications=[],expected_clarifications=[],expected_issue_description='Shipment delayed',expected_revision=1));self.assertEqual(r.json()['workflow']['owner'],'Sarah')
  r=self.client.patch(self.url+'/status',json=dict(status='Resolved',expected_revision=2));self.assertEqual(r.json()['workflow']['events'][-1]['kind'],'case_status_changed')
  self.assertEqual(self.post('/actions',dict(expected_revision=3,description='Ask',responsible='PM',due_at='2026-11-01T12:00:00Z')).status_code,409)
if __name__=='__main__':unittest.main()
