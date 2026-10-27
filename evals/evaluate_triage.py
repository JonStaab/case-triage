"""Run a small live, synthetic triage evaluation. Makes paid API calls.
From the project folder: python evals/evaluate_triage.py
Never reads case records. Results contain synthetic issues only.
"""
import json, os, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['CASES_FILE'] = str(Path(__file__).parent/'unused-evaluation-cases.json')
from Case_Management import suggest_triage, HTTPException

def evaluate(item):
    try:
        result=suggest_triage(item['description'])
        passed=result.business_impact in item['impact'] and result.time_sensitivity in item['urgency']
        if (None in item['impact'] or None in item['urgency']) and not result.missing_information:
            passed=False
        return {'name':item['name'],'passed':passed,'expected_impact':item['impact'],
                'expected_urgency':item['urgency'],'actual':result.model_dump()}
    except HTTPException as error:
        return {'name':item['name'],'passed':False,'error_status':error.status_code,'error':error.detail}

if __name__=='__main__':
    if not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('Set OPENAI_API_KEY before running the live evaluation.')
    folder=Path(__file__).parent
    cases=json.loads((folder/'triage_cases.json').read_text(encoding='utf-8-sig'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(evaluate,cases))
    report={'model':os.environ.get('OPENAI_MODEL','gpt-5.5'),'passed':sum(r['passed'] for r in results),'total':len(results),'results':results}
    (folder/'latest-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"Live evaluation: {report['passed']}/{report['total']} passed")
    for result in results:
        print(result['name'], 'PASS' if result['passed'] else 'FAIL', result.get('error',''))
    raise SystemExit(0 if report['passed']==report['total'] else 1)
