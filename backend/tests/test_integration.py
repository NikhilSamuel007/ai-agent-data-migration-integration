import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import requests
import pytest

ROOT = Path(__file__).resolve().parents[1]

class Server:
    def __init__(self, path):
        self.path = path
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        self.process = None

    def start(self):
        self.process = subprocess.Popen([sys.executable, 'server.py'], cwd=ROOT,
            env=dict(os.environ, PORT=str(self.port), DB_PATH=str(self.path), OLLAMA_URL='http://127.0.0.1:9'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                if self.get('/api/runs').ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(.1)
        raise AssertionError('Server did not start')

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)

    def get(self, path):
        return requests.get(self.url + path, timeout=5)

    def post(self, path, data=None, **kwargs):
        return requests.post(self.url + path, json=data if not kwargs else None, timeout=5, **kwargs)

    def wait(self, id, status):
        for _ in range(150):
            run = self.get('/api/runs/' + id).json()
            if run['status'] == status:
                return run
            time.sleep(.1)
        raise AssertionError(f'Expected {status}: {run}')

    def upload(self, email='unique@example.com'):
        return self.post('/api/runs', files={'files': ('clean.csv', f'Employee ID,First Name,Last Name,Email,Date of Birth,Employment Status\nE100,Test,Person,{email},1990-01-01,Active')}).json()

@pytest.fixture
def server(tmp_path):
    value = Server(tmp_path / 'test.sqlite')
    value.start()
    try:
        yield value
    finally:
        value.stop()

def test_full_pipeline(server):
    clean = server.upload()
    assert server.wait(clean['id'], 'complete')['targetCount'] == 1
    run = server.post('/api/demo', {}).json()
    run = server.wait(run['id'], 'mapping_review')
    assert run['targetCount'] == 0
    pending = [(f,m) for f in run['files'] for m in f['mapping'] if m['status']=='pending']
    assert len(pending) == 1 and pending[0][1]['header'] == 'Status'
    assert server.post(f'/api/runs/{run["id"]}/mapping', dict(file='staff.xlsx',header='Status',field='employment_status',reason='HR export lifecycle')).ok
    run = server.wait(run['id'], 'partial')
    assert sum(r['status'] == 'duplicate' for r in run['records']) == 1
    assert run['targetCount'] == 6
    assert next(r for r in run['records'] if r['data']['employee_id'] == 'E006')['attempts'] == 2
    assert next(r for r in run['records'] if r['data']['employee_id'] == 'E007')['attempts'] == 3
    route = f'/api/runs/{run["id"]}/records/{run["records"][0]["id"]}'
    assert server.post(route, dict(action='reject')).status_code == 409
    assert server.post(f'/api/runs/{run["id"]}/retry', {}).ok
    run = server.wait(run['id'], 'complete')
    assert run['targetCount'] == 7
    delivered = server.get(f'/api/runs/{run["id"]}/target').json()
    assert len(delivered) == 7
    assert all(r['runId'] == run['id'] and r['targetId'] for r in delivered)
    assert next(r for r in run['records'] if r['data']['employee_id'] == 'E007')['attempts'] == 4
    collision = server.upload()
    assert server.wait(collision['id'], 'partial')['targetCount'] == 0
    assert server.post(f'/api/runs/{collision["id"]}/rollback', {}).ok
    assert server.get('/api/runs/' + clean['id']).json()['targetCount'] == 1
    assert server.post(f'/api/runs/{run["id"]}/rollback', {}).json()['deleted'] == 7
    result = server.get('/api/runs/' + run['id']).json()
    assert result['status'] == 'rolled_back' and result['targetCount'] == 0
    assert server.get(f'/api/runs/{run["id"]}/target').json() == []
    assert any(e['action'] == 'Mapping resolved' for e in result['events'])
    assert server.post(f'/api/runs/{run["id"]}/retry', {}).status_code == 409
    assert server.post('/mock/employees', {}).status_code == 403

def test_restart_and_legacy_json_idempotency(server):
    run = server.upload('recovery@example.com')
    run = server.wait(run['id'], 'complete')
    server.stop()
    with sqlite3.connect(server.path) as db:
        run['status'] = 'pushing'
        run['records'][0]['status'] = 'sending'
        db.execute('UPDATE runs SET body=? WHERE id=?', (json.dumps(run), run['id']))
        # Original JavaScript JSON.stringify used compact JSON and a different key order.
        legacy = dict(reversed(list(run['records'][0]['data'].items())))
        db.execute('UPDATE target SET body=? WHERE run_id=?', (json.dumps(legacy, separators=(',', ':')), run['id']))
    server.start()
    assert server.get('/api/runs/' + run['id']).json()['status'] == 'partial'
    assert server.post(f'/api/runs/{run["id"]}/retry', {}).ok
    result = server.wait(run['id'], 'complete')
    assert result['targetCount'] == 1
    assert any(e['action'] == 'Record pushed' and e['detail']['idempotent'] for e in result['events'])

def test_reject_conflict_and_input_guards(server):
    payload = 'Employee ID,First Name,Last Name,Email,Date of Birth,Employment Status,Department\nE1,Ada,Lovelace,ada@example.com,1990-01-01,Active,Sales\nE1,Ada,Lovelace,ada@example.com,1990-01-01,Active,Finance'
    run = server.post('/api/runs', files={'files': ('conflict.csv', payload)}).json()
    run = server.wait(run['id'], 'review')
    assert len([r for r in run['records'] if r['status'] == 'review']) == 2
    assert server.post(f'/api/runs/{run["id"]}/records/{run["records"][1]["id"]}', dict(action='reject', reason='Older conflicting export')).ok
    assert server.wait(run['id'], 'complete')['targetCount'] == 1
    assert server.post('/api/demo', {}, headers={'Origin': 'https://foreign.example'}).status_code == 403
    assert server.get('/api/runs/missing').status_code == 404
    assert server.post('/api/runs', files={'files': ('bad.csv', 'Name,Name\na,b')}).status_code == 400

def test_frontend_cors_and_api_separation(server):
    origin = {'Origin': 'http://localhost:3000'}
    response = requests.options(server.url + '/api/demo', headers={**origin,
        'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'}, timeout=5)
    assert response.status_code == 200
    assert response.headers['Access-Control-Allow-Origin'] == origin['Origin']
    response = requests.get(server.url + '/api/schema', headers=origin, timeout=5)
    assert response.ok and response.headers['Access-Control-Allow-Origin'] == origin['Origin']
    response = requests.options(server.url + '/api/demo', headers={'Origin': 'https://untrusted.example'}, timeout=5)
    assert response.status_code == 403
    assert 'Access-Control-Allow-Origin' not in response.headers
    assert server.get('/').status_code == 404
    assert server.get('/app.js').status_code == 404
    assert server.get('/api/health').json()['service'] == 'relay-backend'

def test_record_correction_revalidates_twice_and_resumes(server):
    payload='Employee ID,First Name,Last Name,Email,Date of Birth,Employment Status\nE200,Ada,Lovelace,ada@@example,03/04/1990,Active'
    run=server.post('/api/runs',files={'files':('uncertain.csv',payload)}).json()
    run=server.wait(run['id'],'review')
    row=run['records'][0]
    assert row['validationAttempts']==2 and run['targetCount']==0
    assert {e['field'] for e in row['errors']}=={'email','date_of_birth'}
    route=f'/api/runs/{run["id"]}/records/{row["id"]}'
    assert server.post(route,dict(action='approve')).status_code==400
    assert server.post(route,dict(action='correct',data={'date_of_birth':'1990-04-03'},reason='Confirmed day/month')).status_code==400
    assert server.post(route,dict(action='correct',data={'date_of_birth':'1990-04-03','email':'ada@example.com'},reason='Client supplied verified email and date')).ok
    assert server.wait(run['id'],'complete')['targetCount']==1
    # Same employee ID with another email must not insert a second target identity.
    conflict=server.post('/api/runs',files={'files':('conflict.csv',payload.replace('ada@@example','other@example.com').replace('03/04/1990','1990-04-03'))}).json()
    result=server.wait(conflict['id'],'partial')
    assert result['records'][0]['attempts']==1 and result['targetCount']==0
