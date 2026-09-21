"""Prove that the running backend uses real models and autonomously delivers.

The unfamiliar email and identifier headers must be automatically mapped using
Ollama agreement, not aliases. Always roll back any writes created by this check.
"""
import os
import time
import json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('API_BASE_URL','http://localhost:8000')
def main():
    with (ROOT/'backend/samples/semantic-auto.csv').open('rb') as f:
        response=requests.post(BASE+'/api/runs',files={'files':('semantic-auto.csv',f)},data={'name':'Real Ollama autonomous mapping verification'},timeout=10)
    response.raise_for_status()
    run_id=response.json()['id']
    try:
        deadline=time.monotonic()+480
        while time.monotonic()<deadline:
            response=requests.get(BASE+'/api/runs/'+run_id,timeout=10);response.raise_for_status()
            run=response.json()
            if run['status'] not in ('mapping','cleaning','ready','pushing'): break
            time.sleep(1)
        assert run['status']=='complete', f'Expected autonomous completion: {run["status"]}'
        mapping=run['files'][0]['mapping']
        semantic=[m for m in mapping if not m['evidence']['alias']]
        assert len(semantic)==3 and all(m['status']=='automatic' and m.get('llmProposal') and m['evidence']['llmAgreement'] for m in semantic)
        assert run['targetCount']==3
        evidence={'runId':run_id,'status':run['status'],'targetCount':run['targetCount'],'mappings':mapping,
                  'events':run['events'],'llm':run['llm'],'model':run['model']}
        (ROOT/'docs/live-ai-verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print('Live real-model mapping, validation and HTTP delivery passed for three employees.')
    finally:
        current=requests.get(BASE+'/api/runs/'+run_id,timeout=10).json()
        if current['status'] in ('complete','partial'):
            result=requests.post(BASE+f'/api/runs/{run_id}/rollback',json={},timeout=10)
            result.raise_for_status()
            print('Verification writes rolled back:',result.json())

if __name__=='__main__': main()
