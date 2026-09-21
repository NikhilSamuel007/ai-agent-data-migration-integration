# Verification — 20 September 2026

## Completed

- Backend: **18 pytest tests passed**. Covers CSV/XLSX, schema/contract consistency, required fields, status enums, birth dates, cleanup, exact duplicates and conflicts, mapping gates, human correction/rejection, retry exhaustion, rollback, persisted target readback, cross-run employee-ID conflicts, CORS, and restart idempotency.
- Frontend: TypeScript checking and Vite production build passed.
- Dependencies: `pip check` passed.
- Browser smoke: real three-file upload → Status review → approval → automatic delivery → retry → rollback. Eight source rows, one duplicate, six initial target successes, seven after manual retry, zero after rollback. No JavaScript errors or mobile overflow.
- Separate browser mapping check: Business group and Status reviewed, one record delivered and rolled back.
- Actual models: **Ollama 0.34.2 / Qwen2.5 1.5B**, CPU inference, and **MiniLM-L6-v2**, ONNX Runtime. No mocked provider was used for the real-model checks below.
- Mapping evaluation: **14 authored cases, 6 automatic mappings, including 3 unfamiliar headers; 0 unsafe automatic decisions in this set**. All deliberately ambiguous, incompatible-value and insufficient-sample cases stayed in review. The remaining clear but weakly supported cases also stayed in review. See [full evidence](mapping-evaluation.json). This is a small regression set, not independently calibrated accuracy.
- Live API model check: three unfamiliar columns mapped automatically with real LLM agreement; three employee records validated and delivered through the HTTP mock target without human input. Verification writes were rolled back. See [run evidence](live-ai-verification.json).

One useful observed failure of model judgment: Qwen assigned `Status` to employment status with a self-score of 1.0. The agent still escalated it because the header is ambiguous and semantic separation is weak. The hard gates, not the model's claimed certainty, control writes.

## Environment limitation

**Container execution remains unverified.** Neither Docker nor a usable Linux container runtime is installed here. `scripts/verify_docker.ps1` was run and correctly stopped with “Docker is not installed. Container verification cannot run.” Dockerfiles, Compose configuration, health checks, persistent volumes and an isolated build/workflow verification script are supplied. On a Docker-enabled Windows machine run:

```powershell
./scripts/verify_docker.ps1
```

This is not a claim that image builds or container execution passed. No hosted deployment, production authentication, distributed execution or real HR connector is claimed.

## Recording

The saved `docs/demo.webm` is **3 minutes 38 seconds**, 1440×1000. Browser playback metadata was verified. All recorded workflow assertions passed with Qwen available; recording and encoding took 228 seconds in total.

`python scripts/record_demo.py` records the actual UI with explanatory captions and a deliberately paced 3–5 minute sequence. `--quick` runs the same workflow assertions without presentation pauses. The recording shows a genuine Status escalation, human resolution, automatic continuation, failure/retry, audit and rollback. It uses explicitly selected mock failure simulation.

## Data compatibility

Schema v3 uses `data/relay-v3.sqlite` by default. Previous data remains in `data/relay.sqlite`; first/last names and birth dates were not guessed from old full-name/start-date data. New sample files and schema are the source of the new demo. Git remains removed as requested.
