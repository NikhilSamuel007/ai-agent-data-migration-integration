from contextlib import contextmanager

class APIError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def run_for(request, run_id):
    run = request.app.state.store.get(run_id)
    if run is None:
        raise APIError('Migration not found', 404)
    return run

@contextmanager
def locked(request, run_id, edit=False):
    lock = request.app.state.agent.lock(run_id)
    if not lock.acquire(blocking=False):
        raise APIError('This migration is currently processing.', 409)
    try:
        run = run_for(request, run_id)
        if edit and run['pushStarted']:
            raise APIError('This migration is locked after integration starts.', 409)
        yield run
    finally:
        lock.release()
