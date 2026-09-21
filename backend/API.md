# Relay backend HTTP API

Base URL: `http://localhost:8000`. FastAPI interactive documentation: `/docs`; machine-readable OpenAPI: `/openapi.json`. Pydantic validates request contracts. Responses are JSON, including errors (`{"error":"..."}`). No frontend files are served by this service. The application is a local, single-operator prototype without authentication. `/mock/*` is internal and requires a private per-process token; the frontend never calls it.

## Endpoints

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/api/health` | None | `{status: "ok", service: "relay-backend"}` |
| GET | `/api/schema` | None | Employee field contract |
| GET | `/api/runs` | None | Array of `{id, name, status, createdAt}` |
| POST | `/api/runs` | Multipart `files` (repeated), optional `name`, `simulate_failure` (default false) | 202, new migration |
| POST | `/api/demo` | `{}` | 202, migration using sample files |
| GET | `/api/runs/{id}` | None | Full migration, source profiles, mapping evidence, records, audit events, MiniLM/Ollama status, target count |
| POST | `/api/runs/{id}/mapping` | Mapping decision below | `{ok: true}` |
| POST | `/api/runs/{id}/records/{recordId}` | Record decision below | `{ok: true}` |
| POST | `/api/runs/{id}/retry` | `{}` | 202, `{ok: true}` |
| POST | `/api/runs/{id}/rollback` | `{}` | `{deleted: number}` |
| GET | `/api/runs/{id}/target` | None | Actual persisted target records for the run |
| GET | `/api/runs/{id}/audit` | None | JSON attachment with migration and audit events |

### Upload example

```sh
curl -F "name=Client employees" -F "files=@samples/employees_hr.csv" -F "files=@samples/employees_backup.csv" http://localhost:8000/api/runs
```

Run this from `backend/`. The response supplies the migration `id`. Poll `GET /api/runs/{id}` to watch progress; the frontend polls every 1.2 seconds. A successful creation response means the job was accepted, not that migration is finished.

### Mapping decision

```json
{
  "file": "semantic-mapping.csv",
  "header": "Business group",
  "field": "department",
  "reason": "Client confirmed this is the department"
}
```

Use `field: null` to explicitly ignore a column. A target field cannot be mapped twice in the same file. Accepted fields: `employee_id`, `first_name`, `last_name`, `email`, `date_of_birth`, `department`, `employment_status`, `account_status`.

### Record decision

```json
{
  "action": "correct",
  "data": {"date_of_birth": "1990-04-03"},
  "reason": "Client confirmed day/month format"
}
```

`action` is `correct`, `approve`, or `reject`. Corrections merge provided target fields into the record. All supplied values must be text. Approve uses the same validation and cannot bypass uncertainty. Reject excludes the row. Resolving the final review automatically resumes delivery; there is no separate unconditional push endpoint.

### Status and errors

Migration states: `mapping`, `mapping_review`, `cleaning`, `review`, `ready`, `pushing`, `partial`, `complete`, `rolled_back`, `error`. A record also exposes `status`, `attempts`, validation `errors`, and any `integrationError`. The database is the source of truth; frontend buttons do not simulate success.

- 400: invalid input or failed correction validation
- 403: disallowed browser origin or internal API token failure
- 404: unknown migration/endpoint
- 409: state/lock conflict (for example editing after delivery begins)
- 413: request exceeds upload limit

## Browser integration

Set backend `FRONTEND_ORIGINS` to the comma-separated exact frontend origins (defaults: `http://localhost:3000,http://127.0.0.1:3000`). Approved origins receive explicit CORS headers, including for preflight and error responses. No wildcard or cookie credentials are used. CORS is a browser boundary, not authentication.

Set frontend `API_BASE_URL` to the URL reachable **from the user's browser**, e.g. `http://localhost:8000`. Docker service hostnames such as `backend` are not browser URLs. `.env.example` documents settings but is not automatically loaded; set environment variables through your shell or Compose.

## Retry and model policy

Transient target errors automatically receive at most three attempts per delivery action, with 0.25s/0.5s backoff. Permanent conflicts are not retried automatically. Manual retry opens a new bounded budget for failed records only. Demo E006 fails once; E007 fails three times before succeeding on consultant retry. Every attempt, retry and escalation is audited.

New mapping entries include `confidence` (heuristic policy score), `evidence`, `llmProposal`, and `proposedField`. Human resolution audits retain the complete previous proposal. Source files include `profile` with column types, missing/unique counts, samples and pattern ratios. No model-only confidence is treated as a calibrated probability.

## Mock target and readback

The agent uses real HTTP requests to `POST /mock/employees`, `GET /mock/employees?run_id=...` and `DELETE /mock/runs/{run_id}`. These internal routes require the process token. Rollback is scoped to a run, so it cannot delete unrelated inserts. Target writes reject conflicts on email **or employee ID**, even across separate runs.

Consultants can read persisted target results through `GET /api/runs/{id}/target`; this returns `{targetId, runId, data}` entries from the actual mock target. After rollback it returns an empty array. The frontend never receives the internal token.

The upload form exposes the explicit `simulate_failure=true` test option. It is off by default and only affects the mock target. It is not inferred from employee contents.
