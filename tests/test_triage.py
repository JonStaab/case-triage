import importlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

class TriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        os.environ['CASES_FILE'] = str(Path(cls.folder.name) / 'cases.json')
        cls.m = importlib.import_module('Case_Management')
        cls.client = TestClient(cls.m.app)

    def setUp(self):
        self.m.cases.clear()
        self.description = 'Checkout stopped for all customers. Restore immediately.'
        self.request = {'issue_description': self.description, 'customer_tier': 'High'}
        self.suggestion = self.m.TriageSuggestion(
            business_impact='Critical', impact_reason='All checkout has stopped.',
            impact_evidence=['Checkout stopped for all customers.'],
            time_sensitivity='Critical', urgency_reason='Immediate restoration requested.',
            urgency_evidence=['Restore immediately.'], missing_information=['When did it begin?'],
            next_action='Escalate to the on-call support lead.')

    def create(self):
        return self.client.post('/cases', json={**self.request, 'customer_name': 'Fictional Co',
            'business_impact': 'Low', 'time_sensitivity': 'Low'}).json()

    def test_preview_without_mutation(self):
        with patch.object(self.m, 'suggest_triage', return_value=self.suggestion):
            response = self.client.post('/triage', json=self.request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['suggested_priority'], 'P1')
        self.assertEqual(self.m.cases, [])

    def test_abstention_has_no_priority(self):
        self.suggestion.time_sensitivity = None
        self.suggestion.urgency_evidence = []
        with patch.object(self.m, 'suggest_triage', return_value=self.suggestion):
            result = self.client.post('/triage', json=self.request).json()
        self.assertIsNone(result['time_sensitivity'])
        self.assertIsNone(result['suggested_priority'])

    def test_validation(self):
        for field, value in [('issue_description', ' '), ('issue_description', 'x'*10001), ('customer_tier', 'VIP')]:
            self.assertEqual(self.client.post('/triage', json={**self.request, field:value}).status_code, 422)

    def test_missing_key(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            self.assertEqual(self.client.post('/triage', json=self.request).status_code, 503)

    def test_sdk_structured_output_and_policy(self):
        mock = MagicMock()
        mock.__enter__.return_value = mock
        mock.responses.parse.return_value = SimpleNamespace(output_parsed=self.suggestion)
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test'}), patch.object(self.m, 'OpenAI', return_value=mock):
            result = self.m.suggest_triage(self.description)
        self.assertEqual(result.business_impact, 'Critical')
        args = mock.responses.parse.call_args.kwargs
        self.assertEqual(args['input'], self.description)
        self.assertIn('not instructions', args['instructions'])
        self.assertFalse(args['store'])
        self.assertEqual(args['text_format'], self.m.TriageSuggestion)

    def test_provider_and_output_failures_are_safe(self):
        for parsed in [None, self.suggestion.model_copy(update={'impact_evidence':['invented evidence']}),
                       self.suggestion.model_copy(update={'impact_evidence':[]})]:
            mock = MagicMock(); mock.__enter__.return_value = mock
            mock.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
            with patch.dict(os.environ, {'OPENAI_API_KEY':'test'}), patch.object(self.m,'OpenAI',return_value=mock):
                self.assertEqual(self.client.post('/triage',json=self.request).status_code,502)
        with patch.object(self.m,'suggest_triage',side_effect=self.m.HTTPException(502,'Unavailable')):
            self.assertEqual(self.client.post('/triage',json=self.request).status_code,502)

    def review(self, case):
        return {'business_impact':'Critical', 'time_sensitivity':'Critical',
                'expected_business_impact':case['business_impact'],
                'expected_time_sensitivity':case['time_sensitivity'],
                'expected_issue_description':case['issue_description']}

    def test_review_saves_priority_and_preserves_model(self):
        case = self.create(); review = self.review(case)
        result = self.client.patch('/cases/'+case['unique_id']+'/triage',json=review)
        self.assertEqual(result.status_code,200)
        result = result.json()
        self.assertEqual(result['priority'],'P1')
        for key in ['unique_id','customer_name','customer_tier','issue_description']:
            self.assertEqual(result[key],case[key])
        self.assertEqual(self.m.load_cases()[0].priority,'P1')
        self.assertEqual(self.client.get('/cases/'+case['unique_id']).json(),result)
        self.assertEqual(self.client.patch('/cases/'+case['unique_id']+'/triage',json=review).status_code,409)

    def test_disk_failure_does_not_mutate(self):
        case=self.create()
        with patch.object(self.m,'save_cases',side_effect=OSError('private filesystem info')):
            result=self.client.patch('/cases/'+case['unique_id']+'/triage',json=self.review(case))
        self.assertEqual(result.status_code,503)
        self.assertNotIn('private',result.text)
        self.assertEqual(self.client.get('/cases/'+case['unique_id']).json(),case)

    def test_two_reviewers_conflict(self):
        case=self.create()
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes=list(pool.map(lambda _:self.client.patch('/cases/'+case['unique_id']+'/triage',json=self.review(case)).status_code, range(2)))
        self.assertEqual(sorted(codes),[200,409])

    def test_missing_and_invalid_review(self):
        case=self.create(); review=self.review(case)
        self.assertEqual(self.client.patch('/cases/missing/triage',json=review).status_code,404)
        self.assertEqual(self.client.patch('/cases/'+case['unique_id']+'/triage',json={**review,'business_impact':'P1'}).status_code,422)

if __name__=='__main__': unittest.main()
