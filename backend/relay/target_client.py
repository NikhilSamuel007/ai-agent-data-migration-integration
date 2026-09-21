"""One transport boundary; retries are orchestrated and audited by Agent."""
import requests

class TargetError(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable

class TargetClient:
    def __init__(self, port, token):
        self.base = f'http://127.0.0.1:{port}'
        self.headers = {'X-Internal-Token': token}

    def create(self, run, row):
        failures = {'E006': 1, 'E007': 3}.get(row['data']['employee_id'], 0) if run['simulateFailure'] else 0
        try:
            response = requests.post(self.base + '/mock/employees', headers=self.headers,
                json=dict(runId=run['id'], recordId=row['id'], data=row['data'], simulateFailures=failures), timeout=5)
            result = response.json()
        except requests.RequestException as exc:
            raise TargetError(str(exc), retryable=True) from exc
        if not response.ok:
            raise TargetError(result.get('error', f'HTTP {response.status_code}'), retryable=response.status_code in (408, 429, 500, 502, 503, 504))
        return result

    def rollback(self, run_id):
        response = requests.delete(self.base + '/mock/runs/' + run_id, headers=self.headers, timeout=5)
        response.raise_for_status()
        return response.json()

    def list(self, run_id):
        response = requests.get(self.base + '/mock/employees', headers=self.headers, params={'run_id': run_id}, timeout=5)
        response.raise_for_status()
        return response.json()
