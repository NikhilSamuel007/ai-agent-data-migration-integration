from fastapi import APIRouter, Request
from .common import APIError, locked
from ..contracts import MappingDecision, RecordDecision
from ..engine import FIELDS, clean, validate

router = APIRouter(prefix='/api/runs', tags=['Human review'])

@router.post('/{run_id}/mapping')
def mapping(run_id: str, data: MappingDecision, request: Request):
    state = request.app.state
    with locked(request, run_id, edit=True) as run:
        if run['status'] != 'mapping_review':
            raise APIError('No mapping review is pending', 409)
        file = next((f for f in run['files'] if f['name'] == data.file), None)
        item = next((m for m in file['mapping'] if m['header'] == data.header), None) if file else None
        if not item or item['status'] != 'pending':
            raise APIError('Pending mapping not found')
        if data.field and any(m is not item and m['field'] == data.field for m in file['mapping']):
            raise APIError('That target field is already mapped. Ignore this column or choose another.')
        before = dict(item)
        item.update(field=data.field, status='approved' if data.field else 'ignored')
        state.store.audit(run, 'Mapping resolved', dict(file=file['name'], header=item['header'], field=data.field, previousProposal=before, actor='local consultant', reason=data.reason))
        state.store.save(run)
        if not any(m['status'] == 'pending' for f in run['files'] for m in f['mapping']):
            state.agent.prepare(run)
        ready = run['status'] == 'ready'
    if ready:
        state.agent.schedule_push(run_id)
    return dict(ok=True)

@router.post('/{run_id}/records/{record_id}')
def resolve(run_id: str, record_id: str, data: RecordDecision, request: Request):
    state = request.app.state
    with locked(request, run_id, edit=True) as run:
        row = next((r for r in run['records'] if r['id'] == record_id), None)
        if not row or row['status'] != 'review':
            raise APIError('Only pending review records can be resolved', 409)
        before = row['data'].copy()
        if data.action == 'reject':
            row['status'] = 'rejected'
        else:
            if set(data.data) - set(FIELDS):
                raise APIError('Unknown employee field')
            corrected = dict(before, **{f: v.strip() for f, v in data.data.items()})
            corrected = clean(corrected, [dict(header=f, field=f) for f in FIELDS])['record']
            errors = validate(corrected)
            if errors:
                state.store.audit(run, 'Correction failed validation', dict(recordId=record_id, errors=errors, actor='local consultant'))
                raise APIError('; '.join(f'{e["field"]}: {e["reason"]}' for e in errors))
            row['data'] = corrected
        state.store.audit(run, 'Human resolution', dict(recordId=record_id, action=data.action, before=before, after=row['data'], actor='local consultant', reason=data.reason))
        state.agent.refresh(run)
        ready = run['status'] == 'ready'
    if ready:
        state.agent.schedule_push(run_id)
    return dict(ok=True)
