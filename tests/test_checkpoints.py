import datetime
import unittest
import test_workflow as foundation
class CheckpointTests(unittest.TestCase):
 setUp=foundation.WorkflowTests.setUp
 post=foundation.WorkflowTests.post
 def test_asap_action_without_deadline(self):
  r=self.post('/actions',dict(description='Contact vendor immediately',responsible='PM',waiting_on='Vendor'))
  self.assertEqual(r.status_code,200);a=r.json()['workflow']['actions'][0];self.assertIsNone(a['due_at']);self.assertEqual(a['kind'],'immediate')
  self.assertIn('Waiting without a follow-up checkpoint',r.json()['attention']['signals']);self.assertEqual(r.json()['attention']['overdue_actions'],[])
 def test_commitment_requires_date(self):
  for kind in ['follow_up','client_update','vendor_response','commitment']:
   self.assertEqual(self.post('/actions',dict(description='Update',responsible='PM',kind=kind)).status_code,422)
 def test_overdue_is_specific_and_completed_is_removed(self):
  r=self.post('/actions',dict(description='Update client',responsible='PM',kind='client_update',due_at='2020-01-01T00:00:00Z'));self.assertEqual(r.status_code,200)
  self.assertIn('Client update commitment overdue',r.json()['attention']['signals']);a=r.json()['workflow']['actions'][0]
  r=self.post('/actions/'+a['id']+'/complete',dict(expected_revision=1,outcome='Update delivered'))
  self.assertNotIn('Client update commitment overdue',r.json()['attention']['signals']);self.assertFalse(r.json()['attention']['acknowledgment_recorded'])
 def test_signal_clock_and_explicit_acknowledgment(self):
  c=self.m.cases[0];c.created_at='2026-01-01T12:00:00+00:00'
  self.m.case_workflow.record(c,'information_requested','Requested facts','PM',occurred_at='2026-01-01T12:05:00+00:00',source='manual')
  at=datetime.datetime(2026,1,1,13,tzinfo=datetime.timezone.utc)
  signal=self.m.case_workflow.attention(c,at);self.assertEqual(signal['elapsed_since_creation_seconds'],3600);self.assertFalse(signal['acknowledgment_recorded'])
  self.m.case_workflow.record(c,'initial_response','Acknowledged','PM',occurred_at='2026-01-01T12:02:00+00:00',source='manual')
  signal=self.m.case_workflow.attention(c,at);self.assertEqual(signal['first_recorded_response_seconds'],120)
 def test_legacy_unknown_and_resolved_pauses(self):
  c=self.m.Case('old','Demo','Issue','Low','Low','Low','P4')
  self.assertIn('Earlier response history unknown',self.m.case_workflow.attention(c)['signals'])
  c.status='Resolved';self.assertEqual(self.m.case_workflow.attention(c)['signals'],[])
 def test_legacy_date_preserved_without_reclassification(self):
  c=self.m.cases[0];c.workflow['actions'].append(dict(id='old',description='Legacy task',responsible='PM',due_at='2020-01-01T00:00:00+00:00',completed_at=None))
  signal=self.m.case_workflow.attention(c);self.assertEqual(signal['overdue_actions'][0]['kind'],'legacy_due');self.assertIn('Dated action overdue',signal['signals'])
