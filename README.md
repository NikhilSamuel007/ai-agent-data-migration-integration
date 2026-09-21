# Relay — controlled autonomous migration

A small employee migration application following the principle: **AI proposes semantic mappings, code performs deterministic transformations, and humans resolve ambiguity.** The React frontend and Python API run independently.

## Architecture and stack

```text
React + TypeScript UI :3000
       │ REST uploads, decisions, polling, audit exports
       ▼
FastAPI + Pydantic API :8000
       ├─ CSV/XLSX ingestion → pandas data profiler
       ├─ Mapping policy → MiniLM semantic ranking + Ollama LLM adapter
       ├─ Deterministic cleanup → validation → identity reconciliation
       ├─ Focused human review → automatic continuation
       └─ Mock target HTTP API → bounded retry / rollback → SQLite audit
```

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic, pandas, openpyxl, requests.
- **AI:** Qwen2.5 1.5B through a swappable Ollama adapter; MiniLM-L6-v2 through local ONNX Runtime for independent semantic evidence.
- **Frontend:** React, TypeScript, Vite, Tailwind CSS plus the app's custom styles. Named dashboard, review, record-result and audit components.
- **Database:** SQLite with Python sqlite3. Existing snapshots and audit history remain compatible.
- **Tests:** pytest and Playwright's Python API.
- **Deployment:** separate frontend/backend Dockerfiles and Compose, with an optional Ollama service.

The version 3 employee schema includes employee ID, first/last name, email, birth date, department and employment status. Optional account status describes platform login access independently of employment; this makes Status a genuine ambiguity. Required fields and status enums are enforced by the backend. There is no swarm, RAG, vector database, name-based automatic fuzzy merge, or arbitrary name title-casing. SQLite stays simple rather than adding an ORM that the prototype does not need.

## Local setup

Requires Python 3.11+ and Node.js 22+ for building the React frontend. Node is not used by the Python agent or required to serve the built frontend.

```sh
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cd frontend
npm install
npm run build
cd ..
```

The included `frontend/pnpm-lock.yaml` is the tested JavaScript lockfile. For exact frontend dependencies use `pnpm install --frozen-lockfile` and `pnpm run build` (pnpm 11.19.0). `backend/requirements-lock.txt` pins the tested Python environment including development tools.

Run in two terminals:

```sh
python backend/server.py
python frontend/server.py
```

- **UI:** http://localhost:3000
- **API health:** http://localhost:8000/api/health
- **Interactive API docs:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json
- **Endpoint examples:** [backend/API.md](backend/API.md)

After setup/build, `python start.py` starts both independent services. For frontend development run `npm run dev` from `frontend/` instead of its Python static host.

## Ollama setup and truthful fallback

Install [Ollama](https://ollama.com/download), start its service, and download the configured model:

```sh
ollama pull qwen2.5:1.5b
```

`OLLAMA_URL` defaults to `http://127.0.0.1:11434`; `OLLAMA_MODEL` defaults to `qwen2.5:1.5b`. Another locally available model can be selected without editing the mapping agent. Unknown column profiles and at most three bounded sample values are sent to this endpoint, so use a trusted local endpoint for client data. No paid API is required.

The adapter requests structured JSON and validates it with Pydantic. Model-supplied fields, scores and reasons are proposals, never executable instructions or permission to write. Invalid JSON, invalid fields, timeout or missing Ollama cause an explicit unavailable state. The cached open-source [MiniLM model](https://huggingface.co/Xenova/all-MiniLM-L6-v2) still ranks candidates, but such mappings stay in human review. For reproducible evidence, run `python scripts/evaluate_mapping.py` and `python scripts/verify_live_ai.py` with Ollama running. These scripts fail if real inference is unavailable. See `docs/VERIFICATION.md` for the actual verification outcome; fixture tests alone do not prove model execution.

## Autonomy policy

1. **Profile deterministically.** Each column has observed type, non-empty/missing counts, unique values, samples, and email/date/ID/text compatibility ratios.
2. **Apply unique explicit aliases automatically.** Their values still undergo record validation; an alias never certifies that a value is valid.
3. **For unfamiliar headers, combine evidence.** Policy score = 0.65 × semantic similarity + 0.15 × agreeing LLM self-score + 0.20 × value compatibility. Each evidence source is counted once. Compatibility for status fields measures membership in the target enum.
4. **Require all gates for semantic autonomy:** score ≥ 0.90, semantic similarity ≥ 0.80, top-two margin ≥ 0.20, value compatibility ≥ 0.95, LLM agreement with score ≥ 0.90, at least three non-empty samples, no reserved target or competing source, and no explicitly ambiguous header. The score is an uncalibrated heuristic, not measured accuracy. Unknown Contact/Status/Date/ID headers remain reviewed.
5. **Normalize safely.** Whitespace, email and known-status casing, and uniquely interpretable dates. Birth dates cannot be in the future, employment status must be Active/Inactive/Leave, and optional account status must be Active/Inactive/Locked. Validate before and after the cleanup pass. Missing values, invalid dates and ambiguous dates are never invented or guessed.
6. **Reconcile conservatively.** Exact normalized duplicates are excluded with lineage retained. Conflicting same-email or employee-ID records require correction/rejection. Human edits are revalidated, and resolving the final case automatically resumes delivery.
7. **Recover transient failures.** Up to three HTTP attempts per delivery action, with bounded 0.25s/0.5s backoff. Timeouts and 408/429/selected 5xx can retry; validation/identity conflicts cannot. Every attempt and retry is audited. An exhausted budget requires a consultant action.
8. **Rollback by ownership.** Remove only target inserts owned by this run. Keep source rows and audit history. Idempotency compares parsed payloads, surviving restarts and the old JavaScript JSON format.

No arbitrary percentage claims: consult the visible mapping evidence and [one-page write-up](docs/APPROACH.md). Threshold calibration on a labeled dataset is explicitly future work.

## Demo story

[Watch the recording](docs/demo.webm).

1. Upload `employees_hr.csv`, `employees_backup.csv`, and `staff.xlsx` from `backend/samples/`. Select **Simulate target failures (demo only)**. The sample shortcut uses the same sources and simulation.
2. Eight source rows have different column names, whitespace, email casing, mixed date formats and an exact duplicate. Known aliases map automatically.
3. The ambiguous **Status** column pauses delivery. Open **Review decisions**, choose **Employment status**, and save a reason confirming the file is an HR lifecycle export. Account status is a distinct optional field for platform login state.
4. The agent resumes, normalizes and validates values, retains duplicate lineage, then delivers seven unique employees. E006 recovers after one transient failure; E007 exhausts three attempts. Six records are delivered.
5. **Retry failed records** delivers E007 on attempt four. Inspect target IDs and the audit's model proposal, human resolution, before/after cleanup and retry events.
6. **Roll back writes** removes these seven inserts while retaining the source rows and audit.

`semantic-auto.csv` supplies three employees with unfamiliar identifier, email and birthday headers for real-model autonomy verification. `semantic-mapping.csv` demonstrates conservative review of Business group and Status. Both are separate from the three-file main demo.

## Source structure

```text
backend/
  server.py                 Uvicorn entry point
  relay/web.py              FastAPI composition and lifecycle
  relay/api/                migration.py, review.py, target.py controllers
  relay/contracts.py        Pydantic HTTP and target models
  relay/agent.py            Workflow supervisor
  relay/profiling.py         pandas-based source profiler
  relay/mapping.py           Evidence policy and autonomy gates
  relay/llm.py               LLMProvider boundary and Ollama adapter
  relay/model.py             Local MiniLM inference
  relay/engine.py            Deterministic cleanup, validation, reconciliation
  relay/target_client.py     HTTP transport with retryable-error classification
  relay/store.py             SQLite state and audit
  tests/                    Policy, engine, HTTP and restart tests
  samples/                  CSV/XLSX demo exports
frontend/
  src/App.tsx               Application state and API polling
  src/api.ts                Typed API client
  src/pages/                Dashboard, ReviewQueue, Records, Audit
  src/components/           EscalationCard, stats, activity, integration actions
  server.py                 Serves production build and runtime config
```

## Configuration and Docker

`.env.example` files document settings; set them through the shell or Compose (they are not automatically loaded). Defaults: API port 8000, frontend port 3000; local hosts bind to loopback. `API_BASE_URL` must be browser-reachable. Configure exact allowed origins through `FRONTEND_ORIGINS`. `DB_PATH` and `MODEL_CACHE_DIR` use project-level data/cache defaults. Schema v3 uses `data/relay-v3.sqlite`; the previous `data/relay.sqlite` is preserved and is not silently converted. Do not point the v3 server at an old-schema database. Run only one backend process; locks are process-local.

```sh
# Works with explicit review fallback when Ollama is absent:
docker compose up --build -d
# Or include the local LLM service:
docker compose --profile ai up --build -d
docker compose exec ollama ollama pull qwen2.5:1.5b
```

Stop local processes occupying ports 3000/8000 first. Named volumes persist database, semantic cache, and Ollama weights. Images do not include client data. `docker compose down` preserves volumes; `down -v` removes them. Docker is unavailable in the authoring environment, so image builds were not executed there. The frontend uses a multi-stage Node build and a small Python static runtime; production hosting should replace the prototype static host and add TLS/authentication.

## Verify

The current local checks passed: 18 backend tests, frontend build, browser workflows, actual Qwen/MiniLM evaluation and autonomous HTTP delivery. See `docs/VERIFICATION.md` for evidence and the Docker limitation.

```sh
python -m pip install -r backend/requirements-dev.txt
python -m pytest -q
cd frontend
npm run build
cd ..
python -m playwright install chromium
# With both services running:
python scripts/check_mapping.py
python scripts/verify_live_ai.py
python scripts/evaluate_mapping.py
python scripts/record_demo.py --quick
python scripts/record_demo.py
```

Tests cover policy gates, malformed LLM output, unavailable-provider escalation, profile statistics, ambiguous dates, normalization, CSV/XLSX validation, duplicates/conflicts, human correction/rejection, automatic retry exhaustion, manual retry, scoped rollback, CORS, and restart idempotency. Browser checks exercise the real two-service UI and local embedding model.

Scope remains single-operator, one employee entity and insert-only mock integration. No authentication, encryption at rest, distributed jobs, real HR connector or tamper-proof audit is claimed. Input limits remain five files, 5 MB each, 1,000 records and 50 columns per file; formulas and oversized expanded XLSX archives are refused. Local Git history remains removed as requested. A source repository must be created separately if required for submission.

## Optional portable Ollama on Windows

The normal Ollama installation above is preferred. This workspace also supports an isolated CPU runtime, extracted from the [official Ollama Windows release](https://github.com/ollama/ollama/releases/tag/v0.34.2). GPU libraries are omitted. Model weights and runtime live under `.cache/` and are excluded from Docker images.

```powershell
python -m pip install remotezip
python scripts/bootstrap_ollama.py
./scripts/start_ollama.ps1
./.cache/ollama-runtime/ollama.exe pull qwen2.5:1.5b
```

The bootstrap checks ZIP entry CRCs; it is an optional setup tool, not an application dependency. Ollama startup binds to loopback and limits parallel inference to one. The API allows up to 120 seconds per model response. Use a machine with sufficient free memory for the configured model.

## Verification artifacts

- `docs/VERIFICATION.md`: completed checks and environment limitations.
- `docs/mapping-evaluation.json`: per-case real-model proposals, evidence, coverage and unsafe automatic decision count. This small authored set is a regression check, not independent statistical calibration.
- `docs/live-ai-verification.json`: actual API run with unfamiliar headers mapped and delivered autonomously.
- `scripts/verify_docker.ps1`: builds and exercises containers on alternate ports using an isolated Compose project, then stops it while preserving volumes. Requires Docker Desktop running Linux containers.
