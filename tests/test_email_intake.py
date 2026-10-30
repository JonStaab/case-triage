import base64,importlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
class EmailTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.env=patch.dict(os.environ,{'EMAIL_INTAKE_ENABLED':'true','DEMO_MODE':'false','PRIVATE_USERNAME':'manager','PRIVATE_PASSWORD':'fictional-password-123','EMAIL_WEBHOOK_SECRET':'s'*40,'GMAIL_INTAKE_MAILBOX':'triage@example.com','EMAIL_DRAFTS_FILE':str(Path(self.tmp.name)/'drafts.json')});self.env.start();self.addCleanup(self.env.stop)
  self.m=importlib.import_module('Case_Management');self.m.CASES_FILE=Path(self.tmp.name)/'cases.json';self.m.cases.clear();self.client=TestClient(self.m.app)
  self.auth={'Authorization':'Basic '+base64.b64encode(b'manager:fictional-password-123').decode()};self.webhook={'Authorization':'Bearer '+'s'*40}
 def payload(self,body='All operations stopped. Support needed today.',message='a1'):
  raw='From: Demo <sender@example.com>\r\nSubject: Fictional outage\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n'+body
  return dict(mailbox='triage@example.com',message_id=message,thread_id='b1',raw=base64.urlsafe_b64encode(raw.encode()).decode().rstrip('='))
 def deliver(self,data=None):return self.client.post('/integrations/gmail',json=data or self.payload(),headers=self.webhook)
 def drafts(self):return self.client.get('/email-drafts',headers=self.auth).json()
 def test_private_gate_all_data_and_static(self):
  for path in ['/','/cases','/email-drafts','/static/index.html','/docs','/demo-config']:
   self.assertEqual(self.client.get(path).status_code,401)
  self.assertEqual(self.client.get('/health').status_code,200)
  self.assertEqual(self.client.get('/cases',headers=self.auth).status_code,200)
 def test_webhook_does_not_accept_manager_password(self):
  self.assertEqual(self.client.post('/integrations/gmail',json=self.payload(),headers=self.auth).status_code,401)
  self.assertEqual(self.client.post('/integrations/gmail',json=self.payload()).status_code,401)
 def test_public_mode_fails_closed(self):
  with patch.dict(os.environ,{'DEMO_MODE':'true'}):self.assertEqual(self.deliver().status_code,503)
 def test_disabled_public_app_unchanged(self):
  with patch.dict(os.environ,{'EMAIL_INTAKE_ENABLED':'false'}):
   self.assertEqual(self.client.get('/cases').status_code,200);self.assertEqual(self.deliver().status_code,404);self.assertEqual(self.client.get('/email-drafts').status_code,404)
 def test_duplicate_delivery_and_thread_grouping(self):
  self.assertEqual(self.deliver().status_code,200);self.assertEqual(self.deliver().json()['status'],'duplicate')
  self.assertEqual(self.deliver(self.payload('Follow up: service still down.',message='a2')).status_code,200)
  d=self.drafts();self.assertEqual(len(d),1);self.assertEqual(len(d[0]['messages']),2);self.assertEqual(d[0]['revision'],2);self.assertEqual(self.m.cases,[])
 def test_mailbox_and_size_validation(self):
  bad=self.payload();bad['mailbox']='personal@example.com';self.assertEqual(self.deliver(bad).status_code,403)
  self.assertEqual(self.deliver(self.payload('x'*8001)).status_code,422)
  bad=self.payload();bad['raw']='!invalid!';self.assertEqual(self.deliver(bad).status_code,422)
 def test_persistence_failure_no_ack(self):
  with patch.object(self.m.email_intake.os,'replace',side_effect=OSError()):self.assertEqual(self.deliver().status_code,503)
  self.assertEqual(self.drafts(),[]);self.assertEqual(self.deliver().status_code,200)
 def test_html_not_executed_attachments_ignored(self):
  raw='From: sender@example.com\r\nSubject: Demo\r\nContent-Type: text/html\r\n\r\n<p>Outage</p><script>secret()</script>'
  data=self.payload();data['raw']=base64.urlsafe_b64encode(raw.encode()).decode()
  self.assertEqual(self.deliver(data).status_code,200);self.assertNotIn('secret()',self.drafts()[0]['messages'][0]['body'])
 def test_review_create_link_and_retry_conflict(self):
  self.deliver();d,description=self.m.email_intake.draft_for_review('b1',1)
  payload=dict(customer_name='Demo',issue_description=description,customer_tier='Low',business_impact='Critical',time_sensitivity='Urgent',source_email_draft_id='b1',source_email_revision=1)
  r=self.client.post('/cases',json=payload,headers=self.auth);self.assertEqual(r.status_code,200);c=r.json()
  self.assertEqual(self.drafts()[0]['linked_case_id'],c['unique_id'])
  self.assertEqual(self.client.post('/cases',json=payload,headers=self.auth).status_code,409)
  self.assertEqual(self.m.load_cases()[0].source_email_draft_id,'b1')
  self.client.patch('/cases/'+c['unique_id']+'/status',json={'status':'Resolved','expected_revision':0},headers=self.auth)
  self.assertEqual(self.m.load_cases()[0].source_email_draft_id,'b1')
 def test_new_mail_rejects_stale_review(self):
  self.deliver();_,text=self.m.email_intake.draft_for_review('b1',1);self.deliver(self.payload('New facts',message='a2'))
  payload=dict(customer_name='Demo',issue_description=text,customer_tier='Low',business_impact='Critical',time_sensitivity='Urgent',source_email_draft_id='b1',source_email_revision=1)
  self.assertEqual(self.client.post('/cases',json=payload,headers=self.auth).status_code,409)
 def test_disabling_connector_keeps_imported_data_private(self):
  self.deliver()
  with patch.dict(os.environ,{'EMAIL_INTAKE_ENABLED':'false'}):
   self.assertEqual(self.client.get('/cases').status_code,401)
 def test_email_not_sent_to_ai_automatically(self):
  with patch.object(self.m,'suggest_triage') as ai:self.deliver();ai.assert_not_called()
if __name__=='__main__':unittest.main()
