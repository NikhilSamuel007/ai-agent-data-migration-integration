"""Background orchestration with per-run locks and real HTTP integration."""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import time
from .target_client import TargetClient, TargetError
from .profiling import profile_file
from .mapping import map_columns
from .engine import clean, reconcile, validate
from .store import now

class Agent:
    def __init__(self, store, port, token):
        self.store, self.port, self.token = store, port, token
        self.target = TargetClient(port, token)
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='relay-agent')
        self._guard, self._locks = threading.Lock(), {}

    def lock(self, run_id):
        with self._guard:
            return self._locks.setdefault(run_id, threading.Lock())

    def create(self, files, name, simulate_failure=False):
        run = dict(id=str(uuid.uuid4()), schemaVersion=3, name=name or 'Client migration', createdAt=now(),
                   status='mapping', files=files, records=[], simulateFailure=simulate_failure, pushStarted=False)
        self.store.save(run)
        self.executor.submit(self.process, run['id'])
        return run

    def refresh(self, run):
        for row in run['records']:
            if row['status'] == 'rejected':
                continue
            row['errors'] = validate(row['data'])
            row['status'] = 'review' if row['errors'] else 'ready'
            row.pop('duplicateOf', None)
        reconcile(run['records'])
        run['status'] = 'review' if any(r['status'] == 'review' for r in run['records']) else 'ready'
        self.store.save(run)

    def process(self, run_id):
        with self.lock(run_id):
            run = self.store.get(run_id)
            try:
                self.store.audit(run, 'Agent started', dict(reason='Infer source mappings, normalize safe values, validate, reconcile identities'))
                for file in run['files']:
                    file['profile'] = profile_file(file)
                    self.store.audit(run, 'Source profiled', dict(file=file['name'], profile=file['profile']))
                    file['mapping'] = map_columns(file)
                    self.store.save(run)
                    self.store.audit(run, 'Mapped source', dict(file=file['name'], mapping=file['mapping']))
                if any(m['status'] == 'pending' for f in run['files'] for m in f['mapping']):
                    run['status'] = 'mapping_review'
                    self.store.save(run)
                    self.store.audit(run, 'Mapping review required', dict(reason='At least one header has no unique explicit alias'))
                else:
                    self.prepare(run)
            except Exception as exc:
                run.update(status='error', error=str(exc))
                self.store.save(run)
                self.store.audit(run, 'Processing failed', dict(error=str(exc)))
        if run['status'] == 'ready':
            self.push(run_id)

    def prepare(self, run):
        run.update(records=[], status='cleaning')
        self.store.save(run)
        for file in run['files']:
            for index, raw in enumerate(file['rows'], 2):
                initial = {m['field']: raw.get(m['header'], '') for m in file['mapping'] if m['field']}
                initial_errors = validate(initial)
                result = clean(raw, file['mapping'])
                row = dict(id=str(uuid.uuid4()), file=file['name'], row=index, raw=raw,
                           data=result['record'], changes=result['changes'], errors=result['errors'],
                           status='review' if result['errors'] else 'ready', attempts=0, validationAttempts=2, initialErrors=initial_errors)
                run['records'].append(row)
                if row['changes']:
                    self.store.audit(run, 'Safe cleanup', dict(recordId=row['id'], source=f'{file["name"]}:{index}', changes=row['changes']))
        self.refresh(run)
        for row in run['records']:
            if row['status'] == 'duplicate':
                self.store.audit(run, 'Exact duplicate excluded', dict(recordId=row['id'], duplicateOf=row['duplicateOf'], reason='All target fields match after normalization; provenance retained'))
        self.store.audit(run, 'Validation complete', {key: sum(r['status'] == status for r in run['records']) for key, status in [('ready', 'ready'), ('review', 'review'), ('duplicates', 'duplicate')]})

    def schedule_push(self, run_id):
        self.executor.submit(self.push, run_id)

    def push(self, run_id):
        with self.lock(run_id):
            run = self.store.get(run_id)
            if run['status'] not in ('ready', 'partial') or any(r['status'] == 'review' for r in run['records']):
                return
            run.update(pushStarted=True, status='pushing')
            self.store.save(run)
            for row in run['records']:
                if row['status'] not in ('ready', 'failed'):
                    continue
                for attempt in range(3):
                    row['attempts'] += 1
                    row['status'] = 'sending'
                    self.store.save(run)
                    try:
                        result = self.target.create(run, row)
                        row.update(status='pushed', integrationError=None, targetId=result.get('targetId'))
                        self.store.audit(run, 'Record pushed', dict(recordId=row['id'], email=row['data']['email'],
                            attempt=row['attempts'], idempotent=result['idempotent'], targetId=row.get('targetId')))
                        self.store.save(run)
                        break
                    except Exception as exc:
                        retryable = isinstance(exc, TargetError) and exc.retryable
                        row.update(status='failed', integrationError=str(exc))
                        self.store.audit(run, 'Push failed', dict(recordId=row['id'], attempt=row['attempts'], error=str(exc),
                            retryable=retryable, reason='Transient errors receive at most three attempts; permanent conflicts are never retried automatically'))
                        self.store.save(run)
                        if not retryable or attempt == 2:
                            self.store.audit(run, 'Delivery escalated', dict(recordId=row['id'], reason='Permanent failure or automatic retry budget exhausted'))
                            break
                        delay = .25 * (2 ** attempt)
                        self.store.audit(run, 'Automatic retry scheduled', dict(recordId=row['id'], nextAttempt=row['attempts']+1, delaySeconds=delay))
                        time.sleep(delay)
            run['status'] = 'partial' if any(r['status'] == 'failed' for r in run['records']) else 'complete'
            self.store.save(run)

    def recover(self):
        for run in self.store.runs():
            if run['status'] in ('mapping', 'cleaning'):
                run.update(status='error', error='Processing interrupted by restart. Start a new migration.')
                self.store.save(run)
                self.store.audit(run, 'Restart recovery', dict(reason=run['error']))
            elif run['status'] == 'pushing':
                for row in run['records']:
                    if row['status'] == 'sending':
                        row.update(status='failed', integrationError='Interrupted; retry uses the same idempotency identity')
                run['status'] = 'partial'
                self.store.save(run)
                self.store.audit(run, 'Restart recovery', dict(reason='Uncertain writes can be retried idempotently'))
            elif run['status'] == 'ready':
                self.schedule_push(run['id'])
