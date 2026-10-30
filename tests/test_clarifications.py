import importlib, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from fastapi.testclient import TestClient

class ClarificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory()
        cls.m=importlib.import_module('Case_Management')
        cls.client=TestClient(cls.m.app)

    def setUp(self):
        self.m.cases.clear()
        os.environ['DEMO_MODE']='false'
        os.environ['OPENAI_API_KEY']='test'
        self.m.CASES_FILE=Path(self.folder.name)/'cases.json'
        self.payload=dict(customer_name='Fictional Supplies',issue_description='Raw material costs are rising.',
            customer_tier='Low', business_impact='Low',time_sensitivity='Low')
        self.note=dict(question='What is the operational impact?',answer='All production has stopped. Restore immediately.')

    def create(self, notes=None):
        return self.client.post('/cases',json={**self.payload,'clarifications': notes or []}).json()

    def patch_data(self,case):
        return dict(clarifications=[self.note],expected_clarifications=case.get('clarifications',[]),
                    expected_issue_description=case['issue_description'])

    def test_new_case_round_trip_and_old_format(self):
        old=self.create()
        self.assertNotIn('clarifications',old)
        case=self.create([self.note])
        self.assertEqual(case['clarifications'],[self.note])
        loaded=self.m.load_cases()
        self.assertEqual(loaded[0].clarifications,[])
        self.assertEqual(loaded[1].clarifications,[self.note])
        self.assertEqual(case['issue_description'],self.payload['issue_description'])

    def test_save_answers_without_changing_ratings(self):
        case=self.create()
        result=self.client.patch('/cases/'+case['unique_id']+'/clarifications',json=self.patch_data(case))
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['clarifications'],[self.note])
        for key,value in case.items():
            if key not in ('revision','workflow'): self.assertEqual(result.json()[key],value)
        self.assertEqual(self.m.load_cases()[0].clarifications,[self.note])
        self.assertEqual(self.client.patch('/cases/'+case['unique_id']+'/clarifications',json=self.patch_data(case)).status_code,409)

    def test_review_saves_answers_and_stale_context_conflicts(self):
        case=self.create()
        review={**self.patch_data(case), 'business_impact':'Critical','time_sensitivity':'Critical',
                'expected_business_impact':'Low','expected_time_sensitivity':'Low'}
        result=self.client.patch('/cases/'+case['unique_id']+'/triage',json=review)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['priority'],'P1')
        self.assertEqual(result.json()['clarifications'],[self.note])
        review['expected_business_impact']='Critical';review['expected_time_sensitivity']='Critical'
        self.assertEqual(self.client.patch('/cases/'+case['unique_id']+'/triage',json=review).status_code,409)

    def test_legacy_review_keeps_saved_answers(self):
        case=self.create([self.note])
        review={**self.patch_data(case),'business_impact':'High','time_sensitivity':'Urgent',
                'expected_business_impact':'Low','expected_time_sensitivity':'Low'}
        del review['clarifications']
        result=self.client.patch('/cases/'+case['unique_id']+'/triage',json=review)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['clarifications'],[self.note])

    def test_answer_validation_and_missing_case(self):
        case=self.create()
        for note in [{**self.note,'answer':' '},{**self.note,'answer':'x'*1501},{**self.note,'question':'x'*501}]:
            self.assertEqual(self.client.post('/cases',json={**self.payload,'clarifications':[note]}).status_code,422)
        self.assertEqual(self.client.post('/triage',json={'issue_description':'x','customer_tier':'Low','clarifications':[self.note]*21}).status_code,422)
        self.assertEqual(self.client.patch('/cases/missing/clarifications',json=self.patch_data(case)).status_code,404)

    def test_save_failure_preserves_memory(self):
        case=self.create()
        with patch.object(self.m,'save_cases',side_effect=OSError('private')):
            result=self.client.patch('/cases/'+case['unique_id']+'/clarifications',json=self.patch_data(case))
        self.assertEqual(result.status_code,503)
        self.assertEqual(self.client.get('/cases/'+case['unique_id']).json(),case)

    def test_model_receives_answers_and_quotes_are_grounded(self):
        suggestion=self.m.TriageSuggestion(business_impact='Critical',impact_reason='Production stopped.',
            impact_evidence=['All production has stopped.'],time_sensitivity='Critical',urgency_reason='Immediate.',
            urgency_evidence=['Restore immediately.'],missing_information=[],next_action='Escalate to the support lead.')
        mock=MagicMock();mock.__enter__.return_value=mock
        mock.responses.parse.return_value=SimpleNamespace(output_parsed=suggestion)
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test'}),patch.object(self.m,'OpenAI',return_value=mock):
            result=self.client.post('/triage',json={'issue_description':self.payload['issue_description'],
                'customer_tier':'Low','clarifications':[self.note]})
        self.assertEqual(result.status_code,200)
        self.assertIn(self.note['answer'],mock.responses.parse.call_args.kwargs['input'])
        self.assertEqual(result.json()['suggested_priority'],'P1')
        # A question alone cannot provide evidence that its premise is true.
        suggestion.impact_evidence=[self.note['question']]
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test'}),patch.object(self.m,'OpenAI',return_value=mock):
            result=self.client.post('/triage',json={'issue_description':self.payload['issue_description'],
                'customer_tier':'Low','clarifications':[self.note]})
        self.assertEqual(result.status_code,502)

    def test_summary_includes_saved_context(self):
        case=self.create([self.note])
        with patch.object(self.m,'summarize_case',return_value='A summary') as summary:
            self.assertEqual(self.client.post('/cases/'+case['unique_id']+'/summary').status_code,200)
        self.assertIn(self.note['answer'],summary.call_args.args[0])

if __name__=='__main__':unittest.main()
