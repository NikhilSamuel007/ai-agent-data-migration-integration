import json
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .common import APIError, run_for, locked
from ..config import BACKEND_ROOT
from ..ingest import ingest
from ..model import MODEL_STATE
from ..llm import LLM_STATE

router = APIRouter(prefix='/api', tags=['Migrations'])

@router.get('/health')
def health(request: Request):
    with request.app.state.store.connect() as db:
        db.execute('SELECT 1')
    return dict(status='ok', service='relay-backend')

@router.get('/schema')
def schema():
    return json.loads((BACKEND_ROOT / 'schema.json').read_text())

@router.get('/runs')
def runs(request: Request):
    return [{k: r[k] for k in ('id', 'name', 'status', 'createdAt')} for r in request.app.state.store.runs()]

@router.get('/runs/{run_id}')
def detail(run_id: str, request: Request):
    store = request.app.state.store
    return dict(run_for(request, run_id), events=store.events(run_id), model=MODEL_STATE.copy(), llm=LLM_STATE.copy(), targetCount=store.target_count(run_id))

@router.get('/runs/{run_id}/audit')
def export(run_id: str, request: Request):
    run = run_for(request, run_id)
    return JSONResponse(dict(run=run, events=request.app.state.store.events(run_id)), headers={'Content-Disposition': f'attachment; filename="relay-{run["id"]}-audit.json"'})

@router.get('/runs/{run_id}/target')
def target_records(run_id: str, request: Request):
    run_for(request, run_id)
    return request.app.state.agent.target.list(run_id)

@router.post('/runs', status_code=202)
async def upload(request: Request, files: list[UploadFile] = File(...), name: str = Form('Client migration'), simulate_failure: bool = Form(False)):
    if not 1 <= len(files) <= 5:
        raise APIError('Choose between one and five source files')
    if len({f.filename for f in files}) != len(files):
        raise APIError('File names must be unique')
    sources = []
    for file in files:
        try:
            content = await file.read(5 * 1024 * 1024 + 1)
            sources.append(await run_in_threadpool(ingest, file.filename or '', content))
        finally:
            await file.close()
    return request.app.state.agent.create(sources, name[:100], simulate_failure)

@router.post('/demo', status_code=202)
def demo(request: Request):
    sources = [ingest(name, (BACKEND_ROOT / 'samples' / name).read_bytes()) for name in ('employees_hr.csv', 'employees_backup.csv', 'staff.xlsx')]
    return request.app.state.agent.create(sources, 'Northstar · Employee migration', True)

@router.post('/runs/{run_id}/retry', status_code=202)
def retry(run_id: str, request: Request):
    with locked(request, run_id) as run:
        if run['status'] not in ('partial', 'ready'):
            raise APIError('Retry is available only for a ready or partially failed migration', 409)
    request.app.state.agent.schedule_push(run_id)
    return dict(ok=True)

@router.post('/runs/{run_id}/rollback')
def rollback(run_id: str, request: Request):
    with locked(request, run_id) as run:
        if run['status'] not in ('partial', 'complete'):
            raise APIError('Wait for integration to finish before rollback', 409)
        state = request.app.state
        state.store.audit(run, 'Rollback started', dict(actor='local consultant', reason='Remove only inserts owned by this run'))
        try:
            result = state.agent.target.rollback(run_id)
        except Exception as exc:
            state.store.audit(run, 'Rollback failed', dict(error=str(exc), actor='local consultant'))
            raise APIError('Rollback failed; target writes are not confirmed removed. Retry rollback.', 502) from exc
        for row in run['records']:
            if row['status'] in ('pushed', 'failed', 'ready'):
                row['status'] = 'rolled_back'
        run['status'] = 'rolled_back'
        state.store.save(run)
        state.store.audit(run, 'Migration rolled back', dict(deleted=result['deleted'], reason='Consultant requested rollback; only records owned by this run were removed', actor='local consultant'))
    return result
