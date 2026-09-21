import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from .common import APIError
from ..contracts import TargetRequest
from ..engine import validate

router = APIRouter(prefix='/mock', tags=['Internal mock target'])

@router.get('/employees')
def employees(request: Request, run_id: str | None = None):
    with request.app.state.store.connect() as db:
        rows = db.execute('SELECT * FROM target WHERE run_id=?', (run_id,)).fetchall() if run_id else db.execute('SELECT * FROM target').fetchall()
    return [dict(targetId=f'T-{r["record_id"]}', runId=r['run_id'], data=json.loads(r['body'])) for r in rows]

@router.post('/employees', status_code=201)
def insert(payload: TargetRequest, request: Request):
    data = payload.data.model_dump()
    if validate(data):
        raise APIError('Target schema validation failed', 422)
    with request.app.state.store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute("SELECT * FROM target WHERE email=? OR json_extract(body, '$.employee_id')=?", (data['email'], data['employee_id'])).fetchone()
        target_id = f'T-{payload.recordId}'
        if existing:
            if existing['run_id'] == payload.runId and existing['record_id'] == payload.recordId and json.loads(existing['body']) == data:
                return JSONResponse(dict(idempotent=True, targetId=target_id))
            raise APIError('Target already contains this email or employee ID. Existing data was not overwritten.', 409)
        for index in range(payload.simulateFailures):
            key = f'{payload.runId}:{payload.recordId}:failure:{index}'
            if not db.execute('SELECT key FROM attempts WHERE key=?', (key,)).fetchone():
                db.execute('INSERT INTO attempts VALUES(?)', (key,))
                return JSONResponse(dict(error=f'Simulated target outage ({index+1}/{payload.simulateFailures}).'), status_code=503)
        db.execute('INSERT INTO target VALUES(?,?,?,?)', (data['email'], json.dumps(data), payload.runId, payload.recordId))
    return dict(idempotent=False, targetId=target_id)

@router.delete('/runs/{run_id}')
def delete(run_id: str, request: Request):
    with request.app.state.store.connect() as db:
        count = db.execute('DELETE FROM target WHERE run_id=?', (run_id,)).rowcount
    return dict(deleted=count)
